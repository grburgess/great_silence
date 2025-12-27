"""Combined hazard evaluation for civilizations."""

import numpy as np
from typing import List, Tuple
from .supernovae import SupernovaModel
from .grb import GammaRayBurstModel
from ..config.parameters import AstrophysicsParameters


class HazardEvaluator:
    """
    Evaluate combined astrophysical hazards affecting civilizations.
    """

    def __init__(self, params: AstrophysicsParameters):
        """
        Initialize hazard evaluator.

        Args:
            params: Astrophysics configuration parameters
        """
        self.params = params
        self.sn_model = SupernovaModel(params)
        self.grb_model = GammaRayBurstModel(params)

    def evaluate_supernova_hazard(
        self,
        civilization_position: np.ndarray,
        stellar_positions: np.ndarray,
        stellar_masses: np.ndarray,
        stellar_ages: np.ndarray,
        component_types: np.ndarray,
        dt_myr: float,
        rng: np.random.Generator,
        spatial_index=None
    ) -> Tuple[bool, dict]:
        """
        Check if civilization is destroyed by supernova.

        Uses spatial index if available for 100-1000x speedup on large N.
        Now accounts for local density and component-dependent rates.

        Args:
            civilization_position: 3D position of civilization
            stellar_positions: Positions of all stars
            stellar_masses: Masses of all stars
            stellar_ages: Ages of all stars (Gyr)
            component_types: Component types (0=bulge, 1=disk)
            dt_myr: Time step in Myr
            rng: Random number generator
            spatial_index: Optional SpatialIndex for fast queries

        Returns:
            Tuple of (destroyed: bool, info: dict with hazard statistics)
        """
        info = {'local_sn_rate': 0.0, 'local_density': 0.0, 'n_nearby_stars': 0}

        # Use spatial index if available (much faster for large N)
        if spatial_index is not None:
            # Query only nearby stars (O(log N) instead of O(N))
            radius_kpc = self.params.sn_sterilization_range_pc / 1000.0
            nearby_indices, distances_kpc = spatial_index.query_radius(
                civilization_position, radius_kpc, return_distances=True
            )

            if len(nearby_indices) == 0:
                return False, info

            distances_pc = distances_kpc * 1000.0
            nearby_masses = stellar_masses[nearby_indices]
            nearby_ages = stellar_ages[nearby_indices]
            nearby_components = component_types[nearby_indices]

        else:
            # Fallback: compute all distances (slow for large N)
            distances_kpc = np.linalg.norm(
                stellar_positions - civilization_position, axis=1
            )
            distances_pc = distances_kpc * 1000

            # Only check stars within sterilization range
            nearby_mask = distances_pc < self.params.sn_sterilization_range_pc

            if not np.any(nearby_mask):
                return False, info

            nearby_indices = np.where(nearby_mask)[0]
            nearby_masses = stellar_masses[nearby_mask]
            nearby_ages = stellar_ages[nearby_mask]
            nearby_components = component_types[nearby_mask]
            distances_pc = distances_pc[nearby_mask]

        # Calculate local stellar density
        # Use volume of sphere with radius = sterilization range
        volume_pc3 = (4.0/3.0) * np.pi * (self.params.sn_sterilization_range_pc)**3
        local_density = len(nearby_masses) / volume_pc3

        info['local_density'] = local_density
        info['n_nearby_stars'] = len(nearby_masses)

        # Calculate local supernova rate (accounts for density and component)
        local_sn_rate = self.sn_model.local_supernova_rate(
            nearby_masses,
            nearby_ages,
            nearby_components,
            local_density
        )
        info['local_sn_rate'] = local_sn_rate

        # Check each nearby massive star for supernova (discrete event model)
        for i in range(len(nearby_masses)):
            # Check if star goes supernova during this timestep
            if self.sn_model.will_go_supernova(
                nearby_masses[i],
                nearby_ages[i],
                dt_myr
            ):
                # Supernova occurred - check if lethal
                p_sterilize = self.sn_model.sterilization_probability(distances_pc[i])

                # Apply density modifier to sterilization probability
                # Dense regions have more frequent supernovae → cumulative damage
                density_hazard_modifier = np.sqrt(local_density / 0.1)  # Normalized to solar neighborhood
                p_sterilize_modified = np.clip(p_sterilize * density_hazard_modifier, 0.0, 1.0)

                if rng.uniform(0, 1) < p_sterilize_modified:
                    info['destroyed_by_sn'] = True
                    info['sn_distance_pc'] = distances_pc[i]
                    return True, info

        return False, info

    def evaluate_grb_hazard(
        self,
        civilization_position: np.ndarray,
        stellar_positions: np.ndarray,
        stellar_masses: np.ndarray,
        stellar_ages: np.ndarray,
        metallicities: np.ndarray,
        dt_myr: float,
        rng: np.random.Generator,
        spatial_index=None
    ) -> Tuple[bool, dict]:
        """
        Check if civilization is destroyed by GRB.

        Now uses metallicity-dependent GRB rates and realistic spatial
        distribution following massive star locations.

        Args:
            civilization_position: 3D position of civilization
            stellar_positions: Positions of all stars
            stellar_masses: Masses of all stars
            stellar_ages: Ages of all stars (Gyr)
            metallicities: Stellar metallicities [Fe/H]
            dt_myr: Time step in Myr
            rng: Random number generator
            spatial_index: Optional SpatialIndex for fast queries

        Returns:
            Tuple of (destroyed: bool, info: dict with hazard statistics)
        """
        info = {'n_grb_events': 0, 'avg_metallicity_modifier': 1.0}

        # Find candidate GRB progenitors (massive stars M > 20 solar masses)
        massive_mask = stellar_masses > 20.0
        massive_indices = np.where(massive_mask)[0]

        if len(massive_indices) == 0:
            return False, info

        # Check each massive star for GRB potential
        grb_events = []
        for idx in massive_indices:
            # Check if star is at right age for GRB
            p_grb = self.grb_model.grb_probability_per_star(
                stellar_masses[idx],
                stellar_ages[idx],
                metallicities[idx],
                dt_myr
            )

            if p_grb > 0 and rng.uniform(0, 1) < p_grb:
                # GRB event occurs at this star
                grb_events.append({
                    'position': stellar_positions[idx],
                    'metallicity': metallicities[idx]
                })

        info['n_grb_events'] = len(grb_events)

        if len(grb_events) == 0:
            return False, info

        # Calculate average metallicity modifier across events
        metallicity_modifiers = [
            self.grb_model.metallicity_rate_modifier(event['metallicity'])
            for event in grb_events
        ]
        info['avg_metallicity_modifier'] = np.mean(metallicity_modifiers)

        # Check if any GRB affects civilization
        for event in grb_events:
            grb_pos = event['position']

            # Check distance
            distance_kpc = np.linalg.norm(civilization_position - grb_pos)

            if distance_kpc > self.grb_model.lethal_distance_kpc():
                continue

            # Sample GRB jet direction (random)
            grb_direction = self.grb_model.sample_grb_direction(rng)

            # Check if civilization is in beam
            if self.grb_model.is_in_beam(grb_pos, grb_direction, civilization_position):
                info['destroyed_by_grb'] = True
                info['grb_distance_kpc'] = distance_kpc
                info['grb_metallicity'] = event['metallicity']
                return True, info

        return False, info
