"""
Tool Executor - Runs the actual functions when the LLM makes tool calls.
Maps tool names to implementations using existing NeuralFoil wrapper.
"""
import numpy as np
import json
import time
from typing import Dict, Any, Optional

from app.utils.neuralfoil_wrapper import (
    get_predictor,
    create_naca_airfoil,
    get_preset_coordinates,
    PRESETS
)


class ToolExecutor:
    """Executes tool calls from the LLM using NeuralFoil."""

    def __init__(self):
        self.predictor = get_predictor()
        self.current_airfoil = None  # Track the currently loaded airfoil
        self.current_designation = None

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route a tool call to the correct handler."""
        handlers = {
            "generate_airfoil": self._generate_airfoil,
            "run_simulation": self._run_simulation,
            "run_polar_sweep": self._run_polar_sweep,
            "compare_airfoils": self._compare_airfoils,
            "optimize_airfoil": self._optimize_airfoil,
            "modify_geometry": self._modify_geometry,
            "explain_concept": self._explain_concept,
            "run_monte_carlo": self._run_monte_carlo,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return handler(**arguments)
        except Exception as e:
            return {"error": str(e)}

    def _generate_airfoil(
        self,
        airfoil_type: str,
        designation: str,
        num_points: int = 200
    ) -> Dict[str, Any]:
        """Generate airfoil coordinates."""
        if airfoil_type == "naca4":
            coords = create_naca_airfoil(designation, n_points=num_points)
            self.current_airfoil = coords
            self.current_designation = designation
            return {
                "status": "success",
                "airfoil_type": "naca4",
                "designation": designation,
                "num_points": len(coords),
                "max_thickness": float(np.max(coords[:, 1]) - np.min(coords[:, 1])),
                "coordinates": coords.tolist()
            }
        elif airfoil_type == "preset":
            coords = get_preset_coordinates(designation)
            if coords is None:
                return {"error": f"Unknown preset: {designation}. Available: {list(PRESETS.keys())}"}
            self.current_airfoil = coords
            self.current_designation = designation
            return {
                "status": "success",
                "airfoil_type": "preset",
                "designation": designation,
                "num_points": len(coords),
                "coordinates": coords.tolist()
            }
        else:
            return {"error": f"Unknown airfoil type: {airfoil_type}"}

    def _run_simulation(
        self,
        naca_designation: Optional[str] = None,
        angle_of_attack: float = 0.0,
        reynolds_number: float = 1e6,
        mach_number: float = 0.0
    ) -> Dict[str, Any]:
        """Run a single simulation."""
        # Use provided designation or fall back to current
        if naca_designation:
            coords = create_naca_airfoil(naca_designation)
            self.current_airfoil = coords
            self.current_designation = naca_designation
        elif self.current_airfoil is not None:
            coords = self.current_airfoil
            naca_designation = self.current_designation
        else:
            return {"error": "No airfoil loaded. Please specify a NACA designation."}

        start = time.time()
        result = self.predictor.predict(
            coordinates=coords,
            alpha=angle_of_attack,
            reynolds=reynolds_number,
            mach=mach_number
        )
        elapsed_ms = (time.time() - start) * 1000

        return {
            "status": "success",
            "airfoil": naca_designation,
            "conditions": {
                "alpha": angle_of_attack,
                "reynolds": reynolds_number,
                "mach": mach_number
            },
            "results": {
                "CL": round(result["CL"], 6),
                "CD": round(result["CD"], 6),
                "CM": round(result["CM"], 6),
                "L_D": round(result["CL"] / result["CD"], 2) if result["CD"] > 0 else None,
            },
            "time_ms": round(elapsed_ms, 2),
            "coordinates": coords.tolist()
        }

    def _run_polar_sweep(
        self,
        naca_designation: str,
        alpha_start: float = -5.0,
        alpha_end: float = 15.0,
        alpha_step: float = 1.0,
        reynolds_number: float = 1e6,
        mach_number: float = 0.0
    ) -> Dict[str, Any]:
        """Run a polar sweep across angles of attack."""
        coords = create_naca_airfoil(naca_designation)

        # Use the wrapper's built-in polar prediction
        polar_results = self.predictor.predict_polar(
            coordinates=coords,
            alpha_range=(alpha_start, alpha_end),
            alpha_step=alpha_step,
            reynolds=reynolds_number,
            mach=mach_number
        )

        # Format results
        results = []
        for r in polar_results:
            results.append({
                "alpha": float(r["alpha"]),
                "CL": round(r["CL"], 6),
                "CD": round(r["CD"], 6),
                "CM": round(r["CM"], 6),
                "L_D": round(r["L_D"], 2) if r["L_D"] else None
            })

        # Find key points
        max_ld_point = max(results, key=lambda x: x["L_D"] or 0)
        max_cl_point = max(results, key=lambda x: x["CL"])

        return {
            "status": "success",
            "airfoil": naca_designation,
            "reynolds": reynolds_number,
            "num_points": len(results),
            "polar_data": results,
            "summary": {
                "max_CL": max_cl_point["CL"],
                "max_CL_alpha": max_cl_point["alpha"],
                "max_L_D": max_ld_point["L_D"],
                "max_L_D_alpha": max_ld_point["alpha"],
            },
            "coordinates": coords.tolist()
        }

    def _compare_airfoils(
        self,
        airfoils: list,
        angle_of_attack: float = 5.0,
        reynolds_number: float = 1e6
    ) -> Dict[str, Any]:
        """Compare multiple airfoils at the same conditions."""
        comparisons = []
        for designation in airfoils:
            coords = create_naca_airfoil(designation)
            r = self.predictor.predict(coordinates=coords, alpha=angle_of_attack, reynolds=reynolds_number)
            comparisons.append({
                "airfoil": designation,
                "CL": round(r["CL"], 6),
                "CD": round(r["CD"], 6),
                "L_D": round(r["CL"] / r["CD"], 2) if r["CD"] > 0 else None,
                "CM": round(r["CM"], 6)
            })

        # Sort by L/D ratio
        comparisons.sort(key=lambda x: x["L_D"] or 0, reverse=True)

        best_ld_airfoil = comparisons[0]["airfoil"]

        return {
            "status": "success",
            "conditions": {
                "alpha": angle_of_attack,
                "reynolds": reynolds_number
            },
            "comparisons": comparisons,
            "best_ld": best_ld_airfoil,
            "best_lift": max(comparisons, key=lambda x: x["CL"])["airfoil"],
            "coordinates": create_naca_airfoil(best_ld_airfoil).tolist()
        }

    def _optimize_airfoil(
        self,
        objective: str,
        naca_designation: Optional[str] = None,
        reynolds_number: float = 1e6,
        alpha_range: Optional[list] = None
    ) -> Dict[str, Any]:
        """Simple optimization by sweeping parameters."""
        if alpha_range is None:
            alpha_range = [0, 15]

        # If specific airfoil given, optimize angle using wrapper's optimize_for_ld
        if naca_designation:
            coords = create_naca_airfoil(naca_designation)
            alphas = np.arange(alpha_range[0], alpha_range[1] + 0.5, 0.5)
            best = None

            for alpha in alphas:
                r = self.predictor.predict(coordinates=coords, alpha=float(alpha), reynolds=reynolds_number)
                score = {
                    "max_lift": r["CL"],
                    "min_drag": -r["CD"],
                    "max_ld_ratio": r["L_D"],
                    "max_endurance": (r["CL"] ** 1.5) / r["CD"] if r["CD"] > 0 else 0
                }[objective]

                if best is None or score > best["score"]:
                    best = {
                        "alpha": float(alpha),
                        "CL": round(r["CL"], 6),
                        "CD": round(r["CD"], 6),
                        "L_D": round(r["L_D"], 2) if r["L_D"] else None,
                        "score": score
                    }

            return {
                "status": "success",
                "objective": objective,
                "airfoil": naca_designation,
                "optimal_conditions": best
            }
        else:
            # Search across common airfoils
            common = ["0012", "1412", "2412", "2415", "4412", "4415", "6412", "2312", "2315"]
            results = []
            for des in common:
                coords = create_naca_airfoil(des)
                for alpha in np.arange(alpha_range[0], alpha_range[1] + 1, 1.0):
                    r = self.predictor.predict(coordinates=coords, alpha=float(alpha), reynolds=reynolds_number)
                    score = {
                        "max_lift": r["CL"],
                        "min_drag": -r["CD"],
                        "max_ld_ratio": r["L_D"],
                        "max_endurance": (r["CL"] ** 1.5) / r["CD"] if r["CD"] > 0 else 0
                    }[objective]
                    results.append({
                        "airfoil": des,
                        "alpha": float(alpha),
                        "CL": round(r["CL"], 6),
                        "CD": round(r["CD"], 6),
                        "L_D": round(r["L_D"], 2) if r["L_D"] else None,
                        "score": score
                    })

            results.sort(key=lambda x: x["score"], reverse=True)
            return {
                "status": "success",
                "objective": objective,
                "top_results": results[:5]
            }

    def _modify_geometry(
        self,
        modification_type: str,
        value: float,
        naca_designation: Optional[str] = None
    ) -> Dict[str, Any]:
        """Modify airfoil geometry."""
        if naca_designation:
            coords = create_naca_airfoil(naca_designation)
        elif self.current_airfoil is not None:
            coords = self.current_airfoil.copy()
        else:
            return {"error": "No airfoil loaded. Specify a NACA designation."}

        if modification_type == "scale_thickness":
            # Scale y-coordinates (thickness)
            mean_y = np.mean(coords[:, 1])
            coords[:, 1] = mean_y + (coords[:, 1] - mean_y) * value
        elif modification_type == "scale_camber":
            # Scale camber
            upper = coords[:len(coords)//2]
            lower = coords[len(coords)//2:]
            camber = (upper[:, 1] + lower[::-1, 1]) / 2
            camber *= value
            # Reconstruct
            thickness = (upper[:, 1] - lower[::-1, 1]) / 2
            upper[:, 1] = camber + thickness
            lower[:, 1] = camber[::-1] - thickness[::-1]
            coords = np.vstack([upper, lower])
        elif modification_type == "add_flap":
            # Simple trailing edge flap deflection
            flap_start = 0.7  # flap starts at 70% chord
            mask = coords[:, 0] > flap_start
            angle_rad = np.radians(value)
            pivot_x = flap_start
            dx = coords[mask, 0] - pivot_x
            dy = coords[mask, 1]
            coords[mask, 0] = pivot_x + dx * np.cos(angle_rad) - dy * np.sin(angle_rad)
            coords[mask, 1] = dx * np.sin(angle_rad) + dy * np.cos(angle_rad)

        self.current_airfoil = coords
        return {
            "status": "success",
            "modification": modification_type,
            "value": value,
            "coordinates": coords.tolist()
        }

    # ------------------------------------------------------------------
    # Monte Carlo
    # ------------------------------------------------------------------

    @staticmethod
    def _naca4_coords(m: float, p: float, t: float, n: int = 100) -> np.ndarray:
        """NACA 4-digit with continuous (non-integer) parameters."""
        x = (1 - np.cos(np.linspace(0, np.pi, n))) / 2
        yt = 5 * t * (
            0.2969 * np.sqrt(np.maximum(x, 0))
            - 0.1260 * x
            - 0.3516 * x ** 2
            + 0.2843 * x ** 3
            - 0.1015 * x ** 4
        )
        if m < 1e-4 or p < 1e-4:
            yc = np.zeros_like(x)
            dyc = np.zeros_like(x)
        else:
            yc = np.where(
                x < p,
                m / p ** 2 * (2 * p * x - x ** 2),
                m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x ** 2),
            )
            dyc = np.where(
                x < p,
                2 * m / p ** 2 * (p - x),
                2 * m / (1 - p) ** 2 * (p - x),
            )
        theta = np.arctan(dyc)
        xu = x - yt * np.sin(theta);  yu = yc + yt * np.cos(theta)
        xl = x + yt * np.sin(theta);  yl = yc - yt * np.cos(theta)
        return np.vstack([
            np.column_stack([xl[::-1], yl[::-1]]),
            np.column_stack([xu[1:], yu[1:]]),
        ]).astype(np.float64)

    def _run_monte_carlo(
        self,
        naca_designation: str,
        alpha: float = 4.0,
        reynolds_number: float = 1_000_000,
        mach_number: float = 0.0,
        n_samples: int = 300,
        perturbation_pct: float = 1.0,
        perturb_camber: bool = True,
        perturb_thickness: bool = True,
        perturb_alpha: bool = False,
        alpha_std: float = 0.5,
    ) -> Dict[str, Any]:
        code = str(naca_designation).zfill(4)
        m_nom = int(code[0]) / 100.0
        p_nom = int(code[1]) / 10.0 or 0.4
        t_nom = int(code[2:]) / 100.0
        sigma = perturbation_pct / 100.0
        n_samples = max(50, min(n_samples, 2000))

        CLs, L_Ds, d_ms, d_ts, d_as = [], [], [], [], []
        start = time.time()

        for _ in range(n_samples):
            dm = float(np.random.normal(0, sigma)) if perturb_camber else 0.0
            dt = float(np.random.normal(0, sigma)) if perturb_thickness else 0.0
            da = float(np.random.normal(0, alpha_std)) if perturb_alpha else 0.0
            m = max(0.0, m_nom + dm)
            t = max(0.04, t_nom + dt)
            a = alpha + da
            try:
                coords = self._naca4_coords(m, p_nom, t)
                r = self.predictor.predict(
                    coordinates=coords, alpha=a,
                    reynolds=reynolds_number, mach=mach_number,
                )
                if r["CD"] > 1e-6:
                    CLs.append(r["CL"])
                    L_Ds.append(r["L_D"])
                    d_ms.append(dm); d_ts.append(dt); d_as.append(da)
            except Exception:
                pass

        if not CLs:
            return {"status": "error", "message": "All samples failed"}

        CLs = np.array(CLs); L_Ds = np.array(L_Ds)
        d_ms = np.array(d_ms); d_ts = np.array(d_ts); d_as = np.array(d_as)

        def pct(arr):
            return {
                "p10": round(float(np.percentile(arr, 10)), 4),
                "p25": round(float(np.percentile(arr, 25)), 4),
                "p50": round(float(np.percentile(arr, 50)), 4),
                "p75": round(float(np.percentile(arr, 75)), 4),
                "p90": round(float(np.percentile(arr, 90)), 4),
                "mean": round(float(np.mean(arr)), 4),
                "std": round(float(np.std(arr)), 4),
            }

        def r2(x):
            if np.std(x) < 1e-10:
                return 0.0
            return float(np.corrcoef(x, CLs)[0, 1] ** 2)

        raw_sens = {}
        if perturb_camber:   raw_sens["camber"]    = r2(d_ms)
        if perturb_thickness: raw_sens["thickness"] = r2(d_ts)
        if perturb_alpha:    raw_sens["alpha"]     = r2(d_as)
        total = sum(raw_sens.values()) or 1
        sensitivity = {k: round(v / total * 100, 1) for k, v in raw_sens.items()}

        # Nearby unexplored NACA codes (high-value experiments)
        candidates = []
        for dm in range(-3, 4):
            for dt in range(-3, 4):
                new_m = max(0, int(round(m_nom * 100)) + dm)
                new_t = max(4, min(21, int(round(t_nom * 100)) + dt))
                p_d = int(p_nom * 10) if m_nom > 0 else 0
                nc = f"{new_m}{p_d}{new_t:02d}"
                if nc == code or len(nc) != 4:
                    continue
                try:
                    coords = create_naca_airfoil(nc)
                    r = self.predictor.predict(
                        coordinates=coords, alpha=alpha,
                        reynolds=reynolds_number, mach=mach_number,
                    )
                    if r["CD"] > 1e-6:
                        candidates.append({
                            "airfoil": nc,
                            "CL": round(r["CL"], 4),
                            "CD": round(r["CD"], 6),
                            "L_D": round(r["L_D"], 2),
                        })
                except Exception:
                    pass
        candidates.sort(key=lambda x: (x["L_D"] or 0), reverse=True)

        return {
            "status": "success",
            "airfoil": code,
            "n_samples": len(CLs),
            "time_ms": round((time.time() - start) * 1000, 1),
            "alpha": alpha,
            "reynolds": reynolds_number,
            "distributions": {"CL": pct(CLs), "L_D": pct(L_Ds)},
            "sensitivity": sensitivity,
            "high_value_experiments": candidates[:5],
        }

    def _explain_concept(self, topic: str) -> Dict[str, Any]:
        """Return the topic for the LLM to explain (LLM handles the actual explanation)."""
        return {
            "status": "success",
            "topic": topic,
            "note": "The LLM will explain this aerodynamic concept."
        }
