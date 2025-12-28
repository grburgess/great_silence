# GalaticBot Jupyter Notebooks

Production-ready notebook interfaces for galactic civilization simulations.

## Quick Start

### 1. Install Dependencies

```bash
# Install with notebook support
pip install -e ".[notebook,viz]"

# Or with micromamba
micromamba activate galaticbot
pip install -e ".[notebook,viz]"
```

**Dependencies installed:**
- `jupyter`, `jupyterlab` - Notebook environment
- `ipywidgets` - Interactive widgets
- `pythreejs` - 3D visualization (Three.js)
- `h5py` - HDF5 storage
- `plotly` - Interactive plots

### 2. Launch JupyterLab

```bash
jupyter lab
```

### 3. Open a Notebook

- **`01_quickstart_production_workflow.ipynb`** - Complete workflow (START HERE)
- **`02_interactive_exploration.ipynb`** - Analyze saved results
- **`03_animation_generation.ipynb`** - Create movies

---

## Notebook Guide

### 01: Quickstart Production Workflow

**What it does:**
- Configure simulation via interactive widget
- Run single or Monte Carlo simulations
- Visualize galaxy structure and civilizations
- Analyze results and statistics
- Export to HDF5

**Usage:**
1. Run all cells sequentially
2. Interact with `SimulationWidget` in cell 3
3. Click "Run Simulation" button
4. Explore visualizations in subsequent cells

**Key features:**
- Preset selector (moderate, optimistic, early_filter, late_filter, rare_earth)
- Parameter overrides (stars, duration, seed)
- No inline widget code - clean notebook
- Progress bar during execution
- Interactive 3D plots with Plotly

---

### 02: Interactive Exploration

**What it does:**
- Load saved simulation results
- Filter civilizations by status, Kardashev level
- Analyze lifetime distributions
- Compare multiple runs
- Custom data analysis

**Usage:**
1. Load results from HDF5 file
2. Use `ResultsExplorer` widget to filter
3. Run custom pandas/matplotlib analysis
4. Compare different simulation scenarios

**Analysis examples:**
- Civilization lifetime statistics
- Death cause breakdown (pie charts)
- Spatial distribution in galaxy
- Kardashev level progression
- Correlation with stellar properties

---

### 03: Animation Generation

**What it does:**
- Create timeline animations
- Generate 3D rotating galaxy movies
- Export frames as PNG sequence
- MP4 video creation

**Usage:**
1. Run simulation with snapshots enabled
2. Use `AnimationBuilder` widget
3. Generate timeline animation via `TimelineAnimator`
4. Create custom frame sequences

**Requirements:**
- `ffmpeg` installed for video encoding
- Snapshots enabled in simulation config

**Install ffmpeg:**
```bash
# macOS
brew install ffmpeg

# Conda/Micromamba
conda install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

---

## Widget Library API

All widgets are imported from `great_silence.notebook`:

### SimulationWidget

High-level interface for running simulations.

```python
from great_silence.notebook import SimulationWidget

widget = SimulationWidget()
widget.display()

# After clicking "Run Simulation":
widget.results              # Results dictionary
widget.runner              # NotebookSimulationRunner instance
widget.export_results(path) # Save to HDF5
```

**Components:**
- Preset selector: Choose Drake equation scenario
- Stars slider: 10k - 500k stars
- Duration slider: 1 - 20 Gyr
- Random seed: Reproducibility
- Monte Carlo checkbox: Multiple realizations
- Run button: Execute simulation

---

### ResultsExplorer

Load and explore saved results.

```python
from great_silence.notebook import ResultsExplorer

# Option 1: Load specific file
explorer = ResultsExplorer('output/my_simulation.h5')

# Option 2: Browse directory
explorer = ResultsExplorer.from_directory('output/')

explorer.display()
```

**Features:**
- File browser for .h5 files
- Status filter (Active/Extinct/All)
- Kardashev level range filter
- Apply button to update view

---

### AnimationBuilder

Create animations from simulation results.

```python
from great_silence.notebook import AnimationBuilder

builder = AnimationBuilder(simulation_data)
builder.display()
```

**Controls:**
- FPS slider: Frame rate (10-60)
- Duration slider: Video length (10-300s)
- Output path: MP4 file location
- Create button: Generate animation

---

### NotebookSimulationRunner

Programmatic simulation control (used by SimulationWidget).

```python
from great_silence import SimulationConfig
from great_silence.notebook import NotebookSimulationRunner

config = SimulationConfig.with_preset('optimistic')
runner = NotebookSimulationRunner(config, seed=42)

# Run simulation
results = runner.run(verbose=True)

# Visualizations
runner.plot_3d_galaxy(backend='plotly')
runner.plot_timeline()
runner.plot_extinction_causes()

# Analysis
runner.get_summary_table()
runner.get_civilization_dataframe()
runner.filter_civilizations(status='active', min_kardashev=1.0)

# Save
runner.save('output/my_simulation')
```

---

## Helper Functions

### configure_notebook_display()

Set matplotlib/plotly defaults for notebooks.

```python
from great_silence.notebook import configure_notebook_display

configure_notebook_display()
```

### load_simulation(path)

Load results from HDF5 file.

```python
from great_silence.notebook import load_simulation

data = load_simulation('output/my_simulation.h5')

# Returns dict with:
data['galaxy']         # Positions, ages, metallicities
data['civilizations']  # List of civilization dicts
data['statistics']     # Summary stats
data['snapshots']      # Time-series snapshots (if saved)
```

### export_interactive_plot(fig, path)

Save Plotly figure as standalone HTML.

```python
from great_silence.notebook import export_interactive_plot

fig = runner.plot_3d_galaxy(backend='plotly')
export_interactive_plot(fig, 'output/galaxy_3d.html')
```

### create_threejs_visualization(positions, colors, sizes)

Create high-performance 3D viz with pythreejs.

```python
from great_silence.notebook import create_threejs_visualization
import numpy as np

positions = np.random.rand(100000, 3) * 20 - 10
renderer = create_threejs_visualization(positions)
display(renderer)  # Interactive in notebook
```

---

## Presets Reference

Available simulation presets:

| Preset | Description | Drake Parameters | Great Filter |
|--------|-------------|------------------|--------------|
| `moderate` | Balanced Fermi-consistent defaults | Default Drake params | Balanced |
| `optimistic` | Life is common | f_life=0.5, f_intel=0.1, f_tech=0.5 | Late filter |
| `early_filter` | Abiogenesis is hard | f_life=0.001 | Very early |
| `late_filter` | Self-destruction common | Kardashev crises | Technology |
| `rare_earth` | Habitable planets rare | habitable=0.01 | Early filter |

Access via:
```python
config = SimulationConfig.with_preset('optimistic')
```

---

## File Organization

### Recommended Directory Structure

```
project/
├── output/                    # Simulation results
│   ├── realistic_run_001.h5   # HDF5 results
│   ├── optimistic_run_001.h5
│   └── animations/            # Generated movies
│       ├── timeline.mp4
│       └── frames/            # PNG sequence
├── notebooks/                 # Jupyter notebooks
│   ├── 01_quickstart_production_workflow.ipynb
│   ├── 02_interactive_exploration.ipynb
│   └── 03_animation_generation.ipynb
```

### HDF5 File Structure

```
simulation.h5
├── galaxy/
│   ├── positions (Nx3 array)
│   ├── ages (N array)
│   └── metallicities (N array)
├── civilizations/
│   ├── parent_star_idx
│   ├── emergence_time_gyr
│   ├── is_active
│   ├── extinction_time_gyr
│   ├── kardashev_level
│   └── death_cause
├── statistics/
│   └── attrs: total_civs, active_civs, etc.
└── snapshots/
    ├── snapshot_0/
    │   ├── time_gyr (attr)
    │   └── positions
    └── snapshot_1/
        └── ...
```

---

## Performance Tips

### For Large Simulations (>200k stars)

1. **Use Monte Carlo mode carefully**
   - Start with 10-50 realizations
   - Increase if needed for statistics

2. **Limit snapshot frequency**
   ```python
   config.simulation.snapshot_interval_myr = 1000.0  # Less frequent
   ```

3. **Use HDF5 compression**
   ```python
   runner.save('output/sim', compress=True)  # Default
   ```

4. **Three.js for 3D visualization**
   ```python
   from great_silence.notebook import create_threejs_visualization
   # Faster than Plotly for 100k+ points
   ```

### Visualization Backends

- **Matplotlib**: Static plots, good for papers/reports
- **Plotly**: Interactive HTML, good for exploration
- **pythreejs**: High-performance 3D, best for large datasets

---

## Troubleshooting

### Widget not displaying

```python
# Enable widget extension
jupyter labextension install @jupyter-widgets/jupyterlab-manager

# Or use nbextension
jupyter nbextension enable --py widgetsnbextension
```

### ffmpeg not found

```bash
# macOS
brew install ffmpeg

# Conda
conda install -c conda-forge ffmpeg
```

### pythreejs not working

```bash
pip install pythreejs
jupyter labextension install @jupyter-widgets/jupyterlab-manager jupyter-threejs
```

### HDF5 file too large

```python
# Use compression
runner.save('output/sim', compress=True)

# Reduce snapshot frequency
config.simulation.snapshot_interval_myr = 500.0

# Subsample stars
config.galaxy.total_stars = 50_000
```

---

## Examples

### Quick Single Run

```python
from great_silence.notebook import SimulationWidget

widget = SimulationWidget()
widget.display()
# Click "Run Simulation"
```

### Custom Configuration

```python
from great_silence import SimulationConfig
from great_silence.notebook import NotebookSimulationRunner

config = SimulationConfig.with_preset('optimistic')
config.galaxy.total_stars = 200_000
config.simulation.simulation_duration_gyr = 13.8

runner = NotebookSimulationRunner(config, seed=123)
results = runner.run(verbose=True)
```

### Load and Analyze

```python
from great_silence.notebook import load_simulation
import pandas as pd

data = load_simulation('output/realistic_run.h5')
civs_df = pd.DataFrame(data['civilizations'])

# Filter advanced civilizations
advanced = civs_df[civs_df['kardashev_level'] >= 2.0]
print(f"Type II+ civilizations: {len(advanced)}")
```

### Create Animation

```python
from great_silence.notebook import AnimationBuilder

builder = AnimationBuilder(widget.results)
builder.fps_slider.value = 30
builder.output_path.value = 'output/my_movie.mp4'
# Click "Create Animation"
```

---

## Next Steps

1. **Start with 01_quickstart_production_workflow.ipynb**
2. **Run a realistic simulation (100k stars, 10 Gyr)**
3. **Explore results in 02_interactive_exploration.ipynb**
4. **Create animations in 03_animation_generation.ipynb**
5. **Customize configs for your research questions**

---

## Questions?

- **Repository**: Check examples/ for script-based workflows
- **Documentation**: See great_silence/notebook/ for widget source code
- **Issues**: Report bugs or request features via GitHub

Happy simulating! 🚀🌌
