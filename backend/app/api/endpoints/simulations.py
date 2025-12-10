"""
Simulation API endpoints using NeuralFoil for real CFD predictions
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import numpy as np

from app.utils.neuralfoil_wrapper import (
    get_predictor,
    create_naca_airfoil,
    create_custom_airfoil,
    get_preset_coordinates,
    PRESETS
)

router = APIRouter()


class SimulationRequest(BaseModel):
    """Request model for CFD simulation"""
    # Airfoil definition
    airfoil_type: str = Field(..., description="Type: 'naca', 'custom', or 'preset'")
    naca_designation: Optional[str] = Field(None, description="NACA 4-digit code (e.g., '0012')")
    preset_name: Optional[str] = Field(None, description="Preset name from available presets")
    camber: Optional[float] = Field(None, ge=0, le=0.15, description="Custom camber (0-0.15)")
    thickness: Optional[float] = Field(None, ge=0.05, le=0.25, description="Custom thickness (0.05-0.25)")
    coordinates: Optional[List[List[float]]] = Field(None, description="Custom (x,y) coordinates")

    # Flow conditions
    alpha: float = Field(5.0, ge=-20, le=30, description="Angle of attack (degrees)")
    reynolds: float = Field(1e6, ge=1e4, le=1e7, description="Reynolds number")
    mach: float = Field(0.0, ge=0, le=0.3, description="Mach number (currently unused)")


class SimulationResponse(BaseModel):
    """Response model for CFD simulation"""
    CL: float
    CD: float
    CM: float
    L_D: float
    converged: bool
    time_ms: float
    solver: str
    coordinates: List[List[float]]


class PolarRequest(BaseModel):
    """Request model for polar curve generation"""
    airfoil_type: str
    naca_designation: Optional[str] = None
    preset_name: Optional[str] = None
    camber: Optional[float] = None
    thickness: Optional[float] = None

    alpha_min: float = Field(0.0, description="Minimum angle of attack")
    alpha_max: float = Field(15.0, description="Maximum angle of attack")
    alpha_step: float = Field(1.0, description="Step size in degrees")
    reynolds: float = Field(1e6, ge=1e4, le=1e7)


class OptimizationRequest(BaseModel):
    """Request model for L/D optimization"""
    airfoil_type: str
    naca_designation: Optional[str] = None
    preset_name: Optional[str] = None
    camber: Optional[float] = None
    thickness: Optional[float] = None

    alpha: float = Field(5.0)
    reynolds: float = Field(1e6)
    n_iterations: int = Field(10, ge=5, le=50)


def get_airfoil_coordinates(request) -> np.ndarray:
    """
    Extract airfoil coordinates from request

    Args:
        request: SimulationRequest, PolarRequest, or OptimizationRequest

    Returns:
        Numpy array of (x,y) coordinates
    """
    if request.airfoil_type == 'naca':
        if not request.naca_designation:
            raise HTTPException(400, "NACA designation required for airfoil_type='naca'")
        return create_naca_airfoil(request.naca_designation)

    elif request.airfoil_type == 'preset':
        if not request.preset_name:
            raise HTTPException(400, "preset_name required for airfoil_type='preset'")
        if request.preset_name not in PRESETS:
            raise HTTPException(400, f"Unknown preset. Available: {list(PRESETS.keys())}")
        return get_preset_coordinates(request.preset_name)

    elif request.airfoil_type == 'custom':
        if hasattr(request, 'coordinates') and request.coordinates:
            return np.array(request.coordinates, dtype=np.float32)
        elif request.camber is not None and request.thickness is not None:
            return create_custom_airfoil(request.camber, request.thickness)
        else:
            raise HTTPException(400, "Custom airfoil requires either 'coordinates' or 'camber' + 'thickness'")

    else:
        raise HTTPException(400, f"Invalid airfoil_type. Must be 'naca', 'preset', or 'custom'")


@router.post("/run", response_model=SimulationResponse)
async def run_simulation(request: SimulationRequest):
    """
    Run CFD simulation using NeuralFoil

    Example request:
    ```json
    {
        "airfoil_type": "naca",
        "naca_designation": "2412",
        "alpha": 8.0,
        "reynolds": 1000000
    }
    ```
    """
    try:
        # Get airfoil coordinates
        coordinates = get_airfoil_coordinates(request)

        # Get predictor instance
        predictor = get_predictor()

        # Run prediction
        result = predictor.predict(
            coordinates=coordinates,
            alpha=request.alpha,
            reynolds=request.reynolds,
            mach=request.mach
        )

        # Add coordinates to response
        result['coordinates'] = coordinates.tolist()

        return SimulationResponse(**result)

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Simulation failed: {str(e)}")


@router.post("/polar")
async def generate_polar(request: PolarRequest):
    """
    Generate polar curve (CL vs alpha)

    Example request:
    ```json
    {
        "airfoil_type": "preset",
        "preset_name": "naca0012",
        "alpha_min": 0,
        "alpha_max": 15,
        "alpha_step": 1.0,
        "reynolds": 1000000
    }
    ```
    """
    try:
        coordinates = get_airfoil_coordinates(request)
        predictor = get_predictor()

        results = predictor.predict_polar(
            coordinates=coordinates,
            alpha_range=(request.alpha_min, request.alpha_max),
            alpha_step=request.alpha_step,
            reynolds=request.reynolds
        )

        return {
            "polar_data": results,
            "coordinates": coordinates.tolist()
        }

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Polar generation failed: {str(e)}")


@router.post("/optimize")
async def optimize_airfoil(request: OptimizationRequest):
    """
    Optimize airfoil for maximum L/D ratio

    Example request:
    ```json
    {
        "airfoil_type": "naca",
        "naca_designation": "0012",
        "alpha": 5.0,
        "reynolds": 1000000,
        "n_iterations": 10
    }
    ```
    """
    try:
        coordinates = get_airfoil_coordinates(request)
        predictor = get_predictor()

        result = predictor.optimize_for_ld(
            base_coordinates=coordinates,
            reynolds=request.reynolds,
            alpha=request.alpha,
            n_iterations=request.n_iterations
        )

        return result

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Optimization failed: {str(e)}")


@router.get("/presets")
async def list_presets():
    """List available preset airfoils"""
    return {
        "presets": list(PRESETS.keys()),
        "examples": {
            "naca0012": "Symmetric, 12% thick",
            "naca2412": "2% camber, 12% thick",
            "naca4412": "4% camber, 12% thick",
            "baseline": "Custom baseline design",
            "high_lift": "High camber for max lift",
            "low_drag": "Low thickness for efficiency"
        }
    }


@router.get("/health")
async def health_check():
    """Check if NeuralFoil is initialized and ready"""
    try:
        predictor = get_predictor()
        # Run quick test
        test_coords = create_naca_airfoil("0012")
        result = predictor.predict(test_coords, alpha=5.0, reynolds=1e6)

        return {
            "status": "healthy",
            "solver": "NeuralFoil",
            "version": "0.3.2",
            "test_latency_ms": result['time_ms']
        }
    except Exception as e:
        raise HTTPException(500, f"Health check failed: {str(e)}")
