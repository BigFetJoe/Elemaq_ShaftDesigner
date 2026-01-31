from typing import List, Tuple, Dict
import numpy as np
from src.models.geometry import Shaft
from src.models.components import Bearing
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
        return {}

    node_A, support_A = bearings[0]
    node_B, support_B = bearings[1]
    
    pos_A = node_A.position
    pos_B = node_B.position
    
    L_span = pos_B - pos_A
    if L_span == 0:
        return {support_A.name: (0,0), support_B.name: (0,0)}

    # Plane XY (Vertical Loads Fy)
    sum_moment_A_planeXY = 0.0
    sum_force_Y = 0.0
    
    all_forces, _ = shaft.get_all_loads()

    for force in all_forces:
        dist = force.position - pos_A
        sum_moment_A_planeXY += force.fy * dist
        sum_force_Y += force.fy
        
    Rby = - sum_moment_A_planeXY / L_span
    Ray = - Rby - sum_force_Y
    
    # Plane XZ (Horizontal Loads Fz)
    sum_moment_A_planeXZ = 0.0
    sum_force_Z = 0.0
    
    for force in all_forces:
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
    Returns arrays for x positions and separated stress diagrams.
    Returns: (x, V_total, Ma, Mm, Ta, Tm)
    - V_total: Total shear force magnitude (static).
    - Ma: Alternating Bending Moment (from rotating bending).
    - Mm: Mean Bending Moment (usually 0 for shafts).
    - Ta: Alternating Torque.
    - Tm: Mean Torque.
    """
    L = shaft.get_total_length()
    if L == 0:
        empty = np.array([])
        return empty, empty, empty, empty, empty, empty
        
    x = np.linspace(0, L, num_points)
    
    reactions = calculate_reactions(shaft)
    if not reactions:
        z = np.zeros_like(x)
        return x, z, z, z, z, z
        
    # Unpack basic layout
    bearings = [n for n in shaft.nodes if isinstance(n.element, Bearing)]
    if len(bearings) < 2:
         z = np.zeros_like(x)
         return x, z, z, z, z, z

    pos_A = bearings[0].position
    pos_B = bearings[1].position
    name_A = bearings[0].element.name
    name_B = bearings[1].element.name
    
    (Ray, Raz) = reactions[name_A]
    (Rby, Rbz) = reactions[name_B]
    
    all_forces, all_torques = shaft.get_all_loads()

    # --- Shear Force V(x) ---
    Vy = np.zeros_like(x)
    Vy += Ray * macaulay(x, pos_A, 0)
    Vy += Rby * macaulay(x, pos_B, 0)
    for f in all_forces:
        Vy += f.fy * macaulay(x, f.position, 0)
        
    Vz = np.zeros_like(x)
    Vz += Raz * macaulay(x, pos_A, 0)
    Vz += Rbz * macaulay(x, pos_B, 0)
    for f in all_forces:
        Vz += f.fz * macaulay(x, f.position, 0)
        
    V_total = np.sqrt(Vy**2 + Vz**2)
    
    # --- Bending Moment M(x) ---
    # Calculates the Static Bending Moment in space (My, Mz).
    # For a rotating shaft, this static moment vector translates to a fully reversed (Alternating) moment cycle.
    
    My_bending = np.zeros_like(x)
    My_bending += Ray * macaulay(x, pos_A, 1)
    My_bending += Rby * macaulay(x, pos_B, 1)
    for f in all_forces:
        My_bending += f.fy * macaulay(x, f.position, 1)
        
    Mz_bending = np.zeros_like(x)
    Mz_bending += Raz * macaulay(x, pos_A, 1)
    Mz_bending += Rbz * macaulay(x, pos_B, 1)
    for f in all_forces:
        Mz_bending += f.fz * macaulay(x, f.position, 1)
        
    # Resultant Bending Moment Magnitude
    M_resultant = np.sqrt(My_bending**2 + Mz_bending**2)
    
    # Assign to Alternating vs Mean
    # Unless we have specific "Mean Bending" loads (rare in shafts, usually from constant axial offset or similar? but axial is separate), 
    # we assume ALL bending from transverse loads is Alternating.
    Ma = M_resultant
    Mm = np.zeros_like(x)
    
    # --- Torque T(x) ---
    # Sum separate components suitable for Fatigue
    Ta = np.zeros_like(x)
    Tm = np.zeros_like(x)
    
    for t in all_torques:
        # Step function from torque position
        Ta += t.alternating * macaulay(x, t.position, 0)
        Tm += t.mean * macaulay(x, t.position, 0)
    
    return x, V_total, Ma, Mm, Ta, Tm
