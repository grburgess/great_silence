"""High-level interactive 3D visualization for GalaticBot simulations."""

import numpy as np
import plotly.graph_objects as go
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .plotly_3d_viz import VisualizationConfig, ColorMapper


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
