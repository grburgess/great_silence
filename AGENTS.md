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
