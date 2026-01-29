from dataclasses import dataclass, field
from typing import List, Optional, Tuple

@dataclass
class MachineElement:
    """Base class for elements attached to the shaft (Gears, Bearings, etc)."""
    name: str = "Element"

@dataclass
class Bearing(MachineElement):
    """Represents a bearing support."""
    type: str = "Ball" # Propriedade simplificada por enquanto
    width: float = 20.0 # mm
    fixed_axial: bool = False

@dataclass
class StressFeature:
    """Base class for geometric features causing stress concentration."""
    description: str = "General Feature"
    # User inputs these manually for now as agreed
    kf_bending: float = 1.0 
    kf_torsion: float = 1.0

@dataclass
class Fillet(StressFeature):
    """Shoulder fillet radius."""
    radius: float = 1.0 # mm
    description: str = "Shoulder Fillet"

@dataclass
class Keyway(StressFeature):
    """Keyway for transmitting torque."""
    type: str = "Profile" # 'Profile' or 'SledRunner'
    description: str = "Keyway"

@dataclass
class Groove(StressFeature):
    """Groove for retaining rings."""
    width: float = 1.1 # mm
    depth: float = 0.5 # mm
    description: str = "Retaining Ring Groove"

@dataclass
class ShaftNode:
    """Represents a point of interest on the shaft."""
    position: float # mm
    diameter_left: float # mm
    diameter_right: float # mm
    element: Optional[MachineElement] = None
    stress_concentration: Optional[StressFeature] = None

    @property
    def is_shoulder(self) -> bool:
        return self.diameter_left != self.diameter_right

@dataclass
class ShaftSegment:
    """Represents the cylindrical segment between two nodes."""
    start_node: ShaftNode
    end_node: ShaftNode
    
    @property
    def length(self) -> float:
        return self.end_node.position - self.start_node.position
    
    @property
    def diameter(self) -> float:
        # Assuming diameter is constant in segment for now, taking check from start node right
        return self.start_node.diameter_right

class Shaft:
    """Manager class for the entire shaft assembly."""
    def __init__(self):
        self.nodes: List[ShaftNode] = []
        self.material: dict = {} # Placeholder for material
        
        # Load storage
        # We store them separately for now, but they should logically link to positions (nodes)
        self.forces: List = [] 
        self.torques: List = []

    def add_node(self, position: float, diameter_left: float = None, diameter_right: float = None, element: Optional[MachineElement] = None):
        """Adds a node to the shaft and keeps nodes sorted by position."""
        
        # If node exists at position, update it? Or error?
        # For simplicity, if close enough, update.
        existing_node = next((n for n in self.nodes if abs(n.position - position) < 1e-5), None)
        
        if existing_node:
            if diameter_left is not None: existing_node.diameter_left = diameter_left
            if diameter_right is not None: existing_node.diameter_right = diameter_right
            if element is not None: existing_node.element = element
            return

        # Infer defaults if new
        if not self.nodes:
            if diameter_left is None: diameter_left = 20.0
            if diameter_right is None: diameter_right = 20.0
        else:
            # Find nearest neighbors to infer defaults if needed
            pass
            # For this MVP, if None, we might copy neighbor or default. 
            # But let's assume UI provides valid data or we explicitly set it.
            if diameter_left is None: diameter_left = 20.0
            if diameter_right is None: diameter_right = 20.0

        node = ShaftNode(position, diameter_left, diameter_right, element)
        self.nodes.append(node)
        self.nodes.sort(key=lambda n: n.position)

    def get_segments(self) -> List[ShaftSegment]:
        """Generates segments based on current nodes."""
        segments = []
        if len(self.nodes) < 2:
            return segments
        
        for i in range(len(self.nodes) - 1):
            segments.append(ShaftSegment(self.nodes[i], self.nodes[i+1]))
        return segments
    
    def get_total_length(self) -> float:
        if not self.nodes:
            return 0.0
        return self.nodes[-1].position - self.nodes[0].position
    
    def reset(self):
        """Clears all data."""
        self.nodes = []
        self.forces = []
        self.torques = []
