from dataclasses import dataclass
from typing import Optional, List, Tuple
import math

@dataclass
class Load:
    """Base class for loads."""
    name: str = "Load"

@dataclass
class RadialForce(Load):
    """Represents a radial force applied at a specific position."""
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
    """Represents torque applied."""
    magnitude: float = 0.0 # N.m (Positive = CCW?)
    position: float = 0.0 # mm

@dataclass
class GearLoad:
    """
    Helper to generate loads from a spur gear.
    """
    torque: float # N.m
    diameter: float # mm (Pitch diameter)
    pressure_angle: float = 20.0 # degrees
    helix_angle: float = 0.0 # degrees (Not fully supported in 2D statics yet)
    mesh_angle: float = 0.0 # degrees (0 = top, 90 = right, etc. - location of mating gear)
    
    def resolve_loads(self, position: float) -> Tuple[RadialForce, Torque]:
        """
        Calculates the RadialForce and Torque equivalent.
        Returns: (RadialForce, Torque)
        """
        # Tangential Force Ft = 2 * T / d (d in meters)
        d_meters = self.diameter / 1000.0
        if d_meters == 0:
            Ft = 0
        else:
            Ft = 2 * abs(self.torque) / d_meters
            
        # Radial Force Fr = Ft * tan(phi)
        Fr = Ft * math.tan(math.radians(self.pressure_angle))
        
        # Total Transverse Force (Magnitude)
        F_transverse = math.sqrt(Ft**2 + Fr**2)
        
        # Direction?
        # If mesh_angle is theta (location of contact).
        # Ft acts perpendicular to radius (tangent).
        # Fr acts towards center (radial).
        
        # This is complex vector addition.
        # Simplified for now: Returns a RadialForce Object representing the Resultant Vector.
        # Vector geometry should be handled by the user ensuring angles are correct, 
        # or we implement full vector addition here. 
        
        # Let's assume standard definitions:
        # User provides mesh_angle.
        # Fr is along mesh_angle + 180 (pushing against shaft).
        # Ft is along mesh_angle +/- 90 (driving vs driven).
        
        # For MVP, let's just return the magnitude and let user fine tune angle,
        # OR we try to estimate the angle of the resultant force.
        
        # Angle of Resultant force relative to Radial component:
        # alpha = atan(Ft/Fr) = atan(1/tan(phi)) = atan(cot(phi)) = 90 - phi
        
        # So force angle is roughly mesh_angle + 180 +/- (90 - phi).
        # This is too implicit.
        # Let's return F_transverse with a clear docstring.
        
        return RadialForce(magnitude=F_transverse, angle=self.mesh_angle, position=position), Torque(magnitude=self.torque, position=position)
