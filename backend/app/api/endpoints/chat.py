"""
FREE AI Chat - Template-based responses (No API costs!)
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


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    current_results: Optional[Dict] = None
    conversation_history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    response: str
    extracted_params: Optional[Dict] = None
    simulation_triggered: bool = False
    simulation_results: Optional[Dict] = None


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


def generate_response(message: str, params: Optional[Dict], simulation_results: Optional[Dict]) -> str:
    """Generate template-based response"""
    message_lower = message.lower()
    
    # Greetings
    if any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I'm your FREE CFD tutor. Try commands like:\n• 'simulate NACA 2412 at 8 degrees'\n• 'run NACA 0012 at 5 degrees'\n• 'test NACA 4412 at 10 degrees'"
    
    # Help requests
    if any(word in message_lower for word in ['help', 'how', 'what can']):
        return """I can help you run CFD simulations! Here's how:

🔹 Basic format: "simulate NACA [4-digit code] at [angle] degrees"
🔹 Examples:
   • "simulate NACA 2412 at 8 degrees"
   • "run NACA 0012 at 5 degrees"
   • "test NACA 4412 at 10 degrees Re 2000000"

📊 I'll give you CL, CD, and L/D ratio in milliseconds!"""
    
    # Simulation results
    if simulation_results:
        cl = simulation_results['CL']
        cd = simulation_results['CD']
        ld = simulation_results['L_D']
        time_ms = simulation_results['time_ms']
        
        # Interpret results
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

Try another angle or airfoil!"""
    
    # Concept explanations
    if 'what is' in message_lower or 'explain' in message_lower:
        if 'lift' in message_lower or 'cl' in message_lower:
            return "**Lift Coefficient (CL)**: Measures how much lift an airfoil generates. Higher CL = more lift. Typical range: 0.2 to 1.5."
        elif 'drag' in message_lower or 'cd' in message_lower:
            return "**Drag Coefficient (CD)**: Measures resistance to motion. Lower CD = more efficient. Good airfoils have CD < 0.01."
        elif 'l/d' in message_lower or 'efficiency' in message_lower:
            return "**L/D Ratio**: Lift divided by Drag. Higher is better! Good airfoils: L/D > 50. Excellent: L/D > 100."
        elif 'reynolds' in message_lower:
            return "**Reynolds Number**: Ratio of inertial to viscous forces. Typical: 1 million (1e6). Higher Re = thinner boundary layer."
        elif 'alpha' in message_lower or 'angle of attack' in message_lower:
            return "**Angle of Attack (α)**: Angle between airfoil and incoming air. Typical: 0-15°. Too high causes stall!"
    
    # Default - encourage simulation
    if params:
        naca = params.get('naca_designation', 'unknown')
        alpha = params.get('alpha', 'unknown')
        return f"I found: NACA {naca} at {alpha}°\n\nI'll run the simulation now!"
    
    return "I didn't quite understand. Try:\n• 'simulate NACA 2412 at 8 degrees'\n• 'help'\n• 'what is lift?'"


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """Send a message to the FREE chatbot"""
    try:
        # Extract parameters
        extracted_params = extract_airfoil_params(request.message)
        
        # Check if we should trigger simulation
        trigger_words = ['run', 'simulate', 'test', 'analyze', 'try']
        should_simulate = any(word in request.message.lower() for word in trigger_words)
        
        simulation_results = None
        simulation_triggered = False
        
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
                
                # ADD COORDINATES TO RESULT
                result['coordinates'] = coords.tolist()
                
                simulation_results = result
                simulation_triggered = True
                
            except Exception as sim_error:
                return ChatResponse(
                    response=f"Simulation error: {str(sim_error)}\n\nTry: 'simulate NACA 2412 at 5 degrees'",
                    extracted_params=extracted_params,
                    simulation_triggered=False,
                    simulation_results=None
                )
        
        # Generate response
        ai_response = generate_response(request.message, extracted_params, simulation_results)
        
        return ChatResponse(
            response=ai_response,
            extracted_params=extracted_params,
            simulation_triggered=simulation_triggered,
            simulation_results=simulation_results
        )
        
    except Exception as e:
        raise HTTPException(500, f"Chat processing failed: {str(e)}")


@router.get("/guidance")
async def get_parameter_guidance():
    """Get parameter guidance for users"""
    return {
        "message": "FREE CFD Tutor - No API costs!",
        "commands": [
            "simulate NACA 2412 at 8 degrees",
            "run NACA 0012 at 5 degrees",
            "test NACA 4412 at 10 degrees",
            "help",
            "what is lift?",
            "what is drag?",
            "explain L/D ratio"
        ],
        "parameters": {
            "NACA codes": ["0012", "2412", "4412", "0015"],
            "Alpha range": "0-15 degrees (typical)",
            "Reynolds": "1,000,000 (default)"
        }
    }