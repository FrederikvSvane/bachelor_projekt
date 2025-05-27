import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Tuple, Optional
# import pandas as pd  # Not needed for basic functionality
from dataclasses import dataclass
import colorsys


@dataclass
class SearchState:
    """Represents a state in the search process"""
    iteration: int
    score: float
    temperature: float
    schedule_features: np.ndarray  # Feature vector representing schedule
    move_type: str
    is_accepted: bool
    is_best: bool
    event_type: Optional[str] = None  # 'reheat', 'ruin_recreate', etc.


class EnergyFunnelVisualizer:
    """Creates an interactive 3D energy funnel visualization of the search landscape"""
    
    def __init__(self, states: List[SearchState]):
        self.states = states
        self.x_coords = None
        self.y_coords = None
        self.z_coords = None
        
    def reduce_dimensions(self, method='tsne', n_components=2, perplexity=30):
        """Reduce high-dimensional schedule features to 2D for visualization"""
        print(f"Reducing {len(self.states)} states to 2D using {method}...")
        
        # Extract feature vectors
        features = np.array([s.schedule_features for s in self.states])
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        if method == 'tsne':
            reducer = TSNE(n_components=n_components, perplexity=min(perplexity, len(self.states)-1), 
                          random_state=42, n_iter=1000)
            coords_2d = reducer.fit_transform(features_scaled)
        else:
            raise ValueError(f"Unknown method: {method}")
            
        self.x_coords = coords_2d[:, 0]
        self.y_coords = coords_2d[:, 1]
        self.z_coords = np.array([s.score for s in self.states])
        
    def temperature_to_color(self, temp: float, max_temp: float = 300) -> str:
        """Convert temperature to color (red=hot, blue=cold)"""
        # Normalize temperature to [0, 1]
        norm_temp = temp / max_temp
        
        # Use HSV color space: red (0°) to blue (240°)
        hue = 240 * (1 - norm_temp) / 360  # Convert to [0, 1] range
        rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        return f'rgb({int(rgb[0]*255)}, {int(rgb[1]*255)}, {int(rgb[2]*255)})'
    
    def create_surface(self, resolution=50):
        """Create the energy landscape surface using interpolation"""
        from scipy.interpolate import griddata
        
        # Create grid
        xi = np.linspace(self.x_coords.min(), self.x_coords.max(), resolution)
        yi = np.linspace(self.y_coords.min(), self.y_coords.max(), resolution)
        xi, yi = np.meshgrid(xi, yi)
        
        # Interpolate z values
        zi = griddata((self.x_coords, self.y_coords), self.z_coords, 
                     (xi, yi), method='cubic', fill_value=self.z_coords.max())
        
        return xi, yi, zi
    
    def create_visualization(self, title="Simulated Annealing Energy Funnel"):
        """Create the interactive 3D visualization"""
        
        if self.x_coords is None:
            self.reduce_dimensions()
            
        # Create surface
        xi, yi, zi = self.create_surface()
        
        # Create figure
        fig = go.Figure()
        
        # Add surface (the energy landscape)
        fig.add_trace(go.Surface(
            x=xi, y=yi, z=zi,
            colorscale='Viridis',
            opacity=0.8,
            name='Energy Landscape',
            showscale=True,
            colorbar=dict(title="Score", x=1.02),
            contours=dict(
                z=dict(show=True, usecolormap=True, highlightcolor="limegreen", project=dict(z=True))
            )
        ))
        
        # Prepare trajectory data
        max_temp = max(s.temperature for s in self.states)
        
        # Add search trajectory as animated scatter
        trajectory_x = []
        trajectory_y = []
        trajectory_z = []
        colors = []
        sizes = []
        hover_texts = []
        symbols = []
        
        for i, state in enumerate(self.states):
            trajectory_x.append(self.x_coords[i])
            trajectory_y.append(self.y_coords[i])
            trajectory_z.append(self.z_coords[i])
            colors.append(self.temperature_to_color(state.temperature, max_temp))
            
            # Size based on whether it's a special event
            size = 8
            if state.is_best:
                size = 15
            elif state.event_type:
                size = 12
                
            sizes.append(size)
            
            # Hover text
            hover_text = (f"Iteration: {state.iteration}<br>"
                         f"Score: {state.score:.2f}<br>"
                         f"Temperature: {state.temperature:.2f}<br>"
                         f"Move: {state.move_type}<br>"
                         f"Accepted: {state.is_accepted}")
            if state.event_type:
                hover_text += f"<br>Event: {state.event_type}"
            hover_texts.append(hover_text)
            
            # Symbol based on move type or event (using valid 3D symbols)
            if state.is_best:
                symbols.append('diamond')  # Use diamond for best solutions
            elif state.event_type == 'reheat':
                symbols.append('cross')
            elif state.event_type == 'ruin_recreate':
                symbols.append('square')
            else:
                symbols.append('circle')
        
        # Add trajectory
        fig.add_trace(go.Scatter3d(
            x=trajectory_x,
            y=trajectory_y,
            z=trajectory_z,
            mode='markers+lines',
            marker=dict(
                size=sizes,
                color=trajectory_z,  # Use z values for color instead of custom colors
                colorscale='RdBu_r',  # Red to Blue reversed (hot to cold)
                showscale=False,
                symbol=symbols,
                line=dict(width=1, color='black'),
                opacity=0.8
            ),
            line=dict(
                width=2,
                color='rgba(255, 255, 255, 0.3)'
            ),
            text=hover_texts,
            hoverinfo='text',
            name='Search Trajectory'
        ))
        
        # Add best solution markers
        best_indices = [i for i, s in enumerate(self.states) if s.is_best]
        if best_indices:
            fig.add_trace(go.Scatter3d(
                x=[self.x_coords[i] for i in best_indices],
                y=[self.y_coords[i] for i in best_indices],
                z=[self.z_coords[i] for i in best_indices],
                mode='markers',
                marker=dict(
                    size=20,
                    color='gold',
                    symbol='diamond',  # Use diamond for best solutions
                    line=dict(width=2, color='black')
                ),
                name='Best Solutions',
                hovertext=[f"Best at iteration {self.states[i].iteration}" for i in best_indices]
            ))
        
        # Create animation frames
        frames = []
        for k in range(10, len(self.states), max(1, len(self.states)//100)):  # 100 frames max
            frame_data = []
            
            # Trajectory up to current point
            frame_data.append(go.Scatter3d(
                x=trajectory_x[:k],
                y=trajectory_y[:k],
                z=trajectory_z[:k],
                mode='markers+lines',
                marker=dict(
                    size=sizes[:k],
                    color=trajectory_z[:k],
                    colorscale='RdBu_r',
                    showscale=False,
                    symbol=symbols[:k],
                    line=dict(width=1, color='black'),
                    opacity=0.8
                ),
                line=dict(
                    width=2,
                    color='rgba(255, 255, 255, 0.3)'
                ),
                text=hover_texts[:k],
                hoverinfo='text',
                name='Search Trajectory'
            ))
            
            # Current position highlight
            frame_data.append(go.Scatter3d(
                x=[trajectory_x[k-1]],
                y=[trajectory_y[k-1]],
                z=[trajectory_z[k-1]],
                mode='markers',
                marker=dict(
                    size=25,
                    color='red',  # Highlight current position in red
                    symbol='circle',
                    line=dict(width=3, color='white')
                ),
                name='Current Position'
            ))
            
            frames.append(go.Frame(
                data=frame_data,
                name=str(k),
                traces=[1, 2]  # Update trajectory and current position
            ))
        
        # Add play/pause buttons
        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    direction="left",
                    buttons=[
                        dict(
                            args=[None, {"frame": {"duration": 50, "redraw": True},
                                       "fromcurrent": True, "transition": {"duration": 0}}],
                            label="Play",
                            method="animate"
                        ),
                        dict(
                            args=[[None], {"frame": {"duration": 0, "redraw": True},
                                         "mode": "immediate",
                                         "transition": {"duration": 0}}],
                            label="Pause",
                            method="animate"
                        )
                    ],
                    pad={"r": 10, "t": 87},
                    showactive=False,
                    x=0.1,
                    xanchor="right",
                    y=0,
                    yanchor="top"
                )
            ],
            sliders=[{
                "active": 0,
                "yanchor": "top",
                "xanchor": "left",
                "currentvalue": {
                    "font": {"size": 20},
                    "prefix": "Iteration:",
                    "visible": True,
                    "xanchor": "right"
                },
                "transition": {"duration": 0},
                "pad": {"b": 10, "t": 50},
                "len": 0.9,
                "x": 0.1,
                "y": 0,
                "steps": [
                    {
                        "args": [[f.name], {"frame": {"duration": 0, "redraw": True},
                                          "mode": "immediate",
                                          "transition": {"duration": 0}}],
                        "label": str(self.states[int(f.name)-1].iteration),
                        "method": "animate"
                    }
                    for f in frames
                ]
            }]
        )
        
        # Update layout
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title="Configuration Space X",
                yaxis_title="Configuration Space Y",
                zaxis_title="Objective Score",
                zaxis=dict(
                    range=[0, max(self.z_coords) * 1.1],  # Start at 0, go to max score + 10%
                    rangemode='tozero'
                ),
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                ),
                aspectmode='manual',
                aspectratio=dict(x=1, y=1, z=0.5)
            ),
            width=1200,
            height=800,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        # Add frames
        fig.frames = frames
        
        return fig
    
    def save_html(self, filename="energy_funnel.html"):
        """Save the visualization as an interactive HTML file"""
        fig = self.create_visualization()
        fig.write_html(filename)
        print(f"Saved visualization to {filename}")
        
        
def extract_schedule_features(schedule) -> np.ndarray:
    """Extract features from a schedule for dimensionality reduction"""
    features = []
    
    # Get appointments list
    appointments = list(schedule.iter_appointments())
    
    # Basic counts
    features.append(len(appointments))
    features.append(len(schedule.get_all_judges()))
    features.append(len(schedule.get_all_rooms()))
    
    # Time distribution
    time_slots = [appt.timeslot_in_day for appt in appointments]
    days = [appt.day for appt in appointments]
    if time_slots:
        features.append(np.mean(time_slots))
        features.append(np.std(time_slots))
        features.append(min(time_slots))
        features.append(max(time_slots))
    else:
        features.extend([0, 0, 0, 0])
    
    # Day distribution
    if days:
        features.append(np.mean(days))
        features.append(np.std(days))
    else:
        features.extend([0, 0])
    
    # Room utilization
    room_counts = {}
    for appt in appointments:
        room_counts[appt.room.room_id] = room_counts.get(appt.room.room_id, 0) + 1
    
    if room_counts:
        features.append(np.mean(list(room_counts.values())))
        features.append(np.std(list(room_counts.values())))
    else:
        features.extend([0, 0])
    
    # Judge workload
    judge_counts = {}
    for appt in appointments:
        judge_counts[appt.judge.judge_id] = judge_counts.get(appt.judge.judge_id, 0) + 1
    
    if judge_counts:
        features.append(np.mean(list(judge_counts.values())))
        features.append(np.std(list(judge_counts.values())))
    else:
        features.extend([0, 0])
    
    # Gap score (if available)
    if hasattr(schedule, 'capacity_calculator'):
        features.append(schedule.capacity_calculator.get_gap_score())
    else:
        features.append(0)  # Default value if not available
    
    return np.array(features)


def create_sample_visualization():
    """Create a sample visualization with synthetic data"""
    np.random.seed(42)
    n_iterations = 1000
    
    # Generate synthetic search states
    states = []
    best_score = float('inf')
    current_x, current_y = 0, 0
    
    for i in range(n_iterations):
        # Temperature cooling
        temp = 300 * (0.95 ** (i // 50))
        
        # Random walk in configuration space
        dx = np.random.normal(0, 0.5)
        dy = np.random.normal(0, 0.5)
        
        # Occasionally jump (ruin & recreate)
        if i % 100 == 0 and i > 0:
            dx *= 10
            dy *= 10
            event_type = 'ruin_recreate'
        elif i % 200 == 0 and i > 0:
            temp = 300  # Reheat
            event_type = 'reheat'
        else:
            event_type = None
            
        current_x += dx
        current_y += dy
        
        # Score based on distance from optimum (with noise)
        score = (current_x - 5)**2 + (current_y - 5)**2 + np.random.normal(0, 5)
        
        # Features (synthetic)
        features = np.array([current_x, current_y, score, temp, i])
        
        is_best = score < best_score
        if is_best:
            best_score = score
            
        move_types = ['swap_judge', 'swap_room', 'move_time', 'contracting', 'insert']
        
        states.append(SearchState(
            iteration=i,
            score=score,
            temperature=temp,
            schedule_features=features,
            move_type=np.random.choice(move_types),
            is_accepted=True if score < best_score + temp/10 else False,
            is_best=is_best,
            event_type=event_type
        ))
    
    # Create visualizer
    viz = EnergyFunnelVisualizer(states)
    viz.x_coords = np.array([s.schedule_features[0] for s in states])
    viz.y_coords = np.array([s.schedule_features[1] for s in states])
    viz.z_coords = np.array([s.score for s in states])
    
    # Save visualization
    viz.save_html("/Users/frederik/projects/personal/bachelor_projekt/src/util/data_visualizer/energy_funnel_demo.html")
    return viz


if __name__ == "__main__":
    # Create sample visualization
    create_sample_visualization()