"""
Problem-agnostic tutor endpoints — Module 01 inference approach applied to
any problem in the research library.

LLM = tutor/discovery only. No function calling. No simulation control.
The sliders run sims; the LLM assesses results and answers physics questions.
"""
import json
import os
import time
from collections import defaultdict, deque
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.session_logger import log_event

router = APIRouter()

_RATE_PER_MIN = int(os.environ.get("TUTOR_RATE_PER_MIN", "10"))
_ip_hits: dict = defaultdict(deque)


def _check_rate(request: Request) -> None:
    now = time.time()
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    hits = _ip_hits[ip]
    while hits and now - hits[0] > 60:
        hits.popleft()
    if len(hits) >= _RATE_PER_MIN:
        raise HTTPException(status_code=429, detail="Too many requests — wait a minute.")
    hits.append(now)


def _load_problems() -> list:
    path = os.path.join(os.path.dirname(__file__), "../../data/problems.json")
    with open(path) as f:
        return json.load(f)["problems"]


def _get_problem(problem_id: str) -> dict:
    problems = _load_problems()
    p = next((p for p in problems if p["id"] == problem_id), None)
    if not p:
        raise HTTPException(status_code=404, detail="Problem not found")
    return p


def _gemini_text(prompt: str) -> str:
    from google import genai
    client = genai.Client()
    model = os.environ.get("AI_MODEL", "gemini-2.5-flash")
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text.strip()


def _success_lines(criteria: dict, design_alpha: float, re: int) -> str:
    lines = []
    if "cruise_CL_min" in criteria:
        lines.append(f"- CL ≥ {criteria['cruise_CL_min']} at α = {design_alpha}°, Re = {re:,}")
    if "target_LD" in criteria:
        lines.append(f"- L/D ≥ {criteria['target_LD']}")
    if "stall_angle_improvement" in criteria:
        lines.append(f"- Stall angle improvement ≥ {criteria['stall_angle_improvement']}° vs baseline")
    return "\n".join(lines) if lines else "- (See problem brief)"


# ------------------------------------------------------------------
# Assess — called after each slider run
# ------------------------------------------------------------------

class AssessRequest(BaseModel):
    session_id: str
    problem_id: str
    airfoil: str
    alpha: float
    reynolds: int
    CL: float
    CD: float
    L_D: Optional[float] = None


@router.post("/assess")
def assess_run(req: AssessRequest, http_request: Request):
    _check_rate(http_request)
    p = _get_problem(req.problem_id)
    criteria = p["success_criteria"]
    design_alpha = p.get("design_alpha", 4)

    cl_min = criteria.get("cruise_CL_min")
    cl_meets = req.CL >= cl_min if cl_min is not None else None
    ld_min = criteria.get("target_LD")
    ld_meets = (req.L_D or 0) >= ld_min if ld_min is not None else None
    at_design = (req.alpha == design_alpha and req.reynolds == req.reynolds)

    status_lines = []
    if cl_min is not None:
        gap = round((req.CL / cl_min - 1) * 100, 1)
        status_lines.append(f"CL = {req.CL:.4f} (need ≥ {cl_min}) → {'MEETS' if cl_meets else f'FAILS ({abs(gap):.1f}% short)'}")
    if ld_min is not None and req.L_D is not None:
        gap = round((req.L_D / ld_min - 1) * 100, 1)
        status_lines.append(f"L/D = {req.L_D:.1f} (need ≥ {ld_min}) → {'MEETS' if ld_meets else f'FAILS ({abs(gap):.1f}% short)'}")
    if req.L_D is not None and ld_min is None:
        status_lines.append(f"L/D = {req.L_D:.1f}")

    cond_note = (
        f"Run at design condition (α = {design_alpha}°, Re = {req.reynolds:,})."
        if req.alpha == design_alpha else
        f"Note: this run was at α = {req.alpha}° — design point is α = {design_alpha}°."
    )

    success_str = _success_lines(criteria, design_alpha, req.reynolds)

    prompt = f"""You are an aerodynamics tutor for AirfoilLearner. A student is solving: "{p['title']}"

Problem context (bottleneck): {p['bottleneck']}

Success criteria:
{success_str}

Student just simulated NACA {req.airfoil} at α = {req.alpha}°, Re = {req.reynolds:,}:
{chr(10).join(status_lines)}
{cond_note}

Write 4 sentences:
1. Which criteria pass or fail, and by how much.
2. What this result reveals about the airfoil's geometry (camber, thickness) for this flow regime.
3. What physical direction to explore next — use geometry terms, never specific NACA codes.
4. One concrete thing to check or think about before the next run.

Be direct and speak to the student as a working aerodynamicist."""

    try:
        message = _gemini_text(prompt)
    except Exception:
        message = " · ".join(status_lines) or "Run recorded."

    compliance = {}
    if cl_min is not None:
        compliance["CL"] = {
            "value": req.CL, "target": cl_min, "meets": bool(cl_meets),
            "gap_pct": round((req.CL / cl_min - 1) * 100, 1),
        }
    if ld_min is not None and req.L_D is not None:
        compliance["L_D"] = {
            "value": req.L_D, "target": ld_min, "meets": bool(ld_meets),
            "gap_pct": round((req.L_D / ld_min - 1) * 100, 1),
        }

    log_event(req.session_id, "tutor_assess", {
        "problem_id": req.problem_id, "airfoil": req.airfoil,
        "alpha": req.alpha, "reynolds": req.reynolds,
        "CL": req.CL, "CD": req.CD,
    })
    return {
        "message": message,
        "compliance": compliance,
        "at_design_condition": req.alpha == design_alpha,
    }


# ------------------------------------------------------------------
# Ask — user-typed physics questions
# ------------------------------------------------------------------

class AskRequest(BaseModel):
    session_id: str
    problem_id: str
    question: str
    run_count: int = 0


@router.post("/ask")
def ask_tutor(req: AskRequest, http_request: Request):
    _check_rate(http_request)
    p = _get_problem(req.problem_id)
    q = req.question.strip()
    if len(q) < 3:
        raise HTTPException(status_code=422, detail="Ask a real question.")
    if len(q) > 600:
        raise HTTPException(status_code=422, detail="Keep the question under 600 characters.")

    success_str = _success_lines(p["success_criteria"], p.get("design_alpha", 4), p.get("Re", 500000))

    prompt = f"""You are an aerodynamics tutor for AirfoilLearner. The student is solving: "{p['title']}"

Bottleneck: {p['bottleneck']}
Success criteria:
{success_str}
Baseline airfoil: NACA {p['starting_airfoil'].replace('naca', '')}
The student has run {req.run_count} simulations so far.

Your role:
- Explain aerodynamic physics clearly — build intuition, not dependency
- Connect airfoil geometry (camber, thickness, camber position) to performance
- Do NOT suggest specific NACA codes or solve the design for them
- Keep answers to 3–5 sentences, concrete and grounded in this specific problem

Student question: {q}"""

    try:
        message = _gemini_text(prompt)
    except Exception:
        message = "Having trouble connecting right now — try again in a moment."

    log_event(req.session_id, "tutor_ask", {
        "problem_id": req.problem_id, "question": q, "run_count": req.run_count,
    })
    return {"message": message}


# ------------------------------------------------------------------
# Hint — welcome and progress hints
# ------------------------------------------------------------------

class HintResult(BaseModel):
    airfoil: str
    CL: float
    cd_meets: bool
    cl_meets: bool


class HintRequest(BaseModel):
    session_id: str
    problem_id: str
    run_count: int = 0
    recent_results: List[HintResult] = Field(default_factory=list)
    hint_type: str = "welcome"


@router.post("/hint")
def get_hint(req: HintRequest, http_request: Request):
    _check_rate(http_request)
    p = _get_problem(req.problem_id)
    design_alpha = p.get("design_alpha", 4)
    re = p.get("Re", 500000)
    baseline = p["starting_airfoil"].replace("naca", "")
    success_str = _success_lines(p["success_criteria"], design_alpha, re)

    if req.hint_type == "welcome":
        prompt = f"""You are an aerodynamics tutor for AirfoilLearner. A student is about to start solving: "{p['title']}"

Bottleneck: {p['bottleneck']}
Baseline: NACA {baseline} at α = {design_alpha}°, Re = {re:,}
Success criteria:
{success_str}

Write a 3-sentence welcome:
1. Frame the design task — what physical constraint is the student solving?
2. Tell them what to do first (run the baseline, observe the gap)
3. Hint at the physical lever without giving a specific airfoil code

Be direct and concrete. No headers or bullet points."""
    else:
        if not req.recent_results:
            return {"message": None}
        results_text = "\n".join(
            f"  NACA {r.airfoil}: CL {'✓' if r.cl_meets else '✗'}"
            for r in req.recent_results
        )
        prompt = f"""You are an aerodynamics tutor for AirfoilLearner. The student is solving: "{p['title']}"

Success criteria:
{success_str}

Their last {len(req.recent_results)} runs:
{results_text}
Total runs so far: {req.run_count}

Give a 3-sentence coaching hint:
1. What their exploration pattern reveals about the design space so far
2. The physical reason for the gap and which geometric property to change
3. A concrete direction to try — use physics terms (camber, thickness, camber position), never specific NACA codes"""

    try:
        message = _gemini_text(prompt)
    except Exception:
        message = f"Keep exploring — run the baseline NACA {baseline} at α = {design_alpha}°, Re = {re:,} first if you haven't yet, then vary camber to close the gap."

    log_event(req.session_id, "tutor_hint", {
        "problem_id": req.problem_id, "hint_type": req.hint_type, "run_count": req.run_count,
    })
    return {"message": message}
