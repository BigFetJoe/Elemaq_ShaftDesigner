
import streamlit as st
import os
import sys

# Ensure the project root is in the path so we can import 'src'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.geometry import Shaft
from src.ui.sidebar import render_sidebar
from src.ui.editor import render_editor, update_shaft_model
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
    
    # 1. Global Config (Sidebar)
    config = render_sidebar(shaft)
    
    # 2. Update Model based on State & Config
    # This ensures the shaft object is up-to-date with inputs even if they are hidden
    update_shaft_model(shaft, config)
    
    # 3. Visualization
    st.subheader("Model Visualization")
    fig_3d = plot_shaft_3d(shaft)
    st.plotly_chart(fig_3d, use_container_width=True)
    
    # 4. Detailed Editor
    render_editor(shaft, config)
    
    st.markdown("---")
    
    # Bottom Section: Analysis
    st.subheader("Analysis Results")
    
    # Run Analysis Button
    from src.analysis.statics import calculate_diagrams
    from src.analysis.optimization import optimize_shaft
    
    col_anal_1, col_anal_2 = st.columns([1, 1])
    
    with col_anal_1:
        run_analysis = st.button("Calculate Analysis", type="primary", use_container_width=True)
        
    with col_anal_2:
        auto_dim = st.button("Auto-Dimension Shaft ✨", type="secondary", use_container_width=True, help="Automatically adjusts diameters to meet Safety Factor")
        
    if auto_dim:
        with st.spinner("Optimizing shaft dimensions..."):
            # Pass safety factor from config or sidebar
            sf_val = config.get('safety_factor', 2.0)
            result = optimize_shaft(shaft, safety_factor=sf_val)
            
            if result['success']:
                st.success("Optimization Complete! Shaft updated.")
                st.session_state['optimization_log'] = result['log']
                st.rerun()
            else:
                st.error(f"Optimization Failed: {result.get('message')}")
    
    if run_analysis:
        # UPDATED UNPACKING: 6 values
        x, V, Ma, Mm, Ta, Tm = calculate_diagrams(shaft)
        
        # Combine for simplified Summary/Display
        # Total Moment Magnitude (at each point)
        # Note: Ma is alternating, Mm is mean. Max moment overall?
        # Usually we care about Ma for fatigue.
        # But for 'Max Bending Moment' metric, let's show Max(Ma + Mm) or just Max(Ma) if rotating?
        # Let's show Max Alternating Moment as it's the critical one for rotating shafts.
        M_display = Ma
        T_display = Tm # Usually torque is mean driven. 
        if max(abs(Ta)) > 0:
            T_display = Ta + Tm # Fallback for metric?
            
        
        if len(x) > 0:
            # Create Tabs for Results
            tab_summary, tab_diagrams, tab_fatigue = st.tabs(["Summary", "Diagrams", "Fatigue"])
            
            with tab_summary:
                # Metric Summary
                # M is in Nmm
                max_ma_nmm = max(abs(Ma)) if len(Ma) > 0 else 0
                max_ma_nm = max_ma_nmm / 1000.0
                
                max_shear = max(abs(V)) if len(V) > 0 else 0
                max_torque = max(abs(T_display)) if len(T_display) > 0 else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Max Alternating Moment", f"{max_ma_nm:.2f} Nm")
                c2.metric("Max Shear Force", f"{max_shear:.2f} N")
                c3.metric("Max Torque", f"{max_torque:.2f} Nm")
                
            with tab_diagrams:
                # Plot Interactive Diagrams
                # Convert M to Nm for plotting to be consistent
                # plot_diagrams expects x, V, M, T.
                # We can perform a clever trick: plot separate traces in plot_diagrams if we updated it,
                # or just plot the dominant ones.
                # For now, pass Ma as "Bending Moment" and Tm as "Torque".
                # TODO: Update plot_diagrams to show Mean/Alt if needed.
                
                Ma_nm = Ma / 1000.0
                # Mm_nm = Mm / 1000.0
                
                # We pass Ma as the primary 'Moment' because that's what designers look for in rotating shafts.
                fig_diagrams = plot_diagrams(x, V, Ma_nm, T_display)
                st.plotly_chart(fig_diagrams, use_container_width=True)
                
            with tab_fatigue:
                if shaft.material:
                    from src.analysis.fatigue import calculate_min_diameter
                    import numpy as np
                    
                    Sut = shaft.material.get('Sut', 380e6)
                    Sy = shaft.material.get('Sy', 205e6)
                    
                    # Calculate Min Diameter at each point
                    d_min_list = []
                    
                    # Gather Fatigue Config
                    fatigue_config = {
                        'surface': st.session_state.get('fatigue_surface', 'usinado'),
                        'reliability': st.session_state.get('fatigue_reliability', '99%'),
                        'temp': st.session_state.get('fatigue_temp', 20.0),
                        'kf': st.session_state.get('fatigue_kf', 1.0)
                    }
                    
                    for i in range(len(x)):
                        # Get local stress components (Nmm for moments, Nm for torques? Check statics units)
                        # statics.py sums: force(N) * dist(mm) = Nmm.
                        # so Ma, Mm are Nmm.
                        # Torques: inputs were Nm usually?
                        # loads.py: Torque magnitude. If input in UI is Nm...
                        # In editor.py: `cols[1].number_input(f"Mag (N.m)", ...)`
                        # So Torque is Nm.
                        # Wait, consistently?
                        # `statics.py`: `Tx += t.magnitude * ...`.
                        # If t.magnitude is Nm, then T(x) is Nm.
                        # Force is N, pos is mm. Moment is Nmm.
                        # We must be careful.
                        
                        ma_val = Ma[i] # Nmm
                        mm_val = Mm[i] # Nmm
                        ta_val = Ta[i] # Nm (if input was Nm)
                        tm_val = Tm[i] # Nm
                        
                        # Convert moments to Nm for fatigue func
                        ma_nm = ma_val / 1000.0
                        mm_nm = mm_val / 1000.0
                        
                        d = calculate_min_diameter(
                            moment_amp=abs(ma_nm), 
                            torque_mean=abs(tm_val),
                            moment_mean=abs(mm_nm),
                            torque_amp=abs(ta_val),
                            Sut=Sut, Sy=Sy, n=2.0,
                            fatigue_config=fatigue_config
                        )
                        d_min_list.append(d)
                    
                    d_min_arr = np.array(d_min_list)
                    max_d_req = np.max(d_min_arr) if len(d_min_arr) > 0 else 0
                    
                    st.info(f"Material: **{shaft.material.get('name', 'Custom')}** | Sut: {Sut/1e6:.0f} MPa | Sy: {Sy/1e6:.0f} MPa")
                    st.metric("Max Required Diameter (Factor of Safety = 2.0)", f"{max_d_req:.2f} mm")
                    
                    # Diameter Constraint Plot
                    
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
