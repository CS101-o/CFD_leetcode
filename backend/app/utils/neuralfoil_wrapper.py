import numpy as np
from typing import Dict

def get_predictor():
    from neuralfoil import get_aero_from_coordinates
    return NeuralFoilPredictor()

class NeuralFoilPredictor:
    def predict(self, coordinates, alpha, reynolds, mach=0.0) -> Dict:
        from neuralfoil import get_aero_from_coordinates
        import time
        start = time.time()
        result = get_aero_from_coordinates(coordinates=coordinates, alpha=alpha, Re=reynolds, mach=mach)
        elapsed_ms = (time.time() - start) * 1000
        CL, CD = result['CL'], result['CD']
        return {'CL': CL, 'CD': CD, 'CM': result.get('CM', 0.0), 'L_D': CL/CD if CD>0 else 0, 'time_ms': elapsed_ms, 'converged': True}

def create_naca_airfoil(designation: str, n_points: int = 100) -> np.ndarray:
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
        yc = np.where(x<p, m/p**2*(2*p*x-x**2), m/(1-p)**2*((1-2*p)+2*p*x-x**2))
        dyc_dx = np.where(x<p, 2*m/p**2*(p-x), 2*m/(1-p)**2*(p-x))
    theta = np.arctan(dyc_dx)
    xu = x - yt*np.sin(theta)
    yu = yc + yt*np.cos(theta)
    xl = x + yt*np.sin(theta)
    yl = yc - yt*np.cos(theta)
    return np.column_stack([np.concatenate([xu[::-1],xl[1:]]), np.concatenate([yu[::-1],yl[1:]])])
