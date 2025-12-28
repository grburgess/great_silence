"""High-level interactive 3D visualization for GalaticBot simulations."""

import numpy as np
import plotly.graph_objects as go
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .plotly_3d_viz import VisualizationConfig, ColorMapper


class TimelineData:
    """
    Pre-computed timeline data for animation frames.

    Builds frame-by-frame visualization data from simulation snapshots,
    filtering civilizations and hazard events by time.
    """

    def __init__(self, simulation):
        """
        Initialize timeline data from simulation.

        Args:
            simulation: GalaxySimulation instance with snapshots
        """
        self.simulation = simulation

        if not hasattr(simulation, 'snapshots') or not simulation.snapshots:
            raise ValueError("Simulation must have snapshots enabled for animation")

        self.time_points_gyr = [s.time_myr / 1000.0 for s in simulation.snapshots]
        self.frames = self._build_frames()

    def _build_frames(self) -> List[Dict[str, Any]]:
        """
        Build data for each animation frame.

        Returns:
            List of frame data dictionaries
        """
        frames = []
        for snapshot in self.simulation.snapshots:
            frame_data = self._build_frame_data(snapshot)
            frames.append(frame_data)
        return frames

    def _build_frame_data(self, snapshot) -> Dict[str, Any]:
        """
        Build visualization data for a single time point.

        Filters civilizations and hazard events based on snapshot time.

        Args:
            snapshot: SimulationSnapshot object

        Returns:
            Dictionary with frame data
        """
        current_time_myr = snapshot.time_myr

        # Filter civilizations by birth/death times
        # Active at this time: born before this time and either still alive or died after
        active_civs = [
            c for c in self.simulation.civilizations
            if c.birth_time_myr <= current_time_myr
            and (c.is_active or (c.death_time_myr is not None and c.death_time_myr > current_time_myr))
        ]

        # Extinct by this time: died before or at this time
        extinct_civs = [
            c for c in self.simulation.civilizations
            if c.death_time_myr is not None
            and c.death_time_myr <= current_time_myr
        ]

        # Filter hazard events up to this time
        hazard_events = []
        if hasattr(self.simulation, 'hazard_events') and self.simulation.hazard_events:
            hazard_events = [
                e for e in self.simulation.hazard_events
                if e.time_myr <= current_time_myr
            ]

        return {
            'time_gyr': current_time_myr / 1000.0,
            'time_myr': current_time_myr,
            'active_civilizations': active_civs,
            'extinct_civilizations': extinct_civs,
            'hazard_events': hazard_events,
            'active_count': len(active_civs),
            'extinct_count': len(extinct_civs),
        }


class Interactive3DVisualizer:
    """
    High-level interface for 3D galaxy visualization from simulation.

    Provides multi-layer visualization with toggleable elements:
    - Background stars
    - Active civilizations (colored by Kardashev level)
    - Extinct civilizations
    - Death markers (with cause)
    - Hazard events (supernovae, GRBs)
    """

    def __init__(self, simulation, config: Optional[VisualizationConfig] = None):
        """
        Initialize visualizer with simulation data.

        Args:
            simulation: GalaxySimulation instance
            config: Optional VisualizationConfig
        """
        self.simulation = simulation
        self.config = config or VisualizationConfig()
        self.color_mapper = ColorMapper(
            palette_name="rainbow_bgyr_35-85_c73",  # Good for many distinct colors
            n_colors=200
        )

    def create_static_figure(self,
                            show_stars: bool = True,
                            show_active: bool = True,
                            show_extinct: bool = True,
                            show_deaths: bool = False,
                            show_hazards: bool = False,
                            subsample_stars: int = 10000) -> go.Figure:
        """
        Create static multi-layer visualization.

        Args:
            show_stars: Show background star field
            show_active: Show active civilizations
            show_extinct: Show extinct civilizations
            show_deaths: Show death location markers
            show_hazards: Show hazard events (supernova/GRB)
            subsample_stars: Number of stars to display (for performance)

        Returns:
            Plotly Figure object
        """
        fig = go.Figure()

        # Layer 1: Background stars
        if show_stars:
            self._add_star_layer(fig, subsample_stars)

        # Layer 2: Active civilizations
        if show_active:
            self._add_active_civilization_layer(fig)

        # Layer 3: Extinct civilizations
        if show_extinct:
            self._add_extinct_civilization_layer(fig)

        # Layer 4: Death markers
        if show_deaths:
            self._add_death_marker_layer(fig)

        # Layer 5: Hazard events
        if show_hazards:
            self._add_hazard_event_layer(fig)

        # Apply pure black background, no grids/axes
        self._apply_layout(fig)

        return fig

    def create_animated_figure(self,
                               subsample_stars: int = 10000,
                               show_stars: bool = True,
                               show_hazards: bool = True) -> go.Figure:
        """
        Create animated 3D figure with time slider.

        Shows civilization lifecycle over time with play/pause controls
        and timeline slider.

        Args:
            subsample_stars: Number of background stars to display
            show_stars: Show background star field
            show_hazards: Show hazard events

        Returns:
            Plotly Figure with animation frames

        Raises:
            ValueError: If simulation doesn't have snapshots
        """
        # Build timeline data
        timeline = TimelineData(self.simulation)

        # Create base figure with first frame
        fig = self._build_frame_figure(timeline.frames[0], subsample_stars, show_stars, show_hazards)

        # Add animation frames
        frames = []
        for i, frame_data in enumerate(timeline.frames):
            frame_traces = self._build_frame_traces(frame_data, subsample_stars, show_stars, show_hazards)
            frames.append(go.Frame(
                data=frame_traces,
                name=f't_{i}',
                layout=go.Layout(
                    title=dict(
                        text=f"Time: {frame_data['time_gyr']:.2f} Gyr | Active: {frame_data['active_count']} | Extinct: {frame_data['extinct_count']}",
                        x=0.5,
                        xanchor='center'
                    )
                )
            ))

        fig.frames = frames

        # Add playback controls
        fig.update_layout(
            title=dict(
                text=f"Time: {timeline.time_points_gyr[0]:.2f} Gyr | Active: {timeline.frames[0]['active_count']} | Extinct: {timeline.frames[0]['extinct_count']}",
                x=0.5,
                xanchor='center',
                font=dict(size=16, color='white')
            ),
            updatemenus=[{
                'type': 'buttons',
                'showactive': False,
                'buttons': [
                    {
                        'label': '▶ Play',
                        'method': 'animate',
                        'args': [None, {
                            'frame': {'duration': 100, 'redraw': True},
                            'fromcurrent': True,
                            'mode': 'immediate',
                            'transition': {'duration': 50}
                        }]
                    },
                    {
                        'label': '⏸ Pause',
                        'method': 'animate',
                        'args': [[None], {
                            'frame': {'duration': 0, 'redraw': False},
                            'mode': 'immediate',
                            'transition': {'duration': 0}
                        }]
                    }
                ],
                'x': 0.1,
                'y': 1.15,
                'xanchor': 'left',
                'yanchor': 'top',
                'bgcolor': 'rgba(50, 50, 50, 0.7)',
                'bordercolor': 'rgba(255, 255, 255, 0.3)',
                'borderwidth': 1
            }],
            sliders=[{
                'active': 0,
                'yanchor': 'top',
                'y': 0,
                'xanchor': 'left',
                'x': 0.1,
                'len': 0.85,
                'currentvalue': {
                    'prefix': 'Time: ',
                    'suffix': ' Gyr',
                    'visible': True,
                    'xanchor': 'right',
                    'font': {'size': 14, 'color': 'white'}
                },
                'steps': [
                    {
                        'args': [[f't_{i}'], {
                            'frame': {'duration': 0, 'redraw': True},
                            'mode': 'immediate',
                            'transition': {'duration': 0}
                        }],
                        'label': f'{t:.2f}',
                        'method': 'animate'
                    }
                    for i, t in enumerate(timeline.time_points_gyr)
                ],
                'bgcolor': 'rgba(50, 50, 50, 0.7)',
                'bordercolor': 'rgba(255, 255, 255, 0.3)',
                'borderwidth': 1,
                'tickcolor': 'white',
                'font': {'color': 'white'}
            }]
        )

        return fig

    def _build_frame_figure(self, frame_data: Dict[str, Any],
                            subsample_stars: int,
                            show_stars: bool,
                            show_hazards: bool) -> go.Figure:
        """Build initial figure for animation from frame data."""
        fig = go.Figure()

        # Add stars layer
        if show_stars:
            self._add_star_layer(fig, subsample_stars)

        # Add civilization and hazard layers for this frame
        traces = self._build_frame_traces(frame_data, subsample_stars, show_stars, show_hazards)
        for trace in traces:
            # Skip stars trace since we already added it
            if trace.name != 'Stars':
                fig.add_trace(trace)

        # Apply layout
        self._apply_layout(fig)

        return fig

    def _build_frame_traces(self, frame_data: Dict[str, Any],
                            subsample_stars: int,
                            show_stars: bool,
                            show_hazards: bool) -> List[go.Scatter3d]:
        """Build traces for a single animation frame."""
        traces = []

        # Stars (only if showing)
        if show_stars:
            positions = self.simulation.galaxy.positions
            if len(positions) > subsample_stars:
                indices = np.random.choice(len(positions), subsample_stars, replace=False)
                positions = positions[indices]

            traces.append(go.Scatter3d(
                x=positions[:, 0],
                y=positions[:, 1],
                z=positions[:, 2],
                mode='markers',
                marker=dict(
                    size=self.config.star_size,
                    color=self.config.star_color,
                    opacity=self.config.star_opacity
                ),
                name='Stars',
                hoverinfo='skip'
            ))

        # Active civilizations
        active_civs = frame_data['active_civilizations']
        if active_civs:
            positions = self.simulation.galaxy.positions
            civ_positions = positions[[c.parent_star_idx for c in active_civs]]
            kardashev_levels = np.array([c.kardashev_scale for c in active_civs])
            tooltips = [self._build_civilization_tooltip(c) for c in active_civs]

            traces.append(go.Scatter3d(
                x=civ_positions[:, 0],
                y=civ_positions[:, 1],
                z=civ_positions[:, 2],
                mode='markers',
                marker=dict(
                    size=self.config.civ_active_size,
                    color=kardashev_levels,
                    colorscale=self.config.kardashev_colorscale,
                    cmin=self.config.kardashev_min,
                    cmax=self.config.kardashev_max,
                    opacity=self.config.civ_active_opacity,
                    colorbar=dict(
                        title='Kardashev<br>Level',
                        len=0.5,
                        y=0.8
                    )
                ),
                text=tooltips,
                hovertemplate='%{text}<extra></extra>',
                name='Active Civilizations'
            ))

        # Extinct civilizations
        extinct_civs = frame_data['extinct_civilizations']
        if extinct_civs:
            positions = self.simulation.galaxy.positions
            civ_positions = positions[[c.parent_star_idx for c in extinct_civs]]
            tooltips = [self._build_civilization_tooltip(c) for c in extinct_civs]

            traces.append(go.Scatter3d(
                x=civ_positions[:, 0],
                y=civ_positions[:, 1],
                z=civ_positions[:, 2],
                mode='markers',
                marker=dict(
                    size=self.config.civ_extinct_size,
                    color='rgb(150, 100, 100)',
                    opacity=self.config.civ_extinct_opacity,
                    symbol=self.config.civ_extinct_marker
                ),
                text=tooltips,
                hovertemplate='%{text}<extra></extra>',
                name='Extinct Civilizations'
            ))

        # Hazard events
        if show_hazards and frame_data['hazard_events']:
            events_by_type = {}
            for event in frame_data['hazard_events']:
                event_type = event.event_type
                if event_type not in events_by_type:
                    events_by_type[event_type] = []
                events_by_type[event_type].append(event)

            event_colors = {
                'supernova': 'rgb(255, 150, 0)',
                'grb': 'rgb(255, 255, 100)'
            }

            for event_type, events in events_by_type.items():
                positions = np.array([e.position for e in events])
                tooltips = [
                    f"<b>{e.event_type.upper()}</b><br>"
                    f"Time: {e.time_myr/1000:.2f} Gyr<br>"
                    f"Energy: {e.energy:.2e} ergs<br>"
                    f"Radius: {e.sterilization_radius_pc:.1f} pc<br>"
                    f"Affected civs: {len(e.affected_civ_ids)}"
                    for e in events
                ]

                traces.append(go.Scatter3d(
                    x=positions[:, 0],
                    y=positions[:, 1],
                    z=positions[:, 2],
                    mode='markers',
                    marker=dict(
                        size=10,
                        color=event_colors.get(event_type, 'rgb(255, 255, 255)'),
                        opacity=0.6,
                        symbol='diamond'
                    ),
                    text=tooltips,
                    hovertemplate='%{text}<extra></extra>',
                    name=f'Hazard: {event_type}'
                ))

        return traces

    def _add_star_layer(self, fig: go.Figure, subsample: int):
        """Add background star field layer."""
        positions = self.simulation.galaxy.positions

        # Subsample for performance
        if len(positions) > subsample:
            indices = np.random.choice(len(positions), subsample, replace=False)
            positions = positions[indices]

        fig.add_trace(go.Scatter3d(
            x=positions[:, 0],
            y=positions[:, 1],
            z=positions[:, 2],
            mode='markers',
            marker=dict(
                size=self.config.star_size,
                color=self.config.star_color,
                opacity=self.config.star_opacity
            ),
            name='Stars',
            hoverinfo='skip'  # No hover for stars (too many)
        ))

    def _add_active_civilization_layer(self, fig: go.Figure):
        """Add active civilizations layer (colored by Kardashev level)."""
        active_civs = [c for c in self.simulation.civilizations if c.is_active]

        if not active_civs:
            return

        positions = self.simulation.galaxy.positions
        civ_positions = positions[[c.parent_star_idx for c in active_civs]]

        # Kardashev levels for coloring
        kardashev_levels = np.array([c.kardashev_scale for c in active_civs])

        # Build tooltips
        tooltips = [self._build_civilization_tooltip(c) for c in active_civs]

        fig.add_trace(go.Scatter3d(
            x=civ_positions[:, 0],
            y=civ_positions[:, 1],
            z=civ_positions[:, 2],
            mode='markers',
            marker=dict(
                size=self.config.civ_active_size,
                color=kardashev_levels,
                colorscale=self.config.kardashev_colorscale,
                cmin=self.config.kardashev_min,
                cmax=self.config.kardashev_max,
                opacity=self.config.civ_active_opacity,
                colorbar=dict(
                    title='Kardashev<br>Level',
                    len=0.5,
                    y=0.8
                )
            ),
            text=tooltips,
            hovertemplate='%{text}<extra></extra>',
            name='Active Civilizations'
        ))

    def _add_extinct_civilization_layer(self, fig: go.Figure):
        """Add extinct civilizations layer."""
        extinct_civs = [c for c in self.simulation.civilizations if not c.is_active]

        if not extinct_civs:
            return

        positions = self.simulation.galaxy.positions
        civ_positions = positions[[c.parent_star_idx for c in extinct_civs]]

        # Build tooltips
        tooltips = [self._build_civilization_tooltip(c) for c in extinct_civs]

        fig.add_trace(go.Scatter3d(
            x=civ_positions[:, 0],
            y=civ_positions[:, 1],
            z=civ_positions[:, 2],
            mode='markers',
            marker=dict(
                size=self.config.civ_extinct_size,
                color='rgb(150, 100, 100)',  # Dim red
                opacity=self.config.civ_extinct_opacity,
                symbol=self.config.civ_extinct_marker
            ),
            text=tooltips,
            hovertemplate='%{text}<extra></extra>',
            name='Extinct Civilizations'
        ))

    def _add_death_marker_layer(self, fig: go.Figure):
        """Add death location markers with cause indicated."""
        dead_civs = [c for c in self.simulation.civilizations
                     if not c.is_active and c.death_cause]

        if not dead_civs:
            return

        # Group by death cause
        death_causes = {}
        for civ in dead_civs:
            cause = civ.death_cause
            if cause not in death_causes:
                death_causes[cause] = []
            death_causes[cause].append(civ)

        positions = self.simulation.galaxy.positions

        # Color map for death causes
        cause_colors = {
            'supernova': 'rgb(255, 100, 50)',
            'grb': 'rgb(255, 200, 50)',
            'self_destruction': 'rgb(200, 50, 255)',
            'old_age': 'rgb(150, 150, 150)',
            'extinction_event': 'rgb(100, 255, 100)'
        }

        for cause, civs in death_causes.items():
            civ_positions = positions[[c.parent_star_idx for c in civs]]
            tooltips = [f"<b>Extinction</b><br>Cause: {cause}<br>Time: {c.death_time_myr/1000:.2f} Gyr"
                       for c in civs]

            fig.add_trace(go.Scatter3d(
                x=civ_positions[:, 0],
                y=civ_positions[:, 1],
                z=civ_positions[:, 2],
                mode='markers',
                marker=dict(
                    size=8,
                    color=cause_colors.get(cause, 'rgb(200, 200, 200)'),
                    opacity=0.7,
                    symbol='x'
                ),
                text=tooltips,
                hovertemplate='%{text}<extra></extra>',
                name=f'Deaths: {cause}'
            ))

    def _add_hazard_event_layer(self, fig: go.Figure):
        """Add hazard event markers (supernovae, GRBs)."""
        if not hasattr(self.simulation, 'hazard_events') or not self.simulation.hazard_events:
            return

        # Group by event type
        events_by_type = {}
        for event in self.simulation.hazard_events:
            if event.event_type not in events_by_type:
                events_by_type[event.event_type] = []
            events_by_type[event.event_type].append(event)

        # Colors for event types
        event_colors = {
            'supernova': 'rgb(255, 150, 0)',
            'grb': 'rgb(255, 255, 100)'
        }

        for event_type, events in events_by_type.items():
            positions = np.array([e.position for e in events])
            tooltips = [
                f"<b>{e.event_type.upper()}</b><br>"
                f"Time: {e.time_myr/1000:.2f} Gyr<br>"
                f"Energy: {e.energy:.2e} ergs<br>"
                f"Radius: {e.sterilization_radius_pc:.1f} pc<br>"
                f"Affected civs: {len(e.affected_civ_ids)}"
                for e in events
            ]

            fig.add_trace(go.Scatter3d(
                x=positions[:, 0],
                y=positions[:, 1],
                z=positions[:, 2],
                mode='markers',
                marker=dict(
                    size=10,
                    color=event_colors.get(event_type, 'rgb(255, 255, 255)'),
                    opacity=0.6,
                    symbol='diamond'
                ),
                text=tooltips,
                hovertemplate='%{text}<extra></extra>',
                name=f'Hazard: {event_type}'
            ))

    def _build_civilization_tooltip(self, civ) -> str:
        """Build HTML tooltip for civilization marker."""
        positions = self.simulation.galaxy.positions
        pos = positions[civ.parent_star_idx]
        star_age = self.simulation.galaxy.ages[civ.parent_star_idx]
        star_metallicity = self.simulation.galaxy.metallicities[civ.parent_star_idx]

        status = 'Active' if civ.is_active else f'Extinct ({civ.death_cause})'
        death_info = f"<br>Death: {civ.death_time_myr/1000:.2f} Gyr" if not civ.is_active else ""

        tooltip = f"""<b>Civilization #{civ.civ_id}</b><br>
Birth: {civ.birth_time_myr/1000:.2f} Gyr<br>
Kardashev: {civ.kardashev_scale:.2f}<br>
Status: {status}{death_info}<br>
Colonies: {len(civ.colonized_stars)}<br>
<br>
<b>Star Properties</b><br>
Age: {star_age:.2f} Gyr<br>
[Fe/H]: {star_metallicity:.2f}<br>
Position: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) kpc"""

        return tooltip

    def _apply_layout(self, fig: go.Figure):
        """Apply pure black background layout with no grids/axes."""
        fig.update_layout(
            scene=dict(
                bgcolor=self.config.background_color,
                xaxis=dict(
                    visible=False,
                    showgrid=False,
                    showticklabels=False,
                    showbackground=False
                ),
                yaxis=dict(
                    visible=False,
                    showgrid=False,
                    showticklabels=False,
                    showbackground=False
                ),
                zaxis=dict(
                    visible=False,
                    showgrid=False,
                    showticklabels=False,
                    showbackground=False
                ),
                camera=dict(
                    eye=dict(
                        x=self.config.camera_eye[0],
                        y=self.config.camera_eye[1],
                        z=self.config.camera_eye[2]
                    )
                )
            ),
            paper_bgcolor=self.config.paper_bgcolor,
            plot_bgcolor=self.config.plot_bgcolor,
            showlegend=True,
            legend=dict(
                x=0.02,
                y=0.98,
                bgcolor='rgba(0, 0, 0, 0.5)',
                bordercolor='rgba(255, 255, 255, 0.3)',
                borderwidth=1
            ),
            width=self.config.width,
            height=self.config.height
        )
