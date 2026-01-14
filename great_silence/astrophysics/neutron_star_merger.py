"""Neutron star merger (kilonova) modeling and hazard assessment.

Neutron star mergers produce:
1. Gravitational waves (already detected by LIGO/Virgo)
2. Short gamma-ray bursts (sGRB) - highly beamed
3. Kilonova - r-process nucleosynthesis, less beamed radiation
4. Relativistic jets

References:
- Abbott et al. (2017): GW170817 detection
- Metzger (2019): Kilonova review
- Fong et al. (2015): sGRB-host galaxy correlations
"""

import numpy as np
from typing import Tuple, Optional
from ..config.parameters import AstrophysicsParameters

try:
    import numba
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False


if HAS_NUMBA:
    @numba.jit(nopython=True, fastmath=True)
    def _compute_ns_merger_rate_kernel(
        positions: np.ndarray,
        masses: np.ndarray,
        ages_gyr: np.ndarray,
        metallicities: np.ndarray,
        query_position: np.ndarray,
        search_radius_kpc: float,
        base_rate_per_myr: float,
    ) -> Tuple[float, int]:
        """Numba-accelerated NS merger rate calculation.
        
        Args:
            positions: (N, 3) stellar positions in kpc
            masses: (N,) stellar masses in solar masses
            ages_gyr: (N,) stellar ages in Gyr
            metallicities: (N,) stellar metallicities [Fe/H]
            query_position: (3,) query position in kpc
            search_radius_kpc: Search radius for local rate calculation
            base_rate_per_myr: Base merger rate per Myr per stellar mass
            
        Returns:
            Tuple of (local_rate_per_myr, n_candidate_systems)
        """
        n_stars = len(positions)
        search_radius_sq = search_radius_kpc * search_radius_kpc
        
        local_mass = 0.0
        n_candidates = 0
        
        for i in range(n_stars):
            dx = positions[i, 0] - query_position[0]
            dy = positions[i, 1] - query_position[1]
            dz = positions[i, 2] - query_position[2]
            dist_sq = dx * dx + dy * dy + dz * dz
            
            if dist_sq > search_radius_sq:
                continue
                
            mass = masses[i]
            age = ages_gyr[i]
            
            if mass < 8.0:
                continue
            
            t_ms_gyr = 10.0 * mass ** (-2.5)
            if age < t_ms_gyr:
                continue
                
            local_mass += mass
            n_candidates += 1
        
        local_rate = local_mass * base_rate_per_myr * 1e-10
        
        return local_rate, n_candidates


    @numba.jit(nopython=True, fastmath=True)
    def _evaluate_ns_merger_sterilization_kernel(
        civ_position: np.ndarray,
        merger_position: np.ndarray,
        sgrb_direction: np.ndarray,
        beaming_angle_deg: float,
        sgrb_lethal_range_kpc: float,
        kilonova_lethal_range_pc: float,
    ) -> Tuple[bool, bool, float]:
        """Check if civilization is affected by NS merger.
        
        Args:
            civ_position: (3,) civilization position in kpc
            merger_position: (3,) merger position in kpc
            sgrb_direction: (3,) unit vector of sGRB jet direction
            beaming_angle_deg: sGRB beaming half-angle
            sgrb_lethal_range_kpc: sGRB lethal distance in kpc
            kilonova_lethal_range_pc: Kilonova lethal distance in pc
            
        Returns:
            Tuple of (destroyed_by_sgrb, destroyed_by_kilonova, distance_pc)
        """
        to_civ = civ_position - merger_position
        distance_kpc = np.sqrt(
            to_civ[0] * to_civ[0] + 
            to_civ[1] * to_civ[1] + 
            to_civ[2] * to_civ[2]
        )
        distance_pc = distance_kpc * 1000.0
        
        in_sgrb_beam = False
        if distance_kpc > 1e-10 and distance_kpc < sgrb_lethal_range_kpc:
            to_civ_unit = to_civ / distance_kpc
            cos_angle = (
                sgrb_direction[0] * to_civ_unit[0] +
                sgrb_direction[1] * to_civ_unit[1] +
                sgrb_direction[2] * to_civ_unit[2]
            )
            angle_rad = np.arccos(min(1.0, max(-1.0, cos_angle)))
            angle_deg = angle_rad * 180.0 / 3.14159265358979
            
            if angle_deg < beaming_angle_deg:
                in_sgrb_beam = True
        
        in_kilonova_range = distance_pc < kilonova_lethal_range_pc
        
        return in_sgrb_beam, in_kilonova_range, distance_pc


class NeutronStarMergerModel:
    """
    Model neutron star mergers (binary NS and NS-BH) and their effects.
    
    NS mergers are rare but devastating events that produce:
    - Short gamma-ray bursts (highly beamed, ~kpc lethal range)
    - Kilonova emission (less beamed, ~10-50 pc lethal range)
    - Heavy element enrichment (r-process)
    
    Rate estimates:
    - Milky Way: ~10-100 Myr^-1 (Abbott et al. 2017)
    - Solar neighborhood density scaling
    """

    def __init__(self, params: AstrophysicsParameters):
        """
        Initialize neutron star merger model.

        Args:
            params: Astrophysics configuration parameters
        """
        self.params = params
        
        self.merger_rate_per_myr = getattr(
            params, 'ns_merger_rate_per_myr', 50.0
        )
        self.sgrb_beaming_angle_deg = getattr(
            params, 'ns_sgrb_beaming_angle_deg', 5.0
        )
        self.sgrb_lethal_range_kpc = getattr(
            params, 'ns_sgrb_lethal_range_kpc', 3.0
        )
        self.kilonova_lethal_range_pc = getattr(
            params, 'ns_kilonova_lethal_range_pc', 30.0
        )
        self.kilonova_sterilization_range_pc = getattr(
            params, 'ns_kilonova_sterilization_range_pc', 100.0
        )
        self.delay_time_min_gyr = getattr(
            params, 'ns_delay_time_min_gyr', 0.01
        )
        self.delay_time_max_gyr = getattr(
            params, 'ns_delay_time_max_gyr', 10.0
        )

    def sample_merger_direction(self, rng: np.random.Generator) -> np.ndarray:
        """
        Sample random merger jet direction (isotropic).

        Args:
            rng: Random number generator

        Returns:
            Unit vector representing jet direction
        """
        theta = np.arccos(2 * rng.uniform(0, 1) - 1)
        phi = rng.uniform(0, 2 * np.pi)

        direction = np.array([
            np.sin(theta) * np.cos(phi),
            np.sin(theta) * np.sin(phi),
            np.cos(theta)
        ])

        return direction

    def delay_time_distribution(self, rng: np.random.Generator) -> float:
        """
        Sample delay time from formation to merger.
        
        NS mergers have a wide delay time distribution, typically
        modeled as P(t) ∝ t^(-1) (power law).
        
        Args:
            rng: Random number generator
            
        Returns:
            Delay time in Gyr
        """
        t_min = self.delay_time_min_gyr
        t_max = self.delay_time_max_gyr
        
        u = rng.uniform(0, 1)
        delay = t_min * np.exp(u * np.log(t_max / t_min))
        
        return delay

    def merger_probability_per_timestep(
        self,
        stellar_positions: np.ndarray,
        stellar_masses: np.ndarray,
        stellar_ages: np.ndarray,
        civ_position: np.ndarray,
        dt_myr: float,
        spatial_index=None
    ) -> Tuple[float, dict]:
        """
        Calculate probability of a merger occurring near civilization.
        
        Uses local stellar mass density to scale the galactic-average
        merger rate.
        
        Args:
            stellar_positions: (N, 3) positions in kpc
            stellar_masses: (N,) masses in solar masses
            stellar_ages: (N,) ages in Gyr
            civ_position: (3,) civilization position in kpc
            dt_myr: Time step in Myr
            spatial_index: Optional SpatialIndex for fast queries
            
        Returns:
            Tuple of (probability, info_dict)
        """
        search_radius_kpc = self.sgrb_lethal_range_kpc
        info = {
            'local_stellar_mass': 0.0,
            'n_ns_progenitors': 0,
            'local_merger_rate': 0.0
        }
        
        if spatial_index is not None:
            nearby_indices, distances = spatial_index.query_radius(
                civ_position, search_radius_kpc, return_distances=True
            )
            if len(nearby_indices) == 0:
                return 0.0, info
                
            nearby_masses = stellar_masses[nearby_indices]
            nearby_ages = stellar_ages[nearby_indices]
            
            massive_mask = nearby_masses > 8.0
            t_ms = 10.0 * nearby_masses[massive_mask] ** (-2.5)
            evolved_mask = nearby_ages[massive_mask] > t_ms
            
            local_mass = np.sum(nearby_masses[massive_mask][evolved_mask])
            n_progenitors = np.sum(evolved_mask)
        else:
            distances_kpc = np.linalg.norm(
                stellar_positions - civ_position, axis=1
            )
            nearby_mask = distances_kpc < search_radius_kpc
            
            if not np.any(nearby_mask):
                return 0.0, info
                
            nearby_masses = stellar_masses[nearby_mask]
            nearby_ages = stellar_ages[nearby_mask]
            
            massive_mask = nearby_masses > 8.0
            t_ms = 10.0 * nearby_masses[massive_mask] ** (-2.5)
            evolved_mask = nearby_ages[massive_mask] > t_ms
            
            local_mass = np.sum(nearby_masses[massive_mask][evolved_mask])
            n_progenitors = np.sum(evolved_mask)
        
        galactic_mass_msun = 6e10
        local_rate_per_myr = (
            self.merger_rate_per_myr * 
            (local_mass / galactic_mass_msun) *
            (search_radius_kpc / 15.0) ** 3
        )
        
        info['local_stellar_mass'] = local_mass
        info['n_ns_progenitors'] = n_progenitors
        info['local_merger_rate'] = local_rate_per_myr
        
        p_merger = 1.0 - np.exp(-local_rate_per_myr * dt_myr)
        
        return p_merger, info

    def evaluate_merger_effects(
        self,
        civ_position: np.ndarray,
        merger_position: np.ndarray,
        rng: np.random.Generator
    ) -> Tuple[bool, dict]:
        """
        Evaluate effects of a NS merger on a civilization.
        
        Considers both:
        1. sGRB (short gamma-ray burst) - highly beamed
        2. Kilonova - less beamed but shorter range
        
        Args:
            civ_position: (3,) civilization position in kpc
            merger_position: (3,) merger position in kpc
            rng: Random number generator
            
        Returns:
            Tuple of (destroyed, info_dict)
        """
        info = {
            'in_sgrb_beam': False,
            'in_kilonova_range': False,
            'distance_pc': 0.0,
            'destruction_cause': None
        }
        
        to_civ = civ_position - merger_position
        distance_kpc = np.linalg.norm(to_civ)
        distance_pc = distance_kpc * 1000.0
        info['distance_pc'] = distance_pc
        
        sgrb_direction = self.sample_merger_direction(rng)
        
        if distance_kpc > 1e-10 and distance_kpc < self.sgrb_lethal_range_kpc:
            to_civ_unit = to_civ / distance_kpc
            cos_angle = np.dot(sgrb_direction, to_civ_unit)
            angle_deg = np.arccos(np.clip(cos_angle, -1, 1)) * 180 / np.pi
            
            check_opposite = np.dot(-sgrb_direction, to_civ_unit)
            angle_deg_opposite = np.arccos(np.clip(check_opposite, -1, 1)) * 180 / np.pi
            
            if (angle_deg < self.sgrb_beaming_angle_deg or 
                angle_deg_opposite < self.sgrb_beaming_angle_deg):
                info['in_sgrb_beam'] = True
                info['destruction_cause'] = 'sgrb'
                return True, info
        
        if distance_pc < self.kilonova_lethal_range_pc:
            info['in_kilonova_range'] = True
            info['destruction_cause'] = 'kilonova'
            return True, info
        elif distance_pc < self.kilonova_sterilization_range_pc:
            r = (distance_pc - self.kilonova_lethal_range_pc) / (
                self.kilonova_sterilization_range_pc - self.kilonova_lethal_range_pc
            )
            p_sterilize = np.exp(-3 * r)
            
            if rng.uniform(0, 1) < p_sterilize:
                info['in_kilonova_range'] = True
                info['destruction_cause'] = 'kilonova'
                return True, info
        
        return False, info

    def sample_merger_position(
        self,
        stellar_positions: np.ndarray,
        stellar_masses: np.ndarray,
        stellar_ages: np.ndarray,
        search_center: np.ndarray,
        search_radius_kpc: float,
        rng: np.random.Generator,
        spatial_index=None
    ) -> Optional[np.ndarray]:
        """
        Sample a merger position based on NS progenitor distribution.
        
        Mergers occur preferentially near massive, evolved stars.
        
        Args:
            stellar_positions: (N, 3) stellar positions
            stellar_masses: (N,) stellar masses
            stellar_ages: (N,) stellar ages
            search_center: (3,) center for search
            search_radius_kpc: Search radius
            rng: Random number generator
            spatial_index: Optional spatial index
            
        Returns:
            (3,) merger position or None if no suitable location
        """
        if spatial_index is not None:
            nearby_indices, _ = spatial_index.query_radius(
                search_center, search_radius_kpc, return_distances=True
            )
            if len(nearby_indices) == 0:
                return None
                
            nearby_positions = stellar_positions[nearby_indices]
            nearby_masses = stellar_masses[nearby_indices]
            nearby_ages = stellar_ages[nearby_indices]
        else:
            distances = np.linalg.norm(
                stellar_positions - search_center, axis=1
            )
            nearby_mask = distances < search_radius_kpc
            
            if not np.any(nearby_mask):
                return None
                
            nearby_positions = stellar_positions[nearby_mask]
            nearby_masses = stellar_masses[nearby_mask]
            nearby_ages = stellar_ages[nearby_mask]
        
        massive_mask = nearby_masses > 8.0
        if not np.any(massive_mask):
            return rng.choice(nearby_positions.shape[0])
            
        t_ms = 10.0 * nearby_masses[massive_mask] ** (-2.5)
        evolved_mask = nearby_ages[massive_mask] > t_ms
        
        if not np.any(evolved_mask):
            idx = rng.integers(0, len(nearby_positions))
            return nearby_positions[idx]
        
        evolved_positions = nearby_positions[massive_mask][evolved_mask]
        idx = rng.integers(0, len(evolved_positions))
        
        return evolved_positions[idx]
