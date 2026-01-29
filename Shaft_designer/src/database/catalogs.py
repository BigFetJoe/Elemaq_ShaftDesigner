# Minimal catalog database
STANDARD_DIAMETERS = [
    10, 12, 15, 17, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100
]

def find_nearest_standard(d_calc: float) -> int:
    """Finds the nearest standard diameter greater than or equal to d_calc.
    
    This is useful for finalizing dimensions after stress analysis.
    """
    for d in STANDARD_DIAMETERS:
        if d >= d_calc:
            return d
    return STANDARD_DIAMETERS[-1] # Return max if larger

def get_next_standard_diameter(current_d: float, step_up: bool = True) -> float:
    """
    Determines the next standard diameter step.
    
    NOTE: This logic is for INITIAL PARAMETERIZATION ONLY (smart guessing).
    Actual sizing will happen in future calculation updates based on stress/fatigue analysis.
    The diameter is not strictly bound to this logic once the user edits specific details or analysis is run.
    """
    sorted_d = sorted(STANDARD_DIAMETERS)
    
    if step_up:
        # Find first d > current_d
        for d in sorted_d:
            if d > current_d:
                return float(d)
        return float(current_d) # Already max
    else:
        # Find first d < current_d (searching backwards)
        for d in reversed(sorted_d):
            if d < current_d:
                return float(d)
        return float(current_d) # Already min
