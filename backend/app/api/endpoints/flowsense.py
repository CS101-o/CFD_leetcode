from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional
import json
import os
import time
from collections import defaultdict, deque

from app.services.session_logger import log_event, get_all_sessions, get_session

router = APIRouter()

_OBSERVE_KEY = os.environ.get("OBSERVE_KEY", "observe2026")

# ------------------------------------------------------------------
# Rate limiting for the LLM endpoint (Gemini spend protection).
# In-memory sliding windows — resets on redeploy, which is fine: this is a
# bot/abuse guard, not accounting.
# ------------------------------------------------------------------
_RATE_PER_MIN_IP = int(os.environ.get("CHAT_RATE_PER_MIN_IP", "8"))
_RATE_PER_DAY_GLOBAL = int(os.environ.get("CHAT_RATE_PER_DAY_GLOBAL", "1000"))
_ip_hits = defaultdict(deque)
_global_hits = deque()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate(request: Request) -> None:
    now = time.time()
    ip = _client_ip(request)
    hits = _ip_hits[ip]
    while hits and now - hits[0] > 60:
        hits.popleft()
    if len(hits) >= _RATE_PER_MIN_IP:
        raise HTTPException(status_code=429, detail="Too many messages — wait a minute and try again.")
    while _global_hits and now - _global_hits[0] > 86400:
        _global_hits.popleft()
    if len(_global_hits) >= _RATE_PER_DAY_GLOBAL:
        raise HTTPException(status_code=429, detail="The assistant is at capacity for today — simulations still work.")
    hits.append(now)
    _global_hits.append(now)


def load_problems():
    path = os.path.join(os.path.dirname(__file__), "../../data/problems.json")
    with open(path) as f:
        return json.load(f)["problems"]


class StartSessionRequest(BaseModel):
    problem_id: str
    session_id: str
    participant_id: str


class FlowSenseMessageRequest(BaseModel):
    problem_id: str
    message: str
    conversation_history: list
    current_results: Optional[dict] = None
    session_id: Optional[str] = None
    participant_id: Optional[str] = None


def _build_success_check(problem: dict) -> str:
    criteria = problem["success_criteria"]
    alpha = problem.get("design_alpha", "cruise")
    lines = []
    if "target_LD" in criteria:
        lines.append(f"- Is the latest L/D >= {criteria['target_LD']}?")
    if "cruise_CL_min" in criteria:
        lines.append(f"- Is the latest CL >= {criteria['cruise_CL_min']} at α = {alpha}°?")
    if "stall_angle_improvement" in criteria:
        lines.append(
            f"- Has the stall angle improved by at least {criteria['stall_angle_improvement']}° "
            f"compared to the baseline, while cruise CL stays >= {criteria.get('cruise_CL_min', 'N/A')}?"
        )
    lines.append("- If ALL of the above are true: the bottleneck is solved.")
    lines.append("- If any are false: state which criterion failed and by exactly how much.")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Problem endpoints
# ------------------------------------------------------------------

@router.get("/problems")
def get_problems():
    return {"problems": load_problems()}


@router.get("/problems/{problem_id}")
def get_problem(problem_id: str):
    problems = load_problems()
    problem = next((p for p in problems if p["id"] == problem_id), None)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


# ------------------------------------------------------------------
# Session lifecycle
# ------------------------------------------------------------------

@router.post("/session/start")
def start_session(req: StartSessionRequest, request: Request):
    problems = load_problems()
    problem = next((p for p in problems if p["id"] == req.problem_id), None)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    log_event(req.session_id, "session_start", {
        "participant_id": req.participant_id,
        "problem_id": req.problem_id,
        "problem_title": problem["title"],
        "difficulty": problem["difficulty"],
        "ip": ip,
    })
    return {"status": "ok"}


# ------------------------------------------------------------------
# Chat / simulation
# ------------------------------------------------------------------

@router.post("/message")
async def flowsense_message(request: FlowSenseMessageRequest, http_request: Request):
    _check_rate(http_request)
    from app.services.llm_service import LLMService

    problems = load_problems()
    problem = next((p for p in problems if p["id"] == request.problem_id), None)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    sid = request.session_id or "unknown"
    pid = request.participant_id or "unknown"

    log_event(sid, "message_sent", {
        "participant_id": pid,
        "problem_id": request.problem_id,
        "message": request.message,
        "history_length": len(request.conversation_history),
    })

    starting = problem['starting_airfoil'].replace('naca', '')
    questions = problem.get('interview_questions', [])
    questions_block = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    action_system = f"""You are AirfoilLearner, a research interviewer studying how engineers use aerodynamic surrogate models.

PROBLEM: {problem['title']}
Starting airfoil: NACA {starting}
Operating conditions: Re={problem['Re']}, Mach={problem['mach']}
Success criteria: {json.dumps(problem['success_criteria'])}

INTERVIEW QUESTIONS (work through these in order):
{questions_block}

YOUR ROLE:
- You are an interviewer, not a teacher. Your job is to understand how the engineer thinks.
- Start immediately with question 1. Do not explain the problem first.
- Ask one interview question at a time. Wait for a substantive response before moving to the next.
- A response is substantive when the engineer has run a simulation or MC that addresses the question, or has given a reasoned answer.
- Do NOT advance to the next question if the engineer has only said something vague or confirmatory.

RULES:
1. Only call a simulation tool when the user message contains an explicit 4-digit NACA code (e.g. "run 4412", "sweep NACA 5409"). If no 4-digit code is present, do NOT call any tool.
2. If the user wants to run something but has not named a specific 4-digit airfoil, respond only with: "Which airfoil would you like to test?" Do not suggest one.
3. For a baseline: run_polar_sweep on NACA {starting}, Re={problem['Re']}, Mach={problem['mach']}, alpha -5 to 15.
4. Always use Re={problem['Re']} and Mach={problem['mach']} unless the user explicitly overrides.
5. Never fabricate CL, CD, or L/D numbers. All data comes from tool results only.
6. Keep all free-text responses to 2–3 sentences maximum. No headers, no bullet points.
7. If the user explicitly names a NACA code in their message (e.g. "run NACA 4412"), always run it — even if it appears in conversation history. Only skip a simulation if the user has NOT named the airfoil and the results are already in history.
8. Never call modify_geometry or generate_airfoil unless the user explicitly asks for geometry modification or coordinate generation."""

    synthesis_instruction = f"""You are AirfoilLearner, a research interviewer studying engineering problem-solving.

PROBLEM: {problem['title']}
SUCCESS CRITERIA: {json.dumps(problem['success_criteria'])}

INTERVIEW QUESTIONS (in order):
{questions_block}

A simulation just ran. Use ONLY these sections:

RESULTS — Key numbers only. For a polar sweep: cruise point (α={problem.get('design_alpha', 4)}°) CL and L/D, plus peak L/D. For single-point: CL, CD, L/D. For Monte Carlo: P50 CL and L/D with P10–P90 range. Maximum 3 lines. No interpretation.
  Exception: if Monte Carlo, add CANDIDATE EXPERIMENTS listing the top 3–5 high-value experiments (airfoil, predicted L/D, predicted CL) and ask: "Which of these would you like to investigate?"

NEXT QUESTION — Look at the conversation history and identify which interview question has not yet received a substantive answer. Ask that question now, in one sentence. Do not repeat a question already answered. If all questions are answered and the bottleneck is solved, ask: "Now that you've solved it, what was the key insight that got you there?"

SUCCESS CHECK — Check each criterion numerically:
{_build_success_check(problem)}
If ALL criteria are met: write "✓ BOTTLENECK SOLVED — [airfoil] achieves L/D=[X] and CL=[Y] at α={problem.get('design_alpha', 4)}°."
If any fail: write "✗ Not solved — [which criterion], gap of [amount]."

Plain text only. No JSON, no code fences."""

    llm = LLMService()
    llm.system_prompt = action_system

    response = await llm.chat(
        message=request.message,
        conversation_history=request.conversation_history,
        summary_instruction=synthesis_instruction,
    )

    if response.get("simulation_triggered") and response.get("simulation_results"):
        sim = response["simulation_results"]
        log_event(sid, "simulation_run", {
            "participant_id": pid,
            "problem_id": request.problem_id,
            "tools_called": response.get("tools_called", []),
            "results_summary": {
                k: v for k, v in (sim or {}).items()
                if k not in ("coordinates", "polar_data")
            },
        })

    log_event(sid, "response_sent", {
        "participant_id": pid,
        "problem_id": request.problem_id,
        "simulation_triggered": response.get("simulation_triggered", False),
        "tools_called": response.get("tools_called", []),
    })

    return response


# ------------------------------------------------------------------
# Observation endpoints (wizard-only, key-gated)
# ------------------------------------------------------------------

@router.get("/observe/sessions")
def observe_sessions(key: str = Query("")):
    if key != _OBSERVE_KEY:
        raise HTTPException(status_code=403, detail="Invalid key")
    sessions = get_all_sessions()
    summary = []
    for s in sessions:
        events = s["events"]
        start = next((e for e in events if e["event"] == "session_start"), {})
        summary.append({
            "session_id": s["session_id"],
            "participant_id": start.get("participant_id", "?"),
            "problem_title": start.get("problem_title", "?"),
            "event_count": len(events),
            "started_at": events[0]["timestamp"] if events else None,
            "last_event_at": events[-1]["timestamp"] if events else None,
        })
    return {"sessions": summary}


@router.get("/observe/session/{session_id}")
def observe_session(session_id: str, key: str = Query("")):
    if key != _OBSERVE_KEY:
        raise HTTPException(status_code=403, detail="Invalid key")
    return {"events": get_session(session_id)}
