import numpy as np
import time
from typing import Dict, List, Tuple, Any

class NeuralFoilPredictor:
    def predict(self, coordinates, alpha, reynolds, mach=0.0) -> Dict[str, Any]:
        """Predicts aerodynamic performance using NeuralFoil."""
        try:
            from neuralfoil import get_aero_from_coordinates
        except ImportError:
            from neuralfoil.main import get_aero_from_coordinates

        alpha_val = float(alpha)
        reynolds_val = float(reynolds)
        
        if not isinstance(coordinates, np.ndarray):
            coords_array = np.array(coordinates, dtype=np.float32)
        else:
            coords_array = coordinates.astype(np.float32)

        start = time.time()
        result = get_aero_from_coordinates(
            coordinates=coords_array,
            alpha=alpha_val,
            Re=reynolds_val
        )
        elapsed_ms = (time.time() - start) * 1000

        def to_float(val):
            return float(val.item()) if hasattr(val, 'item') else float(val)

        cl = to_float(result['CL'])
        cd = to_float(result['CD'])
        cm = to_float(result['CM'])

        return {
            'CL': cl,
            'CD': cd,
            'CM': cm,
            'L_D': cl / cd if cd > 1e-6 else 0.0,
            'time_ms': elapsed_ms,
            'converged': True,
            'solver': 'NeuralFoil'
        }
    
    def predict_polar(self, coordinates, alpha_range: Tuple[float, float], alpha_step: float, reynolds: float) -> List[Dict]:
        """Generate polar curve data"""
        results = []
        alpha_min, alpha_max = alpha_range
        alphas = np.arange(alpha_min, alpha_max + alpha_step, alpha_step)
        
        for alpha in alphas:
            result = self.predict(coordinates, alpha, reynolds)
            result['alpha'] = float(alpha)
            results.append(result)
        
        return results
    
    def optimize_for_ld(self, base_coordinates, reynolds: float, alpha: float, n_iterations: int) -> Dict:
        """Simple L/D optimization"""
        best_ld = 0
        best_result = None
        
        for test_alpha in np.linspace(alpha - 2, alpha + 2, n_iterations):
            result = self.predict(base_coordinates, test_alpha, reynolds)
            if result['L_D'] > best_ld:
                best_ld = result['L_D']
                best_result = result.copy()
                best_result['alpha'] = float(test_alpha)
        
        return {
            'best_alpha': best_result['alpha'],
            'best_L_D': best_ld,
            'CL': best_result['CL'],
            'CD': best_result['CD'],
            'coordinates': base_coordinates.tolist()
        }

def get_predictor():
    return NeuralFoilPredictor()

def create_naca_airfoil(designation: str, n_points: int = 100) -> np.ndarray:
    """Generates coordinates for a NACA 4-digit airfoil."""
    if not designation or len(designation) != 4:
        designation = "0012"

    m = int(designation[0]) / 100
    p = int(designation[1]) / 10
    t = int(designation[2:4]) / 100

    beta = np.linspace(0, np.pi, n_points // 2)
    x = (1 - np.cos(beta)) / 2
    yt = 5*t*(0.2969*np.sqrt(x)-0.1260*x-0.3516*x**2+0.2843*x**3-0.1015*x**4)
    
    if p == 0:
        yc = np.zeros_like(x)
        dyc_dx = np.zeros_like(x)
    else:
        yc = np.where(x < p, m/p**2*(2*p*x-x**2), m/(1-p)**2*((1-2*p)+2*p*x-x**2))
        dyc_dx = np.where(x < p, 2*m/p**2*(p-x), 2*m/(1-p)**2*(p-x))
    
    theta = np.arctan(dyc_dx)
    xu = x - yt*np.sin(theta)
    yu = yc + yt*np.cos(theta)
    xl = x + yt*np.sin(theta)
    yl = yc - yt*np.cos(theta)
    
    upper = np.column_stack((xu[::-1], yu[::-1]))
    lower = np.column_stack((xl[1:], yl[1:]))
    
    return np.concatenate([upper, lower])

def create_custom_airfoil(camber: float = 0.04, thickness: float = 0.12, n_points: int = 100) -> np.ndarray:
    """Generates a simple custom airfoil."""
    m = camber
    p = 0.4
    t = thickness
    
    beta = np.linspace(0, np.pi, n_points // 2)
    x = (1 - np.cos(beta)) / 2
    yt = 5*t*(0.2969*np.sqrt(x)-0.1260*x-0.3516*x**2+0.2843*x**3-0.1015*x**4)
    
    if m == 0:
        yc = np.zeros_like(x)
        dyc_dx = np.zeros_like(x)
    else:
        yc = np.where(x<p, m/p**2*(2*p*x-x**2), m/(1-p)**2*((1-2*p)+2*p*x-x**2))
        dyc_dx = np.where(x<p, 2*m/p**2*(p-x), 2*m/(1-p)**2*(p-x))
    
    theta = np.arctan(dyc_dx)
    xu = x - yt*np.sin(theta)
    yu = yc + yt*np.cos(theta)
    xl = x + yt*np.sin(theta)
    yl = yc - yt*np.cos(theta)
    return np.column_stack([np.concatenate([xu[::-1],xl[1:]]), np.concatenate([yu[::-1],yl[1:]])])

def get_preset_coordinates(preset_name: str) -> np.ndarray:
    """Returns coordinates for a known preset name."""
    preset_name = preset_name.lower().strip()
    
    if preset_name in PRESETS:
        return PRESETS[preset_name]()
    
    if preset_name.startswith('naca'):
        code = preset_name.replace('naca', '')
        if len(code) == 4 and code.isdigit():
            return create_naca_airfoil(code)
            
    return create_naca_airfoil("0012")

PRESETS = {
    'naca0012': lambda: create_naca_airfoil("0012"),
    'naca2412': lambda: create_naca_airfoil("2412"),
    'naca4412': lambda: create_naca_airfoil("4412"),
    'baseline': lambda: create_naca_airfoil("2412"),
    'high_lift': lambda: create_custom_airfoil(camber=0.08, thickness=0.12),
    'low_drag': lambda: create_naca_airfoil("0009"),
}