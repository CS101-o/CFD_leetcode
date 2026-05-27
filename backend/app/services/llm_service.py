"""
LLM Service - Gemini API with native function calling.
Model returns a FunctionCall part; we execute it, then ask for a plain-text summary.
"""
import json
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from app.services.tool_executor import ToolExecutor

def _model() -> str:
    return os.environ.get("AI_MODEL", "gemini-2.0-flash")

_TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="run_simulation",
            description=(
                "Run aerodynamic simulation on a single NACA airfoil at one angle of attack. "
                "Returns CL, CD, and L/D."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "naca_designation": types.Schema(type=types.Type.STRING, description="4-digit NACA code, e.g. '2412'"),
                    "angle_of_attack": types.Schema(type=types.Type.NUMBER, description="Angle of attack in degrees"),
                    "reynolds_number": types.Schema(type=types.Type.NUMBER, description="Reynolds number"),
                    "mach_number": types.Schema(type=types.Type.NUMBER, description="Mach number"),
                },
                required=["naca_designation"],
            ),
        ),
        types.FunctionDeclaration(
            name="run_polar_sweep",
            description=(
                "Run simulations across a range of angles of attack (a polar sweep). "
                "Use for 'diagnose', 'baseline', 'polar', 'sweep', 'CL vs alpha', "
                "or any request to characterise airfoil performance over a range of angles."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "naca_designation": types.Schema(type=types.Type.STRING, description="4-digit NACA code"),
                    "alpha_start": types.Schema(type=types.Type.NUMBER, description="Start angle in degrees (default -5)"),
                    "alpha_end": types.Schema(type=types.Type.NUMBER, description="End angle in degrees (default 15)"),
                    "alpha_step": types.Schema(type=types.Type.NUMBER, description="Step size in degrees (default 1)"),
                    "reynolds_number": types.Schema(type=types.Type.NUMBER, description="Reynolds number"),
                    "mach_number": types.Schema(type=types.Type.NUMBER, description="Mach number (default 0)"),
                },
                required=["naca_designation"],
            ),
        ),
        types.FunctionDeclaration(
            name="compare_airfoils",
            description=(
                "Compare multiple NACA airfoils at a fixed angle of attack. "
                "Use for 'compare', 'vs', 'versus', 'which is better'."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "airfoils": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="List of 4-digit NACA codes",
                    ),
                    "angle_of_attack": types.Schema(type=types.Type.NUMBER, description="Angle of attack in degrees"),
                    "reynolds_number": types.Schema(type=types.Type.NUMBER, description="Reynolds number"),
                },
                required=["airfoils"],
            ),
        ),
        types.FunctionDeclaration(
            name="optimize_airfoil",
            description="Find optimal airfoil or operating conditions. Use for 'optimize', 'maximize', 'minimize', 'best'.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "objective": types.Schema(type=types.Type.STRING, description="max_lift | min_drag | max_ld_ratio | max_endurance"),
                    "naca_designation": types.Schema(type=types.Type.STRING, description="Optional specific airfoil"),
                    "reynolds_number": types.Schema(type=types.Type.NUMBER, description="Reynolds number"),
                    "alpha_range": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.NUMBER),
                        description="[alpha_min, alpha_max]",
                    ),
                },
                required=["objective"],
            ),
        ),
        types.FunctionDeclaration(
            name="generate_airfoil",
            description="Generate airfoil coordinates for visualisation.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "airfoil_type": types.Schema(type=types.Type.STRING, description="'naca4' or 'preset'"),
                    "designation": types.Schema(type=types.Type.STRING, description="NACA designation"),
                    "num_points": types.Schema(type=types.Type.NUMBER, description="Number of surface points"),
                },
                required=["airfoil_type", "designation"],
            ),
        ),
        types.FunctionDeclaration(
            name="modify_geometry",
            description="Modify airfoil geometry (scale thickness or camber, add flap).",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "modification_type": types.Schema(type=types.Type.STRING, description="scale_thickness | scale_camber | shift_max_camber | add_flap"),
                    "value": types.Schema(type=types.Type.NUMBER, description="Modification magnitude"),
                    "naca_designation": types.Schema(type=types.Type.STRING, description="Base NACA airfoil"),
                },
                required=["modification_type", "value"],
            ),
        ),
        types.FunctionDeclaration(
            name="run_monte_carlo",
            description=(
                "Run a Monte Carlo simulation to estimate uncertainty and sensitivity "
                "for a NACA airfoil. Perturbs geometry and/or angle of attack across "
                "many samples and returns P10/P50/P90 distributions, sensitivity "
                "analysis, and high-value next experiments. Use when the user asks "
                "about robustness, uncertainty, sensitivity, or 'what to try next'."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "naca_designation": types.Schema(type=types.Type.STRING),
                    "alpha": types.Schema(type=types.Type.NUMBER),
                    "reynolds_number": types.Schema(type=types.Type.NUMBER),
                    "mach_number": types.Schema(type=types.Type.NUMBER),
                    "n_samples": types.Schema(type=types.Type.NUMBER, description="50–2000"),
                    "perturbation_pct": types.Schema(type=types.Type.NUMBER, description="Geometry std dev as % chord, 0.1–5"),
                    "perturb_camber": types.Schema(type=types.Type.BOOLEAN),
                    "perturb_thickness": types.Schema(type=types.Type.BOOLEAN),
                    "perturb_alpha": types.Schema(type=types.Type.BOOLEAN),
                    "alpha_std": types.Schema(type=types.Type.NUMBER, description="AoA std dev in degrees"),
                },
                required=["naca_designation"],
            ),
        ),
        types.FunctionDeclaration(
            name="explain_concept",
            description="Explain an aerodynamics concept. Use for 'what is', 'explain', 'how does', 'why'.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "topic": types.Schema(type=types.Type.STRING, description="The aerodynamics topic to explain"),
                },
                required=["topic"],
            ),
        ),
    ]
)

_SIM_TOOLS = {"run_simulation", "run_polar_sweep", "compare_airfoils", "optimize_airfoil", "run_monte_carlo"}


def _build_contents(history: List[Dict], message: str) -> List[types.Content]:
    contents = []
    for m in history:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    return contents


class LLMService:
    def __init__(self):
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set")
        self.client = genai.Client(api_key=api_key)
        self.executor = ToolExecutor()
        self.system_prompt = ""

    async def _generate(
        self,
        system: str,
        contents,
        use_tools: bool = True,
    ):
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.3,
            tools=[_TOOLS] if use_tools else None,
        )
        try:
            return await self.client.aio.models.generate_content(
                model=_model(),
                contents=contents,
                config=config,
            )
        except Exception as e:
            print(f"[Gemini] call failed (model={_model()}): {e}")
            return None

    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        challenge_context: Optional[str] = None,
        _current_results: Optional[Dict] = None,
        summary_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:

        history = (conversation_history or [])[-10:]
        system = self.system_prompt
        if challenge_context:
            system += f"\n\n{challenge_context}"

        contents = _build_contents(history, message)

        # Step 1 — tool selection
        response = await self._generate(system, contents, use_tools=True)
        if response is None:
            return self._error("Cannot reach Gemini API. Check GOOGLE_API_KEY.")

        # Extract function call if present
        fc = None
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call and part.function_call.name:
                    fc = part.function_call
                    break

        if fc:
            tool_name = fc.name
            args = dict(fc.args) if fc.args else {}
            print(f"[Gemini] → {tool_name}({json.dumps(args, default=str)})")

            result = self.executor.execute(tool_name, args)
            simulation_data = result if tool_name in _SIM_TOOLS else None
            coordinates = result.get("coordinates") if isinstance(result, dict) else None
            result_no_coords = (
                {k: v for k, v in result.items() if k != "coordinates"}
                if isinstance(result, dict) else result
            )

            # Step 2 — standalone summarisation call (avoids multi-turn FC state issues)
            synth_prompt = (
                f"Tool `{tool_name}` just ran and returned these results:\n"
                f"```json\n{json.dumps(result_no_coords, indent=2, default=str)}\n```\n\n"
                + (summary_instruction or (
                    "Summarise for the engineer in plain English. "
                    "Include key numbers (CL, CD, L/D) and a brief physical interpretation. "
                    "No JSON, no code blocks."
                ))
            )
            summary_contents = [
                types.Content(role="user", parts=[types.Part(text=synth_prompt)])
            ]
            summary_resp = await self._generate(system, summary_contents, use_tools=False)
            if summary_resp and summary_resp.text:
                final_text = summary_resp.text.strip()
            else:
                final_text = self._fallback(result)

            return {
                "response": final_text,
                "simulation_triggered": simulation_data is not None,
                "simulation_results": simulation_data,
                "coordinates": coordinates,
                "tools_called": [tool_name],
            }

        # No function call — plain-text response
        final_text = (response.text or "").strip() or "Try asking me to simulate an airfoil!"
        return {
            "response": final_text,
            "simulation_triggered": False,
            "simulation_results": None,
            "coordinates": None,
            "tools_called": [],
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _fallback(result: Any) -> str:
        if not isinstance(result, dict) or result.get("status") != "success":
            return "Operation completed."
        if "results" in result:
            r = result["results"]
            return f"NACA {result.get('airfoil','?')}: CL={r['CL']:.4f}, CD={r['CD']:.6f}, L/D={r['L_D']}"
        if "summary" in result:
            s = result["summary"]
            return f"Max L/D={s['max_L_D']} at α={s['max_L_D_alpha']}°"
        return "Simulation complete."

    @staticmethod
    def _error(msg: str) -> Dict[str, Any]:
        return {
            "response": msg,
            "simulation_triggered": False,
            "simulation_results": None,
            "coordinates": None,
            "tools_called": [],
            "error": "llm_error",
        }


_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _instance
    if _instance is None:
        _instance = LLMService()
    return _instance
