"""Civilization expansion and colonization modeling."""

import numpy as np
from typing import List, Tuple, Optional


class ExpansionModel:
    """
    Model civilization expansion through space.

    Accounts for:
    - Travel time at sub-light speeds
    - Colonization wave fronts
    - Selection of colonization targets
    """

    def __init__(
        self,
        expansion_velocity_c: float,
        colonization_probability: float,
        max_range_pc: float
    ):
        """
        Initialize expansion model.

        Args:
            expansion_velocity_c: Expansion velocity as fraction of c
            colonization_probability: Probability of colonizing a candidate star
            max_range_pc: Maximum expansion range in parsecs
        """
        self.expansion_velocity_c = expansion_velocity_c
        self.colonization_probability = colonization_probability
        self.max_range_pc = max_range_pc

        # Speed of light in pc/yr
        self.c_pc_yr = 0.306601

    def find_colonization_candidates(
        self,
        colony_positions: np.ndarray,
        stellar_positions: np.ndarray,
        habitable_mask: np.ndarray,
        colonized_indices: set,
        current_time_myr: float
    ) -> List[Tuple[int, float]]:
        """
        Find stars that can be reached and colonized.

        Args:
            colony_positions: Positions of existing colonies
            stellar_positions: All stellar positions
            habitable_mask: Boolean mask of habitable stars
            colonized_indices: Set of already colonized star indices
            current_time_myr: Current simulation time

        Returns:
            List of (star_index, arrival_time_myr) tuples
        """
        candidates = []

        # Find habitable stars within range
        for star_idx in np.where(habitable_mask)[0]:
            if star_idx in colonized_indices:
                continue

            star_pos = stellar_positions[star_idx]

            # Check distance from any colony
            distances_kpc = np.linalg.norm(colony_positions - star_pos, axis=1)
            min_distance_pc = np.min(distances_kpc) * 1000

            if min_distance_pc > self.max_range_pc:
                continue

            # Calculate travel time
            # velocity in pc/yr = expansion_velocity_c * c_pc_yr
            # time in years = distance_pc / velocity_pc_yr
            # time in Myr = time_yr / 1e6
            velocity_pc_yr = self.expansion_velocity_c * self.c_pc_yr
            travel_time_yr = min_distance_pc / velocity_pc_yr
            travel_time_myr = travel_time_yr / 1e6

            arrival_time = current_time_myr + travel_time_myr

            candidates.append((int(star_idx), arrival_time))

        return candidates

    def select_colonies(
        self,
        candidates: List[Tuple[int, float]],
        rng: np.random.Generator,
        max_new_colonies: int = 10
    ) -> List[int]:
        """
        Select which candidates to actually colonize.

        Args:
            candidates: List of (star_index, arrival_time) tuples
            rng: Random number generator
            max_new_colonies: Maximum number of new colonies per time step

        Returns:
            List of selected star indices
        """
        if not candidates:
            return []

        # Randomly select subset
        n_select = min(max_new_colonies, len(candidates))

        # Apply colonization probability
        selected = []
        for star_idx, _ in rng.choice(candidates, size=n_select, replace=False):
            if rng.uniform(0, 1) < self.colonization_probability:
                selected.append(int(star_idx))

        return selected
