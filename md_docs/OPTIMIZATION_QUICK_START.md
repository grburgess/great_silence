# GalaticBot Optimization Quick Start Guide

This is a condensed action plan extracted from the full [PERFORMANCE_OPTIMIZATION_ANALYSIS.md](PERFORMANCE_OPTIMIZATION_ANALYSIS.md). Use this for quick reference.

---

## Top 5 Critical Bottlenecks (Fix These First)

### 1. O(N²) Distance Matrix - CRITICAL
**File:** `src/galaticbot/galaxy/structure.py:206-229`
**Problem:** Allocates 80GB for 100k stars, 80TB for 100M stars
**Fix:** Replace with spatial index queries (NEVER compute full matrix)
**Impact:** 1000-10000x speedup, enable large-scale simulations

### 2. Civilization Emergence Loop
**File:** `src/galaticbot/simulation/engine.py:162-213`
**Problem:** Python list comprehension over millions of stars every timestep
**Fix:** Vectorize with NumPy masks + Poisson thinning for rare events
**Impact:** 10-50x speedup

### 3. Supernova Hazard Evaluation
**File:** `src/galaticbot/astrophysics/hazards.py:26-76`
**Problem:** Nested Python loops, computes distances to ALL stars
**Fix:** Use spatial index + vectorized probability calculations
**Impact:** 100-1000x speedup per civilization

### 4. Rejection Sampling Loops
**Files:**
- `src/galaticbot/galaxy/structure.py:73-81` (stellar positions)
- `src/galaticbot/galaxy/star_formation.py:89-102` (stellar ages)

**Problem:** Python `for`/`while` loops over millions of stars
**Fix:** Batch rejection sampling with NumPy vectorization
**Impact:** 50-100x speedup on initialization

### 5. Missing Numba JIT Compilation
**Files:** All hot loops (position evolution, distance calculations)
**Problem:** Flag exists (`config.simulation.use_numba = True`) but zero `@jit` decorators
**Fix:** Add `@numba.jit(nopython=True, parallel=True)` to hot functions
**Impact:** 5-20x speedup on main loop

---

## Quick Win Implementation (2 Hours)

### Step 1: Add Spatial Index (10 minutes)

```python
# Edit: src/galaticbot/simulation/engine.py

# In __init__ method, add:
self.spatial_index = None

# In initialize() method, add at end:
from ..utils.spatial import SpatialIndex
print("Building spatial index...")
self.spatial_index = SpatialIndex(self.galaxy.positions)
```

### Step 2: Vectorize Civilization Emergence (30 minutes)

Replace `_check_civilization_emergence()` in `engine.py` with:

```python
def _check_civilization_emergence(self) -> None:
    """Vectorized emergence check."""
    if self.habitable_star_indices is None:
        return

    dt_myr = self.config.simulation.time_step_myr
    params = self.config.civilization

    # Drake equation
    p_emergence_per_gyr = (
        params.fraction_stars_with_planets *
        params.avg_habitable_planets_per_system *
        params.fraction_develop_life *
        params.fraction_develop_intelligence *
        params.fraction_develop_technology
    )
    p_emergence = p_emergence_per_gyr * dt_myr / 1000.0

    # VECTORIZED: Create eligibility mask
    age_mask = self.galaxy.ages > 1.0
    eligible_mask = np.zeros(len(self.galaxy.positions), dtype=bool)
    eligible_mask[self.habitable_star_indices] = True
    eligible_mask &= age_mask

    # VECTORIZED: Remove colonized stars
    if self.civilizations:
        colonized_indices = np.concatenate([
            np.array([civ.parent_star_idx] + civ.colonized_stars)
            for civ in self.civilizations
        ])
        eligible_mask[colonized_indices] = False

    eligible_stars = np.where(eligible_mask)[0]

    if len(eligible_stars) == 0:
        return

    # OPTIMIZATION: Poisson thinning for rare events
    expected = p_emergence * len(eligible_stars)

    if expected < 0.1:
        n_emergences = self.rng.poisson(expected)
        if n_emergences == 0:
            return
        emerge_indices = self.rng.choice(
            eligible_stars,
            size=min(n_emergences, len(eligible_stars)),
            replace=False
        )
    else:
        emerge = self.rng.uniform(0, 1, len(eligible_stars)) < p_emergence
        emerge_indices = eligible_stars[emerge]

    # Create civilizations
    for star_idx in emerge_indices:
        new_civ = CivilizationState(
            civ_id=self.next_civ_id,
            birth_time_myr=self.current_time_myr,
            parent_star_idx=int(star_idx),
            colonized_stars=[int(star_idx)]
        )
        self.civilizations.append(new_civ)
        self.next_civ_id += 1
```

### Step 3: Add Basic Numba to Position Evolution (30 minutes)

```python
# Edit: src/galaticbot/galaxy/structure.py

# Add at top:
import numba

# Add standalone function:
@numba.jit(nopython=True, parallel=True, fastmath=True)
def _evolve_positions_numba(
    positions: np.ndarray,
    velocities: np.ndarray,
    dt_myr: float
) -> np.ndarray:
    """Numba-accelerated position evolution."""
    v_kpc_myr = velocities * 0.001022

    for i in numba.prange(len(positions)):
        positions[i, 0] += v_kpc_myr[i, 0] * dt_myr
        positions[i, 1] += v_kpc_myr[i, 1] * dt_myr
        positions[i, 2] += v_kpc_myr[i, 2] * dt_myr

    return positions

# Modify evolve_positions method:
def evolve_positions(self, dt_myr: float) -> None:
    """Evolve stellar positions forward in time."""
    if self.positions is None or self.velocities is None:
        raise ValueError("Must generate positions and velocities first")

    # Check if Numba enabled (need to pass config)
    # For now, always use Numba
    use_numba = True

    if use_numba:
        self.positions = _evolve_positions_numba(
            self.positions.copy(),
            self.velocities,
            dt_myr
        )
    else:
        v_kpc_myr = self.velocities * 0.001022
        self.positions += v_kpc_myr * dt_myr
```

### Step 4: Vectorize Rejection Sampling (30 minutes)

```python
# Edit: src/galaticbot/galaxy/structure.py

# Replace _generate_exponential_disk method:
def _generate_exponential_disk(self, n_stars: int) -> np.ndarray:
    """Vectorized exponential disk generation."""
    h_R = self.params.scale_length_kpc
    h_z = self.params.disk_height_kpc

    # VECTORIZED: Batch rejection sampling
    r = np.zeros(n_stars)
    n_accepted = 0
    batch_size = min(n_stars * 2, 1_000_000)

    while n_accepted < n_stars:
        r_test = self.rng.exponential(h_R, batch_size)
        within_radius = r_test < self.params.disk_radius_kpc
        accept_prob = np.where(
            within_radius,
            r_test / self.params.disk_radius_kpc,
            0.0
        )

        random_uniform = self.rng.uniform(0, 1, batch_size)
        accepted = random_uniform < accept_prob

        n_to_take = min(np.sum(accepted), n_stars - n_accepted)
        accepted_indices = np.where(accepted)[0][:n_to_take]

        r[n_accepted:n_accepted + n_to_take] = r_test[accepted_indices]
        n_accepted += n_to_take

    # Vectorized coordinates
    theta = self.rng.uniform(0, 2 * np.pi, n_stars)
    z = self.rng.laplace(0, h_z, n_stars)

    x = r * np.cos(theta)
    y = r * np.sin(theta)

    return np.column_stack([x, y, z])
```

### Step 5: Test & Benchmark (30 minutes)

```python
# Create: test_optimizations.py

import time
import numpy as np
from great_silence import GalaxySimulation, SimulationConfig

def benchmark_simulation(n_stars=10_000):
    """Quick benchmark."""
    config = SimulationConfig()
    config.galaxy.total_stars = n_stars
    config.simulation.simulation_duration_gyr = 0.1  # Short test
    config.simulation.time_step_myr = 10.0
    config.simulation.save_snapshots = False

    sim = GalaxySimulation(config, seed=42)

    # Benchmark initialization
    start = time.perf_counter()
    sim.initialize()
    init_time = time.perf_counter() - start

    # Benchmark main loop
    start = time.perf_counter()
    sim.run(verbose=False)
    run_time = time.perf_counter() - start

    stats = sim.get_statistics()

    print(f"\nBenchmark Results (N={n_stars:,}):")
    print(f"  Init time: {init_time:.3f}s")
    print(f"  Run time:  {run_time:.3f}s")
    print(f"  Total civilizations: {stats['total_civilizations']}")

    return init_time, run_time

if __name__ == "__main__":
    # Test increasing sizes
    for n in [1_000, 10_000, 100_000]:
        benchmark_simulation(n)
```

**Expected Speedup After Step 5:** 20-50x faster initialization, 5-10x faster main loop

---

## Profiling Commands (Run These First)

```bash
# Install profiling tools
pip install line_profiler memory_profiler py-spy numba

# Create test script
cat > profile_test.py << 'EOF'
from great_silence import GalaxySimulation, SimulationConfig

config = SimulationConfig()
config.galaxy.total_stars = 100_000
config.simulation.simulation_duration_gyr = 0.5
config.simulation.time_step_myr = 10.0
config.simulation.save_snapshots = False

sim = GalaxySimulation(config, seed=42)
sim.run(verbose=True)
EOF

# Run CPU profiler
python -m cProfile -o profile.stats profile_test.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(30)"

# Run sampling profiler (better visualization)
pip install py-spy
py-spy record -o profile.svg --format speedscope -- python profile_test.py
# Open profile.svg in browser
```

**Look for:**
- `_generate_exponential_disk`: Should be 30-40% of init time (OPTIMIZE THIS)
- `_check_civilization_emergence`: Should be 20-30% of loop time (OPTIMIZE THIS)
- `generate_stellar_ages`: Should be 15-20% of init time (OPTIMIZE THIS)

---

## Phase-by-Phase Roadmap

### Phase 1: Quick Wins (2 hours) - START HERE
- ✓ Vectorize rejection sampling
- ✓ Vectorize civilization emergence
- ✓ Add spatial index initialization
- ✓ Basic Numba for position evolution

**Expected:** 20-50x speedup, enable N=1M stars

### Phase 2: Numba Integration (1 day)
- Add Numba to distance calculations
- Add Numba to supernova rate computation
- Add Numba to IMF sampling
- Add configuration flag checking

**Expected:** 10-20x additional speedup

### Phase 3: Spatial Index Usage (2 days)
- Implement vectorized hazard evaluation
- Integrate spatial index into hazard checks
- Implement `_apply_hazards()` method
- Add adaptive spatial index rebuild

**Expected:** 100-1000x speedup on hazard-heavy workloads

### Phase 4: Memory Optimization (1 day)
- Switch to float32 for velocities/ages/masses
- Remove `get_distance_matrix()` method entirely
- Add memory-mapped arrays for N>10M
- Optimize civilization data structures

**Expected:** 2x memory reduction, enable N=100M

### Phase 5: GPU Acceleration (Optional, 2 days)
- Add PyTorch MPS backend
- Move position evolution to GPU
- Move distance calculations to GPU
- Add automatic CPU/GPU selection

**Expected:** 5-20x additional speedup on M1/M2/M3

---

## Common Pitfalls to Avoid

1. **Don't call `get_distance_matrix()` without indices**
   - Will crash for N>10k stars
   - Use spatial index queries instead

2. **Don't forget to rebuild spatial index**
   - After `evolve_positions()`, KD-tree is stale
   - Rebuild every 10-100 timesteps (not every step)

3. **Numba limitations**
   - Can't use `self` in `@jit` functions (extract to standalone)
   - Can't use `np.random.default_rng()` (use `np.random.seed()` legacy)
   - Can't use Python lists/dicts in nopython mode (use NumPy arrays)

4. **Validate numerical accuracy**
   - After each optimization, compare results with seed=42
   - Use `np.testing.assert_allclose()` for positions

5. **Profile before optimizing**
   - Don't guess bottlenecks - measure them
   - Use py-spy for visual flamegraphs

---

## Performance Targets

| Optimization Phase | N=100k Init | N=100k Timestep | N=1M Init | N=1M Timestep |
|-------------------|-------------|-----------------|-----------|---------------|
| **Baseline**      | 5 min       | 5s              | 50 min    | 50s           |
| **Phase 1**       | 5s          | 0.5s            | 50s       | 5s            |
| **Phase 2**       | 5s          | 0.1s            | 50s       | 1s            |
| **Phase 3**       | 5s          | 0.1s            | 50s       | 1s            |
| **Phase 4**       | 5s          | 0.1s            | 50s       | 1s            |
| **Phase 5 (GPU)** | 5s          | 0.05s           | 50s       | 0.2s          |

**Milestone:** After Phase 1, you should be able to run N=1M star simulations in ~1 hour for 1 Gyr.

---

## Questions to Ask While Optimizing

1. **Is this operation O(N²)?**
   - If yes, can I use a spatial index? (usually yes)

2. **Is this a Python loop?**
   - If yes, can I vectorize with NumPy? (usually yes)

3. **Is this function called in the main loop?**
   - If yes, can I apply Numba? (often yes)

4. **Does this allocate a large temporary array?**
   - If yes, can I use in-place operations? (sometimes)

5. **Am I computing the same thing multiple times?**
   - If yes, can I cache it? (depends on memory)

---

## Getting Help

See full analysis in [PERFORMANCE_OPTIMIZATION_ANALYSIS.md](PERFORMANCE_OPTIMIZATION_ANALYSIS.md) for:
- Detailed code examples (Section 11)
- Complete Numba implementation patterns (Section 2)
- Apple Silicon specific optimizations (Section 4)
- Memory optimization strategies (Section 5)
- Validation and testing approaches (Section 10)

---

**Last Updated:** 2025-12-26
**Start with Phase 1 - should take ~2 hours and provide 20-50x speedup!**
