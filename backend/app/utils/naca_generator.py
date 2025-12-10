"""
NACA Airfoil Geometry Generator

Supports:
- NACA 4-digit series (e.g., 0012, 2412, 4412)
- NACA 5-digit series (e.g., 23012, 23112)
- Custom coordinate generation with variable resolution
"""

import numpy as np
from typing import Tuple


def generate_naca_4digit(
    designation: str,
    num_points: int = 100,
    cosine_spacing: bool = True
) -> np.ndarray:
    """
    Generate NACA 4-digit airfoil coordinates

    Args:
        designation: 4-digit NACA code (e.g., "0012", "2412")
        num_points: Number of points on upper/lower surfaces
        cosine_spacing: Use cosine spacing for better leading edge resolution

    Returns:
        Nx2 array of [x, y] coordinates (starting from TE top, going around to TE bottom)
    """
    if len(designation) != 4:
        raise ValueError("NACA 4-digit designation must be 4 digits")

    # Parse NACA designation
    m = int(designation[0]) / 100  # Maximum camber (as fraction of chord)
    p = int(designation[1]) / 10   # Location of maximum camber (as fraction of chord)
    t = int(designation[2:]) / 100  # Maximum thickness (as fraction of chord)

    # Generate x coordinates
    if cosine_spacing:
        # Cosine spacing for better resolution at LE and TE
        beta = np.linspace(0, np.pi, num_points)
        x = 0.5 * (1 - np.cos(beta))
    else:
        # Linear spacing
        x = np.linspace(0, 1, num_points)

    # Calculate thickness distribution using NACA formula
    yt = 5 * t * (
        0.2969 * np.sqrt(x) -
        0.1260 * x -
        0.3516 * x**2 +
        0.2843 * x**3 -
        0.1015 * x**4  # Original NACA (sharp TE)
        # 0.1036 * x**4  # Modified for closed TE
    )

    # Calculate camber line
    if m == 0:
        # Symmetric airfoil
        yc = np.zeros_like(x)
        dyc_dx = np.zeros_like(x)
    else:
        # Cambered airfoil
        yc = np.where(
            x < p,
            m / p**2 * (2 * p * x - x**2),
            m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * x - x**2)
        )

        dyc_dx = np.where(
            x < p,
            2 * m / p**2 * (p - x),
            2 * m / (1 - p)**2 * (p - x)
        )

    # Calculate upper and lower surface coordinates
    theta = np.arctan(dyc_dx)

    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)

    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    # Combine coordinates (upper surface + lower surface reversed)
    # XFoil expects: start at TE (top), go around LE, end at TE (bottom)
    x_coords = np.concatenate([xu[::-1], xl[1:]])
    y_coords = np.concatenate([yu[::-1], yl[1:]])

    return np.column_stack([x_coords, y_coords])


def generate_naca_5digit(
    designation: str,
    num_points: int = 100,
    cosine_spacing: bool = True
) -> np.ndarray:
    """
    Generate NACA 5-digit airfoil coordinates

    Args:
        designation: 5-digit NACA code (e.g., "23012")
        num_points: Number of points on upper/lower surfaces
        cosine_spacing: Use cosine spacing for better leading edge resolution

    Returns:
        Nx2 array of [x, y] coordinates
    """
    if len(designation) != 5:
        raise ValueError("NACA 5-digit designation must be 5 digits")

    # Parse designation
    cl_ideal = int(designation[0]) * 3 / 20  # Design lift coefficient
    p = int(designation[1]) / 20  # Position of maximum camber
    reflex = designation[2] == '1'  # Reflex camber flag
    t = int(designation[3:]) / 100  # Thickness

    # Generate x coordinates
    if cosine_spacing:
        beta = np.linspace(0, np.pi, num_points)
        x = 0.5 * (1 - np.cos(beta))
    else:
        x = np.linspace(0, 1, num_points)

    # Thickness distribution (same as 4-digit)
    yt = 5 * t * (
        0.2969 * np.sqrt(x) -
        0.1260 * x -
        0.3516 * x**2 +
        0.2843 * x**3 -
        0.1015 * x**4
    )

    # Mean camber line parameters (standard NACA 5-digit)
    if not reflex:
        # Standard camber
        m = 0.0580  # Scaling factor
        k1 = 361.4

        yc = np.where(
            x < p,
            k1 / 6 * (x**3 - 3 * m * x**2 + m**2 * (3 - m) * x),
            k1 / 6 * m**3 * (1 - x)
        )

        dyc_dx = np.where(
            x < p,
            k1 / 6 * (3 * x**2 - 6 * m * x + m**2 * (3 - m)),
            -k1 / 6 * m**3 * np.ones_like(x)
        )
    else:
        # Reflex camber (simplified)
        yc = np.zeros_like(x)
        dyc_dx = np.zeros_like(x)

    # Scale camber by design CL
    yc = yc * cl_ideal / 0.3

    # Calculate surface coordinates
    theta = np.arctan(dyc_dx)

    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)

    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    x_coords = np.concatenate([xu[::-1], xl[1:]])
    y_coords = np.concatenate([yu[::-1], yl[1:]])

    return np.column_stack([x_coords, y_coords])


def load_custom_airfoil(filepath: str) -> np.ndarray:
    """
    Load airfoil coordinates from file

    Supports Selig and Lednicer formats:
    - Selig: Name line, then x y pairs (upper then lower)
    - Lednicer: Name line, blank line, upper surface, blank line, lower surface

    Args:
        filepath: Path to airfoil coordinate file

    Returns:
        Nx2 array of [x, y] coordinates
    """
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Skip name line
    lines = [l.strip() for l in lines[1:] if l.strip() and not l.startswith('#')]

    coords = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            try:
                x, y = float(parts[0]), float(parts[1])
                coords.append([x, y])
            except ValueError:
                continue

    return np.array(coords)


def normalize_airfoil(coords: np.ndarray) -> np.ndarray:
    """
    Normalize airfoil coordinates to unit chord

    Args:
        coords: Nx2 array of [x, y] coordinates

    Returns:
        Normalized coordinates with chord length = 1
    """
    x = coords[:, 0]
    y = coords[:, 1]

    # Find chord (max x - min x)
    chord = x.max() - x.min()

    # Translate to start at x=0
    x = x - x.min()

    # Scale to unit chord
    x = x / chord
    y = y / chord

    return np.column_stack([x, y])


def get_preset_airfoils() -> dict:
    """
    Get dictionary of common preset airfoils

    Returns:
        Dictionary mapping airfoil name to NACA designation
    """
    return {
        "NACA 0012": {"type": "4digit", "code": "0012", "description": "Symmetric, 12% thick"},
        "NACA 2412": {"type": "4digit", "code": "2412", "description": "2% camber, 40% location, 12% thick"},
        "NACA 4412": {"type": "4digit", "code": "4412", "description": "4% camber, 40% location, 12% thick"},
        "NACA 0015": {"type": "4digit", "code": "0015", "description": "Symmetric, 15% thick"},
        "NACA 6412": {"type": "4digit", "code": "6412", "description": "6% camber, 40% location, 12% thick"},
        "NACA 23012": {"type": "5digit", "code": "23012", "description": "5-digit series, 12% thick"},
        "NACA 0006": {"type": "4digit", "code": "0006", "description": "Symmetric, 6% thick (thin)"},
        "NACA 0009": {"type": "4digit", "code": "0009", "description": "Symmetric, 9% thick"},
    }


def calculate_geometric_properties(coords: np.ndarray) -> dict:
    """
    Calculate geometric properties of airfoil

    Args:
        coords: Nx2 array of [x, y] coordinates

    Returns:
        Dictionary with geometric properties
    """
    x = coords[:, 0]
    y = coords[:, 1]

    # Find leading edge (minimum x)
    le_idx = np.argmin(x)

    # Split into upper and lower surfaces
    upper = coords[:le_idx + 1]
    lower = coords[le_idx:]

    # Maximum thickness
    max_thickness = 0
    max_thickness_location = 0

    for xi in np.linspace(0, 1, 100):
        # Interpolate y at this x for upper and lower surfaces
        y_upper = np.interp(xi, upper[:, 0], upper[:, 1])
        y_lower = np.interp(xi, lower[:, 0], lower[:, 1])

        thickness = y_upper - y_lower
        if thickness > max_thickness:
            max_thickness = thickness
            max_thickness_location = xi

    # Leading edge radius (approximate)
    le_x = x[le_idx]
    le_y = y[le_idx]

    # Trailing edge thickness
    te_thickness = abs(y[0] - y[-1])

    return {
        "max_thickness": float(max_thickness),
        "max_thickness_location": float(max_thickness_location),
        "leading_edge": [float(le_x), float(le_y)],
        "trailing_edge_thickness": float(te_thickness),
        "chord_length": float(x.max() - x.min())
    }


if __name__ == "__main__":
    # Test NACA generators
    print("Generating NACA 0012...")
    naca0012 = generate_naca_4digit("0012", num_points=100)
    print(f"Generated {len(naca0012)} points")
    print(f"LE coordinates: {naca0012[50]}")  # Approximate LE

    print("\nGenerating NACA 2412...")
    naca2412 = generate_naca_4digit("2412", num_points=100)

    print("\nGeometric properties of NACA 0012:")
    props = calculate_geometric_properties(naca0012)
    for key, value in props.items():
        print(f"  {key}: {value}")

    print("\nAvailable preset airfoils:")
    for name, info in get_preset_airfoils().items():
        print(f"  {name}: {info['description']}")
