from typing import List, Tuple, Dict
import numpy as np
from src.models.geometry import Shaft, Bearing
from src.models.loads import RadialForce, Torque
from src.analysis.utils import macaulay

def calculate_reactions(shaft: Shaft) -> Dict[str, Tuple[float, float]]:
    """
    Calculates reactions at bearings for a simply supported shaft.
    Returns dictionary with bearing name keys and (Ry, Rz) tuples.
    Assumes exactly 2 bearings for determinstic solution.
    """
    # Find bearings
    bearings = []
    for node in shaft.nodes:
        if isinstance(node.element, Bearing):
            bearings.append((node, node.element))
    
    if len(bearings) != 2:
        # Return zeros or raise error. For MVP, return zeros if not exactly 2
        return {}

    node_A, support_A = bearings[0]
    node_B, support_B = bearings[1]
    
    pos_A = node_A.position
    pos_B = node_B.position
    
    # Distance between bearings
    L_span = pos_B - pos_A
    if L_span == 0:
        return {support_A.name: (0,0), support_B.name: (0,0)}

    # Sum of Moments about A = 0
    # Sigma M_A = 0 => R_B * L_span - Sum(F_i * (pos_i - pos_A)) = 0
    # R_B = Sum(F_i * (pos_i - pos_A)) / L_span
    
    sum_moment_y_A = 0.0 # From vertical forces (Fy) creating moment about Z? No, simpler:
    # We analyze planes separately. 
    # Plane XY (Vertical forces Fy, Moments Mz)
    # Plane XZ (Horizontal forces Fz, Moments My)
    
    # 1. Plane XY (Vertical Loads Fy)
    sum_moment_A_planeXY = 0.0
    sum_force_Y = 0.0
    
    for force in shaft.forces:
        dist = force.position - pos_A
        # Moment caused by Fy at distance 'dist'
        # Clockwise is negative? Let's use standard mechanics: Counter-Clockwise +
        # Force Fy upwards (+) causes CCW moment (+).
        sum_moment_A_planeXY += force.fy * dist
        sum_force_Y += force.fy
        
    Ray = 0.0
    Rby = 0.0
    
    # Rby * L_span - sum_moments_loads = 0 (assuming Rby upwards is +)
    # Actually: sum(M) about A:
    # Rby * L + Sum(Fi * di) = 0 ??
    # Let's trust the statics: Sum M_A = 0
    # Forces F_i at x_i.
    # R_B * (xB - xA) + Sum( F_i * (xi - xA) ) = 0
    # R_B = - Sum( F_i * (xi - xA) ) / L_span
    
    # But wait, external loads usually act DOWN (-y). 
    # If load is -100N at L/2.
    # R_B = - (-100 * L/2) / L = 50N. Correct.
    
    Rby = - sum_moment_A_planeXY / L_span
    
    # Sum Fy = 0 => Ray + Rby + Sum(Fy) = 0
    # Ray = - Rby - Sum(Fy)
    Ray = - Rby - sum_force_Y
    
    # 2. Plane XZ (Horizontal Loads Fz)
    sum_moment_A_planeXZ = 0.0
    sum_force_Z = 0.0
    
    for force in shaft.forces:
        dist = force.position - pos_A
        sum_moment_A_planeXZ += force.fz * dist
        sum_force_Z += force.fz
        
    Rbz = - sum_moment_A_planeXZ / L_span
    Raz = - Rbz - sum_force_Z
    
    return {
        support_A.name: (Ray, Raz),
        support_B.name: (Rby, Rbz),
        "A_pos": pos_A,
        "B_pos": pos_B
    }

def calculate_diagrams(shaft: Shaft, num_points: int = 200):
    """
    Returns arrays for x positions, Shear (V), Moment (M), and Torque (T).
    """
    L = shaft.get_total_length()
    if L == 0:
        return np.array([]), np.array([]), np.array([]), np.array([])
        
    x = np.linspace(0, L, num_points)
    
    # Get reactions
    reactions = calculate_reactions(shaft)
    if not reactions:
        return x, np.zeros_like(x), np.zeros_like(x), np.zeros_like(x)
        
    # Unpack basic layout
    bearings = [n for n in shaft.nodes if isinstance(n.element, Bearing)]
    pos_A = bearings[0].position
    pos_B = bearings[1].position
    name_A = bearings[0].element.name
    name_B = bearings[1].element.name
    
    (Ray, Raz) = reactions[name_A]
    (Rby, Rbz) = reactions[name_B]
    
    # --- Shear Force V(x) ---
    # V(x) = Sum of all forces to the left of x
    # Singularity: V(x) = R * <x-a>^0 + F * <x-b>^0 ...
    
    # Plane XY
    Vy = np.zeros_like(x)
    # Reactions
    Vy += Ray * macaulay(x, pos_A, 0)
    Vy += Rby * macaulay(x, pos_B, 0)
    # Loads
    for f in shaft.forces:
        Vy += f.fy * macaulay(x, f.position, 0)
        
    # Plane XZ
    Vz = np.zeros_like(x)
    Vz += Raz * macaulay(x, pos_A, 0)
    Vz += Rbz * macaulay(x, pos_B, 0)
    for f in shaft.forces:
        Vz += f.fz * macaulay(x, f.position, 0)
        
    # Total Shear Magnitude
    # V_total = sqrt(Vy^2 + Vz^2)
    V_total = np.sqrt(Vy**2 + Vz**2)
    
    # --- Bending Moment M(x) ---
    # M(x) = Integral of V(x)
    
    # Plane XY (Mz - Moment about Z axis due to Y forces)
    # M(x) = R * <x-a>^1 + F * <x-b>^1
    My_bending = np.zeros_like(x) # Moment caused by Vertical forces (bending in vertical plane)
    My_bending += Ray * macaulay(x, pos_A, 1)
    My_bending += Rby * macaulay(x, pos_B, 1)
    for f in shaft.forces:
        My_bending += f.fy * macaulay(x, f.position, 1)
        
    # Plane XZ (My - Moment about Y axis due to Z forces)
    Mz_bending = np.zeros_like(x)
    Mz_bending += Raz * macaulay(x, pos_A, 1)
    Mz_bending += Rbz * macaulay(x, pos_B, 1)
    for f in shaft.forces:
        Mz_bending += f.fz * macaulay(x, f.position, 1)
        
    # Total Bending Moment Magnitude
    M_total = np.sqrt(My_bending**2 + Mz_bending**2)
    
    # --- Torque T(x) ---
    Tx = np.zeros_like(x)
    # Torques are just steps: T_applied * <x-a>^0 ??
    # Actually Torque diagram is sum of torques to left.
    for t in shaft.torques:
        # Sign convention?
        # Let's assume input is moment vector magnitude.
        # Simplest: Sum of (Magnitude * <x-pos>^0)
        Tx += t.magnitude * macaulay(x, t.position, 0)
    
    # Correction: Static equilibrium for Torque requires Sum T = 0.
    # If user inputs unbalanced torque, diagram will "fly".
    # We won't auto-balance for now, just show what is.
    
    return x, V_total, M_total, Tx
