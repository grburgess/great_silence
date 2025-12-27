"""Gamma-ray burst modeling and hazard assessment."""

import numpy as np
from typing import Tuple
from ..config.parameters import AstrophysicsParameters


class GammaRayBurstModel:
    """
    Model gamma-ray bursts and their effects.

    GRBs are highly beamed and extremely energetic, but rare.
    """

    def __init__(self, params: AstrophysicsParameters):
        """
        Initialize GRB model.

        Args:
            params: Astrophysics configuration parameters
        """
        self.params = params

    def sample_grb_direction(self, rng: np.random.Generator) -> np.ndarray:
        """
        Sample random GRB jet direction (isotropic).

        Args:
            rng: Random number generator

        Returns:
            Unit vector representing jet direction
        """
        # Sample uniformly on sphere
        theta = np.arccos(2 * rng.uniform(0, 1) - 1)
        phi = rng.uniform(0, 2 * np.pi)

        direction = np.array([
            np.sin(theta) * np.cos(phi),
            np.sin(theta) * np.sin(phi),
            np.cos(theta)
        ])

        return direction

    def is_in_beam(
        self,
        grb_position: np.ndarray,
        grb_direction: np.ndarray,
        target_position: np.ndarray
    ) -> bool:
        """
        Check if target is within GRB beam.

        Args:
            grb_position: 3D position of GRB source
            grb_direction: Unit vector of GRB jet direction
            target_position: 3D position of target

        Returns:
            True if target is in beam
        """
        # Vector from GRB to target
        to_target = target_position - grb_position
        distance = np.linalg.norm(to_target)

        if distance < 1e-10:
            return False

        to_target_unit = to_target / distance

        # Angle between jet and target
        cos_angle = np.dot(grb_direction, to_target_unit)
        angle_deg = np.arccos(np.clip(cos_angle, -1, 1)) * 180 / np.pi

        # Check if within beaming angle
        return angle_deg < self.params.grb_beaming_angle_deg

    def lethal_distance_kpc(self) -> float:
        """
        Get lethal distance for GRB.

        Returns:
            Lethal distance in kpc
        """
        return self.params.grb_lethal_range_kpc

    def metallicity_rate_modifier(self, metallicity_feh: float) -> float:
        """
        Calculate GRB rate modifier based on stellar metallicity.

        Long-duration GRBs (collapsars) are observed to favor low-metallicity
        environments. Metal-poor stars retain more angular momentum, making
        it easier to form the jets that produce GRBs.

        Observational evidence:
        - Modjaz et al. (2008): GRB hosts are metal-poor
        - Levesque et al. (2010): <[Fe/H]> ~ -0.4 for GRB hosts
        - Wolf & Podsiadlowski (2007): Rate ∝ 10^(-0.8 * [Fe/H])

        Args:
            metallicity_feh: Stellar metallicity [Fe/H] in dex

        Returns:
            Rate modifier relative to solar metallicity (>1 for metal-poor)
        """
        # GRB rate increases with decreasing metallicity
        # At [Fe/H] = 0.0 (solar): rate = 1.0 (baseline)
        # At [Fe/H] = -0.5: rate ~ 3.2x higher
        # At [Fe/H] = +0.3 (bulge): rate ~ 0.5x lower
        #
        # Using empirical relation: rate_modifier = 10^(-0.8 * [Fe/H])
        # This gives ~factor of 10 difference across typical metallicity range

        rate_modifier = np.power(10.0, -0.8 * metallicity_feh)

        # Clip to physical range (0.1x to 10x baseline)
        return np.clip(rate_modifier, 0.1, 10.0)

    def grb_probability_per_star(
        self,
        stellar_mass: float,
        stellar_age_gyr: float,
        metallicity_feh: float,
        dt_myr: float
    ) -> float:
        """
        Calculate probability that a star produces a GRB during time step.

        GRBs are associated with massive, rapidly rotating stars at low
        metallicity. They occur at the end of the star's main sequence life.

        Args:
            stellar_mass: Mass in solar masses
            stellar_age_gyr: Current age in Gyr
            metallicity_feh: Stellar metallicity [Fe/H]
            dt_myr: Time step in Myr

        Returns:
            Probability of GRB during this timestep
        """
        # Only very massive, rapidly rotating stars (> 20 solar masses)
        if stellar_mass < 20.0:
            return 0.0

        # Main sequence lifetime
        t_ms_gyr = 10.0 * (stellar_mass)**(-2.5)

        # Star must be near end of life
        dt_gyr = dt_myr / 1000.0
        age_at_step_end = stellar_age_gyr + dt_gyr

        # Check if star is at the right age for GRB
        if not (stellar_age_gyr <= t_ms_gyr < age_at_step_end):
            return 0.0

        # Base GRB probability (fraction of core-collapse SNe that produce GRBs)
        # Only ~1% of massive stars produce GRBs (require rapid rotation + low Z)
        p_base = 0.01

        # Metallicity modifier (low metallicity → higher rate)
        z_modifier = self.metallicity_rate_modifier(metallicity_feh)

        # Combined probability
        # Note: This is already a discrete event (happens when star reaches t_ms)
        # so no need to scale by dt
        return p_base * z_modifier
