# Great Silence Code Map

Navigation guide for the GalaticBot Monte Carlo simulation of intelligent life in a Milky Way-like galaxy.

## Quick Start

```python
from great_silence import GalaxySimulation, SimulationConfig

config = SimulationConfig.with_preset('moderate')
sim = GalaxySimulation(config, seed=42)
sim.run(verbose=True)
stats = sim.get_statistics()
```

## Module Organization

### `great_silence/` (root)
Main exports: `GalaxySimulation`, `SimulationConfig`, `configure_m1_max_threading`

### `galaxy/` - Galactic structure and stellar populations
| File | Lines | Description |
|------|-------|-------------|
| `structure.py` | 695 | 3D galaxy model with bulge/disk components, gravitational potential |
| `star_formation.py` | 295 | Star formation history and initial mass function (IMF) |

### `astrophysics/` - Hazards and stellar evolution
| File | Lines | Description |
|------|-------|-------------|
| `hazards.py` | 222 | Combined hazard evaluation (supernovae, GRBs) |
| `supernovae.py` | 223 | Supernova rate and sterilization models |
| `grb.py` | 167 | Gamma-ray burst models with metallicity dependence |
| `stellar_evolution.py` | 25 | Main sequence lifetime calculations |

### `civilization/` - Emergence, expansion, extinction, interactions
| File | Lines | Description |
|------|-------|-------------|
| `emergence.py` | 77 | Drake equation-based civilization emergence |
| `expansion.py` | 118 | Colonization wave propagation |
| `extinction.py` | 409 | Self-destruction and age-based extinction models |
| `probe_design.py` | 207 | Kardashev-scale dependent probe capabilities |
| `personality.py` | 211 | Civilization personality modeling with evolution |
| `war.py` | 338 | War mechanics with fleet tracking and causal communication |

### `simulation/` - Engine, Monte Carlo, physics
| File | Lines | Description |
|------|-------|-------------|
| `engine.py` | 2601 | Core simulation orchestrator (GalaxySimulation class) |
| `monte_carlo.py` | 148 | Ensemble simulation runner |
| `physics.py` | 104 | Light travel time calculations |

### `simulation/disasters/` - High-performance disaster tracking
| File | Lines | Description |
|------|-------|-------------|
| `scheduler.py` | 116 | Supernova schedule precomputation with min-heap |
| `recovery.py` | 142 | Sterilization status and recovery tracking |
| `archiver.py` | 205 | HDF5 binary encoding for disaster storage |
| `encoding.py` | 185 | Binary format for disaster events |
| `spatial_index.py` | 163 | Fast spatial queries for hazards |

### `visualization/` - Plots, 3D viz, interactive tools
| File | Lines | Description |
|------|-------|-------------|
| `galaxy_viz.py` | 920 | Static matplotlib visualizations |
| `plotly_3d_viz.py` | 789 | Interactive 3D Plotly visualization |
| `interactive_3d.py` | 868 | Three.js-based interactive viewer |
| `timeline.py` | 237 | Temporal visualization of simulation |
| `sphere_builder.py` | 157 | Civilization influence zone spheres |
| `trajectory_builder.py` | 169 | Expansion trajectory lines |

### `visualization/threejs/` - WebGL export infrastructure
| File | Lines | Description |
|------|-------|-------------|
| `config.py` | 128 | Central Three.js visualization configuration |
| `data_extractor.py` | - | Format simulation data for Three.js |
| `html_exporter.py` | - | Generate standalone HTML files |
| `mock_data_generator.py` | 189 | Mock data for template testing |
| `templates/` | 9 files | Jinja2 templates for JS components |

### `config/` - Parameters and configuration
| File | Lines | Description |
|------|-------|-------------|
| `parameters.py` | 391 | SimulationConfig and all parameter dataclasses |

### `utils/` - Spatial indexing, threading, progress
| File | Lines | Description |
|------|-------|-------------|
| `spatial.py` | 85 | KD-tree for nearest neighbor queries |
| `civ_spatial_index.py` | 318 | Civilization territory overlap detection |
| `threading.py` | 236 | M1 Max threading optimization |
| `progress.py` | 172 | Progress tracking with metrics |
| `parallel.py` | 227 | Causality-preserving parallelization |
| `numba_kernels.py` | 598 | JIT-compiled kernels for performance |

### `notebook/` - Jupyter integration
| File | Description |
|------|-------------|
| `widgets.py` | Interactive widgets for notebooks |
| `helpers.py` | Helper functions for analysis |
| `runners.py` | Simulation runners for notebooks |

---

## Key Classes

### GalaxySimulation (`simulation/engine.py:234`)
Main orchestrator for simulation lifecycle (2601 lines).

**Core Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `__init__()` | 242 | Initialize simulation with config and seed |
| `initialize()` | 366 | Set up galaxy and stellar population |
| `run()` | 550 | Main simulation loop with adaptive stepping |
| `_step()` | 488 | Single timestep orchestration |
| `_compute_next_timestep()` | 459 | Adaptive timestep logic |
| `get_statistics()` | 2133 | Return summary statistics |

**Civilization Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_check_civilization_emergence()` | 747 | Drake equation emergence |
| `_evolve_civilizations_sequential()` | 947 | Sequential evolution |
| `_evolve_civilizations_parallel()` | 1230 | Parallel with causality |
| `_advance_civilization_tech()` | 1294 | Kardashev progression |
| `_check_civilization_extinction()` | 1319 | Check self-destruction |

**Probe Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_attempt_expansion()` | 1056 | Initiate probe expansion |
| `_process_probe_events()` | 1102 | Event queue processing |
| `_launch_initial_probes()` | 1516 | Initial wave from home world |
| `_launch_offspring_probes()` | 1563 | Spawn from arrived probe |
| `_handle_probe_arrival()` | 1175 | Mark colonization, schedule replication |
| `_handle_replication_complete()` | 1504 | Launch offspring probes |
| `_find_nearest_targets()` | 1610 | Find colonization targets |
| `_archive_completed_probes()` | 1145 | Memory management |

**War/Encounter Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_scan_for_encounters()` | 2146 | Detect civilization encounters |
| `_handle_encounter()` | 2176 | Process encounter event |
| `_start_war()` | 2257 | Initiate war between civilizations |
| `_resolve_wars()` | 2316 | Resolve ongoing wars |
| `_resolve_battle_at_star()` | 2365 | Battle resolution |
| `_end_war()` | 2490 | Conclude war |
| `_form_alliance()` | 2530 | Alliance formation |

**Hazard Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_apply_hazards()` | 1814 | Apply supernovae/GRBs |
| `_interpolate_probe_positions()` | 1965 | Probes in flight for viz |
| `_save_snapshot()` | 2028 | Save simulation state |

### Supporting Data Classes (`simulation/engine.py`)
| Class | Line | Description |
|-------|------|-------------|
| `ProbeState` | 54 | Single probe with generation tracking |
| `EncounterEvent` | 80 | Record of civilization encounter |
| `CivilizationState` | 93 | Complete civilization state |
| `HazardEvent` | 169/181 | Supernova/GRB event record |
| `ProbeSnapshot` | 193 | Probe state for visualization |
| `SimulationSnapshot` | 209 | Time-slice for visualization |

### GalaxyModel (`galaxy/structure.py:8`)
3D Milky Way-like galaxy model (695 lines).

**Key Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `generate_stellar_population()` | 38 | Full population generation |
| `_generate_exponential_disk()` | 92 | Disk positions (Numba-accelerated) |
| `_generate_bulge()` | 147 | Hernquist bulge |
| `_generate_double_exponential_disk()` | 189 | Thin+thick disk |
| `_apply_spiral_arms()` | 212 | Spiral arm density waves |
| `_generate_velocities()` | 288 | Equilibrium kinematics |
| `_compute_circular_velocity()` | 247 | Rotation curve |
| `calculate_metallicities()` | 368 | Metallicity gradient |
| `evolve_positions()` | 593 | Leapfrog integrator |
| `get_distance_matrix()` | 647 | Pairwise distances |
| `get_stellar_density()` | 672 | Local density |

**Gravitational Potential:**
| Method | Line | Description |
|--------|------|-------------|
| `_compute_disk_acceleration()` | 402 | Miyamoto-Nagai disk |
| `_compute_bulge_acceleration()` | 470 | Hernquist bulge |
| `_compute_halo_acceleration()` | 525 | NFW dark matter halo |
| `_compute_gravitational_acceleration()` | 569 | Combined potential |

### Star Formation (`galaxy/star_formation.py`)
| Class | Line | Description |
|-------|------|-------------|
| `StarFormationHistory` | 8 | Delayed exponential SFR model |
| `InitialMassFunction` | 163 | Kroupa, Salpeter, Chabrier IMFs |

**StarFormationHistory Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `sfr()` | 24 | Delayed exponential SFR |
| `cumulative_stellar_mass()` | 49 | Integrated stellar mass |
| `generate_stellar_ages()` | 73 | Age sampling |
| `generate_stellar_ages_with_gradient()` | 104 | Radial age gradient |

**InitialMassFunction Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `pdf()` | 179 | IMF probability density |
| `sample()` | 212 | Rejection sampling from IMF |
| `mean_mass()` | 250 | Average stellar mass |
| `fraction_above_mass()` | 272 | Massive star fraction |

### ExtinctionModel (`civilization/extinction.py:23`)
Kardashev-dependent extinction with crisis peaks (409 lines).

| Class | Line | Description |
|-------|------|-------------|
| `CrisisPeak` | 9 | Gaussian hazard peak definition |
| `ExtinctionModel` | 23 | Main extinction model |

**Key Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `_create_default_crisis_peaks()` | 93 | Six default crises |
| `calculate_kardashev_hazard_rate()` | 145 | Gaussian crisis peaks |
| `check_self_destruction()` | 196 | Hazard rate to probability |
| `check_age_extinction()` | 240 | Exponential decay |
| `survival_probability()` | 268 | Distributed resilience |
| `get_crisis_info()` | 304 | Crisis configuration |
| `set_crisis_amplitude()` | 321 | Modify crisis severity |
| `enable_crisis()` | 340 | Toggle crisis |
| `plot_hazard_function()` | 357 | Visualize hazard curve |

### HazardEvaluator (`astrophysics/hazards.py:10`)
Combined supernova + GRB evaluation (222 lines).

| Method | Line | Description |
|--------|------|-------------|
| `evaluate_supernova_hazard()` | 26 | SN sterilization check |
| `evaluate_grb_hazard()` | 133 | GRB beam intersection check |

### Probe Design (`civilization/probe_design.py`)
Scaling functions based on Kardashev scale.

| Function | Line | Description |
|----------|------|-------------|
| `probe_velocity_from_kardashev()` | 9 | Velocity scaling (0.001c-0.5c) |
| `per_hop_range_from_kardashev()` | 46 | Range scaling (1-100 pc) |
| `offspring_count()` | 80 | Replication count (1-8) |
| `replication_delay_years()` | 114 | Build time (100k-10k yr) |
| `min_metallicity_for_replication()` | 155 | Metallicity threshold |

### Personality System (`civilization/personality.py`)
Civilization behavior modeling.

| Class/Function | Line | Description |
|----------------|------|-------------|
| `PersonalityState` | 9 | Dynamic personality state |
| `sample_personality()` | 20 | K-dependent personality sampling |
| `evolve_personality()` | 102 | War outcome personality drift |
| `get_colony_personality_modifier()` | 178 | Colony-specific modifiers |

**Personality Types:**
- `expansionist` (friendliness < 0.3)
- `defensive` (0.3-0.5)
- `isolationist` (0.5-0.7)
- `xenophile` (> 0.7)

### War System (`civilization/war.py`)
Fleet tracking and causal communication (338 lines).

| Class | Line | Description |
|-------|------|-------------|
| `BattleOutcome` | 9 | Enum: attacker/defender/stalemate/mutual |
| `WarPhase` | 18 | Enum: mobilization/offensive/stalemate/peace/concluded |
| `FleetState` | 28 | Military fleet state |
| `BattleEvent` | 46 | Battle record |
| `WarState` | 62 | Ongoing war state |
| `CommunicationEvent` | 81 | Light-cone constrained messaging |
| `VassalState` | 94 | Vassal relationship |

| Function | Line | Description |
|----------|------|-------------|
| `calculate_fleet_strength()` | 104 | K-dependent fleet power |
| `calculate_colony_strength()` | 131 | Colony defense |
| `resolve_battle()` | 158 | Battle resolution |
| `calculate_war_duration()` | 227 | Expected war length |
| `calculate_light_cone_arrival()` | 255 | Causal message delay |
| `is_communication_possible()` | 279 | Check light-cone causality |
| `check_alliance_cascade_light_cone()` | 300 | Ally join eligibility |

### Configuration (`config/parameters.py`)
| Class | Line | Description |
|-------|------|-------------|
| `GalaxyParameters` | 9 | Disk/bulge structure, gradients |
| `AstrophysicsParameters` | 60 | IMF, supernova/GRB rates |
| `CivilizationParameters` | 82 | Drake equation, expansion, Kardashev |
| `SimulationParameters` | 227 | Time stepping, parallelization |
| `SimulationConfig` | 277 | Main config container with YAML I/O |

**SimulationConfig Presets:**
- `early_filter` - Rare emergence, high extinction
- `late_filter` - Common emergence, high extinction
- `rare_earth` - Very rare emergence
- `optimistic` - Abundant emergence, low extinction
- `moderate` - Balanced parameters

### Monte Carlo (`simulation/monte_carlo.py`)
| Class | Line | Description |
|-------|------|-------------|
| `MonteCarloRunner` | 12 | Ensemble simulation runner |

| Method | Line | Description |
|--------|------|-------------|
| `run_single_realization()` | 27 | Single simulation run |
| `run_parallel()` | 50 | ProcessPoolExecutor parallelization |
| `run_sequential()` | 77 | Sequential (debugging) |
| `analyze_results()` | 95 | Statistics with 95% CI |

### Spatial Indexing (`utils/spatial.py:8`, `utils/civ_spatial_index.py:21`)
| Class | Line | File | Description |
|-------|------|------|-------------|
| `SpatialIndex` | 8 | spatial.py | KD-tree wrapper |
| `CivilizationSpatialIndex` | 21 | civ_spatial_index.py | Territory overlap detection |
| `ColonyInfo` | 9 | civ_spatial_index.py | Colony metadata |

**SpatialIndex Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `query_radius()` | 25 | Stars within radius |
| `query_nearest()` | 56 | k-nearest neighbors |
| `query_pairs()` | 74 | All pairs within distance |

**CivilizationSpatialIndex Methods:**
| Method | Line | Description |
|--------|------|-------------|
| `add_colony()` | 43 | Register colony |
| `remove_colony()` | 76 | Unregister colony |
| `find_civilizations_in_range()` | 105 | Civs near star |
| `find_territory_overlaps()` | 129 | All overlapping pairs |
| `find_nearby_enemy_colonies()` | 181 | Enemy detection |
| `get_frontier_colonies()` | 229 | Border colonies |
| `find_path_between_colonies()` | 263 | BFS pathfinding |

### Disaster Tracking (`simulation/disasters/`)
| Class | Line | File | Description |
|-------|------|------|-------------|
| `SupernovaScheduler` | 8 | scheduler.py | Pre-computed SN times (min-heap) |
| `SterilizationStatus` | 8 | recovery.py | Star sterilization state |
| `RecoveryQueue` | 16 | recovery.py | Recovery time modeling |
| `DisasterArchiver` | 21 | archiver.py | HDF5 binary encoding |
| `DisasterSpatialIndex` | 13 | spatial_index.py | Fast hazard queries |

### Visualization Classes
| Class | Line | File | Description |
|-------|------|------|-------------|
| `GalaxyVisualizer` | 9 | galaxy_viz.py | Matplotlib 2D/3D plots |
| `VisualizationConfig` | 21 | plotly_3d_viz.py | Plotly config |
| `ColorMapper` | 72 | plotly_3d_viz.py | Civ-to-color mapping |
| `Plotly3DGalaxyViz` | 219 | plotly_3d_viz.py | Interactive 3D Plotly |
| `SphereBuilder` | 9 | sphere_builder.py | Influence zone spheres |
| `TrajectoryBuilder` | 8 | trajectory_builder.py | Expansion lines |
| `ThreeJSConfig` | 8 | threejs/config.py | WebGL configuration |

### Progress Tracking (`utils/progress.py`)
| Class | Line | Description |
|-------|------|-------------|
| `ProgressMetrics` | 8 | Simulation metrics dataclass |
| `ProgressTracker` | 33 | Abstract base class |
| `TqdmProgressTracker` | 66 | Terminal progress bar |
| `JupyterProgressTracker` | 92 | Notebook progress widget |
| `create_progress_tracker()` | 126 | Factory function |

### Parallelization (`utils/parallel.py`)
| Class/Function | Line | Description |
|----------------|------|-------------|
| `ThreadLocalProbeBuffer` | 10 | Thread-safe probe buffer |
| `compute_light_travel_distance()` | 24 | Distance light travels in dt |
| `find_causal_groups_simple()` | 38 | Distance-based partitioning |
| `find_causal_groups_with_colonies()` | 104 | Includes colony overlap |
| `should_use_parallelization()` | 187 | Decision heuristic |

### Numba Kernels (`utils/numba_kernels.py`)
JIT-compiled performance kernels (598 lines).

| Function | Line | Description |
|----------|------|-------------|
| `evolve_positions_numba()` | 33 | Position integration |
| `evolve_positions_inplace_numba()` | 72 | In-place version |
| `compute_distances_to_point_numba()` | 102 | Vectorized distances |
| `find_nearby_mask_numba()` | 132 | Boolean mask for radius |
| `find_nearby_indices_numba()` | 169 | Index array for radius |
| `compute_supernova_rates_numba()` | 228 | SN rate calculation |
| `evaluate_supernova_destruction_vectorized()` | 270 | Vectorized SN hazard |
| `rejection_sample_exponential_disk_radii()` | 345 | Fast disk sampling |
| `compute_circular_velocities()` | 398 | Rotation curve |
| `count_within_radius()` | 471 | Neighbor counting |
| `benchmark_kernel()` | 517 | Kernel benchmarking |

---

## Data Flow

### Initialization Flow
```
SimulationConfig (YAML or preset)
    ↓
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
Initialize disaster tracking (if enabled)
    ├── SupernovaScheduler._build_schedule() [precompute SN times]
    ├── RecoveryQueue for sterilization tracking
    └── DisasterArchiver for HDF5 binary encoding
    ↓
SpatialIndex.build() [KD-tree for O(log N) queries]
    ↓
ExtinctionModel with crisis peaks
```

### Main Simulation Loop
```
while current_time < duration:
    ├── _compute_next_timestep() [adaptive: 10kyr-10Myr]
    ├── _step(dt_myr)
    │   ├── galaxy.evolve_positions(dt_myr) [if motion enabled]
    │   ├── _check_civilization_emergence()
    │   ├── _evolve_civilizations()
    │   │   ├── Advance Kardashev scale
    │   │   ├── Check self-destruction
    │   │   ├── Check age extinction
    │   │   └── Attempt expansion (K ≥ 0.85)
    │   ├── _process_probe_events() [event queue]
    │   ├── _scan_for_encounters() [if enabled]
    │   ├── _resolve_wars(dt_myr) [if ongoing]
    │   ├── _apply_hazards()
    │   └── _save_snapshot() [periodic]
    └── Update progress
```

### Probe Expansion Flow
```
Expansion Start (K ≥ 0.85)
    ├── Lock probe parameters [v, range, offspring, delay]
    └── _launch_initial_probes()
        ├── Find targets within per_hop_range_pc
        ├── Create ProbeState objects
        └── Schedule arrival events
            ↓
Arrival Event (_handle_probe_arrival)
    ├── Mark star colonized
    ├── Schedule replication event
    └── Archive probe
        ↓
Replication Event (_handle_replication_complete)
    ├── _launch_offspring_probes()
    │   ├── Find uncolonized targets
    │   └── Schedule arrival events
    └── Repeat...
```

### Civilization Lifecycle
```
Emergence → Growth → Expansion → Death

Emergence:
    ├── Stellar age ≥ 4 Gyr
    ├── Drake: f_planets × n_habitable × f_life × f_intel × f_tech
    └── Scale by dt_myr

Growth:
    ├── Kardashev advancement: 0.7 → 3.0
    ├── Rate varies per civilization
    └── Breakthrough/stagnation periods

Expansion (K ≥ 0.85):
    ├── Self-replicating probes
    ├── Event-driven O(log N) processing
    └── Distributed colony network

Death:
    ├── Self-destruction [crisis peaks at K=0.72, 0.85, etc.]
    ├── Age-based extinction [exponential decay]
    ├── Supernova sterilization [distance-dependent]
    ├── GRB beam intersection [jet geometry]
    ├── War defeat [territory loss]
    └── All colonies destroyed = civilization death
```

### War Flow (if encounters enabled)
```
_scan_for_encounters()
    ├── Find civilizations with overlapping territories
    └── Generate EncounterEvent
        ↓
_handle_encounter()
    ├── Check personality compatibility
    ├── Calculate war probability
    └── Either _start_war() or _form_alliance()
        ↓
_resolve_wars(dt_myr) [each timestep]
    ├── _resolve_battle_at_star()
    │   ├── Calculate fleet strengths
    │   ├── Apply tech advantage
    │   └── Determine casualties
    ├── Update war exhaustion
    └── Check surrender conditions
        ↓
_end_war()
    ├── Transfer territory
    ├── Evolve personalities
    └── Record outcome
```

---

## Performance Optimizations

1. **Numba JIT Kernels** - 50-100x speedup for hot loops
2. **Vectorized Emergence** - Batch probability across all stars
3. **Spatial Index** - O(log N) hazard queries (KD-tree)
4. **Event Queue** - Probe processing without O(N) polling (10-50x)
5. **Thread-Local Buffers** - Parallel expansion without locking
6. **Binary Disaster Encoding** - Compact HDF5 storage
7. **Probe Archiving** - Prevents exponential memory growth
8. **Adaptive Timestepping** - Fine steps only when needed
9. **Causality Partitioning** - Safe parallel civ evolution

### Adaptive Timestep Logic
```
No active probes       → dt = 10 Myr   [coarse]
Active probes, no events → dt = 100 kyr [medium]
Probe events pending   → dt = 10 kyr   [fine]
```

---

## Key Design Patterns

### Configuration as Data
- All parameters in dataclasses
- YAML serialization/deserialization
- Presets for common scenarios

### Event-Driven Probe Processing
- Min-heap event queue for arrivals/replications
- Replaces O(N) polling with O(log N) event processing

### Causality-Preserving Parallelization
- Partition civilizations by causal independence
- Groups processed in parallel, no race conditions
- Thread-local buffers for probe creation

### Distributed Resilience Model
- Each colony independently survives hazards
- Civilization dies only if ALL colonies die
- p_total = p_single^N_colonies
- Creates U-shaped risk curve (safe at mid-expansion)

### Probe Parameter Locking
- Once expansion starts, probe capabilities locked
- Based on Kardashev level at launch time
- Reflects technological lock-in during expansion

---

## Entry Points

### CLI
```bash
python -m great_silence --mode single --config config.yaml --visualize
python -m great_silence --mode monte-carlo --quick
```

### Library
```python
from great_silence import GalaxySimulation, SimulationConfig

config = SimulationConfig.with_preset('moderate')
sim = GalaxySimulation(config, seed=42)
sim.run(verbose=True)
stats = sim.get_statistics()
```

### Examples
- `examples/basic_simulation.py` - Simple single run
- `examples/enhanced_simulation.py` - Full features
- `notebooks/` - Jupyter integration

---

## Dependencies

### External
| Package | Purpose |
|---------|---------|
| `numpy` | Vectorized operations |
| `scipy.spatial.cKDTree` | Spatial indexing |
| `matplotlib` | Static visualization |
| `plotly` | Interactive 3D viz |
| `tqdm` | Progress bars |
| `pyyaml` | Configuration I/O |
| `h5py` | Disaster archiving (optional) |
| `numba` | JIT compilation (optional, recommended) |
| `colorcet` | Color palettes |
| `jinja2` | Template rendering |

### Internal Dependency Graph
```
simulation/engine.py
├── config/parameters.py
├── galaxy/structure.py
├── galaxy/star_formation.py
├── civilization/extinction.py
├── civilization/probe_design.py
├── civilization/personality.py
├── civilization/war.py
├── astrophysics/hazards.py
├── utils/progress.py
├── utils/parallel.py
├── utils/civ_spatial_index.py
└── simulation/disasters/

galaxy/structure.py
└── config/parameters.py

astrophysics/hazards.py
├── astrophysics/supernovae.py
├── astrophysics/grb.py
└── config/parameters.py

visualization/*
└── (matplotlib/plotly/jinja2 only)
```

---

## Testing

```bash
pytest                                    # All tests
pytest --cov=great-silence --cov-report=html  # With coverage
pytest tests/test_galaxy.py               # Specific file
pytest tests/test_galaxy.py::TestGalaxyModel::test_generation  # Specific test
```

---

## Common Pitfalls

1. **Unit confusion**: Always check units
   - Distances: kpc (galaxy), pc (stellar)
   - Time: Gyr (ages), Myr (timesteps), yr (light travel)
   - Velocity: km/s (stellar), fraction of c (probes)

2. **Time step scaling**: Probabilities MUST scale by dt_myr
   ```python
   p_event = base_rate_per_myr * dt_myr  # Correct
   ```

3. **Random seeds**: Pass seed to all RNG creation
   ```python
   rng = np.random.default_rng(seed)
   ```

4. **Array copying**: Be explicit about views vs copies
   ```python
   positions_copy = self.positions.copy()
   ```

5. **Distance matrix memory**: Don't compute O(N²) for large N
   ```python
   # Use spatial index instead
   spatial_index = SpatialIndex(pos)
   nearby = spatial_index.query_radius(center, radius)
   ```

---

## Incomplete Features

See `AGENTS.md` for details:
- Expansion wavefront with light cones
- Light travel time enforcement in expansion
- Mid-flight probe retargeting (disabled)
- Additional Numba optimization opportunities
