"""Main simulation engine for galactic civilization modeling."""

import heapq
import time
import numpy as np
from pathlib import Path
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
    should_use_parallelization,
)
from ..galaxy.structure import GalaxyModel
from ..galaxy.star_formation import StarFormationHistory, InitialMassFunction
from ..civilization.probe_design import (
    probe_velocity_from_kardashev,
    per_hop_range_from_kardashev,
    offspring_count,
    replication_delay_years,
    min_metallicity_for_replication,
    C_PC_YR,
)
from ..civilization.war import (
    FleetState,
    WarState,
    BattleEvent,
    CommunicationEvent,
    VassalState,
    calculate_fleet_strength,
    calculate_colony_strength,
    resolve_battle,
    calculate_light_cone_arrival,
    is_communication_possible,
    check_alliance_cascade_light_cone,
)
from ..civilization.personality import (
    PersonalityState,
    sample_personality,
    evolve_personality,
    get_colony_personality_modifier,
)
from ..utils.civ_spatial_index import CivilizationSpatialIndex


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
class EncounterEvent:
    """Record of a civilization encounter event."""

    time_myr: float
    civ_1_id: int
    civ_2_id: int
    encounter_type: str  # "probe_arrival", "shared_colony", "sensor_detection"
    outcome: str  # "peace", "war_started", "alliance_formed", "vassalization"
    resolution_details: str
    is_within_light_cone: bool


@dataclass
class CivilizationState:
    """State of a single civilization."""

    civ_id: int
    birth_time_myr: float  # When civilization emerged
    parent_star_idx: int  # Index of star where civilization originated
    colonized_stars: Set[int] = field(
        default_factory=set
    )  # Indices of colonized stars (PRIORITY 1B: Set for O(1) lookups)
    colony_arrival_times: Dict[int, float] = field(
        default_factory=dict
    )  # star_idx -> arrival_time_myr
    kardashev_scale: float = 0.7  # Technological level: 0.7 (modern Earth) to 3.0 (galaxy-scale)
    kardashev_advancement_rate: float = (
        0.01  # Individual advancement rate (varies per civilization)
    )
    is_active: bool = True
    death_time_myr: Optional[float] = None
    death_cause: Optional[str] = (
        None  # 'extinction_event', 'self_destruction', 'old_age', 'supernova', 'grb', 'colonial_war'
    )

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
    active_probes: List["ProbeState"] = field(default_factory=list)
    archived_probes: List["ProbeState"] = field(default_factory=list)  # Completed probes

    # Personality and AI behavior
    personality_type: str = "defensive"
    friendliness: float = 0.5
    aggression_factor: float = 0.5
    war_trauma: float = 0.0
    victory_confidence: float = 0.5

    # Inter-civilization relations
    known_civilizations: Set[int] = field(default_factory=set)
    reputation: Dict[int, float] = field(default_factory=dict)  # civ_id -> reputation [-1.0, 1.0]
    allies: Set[int] = field(default_factory=set)
    enemies: Set[int] = field(default_factory=set)
    vassals: Dict[int, VassalState] = field(default_factory=dict)
    overlord: Optional[int] = None

    # War state
    war_state: Optional[WarState] = None
    battles_fought: int = 0
    wars_won: int = 0
    wars_lost: int = 0

    # Military fleet tracking
    active_fleets: List[FleetState] = field(default_factory=list)
    archived_fleets: List[FleetState] = field(default_factory=list)
    next_fleet_id: int = 0

    # Colony strength tracking
    colony_strengths: Dict[int, float] = field(default_factory=dict)  # star_idx -> strength

    # Strategic resources
    strategic_resource_stockpile: float = 100.0
    resource_debt: float = 0.0
    war_exhaustion: float = 0.0


@dataclass
class HazardEvent:
    """Record of an astrophysical hazard event."""

    time_myr: float
    event_type: str  # 'supernova', 'grb'
    position: np.ndarray  # 3D position in kpc
    energy: float  # Event energy (ergs)
    sterilization_radius_pc: float  # Lethal range in parsecs
    affected_civ_ids: List[int] = field(default_factory=list)  # Civilizations destroyed/affected


@dataclass
class HazardEvent:
    """Record of an astrophysical hazard event."""

    time_myr: float
    event_type: str  # 'supernova', 'grb'
    position: np.ndarray  # 3D position in kpc
    energy: float  # Event energy (ergs)
    sterilization_radius_pc: float  # Lethal range in parsecs
    affected_civ_ids: List[int] = field(default_factory=list)  # Civilizations destroyed/affected


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
    stellar_positions: np.ndarray  # For visualization (may be empty if delta compression)
    stellar_ages: Optional[np.ndarray] = None  # Stellar ages in Gyr for HR diagram evolution
    active_probes_in_flight: List[ProbeSnapshot] = field(default_factory=list)
    total_active_probes: int = 0
    hazard_events: List[HazardEvent] = field(default_factory=list)  # Disasters since last snapshot
    encounter_events: List[EncounterEvent] = field(
        default_factory=list
    )  # Civilization encounters since last snapshot
    communication_events: List[CommunicationEvent] = field(
        default_factory=list
    )  # Inter-civ communications since last snapshot
    battle_events: List[BattleEvent] = field(default_factory=list)  # Battles since last snapshot
    colony_positions: List[Tuple[int, np.ndarray]] = field(
        default_factory=list
    )  # (civ_id, position)
    civ_birth_ages: List[Tuple[int, float]] = field(default_factory=list)  # (civ_id, age_gyr)
    
    # Delta compression fields
    use_delta_compression: bool = False
    reference_time_myr: float = 0.0  # Time when initial_positions were captured
    stellar_velocities: Optional[np.ndarray] = None  # (N, 3) in km/s - only on first snapshot
    initial_positions: Optional[np.ndarray] = None  # (N, 3) in kpc - only on first snapshot
    
    def get_positions(self, fallback_galaxy: Optional[Any] = None) -> np.ndarray:
        """
        Reconstruct stellar positions at this snapshot's time.
        
        For delta compression, computes: initial_positions + velocities * dt
        
        Args:
            fallback_galaxy: GalaxyModel to use for initial_positions/velocities if not stored
            
        Returns:
            (N, 3) array of stellar positions in kpc
        """
        if not self.use_delta_compression:
            return self.stellar_positions
        
        init_pos = self.initial_positions
        vels = self.stellar_velocities
        
        if init_pos is None and fallback_galaxy is not None:
            init_pos = getattr(fallback_galaxy, 'initial_positions', None)
        if vels is None and fallback_galaxy is not None:
            vels = getattr(fallback_galaxy, 'velocities', None)
        
        if init_pos is None or vels is None:
            return self.stellar_positions
        
        dt_myr = self.time_myr - self.reference_time_myr
        v_kpc_myr = vels * 0.001022  # 1 km/s = 0.001022 kpc/Myr
        return init_pos + v_kpc_myr * dt_myr


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
            config.galaxy, seed=self.seed, use_numba=config.simulation.use_numba
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
                enabled=config.civilization.enable_nuclear_crisis,
            ),
            CrisisPeak(
                name="planetary_unification",
                kardashev_center=0.85,
                width=0.08,
                amplitude=config.civilization.crisis_planetary_unification_amplitude,
                enabled=config.civilization.enable_planetary_unification_crisis,
            ),
            CrisisPeak(
                name="ai_transition",
                kardashev_center=1.05,
                width=0.10,
                amplitude=config.civilization.crisis_ai_transition_amplitude,
                enabled=config.civilization.enable_ai_crisis,
            ),
            CrisisPeak(
                name="interplanetary_expansion",
                kardashev_center=1.25,
                width=0.15,
                amplitude=config.civilization.crisis_interplanetary_amplitude,
                enabled=config.civilization.enable_interplanetary_crisis,
            ),
            CrisisPeak(
                name="stellar_engineering",
                kardashev_center=1.80,
                width=0.20,
                amplitude=config.civilization.crisis_stellar_engineering_amplitude,
                enabled=config.civilization.enable_stellar_crisis,
            ),
            CrisisPeak(
                name="relativistic_weapons",
                kardashev_center=2.50,
                width=0.25,
                amplitude=config.civilization.crisis_relativistic_weapons_amplitude,
                enabled=config.civilization.enable_relativistic_weapons_crisis,
            ),
        ]

        self.extinction_model = ExtinctionModel(
            self_destruction_rate=config.civilization.self_destruction_probability_per_myr,
            mean_lifetime_myr=config.civilization.mean_civilization_lifetime_myr,
            model_type=config.civilization.self_destruction_model_type,
            baseline_rate=config.civilization.baseline_self_destruction_rate,
            baseline_scaling=config.civilization.baseline_risk_scaling,
            crisis_peaks=crisis_peaks,
        )

        # Simulation state
        self.current_time_myr: float = 0.0
        self.civilizations: List[CivilizationState] = []
        self.next_civ_id: int = 0
        self._active_civ_count: int = 0  # Cached count for O(1) check
        
        # O(1) lookup indexes for civilizations and probes
        self._civ_by_id: Dict[int, CivilizationState] = {}
        self._probe_by_id: Dict[int, Tuple[int, "ProbeState"]] = {}  # probe_id -> (civ_id, probe)

        # History tracking
        self.snapshots: List[SimulationSnapshot] = []
        self.hazard_events: List[HazardEvent] = []
        self.encounter_events: List[EncounterEvent] = []
        self.communication_events: List[CommunicationEvent] = []
        self.battle_events: List[BattleEvent] = []
        self._last_snapshot_time_myr: Optional[float] = None

        # Habitable star indices (cached)
        self.habitable_star_indices: Optional[np.ndarray] = None

        # Colonized stars tracking (for performance)
        self._colonized_mask: Optional[np.ndarray] = None

        # Spatial index for civilization territories (O(log N) overlap detection)
        self.civ_spatial_index: Optional[CivilizationSpatialIndex] = None

        # Disaster tracking modules (initialized in initialize())
        self.supernova_scheduler: Optional[Any] = None
        self.recovery_queue: Optional[Any] = None
        self.disaster_archiver: Optional[Any] = None

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
                seed=self.seed,
            )
        else:
            self.galaxy.ages = self.sfh.generate_stellar_ages(
                self.config.galaxy.total_stars, max_age_gyr=max_age_gyr, seed=self.seed
            )

        # Generate stellar masses from IMF
        self.galaxy.masses = self.imf.sample(self.config.galaxy.total_stars, seed=self.seed + 1)

        # Ensure massive stars have physically consistent ages
        # To spread SNe/GRBs evenly across the simulation (not clustered at start),
        # we assign time-until-death uniformly over the simulation duration,
        # then compute age = t_ms - time_until_death
        massive_mask = self.galaxy.masses > 8.0
        if massive_mask.any():
            t_ms_gyr = 10.0 * self.galaxy.masses[massive_mask] ** (-2.5)
            t_ms_myr = t_ms_gyr * 1000.0
            sim_duration_myr = self.config.simulation.simulation_duration_gyr * 1000.0
            
            rng = np.random.default_rng(self.seed + 100)
            n_massive = massive_mask.sum()
            
            # Assign time-until-death uniformly across simulation + some buffer
            # This spreads disasters evenly rather than clustering at start
            time_until_death_myr = rng.uniform(0, sim_duration_myr * 1.2, size=n_massive)
            
            # Compute age from time_until_death: age = t_ms - time_until_death
            ages_myr = t_ms_myr - time_until_death_myr
            
            # Clamp ages to valid range [0, t_ms]
            # Stars with computed age < 0 are "just born" (assign small positive age)
            # Stars with computed age > t_ms have "already died" (assign t_ms, scheduler handles)
            ages_myr = np.clip(ages_myr, 0.001, t_ms_myr * 0.999)
            
            self.galaxy.ages[massive_mask] = ages_myr / 1000.0  # Convert to Gyr

        # Generate metallicities (with radial gradient if enabled)
        if self.config.galaxy.use_metallicity_gradient:
            self.galaxy.metallicities = self.galaxy.calculate_metallicities()
        else:
            # Uniform metallicity
            self.galaxy.metallicities = np.zeros(self.config.galaxy.total_stars)

        # Determine stellar types (simplified: 0=unsuitable, 1=potentially habitable)
        # Stars within configured mass range are considered potentially habitable
        self.galaxy.stellar_types = (
            (self.galaxy.masses >= self.config.galaxy.habitable_mass_min_msun)
            & (self.galaxy.masses <= self.config.galaxy.habitable_mass_max_msun)
        ).astype(int)

        # Cache habitable star indices
        self.habitable_star_indices = np.where(self.galaxy.stellar_types == 1)[0]

        # Initialize colonized mask
        self._colonized_mask = np.zeros(self.config.galaxy.total_stars, dtype=bool)

        # Initialize civilization spatial index for efficient overlap detection
        self.civ_spatial_index = CivilizationSpatialIndex(self.galaxy.positions)

        # Build spatial index for efficient hazard and expansion queries
        if self.config.simulation.use_numba:
            print("Building spatial index for fast queries...")
            from ..utils.spatial import SpatialIndex

            self._spatial_index = SpatialIndex(self.galaxy.positions)
        else:
            self._spatial_index = None

        # Initialize disaster tracking modules
        print("Initializing disaster tracking...")
        from .disasters import (
            RecoveryQueue,
            DisasterArchiver,
            UnifiedDisasterScheduler,
        )

        simulation_duration_myr = self.config.simulation.simulation_duration_gyr * 1000.0
        self.disaster_scheduler = UnifiedDisasterScheduler(
            positions=self.galaxy.positions,
            masses=self.galaxy.masses,
            ages_gyr=self.galaxy.ages,
            metallicities=self.galaxy.metallicities,
            config=self.config.astrophysics,
            rng=self.rng,
            simulation_duration_myr=simulation_duration_myr,
            enable_star_formation=self.config.simulation.enable_star_formation,
            galaxy_scale_radius_kpc=self.config.galaxy.scale_length_kpc,
            spread_initial_disasters=self.config.simulation.spread_initial_disasters,
        )
        disaster_stats = self.disaster_scheduler.get_statistics()
        print(f"  Scheduled disasters: {disaster_stats['total_scheduled']} "
              f"(SN: {disaster_stats['supernovae']}, GRB: {disaster_stats['grbs']}, "
              f"NS mergers: {disaster_stats['ns_mergers']})")
        if disaster_stats['scheduled_star_births'] > 0:
            print(f"  Scheduled star births: {disaster_stats['scheduled_star_births']}")

        n_stars = self.config.galaxy.total_stars
        self.recovery_queue = RecoveryQueue(n_stars)

        # Pre-schedule civilization emergence events for O(1) emergence checks
        self._emergence_heap: List[Tuple[float, int]] = []  # (time_myr, star_idx)
        self._schedule_emergence_events(simulation_duration_myr)

        if self.config.simulation.save_snapshots:
            archive_path = Path(self.config.simulation.output_directory) / "disasters.h5"
            self.disaster_archiver = DisasterArchiver(
                archive_path=archive_path, recent_window_myr=10.0, buffer_size=1000
            )

        print(f"Galaxy initialized with {len(self.galaxy.positions)} stars")
        if self.config.galaxy.include_bulge:
            n_bulge = np.sum(self.galaxy.component_type == 0)
            print(f"  Bulge stars: {n_bulge} ({100*n_bulge/len(self.galaxy.positions):.1f}%)")
            print(f"  Disk stars: {len(self.galaxy.positions) - n_bulge}")
        print(f"Habitable stars: {len(self.habitable_star_indices)}")

    def _compute_next_timestep(self) -> float:
        """
        Compute adaptive timestep based on upcoming events.
        
        Considers:
        - Probe arrival/replication events
        - Scheduled disaster events (SN, GRB, NS merger)
        - Scheduled star birth events
        - Civilization activity level
        - Expected emergence time (prevents long stalls in quiet periods)

        Returns:
            Next timestep in Myr
        """
        cfg = self.config.simulation
        candidate_dt = cfg.max_timestep_myr

        if self.event_queue:
            next_event_time = self.event_queue[0][0]
            time_to_event = next_event_time - self.current_time_myr

            if time_to_event > 0 and time_to_event <= cfg.max_adaptive_step_myr:
                candidate_dt = min(candidate_dt, max(time_to_event, cfg.min_timestep_myr))

        if hasattr(self, 'disaster_scheduler') and self.disaster_scheduler is not None:
            next_disaster_time = self.disaster_scheduler.peek_next_disaster_time()
            if next_disaster_time is not None:
                time_to_disaster = next_disaster_time - self.current_time_myr
                if time_to_disaster > 0 and time_to_disaster <= cfg.max_adaptive_step_myr:
                    candidate_dt = min(candidate_dt, max(time_to_disaster + 0.001, cfg.min_timestep_myr))
            
            next_birth_time = self.disaster_scheduler.peek_next_star_birth_time()
            if next_birth_time is not None:
                time_to_birth = next_birth_time - self.current_time_myr
                if time_to_birth > 0 and time_to_birth <= cfg.max_adaptive_step_myr:
                    candidate_dt = min(candidate_dt, max(time_to_birth + 0.001, cfg.min_timestep_myr))

        active_civs = sum(1 for c in self.civilizations if c.is_active)

        if active_civs > 0:
            candidate_dt = min(candidate_dt, cfg.medium_timestep_myr)
        
        if self._emergence_heap:
            next_emergence_time = self._emergence_heap[0][0]
            time_to_emergence = next_emergence_time - self.current_time_myr
            if time_to_emergence > 0 and time_to_emergence <= cfg.max_adaptive_step_myr:
                candidate_dt = min(candidate_dt, max(time_to_emergence + 0.001, cfg.min_timestep_myr))

        return candidate_dt

    def _estimate_emergence_timestep(self) -> float:
        """
        Estimate appropriate timestep for emergence probability accuracy.
        
        Uses the expected emergence rate to choose a timestep that won't
        skip emergence windows, while staying efficient during quiet periods.
        
        Returns:
            Suggested timestep in Myr
        """
        cfg = self.config.simulation
        params = self.config.civilization
        
        f_life = params.fraction_develop_life
        f_intel = params.fraction_develop_intelligence
        f_tech = params.fraction_develop_technology
        n_habitable = params.avg_habitable_planets_per_system
        f_base = params.fraction_stars_with_planets
        
        p_emergence_per_star_gyr = f_base * n_habitable * f_life * f_intel * f_tech
        
        if self.habitable_star_indices is None:
            return cfg.max_timestep_myr
        
        n_eligible = len(self.habitable_star_indices)
        if n_eligible == 0:
            return cfg.max_timestep_myr
        
        expected_emergence_per_gyr = p_emergence_per_star_gyr * n_eligible
        
        if expected_emergence_per_gyr > 0:
            expected_time_between_myr = 1000.0 / expected_emergence_per_gyr
            target_dt = expected_time_between_myr / 10.0
            
            target_dt = max(cfg.medium_timestep_myr, min(target_dt, cfg.max_timestep_myr))
            return target_dt
        
        return cfg.max_timestep_myr

    def _schedule_emergence_events(self, simulation_duration_myr: float) -> None:
        """
        Pre-schedule all civilization emergence events using exponential sampling.
        
        Instead of checking every habitable star every timestep (O(N) per step),
        we sample emergence times upfront using exponential inter-arrival times.
        This reduces emergence checking to O(log N) heap operations.
        
        Stars that aren't old enough at simulation start but will become eligible
        during the simulation have their emergence events scheduled starting from
        the time they become eligible.
        """
        if self.habitable_star_indices is None or len(self.habitable_star_indices) == 0:
            return
        
        params = self.config.civilization
        min_age_gyr = params.min_stellar_age_for_life_gyr
        
        f_life = params.fraction_develop_life
        f_intel = params.fraction_develop_intelligence
        f_tech = params.fraction_develop_technology
        n_habitable = params.avg_habitable_planets_per_system
        f_base = params.fraction_stars_with_planets
        
        star_ages = self.galaxy.ages[self.habitable_star_indices]
        time_until_eligible_myr = np.maximum(0.0, (min_age_gyr - star_ages) * 1000.0)
        
        will_be_eligible_mask = time_until_eligible_myr < simulation_duration_myr
        candidate_indices = self.habitable_star_indices[will_be_eligible_mask]
        candidate_eligible_times = time_until_eligible_myr[will_be_eligible_mask]
        
        if len(candidate_indices) == 0:
            return
        
        metallicities = self.galaxy.metallicities[candidate_indices]
        if self.config.galaxy.use_metallicity_gradient:
            f_planets = f_base * np.power(10.0, metallicities)
            f_planets = np.clip(f_planets, 0.01, 1.0)
        else:
            f_planets = np.full(len(candidate_indices), f_base)
        
        rates_per_myr = f_planets * n_habitable * f_life * f_intel * f_tech / 1000.0
        
        for i, star_idx in enumerate(candidate_indices):
            rate = rates_per_myr[i]
            if rate <= 0:
                continue
            
            start_time = candidate_eligible_times[i]
            current_time = start_time
            while current_time < simulation_duration_myr:
                wait_time = self.rng.exponential(1.0 / rate)
                current_time += wait_time
                
                if current_time < simulation_duration_myr:
                    heapq.heappush(self._emergence_heap, (current_time, int(star_idx)))
        
        n_scheduled = len(self._emergence_heap)
        if n_scheduled > 0:
            print(f"  Pre-scheduled emergence events: {n_scheduled}")

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

        # Evolve stellar ages
        dt_gyr = dt_myr / 1000.0
        self.galaxy.ages += dt_gyr

        # Check for new civilization emergence (O(log N) with pre-scheduled events)
        self._check_civilization_emergence()

        # Fast path: skip civilization-related work when no civs exist
        has_active_civs = self._active_civ_count > 0
        
        if has_active_civs:
            # Evolve galaxy (stellar motion) - only needed for civ interactions
            if self.config.simulation.enable_stellar_motion:
                self.galaxy.evolve_positions(
                    dt_myr,
                    use_numba=self.config.simulation.use_numba,
                    enable_motion=True,
                )

            # Evolve existing civilizations
            self._evolve_civilizations()

            # Update colony strengths
            self._update_colony_strengths(dt_myr)

            # Scan for encounters between civilizations
            self._scan_for_encounters(dt_myr)

            # Resolve ongoing wars
            self._resolve_wars(dt_myr)

            # Manage strategic resources
            self._manage_strategic_resources(dt_myr)

            # Decay reputations
            self._decay_reputations(dt_myr)

        # Continuous star formation (new massive stars) - always process
        self._process_star_formation(dt_myr)

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
                environment="auto",
                show_iteration_rate=cfg.progress_show_iteration_rate,
                show_probe_count=cfg.progress_show_probe_count,
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

        # Finalize disaster archiver
        if self.disaster_archiver is not None:
            self.disaster_archiver.finalize()

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
            wall_time_elapsed=time.time() - self._start_time,
        )

        # Update tracker
        self._progress_tracker.update(metrics)

        # Update tracking state
        self._last_progress_pct = metrics.time_pct
        self._last_update_time = time.time()

    def _partition_civilizations_by_causality(self) -> List[List["CivilizationState"]]:
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
        civ_positions = np.array([self.galaxy.positions[c.parent_star_idx] for c in active_civs])

        civ_ids = [c.civ_id for c in active_civs]

        # Partition based on causality
        if cfg.parallel_check_shared_colonies:
            # Include colony overlap in causality check
            colonized_systems = [c.colonized_stars for c in active_civs]
            group_indices = find_causal_groups_with_colonies(
                civ_positions, civ_ids, colonized_systems, max_causal_distance_kpc
            )
        else:
            # Simple distance-based partitioning
            group_indices = find_causal_groups_simple(
                civ_positions, civ_ids, max_causal_distance_kpc
            )

        # Convert indices to civilization objects
        groups = []
        for group_idx_list in group_indices:
            group_civs = [active_civs[idx] for idx in group_idx_list]
            groups.append(group_civs)

        return groups

    def _check_civilization_emergence(self) -> None:
        """Check for new civilization emergence using pre-scheduled events.
        
        Uses O(log N) heap operations instead of O(N_habitable) per-step checks.
        Events are pre-scheduled at initialization based on Drake equation rates.
        
        Physical correctness: Emergence is cancelled if:
        1. A probe colonizes the star (colonized_mask check) - evolution disrupted
        2. The star was sterilized by a disaster (recovery_queue check) - no life possible
        """
        emerged_stars = []
        
        while self._emergence_heap and self._emergence_heap[0][0] <= self.current_time_myr:
            event_time, star_idx = heapq.heappop(self._emergence_heap)
            
            # If probe arrived before native emergence, skip (evolution disrupted)
            if self._colonized_mask[star_idx]:
                continue
            
            # If star was sterilized by disaster, skip (no life possible)
            if self.recovery_queue is not None and self.recovery_queue.status[star_idx] != 0:
                continue
            
            emerged_stars.append(star_idx)

        for star_idx in emerged_stars:
            star_idx_int = int(star_idx)

            # Sample random initial Kardashev scale
            initial_kardashev = self.rng.normal(
                self.config.civilization.initial_kardashev_scale_mean,
                self.config.civilization.initial_kardashev_scale_stddev,
            )
            initial_kardashev = max(0.5, min(1.0, initial_kardashev))  # Clamp to [0.5, 1.0]

            # Sample random advancement rate
            advancement_rate = self.rng.normal(
                self.config.civilization.kardashev_advancement_rate_mean,
                self.config.civilization.kardashev_advancement_rate_stddev,
            )
            advancement_rate = max(0.001, advancement_rate)  # Ensure positive

            new_civ = CivilizationState(
                civ_id=self.next_civ_id,
                birth_time_myr=self.current_time_myr,
                parent_star_idx=star_idx_int,
                colonized_stars={star_idx_int},
                colony_arrival_times={star_idx_int: self.current_time_myr},
                kardashev_scale=initial_kardashev,
                kardashev_advancement_rate=advancement_rate,
            )

            personality = sample_personality(
                initial_kardashev, self.rng, self.config.civilization.personality_assignment_model
            )
            new_civ.personality_type = personality.personality_type
            new_civ.friendliness = personality.friendliness
            new_civ.aggression_factor = personality.aggression_factor
            new_civ.war_trauma = personality.war_trauma
            new_civ.victory_confidence = personality.victory_confidence

            new_civ.colony_strengths[star_idx_int] = 1.0
            if self.civ_spatial_index is not None:
                self.civ_spatial_index.add_colony(
                    civ_id=new_civ.civ_id,
                    star_idx=star_idx_int,
                    strength=1.0,
                    arrival_time_myr=self.current_time_myr,
                    is_home_world=True,
                )

            self.civilizations.append(new_civ)
            self._civ_by_id[new_civ.civ_id] = new_civ
            self._colonized_mask[star_idx_int] = True
            self.next_civ_id += 1
            self._active_civ_count += 1

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
        self, kardashev_scale: float, num_mature_colonies: int, dt_myr: float
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
        k_factor = kardashev_scale - cfg.colonial_war_kardashev_threshold
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
        if not should_use_parallelization(
            n_active, cfg.parallel_min_civs_threshold, len(groups), cfg.parallel_worker_threads
        ):
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
            p_breakthrough = (
                self.config.civilization.kardashev_breakthrough_probability_per_myr * dt_myr
            )
            if self.rng.uniform(0, 1) < p_breakthrough:
                # Breakthrough! Advance faster
                advancement = (
                    base_advancement * self.config.civilization.kardashev_breakthrough_multiplier
                )
            # Check for technological stagnation
            elif (
                self.rng.uniform(0, 1)
                < self.config.civilization.kardashev_stagnation_probability_per_myr * dt_myr
            ):
                # Stagnation - no advancement this timestep
                advancement = 0.0
            else:
                # Normal advancement
                advancement = base_advancement

            civ.kardashev_scale = min(
                civ.kardashev_scale + advancement, self.config.civilization.kardashev_max_scale
            )

            # Check self-destruction with distributed resilience and colonial war
            # Base self-destruction from crises (nuclear, AI, etc.)
            p_single_crisis = self.extinction_model.check_self_destruction(
                dt_myr=dt_myr, rng=self.rng, kardashev_scale=civ.kardashev_scale
            )

            # Get mature colonies for resilience calculation
            num_mature = self._get_mature_colonies(civ)

            # Distributed resilience: crisis must affect all colonies
            # Each colony independently survives with probability (1 - p)
            if num_mature > 1:
                p_crisis_total = p_single_crisis**num_mature
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
                civ.death_cause = (
                    "colonial_war" if p_colonial_war > p_crisis_total else "self_destruction"
                )
                self._active_civ_count -= 1
                continue

            # Check age-based death with colonization bonus and distributed resilience
            # Calculate effective lifetime with logarithmic colonization bonus
            colonization_bonus = self.config.civilization.colonization_lifetime_bonus_myr * np.log(
                1 + num_mature
            )
            effective_lifetime = (
                self.config.civilization.mean_civilization_lifetime_myr + colonization_bonus
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
                    p_all_die = p_death_single**num_mature
                else:
                    p_all_die = p_death_single

                if self.rng.uniform(0, 1) < p_all_die:
                    civ.is_active = False
                    civ.death_time_myr = self.current_time_myr
                    civ.death_cause = "old_age"
                    self._active_civ_count -= 1
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
                    threshold_k120=self.config.civilization.metallicity_threshold_k120,
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
        Uses O(1) lookup dicts for civilization and probe retrieval.
        """
        while self.event_queue and self.event_queue[0][0] <= self.current_time_myr:
            event_time, event_type, civ_id, probe_id = heapq.heappop(self.event_queue)

            civ = self._civ_by_id.get(civ_id)
            if civ is None or not civ.is_active:
                continue

            probe_entry = self._probe_by_id.get(probe_id)
            if probe_entry is None:
                continue
            
            _, probe = probe_entry

            if event_type == "probe_arrival":
                self._handle_probe_arrival(civ, probe)
            elif event_type == "replication_complete":
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

        # Check if star already colonized by another civ (encounter!)
        for other_civ in self.civilizations:
            if other_civ.civ_id == civ.civ_id or not other_civ.is_active:
                continue

            if probe.target_star_idx in other_civ.colonized_stars:
                # First contact!
                if civ.civ_id not in other_civ.known_civilizations:
                    self._handle_encounter(civ, other_civ, probe.target_star_idx, "probe_arrival")
                break

        # Mark target as colonized
        if probe.target_star_idx not in civ.colonized_stars:
            civ.colonized_stars.add(probe.target_star_idx)
            civ.colony_arrival_times[probe.target_star_idx] = probe.arrival_time_myr
            civ.colony_strengths[probe.target_star_idx] = 1.0
            self._colonized_mask[probe.target_star_idx] = True

            if self.civ_spatial_index is not None:
                self.civ_spatial_index.add_colony(
                    civ_id=civ.civ_id,
                    star_idx=probe.target_star_idx,
                    strength=1.0,
                    arrival_time_myr=probe.arrival_time_myr,
                    is_home_world=False,
                )

        # Schedule replication complete event
        heapq.heappush(
            self.event_queue,
            (
                probe.replication_complete_time_myr,
                "replication_complete",
                civ.civ_id,
                probe.probe_id,
            ),
        )

        # Archive immediately on arrival - probe is now stationary, waiting to replicate
        # We keep probe data for replication event, but remove from active iteration
        # This prevents active_probes from accumulating arrived-but-not-yet-replicated probes
        if probe in civ.active_probes:
            civ.active_probes.remove(probe)
            civ.archived_probes.append(probe)

    def _evolve_civilizations_parallel(self, groups: List[List["CivilizationState"]]) -> None:
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
            futures = [executor.submit(self._evolve_civilization_group, group) for group in groups]

            # Collect results (thread-local buffers)
            buffers = [future.result() for future in futures]

        # Merge thread-local buffers back into shared state (single-threaded)
        self._merge_probe_buffers(buffers)

    def _evolve_civilization_group(
        self, group: List["CivilizationState"]
    ) -> ThreadLocalProbeBuffer:
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
                buffer.extinction_updates.append(
                    (
                        civ.civ_id,
                        False,  # is_active
                        self.current_time_myr,  # death_time_myr
                        civ.death_cause,
                    )
                )
                continue

            # Expansion - collect probes in buffer instead of modifying shared state
            if self.config.civilization.expansion_enabled:
                self._attempt_expansion_buffered(civ, buffer)

        return buffer

    def _advance_civilization_tech(self, civ: "CivilizationState", dt_myr: float) -> None:
        """Advance civilization technology (Kardashev scale)."""
        base_advancement = civ.kardashev_advancement_rate * dt_myr

        # Check for technological breakthrough
        p_breakthrough = (
            self.config.civilization.kardashev_breakthrough_probability_per_myr * dt_myr
        )
        if self.rng.uniform(0, 1) < p_breakthrough:
            advancement = (
                base_advancement * self.config.civilization.kardashev_breakthrough_multiplier
            )
        # Check for stagnation
        elif (
            self.rng.uniform(0, 1)
            < self.config.civilization.kardashev_stagnation_probability_per_myr * dt_myr
        ):
            advancement = 0.0
        else:
            advancement = base_advancement

        civ.kardashev_scale = min(
            civ.kardashev_scale + advancement, self.config.civilization.kardashev_max_scale
        )

    def _check_civilization_extinction(self, civ: "CivilizationState", dt_myr: float) -> bool:
        """
        Check if civilization goes extinct this timestep.

        Returns:
            True if civilization extinct, False otherwise
        """
        # Self-destruction check
        p_single_crisis = self.extinction_model.check_self_destruction(
            dt_myr=dt_myr, rng=self.rng, kardashev_scale=civ.kardashev_scale
        )

        # Distributed resilience
        num_mature = self._get_mature_colonies(civ)
        if num_mature > 1:
            p_crisis_total = p_single_crisis**num_mature
        else:
            p_crisis_total = p_single_crisis

        # Colonial war risk
        p_colonial_war = self._calculate_colonial_war_risk(civ.kardashev_scale, num_mature, dt_myr)

        # Combined extinction probability
        p_total_extinction = 1.0 - (1.0 - p_crisis_total) * (1.0 - p_colonial_war)

        if self.rng.uniform(0, 1) < p_total_extinction:
            civ.is_active = False
            civ.death_time_myr = self.current_time_myr
            civ.death_cause = (
                "colonial_war" if p_colonial_war > p_crisis_total else "self_destruction"
            )
            self._active_civ_count -= 1
            return True

        # Age-based death check
        colonization_bonus = self.config.civilization.colonization_lifetime_bonus_myr * np.log(
            1 + num_mature
        )
        effective_lifetime = (
            self.config.civilization.mean_civilization_lifetime_myr + colonization_bonus
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
                p_all_die = p_death_single**num_mature
            else:
                p_all_die = p_death_single

            if self.rng.uniform(0, 1) < p_all_die:
                civ.is_active = False
                civ.death_time_myr = self.current_time_myr
                civ.death_cause = "old_age"
                self._active_civ_count -= 1
                return True

        return False

    def _attempt_expansion_buffered(
        self, civ: "CivilizationState", buffer: ThreadLocalProbeBuffer
    ) -> None:
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
                    threshold_k120=self.config.civilization.metallicity_threshold_k120,
                )
                civ.probe_sensor_range_pc = self.config.civilization.probe_sensor_range_pc

                # Launch initial probes from home world - collect in buffer
                self._launch_initial_probes_buffered(civ, buffer)

    def _launch_initial_probes_buffered(
        self, civ: "CivilizationState", buffer: ThreadLocalProbeBuffer
    ) -> None:
        """Launch initial probes from home world (buffered version)."""
        source_pos = self.galaxy.positions[civ.parent_star_idx]

        # Find targets
        targets = self._find_nearest_targets(
            source_pos,
            civ.probe_per_hop_range_pc,
            civ.probe_min_metallicity,
            civ.colonized_stars,
            civ.probe_offspring_count,
            civ.parent_star_idx,
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
                replication_complete_time_myr=arrival_time_myr
                + (civ.probe_replication_delay_yr / 1e6),
                has_replicated=False,
            )

            # Add to buffer with civ_id for later merging
            buffer.new_probes.append((civ.civ_id, probe))

            # Add arrival event to buffer
            buffer.new_events.append((arrival_time_myr, "probe_arrival", civ.civ_id, probe_id))

    def _merge_probe_buffers(self, buffers: List[ThreadLocalProbeBuffer]) -> None:
        """
        Merge thread-local probe buffers back into shared state (single-threaded).

        Args:
            buffers: List of thread-local buffers from parallel workers
        """
        for buffer in buffers:
            # Merge probes into civilization lists
            for civ_id, probe in buffer.new_probes:
                civ = self._civ_by_id.get(civ_id)
                if civ is not None:
                    civ.active_probes.append(probe)
                    self._probe_by_id[probe.probe_id] = (civ_id, probe)

            # Merge events into global event queue
            for event in buffer.new_events:
                heapq.heappush(self.event_queue, event)

            # Apply extinction updates
            for civ_id, is_active, death_time, death_cause in buffer.extinction_updates:
                civ = self._civ_by_id.get(civ_id)
                if civ is not None:
                    civ.is_active = is_active
                    civ.death_time_myr = death_time
                    civ.death_cause = death_cause

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
            min_metallicity=civ.probe_min_metallicity,
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
                replication_delay_yr=civ.probe_replication_delay_yr,
            )
            self.next_probe_id += 1
            civ.active_probes.append(probe)
            self._probe_by_id[probe.probe_id] = (civ.civ_id, probe)

            # PRIORITY 2: Schedule probe arrival event
            heapq.heappush(
                self.event_queue, (arrival_time_myr, "probe_arrival", civ.civ_id, probe.probe_id)
            )

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
            min_metallicity=civ.probe_min_metallicity,
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
                replication_delay_yr=civ.probe_replication_delay_yr,
            )
            self.next_probe_id += 1
            civ.active_probes.append(probe)
            self._probe_by_id[probe.probe_id] = (civ.civ_id, probe)

            # PRIORITY 2: Schedule probe arrival event
            heapq.heappush(
                self.event_queue, (arrival_time_myr, "probe_arrival", civ.civ_id, probe.probe_id)
            )

    def _find_nearest_targets(
        self,
        source_pos: np.ndarray,
        max_range_pc: float,
        max_targets: int,
        colonized_set: Set[int],
        exclude_idx: int,
        min_metallicity: float,
    ) -> List[int]:
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

    def _check_sensor_retargeting(self, civ: CivilizationState, probe: "ProbeState") -> None:
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
        if hasattr(probe, "_has_retargeted") and probe._has_retargeted:
            return

        # Calculate probe's current position along trajectory
        elapsed_time_myr = self.current_time_myr - probe.launch_time_myr
        total_time_myr = probe.arrival_time_myr - probe.launch_time_myr

        if total_time_myr <= 0:
            return  # Avoid division by zero

        fraction_complete = min(elapsed_time_myr / total_time_myr, 1.0)

        # Interpolate position
        source_idx = (
            probe.source_star_idx if hasattr(probe, "source_star_idx") else civ.parent_star_idx
        )
        source_pos = self.galaxy.positions[source_idx]
        target_pos = self.galaxy.positions[probe.target_star_idx]
        current_pos = source_pos + fraction_complete * (target_pos - source_pos)

        # Scan for better targets within sensor range
        distances_kpc = np.linalg.norm(self.galaxy.positions - current_pos, axis=1)
        distances_pc = distances_kpc * 1000.0

        # Filter: within sensor range, meets metallicity, uncolonized
        sensor_mask = distances_pc <= civ.probe_sensor_range_pc
        metallicity_mask = self.galaxy.metallicities >= civ.probe_min_metallicity
        not_colonized = ~np.isin(
            np.arange(len(self.galaxy.positions)), civ.colonized_stars
        )  # PRIORITY 1B: No list() needed
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

    def _retarget_probe(
        self, probe: "ProbeState", new_target_idx: int, current_pos: np.ndarray
    ) -> None:
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

    def _process_star_formation(self, dt_myr: float) -> None:
        """
        Process pre-scheduled star births from UnifiedDisasterScheduler.
        
        Star births are scheduled at initialization for the entire simulation,
        so this method only retrieves and processes births in the current window.
        No per-timestep RNG calls - all randomness is resolved at init.
        """
        if not hasattr(self, 'disaster_scheduler') or self.disaster_scheduler is None:
            return
        
        if not self.config.simulation.enable_star_formation:
            return
        
        start_time = self.current_time_myr - dt_myr
        star_births = self.disaster_scheduler.get_star_births_in_window(
            start_myr=start_time,
            end_myr=self.current_time_myr
        )
        
        if not star_births:
            return
        
        for birth in star_births:
            t_ms_gyr = 10.0 * birth.mass ** (-2.5)
            time_until_sn_myr = t_ms_gyr * 1000.0
            sn_time_myr = birth.time_myr + time_until_sn_myr
            
            if sn_time_myr > self.config.simulation.simulation_duration_gyr * 1000:
                continue
            
            self._schedule_new_stellar_death(
                position=birth.position,
                mass=birth.mass,
                metallicity=birth.metallicity,
                sn_time_myr=sn_time_myr,
            )

    def _schedule_new_stellar_death(
        self,
        position: np.ndarray,
        mass: float,
        metallicity: float,
        sn_time_myr: float,
    ) -> None:
        """Add a newly formed massive star to the disaster schedule."""
        from .disasters import ScheduledDisaster, DisasterType
        import heapq
        
        scheduler = self.disaster_scheduler
        
        sn_disaster = ScheduledDisaster(
            time_myr=sn_time_myr,
            disaster_type=DisasterType.SUPERNOVA,
            star_idx=-1,
            position=position.copy(),
            energy_ergs=1e51,
            lethal_radius_pc=self.config.astrophysics.sn_lethal_range_pc,
            sterilization_radius_pc=self.config.astrophysics.sn_sterilization_range_pc,
        )
        
        sn_idx = len(scheduler.scheduled_disasters)
        scheduler.scheduled_disasters.append(sn_disaster)
        heapq.heappush(scheduler.disaster_by_time, (sn_time_myr, sn_idx))
        
        if mass > self.config.astrophysics.grb_min_progenitor_mass:
            grb_base_fraction = self.config.astrophysics.grb_fraction_of_sne
            z_modifier = np.clip(10.0 ** (-0.8 * metallicity), 0.1, 10.0)
            mass_modifier = np.clip((mass / 20.0) ** 0.5, 1.0, 2.0)
            p_grb = np.clip(grb_base_fraction * z_modifier * mass_modifier, 0.0, 1.0)
            
            if self.rng.uniform(0, 1) < p_grb:
                jet_theta = np.arccos(2 * self.rng.uniform(0, 1) - 1)
                jet_phi = self.rng.uniform(0, 2 * np.pi)
                
                grb_disaster = ScheduledDisaster(
                    time_myr=sn_time_myr,
                    disaster_type=DisasterType.GRB,
                    star_idx=-1,
                    position=position.copy(),
                    energy_ergs=1e54,
                    lethal_radius_pc=self.config.astrophysics.grb_lethal_range_kpc * 1000.0,
                    sterilization_radius_pc=self.config.astrophysics.grb_lethal_range_kpc * 1000.0,
                    grb_jet_theta=jet_theta,
                    grb_jet_phi=jet_phi,
                    grb_beaming_angle_deg=self.config.astrophysics.grb_beaming_angle_deg,
                )
                
                grb_idx = len(scheduler.scheduled_disasters)
                scheduler.scheduled_disasters.append(grb_disaster)
                heapq.heappush(scheduler.disaster_by_time, (sn_time_myr, grb_idx))
        
        if mass > 8.0 and mass < 25.0:
            scheduler.ns_remnant_indices.append(-1)
            scheduler.ns_formation_times.append(sn_time_myr)

    def _apply_hazards(self) -> None:
        """
        Apply astrophysical hazards using precomputed disaster schedule.

        Flow:
        1. Get all disasters occurring in this timestep window
        2. Record ALL disaster events (for visualization)
        3. Evaluate effects on civilizations using batch kernels
        4. Apply destruction effects to affected civilizations
        
        Uses UnifiedDisasterScheduler for O(log N) event retrieval and
        Numba-optimized kernels for batch effect evaluation.
        """
        from .disasters import DisasterType
        
        if not hasattr(self, 'disaster_scheduler') or self.disaster_scheduler is None:
            return

        dt_myr = self._current_dt_myr
        start_time = self.current_time_myr
        end_time = self.current_time_myr + dt_myr

        disasters = self.disaster_scheduler.get_disasters_in_window(start_time, end_time)

        if not disasters:
            if self.recovery_queue is not None:
                self.recovery_queue.process_recoveries(self.current_time_myr)
            return

        active_civs = [c for c in self.civilizations if c.is_active]
        
        if active_civs:
            civ_positions = np.array([
                self.galaxy.positions[c.parent_star_idx] for c in active_civs
            ])
        else:
            civ_positions = np.empty((0, 3))

        use_numba = self.config.simulation.use_numba
        if use_numba:
            try:
                from ..utils.numba_kernels import (
                    evaluate_sn_effect_on_civs_kernel,
                    evaluate_grb_effect_on_civs_kernel,
                    evaluate_ns_merger_effect_on_civs_kernel,
                )
                has_kernels = True
            except ImportError:
                has_kernels = False
        else:
            has_kernels = False

        for disaster in disasters:
            event_type_str = {
                DisasterType.SUPERNOVA: "supernova",
                DisasterType.GRB: "grb",
                DisasterType.NS_MERGER: "ns_merger",
            }.get(disaster.disaster_type, "unknown")

            hazard_event = HazardEvent(
                time_myr=disaster.time_myr,
                event_type=event_type_str,
                position=disaster.position.copy(),
                energy=disaster.energy_ergs,
                sterilization_radius_pc=disaster.sterilization_radius_pc,
                affected_civ_ids=[],
            )

            if len(active_civs) > 0:
                n_civs = len(active_civs)
                random_values = self.rng.uniform(0, 1, n_civs).astype(np.float64)

                if disaster.disaster_type == DisasterType.SUPERNOVA:
                    if has_kernels:
                        effects = evaluate_sn_effect_on_civs_kernel(
                            civ_positions.astype(np.float64),
                            disaster.position.astype(np.float64),
                            disaster.lethal_radius_pc,
                            disaster.sterilization_radius_pc,
                            random_values
                        )
                    else:
                        effects = self._evaluate_sn_effects_python(
                            civ_positions, disaster, random_values
                        )

                elif disaster.disaster_type == DisasterType.GRB:
                    if has_kernels:
                        effects = evaluate_grb_effect_on_civs_kernel(
                            civ_positions.astype(np.float64),
                            disaster.position.astype(np.float64),
                            disaster.grb_jet_theta,
                            disaster.grb_jet_phi,
                            disaster.grb_beaming_angle_deg,
                            disaster.lethal_radius_pc / 1000.0
                        )
                    else:
                        effects = self._evaluate_grb_effects_python(
                            civ_positions, disaster
                        )

                elif disaster.disaster_type == DisasterType.NS_MERGER:
                    sgrb_range = getattr(
                        self.config.astrophysics, 'ns_sgrb_lethal_range_kpc', 3.0
                    )
                    kilonova_lethal = getattr(
                        self.config.astrophysics, 'ns_kilonova_lethal_range_pc', 30.0
                    )
                    kilonova_sterilization = getattr(
                        self.config.astrophysics, 'ns_kilonova_sterilization_range_pc', 100.0
                    )
                    
                    if has_kernels:
                        effects = evaluate_ns_merger_effect_on_civs_kernel(
                            civ_positions.astype(np.float64),
                            disaster.position.astype(np.float64),
                            disaster.grb_jet_theta,
                            disaster.grb_jet_phi,
                            disaster.grb_beaming_angle_deg,
                            sgrb_range,
                            kilonova_lethal,
                            kilonova_sterilization,
                            random_values
                        )
                    else:
                        effects = self._evaluate_ns_merger_effects_python(
                            civ_positions, disaster, random_values
                        )
                else:
                    effects = np.zeros(n_civs, dtype=np.int32)

                for i, (civ, effect) in enumerate(zip(active_civs, effects)):
                    if effect > 0:
                        hazard_event.affected_civ_ids.append(civ.civ_id)
                        
                        if not civ.home_world_destroyed:
                            civ.home_world_destroyed = True
                            civ.home_world_destruction_time_myr = self.current_time_myr

                        num_mature = self._get_mature_colonies(civ)
                        if num_mature == 0:
                            civ.is_active = False
                            civ.death_time_myr = self.current_time_myr
                            civ.death_cause = event_type_str
                            self._active_civ_count -= 1

            self.hazard_events.append(hazard_event)

            if self.disaster_archiver is not None:
                self.disaster_archiver.archive_disaster(hazard_event, self.current_time_myr)

            if self.recovery_queue is not None:
                if disaster.star_idx >= 0:
                    self.recovery_queue.sterilize_star(
                        disaster.star_idx,
                        self.current_time_myr,
                        disaster.sterilization_radius_pc / 10.0,
                        permanent=(disaster.energy_ergs > 1e52),
                    )

        if self.recovery_queue is not None:
            self.recovery_queue.process_recoveries(self.current_time_myr)

        active_civs = [c for c in active_civs if c.is_active]

    def _evaluate_sn_effects_python(
        self, civ_positions: np.ndarray, disaster, random_values: np.ndarray
    ) -> np.ndarray:
        """Python fallback for SN effect evaluation."""
        n_civs = len(civ_positions)
        effects = np.zeros(n_civs, dtype=np.int32)
        
        lethal_kpc = disaster.lethal_radius_pc / 1000.0
        sterilization_kpc = disaster.sterilization_radius_pc / 1000.0
        
        for i in range(n_civs):
            dist_kpc = np.linalg.norm(civ_positions[i] - disaster.position)
            dist_pc = dist_kpc * 1000.0
            
            if dist_pc < disaster.lethal_radius_pc:
                effects[i] = 1
            elif dist_pc < disaster.sterilization_radius_pc:
                r = (dist_pc - disaster.lethal_radius_pc) / (
                    disaster.sterilization_radius_pc - disaster.lethal_radius_pc
                )
                if random_values[i] < np.exp(-3.0 * r):
                    effects[i] = 1
        
        return effects

    def _evaluate_grb_effects_python(
        self, civ_positions: np.ndarray, disaster
    ) -> np.ndarray:
        """Python fallback for GRB effect evaluation."""
        n_civs = len(civ_positions)
        effects = np.zeros(n_civs, dtype=np.int32)
        
        jet_dir = np.array([
            np.sin(disaster.grb_jet_theta) * np.cos(disaster.grb_jet_phi),
            np.sin(disaster.grb_jet_theta) * np.sin(disaster.grb_jet_phi),
            np.cos(disaster.grb_jet_theta)
        ])
        
        beaming_rad = disaster.grb_beaming_angle_deg * np.pi / 180.0
        cos_beaming = np.cos(beaming_rad)
        lethal_kpc = disaster.lethal_radius_pc / 1000.0
        
        for i in range(n_civs):
            to_civ = civ_positions[i] - disaster.position
            dist_kpc = np.linalg.norm(to_civ)
            
            if dist_kpc < 1e-10 or dist_kpc > lethal_kpc:
                continue
            
            to_civ_unit = to_civ / dist_kpc
            cos_angle = np.dot(jet_dir, to_civ_unit)
            
            if cos_angle > cos_beaming or (-cos_angle) > cos_beaming:
                effects[i] = 1
        
        return effects

    def _evaluate_ns_merger_effects_python(
        self, civ_positions: np.ndarray, disaster, random_values: np.ndarray
    ) -> np.ndarray:
        """Python fallback for NS merger effect evaluation."""
        n_civs = len(civ_positions)
        effects = np.zeros(n_civs, dtype=np.int32)
        
        sgrb_range = getattr(self.config.astrophysics, 'ns_sgrb_lethal_range_kpc', 3.0)
        kilonova_lethal = getattr(self.config.astrophysics, 'ns_kilonova_lethal_range_pc', 30.0)
        kilonova_sterilization = getattr(
            self.config.astrophysics, 'ns_kilonova_sterilization_range_pc', 100.0
        )
        
        jet_dir = np.array([
            np.sin(disaster.grb_jet_theta) * np.cos(disaster.grb_jet_phi),
            np.sin(disaster.grb_jet_theta) * np.sin(disaster.grb_jet_phi),
            np.cos(disaster.grb_jet_theta)
        ])
        
        beaming_rad = disaster.grb_beaming_angle_deg * np.pi / 180.0
        cos_beaming = np.cos(beaming_rad)
        
        kilonova_lethal_kpc = kilonova_lethal / 1000.0
        kilonova_sterilization_kpc = kilonova_sterilization / 1000.0
        
        for i in range(n_civs):
            to_civ = civ_positions[i] - disaster.position
            dist_kpc = np.linalg.norm(to_civ)
            
            if dist_kpc > 1e-10 and dist_kpc < sgrb_range:
                to_civ_unit = to_civ / dist_kpc
                cos_angle = np.dot(jet_dir, to_civ_unit)
                
                if cos_angle > cos_beaming or (-cos_angle) > cos_beaming:
                    effects[i] = 1
                    continue
            
            if dist_kpc < kilonova_lethal_kpc:
                effects[i] = 2
            elif dist_kpc < kilonova_sterilization_kpc:
                r = (dist_kpc - kilonova_lethal_kpc) / (
                    kilonova_sterilization_kpc - kilonova_lethal_kpc
                )
                if random_values[i] < np.exp(-3.0 * r):
                    effects[i] = 2
        
        return effects

        if self.recovery_queue is not None:
            recovered = self.recovery_queue.process_recoveries(self.current_time_myr)
            if len(recovered) > 0:
                pass

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
                    generation=probe.generation,
                )
                probe_snapshots.append(probe_snapshot)

        return probe_snapshots

    def _save_snapshot(self) -> None:
        """Save current simulation state as snapshot."""
        active_civs = sum(c.is_active for c in self.civilizations)

        # Interpolate in-flight probe positions for visualization
        probe_snapshots = self._interpolate_probe_positions(self.current_time_myr)

        # Collect hazard events since last snapshot
        hazard_events_since_snapshot = []
        if hasattr(self, "hazard_events"):
            hazard_events_since_snapshot = (
                [
                    h
                    for h in self.hazard_events
                    if h.time_myr > self._last_snapshot_time_myr
                    if h.time_myr <= self.current_time_myr
                ]
                if hasattr(self, "_last_snapshot_time_myr")
                and self._last_snapshot_time_myr is not None
                else []
            )

        # Collect encounter events since last snapshot
        encounter_events_since_snapshot = []
        if hasattr(self, "encounter_events"):
            encounter_events_since_snapshot = (
                [
                    e
                    for e in self.encounter_events
                    if e.time_myr > self._last_snapshot_time_myr
                    if e.time_myr <= self.current_time_myr
                ]
                if hasattr(self, "_last_snapshot_time_myr")
                and self._last_snapshot_time_myr is not None
                else []
            )

        # Collect communication events since last snapshot
        communication_events_since_snapshot = []
        if hasattr(self, "communication_events"):
            communication_events_since_snapshot = (
                [
                    c
                    for c in self.communication_events
                    if c.time_myr > self._last_snapshot_time_myr
                    if c.time_myr <= self.current_time_myr
                ]
                if hasattr(self, "_last_snapshot_time_myr")
                and self._last_snapshot_time_myr is not None
                else []
            )

        # Collect battle events since last snapshot
        battle_events_since_snapshot = []
        if hasattr(self, "battle_events"):
            battle_events_since_snapshot = (
                [
                    b
                    for b in self.battle_events
                    if b.time_myr > self._last_snapshot_time_myr
                    if b.time_myr <= self.current_time_myr
                ]
                if hasattr(self, "_last_snapshot_time_myr")
                and self._last_snapshot_time_myr is not None
                else []
            )

        # Collect colony positions
        colony_positions = []
        civ_birth_ages = []
        for civ in self.civilizations:
            civ_birth_ages.append((civ.civ_id, civ.birth_time_myr / 1000.0))
            if civ.is_active and civ.colonized_stars:
                for star_idx in civ.colonized_stars:
                    pos = (
                        self.galaxy.positions[star_idx]
                        if self.galaxy.positions is not None
                        else np.array([0.0, 0.0, 0.0])
                    )
                    colony_positions.append((civ.civ_id, pos.copy()))

        # Determine if we should use delta compression (stellar motion enabled)
        use_delta = self.config.simulation.enable_stellar_motion
        is_first_snapshot = len(self.snapshots) == 0
        
        if use_delta:
            if is_first_snapshot:
                # First snapshot: store initial positions and velocities
                stellar_positions = np.array([])  # Empty - use get_positions()
                initial_positions = (
                    self.galaxy.initial_positions.copy()
                    if hasattr(self.galaxy, 'initial_positions') and self.galaxy.initial_positions is not None
                    else self.galaxy.positions.copy() if self.galaxy.positions is not None else np.array([])
                )
                stellar_velocities = (
                    self.galaxy.velocities.copy()
                    if self.galaxy.velocities is not None
                    else None
                )
            else:
                # Subsequent snapshots: no positions, reference first snapshot
                stellar_positions = np.array([])
                initial_positions = None  # Reference first snapshot
                stellar_velocities = None  # Reference first snapshot
        else:
            # No delta compression: store full positions
            stellar_positions = (
                self.galaxy.positions.copy() if self.galaxy.positions is not None else np.array([])
            )
            initial_positions = None
            stellar_velocities = None

        snapshot = SimulationSnapshot(
            time_myr=self.current_time_myr,
            active_civilizations=active_civs,
            total_civilizations_ever=self.next_civ_id,
            colonized_systems=sum(
                len(c.colonized_stars) for c in self.civilizations if c.is_active
            ),
            civilization_states=[c for c in self.civilizations],
            stellar_positions=stellar_positions,
            stellar_ages=(
                self.galaxy.ages.copy() if self.galaxy.ages is not None else None
            ),
            active_probes_in_flight=probe_snapshots,
            total_active_probes=len(probe_snapshots),
            hazard_events=hazard_events_since_snapshot,
            encounter_events=encounter_events_since_snapshot,
            communication_events=communication_events_since_snapshot,
            battle_events=battle_events_since_snapshot,
            colony_positions=colony_positions,
            civ_birth_ages=civ_birth_ages,
            use_delta_compression=use_delta,
            reference_time_myr=0.0,
            stellar_velocities=stellar_velocities,
            initial_positions=initial_positions,
        )

        self._last_snapshot_time_myr = self.current_time_myr
        self.snapshots.append(snapshot)

    def get_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics."""
        active_civs = sum(c.is_active for c in self.civilizations)

        return {
            "total_civilizations": self.next_civ_id,
            "active_civilizations": active_civs,
            "extinct_civilizations": self.next_civ_id - active_civs,
            "total_colonized_systems": sum(len(c.colonized_stars) for c in self.civilizations),
            "current_time_gyr": self.current_time_myr / 1000.0,
            "snapshots_saved": len(self.snapshots),
        }

    def _scan_for_encounters(self, dt_myr: float) -> None:
        """
        Scan for new encounters between civilizations using spatial index.

        O(N) scan using spatial index instead of O(N²) brute force.
        """
        if self.civ_spatial_index is None:
            return

        active_civs = [c for c in self.civilizations if c.is_active]

        for civ in active_civs:
            if len(civ.colonized_stars) == 0:
                continue

            overlaps = self.civ_spatial_index.find_territory_overlaps([civ.civ_id])

            for civ_a_id, civ_b_id, overlapping_stars in overlaps:
                if civ_b_id in civ.known_civilizations:
                    continue

                civ_a = next((c for c in active_civs if c.civ_id == civ_a_id), None)
                civ_b = next((c for c in active_civs if c.civ_id == civ_b_id), None)

                if civ_a is None or civ_b is None:
                    continue

                star_idx = next(iter(overlapping_stars))
                self._handle_encounter(civ_a, civ_b, star_idx, "shared_colony")

    def _handle_encounter(
        self,
        civ_a: CivilizationState,
        civ_b: CivilizationState,
        location_idx: int,
        encounter_type: str,
    ) -> None:
        """
        Handle first contact between two civilizations.
        """
        civ_a.known_civilizations.add(civ_b.civ_id)
        civ_b.known_civilizations.add(civ_a.civ_id)

        civ_a.reputation[civ_b.civ_id] = 0.0
        civ_b.reputation[civ_a.civ_id] = 0.0

        p_war = self._calculate_encounter_war_probability(civ_a, civ_b)

        if self.rng.uniform(0, 1) < p_war:
            self._start_war(civ_a, civ_b, [location_idx])
            outcome = "war_started"
        else:
            if self.config.civilization.alliance_formation_enabled:
                if civ_a.personality_type == "xenophile" and civ_b.personality_type == "xenophile":
                    self._form_alliance(civ_a, civ_b)
                    outcome = "alliance_formed"
                else:
                    outcome = "peace"
            else:
                outcome = "peace"

        pos_a = (
            self.galaxy.positions[civ_a.parent_star_idx]
            if self.galaxy.positions is not None
            else np.array([0.0, 0.0, 0.0])
        )
        pos_b = (
            self.galaxy.positions[civ_b.parent_star_idx]
            if self.galaxy.positions is not None
            else np.array([0.0, 0.0, 0.0])
        )
        is_causal = is_communication_possible(
            pos_a, pos_b, self.current_time_myr, self.current_time_myr
        )

        self.encounter_events.append(
            EncounterEvent(
                time_myr=self.current_time_myr,
                civ_1_id=civ_a.civ_id,
                civ_2_id=civ_b.civ_id,
                encounter_type=encounter_type,
                outcome=outcome,
                resolution_details=f"K: {civ_a.kardashev_scale:.2f} vs {civ_b.kardashev_scale:.2f}",
                is_within_light_cone=is_causal,
            )
        )

    def _calculate_encounter_war_probability(
        self, civ_a: CivilizationState, civ_b: CivilizationState
    ) -> float:
        """
        Calculate probability that encounter leads to war.
        """
        base_war_prob = 1.0 - (civ_a.friendliness * civ_b.friendliness)

        tech_gap = abs(civ_a.kardashev_scale - civ_b.kardashev_scale)
        tech_factor = tech_gap * self.config.civilization.tech_advantage_sensitivity

        rep_modifier = 0.0
        if self.config.civilization.reputation_enabled:
            civ_a_rep = civ_a.reputation.get(civ_b.civ_id, 0.0)
            civ_b_rep = civ_b.reputation.get(civ_a.civ_id, 0.0)
            rep_modifier = (civ_a_rep + civ_b_rep) * -0.3

            for ally_id in civ_a.allies:
                if ally_id == civ_b.civ_id:
                    rep_modifier -= 0.2

        p_war = base_war_prob + tech_factor + rep_modifier
        return np.clip(p_war, 0.0, 1.0)

    def _start_war(
        self, aggressor: CivilizationState, defender: CivilizationState, disputed_stars: List[int]
    ) -> None:
        """
        Initialize war between two civilizations.
        """
        aggressor.war_state = WarState(
            enemy_civ_id=defender.civ_id,
            start_time_myr=self.current_time_myr,
            last_encounter_time_myr=self.current_time_myr,
            territory_disputed=set(disputed_stars),
            casualties_suffered=0.0,
        )

        defender.war_state = WarState(
            enemy_civ_id=aggressor.civ_id,
            start_time_myr=self.current_time_myr,
            last_encounter_time_myr=self.current_time_myr,
            territory_disputed=set(disputed_stars),
            casualties_suffered=0.0,
        )

        aggressor.enemies.add(defender.civ_id)
        defender.enemies.add(aggressor.civ_id)

        aggressor.reputation[defender.civ_id] -= 0.4

        if self.config.civilization.alliance_propagation_enabled:
            pos_defender = (
                self.galaxy.positions[defender.parent_star_idx]
                if self.galaxy.positions is not None
                else np.array([0.0, 0.0, 0.0])
            )
            ally_positions = {
                ally_id: (
                    self.galaxy.positions[
                        next(
                            (c for c in self.civilizations if c.civ_id == ally_id and c.is_active)
                        ).parent_star_idx
                    ]
                    if self.galaxy.positions is not None
                    else np.array([0.0, 0.0, 0.0])
                )
                for ally_id in defender.allies
            }

            can_join = check_alliance_cascade_light_cone(
                attacker_civ_id=aggressor.civ_id,
                defender_civ_id=defender.civ_id,
                ally_positions=ally_positions,
                war_start_time_myr=self.current_time_myr,
            )

            for ally_id in can_join:
                ally = next((c for c in self.civilizations if c.civ_id == ally_id), None)
                if ally is not None:
                    ally.enemies.add(aggressor.civ_id)
                    aggressor.reputation[ally_id] -= 0.2

    def _resolve_wars(self, dt_myr: float) -> None:
        """
        Resolve ongoing wars for this time step.

        War resolution mechanics:
        - Battles occur periodically at disputed territories
        - Fleets move and engage
        - Territory transferred based on battle outcomes
        - Wars end with victory, stalemate, or destruction
        """
        active_civs = [c for c in self.civilizations if c.is_active]

        for civ in active_civs:
            if civ.war_state is None:
                continue

            enemy = next((c for c in active_civs if c.civ_id == civ.war_state.enemy_civ_id), None)
            if enemy is None or not enemy.is_active:
                self._end_war(civ, victor=civ)
                continue

            war_duration = self.current_time_myr - civ.war_state.start_time_myr
            if war_duration > self.config.civilization.war_duration_max_myr:
                if self.rng.uniform(0, 1) < self.config.civilization.war_stalemate_probability:
                    self._end_war(civ, enemy, stalemate=True)
                    continue

            battles_this_step = int(
                dt_myr / self.config.civilization.battle_resolution_interval_myr
            )
            for _ in range(max(1, battles_this_step)):
                if len(civ.war_state.territory_disputed) == 0:
                    break

                star_idx = self.rng.choice(list(civ.war_state.territory_disputed))
                self._resolve_battle_at_star(civ, enemy, star_idx)

            new_overlap = civ.colonized_stars & enemy.colonized_stars
            civ.war_state.territory_disputed = new_overlap
            enemy.war_state.territory_disputed = new_overlap

            if len(enemy.colonized_stars) == 0:
                self._end_war(civ, enemy, total_destruction=True)
                continue

            if len(civ.colonized_stars) == 0:
                self._end_war(enemy, civ, total_destruction=True)
                continue

    def _resolve_battle_at_star(
        self, civ_a: CivilizationState, civ_b: CivilizationState, star_idx: int
    ) -> None:
        """
        Resolve a single battle at a disputed star.
        """
        colony_strength_a = civ_a.colony_strengths.get(star_idx, 1.0)
        colony_strength_b = civ_b.colony_strengths.get(star_idx, 1.0)

        is_home_world_a = star_idx == civ_a.parent_star_idx
        is_home_world_b = star_idx == civ_b.parent_star_idx

        if is_home_world_a:
            colony_strength_a *= 2.0
        if is_home_world_b:
            colony_strength_b *= 2.0

        colony_age_a = self.current_time_myr - civ_a.colony_arrival_times.get(
            star_idx, self.current_time_myr
        )
        colony_age_b = self.current_time_myr - civ_b.colony_arrival_times.get(
            star_idx, self.current_time_myr
        )

        strength_a = (
            calculate_colony_strength(
                colony_age_myr=colony_age_a,
                kardashev_scale=civ_a.kardashev_scale,
                population=1.0,
                is_home_world=is_home_world_a,
            )
            * colony_strength_a
        )

        strength_b = (
            calculate_colony_strength(
                colony_age_myr=colony_age_b,
                kardashev_scale=civ_b.kardashev_scale,
                population=1.0,
                is_home_world=is_home_world_b,
            )
            * colony_strength_b
        )

        tech_gap = civ_a.kardashev_scale - civ_b.kardashev_scale

        from scipy.special import expit

        win_prob_a = 0.5 + 0.4 * expit(
            tech_gap / self.config.civilization.tech_advantage_sensitivity
        )

        if self.rng.uniform(0, 1) < win_prob_a:
            winner, loser = civ_a, civ_b
        else:
            winner, loser = civ_b, civ_a

        if star_idx in loser.colonized_stars:
            loser.colonized_stars.remove(star_idx)
            loser.colony_strengths.pop(star_idx, None)
            loser.colony_arrival_times.pop(star_idx, None)
            if self.civ_spatial_index is not None:
                self.civ_spatial_index.remove_colony(loser.civ_id, star_idx)

            winner.colonized_stars.add(star_idx)
            winner.colony_strengths[star_idx] = loser.colony_strengths.get(star_idx, 1.0) * 0.9
            winner.colony_arrival_times[star_idx] = self.current_time_myr
            if self.civ_spatial_index is not None:
                self.civ_spatial_index.add_colony(
                    civ_id=winner.civ_id,
                    star_idx=star_idx,
                    strength=winner.colony_strengths[star_idx],
                    arrival_time_myr=self.current_time_myr,
                    is_home_world=star_idx == winner.parent_star_idx,
                )

            winner.reputation[loser.civ_id] = winner.reputation.get(loser.civ_id, 0.0) + 0.1
            loser.reputation[winner.civ_id] = loser.reputation.get(winner.civ_id, 0.0) - 0.2

            if self.config.civilization.personality_evolution_enabled:
                winner.personality = evolve_personality(
                    winner,
                    "victory",
                    num_wars_lost=loser.wars_lost,
                    num_wars_won=winner.wars_won,
                    rng=self.rng,
                    evolution_rate=self.config.civilization.personality_evolution_rate,
                )
                loser.personality = evolve_personality(
                    loser,
                    "defeat",
                    num_wars_lost=loser.wars_lost + 1,
                    num_wars_won=loser.wars_won,
                    rng=self.rng,
                    evolution_rate=self.config.civilization.personality_evolution_rate,
                )

            winner.wars_won += 1
            loser.wars_lost += 1
            winner.war_state.victories += 1
            loser.war_state.defeats += 1

            if star_idx == loser.parent_star_idx:
                loser.home_world_destroyed = True
                loser.home_world_destruction_time_myr = self.current_time_myr

            self.battle_events.append(
                BattleEvent(
                    time_myr=self.current_time_myr,
                    star_idx=star_idx,
                    attacker_civ_id=civ_a.civ_id,
                    defender_civ_id=civ_b.civ_id,
                    attacker_fleet_id=None,
                    defender_fleet_id=None,
                    outcome=(
                        BattleOutcome.ATTACKER_WIN
                        if winner == civ_a
                        else BattleOutcome.DEFENDER_WIN
                    ),
                    attacker_casualties=0.1 * strength_a,
                    defender_casualties=0.2 * strength_b,
                    territory_transferred=True,
                )
            )

    def _end_war(
        self,
        civ_a: CivilizationState,
        civ_b: Optional[CivilizationState] = None,
        victor: Optional[CivilizationState] = None,
        stalemate: bool = False,
        total_destruction: bool = False,
    ) -> None:
        """
        End war between civilizations.
        """
        if civ_a.war_state:
            civ_a.war_state = None

        if civ_b and civ_b.war_state:
            civ_b.war_state = None

        if total_destruction and civ_b and victor:
            civ_b.is_active = False
            civ_b.death_time_myr = self.current_time_myr
            civ_b.death_cause = "war"

            victor.kardashev_scale += 0.05 * (1.0 - victor.kardashev_scale / 3.0)

            for star_idx in civ_b.colonized_stars:
                if star_idx not in victor.colonized_stars:
                    victor.colonized_stars.add(star_idx)
                    victor.colony_strengths[star_idx] = (
                        civ_b.colony_strengths.get(star_idx, 1.0) * 0.5
                    )
                    victor.colony_arrival_times[star_idx] = self.current_time_myr
                    if self.civ_spatial_index is not None:
                        self.civ_spatial_index.add_colony(
                            civ_id=victor.civ_id,
                            star_idx=star_idx,
                            strength=victor.colony_strengths[star_idx],
                            arrival_time_myr=self.current_time_myr,
                            is_home_world=False,
                        )

    def _form_alliance(self, civ_a: CivilizationState, civ_b: CivilizationState) -> None:
        """
        Form alliance between two civilizations.
        """
        civ_a.allies.add(civ_b.civ_id)
        civ_b.allies.add(civ_a.civ_id)

        civ_a.reputation[civ_b.civ_id] = 0.8
        civ_b.reputation[civ_a.civ_id] = 0.8

        civ_a.enemies.discard(civ_b.civ_id)
        civ_b.enemies.discard(civ_a.civ_id)

    def _decay_reputations(self, dt_myr: float) -> None:
        """
        Decay reputation values towards neutral (0.0) over time.
        Only processes active civilizations with non-empty reputations.
        """
        decay = self.config.civilization.reputation_decay_rate * (dt_myr / 1000.0)
        
        if decay <= 0.0:
            return

        for civ in self.civilizations:
            if not civ.is_active or not civ.reputation:
                continue
            
            keys_to_remove = []
            for other_civ_id, rep_value in civ.reputation.items():
                if rep_value > 0:
                    new_val = rep_value - decay
                    if new_val <= 0.001:
                        keys_to_remove.append(other_civ_id)
                    else:
                        civ.reputation[other_civ_id] = new_val
                elif rep_value < 0:
                    new_val = rep_value + decay
                    if new_val >= -0.001:
                        keys_to_remove.append(other_civ_id)
                    else:
                        civ.reputation[other_civ_id] = new_val
            
            for key in keys_to_remove:
                del civ.reputation[key]

    def _update_colony_strengths(self, dt_myr: float) -> None:
        """
        Update colony strengths based on age and civilization K level.
        """
        for civ in self.civilizations:
            if not civ.is_active:
                continue

            for star_idx in civ.colonized_stars:
                colony_age = self.current_time_myr - civ.colony_arrival_times.get(star_idx, 0.0)
                age_factor = 1.0 + np.log10(1.0 + colony_age / 0.05)

                is_home_world = star_idx == civ.parent_star_idx
                home_bonus = 2.0 if is_home_world else 1.0

                tech_bonus = np.exp(civ.kardashev_scale * 0.5)

                civ.colony_strengths[star_idx] = age_factor * home_bonus * tech_bonus

                if self.civ_spatial_index is not None:
                    colony_info = self.civ_spatial_index.get_colony_info(civ.civ_id, star_idx)
                    if colony_info is not None:
                        colony_info.strength = civ.colony_strengths[star_idx]

    def _manage_strategic_resources(self, dt_myr: float) -> None:
        """
        Manage strategic resources for civilizations in war.
        """
        war_cost = self.config.civilization.war_resource_cost_myr * dt_myr
        generation = self.config.civilization.resource_generation_rate * dt_myr

        for civ in self.civilizations:
            if not civ.is_active:
                continue

            if civ.war_state is not None:
                civ.strategic_resource_stockpile -= war_cost
                civ.resource_debt += war_cost * 0.1
                civ.war_exhaustion += 0.01 * dt_myr
            else:
                civ.strategic_resource_stockpile = min(
                    200.0, civ.strategic_resource_stockpile + generation
                )
                civ.war_exhaustion = max(0.0, civ.war_exhaustion - 0.05 * dt_myr)

            civ.strategic_resource_stockpile = max(0.0, civ.strategic_resource_stockpile)
