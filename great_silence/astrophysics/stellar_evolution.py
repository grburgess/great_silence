"""Stellar evolution calculations."""

import numpy as np


class StellarEvolution:
    """Simple stellar evolution model for main sequence lifetimes and colors."""

    @staticmethod
    def main_sequence_lifetime(masses: np.ndarray, metallicities: np.ndarray) -> np.ndarray:
        """Calculate main sequence lifetimes.

        Uses simplified relation: t_ms ∝ M^(-2.5)

        Args:
            masses: (N,) stellar masses in M_sun
            metallicities: (N,) metallicities Z (not used in simple model)

        Returns:
            (N,) main sequence lifetimes in Gyr
        """
        return 10.0 * (masses) ** (-2.5)

    @staticmethod
    def effective_temperature(masses: np.ndarray) -> np.ndarray:
        """Calculate main sequence effective temperature from mass.

        Uses mass-temperature relation for main sequence: T_eff ∝ M^0.5
        Normalized to Sun: T_sun = 5778 K

        Args:
            masses: (N,) stellar masses in M_sun

        Returns:
            (N,) effective temperatures in Kelvin
        """
        T_sun = 5778.0
        return T_sun * np.power(masses, 0.5)

    @staticmethod
    def luminosity(masses: np.ndarray) -> np.ndarray:
        """Calculate main sequence luminosity from mass.

        Uses mass-luminosity relation: L ∝ M^3.5 (approximate)

        Args:
            masses: (N,) stellar masses in M_sun

        Returns:
            (N,) luminosities in L_sun
        """
        return np.power(masses, 3.5)

    @staticmethod
    def temperature_to_rgb(temperatures: np.ndarray) -> np.ndarray:
        """Convert effective temperature to RGB color.

        Uses blackbody approximation for stellar colors.
        Based on Tanner Helland's algorithm adapted for stars.

        Temperature ranges:
        - O stars: > 30000 K (blue-white)
        - B stars: 10000-30000 K (blue-white)
        - A stars: 7500-10000 K (white)
        - F stars: 6000-7500 K (yellow-white)
        - G stars: 5200-6000 K (yellow, Sun-like)
        - K stars: 3700-5200 K (orange)
        - M stars: 2400-3700 K (red)

        Args:
            temperatures: (N,) temperatures in Kelvin

        Returns:
            (N, 3) RGB colors normalized to [0, 1]
        """
        temps = np.clip(np.asarray(temperatures, dtype=float), 1000, 40000)
        temp_100 = temps / 100.0
        n = temps.shape[0]
        colors = np.empty((n, 3))

        hot = temps > 6600

        r = np.ones(n)
        r[hot] = np.clip(329.698727446 * np.power(temp_100[hot] - 60, -0.1332047592) / 255.0, 0, 1)

        g = np.empty(n)
        g[~hot] = np.clip((99.4708025861 * np.log(temp_100[~hot]) - 161.1195681661) / 255.0, 0, 1)
        g[hot] = np.clip(288.1221695283 * np.power(temp_100[hot] - 60, -0.0755148492) / 255.0, 0, 1)

        b = np.ones(n)
        b[temps <= 1900] = 0.0
        mid = (temps > 1900) & (temps < 6600)
        b[mid] = np.clip(
            (138.5177312231 * np.log(temp_100[mid] - 10) - 305.0447927307) / 255.0, 0, 1
        )

        colors[:, 0] = r
        colors[:, 1] = g
        colors[:, 2] = b
        return colors

    @staticmethod
    def mass_to_color(masses: np.ndarray) -> np.ndarray:
        """Convert stellar masses to RGB colors via temperature.

        Args:
            masses: (N,) stellar masses in M_sun

        Returns:
            (N, 3) RGB colors normalized to [0, 1]
        """
        temperatures = StellarEvolution.effective_temperature(masses)
        return StellarEvolution.temperature_to_rgb(temperatures)

    @staticmethod
    def mass_to_apparent_size(masses: np.ndarray, base_size: float = 0.05) -> np.ndarray:
        """Calculate apparent size based on luminosity.

        Brighter stars appear larger. Uses sqrt of luminosity for visual scaling.

        Args:
            masses: (N,) stellar masses in M_sun
            base_size: Base point size for 1 M_sun star

        Returns:
            (N,) apparent sizes for rendering
        """
        luminosities = StellarEvolution.luminosity(masses)
        return base_size * np.sqrt(np.clip(luminosities, 0.01, 100))

    @staticmethod
    def evolved_properties(masses: np.ndarray, ages: np.ndarray) -> tuple:
        """Calculate evolved stellar properties based on mass and age.

        Tracks stellar evolution through phases:
        - Main sequence: stable temperature/luminosity
        - Red giant: cooler (~3500K), brighter (10-1000x MS luminosity)
        - Dead: supernova/white dwarf (removed from visualization)

        Args:
            masses: (N,) stellar masses in M_sun
            ages: (N,) stellar ages in Gyr

        Returns:
            Tuple of:
            - temperatures: (N,) effective temperatures in K
            - luminosities: (N,) luminosities in L_sun
            - phases: (N,) phase codes (0=MS, 1=RGB, 2=dead)
            - colors: (N,3) RGB colors
        """
        n = len(masses)
        ms_lifetimes = StellarEvolution.main_sequence_lifetime(masses, np.zeros(n))

        ms_temps = StellarEvolution.effective_temperature(masses)
        ms_lums = StellarEvolution.luminosity(masses)

        age_fraction = ages / np.maximum(ms_lifetimes, 0.001)

        phases = np.zeros(n, dtype=int)
        phases[age_fraction > 0.9] = 1  # Red giant phase (last 10% of MS life)
        phases[age_fraction >= 1.0] = 2  # Dead

        temperatures = ms_temps.copy()
        luminosities = ms_lums.copy()

        rgb_mask = phases == 1
        if np.any(rgb_mask):
            rgb_progress = (age_fraction[rgb_mask] - 0.9) / 0.1
            rgb_progress = np.clip(rgb_progress, 0, 1)

            temperatures[rgb_mask] = (
                ms_temps[rgb_mask] * (1 - 0.5 * rgb_progress) + 3500 * 0.5 * rgb_progress
            )

            lum_boost = 10 ** (2 * rgb_progress)
            luminosities[rgb_mask] = ms_lums[rgb_mask] * lum_boost

        dead_mask = phases == 2
        temperatures[dead_mask] = 0
        luminosities[dead_mask] = 0

        colors = np.zeros((n, 3))
        alive_mask = phases < 2
        if np.any(alive_mask):
            colors[alive_mask] = StellarEvolution.temperature_to_rgb(temperatures[alive_mask])

        return temperatures, luminosities, phases, colors
