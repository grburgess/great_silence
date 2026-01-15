# GalaticBot Quick Start Guide

The fastest way to get GalaticBot running on your M1 Max.

---

## 🚀 One-Command Installation (Recommended for M1 Max)

```bash
cd /Users/jburgess/coding/projects/galaticbot
./setup_m1_max.sh
```

This script will:
- ✅ Install micromamba (if needed)
- ✅ Create optimized Python environment
- ✅ Install all dependencies
- ✅ Configure M1 Max settings
- ✅ Run verification tests

**Time**: ~5-10 minutes

---

## ⚡ Manual Installation (3 Commands)

### Using Micromamba (Recommended)

```bash
# 1. Create environment
micromamba create -n galaticbot python=3.11 -c conda-forge
micromamba activate galaticbot

# 2. Install dependencies
micromamba install -c conda-forge numpy scipy pandas matplotlib numba pyyaml tqdm

# 3. Install package
pip install -e .
```

### Using pip/venv (Alternative)

```bash
# 1. Create environment
python3 -m venv venv
source venv/bin/activate

# 2. Install package with dependencies
pip install -e ".[dev,viz]"
```

---

## 🎯 First Run

### 1. Activate Environment

```bash
# Micromamba
micromamba activate galaticbot

# OR venv
source venv/bin/activate
```

### 2. Set M1 Max Optimizations (Important!)

```bash
export NUMBA_NUM_THREADS=8
export OMP_NUM_THREADS=8
```

Or add to `~/.zshrc` for permanent:

```bash
echo 'export NUMBA_NUM_THREADS=8' >> ~/.zshrc
echo 'export OMP_NUM_THREADS=8' >> ~/.zshrc
source ~/.zshrc
```

### 3. Run Your First Simulation

```python
from great_silence import SimulationConfig, GalaxySimulation

# Create configuration (uses optimized defaults)
config = SimulationConfig()
config.galaxy.total_stars = 100_000          # Start small
config.simulation.simulation_duration_gyr = 1.0
config.simulation.use_numba = True           # M1 Max acceleration

# Run simulation
sim = GalaxySimulation(config, seed=42)
sim.run()

# Get results
stats = sim.get_statistics()
print(f"Total civilizations emerged: {stats['total_civilizations']}")
print(f"Active civilizations: {stats['active_civilizations']}")
print(f"Extinct civilizations: {stats['extinct_civilizations']}")
```

---

## 🔬 Try Different Scenarios

### Early Filter (Life is Rare)

```python
from great_silence import SimulationConfig

config = SimulationConfig.with_preset('early_filter')
config.galaxy.total_stars = 100_000
```

### Late Filter (Civilizations Self-Destruct)

```python
config = SimulationConfig.with_preset('late_filter')
config.galaxy.total_stars = 100_000
```

### Rare Earth (Habitable Planets are Rare)

```python
config = SimulationConfig.with_preset('rare_earth')
config.galaxy.total_stars = 100_000
```

### Optimistic (Life is Common)

```python
config = SimulationConfig.with_preset('optimistic')
config.galaxy.total_stars = 100_000
# Warning: Predicts many civilizations (not Fermi-consistent)
```

---

## 📊 Run Monte Carlo Analysis

```python
from great_silence.simulation import MonteCarloRunner
from great_silence import SimulationConfig

# Configuration
config = SimulationConfig.with_preset('moderate')
config.galaxy.total_stars = 100_000
config.simulation.num_realizations = 100

# Run parallel simulations (uses all 8 P-cores)
runner = MonteCarloRunner(config)
results = runner.run_parallel(n_processes=8)

# Analyze with confidence intervals
analysis = runner.analyze_results()

# Print results
print(f"\nMonte Carlo Results ({analysis['n_realizations']} realizations):")
print(f"  Mean civilizations: {analysis['total_civilizations']['mean']:.1f}")
print(f"  95% CI: [{analysis['total_civilizations']['ci_95_lower']:.1f}, "
      f"{analysis['total_civilizations']['ci_95_upper']:.1f}]")
print(f"  Median: {analysis['total_civilizations']['median']:.1f}")
print(f"  Std Dev: {analysis['total_civilizations']['std']:.1f}")
```

---

## ⚙️ Verify M1 Max Performance

### 1. Check Numba is Working

```bash
python -m src.great_silence.utils.numba_kernels
```

Expected output on M1 Max:
```
1. Position Evolution (N=1,000,000)
   Time: 2-4 ms
   Throughput: 250-500 M stars/sec
```

### 2. Check Environment Variables

```python
import os
print(f"NUMBA_NUM_THREADS: {os.environ.get('NUMBA_NUM_THREADS')}")  # Should be 8
print(f"OMP_NUM_THREADS: {os.environ.get('OMP_NUM_THREADS')}")      # Should be 8
```

### 3. Check Accelerate Framework (Apple's optimized BLAS)

```python
import numpy as np
np.__config__.show()
# Look for "Accelerate" or "vecLib"
```

---

## 📚 Available Presets

| Preset | Description | Expected # Civilizations |
|--------|-------------|-------------------------|
| `early_filter` | Life emergence is extremely rare | ~10 over galaxy lifetime |
| `late_filter` | Tech civilizations self-destruct quickly | ~100 at any time (short-lived) |
| `rare_earth` | Habitable planets are extremely rare | ~50 over galaxy lifetime |
| `moderate` | **Default** - Balanced, Fermi-consistent | ~1000 over galaxy lifetime |
| `optimistic` | Life and intelligence are common | ~50,000 (NOT Fermi-consistent) |

---

## 🐛 Troubleshooting

### Slow Performance

```bash
# Check environment variables
echo $NUMBA_NUM_THREADS  # Should be 8

# If not set:
export NUMBA_NUM_THREADS=8
export OMP_NUM_THREADS=8
```

### Import Errors

```bash
# Reinstall package
pip install -e .

# Or force reinstall dependencies
micromamba install -c conda-forge numba scipy numpy --force-reinstall
```

### "Module not found"

```bash
# Make sure environment is activated
micromamba activate galaticbot

# Verify package is installed
pip list | grep galaticbot
```

---

## 📖 Full Documentation

- **INSTALL.md** - Complete installation guide (pip, conda, micromamba)
- **M1_MAX_OPTIMIZATION.md** - Performance tuning and benchmarks
- **IMPLEMENTATION_SUMMARY.md** - All changes and improvements
- **CLAUDE.md** - Project architecture and development guide
- **README.md** - Project overview and scientific background

---

## 🎓 Example Workflow

```python
from great_silence import SimulationConfig, GalaxySimulation
from great_silence.simulation import MonteCarloRunner

# 1. Start with a test run (small, fast)
config = SimulationConfig()
config.galaxy.total_stars = 100_000
config.simulation.simulation_duration_gyr = 0.1  # 100 Myr

sim = GalaxySimulation(config, seed=42)
sim.run()
print(f"Test run: {sim.get_statistics()['total_civilizations']} civilizations")

# 2. Try different scenarios
for preset in ['early_filter', 'late_filter', 'rare_earth']:
    config = SimulationConfig.with_preset(preset)
    config.galaxy.total_stars = 100_000
    config.simulation.simulation_duration_gyr = 1.0

    sim = GalaxySimulation(config, seed=42)
    sim.run()

    stats = sim.get_statistics()
    print(f"{preset}: {stats['total_civilizations']} civs, "
          f"{stats['active_civilizations']} active")

# 3. Run full Monte Carlo analysis
config = SimulationConfig.with_preset('moderate')
config.galaxy.total_stars = 1_000_000  # Larger
config.simulation.simulation_duration_gyr = 10.0
config.simulation.num_realizations = 100

runner = MonteCarloRunner(config)
results = runner.run_parallel(n_processes=8)
analysis = runner.analyze_results()

print(f"\nFinal results:")
print(f"  Mean: {analysis['total_civilizations']['mean']:.1f}")
print(f"  95% CI: [{analysis['total_civilizations']['ci_95_lower']:.1f}, "
      f"{analysis['total_civilizations']['ci_95_upper']:.1f}]")
```

---

## 🚀 Performance Tips

1. **Always enable Numba**: `config.simulation.use_numba = True` (default)
2. **Set environment variables**: `NUMBA_NUM_THREADS=8`
3. **Start small**: Test with 100K stars before scaling to 10M+
4. **Use presets**: Easier than manual parameter tuning
5. **Parallel Monte Carlo**: Leverage all 8 P-cores with `run_parallel()`
6. **Monitor memory**: Use Activity Monitor for >10M stars

---

## 💡 Tips

- **First run is slower** (Numba JIT compilation). Subsequent runs are fast.
- **Use presets** to explore different Fermi Paradox hypotheses
- **Check environment variables** if performance is slow
- **Start with 100K stars** for testing, scale up to 10M+ for production
- **Read M1_MAX_OPTIMIZATION.md** for advanced performance tuning

---

**Ready to simulate the galaxy!** 🌌

For more help: `cat INSTALL.md` or `cat M1_MAX_OPTIMIZATION.md`
