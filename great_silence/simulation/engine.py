"""Main simulation engine for galactic civilization modeling."""

import numpy as np
from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, field
from tqdm import tqdm

from ..config.parameters import SimulationConfig
from ..galaxy.structure import GalaxyModel
from ..galaxy.star_formation import StarFormationHistory, InitialMassFunction
from ..civilization.probe_design import (
    probe_velocity_from_kardashev,
    per_hop_range_from_kardashev,
    offspring_count,
    replication_delay_years,
    min_metallicity_for_replication,
    MIN_KARDASHEV_FOR_EXPANSION,
    C_PC_YR
)


@dataclass
class ProbeState:
    """State of a single self-replicating probe."""

    probe_id: int
    parent_probe_id: Optional[int]  # None for home-world-launched probes
    generation: int  # 0 = launched from home world

    launch_star_idx: int
    target_star_idx: int

    launch_time_myr: float
    arrival_time_myr: float

    # Inherited from parent civilization (locked at launch)
    velocity_c: float
    per_hop_range_pc: float
    offspring_count: int
    replication_delay_yr: float

    # Replication status (fields with defaults must come after required fields)
    has_arrived: bool = False
    has_replicated: bool = False
    replication_complete_time_myr: Optional[float] = None


@dataclass
class CivilizationState:
    """State of a single civilization."""

    civ_id: int
    birth_time_myr: float  # When civilization emerged
    parent_star_idx: int  # Index of star where civilization originated
    colonized_stars: List[int] = field(default_factory=list)  # Indices of colonized stars
    colony_arrival_times: Dict[int, float] = field(default_factory=dict)  # star_idx -> arrival_time_myr
    kardashev_scale: float = 0.7  # Technological level: 0.7 (modern Earth) to 3.0 (galaxy-scale)
    kardashev_advancement_rate: float = 0.01  # Individual advancement rate (varies per civilization)
    is_active: bool = True
    death_time_myr: Optional[float] = None
    death_cause: Optional[str] = None  # 'extinction_event', 'self_destruction', 'old_age', 'supernova', 'grb'

    # Self-replicating probe expansion parameters (locked at first launch)
    expansion_program_started: bool = False
    expansion_start_kardashev: Optional[float] = None
    probe_velocity_c: Optional[float] = None
    probe_per_hop_range_pc: Optional[float] = None
    probe_offspring_count: Optional[int] = None
    probe_replication_delay_yr: Optional[float] = None
    probe_min_metallicity: Optional[float] = None
    probe_sensor_range_pc: Optional[float] = None

    # Probe tracking
    active_probes: List['ProbeState'] = field(default_factory=list)


@dataclass
class SimulationSnapshot:
    """Snapshot of simulation state at a given time."""

    time_myr: float
    active_civilizations: int
    total_civilizations_ever: int
    colonized_systems: int
    civilization_states: List[CivilizationState]
    stellar_positions: np.ndarray  # For visualization


@dataclass
class HazardEvent:
    """Record of an astrophysical hazard event."""

    time_myr: float
    event_type: str  # 'supernova', 'grb'
    position: np.ndarray  # 3D position in kpc
    energy: float  # Event energy (ergs)
    sterilization_radius_pc: float  # Lethal range in parsecs
    affected_civ_ids: List[int] = field(default_factory=list)  # Civilizations destroyed/affected


class GalaxySimulation:
    """
    Main simulation engine orchestrating all components.

    Manages galaxy evolution, civilization emergence/expansion, and
    astrophysical hazards over time.
    """

    def __init__(self, config: SimulationConfig, seed: Optional[int] = None):
        """
        Initialize simulation.

        Args:
            config: Simulation configuration
            seed: Random seed for reproducibility
        """
        self.config = config
        self.seed = seed if seed is not None else config.simulation.random_seed
        self.rng = np.random.default_rng(self.seed)

        # Initialize galaxy model
        self.galaxy = GalaxyModel(
            config.galaxy,
            seed=self.seed,
            use_numba=config.simulation.use_numba
        )

        # Star formation history and IMF
        self.sfh = StarFormationHistory(config.astrophysics)
        self.imf = InitialMassFunction(config.astrophysics.imf_type)

        # Probe tracking (for self-replicating expansion)
        self.next_probe_id = 0

        # Extinction model
        from ..civilization.extinction import ExtinctionModel, CrisisPeak
        crisis_peaks = [
            CrisisPeak(
                name="nuclear_age",
                kardashev_center=0.72,
                width=0.05,
                amplitude=config.civilization.crisis_nuclear_age_amplitude,
                enabled=config.civilization.enable_nuclear_crisis
            ),
            CrisisPeak(
                name="planetary_unification",
                kardashev_center=0.85,
                width=0.08,
                amplitude=config.civilization.crisis_planetary_unification_amplitude,
                enabled=config.civilization.enable_planetary_unification_crisis
            ),
            CrisisPeak(
                name="ai_transition",
                kardashev_center=1.05,
                width=0.10,
                amplitude=config.civilization.crisis_ai_transition_amplitude,
                enabled=config.civilization.enable_ai_crisis
            ),
            CrisisPeak(
                name="interplanetary_expansion",
                kardashev_center=1.25,
                width=0.15,
                amplitude=config.civilization.crisis_interplanetary_amplitude,
                enabled=config.civilization.enable_interplanetary_crisis
            ),
            CrisisPeak(
                name="stellar_engineering",
                kardashev_center=1.80,
                width=0.20,
                amplitude=config.civilization.crisis_stellar_engineering_amplitude,
                enabled=config.civilization.enable_stellar_crisis
            ),
            CrisisPeak(
                name="relativistic_weapons",
                kardashev_center=2.50,
                width=0.25,
                amplitude=config.civilization.crisis_relativistic_weapons_amplitude,
                enabled=config.civilization.enable_relativistic_weapons_crisis
            ),
        ]

        self.extinction_model = ExtinctionModel(
            self_destruction_rate=config.civilization.self_destruction_probability_per_myr,
            mean_lifetime_myr=config.civilization.mean_civilization_lifetime_myr,
            model_type=config.civilization.self_destruction_model_type,
            baseline_rate=config.civilization.baseline_self_destruction_rate,
            baseline_scaling=config.civilization.baseline_risk_scaling,
            crisis_peaks=crisis_peaks
        )

        # Simulation state
        self.current_time_myr: float = 0.0
        self.civilizations: List[CivilizationState] = []
        self.next_civ_id: int = 0

        # History tracking
        self.snapshots: List[SimulationSnapshot] = []
        self.hazard_events: List[HazardEvent] = []

        # Habitable star indices (cached)
        self.habitable_star_indices: Optional[np.ndarray] = None

        # Colonized stars tracking (for performance)
        self._colonized_mask: Optional[np.ndarray] = None

    def initialize(self) -> None:
        """Initialize galaxy and stellar population."""
        print("Initializing galaxy...")
        self.galaxy.generate_stellar_population()

        print("Assigning stellar properties...")

        # Calculate galactocentric radii for gradients
        x, y = self.galaxy.positions[:, 0], self.galaxy.positions[:, 1]
        radii = np.sqrt(x**2 + y**2)

        # Generate stellar ages (with radial gradient if enabled)
        max_age_gyr = 13.0  # Age of universe
        if self.config.galaxy.use_age_gradient:
            self.galaxy.ages = self.sfh.generate_stellar_ages_with_gradient(
                self.config.galaxy.total_stars,
                radii=radii,
                component_types=self.galaxy.component_type,
                central_mean_age_gyr=self.config.galaxy.central_mean_age_gyr,
                outer_mean_age_gyr=self.config.galaxy.outer_mean_age_gyr,
                age_gradient_scale_kpc=self.config.galaxy.age_gradient_scale_kpc,
                max_age_gyr=max_age_gyr,
                seed=self.seed
            )
        else:
            self.galaxy.ages = self.sfh.generate_stellar_ages(
                self.config.galaxy.total_stars,
                max_age_gyr=max_age_gyr,
                seed=self.seed
            )

        # Generate stellar masses from IMF
        self.galaxy.masses = self.imf.sample(
            self.config.galaxy.total_stars,
            seed=self.seed + 1
        )

        # Generate metallicities (with radial gradient if enabled)
        if self.config.galaxy.use_metallicity_gradient:
            self.galaxy.metallicities = self.galaxy.calculate_metallicities()
        else:
            # Uniform metallicity
            self.galaxy.metallicities = np.zeros(self.config.galaxy.total_stars)

        # Determine stellar types (simplified: 0=unsuitable, 1=potentially habitable)
        # Stars between 0.5 and 1.5 solar masses are considered potentially habitable
        self.galaxy.stellar_types = (
            (self.galaxy.masses >= 0.5) & (self.galaxy.masses <= 1.5)
        ).astype(int)

        # Cache habitable star indices
        self.habitable_star_indices = np.where(self.galaxy.stellar_types == 1)[0]

        # Initialize colonized mask
        self._colonized_mask = np.zeros(self.config.galaxy.total_stars, dtype=bool)

        # Build spatial index for efficient hazard and expansion queries
        if self.config.simulation.use_numba:
            print("Building spatial index for fast queries...")
            from ..utils.spatial import SpatialIndex
            self._spatial_index = SpatialIndex(self.galaxy.positions)
        else:
            self._spatial_index = None

        print(f"Galaxy initialized with {len(self.galaxy.positions)} stars")
        if self.config.galaxy.include_bulge:
            n_bulge = np.sum(self.galaxy.component_type == 0)
            print(f"  Bulge stars: {n_bulge} ({100*n_bulge/len(self.galaxy.positions):.1f}%)")
            print(f"  Disk stars: {len(self.galaxy.positions) - n_bulge}")
        print(f"Habitable stars: {len(self.habitable_star_indices)}")

    def _step(self) -> None:
        """
        Execute a single simulation timestep.

        This method can be overridden by subclasses for custom stepping logic.
        """
        # Evolve galaxy (stellar motion)
        self.galaxy.evolve_positions(
            self.config.simulation.time_step_myr,
            use_numba=self.config.simulation.use_numba,
            enable_motion=self.config.simulation.enable_stellar_motion
        )

        # Check for new civilization emergence
        self._check_civilization_emergence()

        # Evolve existing civilizations
        self._evolve_civilizations()

        # Apply astrophysical hazards
        self._apply_hazards()

        # Advance time
        self.current_time_myr += self.config.simulation.time_step_myr

    def run(self, verbose: bool = True) -> None:
        """
        Run the main simulation loop.

        Args:
            verbose: Whether to show progress bar
        """
        if self.galaxy.positions is None:
            self.initialize()

        total_steps = int(
            self.config.simulation.simulation_duration_gyr * 1000 /
            self.config.simulation.time_step_myr
        )

        # Progress bar
        pbar = tqdm(total=total_steps, desc="Simulating", disable=not verbose)

        snapshot_counter = 0
        next_snapshot_time = 0.0

        while self.current_time_myr < self.config.simulation.simulation_duration_gyr * 1000:
            # Execute single timestep
            self._step()

            # Save snapshot if needed
            if self.config.simulation.save_snapshots:
                if self.current_time_myr >= next_snapshot_time:
                    self._save_snapshot()
                    next_snapshot_time += self.config.simulation.snapshot_interval_myr

            pbar.update(1)

        pbar.close()

        # Final snapshot
        if self.config.simulation.save_snapshots:
            self._save_snapshot()

        print(f"\nSimulation complete!")
        print(f"Total civilizations emerged: {self.next_civ_id}")
        print(f"Active civilizations: {sum(c.is_active for c in self.civilizations)}")

    def _check_civilization_emergence(self) -> None:
        """Check for new civilization emergence based on Drake equation."""
        if self.habitable_star_indices is None:
            return

        dt_myr = self.config.simulation.time_step_myr
        params = self.config.civilization

        # Check each habitable star
        # Only consider stars old enough to have developed life (> 1 Gyr)
        old_enough = self.galaxy.ages[self.habitable_star_indices] > 1.0
        not_colonized = ~self._colonized_mask[self.habitable_star_indices]

        eligible_mask = old_enough & not_colonized
        eligible_stars = self.habitable_star_indices[eligible_mask]

        if len(eligible_stars) == 0:
            return

        # Calculate emergence probability for each eligible star
        # (accounts for metallicity effects on planet formation)
        p_emergence_array = np.zeros(len(eligible_stars))

        for i, star_idx in enumerate(eligible_stars):
            # Drake equation factors
            f_life = params.fraction_develop_life
            f_intel = params.fraction_develop_intelligence
            f_tech = params.fraction_develop_technology
            n_habitable = params.avg_habitable_planets_per_system

            # Metallicity-dependent planet fraction
            # Higher metallicity → more planets (Fischer & Valenti 2005)
            # f_planets(M) = f_base * 10^(metallicity)
            feh = self.galaxy.metallicities[star_idx]
            f_base = params.fraction_stars_with_planets

            if self.config.galaxy.use_metallicity_gradient:
                # Metallicity effect: factor of ~3 per 0.5 dex
                # At solar metallicity (0.0): f_planets = f_base
                # At +0.3 dex (bulge): f_planets = 2 * f_base
                # At -0.5 dex (outer disk): f_planets = 0.3 * f_base
                f_planets = f_base * np.power(10.0, feh)
                f_planets = np.clip(f_planets, 0.01, 1.0)  # Physical bounds
            else:
                f_planets = f_base

            # Combined probability per Gyr
            p_emergence_per_gyr = f_planets * n_habitable * f_life * f_intel * f_tech

            # Scale to time step
            p_emergence_array[i] = p_emergence_per_gyr * dt_myr / 1000.0

        # Sample emergence (each star has its own probability)
        emerge = self.rng.uniform(0, 1, len(eligible_stars)) < p_emergence_array

        # Create new civilizations
        for star_idx in eligible_stars[emerge]:
            star_idx_int = int(star_idx)

            # Sample random initial Kardashev scale
            initial_kardashev = self.rng.normal(
                self.config.civilization.initial_kardashev_scale_mean,
                self.config.civilization.initial_kardashev_scale_stddev
            )
            initial_kardashev = max(0.5, min(1.0, initial_kardashev))  # Clamp to [0.5, 1.0]

            # Sample random advancement rate
            advancement_rate = self.rng.normal(
                self.config.civilization.kardashev_advancement_rate_mean,
                self.config.civilization.kardashev_advancement_rate_stddev
            )
            advancement_rate = max(0.001, advancement_rate)  # Ensure positive

            new_civ = CivilizationState(
                civ_id=self.next_civ_id,
                birth_time_myr=self.current_time_myr,
                parent_star_idx=star_idx_int,
                colonized_stars=[star_idx_int],
                colony_arrival_times={star_idx_int: self.current_time_myr},  # Home world "arrived" at birth
                kardashev_scale=initial_kardashev,
                kardashev_advancement_rate=advancement_rate
            )
            self.civilizations.append(new_civ)
            self._colonized_mask[star_idx_int] = True  # Mark as colonized
            self.next_civ_id += 1

    def _evolve_civilizations(self) -> None:
        """Evolve existing civilizations (expansion, self-destruction, technological advancement)."""
        dt_myr = self.config.simulation.time_step_myr

        for civ in self.civilizations:
            if not civ.is_active:
                continue

            # Technological advancement with stochastic events
            base_advancement = civ.kardashev_advancement_rate * dt_myr

            # Check for technological breakthrough (rapid advancement)
            p_breakthrough = self.config.civilization.kardashev_breakthrough_probability_per_myr * dt_myr
            if self.rng.uniform(0, 1) < p_breakthrough:
                # Breakthrough! Advance faster
                advancement = base_advancement * self.config.civilization.kardashev_breakthrough_multiplier
            # Check for technological stagnation
            elif self.rng.uniform(0, 1) < self.config.civilization.kardashev_stagnation_probability_per_myr * dt_myr:
                # Stagnation - no advancement this timestep
                advancement = 0.0
            else:
                # Normal advancement
                advancement = base_advancement

            civ.kardashev_scale = min(
                civ.kardashev_scale + advancement,
                self.config.civilization.kardashev_max_scale
            )

            # Check self-destruction (now Kardashev-dependent)
            if self.extinction_model.check_self_destruction(
                dt_myr=dt_myr,
                rng=self.rng,
                kardashev_scale=civ.kardashev_scale
            ):
                civ.is_active = False
                civ.death_time_myr = self.current_time_myr
                civ.death_cause = 'self_destruction'
                continue

            # Check age-based death (continuous exponential decay from birth)
            # Survival probability: S(t) = exp(-t/tau) where tau = mean lifetime
            # Death rate: lambda = 1/tau
            # Probability of death in time dt: p = 1 - exp(-lambda * dt)
            tau = self.config.civilization.mean_civilization_lifetime_myr
            p_death = 1.0 - np.exp(-dt_myr / tau)

            if self.rng.uniform(0, 1) < p_death:
                civ.is_active = False
                civ.death_time_myr = self.current_time_myr
                civ.death_cause = 'old_age'
                continue

            # Expansion (simplified - will be enhanced with proper light travel time)
            if self.config.civilization.expansion_enabled:
                self._attempt_expansion(civ)

    def _attempt_expansion(self, civ: CivilizationState) -> None:
        """
        Self-replicating probe expansion with branching tree model.

        Implements:
        - Minimum Kardashev threshold (0.85) to start expansion
        - Probe characteristics locked at launch based on tech level
        - Branching tree expansion (not wavefront)
        - Metallicity-based targeting (probes need resources, not habitable planets)
        - Preferential targeting of habitable worlds (for potential contact)
        - Per-hop range targeting (nearest uncolonized metal-rich stars)
        - Replication delays at each destination
        """
        # Cap total colonies to prevent runaway
        if len(civ.colonized_stars) >= 1000:
            return

        # Check if civilization can start expansion program
        if not civ.expansion_program_started:
            if civ.kardashev_scale >= MIN_KARDASHEV_FOR_EXPANSION:
                # Lock in probe design parameters at current tech level
                civ.expansion_program_started = True
                civ.expansion_start_kardashev = civ.kardashev_scale
                civ.probe_velocity_c = probe_velocity_from_kardashev(civ.kardashev_scale)
                civ.probe_per_hop_range_pc = per_hop_range_from_kardashev(civ.kardashev_scale)
                civ.probe_offspring_count = offspring_count(civ.kardashev_scale)
                civ.probe_replication_delay_yr = replication_delay_years(civ.kardashev_scale)

                # Use config metallicity thresholds (configurable per scenario)
                civ.probe_min_metallicity = min_metallicity_for_replication(
                    civ.kardashev_scale,
                    threshold_k085=self.config.civilization.metallicity_threshold_k085,
                    threshold_k095=self.config.civilization.metallicity_threshold_k095,
                    threshold_k120=self.config.civilization.metallicity_threshold_k120
                )

                # Store sensor range for mid-flight course corrections
                civ.probe_sensor_range_pc = self.config.civilization.probe_sensor_range_pc

                # Launch initial wave from home world
                self._launch_initial_probes(civ)
            return

        # Process existing probes
        for probe in civ.active_probes:
            # Mid-flight sensor-based course correction (if enabled)
            if (not probe.has_arrived and
                self.config.civilization.enable_mid_flight_retargeting and
                civ.probe_sensor_range_pc is not None):
                self._check_sensor_retargeting(civ, probe)

            # Check if probe has arrived
            if not probe.has_arrived and probe.arrival_time_myr <= self.current_time_myr:
                probe.has_arrived = True
                probe.replication_complete_time_myr = (
                    self.current_time_myr + probe.replication_delay_yr / 1e6
                )

                # Mark target as colonized
                if probe.target_star_idx not in civ.colonized_stars:
                    civ.colonized_stars.append(probe.target_star_idx)
                    civ.colony_arrival_times[probe.target_star_idx] = probe.arrival_time_myr
                    self._colonized_mask[probe.target_star_idx] = True

            # Check if replication is complete
            if (probe.has_arrived and not probe.has_replicated and
                probe.replication_complete_time_myr <= self.current_time_myr):
                probe.has_replicated = True

                # Launch offspring probes
                self._launch_offspring_probes(civ, probe)

    def _launch_initial_probes(self, civ: CivilizationState) -> None:
        """Launch initial wave of probes from home world."""
        home_idx = civ.parent_star_idx
        home_pos = self.galaxy.positions[home_idx]

        # Find nearest uncolonized stars with sufficient metallicity
        targets = self._find_nearest_targets(
            source_pos=home_pos,
            max_range_pc=civ.probe_per_hop_range_pc,
            max_targets=civ.probe_offspring_count,
            colonized_set=set(civ.colonized_stars),
            exclude_idx=home_idx,
            min_metallicity=civ.probe_min_metallicity
        )

        # Launch probes
        for target_idx in targets:
            target_pos = self.galaxy.positions[target_idx]
            distance_kpc = np.linalg.norm(target_pos - home_pos)
            distance_pc = distance_kpc * 1000.0

            # Calculate travel time
            travel_time_yr = distance_pc / (civ.probe_velocity_c * C_PC_YR)
            arrival_time_myr = self.current_time_myr + travel_time_yr / 1e6

            # Create probe
            probe = ProbeState(
                probe_id=self.next_probe_id,
                parent_probe_id=None,  # Launched from home world
                generation=0,
                launch_star_idx=home_idx,
                target_star_idx=target_idx,
                launch_time_myr=self.current_time_myr,
                arrival_time_myr=arrival_time_myr,
                velocity_c=civ.probe_velocity_c,
                per_hop_range_pc=civ.probe_per_hop_range_pc,
                offspring_count=civ.probe_offspring_count,
                replication_delay_yr=civ.probe_replication_delay_yr
            )
            self.next_probe_id += 1
            civ.active_probes.append(probe)

    def _launch_offspring_probes(self, civ: CivilizationState, parent_probe: ProbeState) -> None:
        """Launch offspring probes from arrived parent probe."""
        source_idx = parent_probe.target_star_idx
        source_pos = self.galaxy.positions[source_idx]

        # Find nearest uncolonized stars with sufficient metallicity
        targets = self._find_nearest_targets(
            source_pos=source_pos,
            max_range_pc=civ.probe_per_hop_range_pc,
            max_targets=civ.probe_offspring_count,
            colonized_set=set(civ.colonized_stars),
            exclude_idx=source_idx,
            min_metallicity=civ.probe_min_metallicity
        )

        # Launch offspring probes
        for target_idx in targets:
            target_pos = self.galaxy.positions[target_idx]
            distance_kpc = np.linalg.norm(target_pos - source_pos)
            distance_pc = distance_kpc * 1000.0

            # Calculate travel time
            travel_time_yr = distance_pc / (civ.probe_velocity_c * C_PC_YR)
            arrival_time_myr = self.current_time_myr + travel_time_yr / 1e6

            # Create offspring probe
            probe = ProbeState(
                probe_id=self.next_probe_id,
                parent_probe_id=parent_probe.probe_id,
                generation=parent_probe.generation + 1,
                launch_star_idx=source_idx,
                target_star_idx=target_idx,
                launch_time_myr=self.current_time_myr,
                arrival_time_myr=arrival_time_myr,
                velocity_c=civ.probe_velocity_c,
                per_hop_range_pc=civ.probe_per_hop_range_pc,
                offspring_count=civ.probe_offspring_count,
                replication_delay_yr=civ.probe_replication_delay_yr
            )
            self.next_probe_id += 1
            civ.active_probes.append(probe)

    def _find_nearest_targets(self, source_pos: np.ndarray, max_range_pc: float,
                              max_targets: int, colonized_set: Set[int],
                              exclude_idx: int, min_metallicity: float) -> List[int]:
        """
        Find nearest uncolonized stars with sufficient metallicity for replication.

        Probes target any star with enough metals to extract resources and replicate.
        Habitable stars are preferred (potential for life contact), but probes will
        settle for any metal-rich system to continue expansion.

        Args:
            source_pos: Source position (kpc)
            max_range_pc: Maximum targeting range (parsecs)
            max_targets: Maximum number of targets to return
            colonized_set: Set of already-colonized star indices
            exclude_idx: Source star index to exclude
            min_metallicity: Minimum [Fe/H] metallicity for replication

        Returns:
            List of target star indices (habitable preferred, then metal-rich)
        """
        # Calculate distances to all stars
        distances_kpc = np.linalg.norm(self.galaxy.positions - source_pos, axis=1)
        distances_pc = distances_kpc * 1000.0

        # Filter: sufficient metallicity, within range, uncolonized, not source
        metallicity_mask = self.galaxy.metallicities >= min_metallicity
        range_mask = distances_pc <= max_range_pc
        not_colonized = ~np.isin(np.arange(len(self.galaxy.positions)), list(colonized_set))
        not_source = np.arange(len(self.galaxy.positions)) != exclude_idx

        # Base candidates: any star meeting resource requirements
        candidate_mask = metallicity_mask & range_mask & not_colonized & not_source
        candidate_indices = np.where(candidate_mask)[0]

        if len(candidate_indices) == 0:
            return []

        # Split into habitable vs resource-only targets
        habitable_mask = self.galaxy.stellar_types == 1
        habitable_candidates = candidate_indices[habitable_mask[candidate_indices]]
        resource_candidates = candidate_indices[~habitable_mask[candidate_indices]]

        # Sort each group by distance
        targets = []

        # Prefer habitable planets (potential for life contact)
        if len(habitable_candidates) > 0:
            hab_distances = distances_pc[habitable_candidates]
            hab_sorted = habitable_candidates[np.argsort(hab_distances)]
            targets.extend(hab_sorted[:max_targets].tolist())

        # Fill remaining quota with nearest resource-rich systems
        remaining = max_targets - len(targets)
        if remaining > 0 and len(resource_candidates) > 0:
            res_distances = distances_pc[resource_candidates]
            res_sorted = resource_candidates[np.argsort(res_distances)]
            targets.extend(res_sorted[:remaining].tolist())

        return targets

    def _check_sensor_retargeting(self, civ: CivilizationState, probe: 'ProbeState') -> None:
        """
        Check if probe sensors detect a more favorable target and adjust course.

        Probes can scan within sensor range during flight and retarget to:
        - Habitable planets (always preferred)
        - Higher metallicity systems (better resources)

        Only retargets once per probe to avoid computational overhead.

        Args:
            civ: Civilization state
            probe: Probe in transit
        """
        # Only retarget once to avoid repeated course changes
        if hasattr(probe, '_has_retargeted') and probe._has_retargeted:
            return

        # Calculate probe's current position along trajectory
        elapsed_time_myr = self.current_time_myr - probe.launch_time_myr
        total_time_myr = probe.arrival_time_myr - probe.launch_time_myr

        if total_time_myr <= 0:
            return  # Avoid division by zero

        fraction_complete = min(elapsed_time_myr / total_time_myr, 1.0)

        # Interpolate position
        source_idx = probe.source_star_idx if hasattr(probe, 'source_star_idx') else civ.parent_star_idx
        source_pos = self.galaxy.positions[source_idx]
        target_pos = self.galaxy.positions[probe.target_star_idx]
        current_pos = source_pos + fraction_complete * (target_pos - source_pos)

        # Scan for better targets within sensor range
        distances_kpc = np.linalg.norm(self.galaxy.positions - current_pos, axis=1)
        distances_pc = distances_kpc * 1000.0

        # Filter: within sensor range, meets metallicity, uncolonized
        sensor_mask = distances_pc <= civ.probe_sensor_range_pc
        metallicity_mask = self.galaxy.metallicities >= civ.probe_min_metallicity
        not_colonized = ~np.isin(np.arange(len(self.galaxy.positions)), list(civ.colonized_stars))
        not_current_target = np.arange(len(self.galaxy.positions)) != probe.target_star_idx

        candidate_mask = sensor_mask & metallicity_mask & not_colonized & not_current_target
        candidate_indices = np.where(candidate_mask)[0]

        if len(candidate_indices) == 0:
            return

        # Prioritize habitable planets
        habitable_mask = self.galaxy.stellar_types == 1
        habitable_candidates = candidate_indices[habitable_mask[candidate_indices]]

        current_target_habitable = self.galaxy.stellar_types[probe.target_star_idx] == 1
        current_target_metallicity = self.galaxy.metallicities[probe.target_star_idx]

        # Retarget if we find a habitable planet and current target isn't habitable
        if len(habitable_candidates) > 0 and not current_target_habitable:
            # Choose nearest habitable candidate
            hab_distances = distances_pc[habitable_candidates]
            nearest_idx = habitable_candidates[np.argmin(hab_distances)]

            # Retarget probe
            self._retarget_probe(probe, nearest_idx, current_pos)
            probe._has_retargeted = True  # type: ignore
            return

        # Otherwise, check for significantly better metallicity (at least 0.2 dex improvement)
        candidate_metallicities = self.galaxy.metallicities[candidate_indices]
        metallicity_improvements = candidate_metallicities - current_target_metallicity

        better_candidates = candidate_indices[metallicity_improvements >= 0.2]
        if len(better_candidates) > 0:
            # Choose nearest candidate with better metallicity
            better_distances = distances_pc[better_candidates]
            nearest_idx = better_candidates[np.argmin(better_distances)]

            # Retarget probe
            self._retarget_probe(probe, nearest_idx, current_pos)
            probe._has_retargeted = True  # type: ignore

    def _retarget_probe(self, probe: 'ProbeState', new_target_idx: int, current_pos: np.ndarray) -> None:
        """
        Retarget probe to new destination from current position.

        Args:
            probe: Probe to retarget
            new_target_idx: New target star index
            current_pos: Probe's current position (kpc)
        """
        new_target_pos = self.galaxy.positions[new_target_idx]
        distance_kpc = np.linalg.norm(new_target_pos - current_pos)
        distance_pc = distance_kpc * 1000.0

        # Calculate new travel time from current position
        travel_time_yr = distance_pc / (probe.velocity_c * C_PC_YR)
        travel_time_myr = travel_time_yr / 1e6

        # Update probe parameters
        probe.target_star_idx = new_target_idx
        probe.arrival_time_myr = self.current_time_myr + travel_time_myr
        # Note: launch_time_myr stays the same (original launch), but arrival time updated

    def _apply_hazards(self) -> None:
        """
        Apply astrophysical hazards (supernovae, GRBs) to civilizations.

        Checks each active civilization for destruction by nearby supernovae
        or gamma-ray bursts. Now accounts for metallicity-dependent rates,
        component-dependent supernova rates, and local density effects.
        """
        # Initialize hazard evaluator on first call
        if not hasattr(self, 'hazard_evaluator'):
            from ..astrophysics.hazards import HazardEvaluator
            self.hazard_evaluator = HazardEvaluator(self.config.astrophysics)

        dt_myr = self.config.simulation.time_step_myr

        # Check each civilization for hazard destruction
        for civ in self.civilizations:
            if not civ.is_active:
                continue

            # Check home world for hazards
            civ_pos = self.galaxy.positions[civ.parent_star_idx]

            # Check supernova hazard (now returns tuple with info dict)
            destroyed_by_sn, sn_info = self.hazard_evaluator.evaluate_supernova_hazard(
                civilization_position=civ_pos,
                stellar_positions=self.galaxy.positions,
                stellar_masses=self.galaxy.masses,
                stellar_ages=self.galaxy.ages,
                component_types=self.galaxy.component_type,
                dt_myr=dt_myr,
                rng=self.rng,
                spatial_index=self._spatial_index if hasattr(self, '_spatial_index') else None
            )

            # Store hazard statistics on civilization object for analysis
            if not hasattr(civ, 'hazard_stats'):
                civ.hazard_stats = {}
            civ.hazard_stats.update(sn_info)

            if destroyed_by_sn:
                civ.is_active = False
                civ.death_time_myr = self.current_time_myr
                civ.death_cause = 'supernova'

                # Record hazard event for visualization
                self.hazard_events.append(HazardEvent(
                    time_myr=self.current_time_myr,
                    event_type='supernova',
                    position=civ_pos.copy(),  # Approximate location
                    energy=1e51,  # Typical supernova energy in ergs
                    sterilization_radius_pc=sn_info.get('sn_distance_pc', self.config.astrophysics.sn_sterilization_range_pc),
                    affected_civ_ids=[civ.civ_id]
                ))
                continue

            # Check GRB hazard (now returns tuple with info dict)
            destroyed_by_grb, grb_info = self.hazard_evaluator.evaluate_grb_hazard(
                civilization_position=civ_pos,
                stellar_positions=self.galaxy.positions,
                stellar_masses=self.galaxy.masses,
                stellar_ages=self.galaxy.ages,
                metallicities=self.galaxy.metallicities,
                dt_myr=dt_myr,
                rng=self.rng,
                spatial_index=self._spatial_index if hasattr(self, '_spatial_index') else None
            )

            # Store GRB statistics
            civ.hazard_stats.update(grb_info)

            if destroyed_by_grb:
                civ.is_active = False
                civ.death_time_myr = self.current_time_myr
                civ.death_cause = 'grb'

                # Record hazard event for visualization
                self.hazard_events.append(HazardEvent(
                    time_myr=self.current_time_myr,
                    event_type='grb',
                    position=civ_pos.copy(),  # Approximate location
                    energy=1e54,  # Typical GRB energy in ergs
                    sterilization_radius_pc=grb_info.get('grb_distance_kpc', 1.0) * 1000.0,  # Convert kpc to pc
                    affected_civ_ids=[civ.civ_id]
                ))

    def _save_snapshot(self) -> None:
        """Save current simulation state as snapshot."""
        active_civs = sum(c.is_active for c in self.civilizations)

        snapshot = SimulationSnapshot(
            time_myr=self.current_time_myr,
            active_civilizations=active_civs,
            total_civilizations_ever=self.next_civ_id,
            colonized_systems=sum(len(c.colonized_stars) for c in self.civilizations if c.is_active),
            civilization_states=[c for c in self.civilizations],
            stellar_positions=self.galaxy.positions.copy() if self.galaxy.positions is not None else np.array([])
        )

        self.snapshots.append(snapshot)

    def get_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics."""
        active_civs = sum(c.is_active for c in self.civilizations)

        return {
            'total_civilizations': self.next_civ_id,
            'active_civilizations': active_civs,
            'extinct_civilizations': self.next_civ_id - active_civs,
            'total_colonized_systems': sum(len(c.colonized_stars) for c in self.civilizations),
            'current_time_gyr': self.current_time_myr / 1000.0,
            'snapshots_saved': len(self.snapshots)
        }
