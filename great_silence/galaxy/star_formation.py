"""Star formation history and Initial Mass Function (IMF) modeling."""

import numpy as np
from typing import Optional
from ..config.parameters import AstrophysicsParameters


class StarFormationHistory:
    """
    Models star formation rate as a function of time.

    Uses a delayed exponential model typical for Milky Way-like galaxies.
    """

    def __init__(self, params: AstrophysicsParameters):
        """
        Initialize star formation history model.

        Args:
            params: Astrophysics configuration parameters
        """
        self.params = params

    def sfr(self, age_gyr: float) -> float:
        """
        Star formation rate at a given age (lookback time).

        Args:
            age_gyr: Lookback time in Gyr (0 = present, 13 = early universe)

        Returns:
            Star formation rate in solar masses per year
        """
        # Delayed exponential model: SFR(t) = (t / τ²) * exp(-t/τ)
        tau = self.params.sfr_peak_age_gyr / 2.0  # Peak at t = tau
        t = age_gyr

        if t < 0:
            return 0.0

        sfr = (t / tau**2) * np.exp(-t / tau)

        # Normalize to current SFR
        sfr_current = (13.0 / tau**2) * np.exp(-13.0 / tau)
        normalization = self.params.current_sfr_msun_yr / sfr_current

        return sfr * normalization

    def cumulative_stellar_mass(self, age_gyr: float) -> float:
        """
        Total stellar mass formed up to a given age.

        Args:
            age_gyr: Age in Gyr

        Returns:
            Cumulative stellar mass in solar masses
        """
        # Integrate SFR from 0 to age_gyr
        # For delayed exponential, analytical solution exists
        tau = self.params.sfr_peak_age_gyr / 2.0
        t = age_gyr

        # Integral of t*exp(-t/tau) is -tau*(t+tau)*exp(-t/tau)
        integral = tau * (t + tau) * (1 - np.exp(-t / tau))

        # Convert from Gyr to years and normalize
        sfr_current = (13.0 / tau**2) * np.exp(-13.0 / tau)
        normalization = self.params.current_sfr_msun_yr / sfr_current

        return integral * normalization * 1e9  # Gyr to years

    def generate_stellar_ages(
        self, n_stars: int, max_age_gyr: float = 13.0, seed: Optional[int] = None
    ) -> np.ndarray:
        """
        Generate stellar ages according to star formation history.

        Args:
            n_stars: Number of stars to generate
            max_age_gyr: Maximum stellar age (galaxy age)
            seed: Random seed

        Returns:
            Array of stellar ages in Gyr
        """
        rng = np.random.default_rng(seed)

        # Use rejection sampling
        ages = []
        max_sfr = self.sfr(self.params.sfr_peak_age_gyr)

        while len(ages) < n_stars:
            # Sample uniform age
            age = rng.uniform(0, max_age_gyr)
            sfr_at_age = self.sfr(age)

            # Accept with probability proportional to SFR
            if rng.uniform(0, max_sfr) < sfr_at_age:
                ages.append(age)

        return np.array(ages)

    def generate_stellar_ages_with_gradient(
        self,
        n_stars: int,
        radii: np.ndarray,
        component_types: np.ndarray,
        central_mean_age_gyr: float = 11.0,
        outer_mean_age_gyr: float = 3.0,
        age_gradient_scale_kpc: float = 8.0,
        max_age_gyr: float = 13.0,
        seed: Optional[int] = None
    ) -> np.ndarray:
        """
        Generate stellar ages with radial gradient (inside-out formation).

        Inner stars are older, outer stars are younger.
        Bulge stars are oldest.

        Args:
            n_stars: Number of stars
            radii: Galactocentric radius for each star (kpc)
            component_types: Component type (0=bulge, 1=disk)
            central_mean_age_gyr: Mean age at r=0
            outer_mean_age_gyr: Mean age at large r
            age_gradient_scale_kpc: Scale length for gradient
            max_age_gyr: Maximum age (galaxy age)
            seed: Random seed

        Returns:
            Array of stellar ages in Gyr
        """
        rng = np.random.default_rng(seed)
        ages = np.zeros(n_stars)

        for i in range(n_stars):
            r = radii[i]
            comp_type = component_types[i]

            if comp_type == 0:
                # Bulge: old, metal-rich
                mean_age = central_mean_age_gyr
                sigma_age = 1.5  # Gyr spread
            else:
                # Disk: exponential age gradient
                # Mean age decreases exponentially with radius
                # age(r) = age_outer + (age_central - age_outer) * exp(-r / r_scale)
                mean_age = outer_mean_age_gyr + \
                           (central_mean_age_gyr - outer_mean_age_gyr) * \
                           np.exp(-r / age_gradient_scale_kpc)
                sigma_age = 2.0  # Gyr spread (wider than bulge)

            # Sample from Gaussian around mean age
            age = rng.normal(mean_age, sigma_age)
            age = np.clip(age, 0.5, max_age_gyr)  # Physical bounds

            ages[i] = age

        return ages


class InitialMassFunction:
    """
    Initial Mass Function (IMF) for stellar masses.

    Supports Kroupa, Salpeter, and Chabrier IMFs.
    """

    def __init__(self, imf_type: str = "kroupa"):
        """
        Initialize IMF.

        Args:
            imf_type: Type of IMF ('kroupa', 'salpeter', or 'chabrier')
        """
        self.imf_type = imf_type.lower()

    def pdf(self, mass: float) -> float:
        """
        Probability density function of IMF.

        Args:
            mass: Stellar mass in solar masses

        Returns:
            Probability density (unnormalized)
        """
        if self.imf_type == "salpeter":
            # ξ(m) ∝ m^(-2.35)
            return mass**(-2.35)

        elif self.imf_type == "kroupa":
            # Broken power law
            if mass < 0.08:
                return 0.0  # Below hydrogen burning limit
            elif mass < 0.5:
                return mass**(-1.3)
            else:
                return 0.5**(-1.3) * mass**(-2.3)

        elif self.imf_type == "chabrier":
            # Log-normal for low masses, power law for high
            if mass < 1.0:
                return (1 / mass) * np.exp(-((np.log10(mass) - np.log10(0.2)) ** 2) / (2 * 0.55**2))
            else:
                return mass**(-2.3)

        else:
            raise ValueError(f"Unknown IMF type: {self.imf_type}")

    def sample(
        self,
        n_stars: int,
        mass_range: tuple = (0.08, 100.0),
        seed: Optional[int] = None
    ) -> np.ndarray:
        """
        Sample stellar masses from the IMF.

        Args:
            n_stars: Number of stars to sample
            mass_range: (min_mass, max_mass) in solar masses
            seed: Random seed

        Returns:
            Array of stellar masses in solar masses
        """
        rng = np.random.default_rng(seed)

        min_mass, max_mass = mass_range
        masses = []

        # Find maximum PDF value for rejection sampling
        test_masses = np.logspace(np.log10(min_mass), np.log10(max_mass), 1000)
        max_pdf = max(self.pdf(m) for m in test_masses)

        # Rejection sampling in log space (more efficient)
        while len(masses) < n_stars:
            # Sample log-uniformly
            log_mass = rng.uniform(np.log10(min_mass), np.log10(max_mass))
            mass = 10**log_mass

            # Accept with probability proportional to PDF
            if rng.uniform(0, max_pdf) < self.pdf(mass):
                masses.append(mass)

        return np.array(masses)

    def mean_mass(self, mass_range: tuple = (0.08, 100.0)) -> float:
        """
        Calculate mean stellar mass for this IMF.

        Args:
            mass_range: (min_mass, max_mass) in solar masses

        Returns:
            Mean mass in solar masses
        """
        # Numerical integration
        masses = np.logspace(np.log10(mass_range[0]), np.log10(mass_range[1]), 10000)
        pdfs = np.array([self.pdf(m) for m in masses])

        # Normalize PDF
        pdfs /= np.trapz(pdfs, masses)

        # Calculate mean
        mean = np.trapz(masses * pdfs, masses)

        return mean

    def fraction_above_mass(self, threshold_mass: float, mass_range: tuple = (0.08, 100.0)) -> float:
        """
        Fraction of stars above a given mass threshold.

        Args:
            threshold_mass: Mass threshold in solar masses
            mass_range: (min_mass, max_mass) in solar masses

        Returns:
            Fraction of stars with mass > threshold_mass
        """
        # Numerical integration
        masses = np.logspace(np.log10(mass_range[0]), np.log10(mass_range[1]), 10000)
        pdfs = np.array([self.pdf(m) for m in masses])

        # Normalize PDF
        pdfs /= np.trapz(pdfs, masses)

        # Integrate above threshold
        mask = masses >= threshold_mass
        fraction = np.trapz(pdfs[mask], masses[mask])

        return fraction
