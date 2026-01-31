import streamlit as st
import os
from src.models.geometry import Shaft
from src.ui.sidebar import render_sidebar
from src.ui.visualization import plot_shaft_3d, plot_diagrams
import plotly.graph_objects as go

st.set_page_config(page_title="Shaft Designer", layout="wide", page_icon="⚙️")

def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "src", "ui", "style.css")
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def main():
    load_css()
    
    st.title("Shaft Designer")
    
    # Initialize Session State
    if 'shaft' not in st.session_state:
        st.session_state.shaft = Shaft()
    
    shaft = st.session_state.shaft
    
    # Render Sidebar Interface
    render_sidebar(shaft)
    
    # --- Main Layout ---
    
    # Top Section: 3D Visualization
    st.subheader("Model Visualization")
    fig_3d = plot_shaft_3d(shaft)
    st.plotly_chart(fig_3d, use_container_width=True)
    
    st.markdown("---")
    
    # Bottom Section: Analysis
    st.subheader("Analysis Results")
    
    # Run Analysis Button
    from src.analysis.statics import calculate_diagrams
    
    if st.button("Calculate Analysis", type="primary", use_container_width=True):
        x, V, M, T = calculate_diagrams(shaft)
        
        if len(x) > 0:
            # Create Tabs for Results
            tab_summary, tab_diagrams, tab_fatigue = st.tabs(["Summary", "Diagrams", "Fatigue"])
            
            with tab_summary:
                # Metric Summary
                max_moment = max(abs(M)) if len(M) > 0 else 0
                max_shear = max(abs(V)) if len(V) > 0 else 0
                max_torque = max(abs(T)) if len(T) > 0 else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Max Bending Moment", f"{max_moment:.2f} Nm")
                c2.metric("Max Shear Force", f"{max_shear:.2f} N")
                c3.metric("Max Torque", f"{max_torque:.2f} Nm")
                
            with tab_diagrams:
                # Plot Interactive Diagrams
                fig_diagrams = plot_diagrams(x, V, M, T)
                st.plotly_chart(fig_diagrams, use_container_width=True)
                
            with tab_fatigue:
                if shaft.material:
                    from src.analysis.fatigue import calculate_min_diameter
                    import numpy as np
                    
                    Sut = shaft.material.get('Sut', 380e6)
                    Sy = shaft.material.get('Sy', 205e6)
                    
                    # Calculate Min Diameter at each point
                    d_min_list = []
                    for m_val, t_val in zip(M, T):
                        # Conservative: Assume T is constant mean, M is fully reversed
                        d = calculate_min_diameter(moment_amp=abs(m_val), torque_avg=abs(t_val), 
                                                 Sut=Sut, Sy=Sy, n=2.0)
                        d_min_list.append(d)
                    
                    d_min_arr = np.array(d_min_list)
                    max_d_req = np.max(d_min_arr) if len(d_min_arr) > 0 else 0
                    
                    st.info(f"Material: **{shaft.material.get('name', 'Custom')}** | Sut: {Sut/1e6:.0f} MPa | Sy: {Sy/1e6:.0f} MPa")
                    st.metric("Max Required Diameter (Factor of Safety = 2.0)", f"{max_d_req:.2f} mm")
                    
                    # Diameter Constraint Plot
                    import pandas as pd
                    # Map 'x' back to current shaft design diameter
                    current_diameters = []
                    segments = shaft.get_segments()
                    for pos in x:
                        d_local = 0
                        for seg in segments:
                            if seg.start_node.position <= pos <= seg.end_node.position:
                                d_local = seg.diameter
                                break
                        current_diameters.append(d_local)
                    
                    # Use Plotly for this too for consistency? Or stick to simple chart for now?
                    # Let's stick to st.line_chart for this specific comparison as it's quick, 
                    # or better: upgrade to Plotly to match the theme.
                    
                    fig_fatigue = go.Figure()
                    fig_fatigue.add_trace(go.Scatter(x=x, y=d_min_arr, mode='lines', name='Required Diameter', line=dict(color='red', dash='dash')))
                    fig_fatigue.add_trace(go.Scatter(x=x, y=current_diameters, mode='lines', name='Current Diameter', fill='tozeroy', line=dict(color='lightgrey')))
                    fig_fatigue.update_layout(title="Diameter Check", xaxis_title="Position (mm)", yaxis_title="Diameter (mm)")
                    st.plotly_chart(fig_fatigue, use_container_width=True)
                else:
                    st.warning("Select a material in the sidebar to run fatigue analysis.")

        else:
            st.error("Could not calculate diagrams. Please check shaft geometry and supports.")
    else:
        st.info("Configure the shaft in the sidebar and click **Calculate Analysis**.")

if __name__ == "__main__":
    main()
