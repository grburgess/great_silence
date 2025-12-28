# 🌌 Interactive Galactic Simulation Notebooks

This directory contains Jupyter notebooks for interactive exploration of galactic civilization simulations.

## 🚀 Getting Started

### 1. Install Dependencies

```bash
cd notebooks
pip install -r requirements.txt
```

### 2. Launch JupyterLab

```bash
jupyter lab
```

This will open JupyterLab in your browser at `http://localhost:8888`

### 3. Open the Notebook

Navigate to `interactive_simulation.ipynb` and run the cells in order.

## 📓 Available Notebooks

### `interactive_simulation.ipynb`

**Full-featured interactive simulation interface with:**

- **🎛️ Control Panel**: Adjust simulation parameters via widgets
  - Choose between Realistic (cooperation) or DEADLY (no cooperation) modes
  - Configure number of civilizations (5-100)
  - Set galaxy size (10,000-200,000 stars)
  - Control simulation duration (1,000-20,000 Myr)

- **🎨 Realistic 3D Visualizations**: Interactive Plotly graphics
  - Rotatable, zoomable 3D galaxy view
  - Civilizations color-coded by Kardashev level
  - Death markers showing cause (crisis, supernova, GRB)
  - Astrophysical event overlays

- **📈 Development Timelines**: Track evolution over time
  - Kardashev level progression
  - Social maturity growth
  - Crisis events and survival

- **📊 Statistics Dashboard**: Multi-panel analysis
  - Survival rates
  - Death cause breakdown
  - Astrophysical event counts
  - Kardashev distribution histograms

- **🔍 Interactive Exploration**: Filter and analyze
  - Status filters (alive/dead/cause of death)
  - Kardashev level range selection
  - Custom views of specific civilization types

- **📂 Load Existing Runs**: Browse previous simulations
  - Dropdown selector for all runs in `outputs/`
  - Quick load and visualize past results

- **💾 Export**: Save interactive plots as HTML
  - Standalone files for sharing
  - Full 3D interactivity preserved

## 💡 Usage Tips

1. **Start Small**: Begin with 20 civilizations and 50,000 stars for faster runs
2. **Watch Progress**: The simulation prints updates every 10% of duration
3. **Compare Modes**: Run both Realistic and DEADLY to see cooperation's impact
4. **Explore Deaths**: Use the filter tools to isolate specific death causes
5. **Share Results**: Export HTML visualizations to share interactive 3D plots

## 📦 Architecture

The notebook uses visualization functions from the `great_silence.visualization` library module:
- `create_3d_galaxy_view()` - Interactive 3D Plotly galaxy map
- `create_development_timeline()` - Civilization development over time
- `create_statistics_dashboard()` - Multi-panel statistics dashboard

These functions are defined in `great_silence/visualization/interactive_viz.py` and can be reused in other notebooks or scripts.

## 🎯 Example Workflow

1. **Run Quick Test**:
   - Mode: Realistic
   - Civs: 20
   - Stars: 50,000
   - Duration: 2,000 Myr

2. **Visualize Results**:
   - Run all visualization cells to see 3D map, timelines, and statistics

3. **Apply Filters**:
   - Show only surviving civilizations
   - Filter by Kardashev level range

4. **Compare Modes**:
   - Run DEADLY mode with same parameters
   - Compare survival rates

5. **Load Previous Run**:
   - Use file browser to load existing simulation from `outputs/`
   - Re-visualize with different filters

## 🔧 Troubleshooting

**Widgets not showing?**
```bash
jupyter labextension install @jupyter-widgets/jupyterlab-manager
```

**Plotly not rendering?**
```bash
pip install --upgrade plotly nbformat
```

**Kernel crashes with large simulations?**
- Reduce number of stars
- Shorten duration
- Close other applications to free memory

## 📚 Further Reading

- Main README: `../README.md`
- Production run script: `../examples/production_run.py`
- Deadly simulation: `../examples/deadly_simulation.py`
