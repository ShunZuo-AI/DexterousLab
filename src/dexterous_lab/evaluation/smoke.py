"""Numerical checks shared by runtime verification and unit tests."""

from math import isclose, isfinite


def check_physics_values(masses, materials, expected_mass, expected_friction):
    """Reject actual backend mass/material values that disagree with configuration."""
    if not masses or any(not isfinite(mass) or not isclose(mass, expected_mass, rel_tol=1e-4) for mass in masses):
        raise RuntimeError(f"Backend object mass {masses} differs from configured {expected_mass}")
    if not materials:
        raise RuntimeError("No physics materials were loaded for the object")
    for material in materials:
        if len(material) != 3 or not all(isfinite(value) for value in material):
            raise RuntimeError("Physics material must contain finite static friction, dynamic friction, restitution")
        if any(not isclose(value, expected_friction, rel_tol=1e-4, abs_tol=1e-6) for value in material[:2]):
            raise RuntimeError(f"Backend friction {material[:2]} differs from configured {expected_friction}")
