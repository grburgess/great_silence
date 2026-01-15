# Installation Guide for GalaticBot

Complete installation instructions for macOS (Apple Silicon M1 Max).

---

## Method 1: Using pip + venv (Standard Python)

### 1. Clone/Navigate to Repository

```bash
cd /Users/jburgess/coding/projects/galaticbot
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Package

```bash
# Install in development mode with all dependencies
pip install -e ".[dev,viz]"

# Or minimal installation (just core dependencies)
pip install -e .
```

### 4. Verify Installation

```bash
# Check package is installed
python -c "from great_silence import SimulationConfig; print('✓ GalaticBot installed')"

# Check Numba (critical for performance)
python -c "import numba; print(f'✓ Numba {numba.__version__}')"

# Run benchmark
python -m src.great_silence.utils.numba_kernels
```

### 5. Set M1 Max Environment Variables

```bash
# Add to ~/.zshrc (macOS default shell)
echo 'export NUMBA_NUM_THREADS=8' >> ~/.zshrc
echo 'export OMP_NUM_THREADS=8' >> ~/.zshrc
echo 'export NUMBA_THREADING_LAYER=omp' >> ~/.zshrc

# Reload
source ~/.zshrc

# Verify
echo $NUMBA_NUM_THREADS  # Should print: 8
```

---

## Method 2: Using Micromamba (Recommended for M1 Max)

Micromamba is a lightweight, fast alternative to conda. Highly recommended for Apple Silicon!

### 1. Install Micromamba (if not already installed)

```bash
# Install micromamba
"${SHELL}" <(curl -L micro.mamba.pm/install.sh)

# Restart shell or run:
source ~/.zshrc
```

### 2. Create Environment for GalaticBot

```bash
cd /Users/jburgess/coding/projects/galaticbot

# Create environment with Python 3.11 (recommended for M1 Max)
micromamba create -n galaticbot python=3.11 -c conda-forge

# Activate environment
micromamba activate galaticbot
```

### 3. Install Dependencies via Micromamba

```bash
# Install core numerical packages (optimized for Apple Silicon)
micromamba install -c conda-forge \
    numpy \
    scipy \
    pandas \
    matplotlib \
    numba \
    pyyaml \
    tqdm

# Install development tools
micromamba install -c conda-forge \
    pytest \
    pytest-cov \
    black \
    ruff \
    mypy

# Install visualization (optional)
micromamba install -c conda-forge \
    plotly \
    pyvista
```

### 4. Install GalaticBot Package

```bash
# Install in development mode
pip install -e .
```

### 5. Configure Environment Variables

```bash
# Micromamba automatically sets these, but verify:
micromamba run -n galaticbot python -c "import os; print(f'Threads: {os.cpu_count()}')"

# For manual control, add to ~/.zshrc:
echo 'export NUMBA_NUM_THREADS=8' >> ~/.zshrc
echo 'export OMP_NUM_THREADS=8' >> ~/.zshrc
source ~/.zshrc
```

### 6. Verify Installation

```bash
# Activate environment
micromamba activate galaticbot

# Test import
python -c "from great_silence import SimulationConfig; print('✓ GalaticBot installed')"

# Check optimized packages
python -c "
import numpy as np
import numba
print(f'NumPy: {np.__version__}')
print(f'Numba: {numba.__version__}')
print(np.__config__.show())  # Check for Accelerate framework
"

# Run benchmark
python -m src.great_silence.utils.numba_kernels
```

---

## Method 3: Using Conda/Miniconda

If you prefer standard conda:

### 1. Install Miniconda (if not installed)

```bash
# Download Miniconda for Apple Silicon
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh

# Install
bash Miniconda3-latest-MacOSX-arm64.sh

# Restart shell
source ~/.zshrc
```

### 2. Create Environment

```bash
cd /Users/jburgess/coding/projects/galaticbot

# Create environment
conda create -n galaticbot python=3.11 -c conda-forge

# Activate
conda activate galaticbot
```

### 3. Install Dependencies

```bash
# Core packages
conda install -c conda-forge \
    numpy scipy pandas matplotlib numba pyyaml tqdm

# Dev tools
conda install -c conda-forge \
    pytest pytest-cov black ruff mypy

# Visualization (optional)
conda install -c conda-forge plotly pyvista
```

### 4. Install Package

```bash
pip install -e .
```

---

## Recommended: Micromamba vs Conda vs Pip

**For M1 Max, we recommend Micromamba because:**

| Feature | Micromamba | Conda | Pip/venv |
|---------|-----------|-------|----------|
| Speed | ⚡⚡⚡ Fastest | ⚡ Slow | ⚡⚡ Fast |
| Disk space | 📦 ~50 MB | 📦 ~500 MB | 📦 Minimal |
| Apple Silicon packages | ✅ Optimized | ✅ Optimized | ⚠️ May need compilation |
| Dependency resolution | ✅ Excellent | ✅ Good | ⚠️ Manual |
| Environment isolation | ✅ Yes | ✅ Yes | ✅ Yes |

**Bottom line**: Use Micromamba for best performance on M1 Max.

---

## Quick Start After Installation

### 1. Set Environment Variables (Important!)

```bash
# Add to ~/.zshrc
export NUMBA_NUM_THREADS=8
export OMP_NUM_THREADS=8
export NUMBA_THREADING_LAYER=omp

# Reload
source ~/.zshrc
```

### 2. Run Example Simulation

```bash
# Activate environment (if using micromamba)
micromamba activate galaticbot

# Run basic example
python examples/basic_simulation.py
```

### 3. Try Parameter Presets

```python
from great_silence import SimulationConfig, GalaxySimulation

# Early Filter scenario
config = SimulationConfig.with_preset('early_filter')
config.galaxy.total_stars = 100_000
config.simulation.simulation_duration_gyr = 1.0

sim = GalaxySimulation(config, seed=42)
sim.run()

print(sim.get_statistics())
```

### 4. Run Benchmark

```bash
# Benchmark Numba kernels on your M1 Max
python -m src.great_silence.utils.numba_kernels
```

Expected output:
```
GalaticBot Numba Kernels Benchmark
============================================================

1. Position Evolution (N=1,000,000)
   Time: 2-4 ms
   Throughput: 250-500 M stars/sec

2. Distance Calculation (N=1,000,000)
   Time: 3-6 ms
   Throughput: 150-350 M distances/sec

3. Nearby Search (N=1,000,000, r=1 kpc)
   Time: 3-6 ms
   Found: ~1000 nearby stars
```

---

## Dependencies

### Core (Required)
- `numpy >= 1.24.0` - Numerical arrays
- `scipy >= 1.10.0` - Spatial indexing (KD-tree)
- `pandas >= 2.0.0` - Data analysis
- `matplotlib >= 3.7.0` - Visualization
- `numba >= 0.57.0` - **Critical for M1 Max performance**
- `pyyaml >= 6.0` - Configuration files
- `tqdm >= 4.65.0` - Progress bars

### Development (Optional)
- `pytest >= 7.3.0` - Testing
- `pytest-cov >= 4.1.0` - Coverage
- `black >= 23.3.0` - Code formatting
- `ruff >= 0.0.270` - Linting
- `mypy >= 1.3.0` - Type checking

### Visualization (Optional)
- `plotly >= 5.14.0` - Interactive plots
- `pyvista >= 0.40.0` - 3D visualization

---

## Troubleshooting

### "numba not found" or slow performance

```bash
# Reinstall numba
pip install --force-reinstall numba>=0.57.0

# Or with micromamba
micromamba install -c conda-forge numba --force-reinstall
```

### "scipy not found" or KD-tree errors

```bash
# Reinstall scipy
pip install --force-reinstall scipy>=1.10.0

# Or with micromamba
micromamba install -c conda-forge scipy --force-reinstall
```

### ImportError: cannot import name 'X'

```bash
# Reinstall in development mode
pip uninstall galaticbot
pip install -e .
```

### Performance is slow even with Numba

Check environment variables:

```python
import os
print(f"NUMBA_NUM_THREADS: {os.environ.get('NUMBA_NUM_THREADS')}")
print(f"OMP_NUM_THREADS: {os.environ.get('OMP_NUM_THREADS')}")
```

Should both print: `8`

If not, set them:

```bash
export NUMBA_NUM_THREADS=8
export OMP_NUM_THREADS=8
```

### Verify Apple Accelerate Framework (M1 Max optimization)

```python
import numpy as np
print(np.__config__.show())
```

Look for `Accelerate` or `vecLib` in the output. This confirms NumPy is using Apple's optimized BLAS/LAPACK.

---

## Switching Between Environments

### From pip/venv to Micromamba

```bash
# Deactivate venv
deactivate

# Create micromamba environment
micromamba create -n galaticbot python=3.11 -c conda-forge

# Activate
micromamba activate galaticbot

# Install dependencies
micromamba install -c conda-forge numpy scipy pandas matplotlib numba pyyaml tqdm

# Install package
cd /Users/jburgess/coding/projects/galaticbot
pip install -e .
```

### List All Environments

```bash
# Micromamba
micromamba env list

# Conda
conda env list
```

### Remove Old Environment

```bash
# Remove venv
rm -rf /Users/jburgess/coding/projects/galaticbot/venv

# Remove micromamba environment
micromamba env remove -n galaticbot

# Remove conda environment
conda env remove -n galaticbot
```

---

## Post-Installation Checklist

- [ ] Package installed: `python -c "from great_silence import SimulationConfig; print('OK')"`
- [ ] Numba working: `python -c "import numba; print(numba.__version__)"`
- [ ] Environment variables set: `echo $NUMBA_NUM_THREADS` → `8`
- [ ] Benchmark runs: `python -m src.great_silence.utils.numba_kernels`
- [ ] Example works: `python examples/basic_simulation.py`
- [ ] Parameter presets work: `python -c "from great_silence import SimulationConfig; c = SimulationConfig.with_preset('early_filter'); print('OK')"`

---

## Next Steps

1. **Read the optimization guide**: `M1_MAX_OPTIMIZATION.md`
2. **Read the implementation summary**: `IMPLEMENTATION_SUMMARY.md`
3. **Run example simulations**: `python examples/basic_simulation.py`
4. **Explore parameter presets**: Try different Great Filter scenarios
5. **Run Monte Carlo**: Test statistical analysis with confidence intervals

---

## Support

If you encounter issues:

1. Check this guide's Troubleshooting section
2. Check `M1_MAX_OPTIMIZATION.md` for performance issues
3. Verify all dependencies are installed: `pip list | grep numpy`
4. Try running in verbose mode to see detailed output

**Happy simulating!** 🚀
