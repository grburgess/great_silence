"""Unified disaster scheduler with precomputed SN, GRB, and NS merger events.

This module provides O(log N) disaster event queries using min-heaps.
All disaster types are scheduled at initialization based on stellar properties.
"""

import numpy as np
import heapq
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import IntEnum

try:
    import numba
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False


class DisasterType(IntEnum):
    SUPERNOVA = 0
    GRB = 1
    NS_MERGER = 2


@dataclass
class ScheduledDisaster:
    """A pre-scheduled disaster event."""
    time_myr: float
    disaster_type: DisasterType
    star_idx: int
    position: np.ndarray
    energy_ergs: float
    lethal_radius_pc: float
    sterilization_radius_pc: float
    
    grb_jet_theta: float = 0.0
    grb_jet_phi: float = 0.0
    grb_beaming_angle_deg: float = 10.0
    
    merger_partner_idx: int = -1


if HAS_NUMBA:
    @numba.jit(nopython=True, fastmath=True)
    def _compute_sn_times_kernel(
        masses: np.ndarray,
        ages_gyr: np.ndarray,
        n_stars: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute supernova times for all massive stars.
        
        Returns:
            sn_times_myr: Array of SN times from NOW (negative if already dead)
            is_massive: Boolean mask for M > 8 Msun
        """
        sn_times_myr = np.full(n_stars, -1.0, dtype=np.float64)
        is_massive = np.zeros(n_stars, dtype=np.bool_)
        
        for i in range(n_stars):
            mass = masses[i]
            if mass > 8.0:
                is_massive[i] = True
                t_ms_gyr = 10.0 * mass ** (-2.5)
                time_until_sn_gyr = t_ms_gyr - ages_gyr[i]
                sn_times_myr[i] = time_until_sn_gyr * 1000.0
        
        return sn_times_myr, is_massive

    @numba.jit(nopython=True, fastmath=True)
    def _compute_grb_probability_kernel(
        masses: np.ndarray,
        metallicities: np.ndarray,
        n_stars: int,
        grb_base_fraction: float,
        grb_min_mass: float = 20.0
    ) -> np.ndarray:
        """Compute GRB probability for each massive star.
        
        GRBs favor low metallicity and high mass.
        """
        p_grb = np.zeros(n_stars, dtype=np.float64)
        
        for i in range(n_stars):
            mass = masses[i]
            if mass < grb_min_mass:
                continue
            
            feh = metallicities[i]
            z_modifier = 10.0 ** (-0.8 * feh)
            z_modifier = min(10.0, max(0.1, z_modifier))
            
            mass_modifier = (mass / grb_min_mass) ** 0.5
            mass_modifier = min(2.0, mass_modifier)
            
            p_grb[i] = grb_base_fraction * z_modifier * mass_modifier
            p_grb[i] = min(1.0, p_grb[i])
        
        return p_grb


class UnifiedDisasterScheduler:
    """
    Unified scheduler for all astrophysical disasters.
    
    Precomputes:
    - Supernova times for all M > 8 Msun stars
    - GRB events (subset of SNe based on mass + metallicity)
    - NS merger events (from NS remnants with delay time distribution)
    
    All events stored in min-heaps for O(log N) queries.
    """

    def __init__(
        self,
        positions: np.ndarray,
        masses: np.ndarray,
        ages_gyr: np.ndarray,
        metallicities: np.ndarray,
        config,
        rng: np.random.Generator,
        simulation_duration_myr: float,
    ):
        """
        Initialize unified disaster scheduler.
        
        Args:
            positions: (N, 3) stellar positions in kpc
            masses: (N,) stellar masses in Msun
            ages_gyr: (N,) stellar ages in Gyr
            metallicities: (N,) stellar metallicities [Fe/H]
            config: AstrophysicsParameters
            rng: Random number generator
            simulation_duration_myr: Total simulation duration
        """
        self.positions = positions
        self.masses = masses
        self.ages_gyr = ages_gyr
        self.metallicities = metallicities
        self.config = config
        self.rng = rng
        self.simulation_duration_myr = simulation_duration_myr
        
        self.n_stars = len(masses)
        
        self.sn_heap: List[Tuple[float, int]] = []
        self.grb_heap: List[Tuple[float, int]] = []
        self.ns_merger_heap: List[Tuple[float, int, int]] = []
        
        self.scheduled_disasters: List[ScheduledDisaster] = []
        self.disaster_by_time: List[Tuple[float, int]] = []
        
        self.stellar_is_alive = np.ones(self.n_stars, dtype=np.bool_)
        self.stellar_remnant_type = np.zeros(self.n_stars, dtype=np.int8)
        
        self.ns_remnant_indices: List[int] = []
        self.ns_formation_times: List[float] = []
        
        self._build_schedules()

    def _build_schedules(self):
        """Build all disaster schedules from stellar population."""
        self._schedule_supernovae()
        self._schedule_grbs()
        self._schedule_ns_mergers()
        
        heapq.heapify(self.disaster_by_time)

    def _schedule_supernovae(self):
        """Schedule all supernovae from massive stars."""
        if HAS_NUMBA:
            sn_times_myr, is_massive = _compute_sn_times_kernel(
                self.masses, self.ages_gyr, self.n_stars
            )
        else:
            sn_times_myr = np.full(self.n_stars, -1.0)
            is_massive = self.masses > 8.0
            
            for i in np.where(is_massive)[0]:
                t_ms_gyr = 10.0 * self.masses[i] ** (-2.5)
                sn_times_myr[i] = (t_ms_gyr - self.ages_gyr[i]) * 1000.0
        
        # First, identify pre-existing NS remnants (stars that already died before simulation)
        # These are NS progenitors (8-25 Msun) whose SN time is in the past
        for i in np.where(is_massive)[0]:
            if self.masses[i] > 8.0 and self.masses[i] < 25.0:
                if sn_times_myr[i] <= 0:
                    # Already exploded before simulation - add as existing NS remnant
                    self.ns_remnant_indices.append(i)
                    self.ns_formation_times.append(sn_times_myr[i])
        
        # Schedule future supernovae
        future_mask = (sn_times_myr > 0) & (sn_times_myr < self.simulation_duration_myr)
        future_indices = np.where(future_mask)[0]
        
        for idx in future_indices:
            sn_time = sn_times_myr[idx]
            
            disaster = ScheduledDisaster(
                time_myr=sn_time,
                disaster_type=DisasterType.SUPERNOVA,
                star_idx=idx,
                position=self.positions[idx].copy(),
                energy_ergs=1e51,
                lethal_radius_pc=self.config.sn_lethal_range_pc,
                sterilization_radius_pc=self.config.sn_sterilization_range_pc,
            )
            
            disaster_idx = len(self.scheduled_disasters)
            self.scheduled_disasters.append(disaster)
            
            heapq.heappush(self.sn_heap, (sn_time, disaster_idx))
            heapq.heappush(self.disaster_by_time, (sn_time, disaster_idx))
            
            if self.masses[idx] > 8.0 and self.masses[idx] < 25.0:
                self.ns_remnant_indices.append(idx)
                self.ns_formation_times.append(sn_time)

    def _schedule_grbs(self):
        """Schedule GRBs as subset of massive star deaths."""
        grb_base_fraction = getattr(self.config, 'grb_fraction_of_sne', 0.01)
        grb_min_mass = getattr(self.config, 'grb_min_progenitor_mass', 20.0)
        
        if HAS_NUMBA:
            p_grb = _compute_grb_probability_kernel(
                self.masses, self.metallicities, self.n_stars, grb_base_fraction, grb_min_mass
            )
        else:
            p_grb = np.zeros(self.n_stars)
            massive_mask = self.masses > grb_min_mass
            
            for i in np.where(massive_mask)[0]:
                feh = self.metallicities[i]
                z_modifier = np.clip(10.0 ** (-0.8 * feh), 0.1, 10.0)
                mass_modifier = np.clip((self.masses[i] / grb_min_mass) ** 0.5, 1.0, 2.0)
                p_grb[i] = np.clip(grb_base_fraction * z_modifier * mass_modifier, 0.0, 1.0)
        
        random_draws = self.rng.uniform(0, 1, self.n_stars)
        grb_mask = random_draws < p_grb
        
        for sn_time, disaster_idx in self.sn_heap:
            disaster = self.scheduled_disasters[disaster_idx]
            star_idx = disaster.star_idx
            
            if not grb_mask[star_idx]:
                continue
            
            jet_theta = np.arccos(2 * self.rng.uniform(0, 1) - 1)
            jet_phi = self.rng.uniform(0, 2 * np.pi)
            
            grb_disaster = ScheduledDisaster(
                time_myr=sn_time,
                disaster_type=DisasterType.GRB,
                star_idx=star_idx,
                position=self.positions[star_idx].copy(),
                energy_ergs=1e54,
                lethal_radius_pc=self.config.grb_lethal_range_kpc * 1000.0,
                sterilization_radius_pc=self.config.grb_lethal_range_kpc * 1000.0,
                grb_jet_theta=jet_theta,
                grb_jet_phi=jet_phi,
                grb_beaming_angle_deg=self.config.grb_beaming_angle_deg,
            )
            
            grb_idx = len(self.scheduled_disasters)
            self.scheduled_disasters.append(grb_disaster)
            
            heapq.heappush(self.grb_heap, (sn_time, grb_idx))
            heapq.heappush(self.disaster_by_time, (sn_time, grb_idx))

    def _schedule_ns_mergers(self):
        """Schedule NS mergers using galactic merger rate.
        
        NS merger rate in Milky Way is ~20-50 per Myr. We scale by stellar fraction.
        Merger positions are sampled near NS remnants or in disk if insufficient remnants.
        """
        ns_merger_rate_per_myr = getattr(self.config, 'ns_merger_rate_per_myr', 50.0)
        
        galactic_scale = self.n_stars / 4e11
        scaled_rate = ns_merger_rate_per_myr * galactic_scale
        
        expected_mergers = scaled_rate * self.simulation_duration_myr
        
        if expected_mergers < 1.0:
            n_mergers = 1 if self.rng.uniform(0, 1) < expected_mergers else 0
        else:
            n_mergers = self.rng.poisson(expected_mergers)
        
        min_for_viz = max(1, int(self.simulation_duration_myr / 2000.0))
        n_mergers = max(n_mergers, min_for_viz) if len(self.ns_remnant_indices) > 0 else n_mergers
        
        merger_times = list(self.rng.uniform(0, self.simulation_duration_myr, size=n_mergers))
        
        sgrb_lethal_kpc = getattr(self.config, 'ns_sgrb_lethal_range_kpc', 3.0)
        kilonova_lethal_pc = getattr(self.config, 'ns_kilonova_lethal_range_pc', 30.0)
        kilonova_sterilization_pc = getattr(self.config, 'ns_kilonova_sterilization_range_pc', 100.0)
        sgrb_beaming = getattr(self.config, 'ns_sgrb_beaming_angle_deg', 5.0)
        
        for merger_time in merger_times:
            if len(self.ns_remnant_indices) >= 2:
                # Sample with replacement since same NS can be in multiple binary systems
                ns1_idx, ns2_idx = self.rng.choice(
                    self.ns_remnant_indices, size=2, replace=True
                )
                # Ensure we don't pick the same NS twice
                while ns2_idx == ns1_idx and len(self.ns_remnant_indices) > 1:
                    ns2_idx = self.rng.choice(self.ns_remnant_indices)
                
                pos1 = self.positions[ns1_idx]
                pos2 = self.positions[ns2_idx]
                
                # NS binaries drift from formation location due to natal kicks
                # Add random offset (typical NS kick velocity ~200 km/s, over ~Gyr gives ~kpc drift)
                drift_offset = self.rng.normal(0, 0.5, size=3)  # kpc
                merger_pos = (pos1 + pos2) / 2.0 + drift_offset
            else:
                # Fallback: random position in disk if insufficient NS remnants
                r = self.rng.uniform(2, 12)
                theta = self.rng.uniform(0, 2 * np.pi)
                z = self.rng.normal(0, 0.3)
                merger_pos = np.array([r * np.cos(theta), r * np.sin(theta), z])
                ns1_idx = -1
                ns2_idx = -1
            
            jet_theta = np.arccos(2 * self.rng.uniform(0, 1) - 1)
            jet_phi = self.rng.uniform(0, 2 * np.pi)
            
            merger_disaster = ScheduledDisaster(
                time_myr=merger_time,
                disaster_type=DisasterType.NS_MERGER,
                star_idx=ns1_idx,
                position=merger_pos.copy(),
                energy_ergs=1e52,
                lethal_radius_pc=kilonova_lethal_pc,
                sterilization_radius_pc=kilonova_sterilization_pc,
                grb_jet_theta=jet_theta,
                grb_jet_phi=jet_phi,
                grb_beaming_angle_deg=sgrb_beaming,
                merger_partner_idx=ns2_idx,
            )
            
            merger_idx = len(self.scheduled_disasters)
            self.scheduled_disasters.append(merger_disaster)
            
            heapq.heappush(self.ns_merger_heap, (merger_time, ns1_idx, ns2_idx))
            heapq.heappush(self.disaster_by_time, (merger_time, merger_idx))

    def get_disasters_in_window(
        self, start_myr: float, end_myr: float
    ) -> List[ScheduledDisaster]:
        """
        Get all disasters occurring in time window.
        
        Complexity: O(k log N) where k = events in window
        
        Args:
            start_myr: Window start (Myr)
            end_myr: Window end (Myr)
            
        Returns:
            List of ScheduledDisaster events
        """
        result = []
        
        while self.disaster_by_time and self.disaster_by_time[0][0] <= end_myr:
            event_time, disaster_idx = self.disaster_by_time[0]
            
            if event_time >= start_myr:
                heapq.heappop(self.disaster_by_time)
                disaster = self.scheduled_disasters[disaster_idx]
                result.append(disaster)
                
                if disaster.disaster_type == DisasterType.SUPERNOVA:
                    star_idx = disaster.star_idx
                    if star_idx >= 0:
                        self.stellar_is_alive[star_idx] = False
                        if 8.0 < self.masses[star_idx] < 25.0:
                            self.stellar_remnant_type[star_idx] = 1
                        else:
                            self.stellar_remnant_type[star_idx] = 2
            else:
                heapq.heappop(self.disaster_by_time)
        
        return result

    def peek_next_disaster_time(self) -> Optional[float]:
        """
        Get time of next scheduled disaster without consuming it.
        
        Returns:
            Time in Myr, or None if no more disasters
        """
        if self.disaster_by_time:
            return self.disaster_by_time[0][0]
        return None

    def get_statistics(self) -> dict:
        """Get disaster schedule statistics."""
        sn_count = len([d for d in self.scheduled_disasters 
                       if d.disaster_type == DisasterType.SUPERNOVA])
        grb_count = len([d for d in self.scheduled_disasters 
                        if d.disaster_type == DisasterType.GRB])
        merger_count = len([d for d in self.scheduled_disasters 
                           if d.disaster_type == DisasterType.NS_MERGER])
        
        return {
            'total_scheduled': len(self.scheduled_disasters),
            'supernovae': sn_count,
            'grbs': grb_count,
            'ns_mergers': merger_count,
            'pending_events': len(self.disaster_by_time),
            'ns_remnants_formed': len(self.ns_remnant_indices),
        }

    @property
    def pending_count(self) -> int:
        """Number of disasters still pending."""
        return len(self.disaster_by_time)
