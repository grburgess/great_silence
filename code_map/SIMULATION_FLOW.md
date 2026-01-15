# Simulation Flow Diagram

## High-Level Architecture

```
SimulationConfig
    ↓
GalaxySimulation (engine.py)
    ├── GalaxyModel (galaxy/structure.py)
    ├── StarFormationHistory (galaxy/star_formation.py)
    ├── InitialMassFunction (galaxy/star_formation.py)
    ├── CivilizationEmergence (civilization/emergence.py)
    ├── ExtinctionModel (civilization/extinction.py)
    ├── ExpansionModel (civilization/expansion.py)
    ├── ProbeDesign (civilization/probe_design.py)
    ├── HazardEvaluator (astrophysics/hazards.py)
    ├── SupernovaScheduler (simulation/disasters/scheduler.py)
    ├── RecoveryQueue (simulation/disasters/recovery.py)
    ├── DisasterArchiver (simulation/disasters/archiver.py)
    └── SpatialIndex (utils/spatial.py)
```

## Monte Carlo Flow

```
MonteCarloRunner(config)
    ↓
run_parallel(n_realizations)
    ├─ Spawn worker processes (one per realization)
    │   ├─ Each process: GalaxySimulation(config, seed)
    │   ├─ Each process: sim.initialize() + sim.run()
    │   └─ Each process: Return results
    └─ Collect results from all processes
    ↓
analyze_results()
    ├─ Aggregate statistics across realizations
    │   ├─ Mean/std/median/percentiles of metrics
    │   ├─ Civilization count distribution
    │   ├─ Galactic settlement fraction
    │   └─ Extinction cause breakdown
    └─ Generate distribution plots
```

## Initialization Flow

```
GalaxySimulation.__init__()
    ↓
GalaxyModel.generate_stellar_population()
    ├── _generate_bulge() [Hernquist profile]
    ├── _generate_exponential_disk() [ρ(R,z) ∝ exp(-R/h_R)exp(-|z|/h_z)]
    ├── _apply_spiral_arms() [density wave perturbation]
    ├── _generate_velocities() [rotation curve, equilibrium kinematics]
    ├── SFH.generate_stellar_ages_with_gradient() [radial age gradient]
    ├── IMF.sample() [Kroupa/Salpeter/Chabrier]
    └─ Filter habitable stars [0.5-1.5 M☉]
    ↓
Initialize disaster tracking (if enabled)
    ├─ SupernovaScheduler._build_schedule() [precompute SN times]
    │   └─ Calculate main sequence lifetimes for M > 8 M☉
    │   └─ Build min-heap of (time, star_idx)
    ├─ RecoveryQueue for sterilization tracking
    └─ DisasterArchiver for HDF5 binary encoding
    ↓
SpatialIndex.build() [KD-tree for O(log N) queries]
    ↓
Initialize extinction model with crisis peaks
    ├─ Nuclear age crisis at K=0.72
    ├─ Planetary unification crisis at K=0.85
    └─ Additional configurable peaks
```
GalaxySimulation.__init__()
    ↓
GalaxyModel.generate_stellar_population()
    ├── _generate_bulge() [Hernquist profile]
    ├── _generate_exponential_disk() [ρ(R,z) ∝ exp(-R/h_R)exp(-|z|/h_z)]
    ├── _apply_spiral_arms() [density wave perturbation]
    ├── _generate_velocities() [rotation curve, equilibrium kinematics]
    ├── SFH.generate_stellar_ages_with_gradient() [radial age gradient]
    ├── IMF.sample() [Kroupa/Salpeter/Chabrier]
    └── Filter habitable stars [0.5-1.5 M☉]
    ↓
SpatialIndex.build() [KD-tree for O(log N) queries]
    ↓
SupernovaScheduler._build_schedule() [precompute SN times]
    └── Calculate main sequence lifetimes for M > 8 M☉
    └── Build min-heap of (time, star_idx)
```

## Main Simulation Loop

```
while current_time < duration:
    ├─ Compute adaptive timestep
    ├─ Execute step()
    └─ Update progress
```

### Step Flow (per timestep)

```
_step(dt_myr)
    ↓
galaxy.evolve_positions(dt_myr) [leapfrog integrator]
    ↓
_check_civilization_emergence()
    └── Vectorized Drake equation over habitable stars
    └── p_emergence × dt_myr
    └── Create new CivilizationState objects
    ↓
_evolve_civilizations()
    ├─ Sequential or Parallel (causality-preserving)
    │   ├─ Advance Kardashev scale
    │   ├─ Check self-destruction [crisis peaks at K]
    │   ├─ Check age-based extinction
    │   └─ Attempt expansion (K ≥ 0.85)
    │       └─ _attempt_expansion()
    │           └─ Launch initial probes
    │               └── Schedule arrival events in event_queue
    ↓
_process_probe_events()
    ├─ Pop events from min-heap [(time, type, civ_id, probe_id)]
    ├─ _handle_probe_arrival()
    │   ├─ Mark star as colonized
    │   ├─ Schedule replication event
    │   └─ Archive probe
    └─ _handle_replication_complete()
        └─ Launch offspring probes to new targets
            └── Schedule new arrival events
    ↓
_archive_completed_probes() [periodic memory management]
    ↓
_apply_hazards()
    ├─ Query SupernovaScheduler for SNe in current window
    ├─ Evaluate GRBs stochastically
    ├─ Check sterilization distances
    └── Mark civilizations as destroyed
    ↓
Advance time: current_time += dt_myr
```

## Adaptive Time Stepping

```
_compute_next_timestep()
    ├─ No active probes → dt = 10 Myr [coarse]
    ├─ Active probes but no arrivals → dt = 100 kyr [medium]
    └─ Probe arrivals/replications pending → dt = 10 kyr [fine]
```

## Civilization Lifecycle

```
Emergence
    ├─ Stellar age ≥ 4 Gyr [min for complex life]
    ├─ Drake equation: f_planets × n_habitable × f_life × f_intel × f_tech
    └── Scale by dt_myr
    ↓
Growth
    ├─ Kardashev advancement: 0.7 → 3.0
    ├─ Rate varies per civilization
    └─ Breakthrough/stagnation periods
    ↓
Expansion (K ≥ 0.85)
    ├─ Lock probe parameters [v, range, offspring, replication_delay]
    ├─ Launch initial probes to nearest metal-rich stars
    ├─ Probe lifecycle:
    │   ├─ Launch → travel → arrival
    │   ├─ Arrive → colonize → schedule replication
    │   └─ Replicate → launch offspring → repeat
    └── Event queue: O(log N) instead of O(N) polling
    ↓
Death
    ├─ Self-destruction [crisis peaks at K=0.72, 0.85, etc.]
    ├─ Age-based extinction [exponential decay]
    ├─ Supernova sterilization [distance-dependent]
    ├─ GRB beam intersection [jet geometry]
    └─ All colonies destroyed = civilization death
```

## Probe Expansion Flow

```
Launch from colony
    ├─ Find targets within per_hop_range_pc
    ├─ Filter: uncolonized + habitable + metallicity_threshold
    ├─ Create ProbeState objects
    ├─ Calculate travel time: distance / (velocity_c × c)
    └── Schedule arrival event in event_queue
    ↓
Probe arrives
    ├─ Mark star as colonized (civ.colonized_stars.add(star_idx))
    ├─ Record arrival_time_myr
    ├─ Calculate replication_time = arrival_time + replication_delay_yr
    ├─ Schedule replication event in event_queue
    └─ Archive probe (move active → archived)
    ↓
Replication complete
    ├─ Find nearest uncolonized targets
    ├─ Launch offspring_count probes
    ├─ Increment probe generation
    └── Schedule new arrival events
```

## Hazard Application Flow

```
_apply_hazards()
    ↓
For each active civilization:
    ├─ Get civ position (home world or colony)
    ├─ Supernova check
    │   ├─ Query spatial index for stars within sterilization_radius_pc [O(log N)]
    │   ├─ Calculate local stellar density
    │   ├─ For each nearby massive star (M > 8 M☉):
    │   │   ├─ Check if star goes SN this timestep (will_go_supernova)
    │   │   ├─ Calculate sterilization probability based on distance
    │   │   ├─ Apply density hazard modifier
    │   │   └─ If sterilized:
    │   │       ├─ Record HazardEvent
    │   │       ├─ Archive to DisasterArchiver
    │   │       ├─ Sterilize star in RecoveryQueue
    │   │       └─ Check distributed resilience:
    │   │           ├─ If no mature colonies → civ extinct
    │   │           └─ Else → civ continues from colonies
    │   └─ Return (destroyed: bool, info: dict)
    └─ GRB check
        ├─ Generate GRB stochastically (metallicity-dependent rate)
        ├─ If GRB generated:
        │   ├─ Random position in galaxy (following massive star distribution)
        │   ├─ Random jet orientation
        │   ├─ Check beam intersection with civ position
        │   ├─ Apply distance-dependent lethal dose
        │   ├─ Record HazardEvent
        │   ├─ Archive to DisasterArchiver
        │   └─ Check distributed resilience (same as SN)
        └─ Return (destroyed: bool, info: dict)
    ↓
Distributed resilience
    ├─ Each colony independently survives hazards
    ├─ p_civ_survives = 1 - ∏(1 - p_colony_survives)
    └─ U-shaped risk: safe at mid-expansion
```

## Parallel Civilization Evolution

```
_evolve_civilizations_parallel()
    ↓
Find causal groups
    ├─ Partition civilizations by spacetime causality
    ├─ Groups with overlapping light cones → sequential
    ├─ Independent groups → parallel
    └── find_causal_groups_with_colonies()
    ↓
Process groups in parallel threads
    ├─ ThreadLocalProbeBuffer for thread-safe probe creation
    ├─ Each thread processes independent civs
    └─ No race conditions (causality guaranteed)
    ↓
Merge results
    └── Single-threaded combine of probe buffers
```

## Data Structures

### GalaxyModel
```python
positions: np.ndarray  # (N, 3) in kpc
velocities: np.ndarray  # (N, 3) in km/s
ages: np.ndarray  # N in Gyr
masses: np.ndarray  # N in M☉
metallicities: np.ndarray  # N in [Fe/H] dex
```

### CivilizationState
```python
civ_id: int
birth_time_myr: float
parent_star_idx: int
colonized_stars: Set[int]  # O(1) lookups
colony_arrival_times: Dict[int, float]
kardashev_scale: float
is_active: bool
active_probes: List[ProbeState]
archived_probes: List[ProbeState]
```

### ProbeState
```python
probe_id: int
parent_probe_id: Optional[int]
generation: int
launch_star_idx: int
target_star_idx: int
launch_time_myr: float
arrival_time_myr: float
velocity_c: float  # locked at launch
per_hop_range_pc: float  # locked at launch
offspring_count: int  # locked at launch
replication_delay_yr: float  # locked at launch
```

### Event Queue
```python
event_queue: List[Tuple[float, str, int, int]]
# (event_time_myr, event_type, civ_id, probe_id)
# Min-heap for O(log N) pop/push
# Event types: 'arrival', 'replication'
```

## Performance Optimizations

1. **Numba JIT** - Rejection sampling for exponential disk (50-100x speedup)
2. **Vectorized emergence** - Batch probability across all stars
3. **Spatial indexing** - KD-tree for O(log N) nearest neighbor queries
4. **Event queue** - Probe processing without polling (10-50x speedup)
5. **Thread-local buffers** - Parallel expansion without locking
6. **Probe archiving** - Periodic cleanup prevents exponential memory growth
7. **Adaptive timestepping** - Fine steps only when needed

## Snapshot Saving

```
_save_snapshot()
    ↓
Create SimulationSnapshot
    ├─ time_myr
    ├─ active_civilizations (count)
    ├─ total_civilizations_ever
    ├─ colonized_systems (count)
    ├─ civilization_states (list of CivilizationState)
    ├─ stellar_positions (NumPy array for visualization)
    ├─ active_probes_in_flight (list of ProbeSnapshot with interpolated positions)
    └─ total_active_probes (count)
    ↓
Save to snapshots list or write to disk
```

**ProbeSnapshot interpolation**:
- Calculate progress_fraction = (current_time - launch_time) / (arrival_time - launch_time)
- Interpolate position: pos = launch_pos + progress × (target_pos - launch_pos)
- Enables smooth visualization of probes in flight

## Key Design Decisions

**Event-driven probe processing**: Replaces O(N) polling with O(log N) event queue. Critical for performance with millions of probes.

**Distributed resilience**: Each colony survives independently. Civilization dies only if ALL colonies die. Creates U-shaped risk curve (safe at mid-expansion).

**Causality-preserving parallelization**: Partition civilizations by causal independence. Groups processed in parallel, no race conditions. Two modes:
- Simple: distance-based partitioning
- With colonies: includes colony overlap in causality check

**Adaptive timestepping**: Dynamically adjust timestep based on simulation state. Fine steps (10 kyr) during probe events, coarse steps (10 Myr) during quiet periods.

**Probe parameter locking**: Once expansion starts, probe capabilities (velocity, range, offspring) are locked based on Kardashev level at launch. Reflects technological lock-in during expansion era.

**Spatial indexing for hazards**: KD-tree queries for nearby stars within sterilization range. O(log N) instead of O(N) distance calculations. 100-1000x speedup on large N.

**Density-dependent hazard modifiers**: Local stellar density affects sterilization probability. Dense regions have more frequent supernovae → cumulative damage multiplier.
