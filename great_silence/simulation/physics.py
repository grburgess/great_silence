"""Physics calculations for light travel time and relativistic effects."""

import numpy as np
from typing import Tuple


class LightTravelCalculator:
    """
    Calculate light travel times and communication delays between stars.

    All distances in parsecs, times in years.
    """

    # Speed of light in parsecs/year
    C_PC_YR = 0.306601  # pc/yr

    @staticmethod
    def light_travel_time(distance_pc: float) -> float:
        """
        Calculate light travel time for a given distance.

        Args:
            distance_pc: Distance in parsecs

        Returns:
            Travel time in years
        """
        return distance_pc / LightTravelCalculator.C_PC_YR

    @staticmethod
    def travel_time(distance_pc: float, velocity_fraction_c: float) -> float:
        """
        Calculate travel time at sub-light velocity.

        Args:
            distance_pc: Distance in parsecs
            velocity_fraction_c: Velocity as fraction of light speed

        Returns:
            Travel time in years
        """
        if velocity_fraction_c <= 0 or velocity_fraction_c >= 1:
            raise ValueError("Velocity must be between 0 and 1 (fraction of c)")

        return distance_pc / (velocity_fraction_c * LightTravelCalculator.C_PC_YR)

    @staticmethod
    def relativistic_time_dilation(velocity_fraction_c: float) -> float:
        """
        Calculate relativistic time dilation factor (Lorentz factor).

        Args:
            velocity_fraction_c: Velocity as fraction of light speed

        Returns:
            Gamma factor (proper time = coordinate time / gamma)
        """
        beta = velocity_fraction_c
        return 1.0 / np.sqrt(1 - beta**2)

    @staticmethod
    def proper_time(
        coordinate_time_yr: float,
        velocity_fraction_c: float
    ) -> float:
        """
        Calculate proper time experienced by traveler.

        Args:
            coordinate_time_yr: Time in external reference frame (years)
            velocity_fraction_c: Velocity as fraction of light speed

        Returns:
            Proper time experienced by traveler (years)
        """
        gamma = LightTravelCalculator.relativistic_time_dilation(velocity_fraction_c)
        return coordinate_time_yr / gamma

    @staticmethod
    def observable_horizon(
        current_time_yr: float,
        observer_position: np.ndarray,
        stellar_positions: np.ndarray
    ) -> np.ndarray:
        """
        Determine which stars are within the observable light cone.

        Args:
            current_time_yr: Current time in years
            observer_position: 3D position of observer (kpc)
            stellar_positions: Array of stellar positions (N, 3) in kpc

        Returns:
            Boolean array indicating which stars are observable
        """
        # Calculate distances in parsecs
        distances_kpc = np.linalg.norm(stellar_positions - observer_position, axis=1)
        distances_pc = distances_kpc * 1000.0

        # Light travel times
        light_times_yr = LightTravelCalculator.light_travel_time(distances_pc)

        # Observable if light had time to reach observer
        return light_times_yr <= current_time_yr
