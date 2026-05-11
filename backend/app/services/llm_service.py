"""
LLM Service - Structured JSON prompting (no tool calling protocol).
The model outputs a JSON action, we parse and execute it, then ask the model to summarize.
Works reliably with 7B models that can't do proper tool calling.
"""
import httpx
import json
import re
from typing import Dict, Any, List, Optional

from app.services.llm_tools import SYSTEM_PROMPT
from app.services.tool_executor import ToolExecutor

# Valid tool names the model can invoke
VALID_TOOLS = {
    "generate_airfoil",
    "run_simulation",
    "run_polar_sweep",
    "compare_airfoils",
    "optimize_airfoil",
    "modify_geometry",
    "explain_concept",
}


class LLMService:
    """Manages LLM interactions via Ollama using structured JSON prompting."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b-instruct"):
        self.base_url = base_url
        self.model = model
        self.api_url = f"{base_url}/api/chat"
        self.executor = ToolExecutor()
        self.client = httpx.AsyncClient(timeout=120.0)
        self.system_prompt = self._build_default_system_prompt()

    def _build_default_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        challenge_context: Optional[str] = None,
        current_results: Optional[Dict] = None,
        summary_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message through structured JSON prompting.

        Flow:
        1. Send user message with JSON-output system prompt → model returns JSON action
        2. Parse JSON → execute the tool via ToolExecutor
        3. Send tool results back → model generates human-readable summary

        Args:
            summary_instruction: If provided, replaces the default summary prompt in
                step 3. Use this to inject caller-specific synthesis personality
                (e.g. FlowSense phase 3 instructions) without polluting the action step.
        """
        # --- Build action-step system prompt ---
        system_content = self.system_prompt
        if challenge_context:
            system_content += f"\n\n{challenge_context}"

        messages = [{"role": "system", "content": system_content}]

        if conversation_history:
            messages.extend(conversation_history[-10:])

        messages.append({"role": "user", "content": message})

        # --- Step 1: Ask LLM to decide an action (JSON) ---
        print("\n" + "="*60)
        print("[LLM STEP 1] Sending action request to model...")
        print(f"[LLM STEP 1] System prompt (first 300 chars): {system_content[:300]}")
        print(f"[LLM STEP 1] User message: {message}")
        print("="*60)

        action_response = await self._call_llm(messages)

        if not action_response:
            return self._error_response(
                "Cannot connect to Ollama. Make sure it's running (`ollama serve`) "
                f"with {self.model} pulled."
            )

        raw_content = (
            action_response.get("message", {}).get("content", "").strip()
        )

        print(f"\n[LLM STEP 1] Raw model output:\n{raw_content}\n")

        # --- Step 2: Parse the JSON action ---
        action = self._extract_action(raw_content)

        print(f"[LLM STEP 2] Parsed action: {action}")

        tool_results = []
        simulation_data = None
        coordinates = None

        if action and action.get("tool") in VALID_TOOLS:
            tool_name = action["tool"]
            tool_args = action.get("args", {})

            print(f"\n[TOOL EXEC] Running tool: {tool_name}")
            print(f"[TOOL EXEC] Args: {json.dumps(tool_args, indent=2)}")

            # Execute the tool
            result = self.executor.execute(tool_name, tool_args)
            tool_results.append({"name": tool_name, "result": result})

            print(f"[TOOL EXEC] Result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            if isinstance(result, dict) and "error" not in result:
                # Print key numbers without dumping full coordinates
                summary_keys = {k: v for k, v in result.items() if k != "coordinates"}
                print(f"[TOOL EXEC] Result (no coords): {json.dumps(summary_keys, indent=2, default=str)}")
            else:
                print(f"[TOOL EXEC] Result: {result}")

            # Collect frontend data
            if tool_name in (
                "run_simulation",
                "run_polar_sweep",
                "compare_airfoils",
                "optimize_airfoil",
            ):
                simulation_data = result
            if isinstance(result, dict) and "coordinates" in result:
                coordinates = result["coordinates"]

            # --- Step 3: Ask LLM to summarize the results ---
            result_for_summary = {
                k: v
                for k, v in result.items()
                if k != "coordinates"
            } if isinstance(result, dict) else result

            # Build the summary user turn — use caller-supplied instruction if provided
            if summary_instruction:
                summary_user_content = (
                    f"Tool `{tool_name}` returned these results:\n"
                    f"```json\n{json.dumps(result_for_summary, indent=2, default=str)}\n```\n\n"
                    f"{summary_instruction}"
                )
            else:
                summary_user_content = (
                    f"Tool `{tool_name}` returned these results:\n"
                    f"```json\n{json.dumps(result_for_summary, indent=2, default=str)}\n```\n\n"
                    "Summarize the results for the user in a clear, concise way. "
                    "Include the key numbers (CL, CD, L/D) and a brief interpretation. "
                    "Do NOT output JSON. Respond in plain English."
                )

            messages.append({
                "role": "assistant",
                "content": raw_content,
            })
            messages.append({
                "role": "user",
                "content": summary_user_content,
            })

            print(f"\n[LLM STEP 3] Sending summary request...")
            print(f"[LLM STEP 3] Summary instruction (first 200 chars): {summary_user_content[:200]}")

            summary_response = await self._call_llm(messages)
            if summary_response:
                final_text = (
                    summary_response.get("message", {})
                    .get("content", "")
                    .strip()
                )
                print(f"\n[LLM STEP 3] Summary output:\n{final_text}\n")
            else:
                final_text = self._format_fallback(tool_results)
                print(f"[LLM STEP 3] Summary failed, using fallback: {final_text}")

        elif action and action.get("tool") == "direct_response":
            # Model decided no tool is needed
            final_text = action.get("message", raw_content)
            print(f"[LLM] Direct response (no tool): {final_text[:200]}")

        else:
            # Could not parse action — clean and return raw content
            print(f"[LLM] WARN: Could not parse action from output. Cleaning raw response.")
            final_text = self._clean_response(raw_content)

        return {
            "response": final_text,
            "simulation_triggered": simulation_data is not None,
            "simulation_results": simulation_data,
            "coordinates": coordinates,
            "tools_called": [tr["name"] for tr in tool_results]
            if tool_results
            else [],
        }

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------

    def _extract_action(self, text: str) -> Optional[Dict]:
        """
        Extract a JSON action block from the model's response.

        Tries, in order:
        1. ```json ... ``` fenced block
        2. Raw JSON object at start/end of text
        3. JSON object anywhere in the text
        """
        # 1. Fenced code block
        fence_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL
        )
        if fence_match:
            return self._safe_parse(fence_match.group(1))

        # 2. Starts or ends with {
        stripped = text.strip()
        if stripped.startswith("{"):
            return self._safe_parse(stripped)

        # 3. JSON anywhere
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            return self._safe_parse(brace_match.group(0))

        return None

    @staticmethod
    def _safe_parse(raw: str) -> Optional[Dict]:
        """Parse JSON, tolerating trailing commas and minor issues."""
        # Remove trailing commas before } or ]
        cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        return None

    # ------------------------------------------------------------------
    # Ollama communication
    # ------------------------------------------------------------------

    async def _call_llm(self, messages: List[Dict]) -> Optional[Dict]:
        """Call Ollama's native /api/chat endpoint (no tools param)."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,
            },
        }

        try:
            response = await self.client.post(self.api_url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            print(
                f"ERROR: Cannot connect to Ollama at {self.api_url}. "
                "Is it running? (ollama serve)"
            )
            return None
        except httpx.HTTPStatusError as e:
            print(
                f"ERROR: Ollama returned {e.response.status_code}: "
                f"{e.response.text[:500]}"
            )
            return None
        except Exception as e:
            print(f"ERROR: LLM call failed: {type(e).__name__}: {e}")
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _error_response(msg: str) -> Dict[str, Any]:
        return {
            "response": msg,
            "simulation_triggered": False,
            "simulation_results": None,
            "coordinates": None,
            "tools_called": [],
            "error": "llm_connection_failed",
        }

    @staticmethod
    def _clean_response(text: str) -> str:
        """Remove JSON fragments from a response intended as plain text."""
        # Strip fenced blocks
        text = re.sub(r"```(?:json)?.*?```", "", text, flags=re.DOTALL)
        # Strip orphan JSON objects
        text = re.sub(r"\{[^{}]{5,}\}", "", text)
        return text.strip() or "I'm not sure how to help with that. Try asking me to simulate an airfoil!"

    def _format_fallback(self, tool_results: List[Dict]) -> str:
        """Format results when the LLM can't generate a summary."""
        parts = []
        for tr in tool_results:
            result = tr["result"]
            if not isinstance(result, dict):
                continue
            if result.get("status") == "success":
                if "results" in result:
                    r = result["results"]
                    parts.append(
                        f"NACA {result.get('airfoil', '?')} at "
                        f"α={result['conditions']['alpha']}°: "
                        f"CL={r['CL']:.4f}, CD={r['CD']:.6f}, L/D={r['L_D']}"
                    )
                elif "comparisons" in result:
                    for c in result["comparisons"]:
                        parts.append(
                            f"NACA {c['airfoil']}: CL={c['CL']:.4f}, "
                            f"CD={c['CD']:.6f}, L/D={c['L_D']}"
                        )
                elif "summary" in result:
                    s = result["summary"]
                    parts.append(
                        f"Max CL={s['max_CL']:.4f} at α={s['max_CL_alpha']}°, "
                        f"Max L/D={s['max_L_D']} at α={s['max_L_D_alpha']}°"
                    )
                elif "optimal_conditions" in result:
                    o = result["optimal_conditions"]
                    parts.append(
                        f"Optimal: α={o['alpha']}° → CL={o['CL']:.4f}, "
                        f"CD={o['CD']:.6f}, L/D={o['L_D']}"
                    )
            elif "error" in result:
                parts.append(f"Error: {result['error']}")

        return "\n".join(parts) if parts else "Operation completed."

    async def health_check(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/tags", timeout=5.0
            )
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return any(self.model.split(":")[0] in m for m in models)
        except Exception:
            return False

    async def close(self):
        """Clean up HTTP client."""
        await self.client.aclose()


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service