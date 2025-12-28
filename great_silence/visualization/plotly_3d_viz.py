"""
Advanced 3D Plotly visualization system for galactic civilization simulations.

Provides clean, high-performance 3D scatter plots with multiple toggleable layers,
animation support, and hover tooltips. Built for 100k+ point performance using
WebGL rendering (Scattergl).
"""

import numpy as np
import plotly.graph_objects as go
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import colorcet as cc


# ============================================================================
# CONFIGURATION SECTION - Customize visualization appearance here
# ============================================================================

@dataclass
class VisualizationConfig:
    """Central configuration for all visualization parameters."""

    # 3D Camera and layout
    camera_eye: Tuple[float, float, float] = (1.5, 1.5, 1.3)
    camera_center: Tuple[float, float, float] = (0, 0, 0)
    camera_up: Tuple[float, float, float] = (0, 0, 1)

    # Background and styling
    background_color: str = "rgb(0, 0, 0)"  # Pure black
    paper_bgcolor: str = "rgb(0, 0, 0)"
    plot_bgcolor: str = "rgb(0, 0, 0)"

    # Star field rendering
    star_size: float = 1.5  # Increased from 1.0 for better visibility
    star_opacity: float = 0.35  # Increased from 0.15 for better visibility
    star_color: str = "rgb(220, 220, 220)"  # Slightly brighter gray

    # Civilization markers
    civ_active_size: float = 6.0
    civ_active_opacity: float = 0.9
    civ_extinct_size: float = 4.0
    civ_extinct_opacity: float = 0.5
    civ_extinct_marker: str = "x"

    # Kardashev coloring (for active civilizations)
    kardashev_colorscale: str = "Plasma"  # "Plasma", "Viridis", "Hot", "Turbo"
    kardashev_min: float = 0.7
    kardashev_max: float = 3.0

    # Civilization root color palette
    # Best colorcet palettes for many distinct colors on black background:
    # "tab20_r" (20 distinct), "rainbow_bgyr_35-85" (smooth, many colors)
    # "xkcd" (many named colors), "cividis" (colorblind friendly)
    # "rainbow_bgyr_35-85_s25" (perceptually uniform, many colors)
    root_palette: str = "tab20_r"  # Changed via get_root_color_palette()

    # Sphere rendering
    sphere_color: str = "rgba(100, 150, 255, 0.1)"
    sphere_edge_color: str = "rgba(100, 150, 255, 0.3)"
    sphere_line_width: float = 1.0

    # Figure dimensions
    width: int = 1400
    height: int = 900

    # Animation
    animation_frame_duration: int = 50  # milliseconds per frame
    transition_duration: int = 50


class ColorMapper:
    """Robust color assignment for civilization IDs and Kardashev scales."""

    def __init__(self, palette_name: str = "tab20_r", n_colors: int = 100):
        """
        Initialize color mapper with a specific palette.

        Args:
            palette_name: colorcet palette name (e.g., "tab20_r", "rainbow_bgyr_35-85_s25")
            n_colors: Maximum number of unique colors needed
        """
        self.palette_name = palette_name
        self.n_colors = n_colors
        self._colors_cache = {}
        self._color_array = self._get_palette_colors(palette_name, n_colors)

    def _get_palette_colors(self, palette_name: str, n_colors: int) -> np.ndarray:
        """
        Get color array from colorcet palette.

        Args:
            palette_name: colorcet palette name
            n_colors: Number of colors to sample

        Returns:
            Array of RGB tuples (normalized 0-1)
        """
        try:
            # Colorcet uses underscores in attribute names, not hyphens
            palette_attr = palette_name.replace('-', '_')

            # Get palette colors (colorcet palettes are lists of RGB values already)
            rgb_colors = getattr(cc, palette_attr)

            # Sample n_colors from the palette
            if len(rgb_colors) >= n_colors:
                # Sample evenly if palette is large enough
                indices = np.linspace(0, len(rgb_colors) - 1, n_colors, dtype=int)
                sampled_colors = [rgb_colors[i] for i in indices]
            else:
                # Cycle if we need more colors than palette provides
                sampled_colors = [rgb_colors[i % len(rgb_colors)] for i in range(n_colors)]

            return np.array(sampled_colors)

        except Exception as e:
            print(f"Warning: Could not load palette {palette_name}: {e}")
            print("Falling back to 'glasbey'")
            try:
                rgb_colors = cc.glasbey
                sampled_colors = [rgb_colors[i % len(rgb_colors)] for i in range(n_colors)]
                return np.array(sampled_colors)
            except:
                # Final fallback: generate random colors
                print("Using random colors")
                return np.random.rand(n_colors, 3)

    def civ_id_to_rgba(self, civ_id: int, opacity: float = 1.0) -> str:
        """
        Map civilization ID to RGBA color string.

        Cycles through palette gracefully. Each root civilization gets
        a unique color based on its ID.

        Args:
            civ_id: Civilization ID (any integer)
            opacity: Alpha value (0-1)

        Returns:
            RGBA color string like "rgba(255, 100, 50, 0.8)"
        """
        if civ_id not in self._colors_cache:
            # Use modulo to cycle through available colors
            idx = civ_id % self.n_colors
            rgba = self._color_array[idx]
            self._colors_cache[civ_id] = rgba

        rgba = self._colors_cache[civ_id]
        r, g, b = [int(c * 255) for c in rgba[:3]]
        return f"rgba({r}, {g}, {b}, {opacity})"

    def kardashev_to_rgba(self, kardashev_level: float, colorscale: str = "Plasma") -> str:
        """
        Map Kardashev level to color using a continuous colorscale.

        Args:
            kardashev_level: Kardashev scale value (typically 0.7-3.0)
            colorscale: Plotly colorscale name

        Returns:
            RGBA color string
        """
        # Normalize to [0, 1]
        normalized = max(0, min(1, (kardashev_level - 0.7) / (3.0 - 0.7)))

        # Define colorscale (simplified versions of Plotly scales)
        scales = {
            "Plasma": [
                [0.0, "rgb(13, 8, 135)"],      # Dark purple
                [0.5, "rgb(228, 26, 28)"],     # Red
                [1.0, "rgb(253, 253, 187)"]    # Yellow
            ],
            "Viridis": [
                [0.0, "rgb(68, 1, 84)"],       # Dark purple
                [0.5, "rgb(35, 139, 69)"],     # Green
                [1.0, "rgb(253, 231, 37)"]     # Yellow
            ],
            "Hot": [
                [0.0, "rgb(0, 0, 0)"],         # Black
                [0.5, "rgb(255, 0, 0)"],       # Red
                [1.0, "rgb(255, 255, 0)"]      # Yellow
            ]
        }

        scale = scales.get(colorscale, scales["Plasma"])

        # Linear interpolation between scale stops
        if normalized <= 0.5:
            # Interpolate between first and middle
            t = normalized * 2
            c1 = scale[0][1]
            c2 = scale[1][1]
        else:
            # Interpolate between middle and last
            t = (normalized - 0.5) * 2
            c1 = scale[1][1]
            c2 = scale[2][1]

        # Parse RGB and interpolate
        def parse_rgb(rgb_str):
            rgb_str = rgb_str.replace("rgb(", "").replace(")", "")
            return [int(x.strip()) for x in rgb_str.split(",")]

        r1, g1, b1 = parse_rgb(c1)
        r2, g2, b2 = parse_rgb(c2)

        r = int(r1 * (1 - t) + r2 * t)
        g = int(g1 * (1 - t) + g2 * t)
        b = int(b1 * (1 - t) + b2 * t)

        return f"rgb({r}, {g}, {b})"


# ============================================================================
# MAIN VISUALIZATION CLASS
# ============================================================================

class Plotly3DGalaxyViz:
    """
    High-performance 3D galaxy visualization using Plotly with WebGL.

    Features:
    - Black background with no visible axes/grids
    - Multiple toggleable trace layers
    - Scattergl for 100k+ point performance
    - HTML hover tooltips with multi-line info
    - Animation support with time frames
    - Expanding spheres for influence zones
    """

    def __init__(self, config: Optional[VisualizationConfig] = None):
        """
        Initialize visualizer.

        Args:
            config: VisualizationConfig instance (uses defaults if None)
        """
        self.config = config or VisualizationConfig()
        self.color_mapper = ColorMapper(
            palette_name=self.config.root_palette,
            n_colors=100
        )
        self.fig: Optional[go.Figure] = None

    # ========================================================================
    # LAYER CREATION METHODS
    # ========================================================================

    def create_star_field_trace(
        self,
        stellar_positions: np.ndarray,
        name: str = "Stars",
        visible: bool = True
    ) -> go.Scattergl:
        """
        Create background star field trace using Scattergl (WebGL).

        Args:
            stellar_positions: Array of shape (N, 3) with star positions in kpc
            name: Legend name
            visible: Whether trace is initially visible

        Returns:
            go.Scattergl trace object
        """
        return go.Scattergl(
            x=stellar_positions[:, 0],
            y=stellar_positions[:, 1],
            z=stellar_positions[:, 2],
            mode='markers',
            marker=dict(
                size=self.config.star_size,
                color=self.config.star_color,
                opacity=self.config.star_opacity,
                line=dict(width=0)
            ),
            text=[f"Star" for _ in range(len(stellar_positions))],
            hovertemplate="<b>Star</b><br>Pos: (%.2f, %.2f, %.2f) kpc<extra></extra>",
            name=name,
            visible=visible,
            legendgroup="background",
            showlegend=True
        )

    def create_active_civ_trace(
        self,
        civ_positions: np.ndarray,
        civ_ids: np.ndarray,
        kardashev_levels: np.ndarray,
        parent_star_names: Optional[List[str]] = None,
        use_root_colors: bool = False,
        name: str = "Active Civilizations",
        visible: bool = True
    ) -> go.Scattergl:
        """
        Create active civilization trace, colored by Kardashev level or root ID.

        Args:
            civ_positions: Array of shape (N, 3) with civilization positions
            civ_ids: Array of civilization IDs (for root color assignment)
            kardashev_levels: Array of Kardashev scale values (0.7-3.0)
            parent_star_names: Optional list of parent star names for tooltips
            use_root_colors: If True, color by root civilization ID. If False, by Kardashev.
            name: Legend name
            visible: Whether trace is initially visible

        Returns:
            go.Scattergl trace object
        """
        if len(civ_positions) == 0:
            return go.Scattergl(x=[], y=[], z=[], name=name, visible=visible)

        # Prepare colors
        if use_root_colors:
            colors = [
                self.color_mapper.civ_id_to_rgba(cid, self.config.civ_active_opacity)
                for cid in civ_ids
            ]
            colorscale_info = "Color: Root Civilization"
        else:
            colors = [
                self.color_mapper.kardashev_to_rgba(kd, self.config.kardashev_colorscale)
                for kd in kardashev_levels
            ]
            colorscale_info = f"Kardashev: {kardashev_levels.min():.2f}-{kardashev_levels.max():.2f}"

        # Prepare hover text
        hover_texts = []
        for i in range(len(civ_positions)):
            star_name = parent_star_names[i] if parent_star_names else f"Star {civ_ids[i]}"
            hover_text = (
                f"<b>Civilization {int(civ_ids[i])}</b><br>"
                f"Parent: {star_name}<br>"
                f"Kardashev: {kardashev_levels[i]:.2f}<br>"
                f"Position: ({civ_positions[i, 0]:.1f}, {civ_positions[i, 1]:.1f}, {civ_positions[i, 2]:.1f}) kpc"
            )
            hover_texts.append(hover_text)

        return go.Scattergl(
            x=civ_positions[:, 0],
            y=civ_positions[:, 1],
            z=civ_positions[:, 2],
            mode='markers',
            marker=dict(
                size=self.config.civ_active_size,
                color=colors,
                opacity=self.config.civ_active_opacity,
                line=dict(color='rgba(255, 255, 255, 0.5)', width=1)
            ),
            text=hover_texts,
            hovertemplate="%{text}<extra></extra>",
            name=name,
            visible=visible,
            legendgroup="civilizations",
            showlegend=True
        )

    def create_extinct_civ_trace(
        self,
        extinct_positions: np.ndarray,
        extinct_ids: np.ndarray,
        parent_star_names: Optional[List[str]] = None,
        name: str = "Extinct Civilizations",
        visible: bool = True
    ) -> go.Scattergl:
        """
        Create extinct civilization trace (shown as X markers).

        Args:
            extinct_positions: Array of shape (N, 3)
            extinct_ids: Array of extinct civilization IDs
            parent_star_names: Optional list of parent star names
            name: Legend name
            visible: Whether trace is initially visible

        Returns:
            go.Scattergl trace object
        """
        if len(extinct_positions) == 0:
            return go.Scattergl(x=[], y=[], z=[], name=name, visible=visible)

        hover_texts = []
        for i in range(len(extinct_positions)):
            star_name = parent_star_names[i] if parent_star_names else f"Star {extinct_ids[i]}"
            hover_text = (
                f"<b>Civilization {int(extinct_ids[i])} (Extinct)</b><br>"
                f"Parent: {star_name}<br>"
                f"Position: ({extinct_positions[i, 0]:.1f}, {extinct_positions[i, 1]:.1f}, {extinct_positions[i, 2]:.1f}) kpc"
            )
            hover_texts.append(hover_text)

        return go.Scattergl(
            x=extinct_positions[:, 0],
            y=extinct_positions[:, 1],
            z=extinct_positions[:, 2],
            mode='markers',
            marker=dict(
                size=self.config.civ_extinct_size,
                color='rgba(200, 50, 50, 0.6)',
                symbol='x',
                line=dict(color='rgba(255, 100, 100, 0.8)', width=2)
            ),
            text=hover_texts,
            hovertemplate="%{text}<extra></extra>",
            name=name,
            visible=visible,
            legendgroup="civilizations",
            showlegend=True
        )

    def create_expansion_lines_trace(
        self,
        civ_positions: Dict[int, np.ndarray],
        colonized_positions: Dict[int, List[np.ndarray]],
        civ_ids: np.ndarray,
        name: str = "Expansion",
        visible: bool = True
    ) -> go.Scatter3d:
        """
        Create lines showing expansion from parent star to colonies.

        Args:
            civ_positions: Dict mapping civ_id -> parent position array
            colonized_positions: Dict mapping civ_id -> list of colony positions
            civ_ids: Array of civilization IDs
            name: Legend name
            visible: Whether trace is initially visible

        Returns:
            go.Scatter3d trace object with line mode
        """
        all_x, all_y, all_z = [], [], []
        colors = []

        for civ_id in civ_ids:
            if civ_id not in civ_positions or civ_id not in colonized_positions:
                continue

            parent_pos = civ_positions[civ_id]
            color = self.color_mapper.civ_id_to_rgba(civ_id, 0.4)

            for colony_pos in colonized_positions[civ_id]:
                # Add line segment: parent -> colony
                all_x.extend([parent_pos[0], colony_pos[0], None])
                all_y.extend([parent_pos[1], colony_pos[1], None])
                all_z.extend([parent_pos[2], colony_pos[2], None])
                colors.extend([color, color, None])

        if len(all_x) == 0:
            return go.Scatter3d(x=[], y=[], z=[], name=name, visible=visible)

        return go.Scatter3d(
            x=all_x,
            y=all_y,
            z=all_z,
            mode='lines',
            line=dict(color=colors, width=1),
            hoverinfo='skip',
            name=name,
            visible=visible,
            legendgroup="expansion",
            showlegend=True
        )

    def create_influence_sphere_trace(
        self,
        center_positions: np.ndarray,
        radii: np.ndarray,
        civ_ids: np.ndarray,
        name: str = "Influence Zones",
        visible: bool = True
    ) -> go.Mesh3d:
        """
        Create translucent spheres representing civilization influence zones.

        PERFORMANCE NOTE: For 10-100 spheres, this works well. For more,
        consider sampling or simplifying sphere resolution.

        Args:
            center_positions: Array of shape (N, 3) sphere centers
            radii: Array of shape (N,) sphere radii in kpc
            civ_ids: Array of civilization IDs (for coloring)
            name: Legend name
            visible: Whether trace is initially visible

        Returns:
            go.Mesh3d trace object
        """
        if len(center_positions) == 0:
            return go.Mesh3d(x=[], y=[], z=[], name=name, visible=visible)

        # Create sphere mesh for first civilization, then combine
        # For many spheres, consider creating separate traces instead
        all_x, all_y, all_z = [], [], []

        for center, radius, civ_id in zip(center_positions, radii, civ_ids):
            x, y, z = self._create_sphere_mesh(center, radius, resolution=12)
            all_x.extend(x)
            all_y.extend(y)
            all_z.extend(z)

        color = self.config.sphere_color

        return go.Mesh3d(
            x=all_x,
            y=all_y,
            z=all_z,
            opacity=0.1,
            color=color,
            showlegend=True,
            name=name,
            visible=visible
        )

    @staticmethod
    def _create_sphere_mesh(
        center: np.ndarray,
        radius: float,
        resolution: int = 12
    ) -> Tuple[List, List, List]:
        """
        Create x, y, z coordinates for a sphere mesh.

        Args:
            center: Center position [x, y, z]
            radius: Sphere radius
            resolution: Mesh resolution (lower = fewer points, faster)

        Returns:
            Tuple of (x_list, y_list, z_list) for all mesh points
        """
        u = np.linspace(0, 2 * np.pi, resolution)
        v = np.linspace(0, np.pi, resolution)

        x = radius * np.outer(np.cos(u), np.sin(v)) + center[0]
        y = radius * np.outer(np.sin(u), np.sin(v)) + center[1]
        z = radius * np.outer(np.ones(np.size(u)), np.cos(v)) + center[2]

        return x.flatten().tolist(), y.flatten().tolist(), z.flatten().tolist()

    # ========================================================================
    # FIGURE ASSEMBLY AND LAYOUT
    # ========================================================================

    def create_figure(
        self,
        stellar_positions: np.ndarray,
        active_civs: List,
        extinct_civs: Optional[List] = None,
        title: str = "Galactic Civilization Simulation"
    ) -> go.Figure:
        """
        Create complete 3D figure with all layers and proper layout.

        Args:
            stellar_positions: Background star positions (N, 3)
            active_civs: List of active CivilizationState objects
            extinct_civs: Optional list of extinct CivilizationState objects
            title: Figure title

        Returns:
            Plotly Figure object ready to display/save
        """
        fig = go.Figure()

        # Add star field (background)
        star_trace = self.create_star_field_trace(stellar_positions)
        fig.add_trace(star_trace)

        # Extract active civilization data
        if active_civs:
            active_positions = np.array([
                stellar_positions[civ.parent_star_idx] for civ in active_civs
            ])
            active_ids = np.array([civ.civ_id for civ in active_civs])
            active_kardashev = np.array([civ.kardashev_scale for civ in active_civs])

            # Add active civilizations (colored by Kardashev)
            active_trace = self.create_active_civ_trace(
                active_positions,
                active_ids,
                active_kardashev,
                use_root_colors=False
            )
            fig.add_trace(active_trace)

        # Extract extinct civilization data
        if extinct_civs:
            extinct_positions = np.array([
                stellar_positions[civ.parent_star_idx] for civ in extinct_civs
            ])
            extinct_ids = np.array([civ.civ_id for civ in extinct_civs])

            extinct_trace = self.create_extinct_civ_trace(
                extinct_positions,
                extinct_ids
            )
            fig.add_trace(extinct_trace)

        # Configure layout - NO AXES, NO GRIDS, PURE BLACK BACKGROUND
        fig.update_layout(
            title=dict(text=title, font=dict(size=20, color="white")),
            width=self.config.width,
            height=self.config.height,

            # Black background
            paper_bgcolor=self.config.paper_bgcolor,
            plot_bgcolor=self.config.plot_bgcolor,

            # 3D scene configuration
            scene=dict(
                xaxis=dict(
                    visible=False,
                    showgrid=False,
                    showbackground=False,
                    showticklabels=False
                ),
                yaxis=dict(
                    visible=False,
                    showgrid=False,
                    showbackground=False,
                    showticklabels=False
                ),
                zaxis=dict(
                    visible=False,
                    showgrid=False,
                    showbackground=False,
                    showticklabels=False
                ),
                bgcolor=self.config.background_color,
                camera=dict(
                    eye=dict(x=self.config.camera_eye[0],
                            y=self.config.camera_eye[1],
                            z=self.config.camera_eye[2]),
                    center=dict(x=self.config.camera_center[0],
                               y=self.config.camera_center[1],
                               z=self.config.camera_center[2]),
                    up=dict(x=self.config.camera_up[0],
                           y=self.config.camera_up[1],
                           z=self.config.camera_up[2])
                )
            ),

            # Legend styling
            legend=dict(
                bgcolor="rgba(0, 0, 0, 0.7)",
                bordercolor="rgba(255, 255, 255, 0.3)",
                borderwidth=1,
                font=dict(color="white")
            ),

            # Font colors
            font=dict(color="white"),

            # Hover label styling
            hoverlabel=dict(
                bgcolor="rgba(0, 0, 0, 0.8)",
                bordercolor="rgba(255, 255, 255, 0.5)",
                font=dict(color="white", size=12)
            ),

            margin=dict(l=0, r=0, t=40, b=0)
        )

        self.fig = fig
        return fig

    def add_time_slider_and_animation(
        self,
        snapshots: List,
        time_labels: Optional[List[str]] = None
    ) -> None:
        """
        Convert figure to animated with time slider.

        Args:
            snapshots: List of visualization data at different times
            time_labels: Optional list of time labels (e.g., "0.5 Gyr")
        """
        if not self.fig:
            raise ValueError("Must create figure first with create_figure()")

        # TODO: Implement frame-based animation
        # This requires converting traces to frames
        pass

    def show(self) -> None:
        """Display figure in Jupyter notebook."""
        if self.fig:
            self.fig.show()

    def save_html(self, filepath: str) -> None:
        """
        Save figure as standalone HTML file.

        Args:
            filepath: Path to save HTML (e.g., "viz.html")
        """
        if self.fig:
            self.fig.write_html(filepath)
            print(f"Saved to {filepath}")

    def save_png(self, filepath: str, width: int = 1400, height: int = 900) -> None:
        """
        Save figure as PNG (requires kaleido).

        Args:
            filepath: Path to save PNG
            width: Image width
            height: Image height
        """
        if self.fig:
            try:
                self.fig.write_image(filepath, width=width, height=height)
                print(f"Saved to {filepath}")
            except ImportError:
                print("Warning: kaleido not installed. Install with: pip install kaleido")
