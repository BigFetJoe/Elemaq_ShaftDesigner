import numpy as np
from typing import Optional, Dict
import src.analysis.fatigue_factors as ff

def calculate_endurance_limit(Sut: float, diameter: float = 20.0, 
                            surface_finish: str = "usinado", 
                            reliability: str = "99%") -> float:
    """
    Backward compatibility wrapper for Se calculation.
    """
    
    # 1. Se'
    Se_prime = ff.K_fadiga(Sut)
    
    # 2. Estimate Se
    Se = ff.marin_eq(
        res_ult=Sut,
        se_est=Se_prime,
        acab_superficial=surface_finish,
        diam=diameter/1000.0, # Convert mm to m
        tip_carga='flexão', 
        temp=20.0,
        confiabilidade=reliability
    )
    return Se

def calculate_min_diameter(moment_amp: float, torque_mean: float, 
                         Sut: float, Sy: float, 
                         moment_mean: float = 0.0,
                         torque_amp: float = 0.0,
                         Kf: float = 1.0, Kfs: float = 1.0, 
                         n: float = 2.0,
                         fatigue_config: dict = None,
                         se_overwrite: Optional[float] = None) -> float:
    """
    Calculates minimum diameter based on ASME Elliptic criterion for fatigue (Generalized).
    
    Args:
        moment_amp (Ma): Alternating bending moment (N.m).
        torque_mean (Tm): Mean torque (N.m).
        Sut: Ultimate tensile strength (Pa).
        Sy: Yield strength (Pa).
        moment_mean (Mm): Mean bending moment (N.m).
        torque_amp (Ta): Alternating torque (N.m).
        Kf: Fatigue stress concentration factor (Bending).
        Kfs: Fatigue stress concentration factor (Torsion).
        n: Safety factor.
        fatigue_config: Dict with 'surface', 'reliability', 'temp', 'kf'.
        se_overwrite: If provided, uses this Se instead of calculating generic one.
    
    Returns:
        float: Minimum diameter in mm.
    """
    
    # Defaults
    if fatigue_config is None:
        fatigue_config = {
            'surface': 'usinado',
            'reliability': '99%',
            'temp': 20.0,
            'kf': 1.0
        }

    # Initial Estimate for Diameter (needed for Size Factor kb)
    d_guess = 0.05 # 50mm
    
    if se_overwrite:
        Se = se_overwrite
    else:
        Se_prime = ff.K_fadiga(Sut)
        Se = ff.marin_eq(
            res_ult=Sut,
            se_est=Se_prime,
            acab_superficial=fatigue_config.get('surface', 'usinado'),
            diam=d_guess,
            tip_carga='flexão', 
            temp=fatigue_config.get('temp', 20.0),
            confiabilidade=fatigue_config.get('reliability', '99%'),
            kf_misc=fatigue_config.get('kf', 1.0)
        )
        
    # Generalized ASME Elliptic Failure Criterion for Shafts (Shigley / DE-ASME)
    # 1/n = sqrt( (sigma_a' / Se)^2 + (sigma_m' / Sy)^2 )
    # where sigma' is Von Mises stress relative to alternating/mean components.
    # sigma_a' = (16/pi d^3) * sqrt( 4 (Kf Ma)^2 + 3 (Kfs Ta)^2 )
    # sigma_m' = (16/pi d^3) * sqrt( 4 (Kf Mm)^2 + 3 (Kfs Tm)^2 )
    
    # Let A be the load term for alternating: sqrt( 4 (Kf Ma)^2 + 3 (Kfs Ta)^2 )
    # Let B be the load term for mean:        sqrt( 4 (Kf Mm)^2 + 3 (Kfs Tm)^2 )
    
    # 1/n = (16 / pi d^3) * sqrt( (A/Se)^2 + (B/Sy)^2 )
    # d^3 = (16 n / pi) * sqrt( (A/Se)^2 + (B/Sy)^2 )
    
    A = np.sqrt( 4.0 * (Kf * moment_amp)**2 + 3.0 * (Kfs * torque_amp)**2 )
    B = np.sqrt( 4.0 * (Kf * moment_mean)**2 + 3.0 * (Kfs * torque_mean)**2 )
    
    term_root = np.sqrt( (A/Se)**2 + (B/Sy)**2 )
    
    # d_meters = ( (16 * n / pi) * term_root ) ** (1/3)
    d_meters = ( (16.0 * n / np.pi) * term_root ) ** (1/3)

    return d_meters * 1000.0 # Convert to mm
