import streamlit as st
import uuid
from src.models.geometry import Shaft, Bearing
from src.models.components import SpurGear, Pulley, Component
from src.models.loads import RadialForce, Torque
from src.database.catalogs import STANDARD_DIAMETERS, get_next_standard_diameter

# --- Feature Management Helpers ---
def init_features():
    if "features" not in st.session_state:
        st.session_state.features = []

def add_feature(ftype, pos=0.0):
    feat = {
        "id": str(uuid.uuid4()),
        "type": ftype,
        "pos": pos,
        "props": {}
    }
    # Initialize default props based on type
    if ftype == "Shoulder":
        feat["props"] = {"diameter": 20.0}
    elif ftype == "Spur Gear":
        feat["props"] = {"diameter": 100.0, "angle": 0.0, "power": 0.0, "rpm": 0.0, "manual_fy": 0.0, "manual_fz": 0.0}
    elif ftype == "Pulley":
        feat["props"] = {"diameter": 100.0, "power": 0.0, "rpm": 0.0, "manual_fy": 0.0, "manual_fz": 0.0, "manual_t": 0.0}
    elif ftype == "Radial Force":
        feat["props"] = {"mag": 100.0, "angle": 0.0}
    elif ftype == "Torque":
        feat["props"] = {"mag": 50.0, "type": "Mean"} # Alternating/Mean switch?
        
    st.session_state.features.append(feat)

def remove_feature(idx):
    st.session_state.features.pop(idx)

# --- Shaft Builder Logic ---
def update_shaft_model(shaft: Shaft, config: dict):
    """
    Rebuilds the shaft model based on the Feature List.
    """
    shaft.reset()
    
    total_len = config['total_length']
    start_diameter = st.session_state.get("start_diameter", 20.0)
    
    features = st.session_state.get("features", [])
    
    # 1. Geometry Construction (Shoulders define segments)
    # Collect all points that define diameter changes + End points
    # A "Shoulder" feature says: "From this position onwards, diameter is X"
    
    # We sort valid shoulders by position
    shoulders = [f for f in features if f['type'] == 'Shoulder']
    shoulders.sort(key=lambda x: x['pos'])
    
    # Validate positions
    valid_shoulders = [s for s in shoulders if 0 < s['pos'] < total_len]
    
    # Build Nodes
    # Start Node
    nodes = []
    
    # We drift from 0 to Total Length
    current_pos = 0.0
    current_diam = start_diameter
    
    # Add Start Node (0.0)
    shaft.add_node(position=0.0, diameter_right=current_diam)
    
    # Process Shoulders
    for s in valid_shoulders:
        pos = s['pos']
        new_diam = s['props'].get('diameter', 20.0)
        
        # Add Node at this position (Left diam = old, Right diam = new)
        shaft.add_node(position=pos, diameter_left=current_diam, diameter_right=new_diam)
        current_diam = new_diam
        
    # Add End Node
    shaft.add_node(position=total_len, diameter_left=current_diam)
    
    # 2. Components (Gears, Pulleys)
    # Place them on the shaft. If a node exists nearby (e.g. shoulder), attach to it?
    # Or Component just resides at a position. 
    # Shaft.add_node(..., element=comp) handles standardizing node presence.
    
    comps = [f for f in features if f['type'] in ["Spur Gear", "Pulley"]]
    for c in comps:
        pos = c['pos']
        if not (0 <= pos <= total_len): continue
        
        element = None
        props = c['props']
        
        # Handle Load Inputs (Manual vs P/rev)
        # For MVP we kept 'manual' fields in UI properties
        
        if c['type'] == "Spur Gear":
            element = SpurGear(
                name="Gear", 
                diameter=props.get('diameter', 100.0),
                width=props.get('width', 20.0),
                contact_angle=props.get('angle', 0.0),
                power=props.get('power', 0.0),
                rpm=props.get('rpm', 0.0)
            )
            
            # Manual Loads
            mfy = props.get('manual_fy', 0.0)
            mfz = props.get('manual_fz', 0.0)
            import math
            mag = math.sqrt(mfy**2 + mfz**2)
            ang = math.degrees(math.atan2(mfz, mfy))
            if mag > 1e-6:
                element.manual_forces.append(RadialForce(magnitude=mag, angle=ang, position=pos))
                
        elif c['type'] == "Pulley":
            element = Pulley(
                name="Pulley",
                diameter=props.get('diameter', 100.0),
                width=props.get('width', 20.0),
                power=props.get('power', 0.0),
                rpm=props.get('rpm', 0.0)
            )
            # Manual Loads
            mfy = props.get('manual_fy', 0.0)
            mfz = props.get('manual_fz', 0.0)
            mt = props.get('manual_t', 0.0)
            mag = math.sqrt(mfy**2 + mfz**2)
            ang = math.degrees(math.atan2(mfz, mfy))
            if mag > 1e-6:
                element.manual_forces.append(RadialForce(magnitude=mag, angle=ang, position=pos))
            if abs(mt) > 1e-6:
                element.manual_torques.append(Torque(mean=mt, position=pos))
        
        # Add to shaft (this updates existing node if pos matches, or creates new)
        shaft.add_node(position=pos, element=element)

    # 3. Loads (Points)
    loads = [f for f in features if f['type'] in ["Radial Force", "Torque"]]
    for l in loads:
        pos = l['pos']
        props = l['props']
        
        if l['type'] == "Radial Force":
            rf = RadialForce(
                magnitude=props.get('mag', 100.0),
                angle=props.get('angle', 0.0),
                position=pos
            )
            shaft.forces.append(rf)
            
        elif l['type'] == "Torque":
            # Assume Mean for now unless we add UI for Alt
            t = Torque(
                mean=props.get('mag', 50.0),
                position=pos
            )
            shaft.torques.append(t)

    # 4. Supports
    # Keep explicit inputs for now or allow "Support" feature?
    # User asked for "Add components where I want".
    # Supports are critical. Let's keep the dedicated Support section for A/B for now to ensure statics works easily.
    # (Or add "Bearing" to features? Let's stick to dedicated section for now to match sidebar removal)
    
    pos_a = st.session_state.get("bearing_a_pos", 0.0)
    pos_b = st.session_state.get("bearing_b_pos", total_len)
    
    ba = Bearing(name="Bearing A")
    bb = Bearing(name="Bearing B")
    
    shaft.add_node(position=pos_a, element=ba)
    shaft.add_node(position=pos_b, element=bb)


# --- UI Rendering ---
def render_editor(shaft: Shaft, config: dict):
    init_features()
    
    with st.expander("Shaft Geometry & Features", expanded=True):
        st.caption("Define the initial diameter, then add features (Shoulders, Gears, Loads).")
        st.number_input("Start Diameter (mm)", value=20.0, key="start_diameter")
        
        # Add Feature Bar
        # Add Feature Bar
        c1, c2, c3 = st.columns([3, 1, 1])
        new_type = c1.selectbox("Add Feature", ["Shoulder", "Spur Gear", "Pulley", "Radial Force", "Torque"], label_visibility="collapsed")
        new_pos = c2.number_input("Position", value=0.0, step=10.0, min_value=0.0, max_value=config['total_length'], label_visibility="collapsed")
        if c3.button("Add"):
            add_feature(new_type, pos=new_pos)
            st.rerun()
            
        st.markdown("---")
        
        # Render Features List
        if not st.session_state.features:
            st.info("No features added. Shaft is a simple cylinder.")
            
        for i, feat in enumerate(st.session_state.features):
            ftype = feat['type']
            with st.expander(f"{ftype} #{i+1}", expanded=True):
                # Common: Position
                c_head, c_del = st.columns([5, 1])
                feat['pos'] = c_head.number_input(f"Position (mm)", value=feat['pos'], min_value=0.0, max_value=config['total_length'], key=f"pos_{feat['id']}")
                
                if c_del.button("🗑️", key=f"del_{feat['id']}"):
                    remove_feature(i)
                    st.rerun()
                
                # Context Props
                props = feat['props']
                
                if ftype == "Shoulder":
                    props['diameter'] = st.number_input("New Diameter (mm)", value=props.get('diameter', 20.0), key=f"d_{feat['id']}")
                    
                elif ftype == "Spur Gear":
                    c_g1, c_g2, c_g3 = st.columns(3)
                    props['diameter'] = c_g1.number_input("Pitch Diam (mm)", value=props.get('diameter', 100.0), key=f"gd_{feat['id']}")
                    props['width'] = c_g2.number_input("Width (mm)", value=props.get('width', 20.0), key=f"gw_{feat['id']}")
                    props['angle'] = c_g3.number_input("Contact Angle (deg)", value=props.get('angle', 0.0), key=f"ga_{feat['id']}")
                    
                    st.markdown("**Loads (Manual)**")
                    l1, l2 = st.columns(2)
                    props['manual_fy'] = l1.number_input("Fy (N)", value=props.get('manual_fy', 0.0), key=f"mfy_{feat['id']}")
                    props['manual_fz'] = l2.number_input("Fz (N)", value=props.get('manual_fz', 0.0), key=f"mfz_{feat['id']}")
                    
                elif ftype == "Pulley":
                    c_p1, c_p2 = st.columns(2)
                    props['diameter'] = c_p1.number_input("Diameter (mm)", value=props.get('diameter', 100.0), key=f"pd_{feat['id']}")
                    props['width'] = c_p2.number_input("Width (mm)", value=props.get('width', 20.0), key=f"pw_{feat['id']}")
                    
                    st.markdown("**Loads (Manual)**")
                    l1, l2, l3 = st.columns(3)
                    props['manual_fy'] = l1.number_input("Fy (N)", value=props.get('manual_fy', 0.0), key=f"pfy_{feat['id']}")
                    props['manual_fz'] = l2.number_input("Fz (N)", value=props.get('manual_fz', 0.0), key=f"pfz_{feat['id']}")
                    props['manual_t'] = l3.number_input("Torque (Nm)", value=props.get('manual_t', 0.0), key=f"pt_{feat['id']}")

                elif ftype == "Radial Force":
                    c_f1, c_f2 = st.columns(2)
                    props['mag'] = c_f1.number_input("Magnitude (N)", value=props.get('mag', 100.0), key=f"fmag_{feat['id']}")
                    props['angle'] = c_f2.number_input("Angle (deg)", value=props.get('angle', 0.0), key=f"fang_{feat['id']}")
                    
                elif ftype == "Torque":
                     props['mag'] = st.number_input("Magnitude (Nm)", value=props.get('mag', 50.0), key=f"tmag_{feat['id']}")

    with st.expander("Fatigue Factors", expanded=False):
        _render_fatigue_editor(config)

    with st.expander("Supports (Bearings)", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state['bearing_a_pos'] = c1.number_input("Bearing A Position (mm)", value=st.session_state.get('bearing_a_pos', 0.0))
        st.session_state['bearing_b_pos'] = c2.number_input("Bearing B Position (mm)", value=st.session_state.get('bearing_b_pos', config['total_length']))


def _render_fatigue_editor(config):
    """
    Renders inputs for Fatigue Correction Factors.
    """
    c1, c2 = st.columns(2)
    c1.selectbox("Surface Finish", 
                 ['usinado', 'retificado', 'laminado a frio', 'laminado a quente', 'forjado'], 
                 index=0, key="fatigue_surface")
    
    c2.selectbox("Reliability", 
                 ['50%', '90%', '95%', '99%', '99.9%', '99.99%', '99.999%', '99.9999%'], 
                 index=3, key="fatigue_reliability") # Default 99%
                 
    c3, c4 = st.columns(2)
    c3.number_input("Operating Temperature (°C)", value=20.0, step=10.0, key="fatigue_temp")
    c4.number_input("Misc. Factor (kf)", value=1.0, min_value=0.1, max_value=2.0, step=0.05, key="fatigue_kf", help="Miscellaneous effects (corrosion, plating, etc). Default 1.0")
