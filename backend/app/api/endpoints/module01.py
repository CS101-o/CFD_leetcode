"""
Module 01 — AirfoilLearner v1 ("Forage for Simulation").

Flow: brief -> requirements extraction -> prediction gate -> design loop
      -> intern checkpoint -> design review -> shareable artifact.

Design-loop simulation itself uses the existing /simulate endpoints; this
router owns the module definition, the judgment checkpoints, the review
submission, and the public artifact page.
"""
import html
import json
import os
import re
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.services.session_logger import log_event, get_session
from app.utils.neuralfoil_wrapper import get_predictor, create_naca_airfoil

router = APIRouter()
public_router = APIRouter()

_predictor = get_predictor()

# ------------------------------------------------------------------
# Rate limiting for LLM endpoints
# ------------------------------------------------------------------
_LLM_RATE_PER_MIN = int(os.environ.get("MOD_LLM_RATE_PER_MIN", "30"))
_llm_ip_hits: dict = defaultdict(deque)


def _llm_check_rate(request: Request) -> None:
    now = time.time()
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    hits = _llm_ip_hits[ip]
    while hits and now - hits[0] > 60:
        hits.popleft()
    if len(hits) >= _LLM_RATE_PER_MIN:
        raise HTTPException(status_code=429, detail="Too many requests — wait a minute and try again.")
    hits.append(now)


def _gemini_text(prompt: str) -> str:
    from google import genai
    client = genai.Client()
    model = os.environ.get("AI_MODEL", "gemini-2.5-flash")
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text.strip()

_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")
# User-generated data (artifacts, signups) goes to DATA_DIR when set — e.g. a
# Railway volume at /data — so it survives redeploys. Module content stays in
# the repo's data dir.
_USER_DATA_DIR = os.environ.get("DATA_DIR") or _DATA_DIR
_ARTIFACT_DIR = os.path.join(_USER_DATA_DIR, "artifacts")
_SIGNUPS_PATH = os.path.join(_USER_DATA_DIR, "signups.jsonl")


def _load_module() -> dict:
    with open(os.path.join(_DATA_DIR, "module01.json")) as f:
        return json.load(f)


def _append_signup(record: dict) -> None:
    os.makedirs(_USER_DATA_DIR, exist_ok=True)
    with open(_SIGNUPS_PATH, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **record,
        }) + "\n")


# ------------------------------------------------------------------
# Module definition (answer keys stripped)
# ------------------------------------------------------------------

@router.get("")
def get_module():
    m = _load_module()
    for q in m["requirements_questions"]:
        q.pop("correct", None)
        q.pop("hint", None)
    m["checkpoint"].pop("reveal", None)
    m.pop("requirements_key", None)
    return m


# ------------------------------------------------------------------
# Instrumentation
# ------------------------------------------------------------------

_ALLOWED_EVENTS = {
    "module_start", "stage_enter", "brief_read",
    "estimate_mismatch_shown", "artifact_viewed", "forage_link_clicked",
}


class EventRequest(BaseModel):
    session_id: str
    event: str
    data: dict = Field(default_factory=dict)


@router.post("/event")
def post_event(req: EventRequest):
    if req.event not in _ALLOWED_EVENTS:
        raise HTTPException(status_code=400, detail="Unknown event")
    log_event(req.session_id, req.event, {"module": "module01", **req.data})
    return {"status": "ok"}


class StartRequest(BaseModel):
    session_id: str


@router.post("/start")
def start_module(req: StartRequest, request: Request):
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    log_event(req.session_id, "session_start", {
        "module": "module01",
        "problem_id": "module01_sparrow7",
        "problem_title": "SPARROW-7 Wing Redesign",
        "ip": ip,
    })
    return {"status": "ok"}


# ------------------------------------------------------------------
# LLM tutor — simulation assessment and free Q&A
# ------------------------------------------------------------------

class AssessRequest(BaseModel):
    session_id: str
    airfoil: str
    alpha: float
    reynolds: int
    CL: float
    CD: float
    L_D: Optional[float] = None


@router.post("/assess")
def assess_run(req: AssessRequest, http_request: Request):
    _llm_check_rate(http_request)
    m = _load_module()
    key = m["requirements_key"]
    cl_meets = req.CL >= key["target_CL"]
    cd_meets = req.CD <= key["max_CD"]
    cl_gap_pct = round((req.CL / key["target_CL"] - 1) * 100, 1)
    cd_gap_pct = round((1 - req.CD / key["max_CD"]) * 100, 1)
    at_design = (req.alpha == key["design_alpha"] and req.reynolds == key["reynolds"])

    cond_note = (
        f"This run was at the design condition (α = {key['design_alpha']}°, Re = {key['reynolds']:,})."
        if at_design else
        f"Note: this run was at α = {req.alpha}°, Re = {req.reynolds:,} — not the design point "
        f"(α = {key['design_alpha']}°, Re = {key['reynolds']:,}). The compliance targets apply at the design point."
    )

    prompt = f"""You are an aerodynamics tutor for Module 01 of AirfoilLearner. A student is selecting a NACA 4-digit wing section for SPARROW-7 UAV to recover lift lost to an overweight battery pack while staying within a drag budget that protects endurance.

Design requirements at α = {key['design_alpha']}°, Re = {key['reynolds']:,}:
- CL ≥ {key['target_CL']}
- CD ≤ {key['max_CD']}

Student just simulated NACA {req.airfoil} at α = {req.alpha}°, Re = {req.reynolds:,}:
- CL = {req.CL:.4f} → {"MEETS" if cl_meets else f"FAILS ({abs(cl_gap_pct):.1f}% below target)"}
- CD = {req.CD:.5f} → {"MEETS" if cd_meets else f"FAILS ({abs(cd_gap_pct):.1f}% over budget)"}
{"- L/D = " + str(round(req.L_D, 1)) if req.L_D else ""}
{cond_note}

Write 4–5 sentences total:
1. One sentence on which requirements pass or fail and by what margin.
2. Two sentences on what this result reveals about the airfoil's camber and thickness at this Reynolds number — speak to the physics, not just the numbers.
3. One sentence on what geometric property to adjust next to close any gap — use physics terms (camber, thickness, camber position), never specific NACA codes.

Be direct and specific to these numbers. Speak as one aerodynamicist to another."""

    try:
        message = _gemini_text(prompt)
    except Exception:
        cl_str = f"CL = {req.CL:.4f} ({'meets' if cl_meets else 'below'} target {key['target_CL']})"
        cd_str = f"CD = {req.CD:.5f} ({'meets' if cd_meets else 'exceeds'} budget {key['max_CD']})"
        message = f"{cl_str}; {cd_str}. Run at α = {key['design_alpha']}° and Re = {key['reynolds']:,} to check the design point."

    log_event(req.session_id, "assessment_requested", {
        "module": "module01", "airfoil": req.airfoil,
        "alpha": req.alpha, "reynolds": req.reynolds,
        "CL": req.CL, "CD": req.CD, "cl_meets": cl_meets, "cd_meets": cd_meets,
    })
    return {
        "message": message,
        "compliance": {
            "CL": {"value": req.CL, "target": key["target_CL"], "meets": cl_meets, "gap_pct": cl_gap_pct},
            "CD": {"value": req.CD, "budget": key["max_CD"], "meets": cd_meets, "gap_pct": cd_gap_pct},
        },
        "at_design_condition": at_design,
    }


class AskRequest(BaseModel):
    session_id: str
    question: str
    run_count: int = 0


@router.post("/ask")
def ask_tutor(req: AskRequest, http_request: Request):
    _llm_check_rate(http_request)
    m = _load_module()
    key = m["requirements_key"]
    q = req.question.strip()
    if len(q) < 3:
        raise HTTPException(status_code=422, detail="Ask a real question.")
    if len(q) > 600:
        raise HTTPException(status_code=422, detail="Keep the question under 600 characters.")

    prompt = f"""You are an aerodynamics tutor for Module 01 of AirfoilLearner. The student is selecting a NACA 4-digit wing section for SPARROW-7 UAV. Requirements: CL ≥ {key['target_CL']}, CD ≤ {key['max_CD']}, at α = {key['design_alpha']}°, Re = {key['reynolds']:,}.

The student has run {req.run_count} simulation{"s" if req.run_count != 1 else ""} so far.

Your role:
- Explain aerodynamic physics and build the student's intuition
- Connect airfoil geometry (camber, thickness, camber position) to performance (CL, CD)
- Never suggest specific NACA codes or directly solve the design for them
- Never run or describe simulation results they haven't seen
- Keep answers to 3–5 sentences, concrete and direct

Student question: {q}"""

    try:
        message = _gemini_text(prompt)
    except Exception:
        message = "I'm having trouble connecting right now. The background reading has the physics you need — remember that camber is the primary lever for lift at a fixed angle of attack, and the Reynolds regime here (Re ≈ 5×10⁵) means drag is more sensitive to geometry than it would be at higher speeds."

    log_event(req.session_id, "tutor_question", {
        "module": "module01", "question": q, "run_count": req.run_count,
    })
    return {"message": message}


class HintResult(BaseModel):
    airfoil: str
    CL: float
    CD: float
    cl_meets: bool
    cd_meets: bool


class HintRequest(BaseModel):
    session_id: str
    run_count: int
    recent_results: List[HintResult] = Field(default_factory=list)
    hint_type: str = "progress"   # "welcome" | "progress"


@router.post("/hint")
def get_hint(req: HintRequest, http_request: Request):
    _llm_check_rate(http_request)
    m = _load_module()
    key = m["requirements_key"]

    if req.hint_type == "welcome":
        prompt = f"""You are an aerodynamics tutor for Module 01 of AirfoilLearner. A student is about to start the design loop for SPARROW-7 UAV.

Context:
- Baseline airfoil: NACA {m['conditions']['airfoil_baseline']} at α = {key['design_alpha']}°, Re = {key['reynolds']:,}
- The baseline gives CL ≈ 0.805 — the old cruise target
- Weight increase now requires CL ≥ {key['target_CL']} at the same condition
- Drag budget: CD ≤ {key['max_CD']}

Write a 3-sentence welcome that:
1. Orients them to the design task (what changed and why)
2. Tells them what to do first (run the baseline, observe the gap)
3. Hints at the physical lever to pull — without giving a specific airfoil

Be direct and concrete. Do not use headers or bullet points."""
    else:
        if not req.recent_results:
            return {"message": None}

        results_text = "\n".join(
            f"  NACA {r.airfoil}: CL={r.CL:.4f} ({'✓' if r.cl_meets else '✗'}), CD={r.CD:.5f} ({'✓' if r.cd_meets else '✗'})"
            for r in req.recent_results
        )
        any_cl_meets = any(r.cl_meets for r in req.recent_results)
        any_cd_meets = any(r.cd_meets for r in req.recent_results)

        if any_cl_meets and not any_cd_meets:
            focus = "The lift target is reachable but drag is over budget. Focus on what reduces CD without giving up too much CL."
        elif not any_cl_meets and any_cd_meets:
            focus = "Drag is within budget but lift falls short. Focus on what raises CL at the design angle without pushing CD over the limit."
        else:
            focus = "Both targets are still out of reach. Focus on the lift gap first, then check drag."

        last = req.recent_results[-1] if req.recent_results else None
        last_line = f"Last run: NACA {last.airfoil} — CL={last.CL:.4f} ({'✓' if last.cl_meets else '✗'}), CD={last.CD:.5f} ({'✓' if last.cd_meets else '✗'})" if last else ""

        prompt = f"""You are an aerodynamics tutor for Module 01 of AirfoilLearner. The student is actively designing and needs a concrete next-step suggestion.

Requirements: CL ≥ {key['target_CL']}, CD ≤ {key['max_CD']}, at α = {key['design_alpha']}°, Re = {key['reynolds']:,}.

{last_line}
All recent results:
{results_text}

Situation: {focus}

Give 4 short, punchy sentences — no headers, no bullets:
1. What this specific result tells you about where they are in the design space.
2. The physical reason for the gap (camber, thickness, pressure gradient — be precise).
3. A concrete suggestion: which geometric property to increase or decrease, and roughly by how much (e.g. "try adding 1–2% more camber").
4. One quick thing to watch for in the next run that will confirm whether the change worked.

Write like a senior engineer who wants them to succeed. Give a real suggestion, not a vague nudge."""

    try:
        message = _gemini_text(prompt)
    except Exception:
        if req.hint_type == "welcome":
            message = f"Your starting point is NACA {m['conditions']['airfoil_baseline']} — it meets the old CL target of 0.805 but the weight increase now requires CL ≥ {key['target_CL']}. Run the baseline first at α = {key['design_alpha']}°, Re = {key['reynolds']:,} to see the gap. Camber is the primary lever for lift at a fixed angle of attack."
        else:
            message = f"You're {req.run_count} runs in — keep exploring camber and thickness systematically. At Re = {key['reynolds']:,}, higher camber raises CL at a fixed angle of attack but can increase drag, so watch both numbers together."

    log_event(req.session_id, "hint_given", {
        "module": "module01", "hint_type": req.hint_type,
        "run_count": req.run_count,
    })
    return {"message": message}


# ------------------------------------------------------------------
# Stage 1 — requirements extraction
# ------------------------------------------------------------------

class RequirementsRequest(BaseModel):
    session_id: str
    answers: List[int]


@router.post("/requirements/check")
def check_requirements(req: RequirementsRequest):
    m = _load_module()
    questions = m["requirements_questions"]
    if len(req.answers) != len(questions):
        raise HTTPException(status_code=400, detail="Answer every requirement")
    results = []
    for q, a in zip(questions, req.answers):
        ok = a == q["correct"]
        results.append({
            "id": q["id"],
            "correct": ok,
            "hint": None if ok else q["hint"],
        })
    all_correct = all(r["correct"] for r in results)
    log_event(req.session_id, "requirements_checked", {
        "module": "module01",
        "answers": req.answers,
        "n_wrong": sum(1 for r in results if not r["correct"]),
        "all_correct": all_correct,
    })
    return {"results": results, "all_correct": all_correct}


# ------------------------------------------------------------------
# Stage 2 — prediction gate
# ------------------------------------------------------------------

class PredictionRequest(BaseModel):
    session_id: str
    estimate_CL: float


@router.post("/prediction")
def record_prediction(req: PredictionRequest):
    log_event(req.session_id, "prediction_made", {
        "module": "module01",
        "estimate_CL": req.estimate_CL,
    })
    return {"status": "ok"}


# ------------------------------------------------------------------
# Stage 4 — intern checkpoint
# ------------------------------------------------------------------

class CheckpointRequest(BaseModel):
    session_id: str
    would_sign_off: bool
    reasoning: str


@router.post("/checkpoint")
def answer_checkpoint(req: CheckpointRequest):
    m = _load_module()
    min_chars = m["checkpoint"].get("min_answer_chars", 60)
    if len(req.reasoning.strip()) < min_chars:
        raise HTTPException(
            status_code=422,
            detail=f"A reviewer owes the intern more than that — at least {min_chars} characters of reasoning.",
        )
    log_event(req.session_id, "checkpoint_answer", {
        "module": "module01",
        "would_sign_off": req.would_sign_off,
        "reasoning": req.reasoning.strip(),
    })
    return {"reveal": m["checkpoint"]["reveal"]}


# ------------------------------------------------------------------
# Stage 6 — design review submission -> artifact
# ------------------------------------------------------------------

class ReviewRequest(BaseModel):
    session_id: str
    airfoil: str
    alpha: float = 5.0
    justification: str
    tradeoff: str
    validate_next: str


def _judgment_signals(session_id: str, design_re: float) -> dict:
    events = get_session(session_id)
    runs = [e for e in events if e.get("event") == "simulation_run" and "reynolds" in e]
    sweeps = [e for e in events if e.get("event") == "polar_sweep"]
    wrong_re = [e for e in runs if abs(e.get("reynolds", design_re) - design_re) > design_re * 0.05]
    prediction = next((e for e in events if e.get("event") == "prediction_made"), None)
    first_run = runs[0] if runs else None
    checkpoint = next((e for e in events if e.get("event") == "checkpoint_answer"), None)
    requirements = next((e for e in events if e.get("event") == "requirements_checked"), None)
    return {
        "n_runs": len(runs),
        "n_sweeps": len(sweeps),
        "n_offcondition_runs": len(wrong_re),
        "airfoils_tested": sorted({e.get("airfoil") for e in runs if e.get("airfoil")}),
        "estimate_CL": prediction.get("estimate_CL") if prediction else None,
        "first_run_CL": first_run.get("CL") if first_run else None,
        "requirements_wrong_first_try": requirements.get("n_wrong") if requirements else None,
        "checkpoint_would_sign_off": checkpoint.get("would_sign_off") if checkpoint else None,
        "checkpoint_reasoning": checkpoint.get("reasoning") if checkpoint else None,
    }


@router.post("/review/submit")
def submit_review(req: ReviewRequest):
    m = _load_module()
    form = m["review_form"]
    key = m["requirements_key"]
    cond = m["conditions"]

    code = re.sub(r"\D", "", req.airfoil)
    if len(code) != 4:
        raise HTTPException(status_code=422, detail="Final design must be a 4-digit NACA code")
    for field, value in (("justification", req.justification),
                         ("tradeoff", req.tradeoff),
                         ("validate_next", req.validate_next)):
        min_len = form["min_justification_chars"] if field == "justification" else form["min_field_chars"]
        if len(value.strip()) < min_len:
            raise HTTPException(
                status_code=422,
                detail=f"'{field}' needs a real answer — at least {min_len} characters.",
            )

    # Verify the submitted design at the brief's operating point
    coords = create_naca_airfoil(code)
    point = _predictor.predict(
        coordinates=coords, alpha=req.alpha,
        reynolds=key["reynolds"], mach=cond["mach"],
    )
    polar = _predictor.predict_polar(
        coordinates=coords, alpha_range=(-2, 14), alpha_step=1.0,
        reynolds=key["reynolds"], mach=cond["mach"],
    )

    cl, cd = point["CL"], point["CD"]
    compliance = {
        "CL": {"value": round(cl, 4), "target": key["target_CL"], "meets": cl >= key["target_CL"],
               "margin_pct": round((cl / key["target_CL"] - 1) * 100, 1)},
        "CD": {"value": round(cd, 5), "budget": key["max_CD"], "meets": cd <= key["max_CD"],
               "margin_pct": round((1 - cd / key["max_CD"]) * 100, 1)},
    }

    artifact = {
        "id": uuid.uuid4().hex[:12],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": req.session_id,
        "module": {"id": m["id"], "title": m["title"], "program": m["program"]},
        "brief_summary": (
            "Battery pack came in 8% over spec against a public 90-minute flight-time commitment. "
            "Recover the lift margin at the fixed cruise condition without busting the profile-drag "
            "budget that protects endurance. Two weeks to design freeze."
        ),
        "conditions": {"alpha": req.alpha, "reynolds": key["reynolds"], "mach": cond["mach"]},
        "design": {
            "airfoil": code,
            "CL": round(cl, 4), "CD": round(cd, 5),
            "L_D": round(cl / cd, 1) if cd > 1e-6 else None,
        },
        "compliance": compliance,
        "polar": [
            {"alpha": p["alpha"], "CL": round(p["CL"], 4),
             "L_D": round(p["L_D"], 1) if p["CD"] > 1e-6 else None}
            for p in polar
        ],
        "review": {
            "justification": req.justification.strip(),
            "tradeoff": req.tradeoff.strip(),
            "validate_next": req.validate_next.strip(),
        },
        "signals": _judgment_signals(req.session_id, key["reynolds"]),
        "skills": m["skills"],
        "claimed_email": None,
    }

    os.makedirs(_ARTIFACT_DIR, exist_ok=True)
    with open(os.path.join(_ARTIFACT_DIR, f"{artifact['id']}.json"), "w") as f:
        json.dump(artifact, f, indent=2)

    log_event(req.session_id, "review_submitted", {
        "module": "module01",
        "artifact_id": artifact["id"],
        "airfoil": code,
        "meets_CL": compliance["CL"]["meets"],
        "meets_CD": compliance["CD"]["meets"],
    })
    return {"artifact_id": artifact["id"], "artifact_url": f"/a/{artifact['id']}",
            "compliance": compliance, "design": artifact["design"]}


def _load_artifact(artifact_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{12}", artifact_id):
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = os.path.join(_ARTIFACT_DIR, f"{artifact_id}.json")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Artifact not found")
    with open(path) as f:
        return json.load(f)


@router.get("/artifact/{artifact_id}")
def get_artifact(artifact_id: str):
    return _load_artifact(artifact_id)


# ------------------------------------------------------------------
# Deferred signup — email only, at completion
# ------------------------------------------------------------------

class ClaimRequest(BaseModel):
    artifact_id: str
    email: str


@router.post("/claim")
def claim_artifact(req: ClaimRequest):
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", req.email.strip()):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    artifact = _load_artifact(req.artifact_id)
    artifact["claimed_email"] = req.email.strip()
    with open(os.path.join(_ARTIFACT_DIR, f"{req.artifact_id}.json"), "w") as f:
        json.dump(artifact, f, indent=2)
    _append_signup({"email": req.email.strip(), "type": "claim", "artifact_id": req.artifact_id})
    log_event(artifact["session_id"], "artifact_claimed", {
        "module": "module01", "artifact_id": req.artifact_id,
    })
    return {"status": "ok"}


# ------------------------------------------------------------------
# Fake door — "Forage for Simulation" vision page + waitlist
# ------------------------------------------------------------------

class WaitlistRequest(BaseModel):
    email: str
    source: str = "forage"


@router.post("/waitlist")
def join_waitlist(req: WaitlistRequest):
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", req.email.strip()):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    _append_signup({"email": req.email.strip(), "type": "waitlist", "source": req.source})
    return {"status": "ok"}


@public_router.get("/forage", response_class=HTMLResponse)
def forage_page(request: Request):
    base = (os.environ.get("PUBLIC_BASE_URL") or str(request.base_url)).rstrip("/")
    module_url = os.environ.get("MODULE_URL", "https://airfoillearner.com/demo/")
    og_desc = (
        "Real, project-based simulation experience for engineers and students — "
        "no license seats, no HPC queue. Module 01 is live; more are coming."
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forage for Simulation — real simulation work, no license server</title>
<meta property="og:title" content="Forage for Simulation">
<meta property="og:description" content="{html.escape(og_desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{html.escape(base)}/forage">
<meta property="og:image" content="{html.escape(base)}/static/og-card.png">
<meta name="twitter:card" content="summary_large_image">
<style>
  body {{ margin:0; background:#0E1B2A; color:#E6F0F8;
         font-family:"Avenir Next","Segoe UI",system-ui,sans-serif; line-height:1.6; }}
  .page {{ max-width:680px; margin:0 auto; padding:64px 24px 80px; }}
  .kicker {{ font-family:Menlo,Consolas,monospace; font-size:11px; letter-spacing:0.14em;
             color:#4FA3E8; text-transform:uppercase; margin-bottom:14px; }}
  h1 {{ font-family:"DIN Alternate","Bahnschrift","Arial Narrow",sans-serif;
        font-size:clamp(30px,7vw,46px); text-transform:uppercase; line-height:1.05; margin:0 0 18px; }}
  h1 em {{ font-style:normal; color:#FF6B5E; }}
  .lede {{ font-size:17px; color:#AFC6D8; margin:0 0 36px; }}
  .mod {{ border:1px solid #24374B; background:#122234; padding:18px 20px; margin-bottom:14px;
          display:flex; justify-content:space-between; align-items:center; gap:14px; flex-wrap:wrap; }}
  .mod .t {{ font-weight:600; font-size:15px; }}
  .mod .s {{ font-family:Menlo,Consolas,monospace; font-size:10px; letter-spacing:0.1em; }}
  .live {{ color:#2E9E6B; }} .soon {{ color:#5E7C95; }}
  .cta {{ display:inline-block; background:#1272C4; color:#fff; text-decoration:none;
          font-family:Menlo,Consolas,monospace; font-size:12px; letter-spacing:0.1em;
          padding:10px 18px; }}
  .cta:hover {{ background:#1E86DE; }}
  form {{ margin-top:40px; border-top:1px solid #24374B; padding-top:28px; }}
  .fk {{ font-family:Menlo,Consolas,monospace; font-size:11px; letter-spacing:0.12em;
         color:#5E7C95; text-transform:uppercase; display:block; margin-bottom:10px; }}
  .row {{ display:flex; gap:10px; flex-wrap:wrap; }}
  input {{ flex:1; min-width:220px; background:#122234; border:1px solid #24374B; color:#E6F0F8;
           font-size:14px; padding:11px 14px; outline:none; }}
  input:focus {{ border-color:#1272C4; }}
  button {{ background:#E6F0F8; color:#0E1B2A; border:none; font-family:Menlo,Consolas,monospace;
            font-size:12px; letter-spacing:0.1em; padding:11px 20px; cursor:pointer; }}
  #msg {{ font-size:13px; margin-top:10px; min-height:20px; }}
  .foot {{ margin-top:56px; font-family:Menlo,Consolas,monospace; font-size:10px;
           color:#39506A; letter-spacing:0.1em; }}
</style>
</head>
<body>
<div class="page">
  <div class="kicker">Forage for Simulation</div>
  <h1>Real simulation work.<br>No license server. No queue. <em>No excuse.</em></h1>
  <p class="lede">Universities can't give every engineer real, hands-on simulation projects — license seats and compute are rationed. We can. Free, project-based modules on fast surrogate models: a real design brief, real targets, a design review, and a shareable report at the end.</p>

  <div class="mod">
    <div>
      <div class="t">Module 01 — UAV wing section under a design freeze</div>
      <div class="s live">LIVE · ~30 MINUTES · NO SIGNUP</div>
    </div>
    <a class="cta" href="{html.escape(module_url)}">START MODULE 01 →</a>
  </div>
  <div class="mod">
    <div>
      <div class="t">Module 02 — Parametric trade study: 50 variants, one recommendation</div>
      <div class="s soon">IN DESIGN</div>
    </div>
  </div>
  <div class="mod">
    <div>
      <div class="t">Module 03 — Thermal limits: the case your intuition gets wrong</div>
      <div class="s soon">PLANNED</div>
    </div>
  </div>

  <form onsubmit="return join(event)">
    <span class="fk">Get the next module when it ships</span>
    <div class="row">
      <input id="em" type="email" required placeholder="you@university.edu">
      <button type="submit">NOTIFY ME</button>
    </div>
    <div id="msg"></div>
  </form>

  <div class="foot">AIRFOILLEARNER · FORAGE FOR SIMULATION — REAL PROJECT WORK ON SURROGATE MODELS</div>
</div>
<script>
async function join(ev) {{
  ev.preventDefault();
  const msg = document.getElementById('msg');
  try {{
    const r = await fetch('/api/v1/module01/waitlist', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{email: document.getElementById('em').value, source: 'forage'}}),
    }});
    if (!r.ok) throw new Error((await r.json()).detail || 'try again');
    msg.textContent = "You're on the list — Module 02 lands in your inbox first.";
    msg.style.color = '#2E9E6B';
  }} catch (e) {{
    msg.textContent = e.message;
    msg.style.color = '#FF6B5E';
  }}
  return false;
}}
</script>
</body>
</html>"""
    return HTMLResponse(page)


# ------------------------------------------------------------------
# Public artifact page (no signup to view)
# ------------------------------------------------------------------

def _polar_svg(polar: list, y_key: str, label: str, color: str, design_alpha: float) -> str:
    pts = [(p["alpha"], p[y_key]) for p in polar if p.get(y_key) is not None]
    if not pts:
        return ""
    W, H, PL, PB, PT, PR = 300, 170, 40, 26, 10, 10
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1 = min(xs), max(xs)
    pad = (max(ys) - min(ys)) * 0.1 or 1
    y0, y1 = min(ys) - pad, max(ys) + pad
    sx = lambda a: PL + (a - x0) / (x1 - x0) * (W - PL - PR)
    sy = lambda v: PT + (1 - (v - y0) / (y1 - y0)) * (H - PT - PB)
    line = " ".join(f"{sx(a):.1f},{sy(v):.1f}" for a, v in pts)
    ticks = "".join(
        f'<line x1="{PL}" x2="{W-PR}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" stroke="#2A3B4D" stroke-width="0.5"/>'
        f'<text x="{PL-4}" y="{sy(v)+3:.1f}" text-anchor="end" font-size="8" fill="#5E7C95">{v:.2f}</text>'
        for v in (min(ys), (min(ys) + max(ys)) / 2, max(ys))
    )
    return f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">
{ticks}
<line x1="{sx(design_alpha):.1f}" x2="{sx(design_alpha):.1f}" y1="{PT}" y2="{H-PB}" stroke="#D8322A" stroke-width="1" stroke-dasharray="3,2"/>
<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.8"/>
<text x="{(W+PL)/2}" y="{H-6}" text-anchor="middle" font-size="9" fill="#5E7C95">alpha (deg)</text>
<text x="12" y="{H/2}" text-anchor="middle" font-size="9" fill="{color}" transform="rotate(-90,12,{H/2})">{label}</text>
</svg>'''


@public_router.get("/a/{artifact_id}", response_class=HTMLResponse)
def artifact_page(artifact_id: str, request: Request):
    a = _load_artifact(artifact_id)
    e = html.escape
    d, comp, sig = a["design"], a["compliance"], a["signals"]
    alpha = a["conditions"]["alpha"]
    base = (os.environ.get("PUBLIC_BASE_URL") or str(request.base_url)).rstrip("/")
    og_title = f"Wing-Section Design Report — NACA {d['airfoil']}"
    og_desc = (
        "A UAV wing section designed to real program targets on AirfoilLearner: "
        "requirements extraction, Reynolds-regime reasoning, trade-off analysis, results validation."
    )

    def check(ok):
        return ('<span style="color:#2E9E6B;font-weight:700">MEETS</span>' if ok
                else '<span style="color:#D8322A;font-weight:700">FAILS</span>')

    signals_rows = ""
    if sig.get("n_runs"):
        signals_rows += f"<li>{sig['n_runs']} simulation runs across {len(sig.get('airfoils_tested', []))} candidate sections</li>"
    if sig.get("estimate_CL") is not None and sig.get("first_run_CL") is not None:
        signals_rows += (f"<li>Pre-simulation estimate CL ≈ {sig['estimate_CL']} vs first computed "
                         f"CL = {sig['first_run_CL']:.3f}</li>")
    if sig.get("checkpoint_would_sign_off") is not None:
        verdict = "declined to sign off on" if not sig["checkpoint_would_sign_off"] else "signed off on"
        signals_rows += f"<li>Reviewed a flawed teammate result and {verdict} it, with written reasoning</li>"

    skills = "".join(f'<span class="chip">{e(s)}</span>' for s in a["skills"])

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(og_title)} · AirfoilLearner</title>
<meta property="og:title" content="{e(og_title)}">
<meta property="og:description" content="{e(og_desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{e(base)}/a/{e(a['id'])}">
<meta property="og:image" content="{e(base)}/static/og-card.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:site_name" content="AirfoilLearner — Forage for Simulation">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(og_title)}">
<meta name="twitter:description" content="{e(og_desc)}">
<meta name="twitter:image" content="{e(base)}/static/og-card.png">
<style>
  body {{ margin:0; background:#E9EEF3; color:#182838;
         font-family:"Avenir Next","Segoe UI",system-ui,sans-serif; line-height:1.55; }}
  .page {{ max-width:820px; margin:0 auto; padding:28px 20px 60px; }}
  .head {{ border:1.5px solid #182838; background:#F7FAFC; padding:16px 20px;
           display:flex; justify-content:space-between; align-items:flex-end; gap:12px; flex-wrap:wrap; }}
  .head .t {{ font-family:"DIN Alternate","Bahnschrift","Arial Narrow",sans-serif;
              font-size:26px; text-transform:uppercase; line-height:1.05; }}
  .head .t em {{ font-style:normal; color:#1272C4; }}
  .meta {{ font-family:Menlo,Consolas,monospace; font-size:10px; color:#5A6E80; text-align:right; line-height:1.7; }}
  h2 {{ font-family:"DIN Alternate","Bahnschrift","Arial Narrow",sans-serif; font-size:16px;
        text-transform:uppercase; border-bottom:1.5px solid #182838; padding-bottom:6px; margin:34px 0 14px; }}
  .card {{ background:#F7FAFC; border:1px solid #B9C6D2; padding:16px 18px; }}
  table {{ border-collapse:collapse; width:100%; font-size:14px; }}
  td, th {{ border:1px solid #B9C6D2; padding:7px 10px; text-align:left; }}
  th {{ font-family:Menlo,Consolas,monospace; font-size:10px; letter-spacing:0.08em;
        text-transform:uppercase; color:#5A6E80; background:#EDF3F8; }}
  .big {{ font-family:Menlo,Consolas,monospace; font-size:30px; font-weight:700; color:#1272C4; }}
  .charts {{ display:flex; gap:14px; flex-wrap:wrap; background:#0E1B2A; padding:14px; }}
  .q {{ font-family:Menlo,Consolas,monospace; font-size:10px; letter-spacing:0.08em;
        text-transform:uppercase; color:#D8322A; margin-bottom:4px; }}
  .chip {{ display:inline-block; font-family:Menlo,Consolas,monospace; font-size:11px;
           border:1px solid #1272C4; color:#1272C4; padding:3px 9px; margin:0 6px 6px 0; }}
  .foot {{ margin-top:44px; border-top:1.5px solid #182838; padding-top:10px;
           font-family:Menlo,Consolas,monospace; font-size:10px; color:#5A6E80;
           display:flex; justify-content:space-between; flex-wrap:wrap; gap:6px; }}
  ul {{ margin:8px 0 0; padding-left:20px; }}
</style>
</head>
<body>
<div class="page">
  <div class="head">
    <div class="t">Wing-Section<br>Design Report — <em>NACA {e(d['airfoil'])}</em></div>
    <div class="meta">FORAGE FOR SIMULATION · AIRFOILLEARNER<br>
      MODULE 01 · {e(a['module']['program'])}<br>
      REPORT {e(a['id'])} · {e(a['created_at'][:10])}</div>
  </div>

  <h2>The assignment</h2>
  <div class="card">{e(a['brief_summary'])}</div>

  <h2>Final design at the cruise point (α = {alpha}°, Re = {a['conditions']['reynolds']:,})</h2>
  <div class="card" style="display:flex; gap:34px; flex-wrap:wrap; align-items:center;">
    <div><div class="big">NACA {e(d['airfoil'])}</div></div>
    <div>CL <b>{d['CL']}</b></div>
    <div>CD <b>{d['CD']}</b></div>
    <div>L/D <b>{d['L_D']}</b></div>
  </div>
  <table style="margin-top:12px">
    <tr><th>Requirement</th><th>Target</th><th>Achieved</th><th>Margin</th><th>Status</th></tr>
    <tr><td>Cruise lift coefficient</td><td>CL ≥ {comp['CL']['target']}</td>
        <td>{comp['CL']['value']}</td><td>{comp['CL']['margin_pct']}%</td><td>{check(comp['CL']['meets'])}</td></tr>
    <tr><td>Profile drag budget</td><td>CD ≤ {comp['CD']['budget']}</td>
        <td>{comp['CD']['value']}</td><td>{comp['CD']['margin_pct']}%</td><td>{check(comp['CD']['meets'])}</td></tr>
  </table>

  <h2>Section polars (surrogate, Re = {a['conditions']['reynolds']:,})</h2>
  <div class="charts">
    {_polar_svg(a['polar'], 'CL', 'CL', '#4FA3E8', alpha)}
    {_polar_svg(a['polar'], 'L_D', 'L/D', '#2E9E6B', alpha)}
  </div>

  <h2>Engineering justification</h2>
  <div class="card"><div class="q">Why this section</div>{e(a['review']['justification'])}</div>
  <div class="card" style="margin-top:12px"><div class="q">Trade-off consciously accepted</div>{e(a['review']['tradeoff'])}</div>
  <div class="card" style="margin-top:12px"><div class="q">Would still validate before production</div>{e(a['review']['validate_next'])}</div>

  <h2>Skills demonstrated</h2>
  <div>{skills}</div>

  <h2>Process appendix</h2>
  <div class="card"><ul>{signals_rows or '<li>Session log unavailable</li>'}</ul></div>

  <div class="foot">
    <span>GENERATED BY AIRFOILLEARNER — REAL PROJECT WORK ON SURROGATE MODELS</span>
    <span><a href="{e(base)}/forage" style="color:#1272C4; text-decoration:none;">MORE MODULES COMING → FORAGE FOR SIMULATION</a></span>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(page)
