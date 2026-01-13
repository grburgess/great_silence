# Great Silence Code Map

Navigation guide for the GalaticBot Monte Carlo simulation project.

## Module Organization

### `great_silence/`
Root package with main exports: `GalaxySimulation`, `SimulationConfig`, `configure_m1_max_threading`

### `galaxy/` - Galactic structure and stellar evolution
- `structure.py` - 3D galaxy model with bulge/disk components
- `star_formation.py` - Star formation history and initial mass function (IMF)

### `astrophysics/` - Hazards and stellar evolution
- `hazards.py` - Combined hazard evaluation (supernovae, GRBs)
- `supernovae.py` - Supernova rate and sterilization models
- `grb.py` - Gamma-ray burst models with metallicity dependence
- `stellar_evolution.py` - Main sequence lifetime calculations

### `civilization/` - Emergence, expansion, extinction
- `emergence.py` - Drake equation-based civilization emergence
- `expansion.py` - Colonization wave propagation
- `extinction.py` - Self-destruction and age-based extinction models
- `probe_design.py` - Kardashev-scale dependent probe capabilities

### `simulation/` - Engine, Monte Carlo, physics, disasters
- `engine.py` - Core simulation orchestrator (GalaxySimulation class)
- `monte_carlo.py` - Ensemble simulation runner
- `physics.py` - Light travel time calculations
- `disasters/` - High-performance disaster tracking
  - `scheduler.py` - Supernova schedule precomputation
  - `recovery.py` - Sterilization status and recovery tracking
  - `archiver.py` - HDF5 binary encoding for disaster storage
  - `encoding.py` - Binary format for disaster events
  - `spatial_index.py` - Fast spatial queries for hazards

### `visualization/` - Plots, 3D viz, interactive tools
- `galaxy_viz.py` - Static matplotlib visualizations
- `plotly_3d_viz.py` - Interactive 3D visualization
- `interactive_3d.py` - Three.js-based interactive viewer
- `timeline.py` - Temporal visualization of simulation
- `threejs/` - WebGL export infrastructure
  - `data_extractor.py` - Format simulation data for Three.js
  - `html_exporter.py` - Generate standalone HTML files

### `config/` - Parameters and configuration
- `parameters.py` - SimulationConfig and all parameter dataclasses

### `utils/` - Spatial indexing, threading, progress tracking
- `spatial.py` - KD-tree for nearest neighbor queries
- `threading.py` - M1 Max threading optimization
- `progress.py` - Progress tracking with metrics
- `parallel.py` - Causality-preserving parallelization
- `numba_kernels.py` - JIT-compiled kernels for performance

### `notebook/` - Jupyter integration
- `widgets.py` - Interactive widgets for notebooks
- `helpers.py` - Helper functions for analysis
- `runners.py` - Simulation runners for notebooks

## Key Classes

### Simulation Engine (`simulation/engine.py`)
- **GalaxySimulation** (lines 135-1329)
  - Main orchestrator for simulation lifecycle
  - Manages galaxy, civilizations, probes, hazards
  - Implements adaptive time stepping and event queue
  - Supports sequential and parallel civilization evolution

- **ProbeState** (lines 33-57)
  - Single probe with generation tracking
  - Fixed velocity/range locked at launch

- **CivilizationState** (lines 59-91)
  - Complete civilization state
  - Tracks colonies, probes, Kardashev level
  - Supports distributed resilience model

- **SimulationSnapshot** (lines 109-121)
  - Time-slice of simulation for visualization

- **HazardEvent** (lines 123-133)
  - Supernova/GRB event record

### Galaxy Model (`galaxy/structure.py`)
- **GalaxyModel** (lines 8-696)
  - 3D Milky Way-like galaxy
  - Bulge + disk components
  - Gravitational potential (Miyamoto-Nagai + Hernquist + NFW)
  - Exponential/thin-thick disk profiles
  - Spiral arm perturbations
  - Proper stellar kinematics

### Star Formation (`galaxy/star_formation.py`)
- **StarFormationHistory** (lines 8-161)
  - Delayed exponential SFR model
  - Radial age gradient (inside-out formation)
  - Vectorized age generation

- **InitialMassFunction** (lines 163-295)
  - Kroupa, Salpeter, Chabrier IMFs
  - Log-space rejection sampling

### Hazards (`astrophysics/hazards.py`)
- **HazardEvaluator** (lines 10-223)
  - Combined supernova + GRB evaluation
  - Spatial index optimization for O(log N) queries
  - Density-dependent hazard rates

### Extinction Model (`civilization/extinction.py`)
- **ExtinctionModel** (lines 23-410)
  - Kardashev-dependent self-destruction
  - Crisis peaks at specific tech levels
  - Gaussian hazard functions
  - Age-based exponential decay
  - Distributed resilience (multi-colony survival)

- **CrisisPeak** (lines 8-21)
  - Gaussian hazard peak at Kardashev level
  - Six default crises: nuclear, AI, relativistic weapons, etc.

### Probe Design (`civilization/probe_design.py`)
Scaling functions based on Kardashev scale:
- `probe_velocity_from_kardashev()` (lines 9-43)
- `per_hop_range_from_kardashev()` (lines 46-78)
- `offspring_count()` (lines 80-112)
- `replication_delay_years()` (lines 114-153)
- `min_metallicity_for_replication()` (lines 155-203)

### Configuration (`config/parameters.py`)
- **SimulationConfig** (lines 226-342)
  - Main config container with YAML I/O
  - Presets: early_filter, late_filter, rare_earth, optimistic, moderate

- **GalaxyParameters** (lines 8-57)
  - Disk/bulge structure, gradients, kinematics

- **AstrophysicsParameters** (lines 59-79)
  - IMF, supernova/GRB rates

- **CivilizationParameters** (lines 81-176)
  - Drake equation, expansion, self-destruction, Kardashev progression

- **SimulationParameters** (lines 178-225)
  - Time stepping, adaptive stepping, parallelization, output

### Visualization (`visualization/galaxy_viz.py`)
- **GalaxyVisualizer** (lines 9-921)
  - 2D/3D static plots with matplotlib
  - Multiple views: top, side, 3D, density
  - Civilization distribution, age/metallicity gradients
  - Hazard zone mapping with Galactic Habitable Zone (GHZ)

### Disaster Tracking (`simulation/disasters/`)
- **SupernovaScheduler** (disasters/scheduler.py:8-117)
  - Pre-computed SN times with min-heap
  - O(log N) queries for time windows

- **RecoveryQueue** (disasters/recovery.py)
  - Track sterilization status per star
  - Recovery time modeling

- **DisasterArchiver** (disasters/archiver.py)
  - HDF5 binary encoding for disaster events
  - Tiered storage with recent window

- **DisasterSpatialIndex** (disasters/spatial_index.py)
  - Fast spatial queries for hazard evaluation

### Spatial Index (`utils/spatial.py`)
- **SpatialIndex** (lines 8-86)
  - KD-tree wrapper for 3D queries
  - `query_radius()`, `query_nearest()`, `query_pairs()`

## Core Functions

### Simulation Flow (`simulation/engine.py`)
- `initialize()` (lines 261-361) - Set up galaxy and stellar population
- `run()` (lines 438-529) - Main simulation loop with adaptive stepping
- `_step()` (lines 391-436) - Single timestep orchestration
- `_compute_next_timestep()` (lines 362-389) - Adaptive timestep logic

### Civilization Evolution
- `_check_civilization_emergence()` (lines 642-722) - Drake equation emergence
- `_evolve_civilizations_sequential()` (lines 820-924) - Sequential evolution
- `_evolve_civilizations_parallel()` (lines 1075-1137) - Parallel with causality
- `_attempt_expansion()` (lines 925-970) - Self-replicating probe expansion
- `_process_probe_events()` (lines 971-1013) - Event queue processing (10-50x speedup)

### Probe Lifecycle
- `_launch_initial_probes()` (engine.py:965+) - Initial wave from home world
- `_handle_probe_arrival()` (engine.py:1044-1074) - Mark colonization, schedule replication
- `_handle_replication_complete()` (engine.py:1075+) - Launch offspring probes
- `_archive_completed_probes()` (engine.py:1014-1043) - Memory management

### Hazard Application
- `_apply_hazards()` (engine.py:431) - Apply supernovae/GRBs to civilizations
- `evaluate_supernova_hazard()` (hazards.py:26-131) - SN sterilization check
- `evaluate_grb_hazard()` (hazards.py:133-223) - GRB beam intersection check

### Galaxy Generation (`galaxy/structure.py`)
- `generate_stellar_population()` (lines 38-91) - Full population generation
- `_generate_exponential_disk()` (lines 92-146) - Disk positions (Numba-accelerated)
- `_generate_bulge()` (lines 147-188) - Hernquist bulge
- `_apply_spiral_arms()` (lines 212-246) - Spiral arm density waves
- `_generate_velocities()` (lines 288-367) - Equilibrium kinematics
- `evolve_positions()` (lines 593-646) - Leapfrog integrator (experimental)

### Star Properties (`galaxy/star_formation.py`)
- `StarFormationHistory.sfr()` (lines 24-47) - Delayed exponential SFR
- `StarFormationHistory.generate_stellar_ages_with_gradient()` (lines 104-161) - Age gradient
- `InitialMassFunction.sample()` (lines 212-248) - Rejection sampling from IMF

### Extinction Calculations (`civilization/extinction.py`)
- `calculate_kardashev_hazard_rate()` (lines 145-194) - Gaussian crisis peaks
- `check_self_destruction()` (lines 196-239) - Hazard rate to probability
- `check_age_extinction()` (lines 240-267) - Exponential decay

## Data Flow

### Initialization Flow
1. **Config Loading** → SimulationConfig.from_yaml() or defaults
2. **Galaxy Generation** → GalaxyModel.generate_stellar_population()
   - Generates positions (bulge + disk)
   - Assigns velocities from rotation curve
3. **Stellar Properties** → StarFormationHistory + InitialMassFunction
   - Assign ages (with radial gradient)
   - Sample masses from IMF
   - Calculate metallicities (with radial gradient)
4. **Habitability** → Filter by mass range (0.5-1.5 M☉)
5. **Spatial Index** → Build KD-tree for fast queries (if use_numba=True)

### Main Simulation Loop (per timestep)
1. **Evolve Galaxy** → galaxy.evolve_positions(dt_myr)
   - Update stellar positions (if enable_stellar_motion=True)
2. **Check Emergence** → _check_civilization_emergence()
   - Vectorized Drake equation over habitable stars
   - Scale probability by dt_myr
   - Create new CivilizationState objects
3. **Evolve Civilizations** → _evolve_civilizations()
   - **Sequential**: Loop through all civilizations
   - **Parallel**: Partition by causality, process groups in threads
   - For each civ:
     - Advance Kardashev scale (breakthrough/stagnation)
     - Check self-destruction (crisis peaks)
     - Check age-based extinction
     - Attempt expansion (if K ≥ 0.85)
4. **Process Probe Events** → _process_probe_events()
   - Handle arrivals from event queue
   - Handle replication completions
   - Archive completed probes periodically
5. **Apply Hazards** → _apply_hazards()
   - Check supernovae (using SupernovaScheduler)
   - Check GRBs
   - Mark civilizations as destroyed
6. **Advance Time** → current_time_myr += dt_myr
7. **Save Snapshot** → _save_snapshot() (every snapshot_interval_myr)

### Probe Expansion Flow
1. **Expansion Start** (K ≥ 0.85)
   - Lock probe parameters: velocity, range, offspring count, replication delay
   - Store metallicity threshold
2. **Launch Initial Wave**
   - Find nearest metal-rich stars within per_hop_range
   - Create ProbeState objects
   - Schedule arrival events in event_queue
3. **Arrival Event**
   - Mark star as colonized
   - Schedule replication event (arrival_time + replication_delay)
   - Archive probe (move to active_probes → archived_probes)
4. **Replication Event**
   - Find nearest uncolonized targets
   - Launch offspring probes
   - Schedule new arrival events

### Disaster Tracking Flow
1. **Precomputation** → SupernovaScheduler._build_schedule()
   - Calculate main sequence lifetimes for massive stars (M > 8 M☉)
   - Add ages to get SN times
   - Build min-heap of (time, star_idx) pairs
2. **Per Timestep** → _apply_hazards()
   - Query scheduler for SNe in current window
   - Evaluate GRB events stochastically
   - Check sterilization distances
3. **Recovery Tracking** → RecoveryQueue
   - Track sterilization status per star
   - Model recovery time (for emergence re-enabled)

### Monte Carlo Flow
1. **Ensemble Setup** → MonteCarloRunner(config)
2. **Parallel Execution** → run_parallel()
   - Spawn worker processes (one per realization)
   - Each runs independent GalaxySimulation
   - Collect results
3. **Analysis** → analyze_results()
   - Aggregate statistics across realizations
   - Compute mean/std/median/percentiles
   - Generate distribution plots

## Entry Points

### CLI (`cli.py`)
```bash
python -m great_silence --mode single --config config.yaml --visualize
python -m great_silence --mode monte-carlo --quick
```

Main function: `main()` (lines 13-175)
- Parses arguments
- Loads configuration
- Runs single or Monte Carlo simulation
- Generates visualizations

### Library Usage
```python
from great_silence import GalaxySimulation, SimulationConfig

# Create config
config = SimulationConfig.with_preset('moderate')

# Run simulation
sim = GalaxySimulation(config, seed=42)
sim.run(verbose=True)

# Get statistics
stats = sim.get_statistics()
```

### Quick Test
```python
# 10k stars, 1 Gyr
config = SimulationConfig()
config.galaxy.total_stars = 10000
config.simulation.simulation_duration_gyr = 1.0

sim = GalaxySimulation(config)
sim.run()
```

### Examples
- `examples/basic_simulation.py` - Simple single run
- Jupyter notebooks in `notebook/` directory

## Dependencies

### Module Dependency Graph
```
simulation/engine.py
├── config/parameters.py
├── galaxy/structure.py
├── galaxy/star_formation.py
├── civilization/extinction.py
├── civilization/probe_design.py
├── astrophysics/hazards.py
├── utils/progress.py
├── utils/parallel.py
└── simulation/disasters/

galaxy/structure.py
└── config/parameters.py

astrophysics/hazards.py
├── astrophysics/supernovae.py
├── astrophysics/grb.py
└── config/parameters.py

civilization/extinction.py
└── (no external dependencies)

visualization/galaxy_viz.py
└── (matplotlib only, no internal deps)

utils/spatial.py
└── scipy.spatial.cKDTree
```

### Internal Dependencies
- **GalaxyModel** ← GalaxyParameters, SimulationParameters
- **GalaxySimulation** ← All modules (orchestrator)
- **HazardEvaluator** ← SupernovaModel, GRBModel, StellarEvolution
- **ExtinctionModel** ← CivilizationParameters (crisis peaks)
- **GalaxyVisualizer** ← NumPy arrays only (no sim objects)

### External Dependencies
- `numpy` - Vectorized operations
- `scipy.spatial.cKDTree` - Spatial indexing
- `matplotlib` - Static visualization
- `plotly` - Interactive 3D viz
- `tqdm` - Progress bars
- `pyyaml` - Configuration I/O
- `h5py` - Disaster archiving (optional)
- `numba` - JIT compilation (optional, recommended)
- `nbdev` - Jupyter development (dev only)

## Key Design Patterns

### Configuration as Data
- All parameters in dataclasses (GalaxyParameters, etc.)
- YAML serialization/deserialization
- Presets for common scenarios

### Event-Driven Probe Processing
- Min-heap event queue for probe arrivals/replications
- Replaces O(N_probes) polling with O(log N) event processing
- 10-50x speedup for expansion-heavy scenarios

### Causality-Preserving Parallelization
- Partition civilizations by causal independence
- Groups processed in parallel (no race conditions)
- Thread-local buffers for probe creation
- Single-threaded merge step

### Spatial Indexing
- KD-tree for nearest neighbor queries
- O(log N) instead of O(N) for hazard evaluation
- Used in supernova checks, expansion targeting

### Adaptive Time Stepping
- Fine steps (10 kyr) during probe events
- Medium steps (100 kyr) with active civilizations
- Coarse steps (10 Myr) during quiet periods

### Distributed Resilience Model
- Each colony independently survives hazards
- Civilization dies only if ALL colonies die
- Probability: p_total = p_single^N_colonies
- Creates U-shaped risk curve (safe at mid-expansion)

## Performance Optimizations

1. **Numba JIT Kernels** - Rejection sampling for exponential disk (50-100x speedup)
2. **Vectorized Emergence** - Batch probability calculation across stars
3. **Spatial Index** - O(log N) hazard queries instead of O(N)
4. **Event Queue** - Probe processing without polling
5. **Thread-Local Buffers** - Parallel expansion without locking
6. **Binary Disaster Encoding** - Compact HDF5 storage
7. **Probe Archiving** - Prevents exponential memory growth

## Incomplete Features

See `AGENTS.md` "Incomplete features requiring enhancement":
- Expansion wavefront with light cones (currently branching tree)
- Light travel time enforcement in expansion logic
- Hazard application (call to HazardEvaluator in engine)
- Numba optimization for hot loops
- Mid-flight retargeting (disabled due to O(N) brute force)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=great-silence --cov-report=html

# Specific test
pytest tests/test_galaxy.py::TestGalaxyModel::test_generation
```

See `AGENTS.md` for full testing commands.
