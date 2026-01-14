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
    max_stellar_age_gyr: float = 13.0  # Maximum stellar age / age of universe (Gyr)

    # Habitable star mass range (solar masses)
    habitable_mass_min_msun: float = 0.5  # Minimum mass for habitable zone stability
    habitable_mass_max_msun: float = 1.5  # Maximum mass (main sequence lifetime constraint)


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
    grb_fraction_of_sne: float = 0.01  # Base fraction of massive SNe producing GRBs
    grb_min_progenitor_mass: float = 20.0  # Minimum mass for GRB progenitor (Msun)

    # Neutron star mergers (kilonovae)
    ns_merger_rate_per_myr: float = 50.0  # Galactic rate ~10-100/Myr (Abbott+ 2017)
    ns_sgrb_beaming_angle_deg: float = 5.0  # Short GRB beaming (~3-10 deg)
    ns_sgrb_lethal_range_kpc: float = 3.0  # sGRB lethal distance in kpc
    ns_kilonova_lethal_range_pc: float = 30.0  # Kilonova lethal distance in pc
    ns_kilonova_sterilization_range_pc: float = 100.0  # Partial sterilization range
    ns_delay_time_min_gyr: float = 0.01  # Minimum NS-NS inspiral time
    ns_delay_time_max_gyr: float = 10.0  # Maximum NS-NS inspiral time


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

    # Self-replicating probe expansion parameters
    expansion_enabled: bool = True
    min_kardashev_for_expansion: float = 0.85  # Minimum tech level for interstellar probes
    # NOTE: Velocity, range, offspring count, and replication delay are now
    # calculated dynamically based on Kardashev level at expansion start
    # See great_silence/civilization/probe_design.py for scaling functions

    # Metallicity-based targeting (probes need resources for replication)
    # Override these to customize metallicity thresholds; None = use Kardashev-based defaults
    metallicity_threshold_k085: float = -0.3  # K=0.85-0.95: Metal-rich systems required
    metallicity_threshold_k095: float = -0.5  # K=0.95-1.20: Solar metallicity acceptable
    metallicity_threshold_k120: float = -1.0  # K>1.20: Can use metal-poor systems

    # Probe sensor capabilities for mid-flight course corrections
    # Probes can detect and retarget to favorable planets within sensor range
    probe_sensor_range_pc: float = 10.0  # Sensor range in parsecs (default: 10 pc)
    enable_mid_flight_retargeting: bool = (
        False  # PRIORITY 1D: Disabled (O(N) brute force, needs spatial index fix)
    )

    # Expansion limits
    max_colonies_per_civilization: int = 1000  # Cap to prevent runaway expansion

    # Emergence constraints
    min_stellar_age_for_life_gyr: float = 1.0  # Minimum stellar age for complex life (Gyr)

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

    # Colony maturation and resilience
    colony_maturation_time_myr: float = (
        0.1  # Time colonies need before contributing to resilience (Myr)
    )

    # Colonization lifetime bonus
    colonization_lifetime_bonus_myr: float = (
        0.5  # Logarithmic bonus: bonus × log(1 + num_mature_colonies)
    )

    # Home world destruction effects
    home_world_fragility_period_myr: float = (
        0.5  # Duration of fragility after home world loss (Myr)
    )
    home_world_fragility_factor: float = (
        0.5  # Lifetime multiplier during fragility (0.5 = 50% reduction)
    )

    # Colonial war mechanics
    colonial_war_colony_threshold: int = (
        10  # Minimum mature colonies before colonial war risk applies
    )
    colonial_war_kardashev_threshold: float = 1.5  # Minimum K-scale for colonial war (Type II civs)
    colonial_war_amplitude: float = 0.05  # Base hazard rate amplitude for colonial war (per Myr)

    # Personality system
    personality_assignment_model: str = "kardashev_dependent"
    personality_fixed_friendliness: float = 0.5
    personality_evolution_enabled: bool = True
    personality_evolution_rate: float = 0.1

    # Encounter mechanics
    first_contact_detection_range_pc: float = 100.0
    encounter_scan_interval_myr: float = 100.0
    sensor_range_pc: float = 50.0

    # War mechanics
    war_outcome_model: str = "winner_takes_territory"
    war_duration_max_myr: float = 10.0
    war_stalemate_probability: float = 0.1
    tech_advantage_sensitivity: float = 0.3
    fleet_velocity_multiplier: float = 0.01  # Fraction of c for fleet movement
    battle_resolution_interval_myr: float = 0.5

    # Reputation system
    reputation_enabled: bool = True
    reputation_weight_in_war_decision: float = 0.3
    reputation_propagation_enabled: bool = True
    reputation_decay_rate: float = 0.01

    # Alliance system
    alliance_formation_enabled: bool = True
    alliance_propagation_enabled: bool = True
    alliance_light_cone_constraint: bool = True

    # Strategic resources
    resource_generation_rate: float = 10.0
    war_resource_cost_myr: float = 5.0
    vassalization_enabled: bool = True
    tribute_rate_default: float = 0.2


@dataclass
class SimulationParameters:
    """Parameters for simulation execution."""

    # Time parameters
    simulation_duration_gyr: float = 10.0  # Billion years
    time_step_myr: float = 1.0  # Million years per step (used as base/medium when adaptive)

    # Adaptive time stepping
    adaptive_timestepping: bool = True  # Enable adaptive timesteps based on events
    min_timestep_myr: float = 0.01  # 10,000 years (fine resolution)
    medium_timestep_myr: float = 0.1  # 100,000 years (active civilizations, default)
    max_timestep_myr: float = 10.0  # 10 Myr (quiet periods, no events)
    max_adaptive_step_myr: float = 1.0  # Step to probe events within this range

    # Monte Carlo
    num_realizations: int = 100
    random_seed: int = 42

    # Performance
    use_numba: bool = True
    parallel_processing: bool = True
    chunk_size: int = 10000

    # Physics options
    enable_stellar_motion: bool = (
        False  # Enable gravitational evolution of stellar positions (EXPERIMENTAL)
    )

    # Output
    save_snapshots: bool = True
    snapshot_interval_myr: float = 100.0
    output_directory: str = "output"

    # Progress tracking
    progress_verbose_level: int = 1  # 0=off, 1=basic, 2=detailed
    progress_update_interval_pct: float = 0.1  # Time threshold (%)
    progress_update_interval_steps: int = 10  # Step threshold
    progress_update_interval_seconds: float = 0.5  # Wall-time threshold (sec)
    progress_show_iteration_rate: bool = True
    progress_show_probe_count: bool = True

    # Within-simulation parallelization (causality-preserving)
    enable_within_sim_parallel: bool = False  # Opt-in for parallelization
    parallel_worker_threads: int = 8  # Number of worker threads (M1 Max default)
    parallel_min_civs_threshold: int = 10  # Minimum civs to enable parallelization
    enable_causality_checks: bool = True  # Validate causality partitioning (debug)
    parallel_check_shared_colonies: bool = True  # Include colony overlap in causality


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
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)

        return cls(
            galaxy=GalaxyParameters(**data.get("galaxy", {})),
            astrophysics=AstrophysicsParameters(**data.get("astrophysics", {})),
            civilization=CivilizationParameters(**data.get("civilization", {})),
            simulation=SimulationParameters(**data.get("simulation", {})),
        )

    def to_yaml(self, filepath: str) -> None:
        """Save configuration to YAML file."""
        data = {
            "galaxy": self.galaxy.__dict__,
            "astrophysics": self.astrophysics.__dict__,
            "civilization": self.civilization.__dict__,
            "simulation": self.simulation.__dict__,
        }
        with open(filepath, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "galaxy": self.galaxy.__dict__,
            "astrophysics": self.astrophysics.__dict__,
            "civilization": self.civilization.__dict__,
            "simulation": self.simulation.__dict__,
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

        if preset == "early_filter":
            # Great Filter is early: Abiogenesis is extremely difficult
            config.civilization.fraction_develop_life = 0.001  # 0.1% instead of 10%
            config.civilization.fraction_develop_intelligence = 0.1
            config.civilization.fraction_develop_technology = 0.5
            config.civilization.mean_civilization_lifetime_myr = 10.0  # Long-lived
            config.civilization.self_destruction_probability_per_myr = 0.01  # Low risk (flat model)
            config.civilization.self_destruction_model_type = "flat"
            # Predicts: ~10 civilizations over galaxy lifetime

        elif preset == "late_filter":
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

        elif preset == "rare_earth":
            # Rare Earth hypothesis: Habitable planets are extremely rare
            config.civilization.avg_habitable_planets_per_system = 0.01  # 1% instead of 20%
            config.civilization.fraction_develop_life = 0.5
            config.civilization.fraction_develop_intelligence = 0.1
            config.civilization.fraction_develop_technology = 0.5
            config.civilization.mean_civilization_lifetime_myr = 10.0
            config.civilization.self_destruction_probability_per_myr = 0.01
            # Predicts: ~50 civilizations over galaxy lifetime

        elif preset == "optimistic":
            # Optimistic scenario: Life, intelligence, and technology are common
            config.civilization.fraction_develop_life = 0.5  # 50%
            config.civilization.fraction_develop_intelligence = 0.1  # 10%
            config.civilization.fraction_develop_technology = 0.5  # 50%
            config.civilization.mean_civilization_lifetime_myr = 10.0  # Long-lived
            config.civilization.self_destruction_probability_per_myr = 0.01  # Low risk
            # Predicts: ~50,000 civilizations over galaxy lifetime (NOT Fermi-consistent)
            # WARNING: This preset is for exploration only, inconsistent with observations

        elif preset == "moderate":
            # Use defaults (already Fermi-consistent)
            pass

        else:
            raise ValueError(
                f"Unknown preset '{preset}'. "
                f"Choose from: early_filter, late_filter, rare_earth, optimistic, moderate"
            )

        return config
