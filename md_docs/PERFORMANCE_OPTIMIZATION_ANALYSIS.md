# GalaticBot Performance Optimization Analysis
## Apple Silicon (M1/M2/M3) Optimization Strategy

**Generated:** 2025-12-26
**Target Hardware:** Apple Silicon (M1/M2/M3 processors with ARM64 architecture)
**Codebase Version:** Analyzed from /Users/jburgess/coding/projects/galaticbot

---

## Executive Summary

This analysis identifies critical performance bottlenecks in the GalaticBot galactic civilization simulation and provides specific, actionable optimization strategies for Apple Silicon. The simulation has excellent architectural separation but several O(N²) operations and missing Numba JIT compilation that will severely limit scalability beyond 100k stars.

**Key Findings:**
- **Critical Bottleneck #1:** O(N²) distance matrix computation in `galaxy/structure.py:get_distance_matrix()` (lines 206-229)
- **Critical Bottleneck #2:** Civilization emergence checking all habitable stars every timestep (engine.py:162-213)
- **Critical Bottleneck #3:** Supernova hazard evaluation with nested loops (hazards.py:26-76)
- **Critical Bottleneck #4:** Rejection sampling loops in star generation (structure.py:73-81, star_formation.py:89-102)
- **Missing Optimization:** Numba flag exists but zero `@jit` decorators applied
- **Spatial Indexing:** KD-tree infrastructure exists but underutilized

**Performance Impact Estimates (N=100M stars):**
- Current implementation: ~500 GB RAM for distance matrix, hours per timestep
- With optimizations: ~8 GB RAM, seconds per timestep (100-1000x speedup)

---

## 1. Critical Bottlenecks (Prioritized by Impact)

### 1.1 CRITICAL: O(N²) Distance Matrix Computation

**Location:** `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/galaxy/structure.py:206-229`

```python
def get_distance_matrix(self, indices: Optional[np.ndarray] = None) -> np.ndarray:
    """O(N²) memory and compute - CRITICAL BOTTLENECK"""
    if indices is not None:
        pos = self.positions[indices]
    else:
        pos = self.positions  # Could be 100M stars!

    # Broadcasting creates (N, N, 3) array - HUGE memory usage
    diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]  # O(N²) memory
    dist_kpc = np.sqrt(np.sum(diff**2, axis=2))  # O(N²) compute
    return dist_kpc * 1000.0
```

**Problem:**
- For N=100M stars: (100M × 100M × 8 bytes) = 80,000 TB (impossible)
- For N=100k stars: (100k × 100k × 8 bytes) = 80 GB (will swap/crash)
- For N=10k stars: (10k × 10k × 8 bytes) = 800 MB (workable but slow)

**Impact:** This function is currently NOT called in main loop (placeholder expansion model), but will become catastrophic bottleneck when expansion is implemented.

**Solution:** Never compute full distance matrix. Use spatial indexing instead.

```python
# OPTIMIZED VERSION - Replace entire function
def get_nearby_stars(
    self,
    center_idx: int,
    radius_kpc: float,
    spatial_index: Optional[SpatialIndex] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Get stars within radius of a center star.

    O(log N) query time, O(1) memory for results.

    Returns:
        indices: Star indices within radius
        distances_kpc: Distances to those stars
    """
    if spatial_index is None:
        spatial_index = SpatialIndex(self.positions)

    center_pos = self.positions[center_idx]
    indices, distances = spatial_index.query_radius(
        center_pos, radius_kpc, return_distances=True
    )
    return indices, distances
```

**Memory Reduction:** 80 GB → ~1 MB (for typical queries)
**Compute Reduction:** O(N²) → O(log N) per query
**Speedup:** 1000-10000x for sparse queries

---

### 1.2 CRITICAL: Civilization Emergence Inefficiency

**Location:** `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/simulation/engine.py:162-213`

```python
def _check_civilization_emergence(self) -> None:
    """Checks ALL habitable stars EVERY timestep - inefficient"""
    # ...
    eligible_stars = self.habitable_star_indices[
        self.galaxy.ages[self.habitable_star_indices] > 1.0
    ]  # Could be millions of stars

    # Filter out colonized (O(M * C) where C = colonized stars)
    colonized = set()
    for civ in self.civilizations:
        colonized.add(civ.parent_star_idx)
        colonized.update(civ.colonized_stars)

    # Python list comprehension over potentially millions of stars
    eligible_stars = np.array([s for s in eligible_stars if s not in colonized])

    # Sample emergence for ALL eligible stars
    emerge = self.rng.uniform(0, 1, len(eligible_stars)) < p_emergence
```

**Problems:**
1. **List comprehension** creates Python loop over millions of stars (slow)
2. **Set membership checks** are O(1) but in tight loop
3. **Uniform random sampling** for millions of stars every timestep (wasteful)
4. Probability `p_emergence` is typically ~1e-6, so most computation is wasted

**Current Complexity:** O(H * C) where H=habitable stars, C=colonized stars
**With 1M habitable stars, 1000 colonies:** ~1B operations per timestep

**Solution 1: Vectorized Set Operations**

```python
# OPTIMIZED VERSION
def _check_civilization_emergence(self) -> None:
    """Vectorized emergence check with early termination."""
    if self.habitable_star_indices is None:
        return

    dt_myr = self.config.simulation.time_step_myr
    params = self.config.civilization

    # Drake equation probability
    p_emergence_per_gyr = (
        params.fraction_stars_with_planets *
        params.avg_habitable_planets_per_system *
        params.fraction_develop_life *
        params.fraction_develop_intelligence *
        params.fraction_develop_technology
    )
    p_emergence = p_emergence_per_gyr * dt_myr / 1000.0

    # OPTIMIZATION 1: Vectorized age filter
    age_mask = self.galaxy.ages > 1.0
    eligible_mask = np.zeros(len(self.galaxy.positions), dtype=bool)
    eligible_mask[self.habitable_star_indices] = True
    eligible_mask &= age_mask

    # OPTIMIZATION 2: Vectorized colonization filter
    if self.civilizations:
        colonized_indices = np.concatenate([
            np.array([civ.parent_star_idx] + civ.colonized_stars)
            for civ in self.civilizations
        ])
        eligible_mask[colonized_indices] = False

    eligible_stars = np.where(eligible_mask)[0]

    if len(eligible_stars) == 0:
        return

    # OPTIMIZATION 3: Expected value filtering (Poisson thinning)
    # If p is very small, sample number of emergences from Poisson
    expected_emergences = p_emergence * len(eligible_stars)

    if expected_emergences < 0.1:
        # Very rare event - use Poisson sampling
        n_emergences = self.rng.poisson(expected_emergences)
        if n_emergences == 0:
            return
        # Randomly select which stars get civilizations
        emerge_indices = self.rng.choice(
            eligible_stars, size=min(n_emergences, len(eligible_stars)), replace=False
        )
    else:
        # Standard Bernoulli sampling (when p is not too small)
        emerge = self.rng.uniform(0, 1, len(eligible_stars)) < p_emergence
        emerge_indices = eligible_stars[emerge]

    # Create new civilizations
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

**Speedup:** 10-50x (depending on number of civilizations)
**Memory:** Constant overhead
**Complexity:** O(H + C) instead of O(H * C)

---

### 1.3 HIGH PRIORITY: Supernova Hazard Evaluation

**Location:** `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/astrophysics/hazards.py:26-76`

```python
def evaluate_supernova_hazard(...) -> bool:
    """Has nested loops and inefficient distance computation."""
    # PROBLEM 1: Computes distances to ALL stars for EACH civilization
    distances_kpc = np.linalg.norm(
        stellar_positions - civilization_position, axis=1
    )  # This is OK - vectorized
    distances_pc = distances_kpc * 1000

    nearby_mask = distances_pc < self.params.sn_sterilization_range_pc

    if not np.any(nearby_mask):
        return False

    # PROBLEM 2: Python loop over nearby stars (could be thousands)
    for i in np.where(nearby_mask)[0]:
        rate = self.sn_model.supernova_rate_per_star(
            stellar_masses[i], stellar_ages[i]
        )
        p_sn = rate * dt_myr * 1e6

        if rng.uniform(0, 1) < p_sn:
            p_sterilize = self.sn_model.sterilization_probability(distances_pc[i])
            if rng.uniform(0, 1) < p_sterilize:
                return True

    return False
```

**Problems:**
1. **Python loop** over nearby stars (slow)
2. **Called for every active civilization every timestep** - no spatial indexing
3. Random number generation in loop (not vectorized)

**Current Complexity:** O(C * N) where C=civilizations, N=total stars
**With 1000 civs, 100M stars:** 100B operations per timestep (catastrophic)

**Solution: Vectorized Hazard Evaluation + Spatial Index**

```python
# OPTIMIZED VERSION - Add to HazardEvaluator
def evaluate_supernova_hazard_vectorized(
    self,
    civilization_position: np.ndarray,
    stellar_positions: np.ndarray,
    stellar_masses: np.ndarray,
    stellar_ages: np.ndarray,
    dt_myr: float,
    rng: np.random.Generator,
    spatial_index: Optional[SpatialIndex] = None
) -> bool:
    """
    Vectorized supernova hazard evaluation.

    Uses spatial index to reduce from O(N) to O(log N) per civilization.
    """
    # OPTIMIZATION 1: Use spatial index to find nearby stars
    if spatial_index is None:
        spatial_index = SpatialIndex(stellar_positions)

    # Only check stars within sterilization range
    range_kpc = self.params.sn_sterilization_range_pc / 1000.0
    nearby_indices, distances_kpc = spatial_index.query_radius(
        civilization_position, range_kpc, return_distances=True
    )

    if len(nearby_indices) == 0:
        return False

    distances_pc = distances_kpc * 1000.0

    # OPTIMIZATION 2: Vectorized supernova rate computation
    # Only massive stars go supernova
    nearby_masses = stellar_masses[nearby_indices]
    nearby_ages = stellar_ages[nearby_indices]
    massive_mask = nearby_masses >= 8.0

    if not np.any(massive_mask):
        return False

    # Vectorized main sequence lifetime calculation
    massive_indices = np.where(massive_mask)[0]
    masses = nearby_masses[massive_mask]
    ages = nearby_ages[massive_mask]
    dists = distances_pc[massive_mask]

    # t_ms ∝ M^(-2.5)
    t_ms_gyr = 10.0 * masses**(-2.5)

    # Supernova rate (Gaussian around t_ms)
    rates = np.exp(-((ages - t_ms_gyr) / 0.01)**2)

    # OPTIMIZATION 3: Vectorized probability calculation
    p_sn = rates * dt_myr * 1e6

    # OPTIMIZATION 4: Vectorized sterilization probability
    # Split by lethal vs sterilization range
    lethal_mask = dists < self.params.sn_lethal_range_pc

    # Calculate sterilization probabilities
    p_sterilize = np.ones_like(dists)
    partial_mask = ~lethal_mask & (dists < self.params.sn_sterilization_range_pc)

    if np.any(partial_mask):
        r = ((dists[partial_mask] - self.params.sn_lethal_range_pc) /
             (self.params.sn_sterilization_range_pc - self.params.sn_lethal_range_pc))
        p_sterilize[partial_mask] = np.exp(-3 * r)

    p_sterilize[~lethal_mask & ~partial_mask] = 0.0

    # Combined probability
    p_destruction = p_sn * p_sterilize

    # OPTIMIZATION 5: Single vectorized random draw
    # Any supernova destroys civilization
    random_draws = rng.uniform(0, 1, len(p_destruction))
    destroyed = np.any(random_draws < p_destruction)

    return destroyed
```

**Speedup:** 100-1000x per civilization
**Complexity:** O(log N + M) where M=nearby massive stars (typically < 100)
**Memory:** O(M) instead of O(N)

---

### 1.4 MEDIUM PRIORITY: Rejection Sampling Loops

**Location 1:** `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/galaxy/structure.py:73-81`

```python
# CURRENT: Python loop for rejection sampling radii
for i in range(n_stars):
    while True:
        r_test = self.rng.exponential(h_R)
        if r_test < self.params.disk_radius_kpc:
            if self.rng.uniform(0, 1) < r_test / self.params.disk_radius_kpc:
                r[i] = r_test
                break
```

**Problem:** Python `for` loop over potentially millions of stars, nested `while` loop

**Solution: Vectorized Rejection Sampling**

```python
# OPTIMIZED VERSION
def _generate_exponential_disk_vectorized(self, n_stars: int) -> np.ndarray:
    """
    Vectorized exponential disk generation.

    Uses batch rejection sampling to eliminate Python loops.
    """
    h_R = self.params.scale_length_kpc
    h_z = self.params.disk_height_kpc

    # OPTIMIZATION: Vectorized rejection sampling for radii
    # For 2D exponential: P(r) ∝ r * exp(-r/h_R)
    # Use inverse transform sampling with approximation or batch rejection

    r = np.zeros(n_stars)
    n_accepted = 0
    batch_size = n_stars * 2  # Oversample to reduce iterations

    while n_accepted < n_stars:
        # Generate batch of candidates
        r_test = self.rng.exponential(h_R, batch_size)

        # Vectorized acceptance criterion
        within_radius = r_test < self.params.disk_radius_kpc
        accept_prob = r_test / self.params.disk_radius_kpc
        accept_prob[~within_radius] = 0.0

        random_uniform = self.rng.uniform(0, 1, batch_size)
        accepted = random_uniform < accept_prob

        # Take what we need
        n_to_take = min(np.sum(accepted), n_stars - n_accepted)
        accepted_indices = np.where(accepted)[0][:n_to_take]

        r[n_accepted:n_accepted + n_to_take] = r_test[accepted_indices]
        n_accepted += n_to_take

    # Vectorized coordinate conversion
    theta = self.rng.uniform(0, 2 * np.pi, n_stars)
    z = self.rng.laplace(0, h_z, n_stars)

    x = r * np.cos(theta)
    y = r * np.sin(theta)

    return np.column_stack([x, y, z])
```

**Speedup:** 50-100x for large N
**Complexity:** O(N) vectorized instead of O(N) in Python loops

---

**Location 2:** `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/galaxy/star_formation.py:89-102`

```python
# CURRENT: Rejection sampling for stellar ages
while len(ages) < n_stars:
    age = rng.uniform(0, max_age_gyr)
    sfr_at_age = self.sfr(age)
    if rng.uniform(0, max_sfr) < sfr_at_age:
        ages.append(age)
```

**Solution: Same batch rejection sampling pattern**

```python
def generate_stellar_ages_vectorized(
    self, n_stars: int, max_age_gyr: float = 13.0, seed: Optional[int] = None
) -> np.ndarray:
    """Vectorized stellar age generation using batch rejection sampling."""
    rng = np.random.default_rng(seed)

    max_sfr = self.sfr(self.params.sfr_peak_age_gyr)
    ages = np.zeros(n_stars)
    n_accepted = 0

    # Expected acceptance rate ~50%, so oversample by 2x
    batch_size = n_stars * 2

    while n_accepted < n_stars:
        # Vectorized sampling
        age_candidates = rng.uniform(0, max_age_gyr, batch_size)

        # Vectorized SFR evaluation
        tau = self.params.sfr_peak_age_gyr / 2.0
        sfr_values = (age_candidates / tau**2) * np.exp(-age_candidates / tau)

        # Normalize
        sfr_current = (13.0 / tau**2) * np.exp(-13.0 / tau)
        normalization = self.params.current_sfr_msun_yr / sfr_current
        sfr_values *= normalization

        # Vectorized acceptance
        random_uniform = rng.uniform(0, max_sfr, batch_size)
        accepted = random_uniform < sfr_values

        n_to_take = min(np.sum(accepted), n_stars - n_accepted)
        accepted_indices = np.where(accepted)[0][:n_to_take]

        ages[n_accepted:n_accepted + n_to_take] = age_candidates[accepted_indices]
        n_accepted += n_to_take

    return ages
```

**Speedup:** 20-50x

---

## 2. Numba JIT Optimization Opportunities

The codebase has `config.simulation.use_numba = True` flag but **ZERO** `@jit` decorators applied. This is a missed opportunity for easy 5-50x speedups.

### 2.1 High-Priority Numba Targets

**Target 1: Stellar Position Evolution** (engine.py:186-204)

```python
# ADD TO galaxy/structure.py
import numba

@numba.jit(nopython=True, parallel=True, fastmath=True)
def _evolve_positions_numba(
    positions: np.ndarray,
    velocities: np.ndarray,
    dt_myr: float
) -> np.ndarray:
    """
    Numba-accelerated position evolution.

    Args:
        positions: (N, 3) array of positions in kpc
        velocities: (N, 3) array of velocities in km/s
        dt_myr: Time step in Myr

    Returns:
        Updated positions
    """
    # Convert velocities from km/s to kpc/Myr
    # 1 km/s = 0.001022 kpc/Myr
    v_kpc_myr = velocities * 0.001022

    # Update positions (parallelized across stars)
    for i in numba.prange(len(positions)):
        positions[i, 0] += v_kpc_myr[i, 0] * dt_myr
        positions[i, 1] += v_kpc_myr[i, 1] * dt_myr
        positions[i, 2] += v_kpc_myr[i, 2] * dt_myr

    return positions

# Modify evolve_positions method
def evolve_positions(self, dt_myr: float) -> None:
    """Evolve stellar positions forward in time."""
    if self.positions is None or self.velocities is None:
        raise ValueError("Must generate positions and velocities first")

    if self.config.simulation.use_numba:
        self.positions = _evolve_positions_numba(
            self.positions, self.velocities, dt_myr
        )
    else:
        # Fallback to NumPy
        v_kpc_myr = self.velocities * 0.001022
        self.positions += v_kpc_myr * dt_myr
```

**Expected Speedup:** 5-10x (Numba parallel + fastmath)
**Compilation Overhead:** ~1 second first call, amortized over many timesteps

---

**Target 2: Supernova Rate Calculation**

```python
# ADD TO astrophysics/supernovae.py
import numba

@numba.jit(nopython=True, fastmath=True)
def _compute_supernova_rates_numba(
    stellar_masses: np.ndarray,
    stellar_ages: np.ndarray
) -> np.ndarray:
    """
    Vectorized supernova rate calculation with Numba.

    Returns:
        Array of supernova rates (per year) for each star
    """
    n_stars = len(stellar_masses)
    rates = np.zeros(n_stars)

    for i in range(n_stars):
        mass = stellar_masses[i]
        age = stellar_ages[i]

        # Only massive stars
        if mass < 8.0:
            continue

        # Main sequence lifetime
        t_ms_gyr = 10.0 * mass**(-2.5)

        # Gaussian around t_ms
        if age >= t_ms_gyr:
            rates[i] = np.exp(-((age - t_ms_gyr) / 0.01)**2)

    return rates
```

**Expected Speedup:** 10-20x

---

**Target 3: Distance Calculations**

```python
# ADD TO utils/spatial.py or new utils/numba_kernels.py
import numba

@numba.jit(nopython=True, parallel=True, fastmath=True)
def compute_distances_to_point_numba(
    positions: np.ndarray,
    point: np.ndarray,
    max_distance: float = np.inf
) -> np.ndarray:
    """
    Compute distances from all positions to a single point.

    Early termination if max_distance specified.

    Args:
        positions: (N, 3) array
        point: (3,) array
        max_distance: Early termination threshold (kpc)

    Returns:
        distances: (N,) array in kpc
    """
    n = len(positions)
    distances = np.zeros(n)

    for i in numba.prange(n):
        dx = positions[i, 0] - point[0]
        dy = positions[i, 1] - point[1]
        dz = positions[i, 2] - point[2]

        dist = np.sqrt(dx*dx + dy*dy + dz*dz)
        distances[i] = dist

    return distances

@numba.jit(nopython=True, parallel=True, fastmath=True)
def find_nearby_indices_numba(
    positions: np.ndarray,
    point: np.ndarray,
    radius: float
) -> np.ndarray:
    """
    Find all positions within radius of point.

    Note: Returns variable-length result, so we return mask instead.

    Args:
        positions: (N, 3) array
        point: (3,) array
        radius: Search radius (kpc)

    Returns:
        mask: (N,) boolean array
    """
    n = len(positions)
    mask = np.zeros(n, dtype=np.bool_)
    radius_sq = radius * radius

    for i in numba.prange(n):
        dx = positions[i, 0] - point[0]
        dy = positions[i, 1] - point[1]
        dz = positions[i, 2] - point[2]

        dist_sq = dx*dx + dy*dy + dz*dz

        if dist_sq <= radius_sq:
            mask[i] = True

    return mask
```

**Expected Speedup:** 10-30x for large arrays
**Use Case:** Replace loops in hazard evaluation

---

### 2.2 Numba Limitations and Workarounds

**Numba Cannot Compile:**
- Class methods with `self` (workaround: extract to standalone function)
- Dictionaries, sets in nopython mode (workaround: use NumPy arrays)
- Python lists with variable types (workaround: use NumPy arrays)
- Random number generators from `np.random.default_rng()` (workaround: use `np.random` legacy interface or pass seed)

**Numba-Compatible Random Numbers:**

```python
@numba.jit(nopython=True)
def random_sample_numba(n: int, seed: int) -> np.ndarray:
    """Numba-compatible random number generation."""
    np.random.seed(seed)
    return np.random.random(n)
```

---

## 3. Spatial Indexing Strategy

### 3.1 Current State

The `SpatialIndex` class exists (`/Users/jburgess/coding/projects/galaticbot/src/galaticbot/utils/spatial.py`) but is **NOT USED** in the main simulation loop.

**Current Usage:** Zero imports in engine.py or hazards.py

### 3.2 Integration Plan

**Step 1: Build Spatial Index on Initialization**

```python
# MODIFY engine.py initialize() method
def initialize(self) -> None:
    """Initialize galaxy and stellar population."""
    print("Initializing galaxy...")
    self.galaxy.generate_stellar_population()

    # ... existing code ...

    # NEW: Build spatial index for fast queries
    from ..utils.spatial import SpatialIndex
    print("Building spatial index...")
    self.spatial_index = SpatialIndex(self.galaxy.positions)
    print("Spatial index built.")
```

**Step 2: Rebuild Spatial Index After Position Updates**

```python
# MODIFY engine.py run() main loop
while self.current_time_myr < self.config.simulation.simulation_duration_gyr * 1000:
    # Evolve galaxy (stellar motion)
    self.galaxy.evolve_positions(self.config.simulation.time_step_myr)

    # NEW: Rebuild spatial index after positions change
    # Note: For small timesteps, positions change slowly, could rebuild less frequently
    if self.current_time_myr % 100.0 < self.config.simulation.time_step_myr:
        # Rebuild every 100 Myr
        self.spatial_index = SpatialIndex(self.galaxy.positions)

    # ... rest of loop ...
```

**Optimization:** KD-tree rebuild is O(N log N), which may be expensive for large N. If stellar positions change slowly, can rebuild less frequently (e.g., every 10-100 timesteps).

**Step 3: Use Spatial Index in Hazard Evaluation**

Pass `self.spatial_index` to all hazard evaluation calls:

```python
def _apply_hazards(self) -> None:
    """Apply astrophysical hazards using spatial index."""
    from ..astrophysics.hazards import HazardEvaluator

    if not hasattr(self, 'hazard_evaluator'):
        self.hazard_evaluator = HazardEvaluator(self.config.astrophysics)

    dt_myr = self.config.simulation.time_step_myr

    for civ in self.civilizations:
        if not civ.is_active:
            continue

        civ_pos = self.galaxy.positions[civ.parent_star_idx]

        # Check supernova hazard with spatial index
        destroyed_by_sn = self.hazard_evaluator.evaluate_supernova_hazard_vectorized(
            civ_pos,
            self.galaxy.positions,
            self.galaxy.masses,
            self.galaxy.ages,
            dt_myr,
            self.rng,
            spatial_index=self.spatial_index  # NEW
        )

        if destroyed_by_sn:
            civ.is_active = False
            civ.death_time_myr = self.current_time_myr
            civ.death_cause = 'supernova'
            continue

        # Check GRB hazard
        destroyed_by_grb = self.hazard_evaluator.evaluate_grb_hazard(
            civ_pos, dt_myr, self.rng
        )

        if destroyed_by_grb:
            civ.is_active = False
            civ.death_time_myr = self.current_time_myr
            civ.death_cause = 'grb'
```

---

### 3.3 Spatial Index Performance Characteristics

**cKDTree Build Time:** O(N log N)
- N=100k: ~10 ms
- N=1M: ~150 ms
- N=10M: ~2 seconds
- N=100M: ~30 seconds

**cKDTree Query Time:** O(log N + M) where M=results
- Typical range query (100 pc sphere in galaxy): M ~ 10-1000 stars
- Query time: ~0.1-1 ms regardless of N

**Strategy:** Amortize build cost across multiple timesteps if positions evolve slowly.

---

## 4. Apple Silicon Specific Optimizations

### 4.1 Accelerate Framework (BLAS/LAPACK)

**Current State:** NumPy on macOS automatically uses Apple's Accelerate framework for BLAS/LAPACK operations. No action needed.

**Verify:**

```bash
python -c "import numpy as np; np.show_config()"
```

Should show `accelerate` in BLAS/LAPACK configuration.

**Benefit:** Matrix operations (dot products, linear algebra) already optimized for Apple Silicon.

---

### 4.2 ARM64 NEON SIMD

**Current State:** NumPy's universal functions (ufuncs) automatically use ARM64 NEON SIMD instructions.

**How to Maximize Benefit:**
1. Use NumPy vectorized operations (already doing this well)
2. Avoid Python loops (addressed in Section 1)
3. Use contiguous arrays (`np.ascontiguousarray()` if needed)
4. Align data to 16-byte boundaries (NumPy does this automatically)

**Check Array Contiguity:**

```python
# Add to performance-critical sections
assert positions.flags['C_CONTIGUOUS'], "Array not contiguous!"
```

---

### 4.3 Unified Memory Architecture

Apple Silicon has unified memory (CPU and GPU share same RAM). This is beneficial for:

1. **Large arrays:** No CPU↔GPU copy overhead if using Metal
2. **Memory mapping:** Can use memory-mapped arrays for out-of-core computation

**Potential Use:** For N>100M stars, use memory-mapped NumPy arrays:

```python
# For very large simulations
positions = np.memmap(
    'positions.dat',
    dtype='float64',
    mode='r+',
    shape=(100_000_000, 3)
)
```

**Benefit:** Positions array stays on disk, OS pages in/out as needed. With unified memory, this is very efficient.

---

### 4.4 Metal Performance Shaders (GPU Acceleration)

**Current State:** Not using GPU.

**Opportunity:** Distance calculations and particle evolution are embarrassingly parallel → ideal for GPU.

**Implementation Strategy:**

1. **Use PyTorch with MPS backend:**

```python
import torch

# Check MPS availability
assert torch.backends.mps.is_available(), "MPS not available"

# Convert to MPS tensor
positions_torch = torch.from_numpy(self.positions).to('mps')
velocities_torch = torch.from_numpy(self.velocities).to('mps')

# Position evolution on GPU
dt_myr_tensor = torch.tensor(dt_myr, device='mps')
positions_torch += velocities_torch * 0.001022 * dt_myr_tensor

# Copy back
self.positions = positions_torch.cpu().numpy()
```

2. **Use Metal Compute Shaders (via `pyobjc-framework-Metal`):**

More complex but maximum performance. Write kernels in Metal Shading Language.

**Recommendation:** Start with PyTorch MPS for quick wins, only use raw Metal if needed.

**Expected Speedup:** 5-20x for position evolution, distance calculations on M1/M2/M3

---

### 4.5 Performance vs Efficiency Cores

Apple Silicon has P-cores (performance) and E-cores (efficiency).

**Current Threading Model:**
- NumPy BLAS uses all cores
- Numba `parallel=True` uses all cores
- `ProcessPoolExecutor` uses all cores

**Optimization:** Pin computation to P-cores for latency-critical tasks.

```python
import os

# Force use of only P-cores (M1 Pro has 8 P-cores + 2 E-cores)
# Set thread count to number of P-cores
os.environ['OMP_NUM_THREADS'] = '8'  # Adjust for your chip
os.environ['OPENBLAS_NUM_THREADS'] = '8'
os.environ['MKL_NUM_THREADS'] = '8'
os.environ['NUMBA_NUM_THREADS'] = '8'
```

**Caveat:** This reduces throughput but improves latency. Use for interactive work.

---

## 5. Memory Optimization

### 5.1 Current Memory Usage (Estimated)

For N=100M stars:

```
positions:    100M × 3 × 8 bytes = 2.4 GB
velocities:   100M × 3 × 8 bytes = 2.4 GB
ages:         100M × 8 bytes     = 800 MB
masses:       100M × 8 bytes     = 800 MB
stellar_types: 100M × 4 bytes    = 400 MB
-------------------------------------------------
Total:                            ~6.8 GB
```

This is manageable on M1/M2/M3 with 16-64 GB RAM.

**However:** If `get_distance_matrix()` is called without indices:
```
distance_matrix: 100M × 100M × 8 bytes = 80 PB (IMPOSSIBLE)
```

**Solution:** NEVER allocate full distance matrix (covered in Section 1.1).

---

### 5.2 Data Type Optimization

**Current:** All arrays are `float64` (8 bytes)

**Opportunity:** Use `float32` (4 bytes) where precision isn't critical.

**Analysis:**
- **Positions:** Keep `float64` (need ~1 pc precision across 15 kpc galaxy → 7 digits)
- **Velocities:** Can use `float32` (velocity precision ~0.1 km/s is fine)
- **Ages/Masses:** Can use `float32` (1% precision is sufficient)

**Implementation:**

```python
# Modify galaxy/structure.py initialization
self.velocities = np.zeros((n_stars, 3), dtype=np.float32)
self.ages = np.zeros(n_stars, dtype=np.float32)
self.masses = np.ones(n_stars, dtype=np.float32)
```

**Memory Savings:** 50% for velocities, ages, masses → ~2 GB saved for N=100M

---

### 5.3 Sparse Civilization Data

**Current:** `CivilizationState` stores `colonized_stars` as Python list.

**Problem:** For 1000 civilizations with 1000 colonies each = 1M entries in Python lists (inefficient)

**Solution:** Use NumPy structured arrays or Pandas DataFrame

```python
# Alternative implementation
import pandas as pd

class GalaxySimulation:
    def __init__(self, ...):
        # ...
        # Replace list of CivilizationState with DataFrame
        self.civilizations_df = pd.DataFrame(columns=[
            'civ_id', 'birth_time_myr', 'parent_star_idx',
            'is_active', 'death_time_myr', 'death_cause'
        ])

        # Store colonized stars in separate array
        # (civ_id, star_idx) pairs
        self.colony_mapping = []  # Or use sparse matrix
```

**Benefit:** Faster filtering, vectorized operations on civilization properties

---

## 6. Monte Carlo Parallelization

### 6.1 Current Implementation

`/Users/jburgess/coding/projects/galaticbot/src/galaticbot/simulation/monte_carlo.py:50-75`

Uses `ProcessPoolExecutor` correctly - good!

```python
with ProcessPoolExecutor(max_workers=n_processes) as executor:
    futures = [
        executor.submit(self.run_single_realization, i)
        for i in range(n_realizations)
    ]
```

**This is optimal.** Each realization is independent, perfect for process-based parallelism.

---

### 6.2 Tuning for Apple Silicon

**Problem:** Process creation overhead on macOS can be high.

**Solution 1: Larger Batch Sizes**

Instead of submitting individual realizations, batch them:

```python
def run_batch(self, realization_ids: List[int]) -> List[Dict[str, Any]]:
    """Run multiple realizations in one process."""
    return [self.run_single_realization(i) for i in realization_ids]

def run_parallel_batched(self, n_processes: Optional[int] = None) -> List[Dict[str, Any]]:
    """Run with batching to reduce process overhead."""
    n_realizations = self.config.simulation.num_realizations

    if n_processes is None:
        import os
        n_processes = os.cpu_count()

    # Batch realizations
    batch_size = max(1, n_realizations // (n_processes * 4))  # 4 batches per process
    batches = [
        list(range(i, min(i + batch_size, n_realizations)))
        for i in range(0, n_realizations, batch_size)
    ]

    print(f"Running {n_realizations} realizations in {len(batches)} batches...")

    with ProcessPoolExecutor(max_workers=n_processes) as executor:
        futures = [executor.submit(self.run_batch, batch) for batch in batches]

        results = []
        for future in tqdm(as_completed(futures), total=len(batches)):
            results.extend(future.result())

    self.results = results
    return results
```

**Benefit:** Reduces process creation overhead by 4x

---

**Solution 2: Shared Memory for Galaxy Data**

**Problem:** Each process creates its own copy of stellar positions (2.4 GB × N processes)

**Solution:** Use shared memory arrays (Python 3.8+)

```python
from multiprocessing import shared_memory
import numpy as np

class MonteCarloRunner:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.results = []
        self.shared_mem = None

    def _create_shared_galaxy_data(self, sim: GalaxySimulation):
        """Create shared memory for galaxy positions."""
        positions = sim.galaxy.positions

        # Create shared memory block
        shm = shared_memory.SharedMemory(create=True, size=positions.nbytes)

        # Create numpy array backed by shared memory
        shared_positions = np.ndarray(
            positions.shape, dtype=positions.dtype, buffer=shm.buf
        )
        shared_positions[:] = positions[:]

        return shm, positions.shape, positions.dtype

    def run_single_realization_shared(
        self,
        realization_id: int,
        shm_name: str,
        shape: tuple,
        dtype: np.dtype
    ) -> Dict[str, Any]:
        """Run realization using shared memory positions."""
        # Access existing shared memory
        shm = shared_memory.SharedMemory(name=shm_name)
        positions = np.ndarray(shape, dtype=dtype, buffer=shm.buf)

        # Create simulation with shared positions
        seed = self.config.simulation.random_seed + realization_id
        sim = GalaxySimulation(self.config, seed=seed)
        sim.galaxy.positions = positions  # Use shared array

        # Initialize other properties (velocities, ages, masses)
        # These are randomized per realization, so can't be shared
        sim.galaxy.velocities = sim.galaxy._generate_velocities()
        # ... etc ...

        sim.run(verbose=False)

        stats = sim.get_statistics()
        stats['realization_id'] = realization_id

        shm.close()  # Don't unlink - parent will do that

        return stats
```

**Memory Savings:** For N=100M stars, 2.4 GB × 10 processes = 24 GB → 2.4 GB (10x reduction)

**Caveat:** Positions evolve over time, so shared memory only works if all realizations use same initial conditions. May need read-only shared memory for positions and process-local arrays for evolved positions.

---

## 7. Profile-Worthy Areas (Concrete Commands)

### 7.1 Profiling Setup

```bash
# Install profiling tools
pip install line_profiler memory_profiler py-spy

# Create profiling script
cat > profile_simulation.py << 'EOF'
from great_silence import GalaxySimulation, SimulationConfig

config = SimulationConfig()
config.galaxy.total_stars = 100_000  # Start small
config.simulation.simulation_duration_gyr = 1.0
config.simulation.time_step_myr = 10.0
config.simulation.save_snapshots = False

sim = GalaxySimulation(config, seed=42)
sim.run(verbose=True)
EOF
```

### 7.2 CPU Profiling

```bash
# 1. cProfile (built-in, function-level)
python -m cProfile -o profile.stats profile_simulation.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(30)"

# 2. py-spy (sampling profiler, no code changes)
py-spy record -o profile.svg --format speedscope -- python profile_simulation.py
# Open profile.svg in browser

# 3. line_profiler (line-by-line, add @profile decorator)
# Add @profile to functions in engine.py, structure.py
kernprof -l -v profile_simulation.py
```

### 7.3 Memory Profiling

```bash
# 1. memory_profiler (line-by-line memory)
# Add @profile to memory-intensive functions
python -m memory_profiler profile_simulation.py

# 2. memray (detailed memory tracking)
pip install memray
memray run profile_simulation.py
memray flamegraph memray-profile.bin
```

### 7.4 Expected Hotspots (Pre-Optimization)

Based on code analysis, profiling should show:

1. **`_generate_exponential_disk()` (structure.py:56-93):** 30-40% of init time
   - Python loops in rejection sampling

2. **`_check_civilization_emergence()` (engine.py:162-213):** 20-30% of loop time
   - List comprehension over eligible stars

3. **`generate_stellar_ages()` (star_formation.py:73-102):** 15-20% of init time
   - While loop with rejection sampling

4. **`evolve_positions()` (structure.py:186-204):** 5-10% of loop time
   - This is already vectorized, but Numba can help

### 7.5 Post-Optimization Targets

After applying optimizations, expect bottlenecks to shift to:

1. **KD-tree rebuild:** If rebuilding every timestep
2. **Civilization list operations:** If many civilizations
3. **Snapshot serialization:** If saving large arrays

---

## 8. Optimization Priority Roadmap

### Phase 1: Quick Wins (1-2 days)
**Impact:** 10-50x speedup, enable N=1M stars

1. ✅ Vectorize rejection sampling in `_generate_exponential_disk()` (Section 1.4)
2. ✅ Vectorize stellar age generation (Section 1.4)
3. ✅ Optimize civilization emergence with vectorized filtering (Section 1.2)
4. ✅ Add spatial index to initialization (Section 3.2)

**Expected Result:** Initialization 50x faster, emergence checks 20x faster

---

### Phase 2: Numba Integration (2-3 days)
**Impact:** 5-20x speedup on main loop, enable N=10M stars

1. ✅ Add Numba to position evolution (Section 2.1 Target 1)
2. ✅ Add Numba to distance calculations (Section 2.1 Target 3)
3. ✅ Add Numba to supernova rate computation (Section 2.1 Target 2)
4. ✅ Add configuration flag checking before Numba calls

**Expected Result:** Main loop 10x faster

---

### Phase 3: Spatial Indexing & Hazards (3-5 days)
**Impact:** 100-1000x speedup on hazard evaluation, enable realistic hazard modeling

1. ✅ Implement vectorized supernova hazard evaluation (Section 1.3)
2. ✅ Integrate spatial index into hazard evaluation (Section 3.2 Step 3)
3. ✅ Implement `_apply_hazards()` (currently placeholder)
4. ✅ Add adaptive spatial index rebuild (every N timesteps)

**Expected Result:** Can run simulations with active hazard evaluation

---

### Phase 4: Advanced Optimizations (1-2 weeks)
**Impact:** 2-5x speedup, enable N=100M stars

1. ✅ Replace `get_distance_matrix()` with range queries (Section 1.1)
2. ✅ Implement proper expansion model using spatial index (Section 3.2)
3. ✅ Add float32 for non-critical arrays (Section 5.2)
4. ✅ Optimize Monte Carlo with shared memory (Section 6.2)
5. ✅ Add memory-mapped arrays for very large N (Section 4.3)

**Expected Result:** Full-scale simulations with 100M stars

---

### Phase 5: GPU Acceleration (Optional, 1-2 weeks)
**Impact:** 5-20x speedup on Apple Silicon with Metal

1. ✅ Implement PyTorch MPS backend for position evolution (Section 4.4)
2. ✅ Move distance calculations to GPU
3. ✅ Benchmark GPU vs CPU for various N
4. ✅ Add automatic GPU/CPU selection based on problem size

**Expected Result:** Maximum performance on Apple Silicon

---

## 9. Performance Benchmarks (Projected)

### Current Implementation (Estimated)

| N Stars | Init Time | Timestep | 1 Gyr (1000 steps) | Memory |
|---------|-----------|----------|-------------------|--------|
| 10k     | 30s       | 0.5s     | 8 min             | 50 MB  |
| 100k    | 5 min     | 5s       | 83 min            | 500 MB |
| 1M      | 50 min    | 50s      | 14 hours          | 5 GB   |
| 10M     | 8 hours   | 500s     | 5.8 days          | 50 GB  |
| 100M    | OOM       | OOM      | Impossible        | 500 GB |

### After Phase 1-2 (Vectorization + Numba)

| N Stars | Init Time | Timestep | 1 Gyr (1000 steps) | Memory |
|---------|-----------|----------|-------------------|--------|
| 10k     | 0.5s      | 0.05s    | 50s               | 50 MB  |
| 100k    | 5s        | 0.5s     | 8 min             | 500 MB |
| 1M      | 50s       | 5s       | 83 min            | 5 GB   |
| 10M     | 8 min     | 50s      | 14 hours          | 50 GB  |
| 100M    | 80 min    | 500s     | 5.8 days          | 500 GB |

**Speedup:** 50-100x on initialization, 10x on main loop

### After Phase 3-4 (Spatial Index + Memory Opts)

| N Stars | Init Time | Timestep | 1 Gyr (1000 steps) | Memory  |
|---------|-----------|----------|-------------------|---------|
| 10k     | 0.5s      | 0.01s    | 10s               | 25 MB   |
| 100k    | 5s        | 0.1s     | 100s              | 250 MB  |
| 1M      | 50s       | 1s       | 17 min            | 2.5 GB  |
| 10M     | 8 min     | 10s      | 2.8 hours         | 25 GB   |
| 100M    | 80 min    | 100s     | 28 hours          | 250 GB  |

**Speedup:** 5-10x on hazard-heavy workloads, 2x memory reduction

### After Phase 5 (GPU Acceleration on M3 Max)

| N Stars | Init Time | Timestep | 1 Gyr (1000 steps) | Memory  |
|---------|-----------|----------|-------------------|---------|
| 10k     | 0.5s      | 0.01s    | 10s               | 25 MB   |
| 100k    | 5s        | 0.05s    | 50s               | 250 MB  |
| 1M      | 50s       | 0.2s     | 3.3 min           | 2.5 GB  |
| 10M     | 8 min     | 2s       | 33 min            | 25 GB   |
| 100M    | 80 min    | 20s      | 5.6 hours         | 250 GB  |

**Speedup:** 5-10x on GPU-accelerated operations

---

## 10. Validation Strategy

After each optimization phase, validate correctness:

### 10.1 Numerical Accuracy Tests

```python
# Test that optimized version produces same results
def test_optimization_accuracy():
    config = SimulationConfig()
    config.galaxy.total_stars = 10_000
    config.simulation.simulation_duration_gyr = 0.1
    config.simulation.random_seed = 42

    # Run with optimizations disabled
    config.simulation.use_numba = False
    sim_slow = GalaxySimulation(config, seed=42)
    sim_slow.run(verbose=False)
    stats_slow = sim_slow.get_statistics()

    # Run with optimizations enabled
    config.simulation.use_numba = True
    sim_fast = GalaxySimulation(config, seed=42)
    sim_fast.run(verbose=False)
    stats_fast = sim_fast.get_statistics()

    # Compare results
    assert stats_slow['total_civilizations'] == stats_fast['total_civilizations']

    # Positions should be nearly identical (within floating point error)
    np.testing.assert_allclose(
        sim_slow.galaxy.positions,
        sim_fast.galaxy.positions,
        rtol=1e-10, atol=1e-12
    )
```

### 10.2 Performance Regression Tests

```python
import time

def benchmark_operation(func, *args, n_runs=10):
    """Benchmark a function call."""
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        func(*args)
        end = time.perf_counter()
        times.append(end - start)

    return {
        'mean': np.mean(times),
        'std': np.std(times),
        'min': np.min(times),
        'max': np.max(times)
    }

# Example: Benchmark initialization
config = SimulationConfig()
config.galaxy.total_stars = 100_000

sim = GalaxySimulation(config, seed=42)
results = benchmark_operation(sim.initialize)

print(f"Initialization: {results['mean']:.3f}s ± {results['std']:.3f}s")
```

---

## 11. Code Examples: Complete Optimized Modules

### 11.1 Optimized `galaxy/structure.py` (Key Methods)

```python
"""Optimized 3D galactic structure with Numba acceleration."""

import numpy as np
import numba
from typing import Tuple, Optional
from ..config.parameters import GalaxyParameters


@numba.jit(nopython=True, parallel=True, fastmath=True)
def _evolve_positions_numba(
    positions: np.ndarray,
    velocities: np.ndarray,
    dt_myr: float
) -> np.ndarray:
    """Numba-accelerated position evolution."""
    n_stars = len(positions)
    v_kpc_myr = velocities * 0.001022

    for i in numba.prange(n_stars):
        positions[i, 0] += v_kpc_myr[i, 0] * dt_myr
        positions[i, 1] += v_kpc_myr[i, 1] * dt_myr
        positions[i, 2] += v_kpc_myr[i, 2] * dt_myr

    return positions


class GalaxyModel:
    """Optimized 3D galaxy model."""

    def __init__(self, params: GalaxyParameters, seed: Optional[int] = None):
        self.params = params
        self.rng = np.random.default_rng(seed)
        self.positions: Optional[np.ndarray] = None
        self.velocities: Optional[np.ndarray] = None
        self.ages: Optional[np.ndarray] = None
        self.masses: Optional[np.ndarray] = None
        self.stellar_types: Optional[np.ndarray] = None
        self.use_numba = True  # Default to True

    def _generate_exponential_disk_vectorized(self, n_stars: int) -> np.ndarray:
        """Vectorized exponential disk generation."""
        h_R = self.params.scale_length_kpc
        h_z = self.params.disk_height_kpc

        # Vectorized rejection sampling for radii
        r = np.zeros(n_stars)
        n_accepted = 0
        batch_size = min(n_stars * 2, 1_000_000)  # Cap batch size

        while n_accepted < n_stars:
            r_test = self.rng.exponential(h_R, batch_size)
            within_radius = r_test < self.params.disk_radius_kpc
            accept_prob = np.where(within_radius, r_test / self.params.disk_radius_kpc, 0.0)

            random_uniform = self.rng.uniform(0, 1, batch_size)
            accepted = random_uniform < accept_prob

            n_to_take = min(np.sum(accepted), n_stars - n_accepted)
            accepted_indices = np.where(accepted)[0][:n_to_take]

            r[n_accepted:n_accepted + n_to_take] = r_test[accepted_indices]
            n_accepted += n_to_take

        # Vectorized coordinate conversion
        theta = self.rng.uniform(0, 2 * np.pi, n_stars)
        z = self.rng.laplace(0, h_z, n_stars)

        x = r * np.cos(theta)
        y = r * np.sin(theta)

        return np.column_stack([x, y, z])

    def evolve_positions(self, dt_myr: float) -> None:
        """Evolve stellar positions (Numba-accelerated if enabled)."""
        if self.positions is None or self.velocities is None:
            raise ValueError("Must generate positions and velocities first")

        if self.use_numba:
            self.positions = _evolve_positions_numba(
                self.positions.copy(),  # Copy to avoid in-place mutation issues
                self.velocities,
                dt_myr
            )
        else:
            v_kpc_myr = self.velocities * 0.001022
            self.positions += v_kpc_myr * dt_myr

    def get_nearby_stars(
        self,
        center_idx: int,
        radius_kpc: float,
        spatial_index=None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get stars within radius using spatial index.

        Replaces O(N²) distance matrix computation.
        """
        if spatial_index is None:
            from ..utils.spatial import SpatialIndex
            spatial_index = SpatialIndex(self.positions)

        center_pos = self.positions[center_idx]
        indices, distances = spatial_index.query_radius(
            center_pos, radius_kpc, return_distances=True
        )

        return indices, distances
```

### 11.2 Optimized `simulation/engine.py` (Key Methods)

```python
"""Optimized simulation engine."""

import numpy as np
from typing import Optional
from ..config.parameters import SimulationConfig
from ..galaxy.structure import GalaxyModel
from ..utils.spatial import SpatialIndex


class GalaxySimulation:
    """Optimized main simulation engine."""

    def __init__(self, config: SimulationConfig, seed: Optional[int] = None):
        self.config = config
        self.seed = seed if seed is not None else config.simulation.random_seed
        self.rng = np.random.default_rng(self.seed)

        self.galaxy = GalaxyModel(config.galaxy, seed=self.seed)
        self.galaxy.use_numba = config.simulation.use_numba

        # ... other initialization ...

        self.spatial_index: Optional[SpatialIndex] = None
        self.spatial_index_age_myr = 0.0  # Track when index was built

    def initialize(self) -> None:
        """Initialize with spatial indexing."""
        print("Initializing galaxy...")
        self.galaxy.generate_stellar_population()

        # ... existing code ...

        print("Building spatial index...")
        self.spatial_index = SpatialIndex(self.galaxy.positions)
        self.spatial_index_age_myr = 0.0
        print("Spatial index built.")

    def _rebuild_spatial_index_if_needed(self) -> None:
        """Rebuild spatial index periodically."""
        # Rebuild every 100 Myr (adjustable)
        rebuild_interval = 100.0

        age_since_rebuild = self.current_time_myr - self.spatial_index_age_myr

        if age_since_rebuild >= rebuild_interval:
            self.spatial_index = SpatialIndex(self.galaxy.positions)
            self.spatial_index_age_myr = self.current_time_myr

    def _check_civilization_emergence(self) -> None:
        """Optimized vectorized civilization emergence."""
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

        # Vectorized filtering
        age_mask = self.galaxy.ages > 1.0
        eligible_mask = np.zeros(len(self.galaxy.positions), dtype=bool)
        eligible_mask[self.habitable_star_indices] = True
        eligible_mask &= age_mask

        # Remove colonized stars
        if self.civilizations:
            colonized_indices = np.concatenate([
                np.array([civ.parent_star_idx] + civ.colonized_stars)
                for civ in self.civilizations
            ])
            eligible_mask[colonized_indices] = False

        eligible_stars = np.where(eligible_mask)[0]

        if len(eligible_stars) == 0:
            return

        # Poisson thinning for rare events
        expected_emergences = p_emergence * len(eligible_stars)

        if expected_emergences < 0.1:
            n_emergences = self.rng.poisson(expected_emergences)
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
            from .engine import CivilizationState  # Avoid circular import
            new_civ = CivilizationState(
                civ_id=self.next_civ_id,
                birth_time_myr=self.current_time_myr,
                parent_star_idx=int(star_idx),
                colonized_stars=[int(star_idx)]
            )
            self.civilizations.append(new_civ)
            self.next_civ_id += 1

    def run(self, verbose: bool = True) -> None:
        """Optimized main loop."""
        if self.galaxy.positions is None:
            self.initialize()

        total_steps = int(
            self.config.simulation.simulation_duration_gyr * 1000 /
            self.config.simulation.time_step_myr
        )

        from tqdm import tqdm
        pbar = tqdm(total=total_steps, desc="Simulating", disable=not verbose)

        snapshot_counter = 0
        next_snapshot_time = 0.0

        while self.current_time_myr < self.config.simulation.simulation_duration_gyr * 1000:
            # Evolve galaxy
            self.galaxy.evolve_positions(self.config.simulation.time_step_myr)

            # Rebuild spatial index if needed
            self._rebuild_spatial_index_if_needed()

            # Check civilization emergence
            self._check_civilization_emergence()

            # Evolve civilizations
            self._evolve_civilizations()

            # Apply hazards
            self._apply_hazards()

            # Save snapshot
            if self.config.simulation.save_snapshots:
                if self.current_time_myr >= next_snapshot_time:
                    self._save_snapshot()
                    next_snapshot_time += self.config.simulation.snapshot_interval_myr

            self.current_time_myr += self.config.simulation.time_step_myr
            pbar.update(1)

        pbar.close()

        if self.config.simulation.save_snapshots:
            self._save_snapshot()

        print(f"\nSimulation complete!")
        print(f"Total civilizations: {self.next_civ_id}")
        print(f"Active civilizations: {sum(c.is_active for c in self.civilizations)}")
```

---

## 12. Conclusion and Recommendations

### 12.1 Immediate Actions (This Week)

1. **Run baseline profiling** (Section 7) to confirm bottlenecks
2. **Implement Phase 1 optimizations** (Section 8) - vectorized rejection sampling
3. **Add spatial index initialization** (Section 3.2 Step 1)
4. **Validate numerical accuracy** (Section 10.1)

### 12.2 Medium-Term Goals (This Month)

1. **Complete Numba integration** (Phase 2)
2. **Implement vectorized hazard evaluation** (Phase 3)
3. **Benchmark N=1M stars** and verify scaling
4. **Document performance characteristics** in README

### 12.3 Long-Term Vision (This Quarter)

1. **Enable N=100M star simulations** (Phase 4)
2. **Add GPU acceleration** for Apple Silicon (Phase 5)
3. **Publish performance benchmarks** comparing to literature
4. **Create optimization guide** for users

### 12.4 Key Takeaways

**Do:**
- Use NumPy vectorization everywhere possible
- Apply Numba to remaining hot loops
- Use spatial indexing (KD-tree) for O(log N) queries
- Profile before and after optimization
- Validate numerical correctness after each change

**Don't:**
- Compute full O(N²) distance matrices
- Use Python loops over millions of elements
- Ignore memory layout (use contiguous arrays)
- Optimize without profiling first
- Sacrifice correctness for speed

**Apple Silicon Advantages:**
- Unified memory eliminates CPU↔GPU copies
- Accelerate framework optimizes BLAS/LAPACK automatically
- ARM64 NEON SIMD accelerates NumPy ufuncs
- Metal GPU can provide 5-20x speedup for embarrassingly parallel work

---

## File Paths Referenced

All paths are absolute for reference:

- Main engine: `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/simulation/engine.py`
- Galaxy structure: `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/galaxy/structure.py`
- Spatial index: `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/utils/spatial.py`
- Hazards: `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/astrophysics/hazards.py`
- Star formation: `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/galaxy/star_formation.py`
- Monte Carlo: `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/simulation/monte_carlo.py`
- Configuration: `/Users/jburgess/coding/projects/galaticbot/src/galaticbot/config/parameters.py`

---

**Document Version:** 1.0
**Last Updated:** 2025-12-26
**Author:** Performance Analysis for GalaticBot on Apple Silicon
