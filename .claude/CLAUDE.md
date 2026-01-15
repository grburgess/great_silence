# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Great Silence is a Monte Carlo simulation of intelligent civilizations spreading through a Milky Way-like galaxy. It implements the Drake equation with realistic astrophysical constraints including stellar dynamics, light travel time, supernovae, gamma-ray bursts, and civilization expansion/extinction dynamics.

**Key Goal**: Simulate galactic civilization emergence and evolution with proper physical constraints and numerical optimization.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install with all dependencies (dev + visualization)
pip install -e ".[dev,viz]"
```

### Running Simulations
```bash
# Run basic example
python examples/basic_simulation.py

# Run with custom configuration
python -c "from great_silence import GalaxySimulation, SimulationConfig; \
           config = SimulationConfig(); \
           sim = GalaxySimulation(config); \
           sim.run()"
```

### Testing
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

### Code Quality
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

## Architecture

### Module Organization

The codebase is organized into distinct functional modules under `src/great-silence/`:

1. **galaxy/** - Galactic structure and stellar populations
   - `structure.py`: 3D galaxy model with exponential disk, spiral arms, and stellar kinematics
   - `star_formation.py`: Star formation history (SFH) and Initial Mass Function (IMF)
   - Key: Handles time evolution of stellar positions via `evolve_positions()`

2. **astrophysics/** - Physical hazards affecting civilizations
   - `supernovae.py`: Supernova rate calculation and sterilization zones
   - `grb.py`: Gamma-ray burst beaming and lethality
   - `hazards.py`: Combined hazard evaluator coordinating all astrophysical threats
   - Key: Distance-dependent probabilistic destruction mechanisms

3. **civilization/** - Civilization lifecycle modeling
   - `emergence.py`: Drake equation implementation for civilization birth
   - `expansion.py`: Interstellar colonization with sub-light-speed travel
   - `extinction.py`: Self-destruction, age-based extinction, and hazard responses
   - Key: All probabilities are per time step and must be scaled by `dt_myr`

4. **simulation/** - Core simulation engine
   - `engine.py`: Main `GalaxySimulation` class orchestrating all components
   - `monte_carlo.py`: Parallel execution of multiple simulation realizations
   - `physics.py`: Light travel time calculations and relativistic effects
   - Key: Main loop in `GalaxySimulation.run()` advances time and calls subsystems

5. **visualization/** - Plotting and animation
   - `galaxy_viz.py`: 3D galaxy plots, civilization distribution maps
   - `timeline.py`: Time series plots and animations
   - Key: Uses matplotlib; requires stellar positions as (N, 3) NumPy arrays

6. **config/** - Configuration management
   - `parameters.py`: Dataclass-based configuration with YAML serialization
   - Key: Four parameter groups (galaxy, astrophysics, civilization, simulation)

7. **utils/** - Helper utilities
   - `spatial.py`: KD-tree based spatial indexing for fast nearest neighbor queries
   - Key: Critical for performance when finding nearby stars

### Data Flow

1. **Initialization** (`GalaxySimulation.initialize()`):
   - Generate stellar positions from galactic density profile
   - Assign stellar ages from star formation history
   - Sample stellar masses from IMF
   - Identify habitable stars (0.5-1.5 solar masses)

2. **Main Loop** (`GalaxySimulation.run()`):
   - Evolve stellar positions forward by `dt_myr`
   - Check for civilization emergence (Drake equation + randomness)
   - Evolve existing civilizations (expansion, aging)
   - Apply astrophysical hazards (supernovae, GRBs)
   - Save snapshots at intervals
   - Advance time counter

3. **Civilization Lifecycle**:
   - **Birth**: Probabilistic emergence on habitable stars older than 1 Gyr
   - **Growth**: Expansion to nearby stars (currently simplified, needs enhancement)
   - **Death**: Self-destruction OR age-based extinction OR hazard-induced

4. **Monte Carlo Analysis**:
   - Run N independent realizations with different random seeds
   - Aggregate statistics across realizations
   - Compute mean, std, median, min, max for key metrics

### Key Design Patterns

**Separation of Concerns**: Each module has a single responsibility. Galaxy evolution is independent of civilization dynamics, which is independent of visualization.

**Configuration as Data**: All parameters are in `SimulationConfig` dataclass, supporting YAML serialization for reproducibility.

**Vectorized Operations**: Uses NumPy vectorization wherever possible for performance. Avoid Python loops over stars.

**Lazy Initialization**: Spatial indices and other expensive structures are built on-demand.

**Snapshot System**: Simulation state is periodically serialized to `SimulationSnapshot` objects for visualization and analysis.

### Performance Considerations

**Critical Performance Paths**:
1. Stellar position evolution (vectorized in `galaxy/structure.py`)
2. Nearest neighbor queries (uses `scipy.spatial.cKDTree` in `utils/spatial.py`)
3. Hazard evaluation over all stars (needs vectorization)
4. Distance matrix computation (currently O(N²), needs optimization)

**Optimization Strategy**:
- Use Numba `@jit` decorators for hot loops (when `config.simulation.use_numba = True`)
- Vectorize with NumPy instead of Python loops
- Use spatial indexing (KD-tree) for range queries
- Chunk large operations to fit in cache
- Parallel Monte Carlo with `ProcessPoolExecutor`

**Bottlenecks to Address**:
- `GalaxyModel.get_distance_matrix()` is O(N²) - use spatial index instead
- Civilization emergence checks all habitable stars every time step - consider batch sampling
- Expansion model is placeholder - needs proper wavefront propagation with light cone

## Implementation Guidelines

### Adding New Features

**New Astrophysical Hazard**:
1. Create model class in `src/great-silence/astrophysics/your_hazard.py`
2. Implement rate/probability calculation and lethal range
3. Add to `HazardEvaluator` in `astrophysics/hazards.py`
4. Add configuration parameters to `AstrophysicsParameters` in `config/parameters.py`
5. Call from `GalaxySimulation._apply_hazards()` in `simulation/engine.py`

**New Civilization Behavior**:
1. Add model to appropriate file in `civilization/`
2. Add configuration parameters to `CivilizationParameters`
3. Integrate into `GalaxySimulation._evolve_civilizations()`

**New Visualization**:
1. Add method to `GalaxyVisualizer` or `TimelineAnimator`
2. Accept NumPy arrays as input, not simulation objects
3. Use `save_path` parameter for optional file output
4. Set `facecolor='black'` for space-like appearance

### Testing Guidelines

**Unit Tests**: Test individual components in isolation
```python
def test_imf_sampling():
    imf = InitialMassFunction("kroupa")
    masses = imf.sample(1000, seed=42)
    assert len(masses) == 1000
    assert 0.08 <= masses.min() <= masses.max() <= 100.0
```

**Integration Tests**: Test component interactions
```python
def test_simulation_initialization():
    config = SimulationConfig()
    sim = GalaxySimulation(config, seed=42)
    sim.initialize()
    assert sim.galaxy.positions is not None
    assert len(sim.galaxy.positions) == config.galaxy.total_stars
```

**Property Tests**: Test physical constraints
```python
def test_light_travel_time_positive():
    for distance in [1, 10, 100, 1000]:
        time = LightTravelCalculator.light_travel_time(distance)
        assert time > 0
```

### Common Pitfalls

1. **Unit Confusion**: Always document units in docstrings
   - Distances: kpc in galaxy positions, pc for stellar distances
   - Time: Gyr for ages, Myr for time steps, yr for light travel
   - Velocity: km/s for stellar motion, fraction of c for expansion

2. **Time Step Scaling**: Probabilities must be scaled by `dt_myr`
   ```python
   # Correct
   p_event = base_rate_per_myr * dt_myr

   # Wrong - will over/under-count events
   p_event = base_rate_per_myr
   ```

3. **Random Seeds**: Pass `seed` through to all RNG creation for reproducibility
   ```python
   rng = np.random.default_rng(seed)  # Good
   rng = np.random.default_rng()      # Bad - not reproducible
   ```

4. **Array Copying**: Be explicit about views vs copies
   ```python
   positions_copy = self.positions.copy()  # Explicit copy
   positions_view = self.positions         # Reference (will mutate original)
   ```

5. **Distance Matrix Memory**: Don't compute full O(N²) distance matrices for large N
   ```python
   # Bad for large N
   distances = np.linalg.norm(pos[:, None] - pos[None, :], axis=2)

   # Good - use spatial index for local queries
   spatial_index = SpatialIndex(pos)
   nearby_indices = spatial_index.query_radius(center, radius)
   ```

### Incomplete Features Requiring Enhancement

1. **Expansion Model** (`civilization/expansion.py`):
   - Current: Placeholder with no actual colonization
   - Needed: Proper wavefront propagation with light cones
   - Implementation: Track colony "launch times" and arrival times considering travel duration

2. **Light Travel Time Constraints** (`simulation/physics.py`):
   - Current: Basic calculator implemented but not integrated
   - Needed: Enforce causality - civilizations can only detect/colonize within past light cone
   - Implementation: Use `LightTravelCalculator.observable_horizon()` in expansion logic

3. **Hazard Application** (`simulation/engine.py:_apply_hazards()`):
   - Current: Placeholder (pass statement)
   - Needed: Actually call `HazardEvaluator` methods for each active civilization
   - Implementation: Loop over active civilizations, evaluate SN and GRB hazards, mark destroyed civs

4. **Spatial Optimization** (`simulation/engine.py`):
   - Current: Linear search for nearby stars
   - Needed: Use `SpatialIndex` for O(log N) queries
   - Implementation: Build KD-tree on initialization, use `query_radius()` for colonization candidates

5. **Numba Optimization**:
   - Current: Flag exists but no `@jit` decorators applied
   - Needed: Decorate hot loops (position evolution, distance calculations)
   - Implementation: Add `@numba.jit(nopython=True)` to performance-critical functions

## Scientific Accuracy Notes

**Stellar Kinematics**:
- Flat rotation curve at ~220 km/s is accurate for Milky Way
- Velocity dispersion increases with height (correct for thin/thick disk)

**Star Formation**:
- Delayed exponential model matches observations
- IMF choices (Kroupa, Salpeter, Chabrier) are standard in astrophysics

**Supernova Rates**:
- ~2 per century is consistent with Milky Way estimates
- Lethal range of 10 pc is conservative estimate for sterilization

**GRB Rates**:
- 0.01 per century is highly uncertain (observational limits)
- Beaming angle of 10° is typical for long-duration GRBs

**Drake Equation**:
- Parameter ranges should be adjustable for exploration
- Default values are rough estimates (highly uncertain)

**Expansion Velocity**:
- 0.01c (1% light speed) is optimistic but not impossible
- Enables crossing galaxy in ~1 Gyr

## Dependencies and Their Purpose

**Core Numerical**:
- `numpy`: Array operations, linear algebra, random number generation
- `scipy`: Spatial indexing (cKDTree), special functions
- `numba`: JIT compilation for performance-critical loops

**Visualization**:
- `matplotlib`: 2D/3D plotting, animations
- `plotly` (optional): Interactive 3D visualizations
- `pyvista` (optional): Advanced 3D rendering

**Data Management**:
- `pandas`: Tabular data analysis for Monte Carlo results
- `pyyaml`: Configuration file serialization

**Development**:
- `pytest`: Testing framework
- `black`: Code formatting (line length 100)
- `ruff`: Fast linting
- `mypy`: Static type checking

## File Naming Conventions

- Module files: lowercase with underscores (`star_formation.py`)
- Classes: PascalCase (`GalaxyModel`, `SimulationConfig`)
- Functions/methods: lowercase with underscores (`generate_stellar_population()`)
- Constants: UPPERCASE with underscores (`C_PC_YR`)
- Private methods: leading underscore (`_apply_hazards()`)

## When Making Changes

1. **Maintain Physical Units**: Document units in docstrings, use consistent conventions
2. **Preserve Reproducibility**: Always use seeded RNGs, never use `np.random.random()` directly
3. **Optimize Carefully**: Profile before optimizing, vectorize before using Numba
4. **Test Thoroughly**: Add tests for new features, ensure existing tests pass
5. **Update Documentation**: Modify README.md and this file when adding features

## Quick Reference

**Run a quick test simulation**:
```bash
python -c "from great_silence import GalaxySimulation, SimulationConfig; c = SimulationConfig(); c.galaxy.total_stars = 10000; c.simulation.simulation_duration_gyr = 1.0; s = GalaxySimulation(c); s.run()"
```

**Load and inspect configuration**:
```bash
python -c "from great_silence import SimulationConfig; c = SimulationConfig(); print(c.to_dict())"
```

**Profile performance**:
```bash
python -m cProfile -o profile.stats examples/basic_simulation.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```
