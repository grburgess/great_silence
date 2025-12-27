"""Configuration and parameter classes for simulations."""

from dataclasses import dataclass, field
from typing import Dict, Any
import yaml


@dataclass
class GalaxyParameters:
    """Parameters for galaxy structure and dynamics."""

    # Galaxy size and structure
    disk_radius_kpc: float = 15.0  # Disk radius in kiloparsecs
    disk_height_kpc: float = 0.3  # Disk scale height (thin disk)
    thick_disk_height_kpc: float = 1.0  # Thick disk scale height
    bulge_radius_kpc: float = 1.0  # Bulge effective radius (Hernquist scale)
    halo_radius_kpc: float = 50.0  # Dark matter halo radius

    # Stellar density profile
    stellar_density_profile: str = "exponential"  # or "double_exponential"
    scale_length_kpc: float = 3.5  # Disk scale length

    # Bulge and multi-component structure
    include_bulge: bool = True  # Include central bulge component
    bulge_fraction: float = 0.2  # Fraction of stars in bulge (~20% like MW)
    bulge_to_total_ratio: float = 0.2  # Alternative parameterization

    # Thick disk (old, metal-poor component)
    include_thick_disk: bool = False  # Include thick disk (for advanced users)
    thick_disk_fraction: float = 0.1  # Fraction of stars in thick disk

    # Radial gradients (inside-out formation)
    use_age_gradient: bool = True  # Radial age gradient (inner stars older)
    age_gradient_scale_kpc: float = 8.0  # Scale length for age gradient
    central_mean_age_gyr: float = 11.0  # Mean age in bulge/center
    outer_mean_age_gyr: float = 3.0  # Mean age in outer disk

    # Metallicity gradient
    use_metallicity_gradient: bool = True  # Radial metallicity gradient
    central_metallicity_feh: float = 0.3  # [Fe/H] in bulge (metal-rich)
    metallicity_gradient_dex_per_kpc: float = -0.07  # Gradient (~-0.07 dex/kpc in MW)

    # Dynamics
    rotation_velocity_km_s: float = 220.0  # Circular velocity at solar radius
    bulge_velocity_dispersion_km_s: float = 100.0  # Bulge velocity dispersion
    spiral_arm_count: int = 4
    spiral_arm_strength: float = 0.2
    enable_bar: bool = True

    # Star population
    total_stars: int = 100_000_000  # Total stars in simulation


@dataclass
class AstrophysicsParameters:
    """Parameters for astrophysical processes."""

    # Star formation
    current_sfr_msun_yr: float = 1.5  # Current star formation rate (solar masses/year)
    sfr_peak_age_gyr: float = 10.0  # Peak star formation epoch

    # IMF (Initial Mass Function)
    imf_type: str = "kroupa"  # kroupa, salpeter, or chabrier

    # Supernovae
    sn_rate_per_century: float = 2.0  # Supernova rate per century
    sn_lethal_range_pc: float = 10.0  # Lethal range in parsecs
    sn_sterilization_range_pc: float = 30.0  # Sterilization range

    # Gamma-ray bursts
    grb_rate_per_century: float = 0.01
    grb_lethal_range_kpc: float = 5.0
    grb_beaming_angle_deg: float = 10.0


@dataclass
class CivilizationParameters:
    """
    Parameters for civilization emergence and expansion.

    Default values are calibrated to be consistent with Fermi Paradox
    observations (no detection of alien civilizations). Current defaults
    represent a "Moderate Filter" scenario.
    """

    # Drake equation parameters (RECALIBRATED for Fermi consistency)
    fraction_stars_with_planets: float = 1.0  # Well-established from Kepler
    avg_habitable_planets_per_system: float = 0.2  # ~20% reasonable estimate
    fraction_develop_life: float = 0.1  # ← REDUCED from 0.5 (more conservative)
    fraction_develop_intelligence: float = 0.01  # ← REDUCED from 0.1 (rarer)
    fraction_develop_technology: float = 0.1  # Unchanged
    # Combined: 1.0 × 0.2 × 0.1 × 0.01 × 0.1 = 0.00002 (0.002% per star per Gyr)
    # Predicts ~1000 civilizations over galaxy lifetime (Fermi-consistent)

    # Civilization lifetime and behavior
    mean_civilization_lifetime_myr: float = 1.0  # Million years
    lifetime_stddev_myr: float = 0.5

    # Expansion parameters
    expansion_enabled: bool = True
    expansion_velocity_fraction_c: float = 0.01  # Fraction of light speed (1% c)
    colonization_probability: float = 0.8
    min_habitable_distance_pc: float = 1.0  # Minimum distance to habitable stars
    max_expansion_range_pc: float = 1000.0  # Maximum colonization range

    # Self-destruction model
    self_destruction_model_type: str = "kardashev_dependent"  # "flat" or "kardashev_dependent"
    self_destruction_probability_per_myr: float = 0.1  # 10% per Myr (for flat model)

    # Kardashev-dependent self-destruction parameters
    baseline_self_destruction_rate: float = 0.01  # Baseline hazard at K=0 (per Myr)
    baseline_risk_scaling: float = 0.05  # Linear increase with K

    # Crisis peak amplitudes (can be tuned for scenario exploration)
    crisis_nuclear_age_amplitude: float = 0.15  # K~0.72
    crisis_planetary_unification_amplitude: float = 0.12  # K~0.85
    crisis_ai_transition_amplitude: float = 0.20  # K~1.05 (strongest by default)
    crisis_interplanetary_amplitude: float = 0.10  # K~1.25
    crisis_stellar_engineering_amplitude: float = 0.08  # K~1.80
    crisis_relativistic_weapons_amplitude: float = 0.06  # K~2.50

    # Enable/disable individual crises (for sensitivity analysis)
    enable_nuclear_crisis: bool = True
    enable_planetary_unification_crisis: bool = True
    enable_ai_crisis: bool = True
    enable_interplanetary_crisis: bool = True
    enable_stellar_crisis: bool = True
    enable_relativistic_weapons_crisis: bool = True

    # Kardashev scale progression
    initial_kardashev_scale_mean: float = 0.7  # Mean starting level (modern Earth ~0.7)
    initial_kardashev_scale_stddev: float = 0.1  # Variation in starting technology
    kardashev_advancement_rate_mean: float = 0.01  # Mean advancement rate per Myr
    kardashev_advancement_rate_stddev: float = 0.005  # Variation in advancement rate
    kardashev_stagnation_probability_per_myr: float = 0.05  # Chance of tech stagnation
    kardashev_breakthrough_probability_per_myr: float = 0.02  # Chance of rapid advancement
    kardashev_breakthrough_multiplier: float = 3.0  # How much faster during breakthrough
    kardashev_max_scale: float = 3.0  # Maximum technological level (Type III)


@dataclass
class SimulationParameters:
    """Parameters for simulation execution."""

    # Time parameters
    simulation_duration_gyr: float = 10.0  # Billion years
    time_step_myr: float = 1.0  # Million years per step

    # Monte Carlo
    num_realizations: int = 100
    random_seed: int = 42

    # Performance
    use_numba: bool = True
    parallel_processing: bool = True
    chunk_size: int = 10000

    # Physics options
    enable_stellar_motion: bool = False  # Enable gravitational evolution of stellar positions (EXPERIMENTAL)

    # Output
    save_snapshots: bool = True
    snapshot_interval_myr: float = 100.0
    output_directory: str = "output"


@dataclass
class SimulationConfig:
    """Main configuration container for simulations."""

    galaxy: GalaxyParameters = field(default_factory=GalaxyParameters)
    astrophysics: AstrophysicsParameters = field(default_factory=AstrophysicsParameters)
    civilization: CivilizationParameters = field(default_factory=CivilizationParameters)
    simulation: SimulationParameters = field(default_factory=SimulationParameters)

    @classmethod
    def from_yaml(cls, filepath: str) -> "SimulationConfig":
        """Load configuration from YAML file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        return cls(
            galaxy=GalaxyParameters(**data.get('galaxy', {})),
            astrophysics=AstrophysicsParameters(**data.get('astrophysics', {})),
            civilization=CivilizationParameters(**data.get('civilization', {})),
            simulation=SimulationParameters(**data.get('simulation', {}))
        )

    def to_yaml(self, filepath: str) -> None:
        """Save configuration to YAML file."""
        data = {
            'galaxy': self.galaxy.__dict__,
            'astrophysics': self.astrophysics.__dict__,
            'civilization': self.civilization.__dict__,
            'simulation': self.simulation.__dict__
        }
        with open(filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'galaxy': self.galaxy.__dict__,
            'astrophysics': self.astrophysics.__dict__,
            'civilization': self.civilization.__dict__,
            'simulation': self.simulation.__dict__
        }

    @classmethod
    def with_preset(cls, preset: str) -> "SimulationConfig":
        """
        Create configuration with Drake equation preset.

        Presets represent different Great Filter hypotheses:
        - 'early_filter': Life is extremely rare (abiogenesis is hard)
        - 'late_filter': Technology civilizations self-destruct quickly
        - 'rare_earth': Habitable planets are extremely rare
        - 'optimistic': Life and intelligence are common
        - 'moderate': Default balanced parameters (Fermi-consistent)

        Args:
            preset: Name of preset ('early_filter', 'late_filter', 'rare_earth', 'optimistic', 'moderate')

        Returns:
            SimulationConfig with preset parameters
        """
        config = cls()

        if preset == 'early_filter':
            # Great Filter is early: Abiogenesis is extremely difficult
            config.civilization.fraction_develop_life = 0.001  # 0.1% instead of 10%
            config.civilization.fraction_develop_intelligence = 0.1
            config.civilization.fraction_develop_technology = 0.5
            config.civilization.mean_civilization_lifetime_myr = 10.0  # Long-lived
            config.civilization.self_destruction_probability_per_myr = 0.01  # Low risk (flat model)
            config.civilization.self_destruction_model_type = "flat"
            # Predicts: ~10 civilizations over galaxy lifetime

        elif preset == 'late_filter':
            # Great Filter is late: Civilizations self-destruct rapidly at critical transitions
            config.civilization.fraction_develop_life = 0.5  # Life is common
            config.civilization.fraction_develop_intelligence = 0.1
            config.civilization.fraction_develop_technology = 0.1
            config.civilization.mean_civilization_lifetime_myr = 0.1  # Very short-lived
            config.civilization.self_destruction_model_type = "kardashev_dependent"
            # Amplify crisis peaks for strong late filter
            config.civilization.crisis_nuclear_age_amplitude = 0.25  # Very dangerous
            config.civilization.crisis_ai_transition_amplitude = 0.35  # Extremely dangerous
            config.civilization.crisis_interplanetary_amplitude = 0.20
            # Predicts: ~100 civilizations at any given time, but very short-lived

        elif preset == 'rare_earth':
            # Rare Earth hypothesis: Habitable planets are extremely rare
            config.civilization.avg_habitable_planets_per_system = 0.01  # 1% instead of 20%
            config.civilization.fraction_develop_life = 0.5
            config.civilization.fraction_develop_intelligence = 0.1
            config.civilization.fraction_develop_technology = 0.5
            config.civilization.mean_civilization_lifetime_myr = 10.0
            config.civilization.self_destruction_probability_per_myr = 0.01
            # Predicts: ~50 civilizations over galaxy lifetime

        elif preset == 'optimistic':
            # Optimistic scenario: Life, intelligence, and technology are common
            config.civilization.fraction_develop_life = 0.5  # 50%
            config.civilization.fraction_develop_intelligence = 0.1  # 10%
            config.civilization.fraction_develop_technology = 0.5  # 50%
            config.civilization.mean_civilization_lifetime_myr = 10.0  # Long-lived
            config.civilization.self_destruction_probability_per_myr = 0.01  # Low risk
            # Predicts: ~50,000 civilizations over galaxy lifetime (NOT Fermi-consistent)
            # WARNING: This preset is for exploration only, inconsistent with observations

        elif preset == 'moderate':
            # Use defaults (already Fermi-consistent)
            pass

        else:
            raise ValueError(
                f"Unknown preset '{preset}'. "
                f"Choose from: early_filter, late_filter, rare_earth, optimistic, moderate"
            )

        return config
