# The Great Silence

A sophisticated Monte Carlo simulation exploring the Fermi Paradox and the Great Filter through galactic civilization dynamics.

## Overview

The Great Silence simulates the emergence, expansion, and potential extinction of civilizations in a 3D Milky Way-like galaxy. The simulation accounts for:

- **Realistic galactic structure**: 3D exponential disk with spiral arms, bulge, and proper stellar kinematics
- **Astrophysical hazards**: Supernovae, gamma-ray bursts, and their effects on nearby civilizations
- **Physical constraints**: Light travel time, relativistic effects, and sub-light-speed expansion
- **Star formation history**: Time-dependent star formation rates and stellar populations
- **Drake equation**: Probabilistic civilization emergence based on configurable parameters
- **Numerical optimization**: Uses NumPy, SciPy, and Numba for high-performance computation

## Features

### Galaxy Modeling
- 3D stellar distribution with exponential disk profile
- Spiral arm structure and galactic bar
- Realistic rotation curves and stellar kinematics
- Proper motion of stars over time
- Initial Mass Function (IMF) support (Kroupa, Salpeter, Chabrier)
- Star formation history modeling

### Astrophysics
- Supernova rate modeling based on stellar mass and age
- Distance-dependent sterilization effects
- Gamma-ray bursts with beaming angles
- Time-varying hazard landscapes

### Civilization Dynamics
- Drake equation-based emergence
- Sub-light-speed interstellar expansion
- Colonization wave fronts with light travel time constraints
- Multiple extinction mechanisms (self-destruction, hazards, age)
- Statistical lifetime distributions

### Visualization
- 3D galaxy visualization
- Civilization distribution maps
- Timeline animations
- Statistical analysis plots
- Monte Carlo ensemble analysis

## Installation

### Requirements
- Python 3.9+
- NumPy, SciPy, Numba for numerical computation
- Matplotlib for visualization
- Optional: PyVista, Plotly for advanced 3D visualization

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/great-silence.git
cd great-silence

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Install visualization dependencies
pip install -e ".[viz]"
```

## Quick Start

### Basic Simulation

```python
from great_silence import GalaxySimulation, SimulationConfig

# Create configuration
config = SimulationConfig()

# Customize parameters
config.galaxy.total_stars = 100_000
config.simulation.simulation_duration_gyr = 10.0
config.civilization.fraction_develop_life = 0.5

# Run simulation
sim = GalaxySimulation(config, seed=42)
sim.run()

# Get results
stats = sim.get_statistics()
print(f"Total civilizations: {stats['total_civilizations']}")
print(f"Active civilizations: {stats['active_civilizations']}")
```

### Running the Example

```bash
python examples/basic_simulation.py
```

### Monte Carlo Analysis

```python
from great_silence.simulation import MonteCarloRunner
from great_silence import SimulationConfig

config = SimulationConfig()
config.simulation.num_realizations = 100

runner = MonteCarloRunner(config)
results = runner.run_parallel()
analysis = runner.analyze_results()

print(f"Mean civilizations: {analysis['total_civilizations']['mean']:.1f}")
print(f"Std deviation: {analysis['total_civilizations']['std']:.1f}")
```

## Configuration

Simulations are configured using the `SimulationConfig` class with four main parameter groups:

### Galaxy Parameters
```python
config.galaxy.disk_radius_kpc = 15.0
config.galaxy.total_stars = 100_000_000
config.galaxy.spiral_arm_count = 4
```

### Astrophysics Parameters
```python
config.astrophysics.sn_rate_per_century = 2.0
config.astrophysics.grb_rate_per_century = 0.01
config.astrophysics.imf_type = "kroupa"
```

### Civilization Parameters (Drake Equation)
```python
config.civilization.fraction_stars_with_planets = 1.0
config.civilization.avg_habitable_planets_per_system = 0.2
config.civilization.fraction_develop_life = 0.5
config.civilization.fraction_develop_intelligence = 0.1
config.civilization.fraction_develop_technology = 0.1
config.civilization.mean_civilization_lifetime_myr = 1.0
```

### Simulation Parameters
```python
config.simulation.simulation_duration_gyr = 10.0
config.simulation.time_step_myr = 1.0
config.simulation.num_realizations = 100
config.simulation.use_numba = True
```

Configuration can also be loaded from YAML files:

```python
config = SimulationConfig.from_yaml("config.yaml")
```

## Project Structure

```
great-silence/
├── src/great_silence/
│   ├── galaxy/              # Galactic structure and dynamics
│   │   ├── structure.py     # 3D galaxy model with stellar kinematics
│   │   └── star_formation.py # SFH and IMF
│   ├── astrophysics/        # Astrophysical processes
│   │   ├── supernovae.py    # Supernova modeling
│   │   ├── grb.py           # Gamma-ray bursts
│   │   └── hazards.py       # Combined hazard evaluation
│   ├── civilization/        # Civilization dynamics
│   │   ├── emergence.py     # Drake equation
│   │   ├── expansion.py     # Interstellar colonization
│   │   └── extinction.py    # Extinction mechanisms
│   ├── simulation/          # Core simulation engine
│   │   ├── engine.py        # Main simulation loop
│   │   ├── monte_carlo.py   # Monte Carlo framework
│   │   └── physics.py       # Light travel time, relativity
│   ├── visualization/       # Visualization tools
│   │   ├── galaxy_viz.py    # 3D galaxy plots
│   │   └── timeline.py      # Animations and timelines
│   ├── config/              # Configuration management
│   │   └── parameters.py    # Parameter classes
│   └── utils/               # Utilities
│       └── spatial.py       # Spatial indexing (KD-tree)
├── examples/                # Example scripts
├── tests/                   # Test suite
└── data/                    # Output data directory
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=great_silence --cov-report=html

# Run specific test
pytest tests/test_galaxy.py
```

## Development

### Code Style

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Performance Optimization

The simulation is optimized for performance:
- Numba JIT compilation for critical loops
- Vectorized NumPy operations
- KD-tree spatial indexing for nearest neighbor queries
- Parallel Monte Carlo execution

To enable maximum performance:
```python
config.simulation.use_numba = True
config.simulation.parallel_processing = True
```

## Scientific Background

### Drake Equation
The Drake equation estimates the number of active, communicative civilizations:

N = R* × fp × ne × fl × fi × fc × L

Where:
- R* = star formation rate
- fp = fraction of stars with planets
- ne = average number of habitable planets per star with planets
- fl = fraction of habitable planets that develop life
- fi = fraction of life that develops intelligence
- fc = fraction of intelligent life that develops technology
- L = civilization lifetime

### Astrophysical Hazards
- **Supernovae**: Core-collapse supernovae from massive stars (>8 M☉)
- **Gamma-ray bursts**: Highly collimated jets from stellar collapse or mergers
- **Sterilization zones**: Distance-dependent probability of biosphere destruction

## Contributing

Contributions are welcome! Areas for improvement:
- Enhanced expansion models with proper wavefront propagation
- More sophisticated extinction mechanisms
- Additional astrophysical hazards (asteroid impacts, stellar flares)
- Advanced visualization (interactive 3D, web-based)
- Performance optimizations
- Additional IMF models
- Observational constraint integration

## License

MIT License

## References

- Drake, F. (1961). "The Drake Equation"
- Gowanlock, M. et al. (2011). "A Model of Habitability Within the Milky Way Galaxy"
- Lineweaver, C. et al. (2004). "The Galactic Habitable Zone"
- Kroupa, P. (2001). "On the variation of the initial mass function"

## Citation

If you use The Great Silence in your research, please cite:

```bibtex
@software{great_silence,
  title={The Great Silence: Monte Carlo Simulation of Galactic Civilizations and the Fermi Paradox},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/great-silence}
}
```
