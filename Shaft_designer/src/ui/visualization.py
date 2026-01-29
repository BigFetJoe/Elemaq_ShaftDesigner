import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from src.models.geometry import Shaft

def plot_shaft_3d(shaft: Shaft):
    """Plots the shaft in 3D using Plotly, including bearings and loads."""
    segments = shaft.get_segments()
    
    fig = go.Figure()
    
    # --- 1. Shaft Segments (Cylinders) ---
    for seg in segments:
        r = seg.diameter / 2.0
        x0 = seg.start_node.position
        x1 = seg.end_node.position
        
        # Cylinder mapping
        z = np.linspace(x0, x1, 10) # Axial direction
        theta = np.linspace(0, 2*np.pi, 24)
        theta_grid, z_grid = np.meshgrid(theta, z)
        x_grid = r * np.cos(theta_grid)
        y_grid = r * np.sin(theta_grid)
        
        # Plot surface
        fig.add_trace(go.Surface(
            x=z_grid, y=x_grid, z=y_grid,
            colorscale='Blues',
            showscale=False,
            opacity=0.9,
            name=f'Segment {seg.diameter}mm'
        ))
        
        # Add wireframe circle at ends for better definition
        for x_pos in [x0, x1]:
            xc = x_pos * np.ones_like(theta)
            yc = r * np.cos(theta)
            zc = r * np.sin(theta)
            fig.add_trace(go.Scatter3d(
                x=xc, y=yc, z=zc,
                mode='lines',
                line=dict(color='black', width=2),
                showlegend=False
            ))

    # --- 2. Bearings ---
    # We identify bearings by iterating through nodes
    for node in shaft.nodes:
        if node.element and "Bearing" in node.element.name:
            # Draw a support symbol (e.g., a cone or box)
            # Simplified: Use a Scatter3d marker (Diamond or Square)
            fig.add_trace(go.Scatter3d(
                x=[node.position], y=[0], z=[-node.diameter_left/2 * 1.2], # Below the shaft
                mode='markers+text',
                marker=dict(symbol='diamond', size=10, color='orange'),
                text=[node.element.name],
                textposition='bottom center',
                name='Bearing'
            ))

    # --- 3. Radial Forces ---
    for force in shaft.forces:
        # Convert angle to rads for display calculation
        rad = np.radians(force.angle)
        
        # Find local radius roughly (not critical, just visual)
        # We can just put it at a fixed distance or finding the node radius
        # For MVP, we stick to visual clarity. 
        r_vis = 20.0 # Default visual offset if unsure, or match nearby segment
        
        # Arrow Start (at shaft surface roughly)
        y0 = r_vis * np.cos(rad)
        z0 = r_vis * np.sin(rad)
        
        # Arrow End (pointing TO shaft usually, or FROM)
        # Let's draw arrows pointing TO the shaft
        length = 30.0
        y1 = (r_vis + length) * np.cos(rad)
        z1 = (r_vis + length) * np.sin(rad)
        
        fig.add_trace(go.Scatter3d(
            x=[force.position, force.position],
            y=[y1, y0],
            z=[z1, z0],
            mode='lines+markers',
            marker=dict(symbol='diamond', size=5), # Plotly 3D arrows are tricky, using lines for now
            line=dict(color='red', width=5),
            name=f'Force {force.magnitude}N'
        ))
        
        # Force Label
        fig.add_trace(go.Scatter3d(
            x=[force.position], y=[y1], z=[z1],
            mode='text',
            text=[f"F={force.magnitude}N"],
            textposition='top center',
            showlegend=False
        ))
        
    # --- 4. Torques ---
    for torque in shaft.torques:
        # Visualizing torque is hard in 3D without dedicated glyphs
        # Use a localized thick different colored ring or marker
        fig.add_trace(go.Scatter3d(
             x=[torque.position], y=[0], z=[25], # Floating above
             mode='markers+text',
             marker=dict(symbol='circle-open', size=12, color='green', line=dict(width=3)),
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
