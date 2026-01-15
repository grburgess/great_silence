# AGENTS.md

## Setup commands

Any useful mistakes made or confusions corrected, document at the end of AGENTS.md. Always add, never delete. Be concise.

Refer to the code_map directory for information on the structure of the coding project


```bash
# Always run python with micromamba environment galaticbot


# Install in development mode
pip install -e .

# Install with all dependencies (dev + visualization)
pip install -e ".[dev,viz]"
```

## Running simulations
```bash
# Run basic example
python examples/basic_simulation.py

# Run with custom configuration
python -c "from great_silence import GalaxySimulation, SimulationConfig; \
           config = SimulationConfig(); \
           sim = GalaxySimulation(config); \
           sim.run()"

# Quick test simulation (10k stars, 1 Gyr)
python -c "from great_silence import GalaxySimulation, SimulationConfig; c = SimulationConfig(); c.galaxy.total_stars = 10000; c.simulation.simulation_duration_gyr = 1.0; s = GalaxySimulation(c); s.run()"
```

## Testing commands
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=great-silence --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/test_galaxy.py

# Run specific test
pytest tests/test_galaxy.py::TestGalaxyModel::test_generation
```

## Code quality
```bash
# Format code (auto-fix)
black src/ tests/ examples/

# Lint code
ruff check src/ tests/ examples/

# Type checking
mypy src/

# Run all quality checks
black src/ tests/ && ruff check src/ tests/ && mypy src/
```

## Three.js visualization
```bash
# Export interactive HTML with all features
python -c "
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs import export_html

config = SimulationConfig()
config.simulation.save_snapshots = True
sim = GalaxySimulation(config)
sim.initialize()
sim.run()
export_html(sim, 'visualization.html', animated=True)
"

# Open in browser
open visualization.html
```

## Code style
- Module files: lowercase with underscores (`star_formation.py`)
- Classes: PascalCase (`GalaxyModel`, `SimulationConfig`)
- Functions/methods: lowercase with underscores (`generate_stellar_population()`)
- Constants: UPPERCASE with underscores (`C_PC_YR`)
- Private methods: leading underscore (`_apply_hazards()`)
- Line length: 100 characters (Black default)
- Always follow existing patterns in codebase
- NO COMMENTS unless explicitly asked
- Store documentation about changes in `claude_comments/` folder, NOT in `src/`

## Code style consistency
- ALWAYS respect how things are written in existing project
- DO NOT invent own approaches or innovations
- STRICTLY follow existing style of tests, resolvers, functions, arguments
- Before creating new file, ALWAYS examine similar file and follow its style exactly

## Architecture

### Module organization
`src/great-silence/` modules:
- `galaxy/` - Galactic structure, stellar positions, star formation (evolve_positions key)
- `astrophysics/` - Hazards (supernovae, GRBs), distance-dependent destruction
- `civilization/` - Emergence (Drake eq), expansion, extinction (all probs scaled by dt_myr)
- `simulation/` - Main engine, Monte Carlo, physics (light travel time)
- `visualization/` - Plots, animations (uses matplotlib, stellar positions as (N,3) arrays)
- `config/` - SimulationConfig dataclass, YAML serialization
- `utils/` - Spatial indexing (KD-tree for nearest neighbor queries)

### Data flow
1. Initialization: Generate stars from density profile, assign ages/masses, identify habitable (0.5-1.5 M☉)
2. Main loop: Evolve positions by dt_myr, check emergence, evolve civilizations, apply hazards, save snapshots
3. Civilization lifecycle: Birth (probabilistic), Growth (expansion), Death (self-destruction/age/hazard)
4. Monte Carlo: Run N realizations, aggregate statistics

### Key design patterns
- Separation of Concerns: Each module single responsibility
- Configuration as Data: All params in SimulationConfig dataclass
- Vectorized Operations: Use NumPy, avoid Python loops over stars
- Lazy Initialization: Build expensive structures on-demand
- Snapshot System: Periodic serialization to SimulationSnapshot

### Performance considerations
Critical paths: position evolution, nearest neighbor queries, hazard evaluation, distance matrix

Optimize with: Numba @jit, NumPy vectorization, spatial indexing (KD-tree), chunking, parallel Monte Carlo

Bottlenecks: get_distance_matrix O(N²), emergence checks all stars, expansion needs wavefront

## Implementation guidelines

### Adding new astrophysical hazard
1. Create model class in `src/great-silence/astrophysics/your_hazard.py`
2. Implement rate/probability and lethal range
3. Add to `HazardEvaluator` in `astrophysics/hazards.py`
4. Add config params to `AstrophysicsParameters` in `config/parameters.py`
5. Call from `GalaxySimulation._apply_hazards()` in `simulation/engine.py`

### Adding new civilization behavior
1. Add model to appropriate file in `civilization/`
2. Add config params to `CivilizationParameters`
3. Integrate into `GalaxySimulation._evolve_civilizations()`

### Adding new visualization
1. Add method to `GalaxyVisualizer` or `TimelineAnimator`
2. Accept NumPy arrays, not simulation objects
3. Use `save_path` for optional file output
4. Set `facecolor='black'`

## Common pitfalls

1. **Unit confusion**: Always document units in docstrings
   - Distances: kpc (galaxy positions), pc (stellar distances)
   - Time: Gyr (ages), Myr (time steps), yr (light travel)
   - Velocity: km/s (stellar motion), fraction of c (expansion)

2. **Time step scaling**: Probabilities MUST be scaled by `dt_myr`
   ```python
   p_event = base_rate_per_myr * dt_myr  # Correct
   ```

3. **Random seeds**: Pass `seed` to all RNG creation
   ```python
   rng = np.random.default_rng(seed)  # Good
   ```

4. **Array copying**: Be explicit about views vs copies
   ```python
   positions_copy = self.positions.copy()  # Explicit copy
   ```

5. **Distance matrix memory**: Don't compute O(N²) matrices for large N
   ```python
   # Use spatial index instead
   spatial_index = SpatialIndex(pos)
   nearby_indices = spatial_index.query_radius(center, radius)
   ```

6. **SN time calculation**: Time until SN is `t_ms - age`, NOT `age + t_ms`
   ```python
   t_ms_gyr = 10.0 * mass ** (-2.5)  # Main sequence lifetime
   time_until_sn = t_ms_gyr - age_gyr  # Negative = already dead
   ```

## Incomplete features requiring enhancement

1. **Expansion model** (`civilization/expansion.py`): Needs wavefront propagation with light cones, track launch/arrival times
2. **Light travel time** (`simulation/physics.py`): Enforce causality in expansion logic
3. ~~**Hazard application** (`simulation/engine.py:_apply_hazards()`): Actually call HazardEvaluator~~ ✅ DONE (Jan 2026)
4. ~~**Spatial optimization** (`simulation/engine.py`): Use SpatialIndex for O(log N) queries~~ ✅ Done via UnifiedDisasterScheduler
5. ~~**Numba optimization**: Add @jit decorators to hot loops~~ ✅ Done (batch disaster kernels, hazard kernels)
6. ~~**Precomputed disaster schedule**: Generate all SN/GRB/NS events at init~~ ✅ DONE (Jan 2026)

## When making changes
1. Maintain physical units, document in docstrings
2. Preserve reproducibility, use seeded RNGs
3. Optimize carefully: profile first, vectorize before Numba
4. Test thoroughly, ensure existing tests pass
5. Update documentation

## Profile performance
```bash
python -m cProfile -o profile.stats examples/basic_simulation.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

## Load and inspect configuration
```bash
python -c "from great_silence import SimulationConfig; c = SimulationConfig(); print(c.to_dict())"
```

## Session Notes / Learnings

### Jan 2026 - NS Merger Implementation
- Added `NeutronStarMergerModel` in `astrophysics/neutron_star_merger.py`
- NS mergers produce: sGRB (beamed, ~kpc lethal), kilonova (~30pc lethal)
- Config params: `ns_merger_rate_per_myr`, `ns_sgrb_beaming_angle_deg`, `ns_sgrb_lethal_range_kpc`, `ns_kilonova_lethal_range_pc`
- Added Numba kernels: `evaluate_ns_merger_hazard_kernel`, `batch_evaluate_hazards_kernel` in `utils/numba_kernels.py`
- Updated `HazardEvaluator` with `evaluate_all_hazards()` method
- Updated `_apply_hazards()` to call unified hazard evaluator for all three types (SN, GRB, NS merger)
- Tests in `tests/test_astrophysics.py` (52 tests)
- Run tests with: `mamba run -n galaticbot python -m pytest tests/test_astrophysics.py -v --override-ini="addopts="`

### Jan 2026 - Unified Disaster Scheduler (Precomputed Disasters)
- Created `UnifiedDisasterScheduler` in `simulation/disasters/unified_scheduler.py`
- Precomputes ALL disasters at initialization (SN, GRB, NS merger):
  - SN: scheduled from M > 8 Msun stars based on main-sequence lifetime (`sn_time = t_ms - age`)
  - GRB: subset of SNe (M > 20 Msun, metallicity-dependent probability)
  - NS merger: galactic rate (~50/Myr) scaled by stellar fraction, positions near NS remnants
- Uses min-heap for O(log N) event retrieval: `get_disasters_in_window(start, end)`
- Disasters occur galaxy-wide, recorded in snapshots even without civilizations
- Stellar death tracking: `stellar_is_alive`, `stellar_remnant_type` arrays
- Adaptive timestep integration: `peek_next_disaster_time()` influences dt selection
- New Numba kernels for batch effect evaluation:
  - `evaluate_sn_effect_on_civs_kernel`: Batch SN effect on civs
  - `evaluate_grb_effect_on_civs_kernel`: Batch GRB beam check
  - `evaluate_ns_merger_effect_on_civs_kernel`: sGRB + kilonova combined
  - `batch_find_civs_in_range_kernel`: Fast range queries
- Refactored `_apply_hazards()` to generate-then-affect flow:
  1. Get disasters from scheduler for current timestep
  2. Record ALL disaster events (HazardEvent dataclass)
  3. Evaluate effects on active civs using batch kernels
  4. Apply destruction effects
- Tests in `tests/test_unified_disaster_scheduler.py` (22 tests)
- Run: `mamba run -n galaticbot python -m pytest tests/test_unified_disaster_scheduler.py -v`

### Jan 2026 - Stellar Evolution and Continuous Star Formation
- **Stellar Aging**: Stars now age during simulation (`ages += dt_gyr` each timestep)
- **Pre-Scheduled Star Formation**: All star births computed at initialization
  - Uses `ScheduledStarBirth` dataclass in `unified_scheduler.py`
  - Star birth heap with O(log N) retrieval via `get_star_births_in_window()`
  - Milky Way rate: ~300 massive stars/Myr
  - Scaled by `n_stars / 4e11` to match simulated galaxy size
  - For 50k stars: ~0.2 new massive stars over 5 Gyr (correct scaling!)
  - New stars placed in outer disk (r=4-15 kpc) star-forming regions
  - Positions use exponential disk profile scaled by `galaxy_scale_radius_kpc`
  - New stars trigger disasters via `_schedule_new_stellar_death()`
- **No per-timestep RNG**: All birth times/positions/masses determined at init
- Config: `enable_star_formation: bool = True` in SimulationParameters
- IMF sampling: Kroupa power-law (M > 8 Msun) with α=-2.3
- Tests in `tests/test_unified_disaster_scheduler.py::TestStarBirthScheduling`

### Jan 2026 - Enhanced Disaster Visualization
- Updated `visualization/threejs/templates/layers.js.j2` with comprehensive disaster viz:
  - **Toggle: History Mode** - Show all past disasters vs current only
  - **Toggle: Scale Mode** - Physical scale vs exaggerated (50x) for visibility
  - **Type filters** - Toggle SN (red), GRB (cyan), NS merger (magenta)
  - **Shockwaves** - Expanding ring animations at disaster locations
  - **Sterilization zones** - Semi-transparent spheres showing lethal radii
  - **GRB beam cones** - Stylized 25° bipolar jets (vs actual 5-10°)
  - **Death markers** - X markers at locations where civs were killed
- Added disaster timeline with clickable canvas markers
- Updated `data_extractor.py` to include full disaster data (energy, radii, jet angles)
- UI controls in `index.html.j2` disaster panel
- Color scheme: SN=#ff4400, GRB=#00ffff, NSM=#ff00ff

### Jan 2026 - NiceGUI Web Application Interface
- Created `great_silence/webapp/` module with NiceGUI-based web interface
- Launch with: `mamba run -n galaticbot python -m great_silence.webapp --port 8081`
- Features implemented (GitHub issues #47-51):
  - **Preset selector**: Clickable cards for 5 Drake equation scenarios
  - **Basic settings**: Stars, duration, seed, Monte Carlo toggle
  - **Advanced settings**: All ~100 parameters in collapsible hierarchical panels
  - **Live simulation feed**: Real-time progress, statistics, event feed
  - **Results dashboard**: Statistics tab, 3D viz tab (Three.js embed), export tab
  - **Config management**: Load/Save YAML, custom presets in ~/.great_silence/presets/
- Module structure:
  ```
  webapp/
  ├── app.py              # Main NiceGUI app, page routes
  ├── state.py            # Reactive AppState with callbacks
  ├── config_io.py        # YAML load/save dialogs
  └── components/
      ├── preset_selector.py   # Scenario cards
      ├── basic_settings.py    # Sliders, toggles
      ├── config_panels.py     # Hierarchical param panels
      ├── simulation_runner.py # Run button, progress, events
      └── results_dashboard.py # Stats, Three.js, exports
  ```
- Dark space theme with gradient background, glass-effect cards
- Fullscreen Three.js visualization via dialog overlay

### Jan 2026 - Simulation Performance Optimization (5x Plan)
- **Problem**: Progress bar stalling during quiet periods, latency issues
- **Target**: 5x improvement in simulation latency
- **Benchmark**: 30k stars, 5 Gyr, optimistic preset

#### Phase 1: Baseline Profiling
- Identified main bottleneck: `_check_civilization_emergence` at 55-60% of runtime
- Initial run time: ~0.69s for 30k stars, 5 Gyr

#### Phase 2: Adaptive Timestep Fix
- Added `_estimate_emergence_timestep()` for emergence probability-based dt
- Added star birth event consideration in `_compute_next_timestep()`
- Prevents 10 Myr jumps during quiet periods
- Progress bar now advances smoothly

#### Phase 3: O(1) Lookup Dictionaries
- Added `_civ_by_id: Dict[int, CivilizationState]` for instant civ lookup
- Added `_probe_by_id: Dict[int, Tuple[int, ProbeState]]` for instant probe lookup
- Replaced O(N) linear searches in `_process_probe_events()`
- Replaced O(N) linear searches in `_merge_probe_buffers()`

#### Phase 4: Numba Emergence Kernel
- Added `compute_emergence_probabilities_kernel()` in `utils/numba_kernels.py`
- Uses `cache=True` for fast repeated calls (no re-compilation)
- Non-parallel version faster than NumPy for small arrays (~6k)
- **37% speedup** in `_check_civilization_emergence`

#### Phase 5: KD-tree Causality Partitioning
- Fixed broken function signatures in `utils/parallel.py`
- Replaced O(N²) pairwise distance loops with `scipy.cKDTree.query_pairs()`
- `find_causal_groups_simple()` and `find_causal_groups_with_colonies()` now O(N log N)
- Functions now return indices (matching call site expectations)

#### Phase 6: Batch Operations
- Optimized `_decay_reputations()`:
  - Skip inactive civilizations early
  - Skip empty reputation dicts
  - Prune near-zero entries to prevent dict growth
- Eliminated from top-20 profile hotspots

#### Results (Phase 1-6)
- **Simulation run time**: 0.69s → 0.56s (**19% faster**)
- **Total time (with init)**: 2.32s → 1.79s (**23% faster**)
- **Progress smoothness**: No more stalls, consistent advancement
- **Scalability**: Better foundation for future parallelization

### Jan 2026 - 10x Speedup (Event-Driven Emergence)
Building on Phase 1-6, implemented radical event-driven optimization:

#### Pre-Scheduled Emergence Events
- **Problem**: Checking 6054 habitable stars × 6528 timesteps = 40M checks for ~123 emergences
- **Solution**: Pre-sample emergence times using exponential inter-arrival times
- Added `_schedule_emergence_events()` at initialization
- Uses min-heap for O(log N) event retrieval vs O(N) per-timestep checks
- Adaptive timestep jumps directly to next emergence event

#### Fast Path for Empty Simulation
- Added `_active_civ_count` for O(1) active civilization check
- Skip all civilization-related work when no civs exist:
  - Stellar motion, encounters, wars, resources, reputations
- Timesteps reduced from 6528 to 2418 (smarter stepping)

#### Final Results
- **Original**: 0.69s simulation run
- **Phase 1-6**: 0.56s (**19% faster**)
- **10x Optimization**: 0.05s (**13.8x faster than original**)
- **Total speedup**: 93% reduction in simulation time

#### Benchmark Scripts
```bash
python scripts/benchmark_quick.py     # Fast single-run benchmark
python scripts/benchmark_baseline.py  # Detailed profiling
```

### Jan 2026 - Physical Correctness Fixes
- **Young stars scheduling bug**: Pre-scheduled emergence was only considering stars already old enough at simulation start
  - Stars that would cross `min_stellar_age_for_life_gyr` threshold during simulation were excluded
  - Fix: Calculate `time_until_eligible_myr` for each star, schedule emergence events starting from that time
  - Test added: `test_young_stars_scheduled_for_future_emergence`
- **Colonization-cancels-emergence**: If a probe colonizes a star before native life emerges, emergence is cancelled
  - This is physically correct: if aliens arrive first, the pre-scheduled native emergence is skipped
  - Tests added: `test_colonization_cancels_emergence`, `test_emergence_heap_respects_colonization`
