import numpy as np
from typing import Optional

def calculate_endurance_limit(Sut: float, diameter: float = 20.0, 
                            surface_finish: str = "machined", 
                            reliability: float = 0.99) -> float:
    """
    Calculates the corrected endurance limit (Se) using Marin factors.
    Se = ka * kb * kc * kd * ke * kf * Se'
    """
    # 1. Se' (Rotary beam test limit) - Shigley Estimate
    if Sut < 1400e6:
        Se_prime = 0.5 * Sut
    else:
        Se_prime = 700e6
        
    # 2. ka: Surface Factor
    # ka = a * Sut^b (Sut in MPa)
    Sut_Mpa = Sut / 1e6
    factors = {
        "ground": (1.58, -0.085),
        "machined": (4.51, -0.265),
        "hot_rolled": (57.7, -0.718),
        "as_forged": (272, -0.995)
    }
    
    a, b = factors.get(surface_finish, factors["machined"])
    ka = a * (Sut_Mpa ** b)
    
    # 3. kb: Size Factor (Shigley for Rotating Shaft)
    # d in mm
    d_eff = diameter # Effective dimension
    
    if 2.79 <= d_eff <= 51:
        kb = 1.24 * (d_eff ** -0.107)
    elif 51 < d_eff <= 254:
        kb = 0.859 * (d_eff ** -0.057)
    else:
        kb = 1.0 # Fallback or out of range
        
    # 4. kc: Loading Factor
    kc = 1.0 # Bending = 1, Torsion = 0.59 (Handled in Von Mises or here?)
    # Shigley recommends handling torsion in the stress calc, kc=1 for bending.
    
    # 5. kd: Temperature (Assumed room temp)
    kd = 1.0
    
    # 6. ke: Reliability
    rel_map = {0.5: 1.0, 0.9: 0.897, 0.99: 0.814, 0.999: 0.753}
    ke = rel_map.get(reliability, 0.814)
    
    # 7. kf: Miscellaneous
    kf_factor = 1.0
    
    Se = ka * kb * kc * kd * ke * kf_factor * Se_prime
    return Se

def calculate_min_diameter(moment_amp: float, torque_avg: float, 
                         Sut: float, Sy: float, 
                         Kf: float = 1.0, Kfs: float = 1.0, 
                         n: float = 2.0,
                         se_overwrite: Optional[float] = None) -> float:
    """
    Calculates minimum diameter based on ASME Elliptic criterion for fatigue.
    
    Args:
        moment_amp: Alternating bending moment (N.m). Assumes fully reversed (Mm=0).
        torque_avg: Mean torque (N.m). Assumes steady torque (Ta=0).
        Sut: Ultimate tensile strength (Pa).
        Sy: Yield strength (Pa).
        Kf: Fatigue stress concentration factor (Bending).
        Kfs: Fatigue stress concentration factor (Torsion).
        n: Safety factor.
        se_overwrite: If provided, uses this Se instead of calculating generic one.
    
    Returns:
        float: Minimum diameter in mm.
    """
    
    # If Se is not provided, estimate for a "typical" shaft area (approx d=50mm)
    # Ideally, this is iterative: Assume d -> Calc kb -> Calc Se -> Calc d -> Repeat.
    # For MVP non-iterative check:
    if se_overwrite:
        Se = se_overwrite
    else:
        Se = calculate_endurance_limit(Sut, diameter=50.0)
        
    # ASME Elliptic Failure Criterion
    # (sigma_a / Se)^2 + (sigma_m / Sy)^2 = (1/n)^2
    # For shaft:
    # sigma_a = 32 * Kf * Ma / (pi * d^3)
    # sigma_m = sqrt(3) * 16 * Kfs * Tm / (pi * d^3)  (Von Mises equivalent mean stress)
    # wait, Shigley DE-ASME Elliptic Formula (10th ed, Eq 7-16):
    # d = ( 16n/pi * sqrt( (4 (Kf Ma)/Se)^2 + (3 (Kfs Tm)/Sy)^2 ) ) ^ (1/3)
    
    # Term 1 (Bending Alternating)
    term1 = ( 4.0 * (Kf * moment_amp) / Se ) ** 2
    
    # Term 2 (Torsion Mean) - Note: 3 comes from sqrt(3)^2 for Von Mises Torsion -> Normal
    term2 = ( 3.0 * (Kfs * torque_avg) / Sy ) ** 2
    
    d_meters = ( (16.0 * n / np.pi) * np.sqrt(term1 + term2) ) ** (1/3)
    
    return d_meters * 1000.0 # Convert to mm
