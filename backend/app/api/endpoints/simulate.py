"""
Direct simulation endpoints — no LLM, NeuralFoil only.
Used by all non-chat interaction modes (sliders, table, pareto, target search).
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List

from app.utils.neuralfoil_wrapper import get_predictor, create_naca_airfoil
from app.services.session_logger import log_event
from app.services.tool_executor import ToolExecutor

router = APIRouter()
_predictor = get_predictor()
_executor = ToolExecutor()


def _run(airfoil: str, alpha: float, reynolds: float, mach: float = 0.0) -> dict:
    coords = create_naca_airfoil(airfoil)
    r = _predictor.predict(coordinates=coords, alpha=alpha, reynolds=reynolds, mach=mach)
    return {
        "airfoil": airfoil,
        "alpha": alpha,
        "reynolds": reynolds,
        "CL": round(r["CL"], 6),
        "CD": round(r["CD"], 6),
        "CM": round(r["CM"], 6),
        "L_D": round(r["L_D"], 2) if r["CD"] > 1e-6 else None,
        "coordinates": coords.tolist(),
    }


# ------------------------------------------------------------------
# Single point
# ------------------------------------------------------------------

class SingleRequest(BaseModel):
    airfoil: str = Field("2412", description="NACA 4-digit code")
    alpha: float = Field(0.0, ge=-20, le=30)
    reynolds: float = Field(1_000_000, ge=1e4, le=1e7)
    mach: float = Field(0.0, ge=0, le=0.8)
    session_id: Optional[str] = None
    participant_id: Optional[str] = None
    mode: Optional[str] = "slider"


@router.post("/single")
def simulate_single(req: SingleRequest):
    result = _run(req.airfoil, req.alpha, req.reynolds, req.mach)
    if req.session_id:
        log_event(req.session_id, "simulation_run", {
            "participant_id": req.participant_id or "unknown",
            "mode": req.mode,
            "airfoil": req.airfoil,
            "alpha": req.alpha,
            "reynolds": req.reynolds,
            "CL": result["CL"],
            "CD": result["CD"],
            "L_D": result["L_D"],
        })
    return result


# ------------------------------------------------------------------
# Polar sweep
# ------------------------------------------------------------------

class PolarRequest(BaseModel):
    airfoil: str = "2412"
    alpha_start: float = -5.0
    alpha_end: float = 15.0
    alpha_step: float = 1.0
    reynolds: float = 1_000_000
    mach: float = 0.0
    session_id: Optional[str] = None
    participant_id: Optional[str] = None
    mode: Optional[str] = "slider"


@router.post("/polar")
def simulate_polar(req: PolarRequest):
    import numpy as np
    coords = create_naca_airfoil(req.airfoil)
    polar = _predictor.predict_polar(
        coordinates=coords,
        alpha_range=(req.alpha_start, req.alpha_end),
        alpha_step=req.alpha_step,
        reynolds=req.reynolds,
        mach=req.mach,
    )
    points = [
        {
            "alpha": float(p["alpha"]),
            "CL": round(p["CL"], 6),
            "CD": round(p["CD"], 6),
            "L_D": round(p["L_D"], 2) if p.get("L_D") else None,
        }
        for p in polar
    ]
    if req.session_id:
        log_event(req.session_id, "polar_sweep", {
            "participant_id": req.participant_id or "unknown",
            "mode": req.mode,
            "airfoil": req.airfoil,
            "alpha_range": [req.alpha_start, req.alpha_end],
            "reynolds": req.reynolds,
            "n_points": len(points),
        })
    return {"airfoil": req.airfoil, "reynolds": req.reynolds, "points": points, "coordinates": coords.tolist()}


# ------------------------------------------------------------------
# Compare (design table)
# ------------------------------------------------------------------

class CompareEntry(BaseModel):
    airfoil: str
    alpha: float
    reynolds: float
    mach: float = 0.0


class CompareRequest(BaseModel):
    entries: List[CompareEntry]
    session_id: Optional[str] = None
    participant_id: Optional[str] = None


@router.post("/compare")
def simulate_compare(req: CompareRequest):
    results = []
    for e in req.entries:
        try:
            results.append(_run(e.airfoil, e.alpha, e.reynolds, e.mach))
        except Exception as ex:
            results.append({"airfoil": e.airfoil, "error": str(ex)})
    if req.session_id:
        log_event(req.session_id, "table_compare", {
            "participant_id": req.participant_id or "unknown",
            "mode": "table",
            "n_rows": len(req.entries),
            "airfoils": [e.airfoil for e in req.entries],
        })
    return {"results": results}


# ------------------------------------------------------------------
# Target search
# ------------------------------------------------------------------

class TargetRequest(BaseModel):
    target_LD: Optional[float] = None
    target_CL: Optional[float] = None
    alpha: float = 4.0
    reynolds: float = 1_000_000
    session_id: Optional[str] = None
    participant_id: Optional[str] = None


_SEARCH_AIRFOILS = [
    "0009","0012","0015","1412","2412","2415","2418",
    "4412","4415","4418","6412","6415","2312","2315",
    "3412","3415","5412","6409","6412",
]


@router.post("/target")
def simulate_target(req: TargetRequest):
    candidates = []
    for code in _SEARCH_AIRFOILS:
        try:
            r = _run(code, req.alpha, req.reynolds)
            score = 0.0
            if req.target_LD and r["L_D"]:
                score += min(r["L_D"] / req.target_LD, 1.0)
            if req.target_CL:
                score += min(r["CL"] / req.target_CL, 1.0)
            candidates.append({**r, "score": round(score, 4), "meets_LD": (r["L_D"] or 0) >= (req.target_LD or 0), "meets_CL": r["CL"] >= (req.target_CL or 0)})
        except Exception:
            pass
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top = candidates[:6]
    if req.session_id:
        log_event(req.session_id, "target_search", {
            "participant_id": req.participant_id or "unknown",
            "mode": "target",
            "target_LD": req.target_LD,
            "target_CL": req.target_CL,
            "alpha": req.alpha,
            "reynolds": req.reynolds,
            "top_result": top[0]["airfoil"] if top else None,
        })
    return {"results": top, "targets": {"L_D": req.target_LD, "CL": req.target_CL}}


# ------------------------------------------------------------------
# Monte Carlo
# ------------------------------------------------------------------

class MonteCarloRequest(BaseModel):
    airfoil: str = "2412"
    alpha: float = 4.0
    reynolds: float = 1_000_000
    mach: float = 0.0
    n_samples: int = Field(300, ge=50, le=2000)
    perturbation_pct: float = Field(1.0, ge=0.1, le=5.0)
    perturb_camber: bool = True
    perturb_thickness: bool = True
    perturb_alpha: bool = False
    alpha_std: float = Field(0.5, ge=0.1, le=5.0)
    session_id: Optional[str] = None
    participant_id: Optional[str] = None


@router.post("/montecarlo")
def simulate_montecarlo(req: MonteCarloRequest):
    result = _executor._run_monte_carlo(
        naca_designation=req.airfoil,
        alpha=req.alpha,
        reynolds_number=req.reynolds,
        mach_number=req.mach,
        n_samples=req.n_samples,
        perturbation_pct=req.perturbation_pct,
        perturb_camber=req.perturb_camber,
        perturb_thickness=req.perturb_thickness,
        perturb_alpha=req.perturb_alpha,
        alpha_std=req.alpha_std,
    )
    if req.session_id:
        log_event(req.session_id, "monte_carlo", {
            "participant_id": req.participant_id or "unknown",
            "mode": "montecarlo",
            "airfoil": req.airfoil,
            "n_samples": req.n_samples,
            "perturbation_pct": req.perturbation_pct,
            "perturb_camber": req.perturb_camber,
            "perturb_thickness": req.perturb_thickness,
            "perturb_alpha": req.perturb_alpha,
        })
    return result
