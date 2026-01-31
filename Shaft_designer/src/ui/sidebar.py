import streamlit as st
from src.models.geometry import Shaft
from src.database.materials import MATERIALS

def render_sidebar(shaft: Shaft) -> dict:
    """
    Renders the sidebar for global shaft configuration.
    Returns a dictionary with configuration parameters.
    """
    st.sidebar.header("Global Settings")
    
    # Material Selection
    mat_name = st.sidebar.selectbox("Material", list(MATERIALS.keys()))
    shaft.material = MATERIALS[mat_name]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Model Dimensions")
    
    # Global Counts
    num_sections = st.sidebar.number_input("Number of Sections", min_value=1, max_value=20, value=3)
    num_forces = st.sidebar.number_input("Number of Radial Forces", min_value=0, max_value=10, value=0)
    num_torques = st.sidebar.number_input("Number of Torques", min_value=0, max_value=5, value=0)
    
    return {
        "num_sections": int(num_sections),
        "num_forces": int(num_forces),
        "num_torques": int(num_torques)
    }
