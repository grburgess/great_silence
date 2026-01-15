"""Recovery queue for star sterilization tracking."""

import numpy as np
import heapq
from typing import List


class SterilizationStatus:
    """Enumeration-like class for star sterilization status."""

    HABITABLE = 0
    TEMPORARILY_STERILIZED = 1
    PERMANENTLY_STERILIZED = 2


class RecoveryQueue:
    """Priority queue for star recovery. O(log N) operations."""

    def __init__(self, n_stars: int):
        """Initialize recovery tracking arrays.

        Args:
            n_stars: Number of stars in galaxy
        """
        self.status = np.zeros(n_stars, dtype=int)
        self.recovery_heap: List[tuple[float, int]] = []
        self.in_queue: set[int] = set()
        self.stale_indices: set[int] = set()

    def sterilize_star(
        self,
        star_idx: int,
        current_time_myr: float,
        recovery_time_myr: float,
        permanent: bool = False,
    ):
        """Mark star as sterilized, schedule recovery if temporary.

        Args:
            star_idx: Index of star
            current_time_myr: Current simulation time (Myr)
            recovery_time_myr: Recovery duration (Myr)
            permanent: If True, star never recovers
        """
        if permanent:
            self.status[star_idx] = SterilizationStatus.PERMANENTLY_STERILIZED
        else:
            self.status[star_idx] = (
                SterilizationStatus.TEMPORARILY_STERILIZED
            )

            if star_idx in self.in_queue:
                self.stale_indices.add(star_idx)

            recovery_time = current_time_myr + recovery_time_myr
            heapq.heappush(self.recovery_heap, (recovery_time, star_idx))
            self.in_queue.add(star_idx)

    def sterilize_batch(
        self,
        star_indices: np.ndarray,
        current_time_myr: float,
        recovery_times_myr: np.ndarray,
        permanent_mask: np.ndarray,
    ):
        """Batch sterilization for efficiency.

        Args:
            star_indices: (K,) indices of affected stars
            current_time_myr: Current simulation time (Myr)
            recovery_times_myr: (K,) recovery durations (Myr)
            permanent_mask: (K,) boolean mask for permanent sterilization
        """
        permanent_idx = star_indices[permanent_mask]
        self.status[permanent_idx] = (
            SterilizationStatus.PERMANENTLY_STERILIZED
        )

        temp_mask = ~permanent_mask
        temp_indices = star_indices[temp_mask]
        temp_times = recovery_times_myr[temp_mask]

        for idx, rt in zip(temp_indices, temp_times):
            self.sterilize_star(idx, current_time_myr, rt, permanent=False)

    def process_recoveries(self, current_time_myr: float) -> List[int]:
        """Process all stars that have recovered.

        Complexity: O(k log N) where k = recovered stars

        Args:
            current_time_myr: Current simulation time (Myr)

        Returns:
            List of recovered star indices
        """
        recovered = []
        while (
            self.recovery_heap
            and self.recovery_heap[0][0] <= current_time_myr
        ):
            recovery_time, star_idx = heapq.heappop(self.recovery_heap)
            if star_idx in self.stale_indices:
                self.stale_indices.remove(star_idx)
                continue
            self.status[star_idx] = SterilizationStatus.HABITABLE
            self.in_queue.discard(star_idx)
            recovered.append(star_idx)
        return recovered

    def get_habitable_mask(self) -> np.ndarray:
        """Return boolean mask of habitable stars.

        Returns:
            Boolean array where True = habitable
        """
        return self.status == SterilizationStatus.HABITABLE

    def get_statistics(self) -> dict:
        """Return sterilization statistics.

        Returns:
            Dict with counts and percentages
        """
        n_stars = len(self.status)
        n_habitable = np.sum(self.status == SterilizationStatus.HABITABLE)
        n_temp = np.sum(
            self.status == SterilizationStatus.TEMPORARILY_STERILIZED
        )
        n_perm = np.sum(
            self.status == SterilizationStatus.PERMANENTLY_STERILIZED
        )

        return {
            "total_stars": n_stars,
            "habitable": int(n_habitable),
            "temporarily_sterilized": int(n_temp),
            "permanently_sterilized": int(n_perm),
            "habitable_fraction": float(n_habitable / n_stars),
            "temp_fraction": float(n_temp / n_stars),
            "perm_fraction": float(n_perm / n_stars),
        }
