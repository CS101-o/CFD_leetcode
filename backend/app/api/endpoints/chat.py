"""
AI Chat API endpoints with parameter guidance and NeuralFoil integration
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import anthropic
import os
import re
import json

from app.utils.neuralfoil_wrapper import (
    get_predictor,
    create_naca_airfoil,
    get_preset_coordinates,
    PRESETS
)
from app.core.config import settings

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Request model for chat"""
    message: str
    current_results: Optional[Dict] = None
    conversation_history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    """Response model for chat"""
    response: str
    extracted_params: Optional[Dict] = None
    simulation_triggered: bool = False
    simulation_results: Optional[Dict] = None


def extract_airfoil_params(text: str) -> Optional[Dict]:
    """
    Extract airfoil parameters from natural language text

    Examples:
    - "NACA 2412 at 8 degrees" -> {"airfoil_type": "naca", "naca_designation": "2412", "alpha": 8.0}
    - "camber 0.04, thickness 0.12, alpha 5" -> {"airfoil_type": "custom", "camber": 0.04, "thickness": 0.12, "alpha": 5.0}
    - "preset high_lift at Reynolds 2000000" -> {"airfoil_type": "preset", "preset_name": "high_lift", "reynolds": 2000000}
    """
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

    # Camber and thickness for custom airfoils
    camber_match = re.search(r'camber\s*[:]?\s*(\d+\.?\d*)', text_lower)
    if camber_match:
        params['camber'] = float(camber_match.group(1))
        if 'airfoil_type' not in params:
            params['airfoil_type'] = 'custom'

    thickness_match = re.search(r'thickness\s*[:]?\s*(\d+\.?\d*)', text_lower)
    if thickness_match:
        params['thickness'] = float(thickness_match.group(1))
        if 'airfoil_type' not in params:
            params['airfoil_type'] = 'custom'

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
        r'(\d+\.?\d*)\s*million'
    ]
    for pattern in reynolds_patterns:
        re_match = re.search(pattern, text_lower)
        if re_match:
            value = float(re_match.group(1))
            # Convert to actual Reynolds number if in millions
            if 'million' in text_lower or 'm' in text_lower:
                value *= 1e6
            params['reynolds'] = value
            break

    return params if params else None


def build_guidance_system_prompt() -> str:
    """Build the system prompt for the AI tutor"""
    return f"""You are an expert aerodynamics AI tutor helping users learn about airfoil design and CFD simulation.

Your role is to:
1. Guide users on how to specify airfoil parameters correctly
2. Explain aerodynamic concepts (lift, drag, L/D ratio, angle of attack, Reynolds number)
3. Interpret simulation results and suggest improvements
4. Be educational and encouraging

Available airfoil types:
- **NACA 4-digit** (e.g., "NACA 0012", "NACA 2412", "NACA 4412")
  Format: MPXX where M=max camber (%), P=location of max camber (/10), XX=thickness (%)

- **Presets**: {', '.join(PRESETS.keys())}
  Examples: "naca0012" (symmetric), "high_lift" (high camber), "low_drag" (thin)

- **Custom**: Specify camber and thickness
  Example: "camber 0.04, thickness 0.12"

Parameters you can set:
- **Alpha (angle of attack)**: -20° to 30° (typical: 0-15°)
- **Reynolds number**: 10,000 to 10,000,000 (typical: 1,000,000)
- **Mach number**: 0 to 0.3 (currently unused by NeuralFoil)

When users ask for help:
- Explain parameter ranges and typical values
- Suggest good starting points for beginners
- Interpret results (e.g., "Your L/D of 65 is excellent for a low-speed airfoil")
- Explain trade-offs (lift vs drag, camber vs thickness)

Current simulation tool:
- **NeuralFoil 0.3.2**: Neural network CFD solver
- **Speed**: 3-5ms per prediction
- **Accuracy**: Trained on XFOIL data, accurate for standard airfoils

Keep responses concise (2-4 sentences) unless explaining complex concepts.
"""


async def call_claude_api(messages: List[Dict], system_prompt: str) -> str:
    """Call Claude API for chat completion"""
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            system=system_prompt,
            messages=messages
        )

        return response.content[0].text

    except Exception as e:
        print(f"Claude API error: {e}")
        return "I'm having trouble connecting to my AI brain right now. Please try again!"


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """
    Send a message to the AI tutor chatbot

    The chatbot can:
    - Answer aerodynamics questions
    - Guide parameter selection
    - Extract parameters from natural language
    - Trigger simulations automatically
    - Interpret results
    """
    try:
        # Extract parameters from message
        extracted_params = extract_airfoil_params(request.message)

        # Build conversation context
        system_prompt = build_guidance_system_prompt()

        # Add current results to context if available
        context_parts = []
        if request.current_results:
            context_parts.append(f"Current simulation results: CL={request.current_results.get('CL', 'N/A'):.3f}, CD={request.current_results.get('CD', 'N/A'):.4f}, L/D={request.current_results.get('L_D', 'N/A'):.1f}")

        # Add extracted params to context
        if extracted_params:
            context_parts.append(f"User mentioned parameters: {json.dumps(extracted_params)}")

        # Build messages for Claude
        messages = []

        # Add conversation history
        for msg in request.conversation_history[-6:]:  # Last 3 exchanges
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add current message with context
        user_message = request.message
        if context_parts:
            user_message += "\n\n[Context: " + "; ".join(context_parts) + "]"

        messages.append({
            "role": "user",
            "content": user_message
        })

        # Get AI response
        ai_response = await call_claude_api(messages, system_prompt)

        # Check if we should trigger a simulation
        simulation_results = None
        simulation_triggered = False

        # Trigger simulation if:
        # 1. User explicitly asks to "run", "simulate", "test", etc.
        # 2. AND we have enough parameters
        trigger_words = ['run', 'simulate', 'test', 'analyze', 'try', 'show me']
        should_simulate = any(word in request.message.lower() for word in trigger_words)

        if should_simulate and extracted_params and extracted_params.get('airfoil_type'):
            try:
                # Fill in default values
                if 'alpha' not in extracted_params:
                    extracted_params['alpha'] = 5.0
                if 'reynolds' not in extracted_params:
                    extracted_params['reynolds'] = 1000000

                # Get coordinates
                if extracted_params['airfoil_type'] == 'naca':
                    coords = create_naca_airfoil(extracted_params['naca_designation'])
                elif extracted_params['airfoil_type'] == 'preset':
                    coords = get_preset_coordinates(extracted_params['preset_name'])
                elif extracted_params['airfoil_type'] == 'custom':
                    from app.utils.neuralfoil_wrapper import create_custom_airfoil
                    coords = create_custom_airfoil(
                        extracted_params.get('camber', 0.04),
                        extracted_params.get('thickness', 0.12)
                    )

                # Run simulation
                predictor = get_predictor()
                result = predictor.predict(
                    coordinates=coords,
                    alpha=extracted_params['alpha'],
                    reynolds=extracted_params['reynolds']
                )

                simulation_results = result
                simulation_triggered = True

                # Append results to AI response
                ai_response += f"\n\nSimulation complete! CL={result['CL']:.3f}, CD={result['CD']:.4f}, L/D={result['L_D']:.1f}"

            except Exception as sim_error:
                ai_response += f"\n\nI tried to run the simulation but encountered an error: {str(sim_error)}"

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
        "airfoil_types": {
            "naca": {
                "description": "NACA 4-digit series",
                "format": "MPXX (M=camber %, P=camber position /10, XX=thickness %)",
                "examples": ["0012", "2412", "4412", "0015"]
            },
            "preset": {
                "description": "Pre-configured airfoils",
                "options": list(PRESETS.keys()),
                "examples": {
                    "naca0012": "Symmetric, 12% thick",
                    "high_lift": "High camber for maximum lift",
                    "low_drag": "Thin profile for efficiency"
                }
            },
            "custom": {
                "description": "Custom airfoil design",
                "parameters": {
                    "camber": "0.0-0.15 (typical: 0.02-0.08)",
                    "thickness": "0.05-0.25 (typical: 0.10-0.18)"
                }
            }
        },
        "flow_parameters": {
            "alpha": {
                "name": "Angle of attack",
                "range": "-20° to 30°",
                "typical": "0° to 15°",
                "description": "Angle between airfoil chord and freestream"
            },
            "reynolds": {
                "name": "Reynolds number",
                "range": "10,000 to 10,000,000",
                "typical": "1,000,000",
                "description": "Ratio of inertial to viscous forces"
            }
        },
        "tips": [
            "Start with alpha=5° and Re=1,000,000 for general airfoils",
            "Symmetric airfoils (NACA 0012) have zero lift at alpha=0°",
            "Higher camber increases lift but also drag",
            "Thicker airfoils are stronger but have more drag",
            "L/D ratio above 50 is excellent for low-speed flight"
        ]
    }
