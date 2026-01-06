"""Main simulation engine for galactic civilization modeling."""

import heapq
import time
import numpy as np
from typing import Optional, Dict, List, Any, Set, Tuple
from dataclasses import dataclass, field
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

from ..config.parameters import SimulationConfig
from ..utils.progress import create_progress_tracker, ProgressMetrics
from ..utils.parallel import (
    ThreadLocalProbeBuffer,
    compute_light_travel_distance,
    find_causal_groups_simple,
    find_causal_groups_with_colonies,
    should_use_parallelization
)
from ..galaxy.structure import GalaxyModel
from ..galaxy.star_formation import StarFormationHistory, InitialMassFunction
from ..civilization.probe_design import (
    probe_velocity_from_kardashev,
    per_hop_range_from_kardashev,
    offspring_count,
    replication_delay_years,
    min_metallicity_for_replication,
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
    colonized_stars: Set[int] = field(default_factory=set)  # Indices of colonized stars (PRIORITY 1B: Set for O(1) lookups)
    colony_arrival_times: Dict[int, float] = field(default_factory=dict)  # star_idx -> arrival_time_myr
    kardashev_scale: float = 0.7  # Technological level: 0.7 (modern Earth) to 3.0 (galaxy-scale)
    kardashev_advancement_rate: float = 0.01  # Individual advancement rate (varies per civilization)
    is_active: bool = True
    death_time_myr: Optional[float] = None
    death_cause: Optional[str] = None  # 'extinction_event', 'self_destruction', 'old_age', 'supernova', 'grb', 'colonial_war'

    # Home world destruction tracking (for distributed resilience)
    home_world_destroyed: bool = False
    home_world_destruction_time_myr: Optional[float] = None

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
    archived_probes: List['ProbeState'] = field(default_factory=list)  # Completed probes


@dataclass
class ProbeSnapshot:
    """Snapshot of a single probe's state for visualization."""

    probe_id: int
    civ_id: int
    launch_star_idx: int
    target_star_idx: int
    current_position: np.ndarray  # Interpolated 3D position [x, y, z] in kpc
    launch_time_myr: float
    arrival_time_myr: float
    progress_fraction: float  # 0.0 (just launched) to 1.0 (arrived)
    velocity_c: float
    generation: int


@dataclass
class SimulationSnapshot:
    """Snapshot of simulation state at a given time."""

    time_myr: float
    active_civilizations: int
    total_civilizations_ever: int
    colonized_systems: int
    civilization_states: List[CivilizationState]
    stellar_positions: np.ndarray  # For visualization
    active_probes_in_flight: List[ProbeSnapshot] = field(default_factory=list)
    total_active_probes: int = 0


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

        # PRIORITY 2: Event queue for probe arrivals/replications (10-50x speedup)
        # Min-heap: (event_time_myr, event_type, civ_id, probe_id)
        self.event_queue: List[Tuple[float, str, int, int]] = []

        # Progress tracking
        self._progress_tracker = None
        self._step_count = 0
        self._last_update_time = 0.0
        self._last_progress_pct = 0.0
        self._current_dt_myr = 0.0
        self._start_time = 0.0

        # Probe archival tracking
        self._last_archive_time_myr = 0.0
        self._archive_interval_myr = 1.0  # Archive every 1 Myr

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
        max_age_gyr = self.config.galaxy.max_stellar_age_gyr
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
        # Stars within configured mass range are considered potentially habitable
        self.galaxy.stellar_types = (
            (self.galaxy.masses >= self.config.galaxy.habitable_mass_min_msun) &
            (self.galaxy.masses <= self.config.galaxy.habitable_mass_max_msun)
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

    def _compute_next_timestep(self) -> float:
        """
        Compute adaptive timestep based on upcoming probe events and activity.

        Returns:
            Next timestep in Myr
        """
        cfg = self.config.simulation

        # Check for imminent probe events
        if self.event_queue:
            next_event_time = self.event_queue[0][0]  # Peek min-heap
            time_to_event = next_event_time - self.current_time_myr

            # Step to event if within adaptive window and positive
            if time_to_event > 0 and time_to_event <= cfg.max_adaptive_step_myr:
                # Clamp to min timestep for stability
                return max(time_to_event, cfg.min_timestep_myr)

        # No imminent events - use activity-based logic
        active_civs = sum(1 for c in self.civilizations if c.is_active)

        if active_civs > 0:
            # Active civilizations - use medium timestep
            return cfg.medium_timestep_myr
        else:
            # No active civilizations - use max timestep
            return cfg.max_timestep_myr

    def _step(self, dt_myr: Optional[float] = None) -> float:
        """
        Execute a single simulation timestep.

        Args:
            dt_myr: Timestep size in Myr. If None, uses config default.

        Returns:
            Actual timestep used (for adaptive stepping)

        This method can be overridden by subclasses for custom stepping logic.
        """
        if dt_myr is None:
            dt_myr = self.config.simulation.time_step_myr

        # Store for methods that need it
        self._current_dt_myr = dt_myr

        # Evolve galaxy (stellar motion)
        self.galaxy.evolve_positions(
            dt_myr,
            use_numba=self.config.simulation.use_numba,
            enable_motion=self.config.simulation.enable_stellar_motion
        )

        # Check for new civilization emergence
        self._check_civilization_emergence()

        # Evolve existing civilizations
        self._evolve_civilizations()

        # PRIORITY 2: Process probe events (arrival, replication) from event queue
        self._process_probe_events()

        # Archive completed probes periodically to prevent exponential memory/performance issues
        if (self.current_time_myr - self._last_archive_time_myr) >= self._archive_interval_myr:
            self._archive_completed_probes()
            self._last_archive_time_myr = self.current_time_myr

        # Apply astrophysical hazards
        self._apply_hazards()

        # Advance time
        self.current_time_myr += dt_myr

        return dt_myr

    def run(self, verbose: bool = True) -> None:
        """
        Run the main simulation loop with adaptive or fixed time stepping.

        Args:
            verbose: Whether to show progress bar
        """
        if self.galaxy.positions is None:
            self.initialize()

        duration_myr = self.config.simulation.simulation_duration_gyr * 1000
        cfg = self.config.simulation

        # Progress tracking setup
        if verbose:
            self._progress_tracker = create_progress_tracker(
                environment='auto',
                show_iteration_rate=cfg.progress_show_iteration_rate,
                show_probe_count=cfg.progress_show_probe_count
            )
            self._progress_tracker.start(duration_myr)

        self._start_time = time.time()
        self._step_count = 0
        self._last_update_time = self._start_time
        self._last_progress_pct = 0.0

        snapshot_counter = 0
        next_snapshot_time = 0.0

        if cfg.adaptive_timestepping:
            # Adaptive timestep loop
            while self.current_time_myr < duration_myr:
                # Compute adaptive timestep
                dt_myr = self._compute_next_timestep()

                # Don't overshoot simulation end
                dt_myr = min(dt_myr, duration_myr - self.current_time_myr)

                # Store current dt for progress tracking
                self._current_dt_myr = dt_myr

                # Execute step with adaptive dt
                self._step(dt_myr)

                # Save snapshot if needed
                if cfg.save_snapshots:
                    if self.current_time_myr >= next_snapshot_time:
                        self._save_snapshot()
                        next_snapshot_time += cfg.snapshot_interval_myr

                # Update progress tracking
                self._step_count += 1
                if self._should_update_progress(duration_myr):
                    self._update_progress(duration_myr)

        else:
            # Legacy fixed timestep loop
            while self.current_time_myr < duration_myr:
                # Store current dt for progress tracking (fixed timestep)
                self._current_dt_myr = cfg.time_step_myr

                # Execute step with fixed dt
                self._step()

                # Save snapshot if needed
                if cfg.save_snapshots:
                    if self.current_time_myr >= next_snapshot_time:
                        self._save_snapshot()
                        next_snapshot_time += cfg.snapshot_interval_myr

                # Update progress tracking
                self._step_count += 1
                if self._should_update_progress(duration_myr):
                    self._update_progress(duration_myr)

        # Finalize progress tracker
        if verbose and self._progress_tracker:
            self._progress_tracker.finish()

        # Final snapshot
        if cfg.save_snapshots:
            self._save_snapshot()

        print(f"\nSimulation complete!")
        print(f"Total civilizations emerged: {self.next_civ_id}")
        print(f"Active civilizations: {sum(c.is_active for c in self.civilizations)}")

    def _should_update_progress(self, duration_myr: float) -> bool:
        """Check if progress should be updated based on hybrid thresholds."""
        if not self._progress_tracker:
            return False

        cfg = self.config.simulation

        # Time threshold: >= 0.1% simulation time progress
        current_progress_pct = (self.current_time_myr / duration_myr) * 100
        time_delta = current_progress_pct - self._last_progress_pct
        if time_delta >= cfg.progress_update_interval_pct:
            return True

        # Step threshold: >= 10 iterations
        if self._step_count % cfg.progress_update_interval_steps == 0:
            return True

        # Wall-time threshold: >= 0.5 seconds
        current_wall_time = time.time()
        if current_wall_time - self._last_update_time >= cfg.progress_update_interval_seconds:
            return True

        return False

    def _update_progress(self, duration_myr: float) -> None:
        """Collect metrics and update progress display."""
        if not self._progress_tracker:
            return

        # Count active civilizations and probes
        active_civs = sum(1 for c in self.civilizations if c.is_active)
        active_probes = sum(len(c.active_probes) for c in self.civilizations if c.is_active)

        # Create metrics snapshot
        metrics = ProgressMetrics(
            current_time_myr=self.current_time_myr,
            total_time_myr=duration_myr,
            step_count=self._step_count,
            current_dt_myr=self._current_dt_myr,
            active_civs=active_civs,
            active_probes=active_probes,
            event_queue_size=len(self.event_queue),
            wall_time_elapsed=time.time() - self._start_time
        )

        # Update tracker
        self._progress_tracker.update(metrics)

        # Update tracking state
        self._last_progress_pct = metrics.time_pct
        self._last_update_time = time.time()

    def _partition_civilizations_by_causality(self) -> List[List['CivilizationState']]:
        """
        Partition civilizations into causally independent groups.

        Two civilizations are causally connected if:
        1. Distance < c × dt (light can travel between them this timestep), OR
        2. They share colonized systems (if enabled in config)

        Groups are processed in parallel since they cannot interact within this timestep.

        Returns:
            List of civilization groups, each group can be processed independently
        """
        cfg = self.config.simulation

        # Get active civilizations
        active_civs = [c for c in self.civilizations if c.is_active]

        if len(active_civs) == 0:
            return []

        if len(active_civs) == 1:
            return [active_civs]

        # Compute light-travel distance for current timestep
        max_causal_distance_kpc = compute_light_travel_distance(self._current_dt_myr)

        # Extract civilization positions
        civ_positions = np.array([
            self.galaxy.positions[c.parent_star_idx] for c in active_civs
        ])

        civ_ids = [c.civ_id for c in active_civs]

        # Partition based on causality
        if cfg.parallel_check_shared_colonies:
            # Include colony overlap in causality check
            colonized_systems = [c.colonized_stars for c in active_civs]
            group_indices = find_causal_groups_with_colonies(
                civ_positions,
                civ_ids,
                colonized_systems,
                max_causal_distance_kpc
            )
        else:
            # Simple distance-based partitioning
            group_indices = find_causal_groups_simple(
                civ_positions,
                civ_ids,
                max_causal_distance_kpc
            )

        # Convert indices to civilization objects
        groups = []
        for group_idx_list in group_indices:
            group_civs = [active_civs[idx] for idx in group_idx_list]
            groups.append(group_civs)

        return groups

    def _check_civilization_emergence(self) -> None:
        """Check for new civilization emergence based on Drake equation."""
        if self.habitable_star_indices is None:
            return

        dt_myr = self._current_dt_myr
        params = self.config.civilization

        # Check each habitable star
        # Only consider stars old enough to have developed life
        old_enough = self.galaxy.ages[self.habitable_star_indices] > self.config.civilization.min_stellar_age_for_life_gyr
        not_colonized = ~self._colonized_mask[self.habitable_star_indices]

        eligible_mask = old_enough & not_colonized
        eligible_stars = self.habitable_star_indices[eligible_mask]

        if len(eligible_stars) == 0:
            return

        # PRIORITY 1C OPTIMIZATION: Vectorize emergence probability calculation
        # Drake equation factors (scalar constants)
        f_life = params.fraction_develop_life
        f_intel = params.fraction_develop_intelligence
        f_tech = params.fraction_develop_technology
        n_habitable = params.avg_habitable_planets_per_system
        f_base = params.fraction_stars_with_planets

        # Get all metallicities at once (vectorized)
        metallicities = self.galaxy.metallicities[eligible_stars]

        # Compute metallicity-dependent planet fraction (vectorized)
        if self.config.galaxy.use_metallicity_gradient:
            # Metallicity effect: factor of ~3 per 0.5 dex
            # At solar metallicity (0.0): f_planets = f_base
            # At +0.3 dex (bulge): f_planets = 2 * f_base
            # At -0.5 dex (outer disk): f_planets = 0.3 * f_base
            f_planets_array = f_base * np.power(10.0, metallicities)
            f_planets_array = np.clip(f_planets_array, 0.01, 1.0)  # Physical bounds
        else:
            f_planets_array = np.full(len(eligible_stars), f_base)

        # Combined probability per Gyr (vectorized)
        p_emergence_per_gyr = f_planets_array * n_habitable * f_life * f_intel * f_tech

        # Scale to time step (vectorized)
        p_emergence_array = p_emergence_per_gyr * dt_myr / 1000.0

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
                colonized_stars={star_idx_int},  # PRIORITY 1B: Set instead of list
                colony_arrival_times={star_idx_int: self.current_time_myr},  # Home world "arrived" at birth
                kardashev_scale=initial_kardashev,
                kardashev_advancement_rate=advancement_rate
            )
            self.civilizations.append(new_civ)
            self._colonized_mask[star_idx_int] = True  # Mark as colonized
            self.next_civ_id += 1

    def _get_mature_colonies(self, civ: CivilizationState) -> int:
        """
        Count colonies mature enough to contribute to resilience.

        Colonies need time to become self-sufficient before providing
        redundancy against extinction events.

        Args:
            civ: Civilization to check

        Returns:
            Number of mature colonies (age >= colony_maturation_time_myr)
        """
        maturation_threshold = self.config.civilization.colony_maturation_time_myr
        mature_count = 0

        for star_idx, arrival_time in civ.colony_arrival_times.items():
            age = self.current_time_myr - arrival_time
            if age >= maturation_threshold:
                mature_count += 1

        return mature_count

    def _calculate_colonial_war_risk(
        self,
        kardashev_scale: float,
        num_mature_colonies: int,
        dt_myr: float
    ) -> float:
        """
        Calculate colonial war extinction probability.

        Risk increases with:
        - Kardashev scale above threshold (more dangerous weapons)
        - Number of colonies (more factions, coordination breakdown)

        Only applies when colonies are numerous and technologically advanced.

        Args:
            kardashev_scale: Current technological level
            num_mature_colonies: Number of mature colonies
            dt_myr: Time step in Myr

        Returns:
            Probability of extinction from colonial war this timestep
        """
        cfg = self.config.civilization

        # No risk below thresholds
        if num_mature_colonies < cfg.colonial_war_colony_threshold:
            return 0.0

        if kardashev_scale < cfg.colonial_war_kardashev_threshold:
            return 0.0

        # Hazard rate increases with K-scale and colonies
        k_factor = (kardashev_scale - cfg.colonial_war_kardashev_threshold)
        colony_factor = np.log(num_mature_colonies / cfg.colonial_war_colony_threshold)

        lambda_war = cfg.colonial_war_amplitude * k_factor * colony_factor

        # Convert hazard rate to probability
        p_war = 1.0 - np.exp(-lambda_war * dt_myr)

        return p_war

    def _evolve_civilizations(self) -> None:
        """
        Evolve existing civilizations - dispatcher for parallel vs sequential.

        Chooses between parallel and sequential processing based on:
        - Config setting (enable_within_sim_parallel)
        - Number of active civilizations (must exceed threshold)
        - Causality grouping (must have multiple independent groups)
        """
        cfg = self.config.simulation

        # Get active civilizations count
        active_civs = [c for c in self.civilizations if c.is_active]
        n_active = len(active_civs)

        # Decide whether to use parallelization
        if not cfg.enable_within_sim_parallel or n_active < cfg.parallel_min_civs_threshold:
            # Sequential processing
            return self._evolve_civilizations_sequential()

        # Partition by causality
        groups = self._partition_civilizations_by_causality()

        # Check if parallelization is beneficial
        if not should_use_parallelization(n_active, cfg.parallel_min_civs_threshold, len(groups), cfg.parallel_worker_threads):
            # Fall back to sequential
            return self._evolve_civilizations_sequential()

        # Parallel processing
        return self._evolve_civilizations_parallel(groups)

    def _evolve_civilizations_sequential(self) -> None:
        """Evolve existing civilizations sequentially (original implementation)."""
        dt_myr = self._current_dt_myr

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

            # Check self-destruction with distributed resilience and colonial war
            # Base self-destruction from crises (nuclear, AI, etc.)
            p_single_crisis = self.extinction_model.check_self_destruction(
                dt_myr=dt_myr,
                rng=self.rng,
                kardashev_scale=civ.kardashev_scale
            )

            # Get mature colonies for resilience calculation
            num_mature = self._get_mature_colonies(civ)

            # Distributed resilience: crisis must affect all colonies
            # Each colony independently survives with probability (1 - p)
            if num_mature > 1:
                p_crisis_total = p_single_crisis ** num_mature
            else:
                p_crisis_total = p_single_crisis

            # Colonial war risk (increases with colonies & K-scale)
            p_colonial_war = self._calculate_colonial_war_risk(
                civ.kardashev_scale, num_mature, dt_myr
            )

            # Combined extinction probability: either crisis OR war
            # P(A or B) = 1 - (1-P(A))(1-P(B))
            p_total_extinction = 1.0 - (1.0 - p_crisis_total) * (1.0 - p_colonial_war)

            if self.rng.uniform(0, 1) < p_total_extinction:
                civ.is_active = False
                civ.death_time_myr = self.current_time_myr
                # Assign cause based on which was more likely
                civ.death_cause = 'colonial_war' if p_colonial_war > p_crisis_total else 'self_destruction'
                continue

            # Check age-based death with colonization bonus and distributed resilience
            # Calculate effective lifetime with logarithmic colonization bonus
            colonization_bonus = (
                self.config.civilization.colonization_lifetime_bonus_myr *
                np.log(1 + num_mature)
            )
            effective_lifetime = (
                self.config.civilization.mean_civilization_lifetime_myr +
                colonization_bonus
            )

            # Apply home world fragility penalty if applicable
            if civ.home_world_destroyed:
                time_since_loss = self.current_time_myr - civ.home_world_destruction_time_myr
                if time_since_loss < self.config.civilization.home_world_fragility_period_myr:
                    # Temporary fragility - reduced lifetime during reorganization
                    effective_lifetime *= self.config.civilization.home_world_fragility_factor

            # Old-age death check with effective lifetime
            age = self.current_time_myr - civ.birth_time_myr
            if age >= effective_lifetime:
                # Exponential decay: lambda = 1/tau
                decay_rate = 1.0 / effective_lifetime
                p_death_single = 1.0 - np.exp(-decay_rate * dt_myr)

                # Distributed model: each mature colony rolls independently
                # Civilization dies only if ALL colonies die
                if num_mature > 1:
                    p_all_die = p_death_single ** num_mature
                else:
                    p_all_die = p_death_single

                if self.rng.uniform(0, 1) < p_all_die:
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
        if len(civ.colonized_stars) >= self.config.civilization.max_colonies_per_civilization:
            return

        # Check if civilization can start expansion program
        if not civ.expansion_program_started:
            if civ.kardashev_scale >= self.config.civilization.min_kardashev_for_expansion:
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

        # PRIORITY 2: Probe events are now handled by event queue (see _process_probe_events)
        # Old polling loop removed for 10-50x speedup

    def _process_probe_events(self) -> None:
        """
        PRIORITY 2: Process probe arrival and replication events from event queue.

        Replaces O(N_probes) polling loop with O(log N) event-driven processing.
        Expected speedup: 10-50x for expansion-heavy scenarios.
        """
        # Process all events that should occur at or before current time
        while self.event_queue and self.event_queue[0][0] <= self.current_time_myr:
            event_time, event_type, civ_id, probe_id = heapq.heappop(self.event_queue)

            # Find civilization and probe
            civ = None
            for c in self.civilizations:
                if c.civ_id == civ_id:
                    civ = c
                    break

            if civ is None or not civ.is_active:
                continue  # Civilization extinct, ignore event

            # Search for probe in both active and archived lists
            # (probe may have been archived on arrival but still needs replication processing)
            probe = None
            for p in civ.active_probes:
                if p.probe_id == probe_id:
                    probe = p
                    break

            if probe is None:
                for p in civ.archived_probes:
                    if p.probe_id == probe_id:
                        probe = p
                        break

            if probe is None:
                continue  # Probe not found (shouldn't happen)

            if event_type == 'probe_arrival':
                self._handle_probe_arrival(civ, probe)
            elif event_type == 'replication_complete':
                self._handle_replication_complete(civ, probe)

    def _archive_completed_probes(self) -> None:
        """
        Archive completed probes to prevent memory/performance issues.

        A probe is considered "completed" when:
        - It has arrived at target (has_arrived = True)
        - It has finished replication (has_replicated = True)
        - It is no longer needed for active simulation

        This prevents the active_probes list from growing exponentially.
        """
        for civ in self.civilizations:
            if not civ.is_active:
                continue

            # Separate active from completed probes
            still_active = []
            newly_archived = []

            for probe in civ.active_probes:
                # Probe is completed if it has arrived AND replicated
                if probe.has_arrived and probe.has_replicated:
                    newly_archived.append(probe)
                else:
                    still_active.append(probe)

            # Update lists
            civ.active_probes = still_active
            civ.archived_probes.extend(newly_archived)

    def _handle_probe_arrival(self, civ: CivilizationState, probe: ProbeState) -> None:
        """Handle probe arrival at target star."""
        if probe.has_arrived:
            return  # Already processed

        probe.has_arrived = True
        probe.replication_complete_time_myr = (
            self.current_time_myr + probe.replication_delay_yr / 1e6
        )

        # Mark target as colonized
        if probe.target_star_idx not in civ.colonized_stars:
            civ.colonized_stars.add(probe.target_star_idx)
            civ.colony_arrival_times[probe.target_star_idx] = probe.arrival_time_myr
            self._colonized_mask[probe.target_star_idx] = True

        # Schedule replication complete event
        heapq.heappush(self.event_queue, (
            probe.replication_complete_time_myr,
            'replication_complete',
            civ.civ_id,
            probe.probe_id
        ))

        # Archive immediately on arrival - probe is now stationary, waiting to replicate
        # We keep probe data for replication event, but remove from active iteration
        # This prevents active_probes from accumulating arrived-but-not-yet-replicated probes
        if probe in civ.active_probes:
            civ.active_probes.remove(probe)
            civ.archived_probes.append(probe)

    def _evolve_civilizations_parallel(self, groups: List[List['CivilizationState']]) -> None:
        """
        Evolve civilizations in parallel using causality-preserving groups.

        Each group contains civilizations that are causally independent from other groups,
        allowing safe parallel processing without race conditions.

        Args:
            groups: List of civilization groups from causality partitioning
        """
        cfg = self.config.simulation

        # Process groups in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=cfg.parallel_worker_threads) as executor:
            # Submit all groups for parallel processing
            futures = [
                executor.submit(self._evolve_civilization_group, group)
                for group in groups
            ]

            # Collect results (thread-local buffers)
            buffers = [future.result() for future in futures]

        # Merge thread-local buffers back into shared state (single-threaded)
        self._merge_probe_buffers(buffers)

    def _evolve_civilization_group(self, group: List['CivilizationState']) -> ThreadLocalProbeBuffer:
        """
        Evolve a group of causally-independent civilizations.

        This method is called from worker threads, so it must not modify shared state directly.
        Instead, it collects changes in a thread-local buffer that is merged later.

        Args:
            group: List of civilizations to process

        Returns:
            ThreadLocalProbeBuffer with collected probes and events
        """
        buffer = ThreadLocalProbeBuffer()
        dt_myr = self._current_dt_myr

        for civ in group:
            # Technological advancement
            self._advance_civilization_tech(civ, dt_myr)

            # Check extinction (updates civ state directly - safe since civs in group are independent)
            extinct = self._check_civilization_extinction(civ, dt_myr)
            if extinct:
                buffer.extinction_updates.append((
                    civ.civ_id,
                    False,  # is_active
                    self.current_time_myr,  # death_time_myr
                    civ.death_cause
                ))
                continue

            # Expansion - collect probes in buffer instead of modifying shared state
            if self.config.civilization.expansion_enabled:
                self._attempt_expansion_buffered(civ, buffer)

        return buffer

    def _advance_civilization_tech(self, civ: 'CivilizationState', dt_myr: float) -> None:
        """Advance civilization technology (Kardashev scale)."""
        base_advancement = civ.kardashev_advancement_rate * dt_myr

        # Check for technological breakthrough
        p_breakthrough = self.config.civilization.kardashev_breakthrough_probability_per_myr * dt_myr
        if self.rng.uniform(0, 1) < p_breakthrough:
            advancement = base_advancement * self.config.civilization.kardashev_breakthrough_multiplier
        # Check for stagnation
        elif self.rng.uniform(0, 1) < self.config.civilization.kardashev_stagnation_probability_per_myr * dt_myr:
            advancement = 0.0
        else:
            advancement = base_advancement

        civ.kardashev_scale = min(
            civ.kardashev_scale + advancement,
            self.config.civilization.kardashev_max_scale
        )

    def _check_civilization_extinction(self, civ: 'CivilizationState', dt_myr: float) -> bool:
        """
        Check if civilization goes extinct this timestep.

        Returns:
            True if civilization extinct, False otherwise
        """
        # Self-destruction check
        p_single_crisis = self.extinction_model.check_self_destruction(
            dt_myr=dt_myr,
            rng=self.rng,
            kardashev_scale=civ.kardashev_scale
        )

        # Distributed resilience
        num_mature = self._get_mature_colonies(civ)
        if num_mature > 1:
            p_crisis_total = p_single_crisis ** num_mature
        else:
            p_crisis_total = p_single_crisis

        # Colonial war risk
        p_colonial_war = self._calculate_colonial_war_risk(
            civ.kardashev_scale, num_mature, dt_myr
        )

        # Combined extinction probability
        p_total_extinction = 1.0 - (1.0 - p_crisis_total) * (1.0 - p_colonial_war)

        if self.rng.uniform(0, 1) < p_total_extinction:
            civ.is_active = False
            civ.death_time_myr = self.current_time_myr
            civ.death_cause = 'colonial_war' if p_colonial_war > p_crisis_total else 'self_destruction'
            return True

        # Age-based death check
        colonization_bonus = (
            self.config.civilization.colonization_lifetime_bonus_myr *
            np.log(1 + num_mature)
        )
        effective_lifetime = (
            self.config.civilization.mean_civilization_lifetime_myr +
            colonization_bonus
        )

        # Home world fragility penalty
        if civ.home_world_destroyed:
            time_since_loss = self.current_time_myr - civ.home_world_destruction_time_myr
            if time_since_loss < self.config.civilization.home_world_fragility_period_myr:
                effective_lifetime *= self.config.civilization.home_world_fragility_factor

        # Old-age death
        age = self.current_time_myr - civ.birth_time_myr
        if age >= effective_lifetime:
            decay_rate = 1.0 / effective_lifetime
            p_death_single = 1.0 - np.exp(-decay_rate * dt_myr)

            if num_mature > 1:
                p_all_die = p_death_single ** num_mature
            else:
                p_all_die = p_death_single

            if self.rng.uniform(0, 1) < p_all_die:
                civ.is_active = False
                civ.death_time_myr = self.current_time_myr
                civ.death_cause = 'old_age'
                return True

        return False

    def _attempt_expansion_buffered(self, civ: 'CivilizationState', buffer: ThreadLocalProbeBuffer) -> None:
        """
        Attempt expansion using thread-local buffer (parallel-safe version).

        Instead of modifying shared state (event queue, probe lists), this collects
        new probes and events in a thread-local buffer for later merging.

        Args:
            civ: Civilization attempting expansion
            buffer: Thread-local buffer to collect probes/events
        """
        # Check colony cap
        if len(civ.colonized_stars) >= self.config.civilization.max_colonies_per_civilization:
            return

        # Check if can start expansion
        if not civ.expansion_program_started:
            if civ.kardashev_scale >= self.config.civilization.min_kardashev_for_expansion:
                # Lock in probe design
                civ.expansion_program_started = True
                civ.expansion_start_kardashev = civ.kardashev_scale
                civ.probe_velocity_c = probe_velocity_from_kardashev(civ.kardashev_scale)
                civ.probe_per_hop_range_pc = per_hop_range_from_kardashev(civ.kardashev_scale)
                civ.probe_offspring_count = offspring_count(civ.kardashev_scale)
                civ.probe_replication_delay_yr = replication_delay_years(civ.kardashev_scale)
                civ.probe_min_metallicity = min_metallicity_for_replication(
                    civ.kardashev_scale,
                    threshold_k085=self.config.civilization.metallicity_threshold_k085,
                    threshold_k095=self.config.civilization.metallicity_threshold_k095,
                    threshold_k120=self.config.civilization.metallicity_threshold_k120
                )
                civ.probe_sensor_range_pc = self.config.civilization.probe_sensor_range_pc

                # Launch initial probes from home world - collect in buffer
                self._launch_initial_probes_buffered(civ, buffer)

    def _launch_initial_probes_buffered(self, civ: 'CivilizationState', buffer: ThreadLocalProbeBuffer) -> None:
        """Launch initial probes from home world (buffered version)."""
        source_pos = self.galaxy.positions[civ.parent_star_idx]

        # Find targets
        targets = self._find_nearest_targets(
            source_pos,
            civ.probe_per_hop_range_pc,
            civ.probe_min_metallicity,
            civ.colonized_stars,
            civ.probe_offspring_count,
            civ.parent_star_idx
        )

        if len(targets) == 0:
            return

        # Create probes and events in buffer
        for target_idx in targets:
            probe_id = self.next_probe_id
            self.next_probe_id += 1

            target_pos = self.galaxy.positions[target_idx]
            distance_pc = np.linalg.norm(target_pos - source_pos)
            travel_time_yr = distance_pc / (civ.probe_velocity_c * C_PC_YR)
            travel_time_myr = travel_time_yr / 1e6

            arrival_time_myr = self.current_time_myr + travel_time_myr

            # Create probe
            probe = ProbeState(
                probe_id=probe_id,
                parent_probe_id=None,
                generation=0,
                launch_star_idx=civ.parent_star_idx,
                target_star_idx=target_idx,
                launch_time_myr=self.current_time_myr,
                arrival_time_myr=arrival_time_myr,
                has_arrived=False,
                replication_complete_time_myr=arrival_time_myr + (civ.probe_replication_delay_yr / 1e6),
                has_replicated=False
            )

            # Add to buffer with civ_id for later merging
            buffer.new_probes.append((civ.civ_id, probe))

            # Add arrival event to buffer
            buffer.new_events.append((
                arrival_time_myr,
                'probe_arrival',
                civ.civ_id,
                probe_id
            ))

    def _merge_probe_buffers(self, buffers: List[ThreadLocalProbeBuffer]) -> None:
        """
        Merge thread-local probe buffers back into shared state (single-threaded).

        Args:
            buffers: List of thread-local buffers from parallel workers
        """
        for buffer in buffers:
            # Merge probes into civilization lists
            for civ_id, probe in buffer.new_probes:
                # Find owning civilization
                for civ in self.civilizations:
                    if civ.civ_id == civ_id:
                        civ.active_probes.append(probe)
                        break

            # Merge events into global event queue
            for event in buffer.new_events:
                heapq.heappush(self.event_queue, event)

            # Apply extinction updates
            for civ_id, is_active, death_time, death_cause in buffer.extinction_updates:
                for civ in self.civilizations:
                    if civ.civ_id == civ_id:
                        civ.is_active = is_active
                        civ.death_time_myr = death_time
                        civ.death_cause = death_cause
                        break

    def _handle_replication_complete(self, civ: CivilizationState, probe: ProbeState) -> None:
        """Handle probe replication completion."""
        if probe.has_replicated:
            return  # Already processed

        probe.has_replicated = True

        # Launch offspring probes
        # Note: Parent probe was already archived on arrival (see _handle_probe_arrival)
        # We retrieve it from archived_probes to access its target location for offspring launch
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
            colonized_set=civ.colonized_stars,  # PRIORITY 1B: Already a Set, no conversion needed
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

            # PRIORITY 2: Schedule probe arrival event
            heapq.heappush(self.event_queue, (
                arrival_time_myr,
                'probe_arrival',
                civ.civ_id,
                probe.probe_id
            ))

    def _launch_offspring_probes(self, civ: CivilizationState, parent_probe: ProbeState) -> None:
        """Launch offspring probes from arrived parent probe."""
        source_idx = parent_probe.target_star_idx
        source_pos = self.galaxy.positions[source_idx]

        # Find nearest uncolonized stars with sufficient metallicity
        targets = self._find_nearest_targets(
            source_pos=source_pos,
            max_range_pc=civ.probe_per_hop_range_pc,
            max_targets=civ.probe_offspring_count,
            colonized_set=civ.colonized_stars,  # PRIORITY 1B: Already a Set, no conversion needed
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

            # PRIORITY 2: Schedule probe arrival event
            heapq.heappush(self.event_queue, (
                arrival_time_myr,
                'probe_arrival',
                civ.civ_id,
                probe.probe_id
            ))

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
        # PRIORITY 1A OPTIMIZATION: Use spatial index for efficient radius query
        # Instead of O(N) distance calc to all stars, use O(log N) KD-tree query
        if self._spatial_index is not None:
            # Query spatial index for stars within range
            max_range_kpc = max_range_pc / 1000.0
            nearby_indices, nearby_distances_kpc = self._spatial_index.query_radius(
                source_pos, max_range_kpc, return_distances=True
            )

            if len(nearby_indices) == 0:
                return []

            # Convert distances to parsecs for consistency
            distances_pc = nearby_distances_kpc * 1000.0
        else:
            # Fallback to brute force if spatial index not available
            distances_kpc = np.linalg.norm(self.galaxy.positions - source_pos, axis=1)
            distances_pc = distances_kpc * 1000.0
            range_mask = distances_pc <= max_range_pc
            nearby_indices = np.where(range_mask)[0]

            if len(nearby_indices) == 0:
                return []

        # Filter nearby stars: sufficient metallicity, uncolonized, not source
        metallicity_mask = self.galaxy.metallicities[nearby_indices] >= min_metallicity
        not_colonized = ~np.isin(nearby_indices, list(colonized_set))
        not_source = nearby_indices != exclude_idx

        # Base candidates: any star meeting resource requirements
        candidate_mask = metallicity_mask & not_colonized & not_source
        candidate_local_indices = np.where(candidate_mask)[0]

        if len(candidate_local_indices) == 0:
            return []

        # Map back to global indices
        candidate_indices = nearby_indices[candidate_local_indices]
        candidate_distances_pc = distances_pc[candidate_local_indices]

        # Split into habitable vs resource-only targets
        habitable_mask = self.galaxy.stellar_types[candidate_indices] == 1
        habitable_local_mask = habitable_mask

        habitable_candidates = candidate_indices[habitable_local_mask]
        habitable_distances = candidate_distances_pc[habitable_local_mask]

        resource_candidates = candidate_indices[~habitable_local_mask]
        resource_distances = candidate_distances_pc[~habitable_local_mask]

        # Sort each group by distance
        targets = []

        # Prefer habitable planets (potential for life contact)
        if len(habitable_candidates) > 0:
            hab_sorted_idx = np.argsort(habitable_distances)
            hab_sorted = habitable_candidates[hab_sorted_idx]
            targets.extend(hab_sorted[:max_targets].tolist())

        # Fill remaining quota with nearest resource-rich systems
        remaining = max_targets - len(targets)
        if remaining > 0 and len(resource_candidates) > 0:
            res_sorted_idx = np.argsort(resource_distances)
            res_sorted = resource_candidates[res_sorted_idx]
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
        not_colonized = ~np.isin(np.arange(len(self.galaxy.positions)), civ.colonized_stars)  # PRIORITY 1B: No list() needed
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

        dt_myr = self._current_dt_myr

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
                # Home world destroyed - check if civilization can survive from colonies
                if not civ.home_world_destroyed:
                    civ.home_world_destroyed = True
                    civ.home_world_destruction_time_myr = self.current_time_myr

                # Check if civilization has mature colonies to continue from
                num_mature = self._get_mature_colonies(civ)
                if num_mature == 0:
                    # No mature colonies - civilization extinct
                    civ.is_active = False
                    civ.death_time_myr = self.current_time_myr
                    civ.death_cause = 'supernova'
                # else: civilization continues from colonies with fragility penalty

                # Record hazard event for visualization
                self.hazard_events.append(HazardEvent(
                    time_myr=self.current_time_myr,
                    event_type='supernova',
                    position=civ_pos.copy(),  # Approximate location
                    energy=1e51,  # Typical supernova energy in ergs
                    sterilization_radius_pc=sn_info.get('sn_distance_pc', self.config.astrophysics.sn_sterilization_range_pc),
                    affected_civ_ids=[civ.civ_id]
                ))

                if not civ.is_active:
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
                # Home world destroyed - check if civilization can survive from colonies
                if not civ.home_world_destroyed:
                    civ.home_world_destroyed = True
                    civ.home_world_destruction_time_myr = self.current_time_myr

                # Check if civilization has mature colonies to continue from
                num_mature = self._get_mature_colonies(civ)
                if num_mature == 0:
                    # No mature colonies - civilization extinct
                    civ.is_active = False
                    civ.death_time_myr = self.current_time_myr
                    civ.death_cause = 'grb'
                # else: civilization continues from colonies with fragility penalty

                # Record hazard event for visualization
                self.hazard_events.append(HazardEvent(
                    time_myr=self.current_time_myr,
                    event_type='grb',
                    position=civ_pos.copy(),  # Approximate location
                    energy=1e54,  # Typical GRB energy in ergs
                    sterilization_radius_pc=grb_info.get('grb_distance_kpc', 1.0) * 1000.0,  # Convert kpc to pc
                    affected_civ_ids=[civ.civ_id]
                ))

    def _interpolate_probe_positions(self, current_time_myr: float) -> List[ProbeSnapshot]:
        """
        Calculate current positions of all in-flight probes.

        Interpolates probe positions between launch and arrival based on
        current simulation time. Used for visualization of expanding wavefronts.

        Args:
            current_time_myr: Current simulation time in Myr

        Returns:
            List of ProbeSnapshot objects with interpolated positions
        """
        probe_snapshots = []

        for civ in self.civilizations:
            # Skip dead civilizations
            if not civ.is_active:
                continue

            # Skip civilizations that haven't started expanding
            if not civ.active_probes:
                continue

            for probe in civ.active_probes:
                # Skip probes that have arrived (already counted as colonies)
                if probe.has_arrived:
                    continue

                # Skip probes not yet launched (shouldn't exist but be safe)
                if probe.launch_time_myr > current_time_myr:
                    continue

                # Calculate progress fraction
                total_time = probe.arrival_time_myr - probe.launch_time_myr
                elapsed_time = current_time_myr - probe.launch_time_myr

                if total_time > 0:
                    progress = min(1.0, elapsed_time / total_time)
                else:
                    progress = 0.0

                # Linear interpolation of position
                source_pos = self.galaxy.positions[probe.launch_star_idx]
                target_pos = self.galaxy.positions[probe.target_star_idx]
                current_pos = source_pos + progress * (target_pos - source_pos)

                probe_snapshot = ProbeSnapshot(
                    probe_id=probe.probe_id,
                    civ_id=civ.civ_id,
                    launch_star_idx=probe.launch_star_idx,
                    target_star_idx=probe.target_star_idx,
                    current_position=current_pos,
                    launch_time_myr=probe.launch_time_myr,
                    arrival_time_myr=probe.arrival_time_myr,
                    progress_fraction=progress,
                    velocity_c=probe.velocity_c,
                    generation=probe.generation
                )
                probe_snapshots.append(probe_snapshot)

        return probe_snapshots

    def _save_snapshot(self) -> None:
        """Save current simulation state as snapshot."""
        active_civs = sum(c.is_active for c in self.civilizations)

        # Interpolate in-flight probe positions for visualization
        probe_snapshots = self._interpolate_probe_positions(self.current_time_myr)

        snapshot = SimulationSnapshot(
            time_myr=self.current_time_myr,
            active_civilizations=active_civs,
            total_civilizations_ever=self.next_civ_id,
            colonized_systems=sum(len(c.colonized_stars) for c in self.civilizations if c.is_active),
            civilization_states=[c for c in self.civilizations],
            stellar_positions=self.galaxy.positions.copy() if self.galaxy.positions is not None else np.array([]),
            active_probes_in_flight=probe_snapshots,
            total_active_probes=len(probe_snapshots)
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
