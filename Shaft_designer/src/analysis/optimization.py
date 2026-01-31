import streamlit as st
import numpy as np
from src.models.geometry import Shaft
from src.analysis.statics import calculate_diagrams
from src.analysis.fatigue import calculate_min_diameter, calculate_endurance_limit
from src.database.catalogs import STANDARD_DIAMETERS, get_next_standard_diameter

def optimize_shaft(shaft: Shaft, safety_factor: float = 2.0, max_iterations: int = 5) -> dict:
    """
    Iteratively adjusts the shaft diameters to meet the required safety factor.
    Returns a dictionary with the results of the optimization.
    Updates st.session_state['features'] and 'start_diameter' directly.
    """
    
    iteration_log = []
    
    # We need to recognize "Zones" of constant diameter.
    # In the Feature-based model, a Zone determines diameter from:
    # 1. Start (0.0) -> Controlled by 'start_diameter'.
    # 2. Shoulder (Pos X) -> Controlled by 'Shoulder' feature at Pos X.
    
    # We will identify these Zones by iterating through the CURRENT shaft nodes/segments,
    # and mapping them back to the features.
    
    for iteration in range(max_iterations):
        # 1. Run Analysis
        # We assume shaft geometry is up-to-date with features at start of loop.
        # (Caller should have called update_shaft_model)
        
        x, V, Ma, Mm, Ta, Tm = calculate_diagrams(shaft, num_points=200)
        
        if len(x) == 0:
            return {"success": False, "message": "Analysis failed to run."}
            
        changes_made = False
        
        # Group Segments into Zones
        # A Zone is a contiguous set of segments with the same diameter (or intended same diameter).
        # In our builder, `add_node` splits zones if we add a gear.
        # But logically, the diameter is constant between Shoulders.
        
        # Let's verify: `update_shaft_model` creates nodes at Shoulders.
        # It sets `diameter_right` for that node.
        # Any subsequent nodes (Gears) added inside that zone inherit that diameter.
        
        # So we can iterate segments. 
        # For each segment, calculate D_req.
        # Find the max D_req for the whole Zone.
        # Update the Zone's source.
        
        segments = shaft.get_segments()
        
        # Map: FeatureID (or "START") -> Max D_req seen in its zone
        zone_reqs = {} 
        
        features = st.session_state.get("features", [])
        shoulders = [f for f in features if f['type'] == 'Shoulder']
        shoulders.sort(key=lambda f: f['pos'])
        
        # Helper to find which feature controls a position 'pos' (start of segment)
        def get_controlling_source(pos):
            # If pos < first_shoulder, it's START
            if not shoulders or pos < shoulders[0]['pos']:
                return "START"
            
            # Find the last shoulder before or at pos
            # Since shoulders are sorted:
            candidate = None
            for s in shoulders:
                if s['pos'] <= pos + 1e-5: # Epsilon for match
                    candidate = s
                else:
                    break
            if candidate:
                return candidate['id']
            return "START" # Should not happen if logic holds
            
        
        for segment in segments:
            # Analyze this segment
            start_pos = segment.start_node.position
            end_pos = segment.end_node.position
            
            # Extract loads
            mask = (x >= start_pos) & (x <= end_pos)
            if not np.any(mask): continue
            
            # Get Max Loads
            # M -> Alternating (Ma), Mean (Mm)
            # T -> Alternating (Ta), Mean (Tm)
            
            # Note: calculate_min_diameter handles inputs in Nm. statics returns Nmm for Moment.
            ma_seg = np.max(np.abs(Ma[mask])) / 1000.0
            mm_seg = np.max(np.abs(Mm[mask])) / 1000.0
            ta_seg = np.max(np.abs(Ta[mask])) # Torque assumed Nm in statics (checked previously)
            tm_seg = np.max(np.abs(Tm[mask]))
            
            current_d = segment.diameter
            
            Sut = shaft.material.get('Sut', 380e6)
            Sy = shaft.material.get('Sy', 205e6)
            
            # Calc D_req
            d_guess = current_d
            # Quick conversion
            Se = calculate_endurance_limit(Sut, diameter=d_guess)
            d_req_mm = calculate_min_diameter(
                moment_amp=ma_seg, torque_avg=tm_seg,
                moment_mean=mm_seg, torque_amp=ta_seg,
                Sut=Sut, Sy=Sy, n=safety_factor, se_overwrite=Se
            )
            
            # Find closest standard diameter UP
            valid_diams = [d for d in STANDARD_DIAMETERS if d >= d_req_mm]
            suggested_d = valid_diams[0] if valid_diams else max(STANDARD_DIAMETERS)
            
            # Identify Source
            source_id = get_controlling_source(start_pos)
            
            # Track max required for this source
            if source_id not in zone_reqs:
                zone_reqs[source_id] = suggested_d
            else:
                zone_reqs[source_id] = max(zone_reqs[source_id], suggested_d)
        
        # Apply Updates
        for source_id, new_d in zone_reqs.items():
            if source_id == "START":
                current_start = st.session_state.get("start_diameter", 20.0)
                if abs(current_start - new_d) > 1e-3:
                    st.session_state["start_diameter"] = new_d
                    changes_made = True
                    iteration_log.append(f"Start Segments: {current_start} -> {new_d}")
            else:
                # Find feature
                feat = next((f for f in features if f['id'] == source_id), None)
                if feat:
                    old_d = feat['props']['diameter']
                    if abs(old_d - new_d) > 1e-3:
                        feat['props']['diameter'] = new_d
                        changes_made = True
                        iteration_log.append(f"Shoulder @ {feat['pos']}: {old_d} -> {new_d}")
                        
        if not changes_made:
            break
            
        # Rebuild Shaft for next iteration
        # We need to call update_shaft_model.
        # Since we modified st.session_state, we can call it.
        # BUT we need 'config'. 
        # In app.py, config has 'total_length'.
        # We can try to grab it from shaft length or session state if we trusted sidebars?
        # Sidebar no longer puts total_len in session_state explicitly unless we keyed it.
        # In sidebar.py: `st.sidebar.number_input(..., value=500.0)` NO KEY.
        
        # WORKAROUND: Use shaft.get_total_length() as proxy for config['total_length']
        # The length doesn't change during optimization (only diameters).
        
        mock_config = {'total_length': shaft.get_total_length()}
        
        from src.ui.editor import update_shaft_model
        update_shaft_model(shaft, mock_config)
        
    return {"success": True, "log": iteration_log}
