import numpy as np

def macaulay(x: np.ndarray, a: float, n: int) -> np.ndarray:
    """
    Computes the Macaulay bracket <x - a>^n.
    
    Args:
        x (np.ndarray): The spatial coordinates to evaluate.
        a (float): The location of the singularity.
        n (int): The power of the function.
        
    Returns:
        np.ndarray: The evaluated function.
    """
    val = x - a
    # Create mask where (x-a) >= 0
    mask = val >= 0
    
    # Calculate result
    res = np.zeros_like(x)
    
    if n == 0:
        res[mask] = 1.0 # Force (integral of singularity) -> Unit Step
        # Actually for point load shear: V = -F * <x-a>^0
    elif n == 1:
        res[mask] = val[mask] # Moment -> Ramp
    elif n >= 2:
        res[mask] = val[mask]**n
    elif n < 0:
        # Handling singularity doublets/impulses if needed (rare for simple shaft)
        pass
        
    return res

def singularity_shear(x: np.ndarray, force: float, pos: float) -> np.ndarray:
    """Shear force contribution from a point load F at pos: -F * <x-a>^0"""
    return -force * macaulay(x, pos, 0)

def singularity_moment(x: np.ndarray, force: float, pos: float) -> np.ndarray:
    """Bending moment contribution from a point load F at pos: F * <x-a>^1"""
    return force * macaulay(x, pos, 1) # Integral of -V -> Integral of F = F*x
    # Wait, sign convention.
    # V = dM/dx. 
    # If V = -F (after load), M = -F*x + C.
    # Let's stick to standard beam formulas superposition.
    # Force F upwards at 'a':
    # V(x) = +F for x<a (support), ... no this is getting complex with reactions.
    # Result: Reaction R_left * <x-0>^0 - Force F * <x-a>^0 ...
