"""
AI Tutor Service - Conversational CFD tutoring using Claude/GPT

This service provides context-aware AI assistance for learning CFD:
- Explains aerodynamic concepts (lift, drag, boundary layers, etc.)
- Debugs simulation issues (convergence failures, unrealistic results)
- Suggests improvements and next steps
- Provides hints for challenges
"""

import json
from typing import List, Dict, Optional
from anthropic import Anthropic
from openai import OpenAI

from app.core.config import settings
from app.models import Simulation, Challenge


class AITutorService:
    """AI-powered CFD tutor using Claude or GPT-4"""

    def __init__(self):
        self.provider = settings.AI_PROVIDER

        if self.provider == "anthropic":
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = settings.AI_MODEL
        elif self.provider == "openai":
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.AI_MODEL
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

        # System prompt for CFD tutoring
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt for CFD tutoring"""
        return """You are an expert CFD (Computational Fluid Dynamics) tutor for AirfoilLearner,
an educational platform for learning aerodynamics through interactive simulations.

Your role:
1. **Explain CFD concepts**: Teach users about lift, drag, pressure distributions, boundary layers,
   flow separation, stall, Reynolds number effects, etc. Use analogies and visual descriptions.

2. **Debug simulations**: Help users understand why simulations fail (convergence issues,
   unrealistic boundary conditions, mesh problems) and suggest fixes.

3. **Guide learning**: Provide progressive hints for challenges without giving away answers.
   Encourage exploration and understanding over memorization.

4. **Analyze results**: Help interpret Cp distributions, Cl/Cd curves, and transition points.
   Explain what physical phenomena cause observed patterns.

5. **Best practices**: Teach simulation best practices (appropriate Reynolds numbers,
   angle of attack ranges, when to use viscous vs inviscid, etc.).

Communication style:
- Be encouraging and Socratic - ask questions to guide thinking
- Use clear, accessible language (avoid excessive jargon)
- Provide formulas when relevant (use LaTeX: $C_L = L/(0.5 \\rho V^2 S)$)
- Reference real-world examples (aircraft, wind turbines, etc.)
- Be concise but thorough

Context awareness:
- You'll receive simulation parameters and results in the conversation
- Tailor explanations to the user's current challenge or experiment
- Build on previous messages in the conversation

Safety:
- Don't provide complete solutions to challenges - give hints instead
- Ensure users understand the physics, not just the numbers
- Correct misconceptions gently

Remember: You're teaching aerodynamics and CFD, not just answering questions.
Foster curiosity and deep understanding."""

    async def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        context: Optional[Dict] = None
    ) -> str:
        """
        Generate AI tutor response

        Args:
            user_message: Latest user message
            conversation_history: Previous messages [{"role": "user/assistant", "content": "..."}]
            context: Optional simulation/challenge context

        Returns:
            AI-generated response
        """
        # Build context-aware prompt
        enhanced_message = self._enhance_message_with_context(user_message, context)

        # Prepare messages for API
        messages = conversation_history + [
            {"role": "user", "content": enhanced_message}
        ]

        # Call appropriate API
        if self.provider == "anthropic":
            return await self._generate_anthropic(messages)
        else:
            return await self._generate_openai(messages)

    def _enhance_message_with_context(
        self,
        message: str,
        context: Optional[Dict]
    ) -> str:
        """Add simulation/challenge context to user message"""
        if not context:
            return message

        context_parts = [message, "\n\n[Context]"]

        # Add simulation context
        if "simulation" in context:
            sim = context["simulation"]
            context_parts.append(
                f"Current simulation: {sim.get('airfoil_designation', 'custom')} airfoil\n"
                f"- Angle of attack: {sim.get('alpha')}°\n"
                f"- Reynolds number: {sim.get('reynolds'):.2e}\n"
                f"- Solver: {sim.get('solver_type')}\n"
                f"- Status: {sim.get('status')}"
            )

            if sim.get("results"):
                results = sim["results"]
                context_parts.append(
                    f"\nResults:\n"
                    f"- CL: {results.get('cl', 'N/A')}\n"
                    f"- CD: {results.get('cd', 'N/A')}\n"
                    f"- CM: {results.get('cm', 'N/A')}\n"
                    f"- Converged: {results.get('converged', False)}"
                )

        # Add challenge context
        if "challenge" in context:
            ch = context["challenge"]
            context_parts.append(
                f"\nActive challenge: '{ch.get('title')}'\n"
                f"- Difficulty: {ch.get('difficulty')}\n"
                f"- Category: {ch.get('category')}"
            )

        return "\n".join(context_parts)

    async def _generate_anthropic(self, messages: List[Dict]) -> str:
        """Generate response using Claude"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=self.system_prompt,
            messages=messages
        )

        return response.content[0].text

    async def _generate_openai(self, messages: List[Dict]) -> str:
        """Generate response using GPT"""
        messages_with_system = [
            {"role": "system", "content": self.system_prompt}
        ] + messages

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages_with_system,
            max_tokens=2000,
            temperature=0.7
        )

        return response.choices[0].message.content

    async def explain_concept(self, concept: str) -> str:
        """
        Explain a specific CFD concept

        Args:
            concept: Concept name (e.g., "boundary layer", "stall", "pressure coefficient")

        Returns:
            Detailed explanation
        """
        prompt = f"""Explain the CFD concept '{concept}' in a clear, educational way.
Include:
1. What it is (definition)
2. Why it matters in aerodynamics
3. How it appears in simulations (what to look for)
4. Real-world examples
5. Related concepts

Use analogies and visual descriptions. Include relevant formulas in LaTeX."""

        return await self.generate_response(
            user_message=prompt,
            conversation_history=[]
        )

    async def debug_simulation(
        self,
        simulation_data: Dict,
        error_message: Optional[str] = None
    ) -> str:
        """
        Help debug a failed or suspicious simulation

        Args:
            simulation_data: Simulation parameters and results
            error_message: Optional error message from solver

        Returns:
            Debugging suggestions
        """
        prompt = f"""I'm having trouble with my CFD simulation. Here are the details:

Airfoil: {simulation_data.get('airfoil_designation', 'custom')}
Angle of attack: {simulation_data.get('alpha')}°
Reynolds number: {simulation_data.get('reynolds'):.2e}
Mach number: {simulation_data.get('mach', 0.0)}
Solver: {simulation_data.get('solver_type')}
Status: {simulation_data.get('status')}
"""

        if error_message:
            prompt += f"\nError message: {error_message}"

        if simulation_data.get("results"):
            results = simulation_data["results"]
            prompt += f"""
Results:
- CL: {results.get('cl')}
- CD: {results.get('cd')}
- Converged: {results.get('converged', False)}
"""

        prompt += "\nWhat might be wrong and how can I fix it?"

        return await self.generate_response(
            user_message=prompt,
            conversation_history=[]
        )

    async def get_challenge_hint(
        self,
        challenge: Dict,
        attempt_number: int,
        previous_results: Optional[List[Dict]] = None
    ) -> str:
        """
        Provide progressive hint for challenge

        Args:
            challenge: Challenge data
            attempt_number: Which attempt this is (for progressive hints)
            previous_results: User's previous simulation results

        Returns:
            Context-aware hint
        """
        # Use pre-defined hints if available
        if challenge.get("hints") and attempt_number <= len(challenge["hints"]):
            predefined_hint = challenge["hints"][attempt_number - 1]

            # Enhance predefined hint with context
            prompt = f"""The user is working on the challenge '{challenge['title']}'
(attempt #{attempt_number}). Give them this hint in an encouraging way: "{predefined_hint}"

Add brief context about why this hint is important."""
        else:
            # Generate dynamic hint
            prompt = f"""The user is working on challenge '{challenge['title']}'
({challenge['difficulty']} difficulty, category: {challenge['category']}).

Attempt: #{attempt_number}
"""

            if previous_results:
                prompt += f"\nTheir previous attempts:\n"
                for i, result in enumerate(previous_results[-3:], 1):  # Last 3 attempts
                    prompt += f"  {i}. Alpha={result.get('alpha')}°, CL={result.get('cl')}, CD={result.get('cd')}\n"

            prompt += "\nProvide a helpful hint (not the full solution) to guide them toward success."

        return await self.generate_response(
            user_message=prompt,
            conversation_history=[]
        )

    async def analyze_results(self, simulation_data: Dict) -> str:
        """
        Provide detailed analysis of simulation results

        Args:
            simulation_data: Complete simulation data with results

        Returns:
            Analysis and insights
        """
        results = simulation_data.get("results", {})

        prompt = f"""Analyze these CFD simulation results for {simulation_data.get('airfoil_designation')} airfoil:

Parameters:
- Angle of attack: {simulation_data.get('alpha')}°
- Reynolds number: {simulation_data.get('reynolds'):.2e}

Results:
- CL (lift coefficient): {results.get('cl')}
- CD (drag coefficient): {results.get('cd')}
- CM (moment coefficient): {results.get('cm')}
- L/D ratio: {results.get('cl', 0) / results.get('cd', 1):.1f}
- Top transition: {results.get('top_xtr')}
- Bottom transition: {results.get('bot_xtr')}

Provide:
1. Physical interpretation of these values
2. What's happening with the flow (attached, separated, transitional?)
3. How these compare to typical values
4. Suggestions for further exploration
"""

        return await self.generate_response(
            user_message=prompt,
            conversation_history=[]
        )


# Example usage and testing
async def test_ai_tutor():
    """Test AI tutor functionality"""
    tutor = AITutorService()

    print("Test 1: Explain a concept")
    print("=" * 60)
    explanation = await tutor.explain_concept("boundary layer separation")
    print(explanation)
    print("\n")

    print("Test 2: Debug simulation")
    print("=" * 60)
    sim_data = {
        "airfoil_designation": "NACA 0012",
        "alpha": 25.0,
        "reynolds": 1e6,
        "solver_type": "xfoil",
        "status": "failed",
        "results": {"converged": False}
    }
    debug_help = await tutor.debug_simulation(sim_data)
    print(debug_help)
    print("\n")

    print("Test 3: Analyze results")
    print("=" * 60)
    sim_data_success = {
        "airfoil_designation": "NACA 2412",
        "alpha": 5.0,
        "reynolds": 1e6,
        "results": {
            "cl": 0.845,
            "cd": 0.0089,
            "cm": -0.062,
            "top_xtr": 0.42,
            "bot_xtr": 0.18,
            "converged": True
        }
    }
    analysis = await tutor.analyze_results(sim_data_success)
    print(analysis)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_tutor())
