import streamlit as st
from src.models.geometry import Shaft, Bearing, SpurGear, Pulley
from src.models.loads import RadialForce, Torque
from src.database.catalogs import get_next_standard_diameter, STANDARD_DIAMETERS

def update_shaft_model(shaft: Shaft, config: dict):
    """
    Rebuilds the shaft model based on session_state values and global config.
    Must be called before plotting to ensure visualization matches data.
    """
    # --- 1. Geometry (Sections) ---
    shaft.nodes = []
    num_sections = config['num_sections']
    
    # Retrieve or Initialize Start Diameter
    start_diameter = st.session_state.get("start_diameter", 20.0)
    
    # Add initial node
    shaft.add_node(position=0.0, diameter_right=start_diameter)
    
    current_pos = 0.0
    current_diameter = start_diameter
    
    for i in range(num_sections):
        # Retrieve values from session_state (or defaults)
        length = st.session_state.get(f"len_{i}", 100.0)
        has_shoulder = st.session_state.get(f"sh_{i}", False)
        
        # Diameter Logic (Simplified for reconstruction)
        # We need to know what the UI *would* calculate for next_diameter
        # or we store next_diameter explicitly?
        # Ideally, we calculate it dynamically like the UI did to preserve the logic.
        
        el_type = st.session_state.get(f"el_{i}_type", "None")
        
        # Diameter Logic (Simplified for reconstruction)
        # We need to know what the UI *would* calculate for next_diameter
        # or we store next_diameter explicitly?
        # Ideally, we calculate it dynamically like the UI did to preserve the logic.
        
        is_step_up = (i + 1) <= (num_sections / 2.0)
        next_diameter = current_diameter
        
        # Treat any element presence (Shoulder, Gear, Pulley) as a potential diameter step
        has_shoulder = el_type != "None"
        
        if has_shoulder:
            next_diameter = get_next_standard_diameter(current_diameter, step_up=is_step_up)
            if not is_step_up and next_diameter == current_diameter and current_diameter == min(STANDARD_DIAMETERS):
                 pass # Warning handled in UI
        
        current_pos += length
        
        # Create Element if applicable
        element = None
        if el_type == "Spur Gear":
            # Props
            diam = st.session_state.get(f"el_{i}_diam", 100.0)
            angle_contact = st.session_state.get(f"el_{i}_angle", 0.0)
            
            element = SpurGear(name="Gear", diameter=diam, contact_angle=angle_contact)
            
            # Read manual forces
            fy = st.session_state.get(f"el_{i}_fy", 0.0)
            fz = st.session_state.get(f"el_{i}_fz", 0.0)
            
            # Add forces to element
            import math
            mag = math.sqrt(fy**2 + fz**2)
            # Angle: 0=+Y, 90=+Z per loads.py interpretation?
            # loads.py: fy=mag*cos(ang), fz=mag*sin(ang) -> 0 is +Y
            angle = math.degrees(math.atan2(fz, fy)) 
            
            if mag > 1e-6:
                element.manual_forces.append(RadialForce(magnitude=mag, angle=angle, position=current_pos))
            # NO Manual Torque for Gear (Calculated)
                
        elif el_type == "Pulley":
            element = Pulley(name="Pulley")
            # Same Manual Loads logic
            fy = st.session_state.get(f"el_{i}_fy", 0.0)
            fz = st.session_state.get(f"el_{i}_fz", 0.0)
            t = st.session_state.get(f"el_{i}_t", 0.0)
            
            import math
            mag = math.sqrt(fy**2 + fz**2)
            angle = math.degrees(math.atan2(fz, fy)) 
            
            if mag > 1e-6:
                element.manual_forces.append(RadialForce(magnitude=mag, angle=angle, position=current_pos))
            if abs(t) > 1e-6:
                element.manual_torques.append(Torque(magnitude=t, position=current_pos))

        shaft.add_node(position=current_pos, diameter_left=current_diameter, diameter_right=next_diameter, element=element)
        current_diameter = next_diameter

    # --- 2. Loads ---
    shaft.forces = []
    for i in range(config['num_forces']):
        pos = st.session_state.get(f"f_pos_{i}", 0.0)
        mag = st.session_state.get(f"f_mag_{i}", 100.0)
        angle = st.session_state.get(f"f_ang_{i}", 0.0)
        shaft.forces.append(RadialForce(magnitude=mag, angle=angle, position=pos))
        
    shaft.torques = []
    for i in range(config['num_torques']):
        pos = st.session_state.get(f"t_pos_{i}", 0.0)
        mag = st.session_state.get(f"t_mag_{i}", 50.0)
        shaft.torques.append(Torque(magnitude=mag, position=pos))

    # --- 3. Bearings ---
    # Bearings are just nodes with elements in this model
    # We need to find the node closest to the bearing position or add one?
    # The original sidebar added nodes for bearings.
    pos_a = st.session_state.get("bearing_a_pos", 0.0)
    # Default pos_b is end of shaft? We need total length from above loop.
    total_len = current_pos
    pos_b = st.session_state.get("bearing_b_pos", total_len)
    
    bearing_a = Bearing(name="Bearing A")
    bearing_b = Bearing(name="Bearing B")
    
    shaft.add_node(position=pos_a, element=bearing_a)
    shaft.add_node(position=pos_b, element=bearing_b)


def render_editor(shaft: Shaft, config: dict):
    """
    Renders the editor UI components.
    Uses a dropdown to select the active editing mode.
    """
    with st.expander("Model Editor", expanded=True):
        mode = st.selectbox("Edit Mode", ["Geometry", "Loads", "Supports"])
        st.markdown("---")
        
        if mode == "Geometry":
            _render_geometry_editor(config)
        elif mode == "Loads":
            _render_loads_editor(config)
        elif mode == "Supports":
            _render_supports_editor(config, shaft)

def _render_geometry_editor(config):
    st.subheader("Shaft Segments")
    
    col_start = st.columns(2)
    col_start[0].selectbox("Start Diameter (mm)", STANDARD_DIAMETERS, index=4, key="start_diameter")
    
    num_sections = config['num_sections']
    
    # We just render inputs. The 'update_shaft_model' function reads these keys next rerun.
    for i in range(num_sections):
        st.markdown(f"**Section {i+1}**")
        c1, c2 = st.columns(2)
        c1.number_input(f"Length (mm)", value=100.0, key=f"len_{i}")
        
        # Element Type Selector
        el_type = c2.selectbox("Element Type", ["None", "Shoulder", "Spur Gear", "Pulley"], key=f"el_{i}_type")
        
        # If Gear or Pulley, show load inputs
        if el_type == "Spur Gear":
            st.markdown(f"**Spur Gear Properties**")
            gc1, gc2 = st.columns(2)
            gc1.number_input("Pitch Diameter (mm)", value=100.0, key=f"el_{i}_diam")
            gc2.number_input("Contact Angle (deg)", value=0.0, key=f"el_{i}_angle", help="0=Right, 90=Top")
            
            st.markdown(f"**Loads acting on Gear**")
            lc1, lc2 = st.columns(2)
            lc1.number_input("Fy (N) [Vertical]", value=0.0, key=f"el_{i}_fy")
            lc2.number_input("Fz (N) [Horizontal]", value=0.0, key=f"el_{i}_fz")
            
        elif el_type == "Pulley":
            st.markdown(f"**Pulley Loads**")
            lc1, lc2, lc3 = st.columns(3)
            lc1.number_input("Fy (N)", value=0.0, key=f"el_{i}_fy", help="Vertical Force")
            lc2.number_input("Fz (N)", value=0.0, key=f"el_{i}_fz", help="Horizontal Force")
            lc3.number_input("Torque (Nm)", value=0.0, key=f"el_{i}_t")
        
def _render_loads_editor(config):
    st.subheader("Radial Forces")
    if config['num_forces'] == 0:
        st.info("Increase 'Number of Radial Forces' in Sidebar to add loads.")
    
    for i in range(config['num_forces']):
        st.markdown(f"**Force {i+1}**")
        cols = st.columns(3)
        cols[0].number_input(f"Pos (mm)", value=0.0, key=f"f_pos_{i}")
        cols[1].number_input(f"Mag (N)", value=100.0, key=f"f_mag_{i}")
        cols[2].number_input(f"Angle (deg)", value=0.0, key=f"f_ang_{i}")

    st.markdown("---")
    st.subheader("Torques")
    if config['num_torques'] == 0:
        st.info("Increase 'Number of Torques' in Sidebar to add torques.")
        
    for i in range(config['num_torques']):
        st.markdown(f"**Torque {i+1}**")
        cols = st.columns(2)
        cols[0].number_input(f"Pos (mm)", value=0.0, key=f"t_pos_{i}")
        cols[1].number_input(f"Mag (N.m)", value=50.0, key=f"t_mag_{i}")

def _render_supports_editor(config, shaft):
    st.subheader("Bearings")
    c1, c2 = st.columns(2)
    # Default value logic to avoid 0.0 jumps if uninitialized?
    # Streamlit defaults key to 'value' on first run.
    # We used current_pos as default for B in sidebar.
    # We can try to approximate.
    c1.number_input("Bearing A Position (mm)", value=0.0, key="bearing_a_pos")
    c2.number_input("Bearing B Position (mm)", value=shaft.get_total_length(), key="bearing_b_pos")
