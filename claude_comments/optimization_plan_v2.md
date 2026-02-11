# Optimization Plan v2: Data-Driven

**Date**: 2026-02-11
**Baseline**: 358.8s (Init: 64.5s, Run: 294.3s) @ 100k stars, 10 Gyr

## Profiled Bottleneck Breakdown (Run: 294s)

### Tier 1: Stellar Motion — 231s (79%)

| Function | tottime | cumtime | calls | note |
|----------|---------|---------|-------|------|
| `evolve_positions_adaptive` | 97.9s | 230.9s | 20,778 | Main loop |
| `_compute_gravitational_acceleration` | 10.7s | 134.4s | 201,528 | 2× per step per batch |
| `_compute_disk_acceleration` | 0.96s | 79.5s | 201,528 | numexpr but column_stack |
| `column_stack` (positions property) | 69.3s | 70.4s | 777,623 | **THE bottleneck** |
| `numexpr.evaluate` + `re_evaluate` | ~50s | | 1.6M | disk accel inner loop |
| `_compute_bulge_acceleration` | 16.5s | 22.9s | 201,528 | plain NumPy |
| `_compute_halo_acceleration` | 14.0s | 21.3s | 201,528 | plain NumPy |

**Root cause**: `evolve_positions_adaptive()` calls Python-level `_compute_gravitational_acceleration()` which calls three sub-functions, each doing:
1. Unpack (N,3) → x, y, z
2. Compute in SoA
3. `column_stack` back to (N,3)

Then the parent sums three (N,3) arrays. **6 column_stacks per accel call × 201k calls = 1.2M column_stacks** (only 777k recorded due to some caching).

Meanwhile, Numba kernels (`compute_total_acceleration_kernel`) exist that do ALL THREE potentials in a single fused loop with zero allocation. But `evolve_positions_adaptive()` doesn't use them.

### Tier 2: Probe Operations — 39s (13%)

| Function | tottime | cumtime | calls | note |
|----------|---------|---------|-------|------|
| `_find_nearest_targets` | 3.6s | 22.3s | 14,925 | Target selection |
| `isin`/`in1d` | 0.8s | 16.9s | 14,925 | Set membership check |
| `unique` | 0.3s | 11.2s | 29,266 | Inside `in1d` |
| `_handle_probe_arrival` | 16.0s | 55.6s | 15,130 | Arrival processing |

**Root cause**: `np.isin(nearby_indices, list(excluded_stars))` converts a Python `Set[int]` to a list → array → sorts → binary search. For each of 14,925 calls with growing excluded sets. A boolean mask array would be O(K) instead.

### Tier 3: Initialization — 65s (18%)

| Function | tottime | cumtime | calls |
|----------|---------|---------|-------|
| `generate_stellar_population` | - | 60.1s | 1 |
| `_generate_velocities_simple` | 2.3s | 59.0s | 1 |
| `_compute_circular_velocity` | 0.5s | 31.1s | 160,001 |
| `_compute_asymmetric_drift` | 0.1s | 15.2s | 1 |

`_compute_circular_velocity` called 160k times (once per star). Could be vectorized.

---

## Optimization Plan

### OPT-1: Use Numba kernel in evolve_positions_adaptive (231s → ~30s)

**Impact: -200s (68% of runtime)**

The Numba kernel `compute_total_acceleration_kernel` already exists and fuses disk+bulge+halo into a single parallel loop with zero allocations. But `evolve_positions_adaptive()` calls the Python functions instead.

**Change**: Replace the two `_compute_gravitational_acceleration()` calls in `evolve_positions_adaptive()` with direct calls to `compute_total_acceleration_kernel`.

**Why it works**:
- Eliminates ALL column_stack calls in the hot path (70s saved)
- Eliminates numexpr overhead (50s saved)
- Eliminates Python function call overhead (10.7s saved)
- Eliminates temporary array allocations for disk/bulge/halo intermediates
- Numba parallel loop fuses all three potentials into one pass
- Already tested and proven in `evolve_positions()` (non-adaptive path)

**Risk**: Low. Kernel already exists and is tested. Just need to wire it into the adaptive path.

**Implementation**:
```python
def evolve_positions_adaptive(self, dt_myr, use_numba=True):
    ...
    if use_numba:
        # Precompute potential parameters (once per call)
        # ... same params as evolve_positions() already computes ...

        # Compute acceleration at current positions
        a_current = np.empty_like(pos_update)
        compute_total_acceleration_kernel(
            pos_update, a_current,
            disk_a, disk_b, disk_G_M,
            bulge_a, bulge_G_M, halo_v_sq,
            include_bulge
        )

        # ... leapfrog step ...

        # Compute acceleration at new positions
        a_new = np.empty_like(pos_new)
        compute_total_acceleration_kernel(
            pos_new, a_new,
            disk_a, disk_b, disk_G_M,
            bulge_a, bulge_G_M, halo_v_sq,
            include_bulge
        )
    else:
        # Fallback to Python path
        a_current = self._compute_gravitational_acceleration(pos_update)
        a_new = self._compute_gravitational_acceleration(pos_new)
```

### OPT-2: Boolean mask for probe exclusion (17s → <1s)

**Impact: -16s (5% of runtime)**

Replace `np.isin(nearby_indices, list(excluded_stars))` with a pre-allocated boolean mask.

**Change**:
- Add `_colonized_mask: np.ndarray` (bool, shape n_stars) to engine
- Update on colonization/decolonization events
- In `_find_nearest_targets`: `not_excluded = ~self._colonized_mask[nearby_indices] & ~self._targeted_mask[nearby_indices]`

**Why it works**: O(K) array indexing vs O(K × M × log M) sort-based set membership.

**Risk**: Low. Simple data structure change.

### OPT-3: Vectorize _compute_circular_velocity (31s → <1s, init only)

**Impact: -30s on init time**

Currently called 160k times (once per star) in a loop. Should accept an array of radii and compute all at once.

**Risk**: Low. Pure vectorization of existing math.

---

## Expected Results

| Component | Before | After | Saved |
|-----------|--------|-------|-------|
| Stellar motion (OPT-1) | 231s | ~30s | **~200s** |
| Probe targeting (OPT-2) | 17s | <1s | **~16s** |
| Init velocity (OPT-3) | 60s | ~30s | **~30s** |
| **Total** | **359s** | **~113s** | **~246s** |
| **Speedup** | | | **~3.2x** |

## Why This Plan is Different from Phase 1

| Phase 1 (Failed) | Plan v2 |
|-------------------|---------|
| Added new data structures (spatial hash) | Use EXISTING Numba kernels |
| Changed external API (positions caching) | Change internal wiring only |
| Theory-driven (O(1) vs O(log N)) | Profile-driven (eliminate 70s column_stack) |
| Three simultaneous changes | One change at a time with benchmarks |
| Untested assumptions about timestep scaling | Proven kernel already benchmarked |

## Implementation Order

1. **OPT-1** first (biggest impact, lowest risk, kernel exists)
2. Benchmark OPT-1 alone
3. **OPT-2** second (if OPT-1 succeeds)
4. Benchmark OPT-1 + OPT-2
5. **OPT-3** third (init-only, independent)
6. Final benchmark

## Unresolved Questions

- Does `compute_total_acceleration_kernel` handle subsets correctly? (need to verify it works with arbitrary-length input, not just full galaxy)
- Numba first-call JIT compilation delay acceptable? (should be cached after first call)
- Any numerical differences between Numba and numexpr paths? (need energy conservation check)
