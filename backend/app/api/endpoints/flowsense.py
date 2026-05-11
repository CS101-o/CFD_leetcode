from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import os

router = APIRouter()


def load_problems():
    path = os.path.join(os.path.dirname(__file__), "../../data/problems.json")
    with open(path) as f:
        return json.load(f)["problems"]


class StartSessionRequest(BaseModel):
    problem_id: str


class FlowSenseMessageRequest(BaseModel):
    problem_id: str
    message: str
    conversation_history: list
    current_results: Optional[dict] = None


def _build_success_check(problem: dict) -> str:
    """Build an explicit, numeric success-check instruction from a problem's criteria."""
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


@router.post("/message")
async def flowsense_message(request: FlowSenseMessageRequest):
    from app.services.llm_service import LLMService
    from app.services.llm_tools import SYSTEM_PROMPT

    problems = load_problems()
    problem = next((p for p in problems if p["id"] == request.problem_id), None)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # --- ACTION STEP SYSTEM PROMPT ---
    # Keep the original strict JSON-only format from SYSTEM_PROMPT so the 7B
    # model reliably outputs a tool call. Append only the problem facts
    # (no phase prose) so the model knows what conditions to test.
    action_system = SYSTEM_PROMPT + f"""

## ACTIVE BOTTLENECK CONTEXT
Problem: {problem['title']}
Starting airfoil: {problem['starting_airfoil'].replace('naca', 'NACA ')}
Operating conditions: Re={problem['Re']}, Mach={problem['mach']}
Success criteria: {json.dumps(problem['success_criteria'])}

When the user asks to diagnose, run a polar sweep on the starting airfoil at the
operating Reynolds number to establish the baseline. Always use the exact Re and
Mach from the context above unless the user specifies otherwise.

If the conversation history shows that FlowSense previously suggested a tool call
(modify_geometry, compare_airfoils, run_simulation, run_polar_sweep, etc.) but it
was not executed, execute that tool now when the user asks for the next step or
asks what to try next.

If the user asks "what did we learn" or "what should we try next", run the
previously suggested tool rather than repeating the same synthesis."""

    # --- SUMMARY STEP INSTRUCTION ---
    # This is injected ONLY into the summary step (step 3), where prose is wanted.
    # The model has already executed the tool; now synthesise like FlowSense.
    synthesis_instruction = f"""You are FlowSense, an aerodynamic experimentation intelligence.

The engineer is solving this bottleneck:
PROBLEM: {problem['title']}
BOTTLENECK: {problem['bottleneck']}
SUCCESS CRITERIA: {json.dumps(problem['success_criteria'])}

Now that the simulation results are in, provide a FlowSense synthesis:

DIAGNOSIS — What do the numbers reveal about the physical root cause?
EXPERIMENT INSIGHT — What did this run confirm or rule out?
TOP FINDINGS — List the 2–3 most important numbers and what they mean physically.
NEXT EXPERIMENT — Propose the exact next experiment in plain words (specific NACA code, Re, alpha range). Example: "Next, run a polar sweep on NACA 6412 from -2 to 18 degrees at Re=1,500,000."

SUCCESS CHECK — You must now evaluate whether the bottleneck is solved. Look at the simulation results and check each criterion numerically:
{_build_success_check(problem)}
If ALL criteria above are met: respond with "🎯 BOTTLENECK SOLVED" followed by the airfoil name and the exact achieved values for every criterion.
If any criterion is unmet: state which one failed, by how much (e.g. "L/D = 74, need 90 — gap of 16"), and do not claim the bottleneck is solved.
Do not output template text. Actually do the comparison with the numbers in front of you and state the result explicitly.
Do not suggest further experiments if the bottleneck is solved.

CRITICAL: Your response must be plain text only. Do not include JSON blocks, code fences, or tool call syntax. If you want to suggest a next experiment, describe it in words — never as a JSON block."""

    llm = LLMService()
    llm.system_prompt = action_system

    response = await llm.chat(
        message=request.message,
        conversation_history=request.conversation_history,
        current_results=request.current_results,
        summary_instruction=synthesis_instruction,
    )

    return response
