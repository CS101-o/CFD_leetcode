"""
AI Chat - LLM-powered with Ollama (Qwen2.5) function calling
Preserves challenge system from template-based version.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict

from app.services.llm_service import get_llm_service

router = APIRouter()

# In-memory challenge state (per session)
active_challenges = {}

# Challenge definitions
CHALLENGES = {
    "easy": {
        "id": "easy",
        "title": "First Flight",
        "description": "Design an airfoil that generates CL ≥ 0.5 at 5° angle of attack.",
        "constraints": {
            "alpha": 5.0,
            "target_cl_min": 0.5
        },
        "hints": [
            "Symmetric airfoils have zero lift at 0°",
            "Add camber (first digit) for more lift",
            "Try NACA 2412 or NACA 4412"
        ]
    },
    "medium": {
        "id": "medium",
        "title": "High Lift Challenge",
        "description": "Design an airfoil with CL > 1.2 AND CD < 0.02 at 10°.",
        "constraints": {
            "alpha": 10.0,
            "target_cl_min": 1.2,
            "target_cd_max": 0.02
        },
        "hints": [
            "High camber = more lift but also more drag",
            "Try NACA 4412 or NACA 6412",
            "Balance is key!"
        ]
    },
    "hard": {
        "id": "hard",
        "title": "Perfect Balance",
        "description": "Achieve CL > 1.0, CD < 0.01, and L/D > 100 at any angle (5-10°).",
        "constraints": {
            "alpha_min": 5.0,
            "alpha_max": 10.0,
            "target_cl_min": 1.0,
            "target_cd_max": 0.01,
            "target_ld_min": 100
        },
        "hints": [
            "Find both the right airfoil AND angle",
            "Moderate camber (2-4%) often works best",
            "Test multiple angles"
        ]
    }
}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    current_results: Optional[Dict] = None
    conversation_history: List[ChatMessage] = []
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    extracted_params: Optional[Dict] = None
    simulation_triggered: bool = False
    simulation_results: Optional[Dict] = None
    challenge_active: bool = False
    challenge_passed: bool = False


def check_challenge_requirements(challenge: Dict, simulation_results: Dict, alpha: float) -> tuple[bool, str]:
    """Check if simulation meets challenge requirements"""
    constraints = challenge["constraints"]
    feedback_parts = []
    success = True

    # Check angle requirement
    if "alpha" in constraints:
        if abs(alpha - constraints["alpha"]) > 0.1:
            return False, f"❌ You must test at exactly {constraints['alpha']}° (you tested at {alpha}°)"

    if "alpha_min" in constraints and "alpha_max" in constraints:
        if alpha < constraints["alpha_min"] or alpha > constraints["alpha_max"]:
            return False, f"❌ Angle must be between {constraints['alpha_min']}-{constraints['alpha_max']}° (you used {alpha}°)"

    # Check CL
    if "target_cl_min" in constraints:
        if simulation_results['CL'] < constraints["target_cl_min"]:
            success = False
            feedback_parts.append(f"❌ CL too low: {simulation_results['CL']:.4f} < {constraints['target_cl_min']:.4f}")
        else:
            feedback_parts.append(f"✅ CL requirement met: {simulation_results['CL']:.4f} ≥ {constraints['target_cl_min']:.4f}")

    # Check CD
    if "target_cd_max" in constraints:
        if simulation_results['CD'] > constraints["target_cd_max"]:
            success = False
            feedback_parts.append(f"❌ CD too high: {simulation_results['CD']:.6f} > {constraints['target_cd_max']:.6f}")
        else:
            feedback_parts.append(f"✅ CD requirement met: {simulation_results['CD']:.6f} ≤ {constraints['target_cd_max']:.6f}")

    # Check L/D
    if "target_ld_min" in constraints:
        if simulation_results['L_D'] < constraints["target_ld_min"]:
            success = False
            feedback_parts.append(f"❌ L/D too low: {simulation_results['L_D']:.1f} < {constraints['target_ld_min']:.1f}")
        else:
            feedback_parts.append(f"✅ L/D requirement met: {simulation_results['L_D']:.1f} ≥ {constraints['target_ld_min']:.1f}")

    feedback = "\n".join(feedback_parts)
    return success, feedback


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """Send a message to the LLM-powered chatbot"""
    try:
        session_id = request.session_id
        message_lower = request.message.lower()

        # Check if user is starting a challenge
        if 'challenge' in message_lower:
            if 'easy' in message_lower or 'beginner' in message_lower:
                active_challenges[session_id] = CHALLENGES['easy']
            elif 'medium' in message_lower or 'intermediate' in message_lower:
                active_challenges[session_id] = CHALLENGES['medium']
            elif 'hard' in message_lower or 'difficult' in message_lower:
                active_challenges[session_id] = CHALLENGES['hard']

        # Get active challenge
        active_challenge = active_challenges.get(session_id)

        # Build challenge context if challenge is active
        challenge_context = None
        if active_challenge:
            constraints = active_challenge['constraints']
            req_text = []
            if 'alpha' in constraints:
                req_text.append(f"Must test at exactly {constraints['alpha']}°")
            if 'alpha_min' in constraints and 'alpha_max' in constraints:
                req_text.append(f"Must test between {constraints['alpha_min']}-{constraints['alpha_max']}°")
            if 'target_cl_min' in constraints:
                req_text.append(f"CL must be > {constraints['target_cl_min']}")
            if 'target_cd_max' in constraints:
                req_text.append(f"CD must be < {constraints['target_cd_max']}")
            if 'target_ld_min' in constraints:
                req_text.append(f"L/D must be > {constraints['target_ld_min']}")

            challenge_context = f"""ACTIVE CHALLENGE: {active_challenge['title']}
{active_challenge['description']}
Requirements: {', '.join(req_text)}"""

        # Get LLM service and process message
        llm = get_llm_service()

        # Convert conversation history to dict format
        history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]

        # Call LLM
        result = await llm.chat(
            message=request.message,
            conversation_history=history,
            challenge_context=challenge_context
        )

        # Check for LLM connection issues
        if result.get("error") == "llm_connection_failed":
            return ChatResponse(
                response=result["response"],
                simulation_triggered=False,
                challenge_active=active_challenge is not None,
                challenge_passed=False
            )

        # Process challenge requirements if simulation was run
        challenge_passed = False
        challenge_feedback = None
        simulation_triggered = False
        simulation_results = None

        if "run_simulation" in result.get("tools_called", []) and active_challenge:
            simulation_results = result.get("simulation_results")
            if simulation_results and "results" in simulation_results:
                # Extract the actual results
                sim_res = simulation_results["results"]
                alpha = simulation_results["conditions"]["alpha"]

                challenge_passed, challenge_feedback = check_challenge_requirements(
                    active_challenge,
                    sim_res,
                    alpha
                )

                # Append challenge feedback to response
                if challenge_feedback:
                    if challenge_passed:
                        result["response"] += f"\n\n🎉 **Challenge Complete!** 🎉\n{challenge_feedback}"
                        # Clear challenge on success
                        del active_challenges[session_id]
                    else:
                        result["response"] += f"\n\n🎯 **Challenge Progress:**\n{challenge_feedback}"

                simulation_triggered = True
        elif result.get("simulation_results"):
            simulation_triggered = True
            simulation_results = result.get("simulation_results")

        return ChatResponse(
            response=result["response"],
            simulation_triggered=simulation_triggered,
            simulation_results=simulation_results,
            challenge_active=active_challenge is not None,
            challenge_passed=challenge_passed
        )

    except Exception as e:
        raise HTTPException(500, f"Chat processing failed: {str(e)}")


@router.get("/health")
async def chat_health():
    """Check if the LLM backend is available."""
    llm = get_llm_service()
    is_healthy = await llm.health_check()
    return {
        "status": "healthy" if is_healthy else "degraded",
        "llm_available": is_healthy,
        "model": llm.model,
        "message": "Ollama + Qwen2.5 ready" if is_healthy else "Ollama not running. Run: ollama serve"
    }


@router.get("/guidance")
async def get_parameter_guidance():
    """Get parameter guidance"""
    return {
        "message": "CFD LeetCode - AI-Powered Platform",
        "challenges": ["easy", "medium", "hard"],
        "commands": [
            "easy challenge",
            "simulate NACA 2412 at 5 degrees",
            "compare 2412 vs 4412 vs 0012",
            "help",
            "what is lift?"
        ]
    }
