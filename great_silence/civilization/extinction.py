"""Civilization extinction modeling."""

import numpy as np
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class CrisisPeak:
    """
    Represents a technological crisis peak in the Kardashev scale.

    Each crisis is modeled as a Gaussian hazard peak centered at a specific
    technological level, representing periods of heightened self-destruction risk.
    """
    name: str
    kardashev_center: float  # Center of crisis on Kardashev scale
    width: float  # Standard deviation (how broad the crisis window is)
    amplitude: float  # Peak hazard rate (probability per Myr)
    enabled: bool = True


class ExtinctionModel:
    """
    Model various causes of civilization extinction.

    Implements:
    -----------
    1. Kardashev-dependent self-destruction with crisis peaks (Great Filter stages)
    2. Age-based exponential decay with colonization lifetime extension
    3. Colonial war risk (increases with colonies & K-scale at high tech levels)
    4. Distributed resilience (colonies provide survival redundancy)
    5. Home world destruction with temporary fragility period

    Physical Basis - Crisis Peaks:
    ------------------------------
    The Kardashev-dependent model captures the empirical observation that technological
    civilizations face distinct existential risks at specific developmental stages:

    1. Nuclear Age (K~0.72): Nuclear war, climate collapse, biosphere degradation
    2. Planetary Unification (K~0.85): Coordination failures, resource conflicts
    3. AI Transition (K~1.05): AGI alignment failure, loss of human control
    4. Interplanetary Expansion (K~1.25): Space habitat failures, resource wars
    5. Stellar Engineering (K~1.80): Dyson sphere accidents, star manipulation failures
    6. Relativistic Weapons (K~2.50): Self-annihilation with near-c projectiles

    Each crisis is modeled as a Gaussian hazard peak. Total hazard rate is:
        λ(K) = λ_base(K) + Σᵢ Aᵢ × exp(-((K - Kᵢ)² / (2σᵢ²)))

    where λ_base increases slowly with K (more complex systems, more failure modes).

    Distributed Resilience:
    -----------------------
    Multi-colony civilizations have reduced extinction risk from crises:
    - Crisis probability: p_total = p_single^N_mature (all colonies must fail)
    - Old-age death: p_total = p_single^N_mature (all colonies must die)
    - Colonial war risk: increases with colonies at K ≥ 1.5 (coordination breakdown)
    - Creates U-shaped risk curve: safe at mid-expansion, risky at extremes
    """

    def __init__(
        self,
        self_destruction_rate: float,
        mean_lifetime_myr: float,
        model_type: str = "flat",
        baseline_rate: float = 0.01,
        baseline_scaling: float = 0.05,
        crisis_peaks: Optional[List[CrisisPeak]] = None
    ):
        """
        Initialize extinction model.

        Args:
            self_destruction_rate: Self-destruction probability per Myr (for flat model)
            mean_lifetime_myr: Mean civilization lifetime in Myr
            model_type: "flat" for constant rate, "kardashev_dependent" for crisis peaks
            baseline_rate: Baseline hazard rate at K=0 (per Myr)
            baseline_scaling: Linear scaling factor for baseline with Kardashev scale
            crisis_peaks: List of crisis peaks (if None, uses defaults)
        """
        self.self_destruction_rate = self_destruction_rate
        self.mean_lifetime_myr = mean_lifetime_myr
        self.model_type = model_type
        self.baseline_rate = baseline_rate
        self.baseline_scaling = baseline_scaling

        # Initialize crisis peaks
        if crisis_peaks is None:
            self.crisis_peaks = self._create_default_crisis_peaks()
        else:
            self.crisis_peaks = crisis_peaks

    def _create_default_crisis_peaks(self) -> List[CrisisPeak]:
        """
        Create default crisis peaks based on theoretical Great Filter stages.

        Returns:
            List of CrisisPeak objects with scientifically motivated parameters
        """
        return [
            CrisisPeak(
                name="nuclear_age",
                kardashev_center=0.72,
                width=0.05,
                amplitude=0.15,
                enabled=True
            ),
            CrisisPeak(
                name="planetary_unification",
                kardashev_center=0.85,
                width=0.08,
                amplitude=0.12,
                enabled=True
            ),
            CrisisPeak(
                name="ai_transition",
                kardashev_center=1.05,
                width=0.10,
                amplitude=0.20,  # Highest risk by default
                enabled=True
            ),
            CrisisPeak(
                name="interplanetary_expansion",
                kardashev_center=1.25,
                width=0.15,
                amplitude=0.10,
                enabled=True
            ),
            CrisisPeak(
                name="stellar_engineering",
                kardashev_center=1.80,
                width=0.20,
                amplitude=0.08,
                enabled=True
            ),
            CrisisPeak(
                name="relativistic_weapons",
                kardashev_center=2.50,
                width=0.25,
                amplitude=0.06,
                enabled=True
            ),
        ]

    def calculate_kardashev_hazard_rate(self, kardashev_scale: float) -> float:
        """
        Calculate self-destruction hazard rate based on Kardashev scale.

        Implements multi-peaked hazard function representing technological crises.

        Args:
            kardashev_scale: Current Kardashev scale (0.7 = modern Earth, 3.0 = galactic)

        Returns:
            Hazard rate λ(K) in units of per Myr

        Physical Interpretation:
        -----------------------
        - Baseline risk increases slowly with technology (complex systems are fragile)
        - Crisis peaks represent critical transitions with heightened risk
        - Peak widths reflect transition timescales (narrow = brief crisis, wide = prolonged)
        - Peak amplitudes reflect maximum hazard during crisis

        Example:
        --------
        At K=0.72 (modern Earth, nuclear age peak):
            λ ≈ 0.01 (baseline) + 0.15 (nuclear crisis) = 0.16 per Myr
            Survival probability over 1 Myr: exp(-0.16) ≈ 85%
            Expected survival time: 1/0.16 ≈ 6.3 Myr

        At K=1.05 (AI transition peak):
            λ ≈ 0.015 (baseline) + 0.20 (AI crisis) = 0.215 per Myr
            Expected survival time: 1/0.215 ≈ 4.7 Myr

        At K=2.0 (Type II, between crises):
            λ ≈ 0.02 (baseline) + ~0.03 (tail of stellar crisis) = 0.05 per Myr
            Expected survival time: 1/0.05 = 20 Myr (much safer!)
        """
        # Baseline hazard increases with technological complexity
        lambda_base = self.baseline_rate * (1.0 + self.baseline_scaling * kardashev_scale)

        # Add Gaussian crisis peaks
        crisis_risk = 0.0
        for crisis in self.crisis_peaks:
            if not crisis.enabled:
                continue

            # Gaussian centered at crisis Kardashev scale
            delta_K = kardashev_scale - crisis.kardashev_center
            exponent = -0.5 * (delta_K / crisis.width) ** 2
            gaussian = crisis.amplitude * np.exp(exponent)
            crisis_risk += gaussian

        return lambda_base + crisis_risk

    def check_self_destruction(
        self,
        dt_myr: float,
        rng: np.random.Generator,
        kardashev_scale: Optional[float] = None
    ) -> bool:
        """
        Check if civilization self-destructs.

        Supports two models:
        - "flat": Constant hazard rate (original simple model)
        - "kardashev_dependent": Hazard varies with technological level

        Args:
            dt_myr: Time step in Myr
            rng: Random number generator
            kardashev_scale: Current Kardashev scale (required if model_type="kardashev_dependent")

        Returns:
            True if self-destruction occurs

        Raises:
            ValueError: If kardashev_dependent model used without providing kardashev_scale
        """
        if self.model_type == "flat":
            # Original simple model: constant hazard rate
            lambda_rate = self.self_destruction_rate
        elif self.model_type == "kardashev_dependent":
            if kardashev_scale is None:
                raise ValueError(
                    "kardashev_scale must be provided when using kardashev_dependent model"
                )
            lambda_rate = self.calculate_kardashev_hazard_rate(kardashev_scale)
        else:
            raise ValueError(
                f"Unknown model_type '{self.model_type}'. Choose 'flat' or 'kardashev_dependent'"
            )

        # Convert hazard rate to per-timestep probability
        # For small λ*dt, this approximates λ*dt, but is exact for any λ*dt
        p = 1.0 - np.exp(-lambda_rate * dt_myr)

        return rng.uniform(0, 1) < p

    def check_age_extinction(
        self,
        age_myr: float,
        dt_myr: float,
        rng: np.random.Generator
    ) -> bool:
        """
        Check if civilization dies of old age.

        Uses exponential decay after mean lifetime.

        Args:
            age_myr: Current age in Myr
            dt_myr: Time step in Myr
            rng: Random number generator

        Returns:
            True if extinction occurs
        """
        if age_myr < self.mean_lifetime_myr:
            return False

        # Exponential decay beyond mean lifetime
        decay_rate = 1.0 / self.mean_lifetime_myr
        p = 1.0 - np.exp(-decay_rate * dt_myr)

        return rng.uniform(0, 1) < p

    def survival_probability(
        self,
        age_myr: float,
        kardashev_scale: Optional[float] = None
    ) -> float:
        """
        Calculate survival probability at given age.

        For kardashev_dependent model, this is an approximation assuming
        constant Kardashev scale (actual scale evolves with time).

        Args:
            age_myr: Age in Myr
            kardashev_scale: Current Kardashev scale (for kardashev_dependent model)

        Returns:
            Probability of surviving to this age
        """
        if age_myr <= 0:
            return 1.0

        # Determine self-destruction rate
        if self.model_type == "flat":
            sd_rate = self.self_destruction_rate
        elif self.model_type == "kardashev_dependent":
            if kardashev_scale is None:
                kardashev_scale = 0.7  # Default to modern Earth level
            sd_rate = self.calculate_kardashev_hazard_rate(kardashev_scale)
        else:
            sd_rate = self.self_destruction_rate

        # Combine self-destruction and age-based extinction
        total_rate = sd_rate + 1.0 / self.mean_lifetime_myr

        return np.exp(-total_rate * age_myr)

    def get_crisis_info(self) -> Dict[str, Dict[str, float]]:
        """
        Get information about all crisis peaks.

        Returns:
            Dictionary mapping crisis names to their parameters
        """
        return {
            crisis.name: {
                'kardashev_center': crisis.kardashev_center,
                'width': crisis.width,
                'amplitude': crisis.amplitude,
                'enabled': crisis.enabled
            }
            for crisis in self.crisis_peaks
        }

    def set_crisis_amplitude(self, crisis_name: str, amplitude: float) -> None:
        """
        Modify the amplitude of a specific crisis peak.

        Useful for scenario exploration (e.g., "what if AI risk is higher?").

        Args:
            crisis_name: Name of crisis (e.g., "ai_transition")
            amplitude: New amplitude (hazard rate in per Myr)

        Raises:
            ValueError: If crisis_name not found
        """
        for crisis in self.crisis_peaks:
            if crisis.name == crisis_name:
                crisis.amplitude = amplitude
                return
        raise ValueError(f"Crisis '{crisis_name}' not found")

    def enable_crisis(self, crisis_name: str, enabled: bool = True) -> None:
        """
        Enable or disable a specific crisis peak.

        Args:
            crisis_name: Name of crisis (e.g., "nuclear_age")
            enabled: True to enable, False to disable

        Raises:
            ValueError: If crisis_name not found
        """
        for crisis in self.crisis_peaks:
            if crisis.name == crisis_name:
                crisis.enabled = enabled
                return
        raise ValueError(f"Crisis '{crisis_name}' not found")

    def plot_hazard_function(self, k_range: Optional[tuple] = None) -> None:
        """
        Plot the hazard function λ(K) vs Kardashev scale.

        Requires matplotlib. Useful for understanding the crisis landscape.

        Args:
            k_range: Tuple of (k_min, k_max) for plotting range. Default: (0.5, 3.0)

        Raises:
            ImportError: If matplotlib not available
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib required for plotting. Install with: pip install matplotlib")

        if k_range is None:
            k_range = (0.5, 3.0)

        k_values = np.linspace(k_range[0], k_range[1], 1000)
        lambda_values = np.array([self.calculate_kardashev_hazard_rate(k) for k in k_values])

        fig, ax = plt.subplots(figsize=(10, 6), facecolor='black')
        ax.set_facecolor('black')

        # Plot hazard function
        ax.plot(k_values, lambda_values, color='cyan', linewidth=2, label='Total hazard λ(K)')

        # Mark crisis peaks
        for crisis in self.crisis_peaks:
            if crisis.enabled:
                ax.axvline(crisis.kardashev_center, color='red', linestyle='--', alpha=0.5)
                ax.text(
                    crisis.kardashev_center, ax.get_ylim()[1] * 0.95,
                    crisis.name.replace('_', ' ').title(),
                    rotation=90, va='top', ha='right', color='white', fontsize=8
                )

        # Mark Kardashev milestones
        ax.axvline(1.0, color='yellow', linestyle=':', alpha=0.3, label='Type I')
        ax.axvline(2.0, color='yellow', linestyle=':', alpha=0.3, label='Type II')
        ax.axvline(3.0, color='yellow', linestyle=':', alpha=0.3, label='Type III')

        ax.set_xlabel('Kardashev Scale', color='white', fontsize=12)
        ax.set_ylabel('Hazard Rate λ(K) [per Myr]', color='white', fontsize=12)
        ax.set_title('Self-Destruction Hazard Function', color='white', fontsize=14, fontweight='bold')
        ax.tick_params(colors='white')
        ax.legend(loc='upper left', facecolor='black', edgecolor='white', labelcolor='white')
        ax.grid(True, alpha=0.2, color='white')

        plt.tight_layout()
        plt.show()
