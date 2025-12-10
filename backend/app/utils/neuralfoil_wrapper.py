"""
NeuralFoil CFD Wrapper
Fast neural network-based airfoil performance prediction
"""
import numpy as np
from neuralfoil.main import get_aero_from_coordinates
from typing import Dict, Optional, List, Tuple
import time


def to_float(val) -> float:
    """Convert numpy types to Python float"""
    return float(val.item()) if isinstance(val, np.ndarray) else float(val)


def create_naca_airfoil(designation: str = "0012", n_points: int = 100) -> np.ndarray:
    """
    Generate NACA 4-digit airfoil coordinates
    
    Args:
        designation: NACA 4-digit code (e.g., "0012", "2412")
        n_points: Number of points per surface
        
    Returns:
        Numpy array of (x, y) coordinates
    """
    if len(designation) != 4:
        raise ValueError("NACA designation must be 4 digits")
    
    m = int(designation[0]) / 100  # Maximum camber
    p = int(designation[1]) / 10   # Location of maximum camber
    t = int(designation[2:4]) / 100  # Thickness
    
    # Cosine spacing for better resolution near leading edge
    beta = np.linspace(0, np.pi, n_points)
    x = (1 - np.cos(beta)) / 2
    
    # Thickness distribution
    yt = 5 * t * (
        0.2969 * np.sqrt(x) - 
        0.1260 * x - 
        0.3516 * x**2 + 
        0.2843 * x**3 - 
        0.1015 * x**4
    )
    
    # Camber line
    if m == 0 or p == 0:  # Symmetric airfoil
        yc = np.zeros_like(x)
    else:
        yc = np.where(
            x < p,
            m / p**2 * (2 * p * x - x**2),
            m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * x - x**2)
        )
    
    # Upper and lower surfaces
    y_upper = yc + yt
    y_lower = yc - yt
    
    # Combine into single array (clockwise from trailing edge)
    coords = np.vstack([
        np.column_stack([x, y_upper]),
        np.column_stack([x[::-1], y_lower[::-1]])
    ])
    
    return coords.astype(np.float32)


def create_custom_airfoil(camber: float = 0.04, thickness: float = 0.12, n_points: int = 100) -> np.ndarray:
    """
    Generate custom airfoil with specified camber and thickness
    
    Args:
        camber: Maximum camber (0-0.1 typical)
        thickness: Maximum thickness (0.08-0.18 typical)
        n_points: Number of points
        
    Returns:
        Numpy array of coordinates
    """
    x = np.linspace(0, 1, n_points)
    
    # Thickness distribution
    y_upper = thickness * np.sqrt(x) * (1 - x) + camber * x * (1 - x)
    y_lower = -thickness * 0.4 * np.sqrt(x) * (1 - x) + camber * 0.3 * x * (1 - x)
    
    coords = np.vstack([
        np.column_stack([x, y_upper]),
        np.column_stack([x[::-1], y_lower[::-1]])
    ])
    
    return coords.astype(np.float32)


class NeuralFoilPredictor:
    """Fast CFD predictions using NeuralFoil neural network"""
    
    def __init__(self):
        """Initialize and warm up the model"""
        print("🚀 Initializing NeuralFoil 0.3.2...")
        self._warmup()
        print("✅ NeuralFoil ready! Average latency: 3-5ms")
    
    def _warmup(self):
        """Warm up the model with a dummy prediction"""
        coords = create_naca_airfoil("0012")
        get_aero_from_coordinates(coords, alpha=5.0, Re=1e6)
    
    def predict(
        self,
        coordinates: np.ndarray,
        alpha: float = 5.0,
        reynolds: float = 1e6,
        mach: float = 0.0
    ) -> Dict:
        """
        Run CFD prediction
        
        Args:
            coordinates: Airfoil (x,y) coordinates
            alpha: Angle of attack in degrees
            reynolds: Reynolds number
            mach: Mach number (currently ignored by NeuralFoil)
            
        Returns:
            Dictionary with CL, CD, CM, L/D, and timing
        """
        start_time = time.time()
        
        # Ensure correct format
        if not isinstance(coordinates, np.ndarray):
            coordinates = np.array(coordinates, dtype=np.float32)
        
        # Call NeuralFoil
        result = get_aero_from_coordinates(
            coordinates=coordinates,
            alpha=float(alpha),
            Re=float(reynolds)
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Extract coefficients
        CL = to_float(result['CL'])
        CD = to_float(result['CD'])
        CM = to_float(result['CM'])
        
        return {
            'CL': CL,
            'CD': CD,
            'CM': CM,
            'L_D': CL / CD if CD != 0 else 0,
            'converged': True,  # NeuralFoil always converges
            'time_ms': round(elapsed_ms, 1),
            'solver': 'NeuralFoil'
        }
    
    def predict_polar(
        self,
        coordinates: np.ndarray,
        alpha_range: Tuple[float, float] = (0, 15),
        alpha_step: float = 1.0,
        reynolds: float = 1e6
    ) -> List[Dict]:
        """
        Generate polar (CL vs alpha curve)
        
        Args:
            coordinates: Airfoil coordinates
            alpha_range: (min_alpha, max_alpha)
            alpha_step: Step size in degrees
            reynolds: Reynolds number
            
        Returns:
            List of results for each alpha
        """
        alphas = np.arange(alpha_range[0], alpha_range[1] + alpha_step, alpha_step)
        results = []
        
        for alpha in alphas:
            result = self.predict(coordinates, alpha=alpha, reynolds=reynolds)
            result['alpha'] = float(alpha)
            results.append(result)
        
        return results
    
    def optimize_for_ld(
        self,
        base_coordinates: np.ndarray,
        reynolds: float = 1e6,
        alpha: float = 5.0,
        n_iterations: int = 10
    ) -> Dict:
        """
        Simple optimization to maximize L/D ratio
        
        Args:
            base_coordinates: Starting airfoil
            reynolds: Reynolds number
            alpha: Angle of attack
            n_iterations: Number of thickness variations to try
            
        Returns:
            Best configuration and coordinates
        """
        current_perf = self.predict(base_coordinates, alpha=alpha, reynolds=reynolds)
        
        best_coords = base_coordinates
        best_perf = current_perf
        best_ld = current_perf['L_D']
        
        # Try thickness variations
        for factor in np.linspace(0.8, 1.2, n_iterations):
            variant = base_coordinates.copy()
            variant[:, 1] *= factor  # Scale y-coordinates
            
            perf = self.predict(variant, alpha=alpha, reynolds=reynolds)
            
            if perf['L_D'] > best_ld:
                best_ld = perf['L_D']
                best_perf = perf
                best_coords = variant
        
        improvement_pct = ((best_ld / current_perf['L_D']) - 1) * 100 if current_perf['L_D'] != 0 else 0
        
        return {
            'before': current_perf,
            'after': best_perf,
            'improvement_percent': round(improvement_pct, 1),
            'optimized_coordinates': best_coords.tolist()
        }


# Global instance (initialized once)
_predictor = None

def get_predictor() -> NeuralFoilPredictor:
    """Get or create global predictor instance"""
    global _predictor
    if _predictor is None:
        _predictor = NeuralFoilPredictor()
    return _predictor


# Preset airfoils
PRESETS = {
    'naca0012': lambda: create_naca_airfoil("0012"),
    'naca2412': lambda: create_naca_airfoil("2412"),
    'naca4412': lambda: create_naca_airfoil("4412"),
    'naca0015': lambda: create_naca_airfoil("0015"),
    'baseline': lambda: create_custom_airfoil(0.04, 0.12),
    'high_lift': lambda: create_custom_airfoil(0.08, 0.12),
    'low_drag': lambda: create_custom_airfoil(0.02, 0.10),
    'thick': lambda: create_custom_airfoil(0.04, 0.18),
}


def get_preset_coordinates(preset_name: str) -> np.ndarray:
    """Get coordinates for a preset airfoil"""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    return PRESETS[preset_name]()
