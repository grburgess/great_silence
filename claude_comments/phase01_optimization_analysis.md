# Phase 0+1 Optimization Analysis

**Benchmark Date**: 2026-02-11
**Commit**: d561ed0

## Configuration
- **Stars**: 100,000
- **Duration**: 10.0 Gyr
- **Emergence rate**: 0.1 per Myr
- **Result**: 1,012 civilizations, 16,142 colonized systems

## Performance Summary

| Metric | Value | Percentage |
|--------|-------|------------|
| **Total time** | 346.08s (5.77 min) | 100% |
| Init time | 61.08s | 17.6% |
| Run time | 285.01s | 82.4% |
| **Peak memory** | 806.9 MB | - |

## Profiling Analysis - Top Bottlenecks

### 1. Stellar Motion (79% of run time)
- `evolve_positions_adaptive`: **224s** (79% of simulation)
  - `_compute_gravitational_acceleration`: 131s
  - Adaptive timestep overhead with 100k stars
  - Called 20,778 times (201,528 sub-steps)

**Optimization opportunities**:
- ✅ Already using Numba kernels for acceleration
- ✅ Already using adaptive individual timesteps (256x speedup vs sub-cycling)
- 🔄 **SoA layout** implemented but `column_stack` conversion taking 67s
  - Need to eliminate AoS↔SoA conversions in hot path
- 🔄 **Yoshida integrator** implemented but not used
  - Could enable larger timesteps (4-8x)

### 2. Array Reshaping (23% of run time)
- `column_stack`: **67s** (23% of simulation)
  - Converting SoA → AoS format 777,623 times
  - Called from `structure.py:55(positions)` property

**Fix**: Keep SoA throughout, only convert for visualization/export.

### 3. NumExpr Evaluation (25% of run time)
- `necompiler.py:evaluate`: **70s** (25% of simulation)
  - Used for disk/bulge/halo acceleration calculations
  - 1.6M calls total

**Status**: Already using numexpr for vectorized math - this is expected overhead.

### 4. Probe System (13% of run time)
- `_process_probe_events`: 36s
- `_handle_replication_complete`: 32s
- `_launch_offspring_probes`: 31s
- `_find_nearest_targets`: 21s

**Optimization opportunities**:
- ✅ Already using `_civ_by_id` and `_probe_by_id` dicts (O(1) lookups)
- ✅ Already using spatial index for queries
- 🔄 **Spatial hash grid** implemented but not integrated
  - Would improve `_find_nearest_targets` from O(log N) to O(1)

## Implementation Status

### ✅ Completed (Phase 0+1)
1. **Phase 0.1**: Benchmark script - ✅
2. **Phase 0.2**: Bug fixes (8 issues) - ✅
3. **Phase 0.3**: Quick wins (memory pools, numexpr, active filtering) - ✅
4. **Phase 1.1**: SoA layout - ✅ (but needs integration)
5. **Phase 1.2**: Yoshida integrator - ✅ (but not used)
6. **Phase 1.3**: Spatial hash grid - ✅ (but not integrated)
7. **Phase 1.4**: Blosc2 compression - ✅
8. **Phase 1.5**: Branchless kernels - ✅
9. **Phase 1.6**: float32 utilities - ✅

### 📋 Remaining Integration Work
- **Eliminate SoA↔AoS conversions**: Keep SoA in hot path, only convert for export
- **Enable Yoshida integrator**: Replace leapfrog with Yoshida for stellar motion
- **Integrate spatial hash**: Replace KD-tree with hash grid for probe targeting

## Estimated Speedup Potential

### Current Bottleneck Breakdown
| Component | Time (s) | % of Total |
|-----------|----------|------------|
| Stellar motion | 224 | 64.7% |
| Array conversions | 67 | 19.4% |
| NumExpr | 70 | 20.2% |
| Probe system | 31 | 9.0% |
| Other | 15 | 4.3% |

### Integration Targets
1. **Eliminate column_stack** (67s → ~5s): **~18% faster** (62s saved)
2. **Enable Yoshida integrator** (224s → 56-112s): **32-48% faster** (112-168s saved)
3. **Spatial hash for probes** (21s → 5s): **~5% faster** (16s saved)

### Combined Potential
- **Conservative**: 62 + 112 + 16 = 190s saved → **346s → 156s** (**2.2x faster**)
- **Optimistic**: 62 + 168 + 16 = 246s saved → **346s → 100s** (**3.5x faster**)

## Recommended Next Steps

### Option A: Complete Phase 1 Integration (Recommended)
**Goal**: Realize speedup from already-implemented optimizations
**Effort**: 1-2 hours
**Expected gain**: 2.2-3.5x speedup

Tasks:
1. Refactor to eliminate `positions` property calls in hot path
2. Enable Yoshida integrator for stellar motion
3. Replace KD-tree with spatial hash in `_find_nearest_targets()`
4. Re-benchmark

### Option B: Proceed to Phase 2 (War Mechanics)
**Goal**: Implement war phase transitions, exhaustion mechanics
**Effort**: 4-6 hours
**Expected gain**: New features, unknown perf impact

Note: Would be building on non-optimized foundation.

### Option C: Implement Remaining Phase 1 Items (1.7-1.10)
**Goal**: Add sector partitioning, incremental overlap, adaptive snapshots
**Effort**: 2-3 hours
**Expected gain**: 3-5x additional (see phase1_remaining_optimizations.md)

Note: These are documented but not yet implemented.

## Recommendation

**Choose Option A**: Complete Phase 1 integration before adding new features. The infrastructure is already built but not fully utilized. Realizing the 2-3x speedup will make all future development faster.

After Option A, revisit based on new bottlenecks revealed by profiling.
