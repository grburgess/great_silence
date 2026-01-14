"""Stellar evolution calculations."""

import numpy as np


class StellarEvolution:
    """Simple stellar evolution model for main sequence lifetimes and colors."""

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
        n = len(temperatures)
        colors = np.zeros((n, 3))
        
        for i, temp in enumerate(temperatures):
            temp = np.clip(temp, 1000, 40000)
            temp_100 = temp / 100.0
            
            if temp <= 6600:
                r = 1.0
            else:
                r = temp_100 - 60
                r = 329.698727446 * np.power(r, -0.1332047592)
                r = np.clip(r / 255.0, 0, 1)
            
            if temp <= 6600:
                g = temp_100
                g = 99.4708025861 * np.log(g) - 161.1195681661
                g = np.clip(g / 255.0, 0, 1)
            else:
                g = temp_100 - 60
                g = 288.1221695283 * np.power(g, -0.0755148492)
                g = np.clip(g / 255.0, 0, 1)
            
            if temp >= 6600:
                b = 1.0
            elif temp <= 1900:
                b = 0.0
            else:
                b = temp_100 - 10
                b = 138.5177312231 * np.log(b) - 305.0447927307
                b = np.clip(b / 255.0, 0, 1)
            
            colors[i] = [r, g, b]
        
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
