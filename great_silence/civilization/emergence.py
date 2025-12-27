"""Civilization emergence modeling based on Drake equation."""

import numpy as np
from typing import Optional
from ..config.parameters import CivilizationParameters


class CivilizationEmergence:
    """
    Model emergence of civilizations using Drake equation framework.
    """

    def __init__(self, params: CivilizationParameters):
        """
        Initialize emergence model.

        Args:
            params: Civilization configuration parameters
        """
        self.params = params

    def emergence_probability(
        self,
        stellar_age_gyr: float,
        dt_gyr: float
    ) -> float:
        """
        Calculate probability of civilization emerging during time step.

        Args:
            stellar_age_gyr: Age of the host star (Gyr)
            dt_gyr: Time step duration (Gyr)

        Returns:
            Probability of emergence
        """
        # Stars must be old enough (> 1 Gyr for complex life)
        if stellar_age_gyr < 1.0:
            return 0.0

        # Drake equation terms
        f_planets = self.params.fraction_stars_with_planets
        n_habitable = self.params.avg_habitable_planets_per_system
        f_life = self.params.fraction_develop_life
        f_intel = self.params.fraction_develop_intelligence
        f_tech = self.params.fraction_develop_technology

        # Combined emergence rate (per Gyr)
        rate = f_planets * n_habitable * f_life * f_intel * f_tech

        # Probability for this time step
        return rate * dt_gyr

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
