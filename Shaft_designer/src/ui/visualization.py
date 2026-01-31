import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from src.models.geometry import Shaft, Bearing, SpurGear, Pulley

def draw_cylinder(fig, start_pos, end_pos, diameter, color='blue', name='Cylinder', opacity=1.0):
    """Helper to draw a cylinder (shaft segment, gear, pulley)."""
    r = diameter / 2.0
    
    # Cylinder mapping
    z = np.linspace(start_pos, end_pos, 10) # Axial direction
    theta = np.linspace(0, 2*np.pi, 24)
    theta_grid, z_grid = np.meshgrid(theta, z)
    x_grid = r * np.cos(theta_grid)
    y_grid = r * np.sin(theta_grid)
    
    # Plot surface
    fig.add_trace(go.Surface(
        x=z_grid, y=x_grid, z=y_grid,
        colorscale=[[0, color], [1, color]],
        showscale=False,
        opacity=opacity,
        name=name,
        hoverinfo='name'
    ))
    
    # Add wireframe circle at ends for better definition
    for x_pos in [start_pos, end_pos]:
        xc = x_pos * np.ones_like(theta)
        yc = r * np.cos(theta)
        zc = r * np.sin(theta)
        fig.add_trace(go.Scatter3d(
            x=xc, y=yc, z=zc,
            mode='lines',
            line=dict(color='black', width=2),
            showlegend=False,
            hoverinfo='skip'
        ))
        
    # Draw caps (disks) to close the cylinder - important for thin objects like gears
    # Center points
    # fig.add_trace(go.Mesh3d(x=[start_pos]*len(theta), y=yc, z=zc, color=color, opacity=opacity)) # Mesh is harder to align simply

def draw_bearing_housing(fig, center_pos, shaft_diameter, housing_width=20.0, color='orange', name='Bearing'):
    """Draws a bearing housing as a box with a hole (simplified as a box for now)."""
    # Box dimensions
    h = shaft_diameter * 2.5 # Height
    w = housing_width        # Width (axial)
    d = shaft_diameter * 2.5 # Depth
    
    # Vertices of a cube centered at (center_pos, 0, 0)
    # x is axial
    x_min = center_pos - w/2
    x_max = center_pos + w/2
    y_min = -h/2
    y_max = h/2
    z_min = -d/2
    z_max = d/2 # Positioned so shaft goes through? 
    # Shaft is at y=0, z=0. 
    # Let's shift bearing down so shaft sits on it/in it. 
    # Pillow block usually sits below.
    # Center of bearing hole is 0,0.
    
    # Define 8 corners
    x = [x_min, x_min, x_max, x_max, x_min, x_min, x_max, x_max]
    y = [y_min, y_max, y_max, y_min, y_min, y_max, y_max, y_min]
    z = [z_min, z_min, z_min, z_min, z_max, z_max, z_max, z_max]
    
    # Plotly Mesh3d for box
    # 0: 000, 1: 010, 2: 110, 3: 100 
    # 4: 001, 5: 011, 6: 111, 7: 101
    
    fig.add_trace(go.Mesh3d(
        x=x, y=y, z=z,
        color=color,
        alphahull=0, # Convex hull
        opacity=0.8,
        name=name
    ))


def plot_shaft_3d(shaft: Shaft):
    """Plots the shaft in 3D using Plotly, including bearings and loads."""
    segments = shaft.get_segments()
    
    fig = go.Figure()
    
    # --- 1. Shaft Segments (Cylinders) ---
    for seg in segments:
        draw_cylinder(fig, seg.start_node.position, seg.end_node.position, seg.diameter, color='lightblue', name=f'Shaft {seg.diameter}mm')

    # --- 2. Bearings and Elements ---
    # iterate through nodes
    for i, node in enumerate(shaft.nodes):
        if node.element:
            el = node.element
            
            # Determine correct shaft diameter for the element
            # At start (i=0), shaft is to the right.
            # At end, shaft is to the left.
            # In middle, use max to prevent housing being smaller than shoulder (simplified).
            if i == 0:
                d_node = node.diameter_right
            elif i == len(shaft.nodes) - 1:
                d_node = node.diameter_left
            else:
                d_node = max(node.diameter_left, node.diameter_right)

            if isinstance(el, Bearing):
                # Draw Bearing
                width = el.width if hasattr(el, 'width') else 20.0
                draw_bearing_housing(fig, node.position, d_node, housing_width=width, color='orange', name=el.name)
                
            elif isinstance(el, SpurGear):
                # Draw Gear
                # Position is center.
                width = el.width
                d = el.diameter
                draw_cylinder(fig, node.position - width/2, node.position + width/2, d, color='grey', name=el.name, opacity=0.9)
                
            elif isinstance(el, Pulley):
                # Draw Pulley
                width = el.width
                d = el.diameter
                draw_cylinder(fig, node.position - width/2, node.position + width/2, d, color='red', name=el.name, opacity=0.9)
                
            elif "Bearing" in el.name: # Fallback for base class if named Bearing
                 draw_bearing_housing(fig, node.position, d_node, housing_width=20.0, color='orange', name=el.name)


    # --- 3. Radial Forces ---
    # Retrieve all forces (manual + element generated)
    all_forces, all_torques = shaft.get_all_loads()
    
    for force in all_forces:
        # Find if there is an element at this position (tolerance 1mm)
        associated_node = next((n for n in shaft.nodes if abs(n.position - force.position) < 1.0), None)
        
        # Default Visualization parameters
        # If no element, we assume it's directly on the shaft surface
        if associated_node:
            # Safest visual radius is the shaft radius
            # Handle edge case where diameter_left/right might be None if node init logic failed (shouldn't happen but good practice)
            d_l = associated_node.diameter_left if associated_node.diameter_left else 20.0
            d_r = associated_node.diameter_right if associated_node.diameter_right else 20.0
            r_vis = max(d_l, d_r) / 2.0
        else:
            r_vis = 20.0 # Fallback
            
        force_angle_rad = np.radians(force.angle)
        visual_angle_rad = force_angle_rad # Default: arrow comes from the force's direction
        
        # Override if Element matches
        if associated_node and associated_node.element:
            el = associated_node.element
            if isinstance(el, SpurGear):
                # For Gears, we want to visualize the force acting AT the mesh point
                r_vis = el.diameter / 2.0
                visual_angle_rad = np.radians(el.contact_angle)
            elif isinstance(el, Pulley):
                # For Pulleys, we visualize at the rim
                r_vis = el.diameter / 2.0
                # Pulley belt load is usually calculated as a resultant.
                # Visualization matches the vector direction (simplified)
                visual_angle_rad = force_angle_rad
            elif isinstance(el, Bearing):
                pass 
                # Bearings don't usually generate loads in this context (they support them), 
                # but if there is a load exactly at a bearing, it might be a reaction.
                # Leave on shaft or housing? Let's leave on shaft for now (hidden inside housing).

        # Arrow geometry
        # Tip touches the surface at (r_vis, visual_angle_rad)
        y_tip = r_vis * np.cos(visual_angle_rad)
        z_tip = r_vis * np.sin(visual_angle_rad)
        
        # Tail is further out. We draw arrow pointing TOWARDS the tip (Action on Shaft).
        length = 40.0
        y_tail = (r_vis + length) * np.cos(visual_angle_rad)
        z_tail = (r_vis + length) * np.sin(visual_angle_rad)
        
        fig.add_trace(go.Scatter3d(
            x=[force.position, force.position],
            y=[y_tail, y_tip],
            z=[z_tail, z_tip],
            mode='lines+markers',
            marker=dict(symbol='diamond', size=5), 
            line=dict(color='red', width=5),
            name=f'Force {force.magnitude:.0f}N'
        ))
        
        # Force Label (at the tail so it doesn't obscure the contact)
        fig.add_trace(go.Scatter3d(
            x=[force.position], y=[y_tail], z=[z_tail],
            mode='text',
            text=[f"F={force.magnitude:.0f}N"],
            textposition='top center',
            showlegend=False
        ))
        
    # --- 4. Torques ---
    for torque in all_torques:
        # Visualizing torque is hard in 3D without dedicated glyphs
        # Use a localized thick different colored ring or marker
        # Determine radius to place it
        node = next((n for n in shaft.nodes if abs(n.position - torque.position) < 1.0), None)
        r_vis = 20.0
        if node and node.element:
             if hasattr(node.element, 'diameter'):
                 r_vis = node.element.diameter / 2.0 + 10 # Slightly above element
        
        fig.add_trace(go.Scatter3d(
             x=[torque.position], y=[0], z=[r_vis], # Floating above
             mode='markers+text',
             marker=dict(symbol='diamond-open', size=12, color='green', line=dict(width=3)),
             text=[f"T={torque.magnitude}Nm"],
             textposition="top center",
             name='Torque'
        ))

    # Layout Updates
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (X)',
            yaxis_title='Radial (Y)',
            zaxis_title='Radial (Z)',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        showlegend=True,
        legend=dict(x=0, y=1)
    )
    
    return fig

def plot_diagrams(x, V, M, T):
    """Plots Share, Moment, and Torque diagrams using Plotly subplots."""
    
    fig = make_subplots(rows=3, cols=1, 
                        shared_xaxes=True,
                        vertical_spacing=0.1,
                        subplot_titles=("Bending Moment", "Shear Force", "Torque"))

    # Moment
    fig.add_trace(go.Scatter(x=x, y=M, fill='tozeroy', line=dict(color='#3498db'), name="Moment (Nm)"), row=1, col=1)
    
    # Shear
    fig.add_trace(go.Scatter(x=x, y=V, fill='tozeroy', line=dict(color='#e74c3c'), name="Shear (N)"), row=2, col=1)
    
    # Torque
    fig.add_trace(go.Scatter(x=x, y=T, fill='tozeroy', line=dict(color='#2ecc71'), name="Torque (Nm)"), row=3, col=1)

    fig.update_layout(height=800, showlegend=False, title_text="Static Analysis Results")
    fig.update_xaxes(title_text="Position (mm)", row=3, col=1)
    
    return fig
