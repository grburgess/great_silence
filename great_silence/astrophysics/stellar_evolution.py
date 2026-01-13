"""Stellar evolution calculations."""

import numpy as np


class StellarEvolution:
    """Simple stellar evolution model for main sequence lifetimes."""

    @staticmethod
    def main_sequence_lifetime(
        masses: np.ndarray,
        metallicities: np.ndarray
    ) -> np.ndarray:
        """Calculate main sequence lifetimes.

        Uses simplified relation: t_ms ∝ M^(-2.5)

        Args:
            masses: (N,) stellar masses in M_sun
            metallicities: (N,) metallicities Z (not used in simple model)

        Returns:
            (N,) main sequence lifetimes in Gyr
        """
        return 10.0 * (masses) ** (-2.5)
