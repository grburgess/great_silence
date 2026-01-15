"""Supernova scheduler for pre-computed explosion times."""

import numpy as np
import heapq
from typing import List


class SupernovaScheduler:
    """Pre-computed supernova schedule with O(log N) queries."""

    def __init__(
        self,
        masses: np.ndarray,
        metallicities: np.ndarray,
        ages_myr: np.ndarray,
        stellar_evolution,
    ):
        """Initialize scheduler with galaxy data.

        Args:
            masses: (N,) stellar masses in M_sun
            metallicities: (N,) metallicities Z
            ages_myr: (N,) stellar ages in Myr
            stellar_evolution: StellarEvolution instance
        """
        self.stellar_evolution = stellar_evolution
        self.heap: List[tuple[float, int]] = []
        self._build_schedule(masses, metallicities, ages_myr)

    def _build_schedule(
        self,
        masses: np.ndarray,
        metallicities: np.ndarray,
        ages_myr: np.ndarray,
    ):
        """Pre-compute SN times for all massive stars.

        Complexity: O(N_massive log N_massive)
        """
        massive_mask = masses > 8.0
        massive_indices = np.where(massive_mask)[0]

        if len(massive_indices) == 0:
            return

        ms_lifetimes = self.stellar_evolution.main_sequence_lifetime(
            masses[massive_mask], metallicities[massive_mask]
        )
        sn_times_myr = ages_myr[massive_indices] + ms_lifetimes * 1000

        future_mask = sn_times_myr > 0
        future_indices = massive_indices[future_mask]
        future_times = sn_times_myr[future_mask]

        schedule = list(zip(future_times, future_indices))
        heapq.heapify(schedule)
        self.heap = schedule

    def get_supernovae_in_window(
        self, start_myr: float, end_myr: float
    ) -> List[int]:
        """Get star indices that go SN in time window.

        Complexity: O(k log N) where k = SNe in window

        Args:
            start_myr: Window start (Myr)
            end_myr: Window end (Myr)

        Returns:
            List of star indices
        """
        result = []
        while self.heap and self.heap[0][0] <= end_myr:
            sn_time, star_idx = self.heap[0]
            if sn_time >= start_myr:
                heapq.heappop(self.heap)
                result.append(star_idx)
            else:
                heapq.heappop(self.heap)
        return result

    def add_new_star(
        self,
        star_idx: int,
        mass: float,
        metallicity: float,
        birth_time_myr: float,
    ):
        """Add newly formed star to schedule.

        Args:
            star_idx: Index of new star in galaxy arrays
            mass: Stellar mass (M_sun)
            metallicity: Metallicity Z
            birth_time_myr: Birth time (Myr)
        """
        if mass <= 8.0:
            return

        ms_lifetime_gyr = self.stellar_evolution.main_sequence_lifetime(
            np.array([mass]), np.array([metallicity])
        )[0]
        sn_time_myr = birth_time_myr + ms_lifetime_gyr * 1000

        if sn_time_myr > 0:
            heapq.heappush(self.heap, (sn_time_myr, star_idx))

    @property
    def pending_count(self) -> int:
        """Number of stars still scheduled to explode.

        Returns:
            Count of pending supernovae
        """
        return len(self.heap)
