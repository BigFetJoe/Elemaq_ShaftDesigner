from dataclasses import dataclass
from typing import Optional, List, Tuple
import math

@dataclass
class Load:
    """Base class for loads."""
    name: str = "Load"

@dataclass
class RadialForce(Load):
    """
    Represents a radial force applied at a specific position.
    In a rotating shaft context, a static RadialForce causes:
    - Alternating Bending Moment (Ma)
    - Zero Mean Bending Moment (Mm = 0)
    """
    magnitude: float = 0.0 # N
    angle: float = 0.0 # degrees (angle of the force vector in YZ plane)
    position: float = 0.0 # mm
    
    @property
    def fy(self) -> float:
        """Vertical component (assuming angle 0 is along Y)."""
        return self.magnitude * math.cos(math.radians(self.angle))

    @property
    def fz(self) -> float:
        """Horizontal component."""
        return self.magnitude * math.sin(math.radians(self.angle))

@dataclass
class Torque(Load):
    """
    Represents torque applied.
    Usually:
    - Power transmission causes Constant (Mean) Torque.
    - Start/Stop or reciprocating machinery causes Alternating Torque.
    """
    magnitude: float = 0.0 # N.m (Legacy: treated as Mean if not specified)
    alternating: float = 0.0 # N.m
    mean: float = 0.0 # N.m
    position: float = 0.0 # mm

    def __post_init__(self):
        # Backward compatibility: if magnitude set but mean not, assume mean = magnitude
        if self.magnitude != 0 and self.mean == 0:
            self.mean = self.magnitude
        # Sync magnitude to mean (primary behavior) for simple access
        self.magnitude = self.mean

@dataclass
class Moment(Load):
    """
    Represents a generic bending moment.
    """
    alternating: float = 0.0 # N.m
    mean: float = 0.0 # N.m
    plane: str = "XY" # XY or XZ
    position: float = 0.0 # mm


# Legacy helpers can be deprecated or kept for now
@dataclass
class GearLoad:
    """
    Legacy Helper. Prefer using components.SpurGear.
    """
    torque: float # N.m
    diameter: float # mm (Pitch diameter)
    pressure_angle: float = 20.0 
    helix_angle: float = 0.0
    mesh_angle: float = 0.0
    
    def resolve_loads(self, position: float) -> Tuple[RadialForce, Torque]:
        d_meters = self.diameter / 1000.0
        if d_meters == 0:
            Ft = 0
        else:
            Ft = 2 * abs(self.torque) / d_meters
            
        Fr = Ft * math.tan(math.radians(self.pressure_angle))
        F_transverse = math.sqrt(Ft**2 + Fr**2)
        
        return RadialForce(magnitude=F_transverse, angle=self.mesh_angle, position=position), Torque(mean=self.torque, position=position)
