"""Explicit, limited lift/contact/hold outcome checks, independent of scene loading."""

from math import isfinite


def next_hold_count(previous, lift, contact_force, linear_speed, criteria):
    if any(not isfinite(value) for value in (lift, contact_force, linear_speed)):
        raise ValueError('Nonfinite measured grasp outcome')
    held = (lift >= criteria['lift_height_m']
            and contact_force >= criteria['contact_force_threshold_n']
            and linear_speed <= criteria['max_linear_speed_m_s'])
    return previous + 1 if held else 0
