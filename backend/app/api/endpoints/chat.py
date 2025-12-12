"""
FREE AI Chat - Template-based responses with Challenge Support
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import re
import json

from app.utils.neuralfoil_wrapper import (
    get_predictor,
    create_naca_airfoil,
    get_preset_coordinates,
    PRESETS
)

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
    session_id: str = "default"  # Add session ID


class ChatResponse(BaseModel):
    response: str
    extracted_params: Optional[Dict] = None
    simulation_triggered: bool = False
    simulation_results: Optional[Dict] = None
    challenge_active: bool = False
    challenge_passed: bool = False


def extract_airfoil_params(text: str) -> Optional[Dict]:
    """Extract airfoil parameters from natural language text"""
    params = {}
    text_lower = text.lower()

    # NACA pattern
    naca_match = re.search(r'naca\s*(\d{4})', text_lower)
    if naca_match:
        params['airfoil_type'] = 'naca'
        params['naca_designation'] = naca_match.group(1)

    # Preset pattern
    for preset in PRESETS.keys():
        if preset in text_lower:
            params['airfoil_type'] = 'preset'
            params['preset_name'] = preset
            break

    # Angle of attack
    alpha_patterns = [
        r'(?:alpha|angle\s*of\s*attack|aoa)\s*[:]?\s*(-?\d+\.?\d*)',
        r'(\d+\.?\d*)\s*degrees?',
        r'at\s*(-?\d+\.?\d*)\s*°'
    ]
    for pattern in alpha_patterns:
        alpha_match = re.search(pattern, text_lower)
        if alpha_match:
            params['alpha'] = float(alpha_match.group(1))
            break

    # Reynolds number
    reynolds_patterns = [
        r'reynolds\s*(?:number)?\s*[:]?\s*(\d+\.?\d*)\s*(?:million|m)?',
        r're\s*[=:]?\s*(\d+\.?\d*)\s*(?:million|m)?',
    ]
    for pattern in reynolds_patterns:
        re_match = re.search(pattern, text_lower)
        if re_match:
            value = float(re_match.group(1))
            if 'million' in text_lower or 'm' in text_lower:
                value *= 1e6
            params['reynolds'] = value
            break

    return params if params else None


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


def generate_response(message: str, params: Optional[Dict], simulation_results: Optional[Dict], 
                     active_challenge: Optional[Dict], challenge_feedback: Optional[str]) -> str:
    """Generate template-based response"""
    message_lower = message.lower()
    
    # Challenge passed!
    if challenge_feedback and "✅" in challenge_feedback and active_challenge:
        return f"""🎉 **Challenge Complete!** 🎉

{challenge_feedback}

You solved: **{active_challenge['title']}**

Want another challenge? Say "easy challenge", "medium challenge", or "hard challenge"!"""
    
    # Challenge failed but with feedback
    if challenge_feedback and active_challenge:
        cl = simulation_results['CL']
        cd = simulation_results['CD']
        ld = simulation_results['L_D']
        time_ms = simulation_results['time_ms']
        
        return f"""Simulation complete! ⚡ ({time_ms:.1f}ms)

📊 Results:
- CL: {cl:.4f}
- CD: {cd:.6f}
- L/D: {ld:.1f}

🎯 **Challenge Progress:**
{challenge_feedback}

💡 **Hints:**
{chr(10).join('• ' + hint for hint in active_challenge['hints'])}

Keep trying! Adjust your airfoil or angle."""
    
    # Challenge requested
    if 'challenge' in message_lower:
        if 'easy' in message_lower or 'beginner' in message_lower:
            challenge = CHALLENGES['easy']
            return f"""🎯 **{challenge['title']}**

{challenge['description']}

**Requirements:**
- Must test at {challenge['constraints']['alpha']}°
- CL ≥ {challenge['constraints']['target_cl_min']}

**Hints:**
{chr(10).join('• ' + hint for hint in challenge['hints'])}

Try: "simulate NACA 2412 at 5 degrees"

Challenge activated! Good luck! 🚀"""
        
        elif 'medium' in message_lower or 'intermediate' in message_lower:
            challenge = CHALLENGES['medium']
            return f"""🎯 **{challenge['title']}**

{challenge['description']}

**Requirements:**
- Must test at {challenge['constraints']['alpha']}°
- CL > {challenge['constraints']['target_cl_min']}
- CD < {challenge['constraints']['target_cd_max']}

**Hints:**
{chr(10).join('• ' + hint for hint in challenge['hints'])}

Try: "simulate NACA 4412 at 10 degrees"

Challenge activated! Good luck! 🚀"""
        
        elif 'hard' in message_lower or 'difficult' in message_lower:
            challenge = CHALLENGES['hard']
            return f"""🎯 **{challenge['title']}**

{challenge['description']}

**Requirements:**
- Test between {challenge['constraints']['alpha_min']}-{challenge['constraints']['alpha_max']}°
- CL > {challenge['constraints']['target_cl_min']}
- CD < {challenge['constraints']['target_cd_max']}
- L/D > {challenge['constraints']['target_ld_min']}

**Hints:**
{chr(10).join('• ' + hint for hint in challenge['hints'])}

This is the toughest one! Good luck! 🚀"""
        
        else:
            return """🎯 **Available Challenges:**

🟢 **Easy: First Flight**
   Design CL ≥ 0.5 at 5°

🟡 **Medium: High Lift**  
   CL > 1.2, CD < 0.02 at 10°

🔴 **Hard: Perfect Balance**
   CL > 1.0, CD < 0.01, L/D > 100

Say "easy challenge", "medium challenge", or "hard challenge"!"""
    
    # Greetings
    if any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I'm your FREE CFD tutor. Try:\n• 'easy challenge' for a fun problem\n• 'simulate NACA 2412 at 8 degrees' to test airfoils"
    
    # Help
    if any(word in message_lower for word in ['help', 'how', 'what can']):
        return """I can help you run CFD simulations!

🎯 **Challenges:** Say "easy challenge" for guided problems
🔹 **Quick sim:** "simulate NACA 2412 at 8 degrees"
💡 **Learn:** Ask "what is lift?" or "what is drag?"

Let's get started!"""
    
    # Regular simulation results (no active challenge)
    if simulation_results and not active_challenge:
        cl = simulation_results['CL']
        cd = simulation_results['CD']
        ld = simulation_results['L_D']
        time_ms = simulation_results['time_ms']
        
        interpretation = ""
        if ld > 100:
            interpretation = "Excellent efficiency! 🚀"
        elif ld > 50:
            interpretation = "Good performance! ✈️"
        elif ld > 25:
            interpretation = "Decent results. 👍"
        else:
            interpretation = "Low efficiency - try lower angles. 💡"
        
        return f"""Simulation complete! ⚡ ({time_ms:.1f}ms)

📊 Results:
- CL (Lift): {cl:.4f}
- CD (Drag): {cd:.6f}
- L/D Ratio: {ld:.1f}

{interpretation}

Want a challenge? Say "easy challenge"!"""
    
    # Concept explanations
    if 'what is' in message_lower or 'explain' in message_lower:
        if 'lift' in message_lower or 'cl' in message_lower:
            return "**Lift Coefficient (CL)**: Measures how much lift an airfoil generates. Higher CL = more lift. Typical range: 0.2 to 1.5."
        elif 'drag' in message_lower or 'cd' in message_lower:
            return "**Drag Coefficient (CD)**: Measures resistance. Lower CD = more efficient. Good airfoils have CD < 0.01."
        elif 'l/d' in message_lower:
            return "**L/D Ratio**: Lift ÷ Drag. Higher is better! Good: L/D > 50. Excellent: L/D > 100."
    
    # Default
    if params:
        naca = params.get('naca_designation', 'unknown')
        alpha = params.get('alpha', 'unknown')
        return f"Running simulation for NACA {naca} at {alpha}°..."
    
    return "Try:\n• 'easy challenge' for a guided problem\n• 'simulate NACA 2412 at 5 degrees'\n• 'help'"


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """Send a message to the FREE chatbot"""
    try:
        session_id = request.session_id
        
        # Check if user is starting a challenge
        message_lower = request.message.lower()
        if 'challenge' in message_lower:
            if 'easy' in message_lower or 'beginner' in message_lower:
                active_challenges[session_id] = CHALLENGES['easy']
            elif 'medium' in message_lower or 'intermediate' in message_lower:
                active_challenges[session_id] = CHALLENGES['medium']
            elif 'hard' in message_lower or 'difficult' in message_lower:
                active_challenges[session_id] = CHALLENGES['hard']
        
        # Get active challenge
        active_challenge = active_challenges.get(session_id)
        
        # Extract parameters
        extracted_params = extract_airfoil_params(request.message)
        
        # Check if we should trigger simulation
        trigger_words = ['run', 'simulate', 'test', 'analyze', 'try']
        should_simulate = any(word in message_lower for word in trigger_words)
        
        simulation_results = None
        simulation_triggered = False
        challenge_feedback = None
        challenge_passed = False
        
        if should_simulate and extracted_params and extracted_params.get('airfoil_type'):
            try:
                # Fill in defaults
                if 'alpha' not in extracted_params:
                    extracted_params['alpha'] = 5.0
                if 'reynolds' not in extracted_params:
                    extracted_params['reynolds'] = 1000000
                
                # Get coordinates
                if extracted_params['airfoil_type'] == 'naca':
                    coords = create_naca_airfoil(extracted_params['naca_designation'])
                elif extracted_params['airfoil_type'] == 'preset':
                    coords = get_preset_coordinates(extracted_params['preset_name'])
                else:
                    coords = create_naca_airfoil("0012")
                
                # Run simulation
                predictor = get_predictor()
                result = predictor.predict(
                    coordinates=coords,
                    alpha=extracted_params['alpha'],
                    reynolds=extracted_params['reynolds']
                )
                
                result['coordinates'] = coords.tolist()
                simulation_results = result
                simulation_triggered = True
                
                # Check challenge if active
                if active_challenge:
                    challenge_passed, challenge_feedback = check_challenge_requirements(
                        active_challenge, 
                        result, 
                        extracted_params['alpha']
                    )
                    
                    if challenge_passed:
                        # Clear challenge on success
                        del active_challenges[session_id]
                
            except Exception as sim_error:
                return ChatResponse(
                    response=f"Simulation error: {str(sim_error)}",
                    extracted_params=extracted_params,
                    simulation_triggered=False,
                    simulation_results=None,
                    challenge_active=active_challenge is not None,
                    challenge_passed=False
                )
        
        # Generate response
        ai_response = generate_response(
            request.message, 
            extracted_params, 
            simulation_results,
            active_challenge,
            challenge_feedback
        )
        
        return ChatResponse(
            response=ai_response,
            extracted_params=extracted_params,
            simulation_triggered=simulation_triggered,
            simulation_results=simulation_results,
            challenge_active=active_challenge is not None,
            challenge_passed=challenge_passed
        )
        
    except Exception as e:
        raise HTTPException(500, f"Chat processing failed: {str(e)}")


@router.get("/guidance")
async def get_parameter_guidance():
    """Get parameter guidance"""
    return {
        "message": "CFD LeetCode - FREE Platform",
        "challenges": ["easy", "medium", "hard"],
        "commands": [
            "easy challenge",
            "simulate NACA 2412 at 5 degrees",
            "help",
            "what is lift?"
        ]
    }