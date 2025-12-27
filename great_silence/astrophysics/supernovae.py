"""Supernova modeling and hazard assessment."""

import numpy as np
from typing import Optional
from ..config.parameters import AstrophysicsParameters


class SupernovaModel:
    """
    Model supernova rates and their effects on nearby civilizations.
    """

    def __init__(self, params: AstrophysicsParameters):
        """
        Initialize supernova model.

        Args:
            params: Astrophysics configuration parameters
        """
        self.params = params

    def will_go_supernova(
        self,
        stellar_mass: float,
        stellar_age_gyr: float,
        dt_myr: float
    ) -> bool:
        """
        Check if star will go supernova during this time step (discrete event).

        A star goes supernova when it reaches the end of its main sequence
        lifetime, which depends on its mass.

        Args:
            stellar_mass: Mass in solar masses
            stellar_age_gyr: Current age in Gyr
            dt_myr: Time step in Myr

        Returns:
            True if star goes supernova during this timestep
        """
        # Only massive stars (> 8 solar masses) go supernova
        if stellar_mass < 8.0:
            return False

        # Main sequence lifetime: t_ms ∝ M^(-2.5)
        t_ms_gyr = 10.0 * (stellar_mass)**(-2.5)

        # Convert dt to Gyr
        dt_gyr = dt_myr / 1000.0

        # Star goes supernova if we cross t_ms during this timestep
        age_at_step_end = stellar_age_gyr + dt_gyr

        # Supernova occurs if t_ms falls within [stellar_age, stellar_age + dt]
        return stellar_age_gyr <= t_ms_gyr < age_at_step_end

    def supernova_rate_per_star(self, stellar_mass: float, stellar_age_gyr: float) -> float:
        """
        Calculate supernova probability for a star (DEPRECATED - use will_go_supernova).

        This method is kept for backwards compatibility but should not be used
        for new code. Use will_go_supernova() instead for discrete event modeling.

        Args:
            stellar_mass: Mass in solar masses
            stellar_age_gyr: Age in Gyr

        Returns:
            Probability per year
        """
        # Only massive stars (> 8 solar masses) go supernova
        if stellar_mass < 8.0:
            return 0.0

        # Main sequence lifetime (rough approximation)
        # t_ms ∝ M^(-2.5)
        t_ms_gyr = 10.0 * (stellar_mass)**(-2.5)

        # Star goes supernova at end of main sequence
        if stellar_age_gyr >= t_ms_gyr:
            # Already exploded or will soon
            # Model as Gaussian around t_ms
            return np.exp(-((stellar_age_gyr - t_ms_gyr) / 0.01)**2)
        else:
            return 0.0

    def is_lethal(self, distance_pc: float) -> bool:
        """
        Check if supernova is lethal at given distance.

        Args:
            distance_pc: Distance in parsecs

        Returns:
            True if lethal
        """
        return distance_pc < self.params.sn_lethal_range_pc

    def sterilization_probability(self, distance_pc: float) -> float:
        """
        Probability of sterilizing a planet at given distance.

        Args:
            distance_pc: Distance in parsecs

        Returns:
            Sterilization probability [0, 1]
        """
        if distance_pc < self.params.sn_lethal_range_pc:
            return 1.0
        elif distance_pc < self.params.sn_sterilization_range_pc:
            # Exponential decay
            r = (distance_pc - self.params.sn_lethal_range_pc) / \
                (self.params.sn_sterilization_range_pc - self.params.sn_lethal_range_pc)
            return np.exp(-3 * r)
        else:
            return 0.0

    def local_supernova_rate(
        self,
        stellar_masses: np.ndarray,
        stellar_ages: np.ndarray,
        component_types: np.ndarray,
        local_density_stars_per_pc3: float
    ) -> float:
        """
        Calculate local supernova rate based on stellar population.

        The supernova rate depends on:
        1. Number of massive stars (M > 8 solar masses)
        2. Age distribution (older populations have more evolved stars)
        3. Component type (bulge vs disk have different histories)
        4. Local stellar density (more stars → more supernovae)

        Args:
            stellar_masses: Array of stellar masses in solar masses
            stellar_ages: Array of stellar ages in Gyr
            component_types: Array of component types (0=bulge, 1=disk)
            local_density_stars_per_pc3: Local stellar density

        Returns:
            Supernova rate in events per Myr within local region
        """
        # Count massive stars that could go supernova
        massive_mask = stellar_masses > 8.0
        n_massive = np.sum(massive_mask)

        if n_massive == 0:
            return 0.0

        # Calculate how many are near supernova age
        # For each massive star, check if it's close to its t_ms
        t_ms_array = 10.0 * (stellar_masses[massive_mask])**(-2.5)
        age_array = stellar_ages[massive_mask]

        # Stars within 10% of their main sequence lifetime are "near supernova"
        near_sn_mask = (age_array >= 0.9 * t_ms_array)
        n_near_sn = np.sum(near_sn_mask)

        # Component modifier
        # Bulge has older stellar population → higher fraction of evolved stars
        # Count bulge vs disk in local region
        n_bulge = np.sum(component_types == 0)
        n_total = len(component_types)

        if n_total > 0:
            bulge_fraction = n_bulge / n_total
        else:
            bulge_fraction = 0.0

        # Bulge component has ~2x higher evolved fraction due to age
        component_modifier = 1.0 + bulge_fraction  # 1.0 for pure disk, 2.0 for pure bulge

        # Density modifier
        # Higher density → more frequent encounters
        # Normalize to solar neighborhood density (~0.1 stars/pc^3)
        density_modifier = local_density_stars_per_pc3 / 0.1

        # Base rate: ~1 supernova per 100 massive stars per Gyr
        # (Milky Way has ~2 SN per century with ~10^11 stars, ~0.1% massive)
        base_rate_per_gyr = n_near_sn * 0.01

        # Convert to per Myr and apply modifiers
        rate_per_myr = (base_rate_per_gyr / 1000.0) * component_modifier * np.sqrt(density_modifier)

        return rate_per_myr

    def metallicity_type_ratio(self, metallicity_feh: float) -> dict:
        """
        Calculate relative rates of different supernova types by metallicity.

        Type Ia SN (white dwarf): Slightly favor metal-rich environments
        Type II SN (core collapse): Metallicity-independent
        Pair-instability SN: Only at very low metallicity (Z < 0.01 Z_sun)

        Args:
            metallicity_feh: Stellar metallicity [Fe/H]

        Returns:
            Dictionary with relative rates: {'Ia': float, 'II': float, 'PI': float}
        """
        # Type Ia rate increases slightly with metallicity
        # (metal-rich systems more likely to have close binaries)
        # Mannucci et al. (2005): weak correlation
        type_ia_modifier = 1.0 + 0.3 * metallicity_feh  # ±30% across typical range
        type_ia_modifier = np.clip(type_ia_modifier, 0.5, 1.5)

        # Type II (core collapse) is roughly independent of metallicity
        type_ii_modifier = 1.0

        # Pair-instability supernovae only occur at very low metallicity
        # Z < 0.01 Z_sun means [Fe/H] < -2.0
        if metallicity_feh < -2.0:
            pair_instability_modifier = 1.0
        else:
            pair_instability_modifier = 0.0

        return {
            'Ia': type_ia_modifier,
            'II': type_ii_modifier,
            'PI': pair_instability_modifier
        }
