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

## Incomplete features requiring enhancement

1. **Expansion model** (`civilization/expansion.py`): Needs wavefront propagation with light cones, track launch/arrival times
2. **Light travel time** (`simulation/physics.py`): Enforce causality in expansion logic
3. **Hazard application** (`simulation/engine.py:_apply_hazards()`): Actually call HazardEvaluator
4. **Spatial optimization** (`simulation/engine.py`): Use SpatialIndex for O(log N) queries
5. **Numba optimization**: Add @jit decorators to hot loops

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
