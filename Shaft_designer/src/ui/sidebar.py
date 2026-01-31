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
    
    # Global Config
    total_len = st.sidebar.number_input("Total Shaft Length (mm)", min_value=10.0, max_value=5000.0, value=500.0, step=10.0)
    
    st.sidebar.markdown("---")
    safety_factor = st.sidebar.number_input("Safety Factor (n)", min_value=1.1, max_value=10.0, value=2.0, step=0.1)

    return {
        "total_length": float(total_len),
        "safety_factor": float(safety_factor)
    }
