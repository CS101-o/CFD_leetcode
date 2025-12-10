"""
XFoil Wrapper for AirfoilLearner
Handles XFoil subprocess execution and result parsing
"""

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class XFoilResults:
    """Container for XFoil simulation results"""
    alpha: float
    cl: float
    cd: float
    cdp: float  # Pressure drag coefficient
    cm: float  # Moment coefficient
    top_xtr: float  # Top transition point
    bot_xtr: float  # Bottom transition point
    converged: bool
    cp_distribution: Optional[np.ndarray] = None  # [x, y, Cp]
    bl_data: Optional[Dict] = None  # Boundary layer data


class XFoilWrapper:
    """
    Wrapper class for XFoil inviscid and viscous airfoil analysis

    XFoil must be installed and accessible in PATH or specified via xfoil_path
    Download: https://web.mit.edu/drela/Public/web/xfoil/
    """

    def __init__(
        self,
        xfoil_path: str = "xfoil",
        max_iter: int = 100,
        timeout: int = 60
    ):
        self.xfoil_path = xfoil_path
        self.max_iter = max_iter
        self.timeout = timeout

        # Verify XFoil is available
        if not self._check_xfoil():
            raise RuntimeError(
                f"XFoil not found at {xfoil_path}. "
                "Please install XFoil or specify correct path."
            )

    def _check_xfoil(self) -> bool:
        """Check if XFoil executable is available"""
        try:
            result = subprocess.run(
                [self.xfoil_path],
                input=b"\nquit\n",
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0 or "XFOIL" in result.stdout.decode()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def run_analysis(
        self,
        airfoil_coords: np.ndarray,
        alpha: float,
        reynolds: float = 1e6,
        mach: float = 0.0,
        n_crit: float = 9.0,
        viscous: bool = True
    ) -> XFoilResults:
        """
        Run XFoil analysis for a single angle of attack

        Args:
            airfoil_coords: Nx2 array of [x, y] coordinates (leading edge first)
            alpha: Angle of attack in degrees
            reynolds: Reynolds number
            mach: Mach number
            n_crit: Critical amplification factor (9.0 for wind tunnel, 5.0 for flight)
            viscous: Enable viscous analysis (if False, uses inviscid)

        Returns:
            XFoilResults object with simulation data
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Write airfoil coordinates to file
            airfoil_file = tmpdir_path / "airfoil.dat"
            self._write_airfoil_file(airfoil_coords, airfoil_file)

            # Prepare output files
            polar_file = tmpdir_path / "polar.txt"
            cp_file = tmpdir_path / "cp.txt"

            # Generate XFoil command script
            commands = self._generate_commands(
                airfoil_file=str(airfoil_file),
                polar_file=str(polar_file),
                cp_file=str(cp_file),
                alpha=alpha,
                reynolds=reynolds,
                mach=mach,
                n_crit=n_crit,
                viscous=viscous
            )

            # Run XFoil
            try:
                result = subprocess.run(
                    [self.xfoil_path],
                    input=commands.encode(),
                    capture_output=True,
                    timeout=self.timeout,
                    cwd=tmpdir
                )

                # Parse results
                return self._parse_results(
                    polar_file=polar_file,
                    cp_file=cp_file,
                    stdout=result.stdout.decode(),
                    alpha=alpha
                )

            except subprocess.TimeoutExpired:
                return XFoilResults(
                    alpha=alpha,
                    cl=0.0,
                    cd=0.0,
                    cdp=0.0,
                    cm=0.0,
                    top_xtr=0.0,
                    bot_xtr=0.0,
                    converged=False
                )

    def run_polar(
        self,
        airfoil_coords: np.ndarray,
        alpha_start: float,
        alpha_end: float,
        alpha_step: float = 0.5,
        reynolds: float = 1e6,
        mach: float = 0.0,
        n_crit: float = 9.0,
        viscous: bool = True
    ) -> List[XFoilResults]:
        """
        Run XFoil polar analysis over a range of angles of attack

        Returns:
            List of XFoilResults for each converged angle
        """
        results = []
        alpha_range = np.arange(alpha_start, alpha_end + alpha_step, alpha_step)

        for alpha in alpha_range:
            result = self.run_analysis(
                airfoil_coords=airfoil_coords,
                alpha=alpha,
                reynolds=reynolds,
                mach=mach,
                n_crit=n_crit,
                viscous=viscous
            )
            if result.converged:
                results.append(result)

        return results

    def _write_airfoil_file(self, coords: np.ndarray, filepath: Path):
        """Write airfoil coordinates to XFoil format"""
        with open(filepath, 'w') as f:
            f.write("Airfoil\n")  # Name line
            for x, y in coords:
                f.write(f"{x:10.6f} {y:10.6f}\n")

    def _generate_commands(
        self,
        airfoil_file: str,
        polar_file: str,
        cp_file: str,
        alpha: float,
        reynolds: float,
        mach: float,
        n_crit: float,
        viscous: bool
    ) -> str:
        """Generate XFoil command script"""
        commands = [
            f"LOAD {airfoil_file}",  # Load airfoil
            "",  # Confirm name
            "PANE",  # Re-panel for better distribution
        ]

        if viscous:
            commands.extend([
                "OPER",
                f"VISC {reynolds}",  # Enable viscous mode
                f"M {mach}",  # Set Mach number
                f"VPAR",
                f"N {n_crit}",  # Set N_crit
                "",  # Exit VPAR
                f"ITER {self.max_iter}",  # Set max iterations
            ])
        else:
            commands.append("OPER")

        commands.extend([
            f"ALFA {alpha}",  # Set angle of attack
            f"CPWR {cp_file}",  # Write Cp distribution
            f"PWRT",  # Write polar to file
            f"{polar_file}",
            "",  # Overwrite if exists
            "QUIT"
        ])

        return "\n".join(commands) + "\n"

    def _parse_results(
        self,
        polar_file: Path,
        cp_file: Path,
        stdout: str,
        alpha: float
    ) -> XFoilResults:
        """Parse XFoil output files"""

        # Check convergence from stdout
        converged = "VISCAL:  Convergence failed" not in stdout

        # Parse polar file
        if polar_file.exists() and converged:
            polar_data = self._parse_polar_file(polar_file)
            if polar_data:
                cl, cd, cdp, cm, top_xtr, bot_xtr = polar_data
            else:
                converged = False
                cl = cd = cdp = cm = top_xtr = bot_xtr = 0.0
        else:
            converged = False
            cl = cd = cdp = cm = top_xtr = bot_xtr = 0.0

        # Parse Cp distribution
        cp_distribution = None
        if cp_file.exists() and converged:
            cp_distribution = self._parse_cp_file(cp_file)

        return XFoilResults(
            alpha=alpha,
            cl=cl,
            cd=cd,
            cdp=cdp,
            cm=cm,
            top_xtr=top_xtr,
            bot_xtr=bot_xtr,
            converged=converged,
            cp_distribution=cp_distribution
        )

    def _parse_polar_file(self, filepath: Path) -> Optional[Tuple[float, ...]]:
        """Parse polar file to extract aerodynamic coefficients"""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()

            # Find data line (skip header)
            for line in lines:
                if line.strip() and not line.startswith('-'):
                    # Format: alpha CL CD CDp CM Top_Xtr Bot_Xtr
                    parts = line.split()
                    if len(parts) >= 7:
                        _, cl, cd, cdp, cm, top_xtr, bot_xtr = map(float, parts[:7])
                        return cl, cd, cdp, cm, top_xtr, bot_xtr
        except Exception as e:
            print(f"Error parsing polar file: {e}")

        return None

    def _parse_cp_file(self, filepath: Path) -> Optional[np.ndarray]:
        """Parse Cp distribution file"""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()

            # Skip header lines
            data_lines = [l for l in lines if not l.strip().startswith('#')]

            # Parse x, y, Cp columns
            data = []
            for line in data_lines:
                parts = line.split()
                if len(parts) >= 3:
                    x, y, cp = map(float, parts[:3])
                    data.append([x, y, cp])

            return np.array(data) if data else None

        except Exception as e:
            print(f"Error parsing Cp file: {e}")
            return None


def test_xfoil():
    """Test XFoil wrapper with NACA 0012 airfoil"""
    from .naca_generator import generate_naca_4digit

    # Generate NACA 0012
    coords = generate_naca_4digit("0012", num_points=100)

    # Initialize wrapper
    xfoil = XFoilWrapper()

    # Run single analysis
    print("Running XFoil analysis for NACA 0012 at α=5°, Re=1e6...")
    result = xfoil.run_analysis(
        airfoil_coords=coords,
        alpha=5.0,
        reynolds=1e6,
        viscous=True
    )

    print(f"Results:")
    print(f"  Converged: {result.converged}")
    print(f"  CL: {result.cl:.4f}")
    print(f"  CD: {result.cd:.6f}")
    print(f"  CM: {result.cm:.4f}")
    print(f"  L/D: {result.cl/result.cd:.2f}")

    # Run polar
    print("\nRunning polar sweep from -5° to 15°...")
    results = xfoil.run_polar(
        airfoil_coords=coords,
        alpha_start=-5.0,
        alpha_end=15.0,
        alpha_step=1.0,
        reynolds=1e6,
        viscous=True
    )

    print(f"Converged for {len(results)} angles")
    print(f"Max CL: {max(r.cl for r in results):.4f}")
    print(f"Min CD: {min(r.cd for r in results):.6f}")


if __name__ == "__main__":
    test_xfoil()
