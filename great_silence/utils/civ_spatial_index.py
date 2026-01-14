"""Spatial indexing for civilization territory overlap detection."""

import numpy as np
from scipy.spatial import cKDTree
from typing import Dict, Set, Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class ColonyInfo:
    """Information about a colony for spatial indexing."""

    star_idx: int
    civ_id: int
    position: np.ndarray
    strength: float
    arrival_time_myr: float
    is_home_world: bool = False


class CivilizationSpatialIndex:
    """
    Efficient spatial index for detecting territory overlaps between civilizations.

    Uses KD-tree for O(log N) queries instead of O(N²) scans.
    Maintains per-civilization colony maps for quick overlap detection.
    """

    def __init__(self, positions: np.ndarray):
        """
        Initialize spatial index with stellar positions.

        Args:
            positions: Array of shape (N_stars, 3) with stellar positions in kpc
        """
        self.positions = positions
        self.n_stars = positions.shape[0]
        self.tree = cKDTree(positions)

        self.civ_colonies: Dict[int, Set[int]] = {}
        self.civ_colony_info: Dict[int, Dict[int, ColonyInfo]] = {}

    def add_colony(
        self,
        civ_id: int,
        star_idx: int,
        strength: float = 1.0,
        arrival_time_myr: float = 0.0,
        is_home_world: bool = False,
    ) -> None:
        """
        Add a colony to the spatial index.

        Args:
            civ_id: Civilization ID
            star_idx: Star index
            strength: Colony strength multiplier
            arrival_time_myr: Time colony was established
            is_home_world: Whether this is the home world
        """
        if civ_id not in self.civ_colonies:
            self.civ_colonies[civ_id] = set()
            self.civ_colony_info[civ_id] = {}

        self.civ_colonies[civ_id].add(star_idx)

        self.civ_colony_info[civ_id][star_idx] = ColonyInfo(
            star_idx=star_idx,
            civ_id=civ_id,
            position=self.positions[star_idx],
            strength=strength,
            arrival_time_myr=arrival_time_myr,
            is_home_world=is_home_world,
        )

    def remove_colony(self, civ_id: int, star_idx: int) -> None:
        """
        Remove a colony from the spatial index.

        Args:
            civ_id: Civilization ID
            star_idx: Star index
        """
        if civ_id in self.civ_colonies:
            self.civ_colonies[civ_id].discard(star_idx)

        if civ_id in self.civ_colony_info:
            self.civ_colony_info[civ_id].pop(star_idx, None)

    def get_colony_info(self, civ_id: int, star_idx: int) -> Optional[ColonyInfo]:
        """
        Get colony information.

        Args:
            civ_id: Civilization ID
            star_idx: Star index

        Returns:
            ColonyInfo or None if not found
        """
        if civ_id in self.civ_colony_info:
            return self.civ_colony_info[civ_id].get(star_idx)
        return None

    def find_civilizations_in_range(self, center_star_idx: int, radius_pc: float) -> Set[int]:
        """
        Find all civilizations with colonies within range of a star.

        Args:
            center_star_idx: Center star index
            radius_pc: Search radius in parsecs

        Returns:
            Set of civilization IDs with colonies in range
        """
        center_pos = self.positions[center_star_idx]
        radius_kpc = radius_pc / 1000.0

        star_indices = self.tree.query_ball_point(center_pos, radius_kpc)

        civs_in_range = set()
        for star_idx in star_indices:
            for civ_id, colonies in self.civ_colonies.items():
                if star_idx in colonies:
                    civs_in_range.add(civ_id)

        return civs_in_range

    def find_territory_overlaps(
        self, civ_ids: Optional[List[int]] = None
    ) -> List[Tuple[int, int, Set[int]]]:
        """
        Find all territory overlaps between civilizations.

        Returns pairs of civ IDs that share stars, along with overlapping star indices.

        Args:
            civ_ids: List of civ IDs to check (None = check all)

        Returns:
            List of (civ_a_id, civ_b_id, overlapping_star_indices) tuples
        """
        if civ_ids is None:
            civ_ids = list(self.civ_colonies.keys())

        overlaps = []

        star_to_civs: Dict[int, Set[int]] = {}

        for civ_id in civ_ids:
            if civ_id not in self.civ_colonies:
                continue
            for star_idx in self.civ_colonies[civ_id]:
                if star_idx not in star_to_civs:
                    star_to_civs[star_idx] = set()
                star_to_civs[star_idx].add(civ_id)

        for star_idx, civs_at_star in star_to_civs.items():
            if len(civs_at_star) > 1:
                civ_list = sorted(civs_at_star)
                for i in range(len(civ_list)):
                    for j in range(i + 1, len(civ_list)):
                        civ_a = civ_list[i]
                        civ_b = civ_list[j]

                        existing = None
                        for overlap in overlaps:
                            if (overlap[0] == civ_a and overlap[1] == civ_b) or (
                                overlap[0] == civ_b and overlap[1] == civ_a
                            ):
                                existing = overlap
                                break

                        if existing:
                            existing[2].add(star_idx)
                        else:
                            overlaps.append((civ_a, civ_b, {star_idx}))

        return overlaps

    def find_nearby_enemy_colonies(
        self, civ_id: int, enemy_civ_ids: Set[int], radius_pc: float, min_stars: int = 1
    ) -> List[Tuple[int, float, float]]:
        """
        Find enemy colonies near this civilization's territory.

        Args:
            civ_id: Our civilization ID
            enemy_civ_ids: Set of enemy civilization IDs
            radius_pc: Search radius in parsecs
            min_stars: Minimum stars before considering this an area of interest

        Returns:
            List of (star_idx, distance_pc, strength) tuples
        """
        if civ_id not in self.civ_colonies:
            return []

        radius_kpc = radius_pc / 1000.0
        nearby_enemy_cols = []

        for star_idx in self.civ_colonies[civ_id]:
            center_pos = self.positions[star_idx]

            nearby_stars = self.tree.query_ball_point(center_pos, radius_kpc)

            for nearby_star_idx in nearby_stars:
                if nearby_star_idx == star_idx:
                    continue

                for enemy_id in enemy_civ_ids:
                    if enemy_id in self.civ_colony_info:
                        if nearby_star_idx in self.civ_colony_info[enemy_id]:
                            colony = self.civ_colony_info[enemy_id][nearby_star_idx]
                            distance_pc = (
                                np.linalg.norm(self.positions[nearby_star_idx] - center_pos)
                                * 1000.0
                            )

                            nearby_enemy_cols.append(
                                (nearby_star_idx, distance_pc, colony.strength)
                            )

        if len(nearby_enemy_cols) >= min_stars:
            return nearby_enemy_cols

        return []

    def get_frontier_colonies(self, civ_id: int, radius_pc: float) -> List[Tuple[int, int]]:
        """
        Identify frontier colonies (colonies near other civs).

        Args:
            civ_id: Civilization ID
            radius_pc: Frontier detection radius in parsecs

        Returns:
            List of (star_idx, num_nearby_enemies) tuples
        """
        if civ_id not in self.civ_colonies:
            return []

        frontier_cols = []
        radius_kpc = radius_pc / 1000.0

        for star_idx in self.civ_colonies[civ_id]:
            center_pos = self.positions[star_idx]
            nearby_stars = self.tree.query_ball_point(center_pos, radius_kpc)

            num_other_civs = 0
            for nearby_star_idx in nearby_stars:
                for other_civ_id in self.civ_colonies:
                    if other_civ_id != civ_id:
                        if nearby_star_idx in self.civ_colonies[other_civ_id]:
                            num_other_civs += 1
                            break

            if num_other_civs > 0:
                frontier_cols.append((star_idx, num_other_civs))

        return sorted(frontier_cols, key=lambda x: x[1], reverse=True)

    def find_path_between_colonies(
        self, civ_id: int, start_star_idx: int, end_star_idx: int, max_hops: int = 10
    ) -> Optional[List[int]]:
        """
        Find path through this civilization's colonies.

        Uses BFS to find shortest path.

        Args:
            civ_id: Civilization ID
            start_star_idx: Start star index
            end_star_idx: End star index
            max_hops: Maximum number of hops to search

        Returns:
            List of star indices forming path, or None if no path found
        """
        if civ_id not in self.civ_colonies:
            return None

        if (
            start_star_idx not in self.civ_colonies[civ_id]
            or end_star_idx not in self.civ_colonies[civ_id]
        ):
            return None

        if start_star_idx == end_star_idx:
            return [start_star_idx]

        from collections import deque

        queue = deque([(start_star_idx, [start_star_idx])])
        visited = {start_star_idx}

        while queue:
            current, path = queue.popleft()

            if len(path) > max_hops:
                continue

            center_pos = self.positions[current]

            radius_kpc = 0.002

            nearby_stars = self.tree.query_ball_point(center_pos, radius_kpc)

            for nearby_star_idx in nearby_stars:
                if nearby_star_idx in self.civ_colonies[civ_id]:
                    if nearby_star_idx == end_star_idx:
                        return path + [nearby_star_idx]

                    if nearby_star_idx not in visited:
                        visited.add(nearby_star_idx)
                        queue.append((nearby_star_idx, path + [nearby_star_idx]))

        return None
