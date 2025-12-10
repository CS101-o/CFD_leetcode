import numpy as np
import re
from typing import Dict, List
from dataclasses import dataclass
from app.utils.neuralfoil_wrapper import get_predictor, create_naca_airfoil

@dataclass
class SimulationCondition:
    alpha: float
    reynolds: float
    name: str = "Unnamed"

class FreeAirfoilAgent:
    def __init__(self):
        self.current_airfoil = None
        self.predictor = get_predictor()
        self.simulation_history = []
    
    def process_command(self, command: str) -> Dict:
        command = command.lower().strip()
        if "generate" in command or "create" in command:
            naca_match = re.search(r'naca\s*(\d{4})', command)
            if naca_match:
                return self.generate_airfoil(f"NACA {naca_match.group(1)}")
            return {"error": "Could not parse NACA code"}
        elif "test" in command or "simulate" in command:
            conditions = self._parse_conditions(command)
            if not conditions:
                conditions = [SimulationCondition(4.0, 2e6, "Cruise")]
            return self.run_simulations(conditions)
        return {"error": "Command not recognized"}
    
    def generate_airfoil(self, description: str) -> Dict:
        naca_match = re.search(r'naca\s*(\d{4})', description.lower())
        if naca_match:
            naca_code = naca_match.group(1)
            coords = create_naca_airfoil(naca_code)
            self.current_airfoil = coords
            return {"action": "generate", "success": True, "airfoil": {"coordinates": coords.tolist(), "type": "naca", "designation": f"NACA {naca_code}"}, "message": f"Generated NACA {naca_code}"}
        return {"error": "Could not parse airfoil description"}
    
    def run_simulations(self, conditions: List[SimulationCondition]) -> Dict:
        if self.current_airfoil is None:
            return {"error": "No airfoil generated yet"}
        results = []
        for cond in conditions:
            result = self.predictor.predict(self.current_airfoil, cond.alpha, cond.reynolds, 0.0)
            results.append({"condition": cond.name, "alpha": cond.alpha, "reynolds": cond.reynolds, "metrics": {"CL": result['CL'], "CD": result['CD'], "CM": result['CM'], "L_D": result['L_D'], "stall_risk": self._assess_stall(result['CL'], cond.alpha), "efficiency_rating": self._rate_efficiency(result['L_D'])}, "time_ms": result['time_ms']})
        self.simulation_history.extend(results)
        return {"action": "simulate", "success": True, "results": results, "message": f"Completed {len(results)} simulations"}
    
    def _parse_conditions(self, command: str) -> List[SimulationCondition]:
        conditions = []
        if "cruise" in command:
            conditions.append(SimulationCondition(4.0, 2e6, "Cruise"))
        if "takeoff" in command:
            conditions.append(SimulationCondition(8.0, 1.5e6, "Takeoff"))
        if "landing" in command:
            conditions.append(SimulationCondition(6.0, 1e6, "Landing"))
        return conditions
    
    def _assess_stall(self, CL: float, alpha: float) -> str:
        if alpha > 15 or CL > 1.5:
            return "high"
        elif alpha > 10 or CL > 1.2:
            return "medium"
        return "low"
    
    def _rate_efficiency(self, L_D: float) -> str:
        if L_D > 100:
            return "excellent"
        elif L_D > 50:
            return "good"
        elif L_D > 25:
            return "fair"
        return "poor"
