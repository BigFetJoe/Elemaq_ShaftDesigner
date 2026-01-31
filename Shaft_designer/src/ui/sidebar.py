import streamlit as st
from src.models.geometry import Shaft, Bearing
from src.models.loads import RadialForce, Torque
from src.database.materials import MATERIALS
from src.database.catalogs import get_next_standard_diameter, STANDARD_DIAMETERS, find_nearest_standard

def render_sidebar(shaft: Shaft):
    """Renders the sidebar for shaft configuration."""
    st.sidebar.header("Shaft Configuration")
    
    # Material Selection
    mat_name = st.sidebar.selectbox("Material", list(MATERIALS.keys()))
    shaft.material = MATERIALS[mat_name]
    
    st.sidebar.markdown("---")
    
    # Tabs for different inputs
    tab_geo, tab_loads, tab_supports = st.sidebar.tabs(["Geometry", "Loads", "Supports"])
    
    with tab_geo:
        st.subheader("Shaft Sections")
        
        # Global Shaft Parameters
        col_g1, col_g2 = st.columns(2)
        num_sections = col_g1.number_input("Number of Sections", min_value=1, max_value=20, value=3)
        start_diameter = col_g2.selectbox("Start Diameter (mm)", STANDARD_DIAMETERS, index=4) # Default 20mm
        
        # Reset shaft nodes for regeneration
        shaft.nodes = [] 
        
        # Add initial node (Start of shaft)
        shaft.add_node(position=0.0, diameter_right=start_diameter)
        
        current_pos = 0.0
        current_diameter = start_diameter
        
        # Iterate to create sections
        for i in range(int(num_sections)):
            st.markdown(f"**Section {i+1}**")
            
            # Correct Logic:
            # The shoulder is at the END of section i (Node i+1).
            # We compare the transition node index (i+1) with the shaft center.
            # If transition is before or at center -> Step UP.
            # If transition is after center -> Step DOWN.
            is_step_up = (i + 1) <= (num_sections / 2.0)
            
            c1, c2 = st.columns(2)
            length = c1.number_input(f"Length (mm)", value=100.0, key=f"len_{i}")
            has_shoulder = c2.checkbox("Has Shoulder?", value=False, key=f"sh_{i}")
            
            next_diameter = current_diameter
            
            if has_shoulder:
                # Calculate next diameter based on catalog standards
                # NOTE: This is for initial estimation only.
                next_diameter = get_next_standard_diameter(current_diameter, step_up=is_step_up)
                
                # Check for minimum limit warning
                if not is_step_up and next_diameter == current_diameter:
                     # Check if we are actually at the minimum of the list
                     if current_diameter == min(STANDARD_DIAMETERS):
                         st.warning(f"Section {i+1}: Cannot reduce diameter further (Min {current_diameter}mm reached).")
            
            # Close the section
            current_pos += length
            
            # The node at the end of this section has:
            # diameter_left = diameter of this section (current_diameter)
            # diameter_right = diameter of the next section (next_diameter)
            shaft.add_node(position=current_pos, diameter_left=current_diameter, diameter_right=next_diameter)
            
            # Update for next iteration
            current_diameter = next_diameter

    with tab_loads:
        st.subheader("External Loads")
        
        # Forces
        with st.expander("Radial Forces"):
            num_forces = st.number_input("Count", min_value=0, max_value=5, value=0, key="num_forces")
            shaft.forces.clear() 
            
            for i in range(int(num_forces)):
                st.markdown(f"**Force {i+1}**")
                cols = st.columns(3)
                pos = cols[0].number_input(f"Pos (mm)", value=0.0, key=f"f_pos_{i}")
                mag = cols[1].number_input(f"Mag (N)", value=100.0, key=f"f_mag_{i}")
                angle = cols[2].number_input(f"Angle (deg)", value=0.0, key=f"f_ang_{i}")
                
                shaft.forces.append(RadialForce(magnitude=mag, angle=angle, position=pos))
        
        # Torques
        with st.expander("Torques"):
            num_torques = st.number_input("Count", min_value=0, max_value=5, value=0, key="num_torques")
            shaft.torques.clear()
            
            for i in range(int(num_torques)):
                st.markdown(f"**Torque {i+1}**")
                cols = st.columns(2)
                pos = cols[0].number_input(f"Pos (mm)", value=0.0, key=f"t_pos_{i}")
                mag = cols[1].number_input(f"Mag (N.m)", value=50.0, key=f"t_mag_{i}")
                
                shaft.torques.append(Torque(magnitude=mag, position=pos))

    with tab_supports:
        st.subheader("Bearings")
        st.write("Define Bearings position")
        col_b1, col_b2 = st.columns(2)
        pos_a = col_b1.number_input("Bearing A Position (mm)", value=0.0)
        pos_b = col_b2.number_input("Bearing B Position (mm)", value=current_pos) # Default to end
        
        bearing_a = Bearing(name="Bearing A")
        bearing_b = Bearing(name="Bearing B")
        
        shaft.add_node(position=pos_a, element=bearing_a)
        shaft.add_node(position=pos_b, element=bearing_b)
