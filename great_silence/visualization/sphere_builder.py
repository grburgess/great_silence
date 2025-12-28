"""Build translucent spheres for civilization influence zones."""

import numpy as np
import plotly.graph_objects as go
from typing import List, Optional
from .plotly_3d_viz import ColorMapper


class SphereBuilder:
    """
    Build mesh3d spheres for civilization influence zones.

    Influence radius is calculated as the distance from the home world
    to the furthest colonized star.
    """

    def __init__(self, color_mapper: Optional[ColorMapper] = None):
        """
        Initialize sphere builder.

        Args:
            color_mapper: Optional ColorMapper (creates default if None)
        """
        self.color_mapper = color_mapper or ColorMapper(
            palette_name="rainbow_bgyr_35_85_c73",
            n_colors=200
        )

    def build_sphere(self, center: np.ndarray, radius: float,
                    color: str, opacity: float = 0.1,
                    resolution: int = 12) -> go.Mesh3d:
        """
        Build mesh3d sphere.

        Args:
            center: (x, y, z) center position in kpc
            radius: Sphere radius in kpc
            color: RGB color string
            opacity: Sphere opacity (0-1), default 0.1 for translucency
            resolution: Mesh resolution (12=low, 20=medium, 32=high)

        Returns:
            plotly Mesh3d object
        """
        # Generate sphere vertices using spherical coordinates
        u = np.linspace(0, 2 * np.pi, resolution)
        v = np.linspace(0, np.pi, resolution)

        # Meshgrid for spherical coordinates
        u_grid, v_grid = np.meshgrid(u, v)

        # Convert to Cartesian coordinates
        x = center[0] + radius * np.sin(v_grid) * np.cos(u_grid)
        y = center[1] + radius * np.sin(v_grid) * np.sin(u_grid)
        z = center[2] + radius * np.cos(v_grid)

        # Flatten arrays for plotly Mesh3d
        x_flat = x.flatten()
        y_flat = y.flatten()
        z_flat = z.flatten()

        return go.Mesh3d(
            x=x_flat,
            y=y_flat,
            z=z_flat,
            alphahull=0,  # Use convex hull
            opacity=opacity,
            color=color,
            showlegend=False,
            hoverinfo='skip',
            flatshading=True  # Smoother appearance
        )

    def build_influence_spheres(self, civilizations: List,
                                galaxy_positions: np.ndarray,
                                current_time_myr: float) -> List[go.Mesh3d]:
        """
        Build influence spheres for all civilizations at current time.

        Args:
            civilizations: List of CivilizationState objects
            galaxy_positions: Galaxy star positions array
            current_time_myr: Current simulation time in Myr

        Returns:
            List of Mesh3d sphere objects
        """
        spheres = []

        for civ in civilizations:
            # Skip if not born yet
            if civ.birth_time_myr > current_time_myr:
                continue

            # Skip if extinct before current time
            if not civ.is_active and civ.death_time_myr is not None and civ.death_time_myr < current_time_myr:
                continue

            # Calculate influence radius
            radius = self._calculate_influence_radius(
                civ, galaxy_positions, current_time_myr
            )

            if radius == 0:
                continue  # No colonies yet

            # Get center (home world position)
            center = galaxy_positions[civ.parent_star_idx]

            # Get color for this civilization (rgba format with opacity)
            color = self.color_mapper.civ_id_to_rgba(civ.civ_id, opacity=0.1)

            # Build sphere
            sphere = self.build_sphere(center, radius, color, opacity=0.1, resolution=12)
            spheres.append(sphere)

        return spheres

    def _calculate_influence_radius(self, civ, galaxy_positions: np.ndarray,
                                    current_time_myr: float) -> float:
        """
        Calculate influence radius as distance to furthest colonized star.

        Args:
            civ: CivilizationState object
            galaxy_positions: Galaxy star positions array
            current_time_myr: Current simulation time in Myr

        Returns:
            Radius in kpc
        """
        if not civ.colonized_stars:
            return 0.0

        root_pos = galaxy_positions[civ.parent_star_idx]
        max_distance = 0.0

        # Find furthest colony that has arrived
        for colony_idx, arrival_time in civ.colony_arrival_times.items():
            # Skip if not arrived yet
            if arrival_time > current_time_myr:
                continue

            # Skip self
            if colony_idx == civ.parent_star_idx:
                continue

            colony_pos = galaxy_positions[colony_idx]
            distance = np.linalg.norm(colony_pos - root_pos)
            max_distance = max(max_distance, distance)

        return max_distance
