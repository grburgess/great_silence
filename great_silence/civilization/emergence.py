"""Civilization emergence modeling based on Drake equation."""

import numpy as np
from typing import Optional
from ..config.parameters import CivilizationParameters


class CivilizationEmergence:
    """
    Model emergence of civilizations using Drake equation framework.

    Incorporates observational constraints from exoplanet surveys (Kepler, TESS)
    and realistic stellar habitability criteria based on 2024-2025 data.
    """

    def __init__(self, params: CivilizationParameters):
        """
        Initialize emergence model.

        Args:
            params: Civilization configuration parameters
        """
        self.params = params

    def is_star_habitable(
        self,
        stellar_mass: float,
        stellar_age_gyr: float,
        metallicity_feh: float = 0.0
    ) -> bool:
        """
        Check if a star can potentially host habitable planets.

        Based on current astrophysical understanding:
        - Mass range: 0.5-1.4 M☉ (K, G, F stars; some M-dwarfs)
        - Minimum age: 1.0 Gyr (time for complex life to evolve)
        - Metallicity: [Fe/H] > -0.5 (need rocky planets)

        Args:
            stellar_mass: Mass in solar masses
            stellar_age_gyr: Age in Gyr
            metallicity_feh: Metallicity [Fe/H] in dex

        Returns:
            True if star can host habitable planets
        """
        # Mass range: 0.5-1.4 M☉
        # Below 0.5: M-dwarfs with severe tidal locking issues
        # Above 1.4: F-stars with short main sequence lifetimes
        if stellar_mass < 0.5 or stellar_mass > 1.4:
            return False

        # Minimum age for complex life (based on Earth's 4.5 Gyr history)
        if stellar_age_gyr < 1.0:
            return False

        # Metallicity floor (very metal-poor stars unlikely to form rocky planets)
        if metallicity_feh < -0.5:
            return False

        return True

    def metallicity_planet_modifier(self, metallicity_feh: float) -> float:
        """
        Calculate planet occurrence rate modifier based on stellar metallicity.

        Observational data (Zhu & Dong 2021, Johnson et al. 2010) shows
        planet occurrence strongly correlates with metallicity:
        - Rocky planets favor metal-rich stars
        - Occurrence rises from ~10% (sub-solar) to ~30% (super-solar)

        Args:
            metallicity_feh: Stellar metallicity [Fe/H] in dex

        Returns:
            Multiplicative modifier to habitable planet occurrence (0.5 to 1.5)
        """
        # Linear scaling: 1.0 at solar, increases with [Fe/H]
        # Strength factor of 0.5 means ±50% variation across typical range
        modifier = 1.0 + 0.5 * metallicity_feh

        # Clip to physical range
        return np.clip(modifier, 0.5, 1.5)

    def age_dependent_emergence_factor(self, stellar_age_gyr: float) -> float:
        """
        Calculate age-dependent emergence probability factor.

        Based on Earth's timeline:
        - Simple life: ~0.5 Gyr after formation
        - Complex life: ~4.0 Gyr after formation
        - Intelligence: ~4.5 Gyr after formation

        Peak emergence expected around 5 Gyr when stars are:
        - Old enough for complex life
        - Young enough to have stable habitable zones

        Args:
            stellar_age_gyr: Age of host star in Gyr

        Returns:
            Multiplicative factor (0.0 to 1.0) representing age optimality
        """
        if stellar_age_gyr < 1.0:
            return 0.0

        # Sigmoid rise from 1-4 Gyr (ramp-up as complexity evolves)
        rise_factor = 1.0 / (1.0 + np.exp(-2.0 * (stellar_age_gyr - 2.5)))

        # Gaussian peak centered at 5 Gyr (optimal age window)
        peak_age = 5.0
        peak_width = 2.0
        peak_factor = np.exp(-0.5 * ((stellar_age_gyr - peak_age) / peak_width)**2)

        # Combine: gradual rise × optimal age window
        return rise_factor * (0.3 + 0.7 * peak_factor)

    def emergence_probability(
        self,
        stellar_age_gyr: float,
        dt_gyr: float,
        stellar_mass: float = 1.0,
        metallicity_feh: float = 0.0
    ) -> float:
        """
        Calculate probability of civilization emerging during time step.

        Incorporates physical constraints from exoplanet surveys:
        - Stellar habitability (mass, age, metallicity)
        - Age-dependent emergence (peak at ~5 Gyr)
        - Metallicity-dependent planet occurrence

        Args:
            stellar_age_gyr: Age of the host star (Gyr)
            dt_gyr: Time step duration (Gyr)
            stellar_mass: Mass in solar masses (default: 1.0)
            metallicity_feh: Metallicity [Fe/H] (default: 0.0)

        Returns:
            Probability of emergence during this time step
        """
        # Stars must be old enough for complex life
        if stellar_age_gyr < self.params.min_stellar_age_for_life_gyr:
            return 0.0

        # Drake equation base terms
        f_planets = self.params.fraction_stars_with_planets
        n_habitable = self.params.avg_habitable_planets_per_system
        f_life = self.params.fraction_develop_life
        f_intel = self.params.fraction_develop_intelligence
        f_tech = self.params.fraction_develop_technology

        # Apply physical modifiers
        metallicity_modifier = self.metallicity_planet_modifier(metallicity_feh)
        age_factor = self.age_dependent_emergence_factor(stellar_age_gyr)

        # M-dwarf penalty for tidal locking (stars below 0.6 M☉)
        # Recent research (2024) shows ~25% may avoid locking via spin-orbit resonances
        m_dwarf_penalty = 0.25 if stellar_mass < 0.6 else 1.0

        # Combined emergence rate (per Gyr)
        rate = (f_planets * n_habitable * f_life * f_intel * f_tech *
                metallicity_modifier * age_factor * m_dwarf_penalty)

        # Probability for this time step
        return min(1.0, rate * dt_gyr)  # Cap at 100%

    def sample_civilization_lifetime(
        self,
        rng: np.random.Generator
    ) -> float:
        """
        Sample civilization lifetime from distribution.

        Args:
            rng: Random number generator

        Returns:
            Lifetime in Myr
        """
        # Log-normal distribution
        mean_myr = self.params.mean_civilization_lifetime_myr
        std_myr = self.params.lifetime_stddev_myr

        # Convert to log-normal parameters
        mu = np.log(mean_myr**2 / np.sqrt(mean_myr**2 + std_myr**2))
        sigma = np.sqrt(np.log(1 + (std_myr / mean_myr)**2))

        lifetime = rng.lognormal(mu, sigma)

        return max(0.01, lifetime)  # Minimum 10,000 years
