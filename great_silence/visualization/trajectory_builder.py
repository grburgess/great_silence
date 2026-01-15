"""Build expansion trajectory lines from civilization colonization data."""

import numpy as np
from typing import List, Dict, Any, Optional
from .plotly_3d_viz import ColorMapper


class TrajectoryBuilder:
    """
    Build expansion trajectory lines showing parent→colony connections.

    Creates line segments from a civilization's home world to its colonies,
    color-coded by root civilization using colorcet palettes.
    """

    def __init__(self, simulation, color_mapper: Optional[ColorMapper] = None):
        """
        Initialize trajectory builder.

        Args:
            simulation: GalaxySimulation instance
            color_mapper: Optional ColorMapper (creates default if None)
        """
        self.simulation = simulation
        self.galaxy_positions = simulation.galaxy.positions
        self.color_mapper = color_mapper or ColorMapper(
            palette_name="rainbow_bgyr_35_85_c73",
            n_colors=200
        )

    def build_trajectories_for_time(self, current_time_myr: float) -> List[Dict[str, Any]]:
        """
        Build all trajectory lines visible at current time.

        Args:
            current_time_myr: Current simulation time in Myr

        Returns:
            List of trajectory dictionaries with x/y/z coordinates and colors
        """
        trajectories = []

        for civ in self.simulation.civilizations:
            if civ.birth_time_myr > current_time_myr:
                continue  # Not born yet

            civ_trajectories = self._build_civ_trajectories(civ, current_time_myr)
            trajectories.extend(civ_trajectories)

        return trajectories

    def _build_civ_trajectories(self, civ, current_time_myr: float) -> List[Dict[str, Any]]:
        """
        Build trajectories for a single civilization.

        Args:
            civ: CivilizationState object
            current_time_myr: Current simulation time in Myr

        Returns:
            List of trajectory line segments
        """
        trajectories = []

        # Get color for this civilization (rgba format)
        color = self.color_mapper.civ_id_to_rgba(civ.civ_id, opacity=1.0)

        # Parent star is the root/home world
        parent_idx = civ.parent_star_idx
        parent_pos = self.galaxy_positions[parent_idx]

        # Build lines from parent to each colony that has arrived
        for colony_idx, arrival_time in civ.colony_arrival_times.items():
            # Skip if not arrived yet
            if arrival_time > current_time_myr:
                continue

            # Skip self (home world is in colony list)
            if colony_idx == parent_idx:
                continue

            colony_pos = self.galaxy_positions[colony_idx]

            # Create line segment
            # Use None to create breaks between separate line segments
            trajectories.append({
                'x': [parent_pos[0], colony_pos[0], None],
                'y': [parent_pos[1], colony_pos[1], None],
                'z': [parent_pos[2], colony_pos[2], None],
                'color': color,
                'civ_id': civ.civ_id,
            })

        return trajectories

    def get_trajectory_lines(self, current_time_myr: float) -> Dict[str, Any]:
        """
        Get all trajectory data as concatenated line data for plotly.

        Args:
            current_time_myr: Current simulation time in Myr

        Returns:
            Dictionary with concatenated x/y/z arrays and color list
        """
        trajectories = self.build_trajectories_for_time(current_time_myr)

        if not trajectories:
            return {
                'x': [],
                'y': [],
                'z': [],
                'colors': []
            }

        # Concatenate all line segments
        all_x = []
        all_y = []
        all_z = []

        for traj in trajectories:
            all_x.extend(traj['x'])
            all_y.extend(traj['y'])
            all_z.extend(traj['z'])

        # Use first trajectory color for the entire trace
        # (plotly Scatter3d doesn't support per-segment colors easily)
        color = trajectories[0]['color'] if trajectories else 'rgb(150, 150, 150)'

        return {
            'x': all_x,
            'y': all_y,
            'z': all_z,
            'color': color,
            'num_lines': len(trajectories)
        }

    def get_trajectory_traces_by_civilization(self, current_time_myr: float) -> Dict[int, Dict[str, Any]]:
        """
        Get trajectory data grouped by civilization for proper color-coding.

        Args:
            current_time_myr: Current simulation time in Myr

        Returns:
            Dictionary mapping civ_id to trajectory data dict with x/y/z/color
        """
        trajectories = self.build_trajectories_for_time(current_time_myr)

        if not trajectories:
            return {}

        # Group by civilization
        civ_traces = {}
        for traj in trajectories:
            civ_id = traj['civ_id']
            if civ_id not in civ_traces:
                civ_traces[civ_id] = {
                    'x': [],
                    'y': [],
                    'z': [],
                    'color': traj['color']
                }

            civ_traces[civ_id]['x'].extend(traj['x'])
            civ_traces[civ_id]['y'].extend(traj['y'])
            civ_traces[civ_id]['z'].extend(traj['z'])

        return civ_traces
