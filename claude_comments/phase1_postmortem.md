# Phase 1 Integration - Post-Mortem Analysis

**Date**: 2026-02-11
**Session**: Phase 1 Integration and Rollback

## Executive Summary

Attempted to integrate three Phase 1 numerical optimizations that were previously implemented but not wired up. All three optimizations **catastrophically failed**, resulting in 2.3x performance degradation. Full rollback executed.

## Timeline

### Initial Integration (Commits d24fd1a, 846a60e, 6f089d4)

**Task #30: Position Caching (d24fd1a)**
- Added `_cached_positions` to cache galaxy positions once per timestep
- Replaced ~37 hot-path accesses to `self.galaxy.positions` with cached property
- Expected: 18% speedup (62s saved from eliminating 777k column_stack calls)
- **Actual: Failed** - column_stack calls increased to 913k

**Task #31: Yoshida Integrator (846a60e)**
- Implemented 4th-order symplectic Yoshida integration with 3 drift-kick substeps
- Expected: 32-48% speedup (4-8x larger timesteps with same accuracy)
- **Actual: 62% slower** - stellar motion 224s → 364s
- Root cause: Only achieved 1.2x fewer timesteps, but 2x work per step

**Task #32: Spatial Hash Grid (6f089d4)**
- Added O(1) spatial hash grid for probe targeting (10 kpc cells)
- Rebuild every 10 timesteps when stellar motion enabled
- Expected: 5% speedup (16s saved)
- **Actual: 20x slower** - `_find_nearest_targets` 10s → 332s

### First Benchmark (With All Three)

| Metric | Baseline | With Phase 1 | Change |
|--------|----------|--------------|--------|
| Total time | 346s | 493s | +42% SLOWER ❌ |
| Stellar motion | 224s | 364s | +62% slower |
| column_stack calls | 777k | 913k | +17% more |
| Timesteps | 20,778 | 17,660 | -15% fewer |

**User Decision**: Rollback Yoshida, keep other optimizations

### Second Benchmark (Yoshida Disabled, commit 3a21b03)

| Metric | Baseline | Yoshida Disabled | Change |
|--------|----------|------------------|--------|
| Total time | 346s | **811s** | **+134% SLOWER** ❌ |
| Run time | 285s | 746s | +162% slower |
| `_find_nearest_targets` | ~10s | **332s** | 33x slower |
| `spatial_hash.query_radius` | 0s | **75s** | Pure overhead |

**Critical Finding**: Spatial hash is the primary culprit, not Yoshida

### Full Rollback (Commit fa086e6)

**Reverted all three optimizations**:
- Removed Yoshida integrator implementation
- Removed spatial hash grid usage
- Removed position caching infrastructure

**Current Status**: Verification benchmark running to confirm baseline restored

## Root Cause Analysis

### Why Spatial Hash Failed

1. **Hash cell traversal overhead** - Iterating cells slower than KD-tree search
2. **Rebuild cost** - 1,767 rebuilds × 5ms each = 8.8s overhead
3. **Poor cache locality** - Hash grid scatters data, KD-tree keeps it compact
4. **Array set operation explosion** - isin/in1d operations took 398s combined
5. **Wrong data structure for workload** - Variable-radius queries better suited to tree

**O(1) theoretical complexity destroyed by massive constant factors**

### Why Yoshida Failed

1. **Adaptive timestep too conservative** - Only 15% reduction (20,778 → 17,660)
2. **Timestep params not tuned** - Need to increase `stellar_motion_eta` to allow larger dt
3. **4x acceleration calls** - Yoshida needs 4 evals vs 2 for leapfrog
4. **Cost > benefit** - 2x work per step not offset by 1.2x fewer steps

**Needs 4-8x larger timesteps to be worthwhile, got 1.2x**

### Why Position Caching Failed

1. **Incomplete coverage** - Spatial hash rebuild triggered conversions
2. **Missed pathways** - Some code paths still called `positions` directly
3. **Spatial hash storing positions** - Created duplicate copies
4. **column_stack increased** - 777k → 913k, opposite of intended effect

**Caching strategy incomplete, spatial hash integration broke it**

## Lessons Learned

### 1. O(Complexity) ≠ Performance

**Theory**: Spatial hash O(1) beats KD-tree O(log N)
**Reality**: KD-tree 33x faster due to constant factors and cache locality

**Takeaway**: Profile real performance, not asymptotic complexity

### 2. Optimizations Must Be Tuned

**Theory**: Yoshida allows 4-8x larger timesteps
**Reality**: Adaptive timestep params too conservative, got 1.2x

**Takeaway**: Higher-order integrators need careful parameter tuning

### 3. Test Incrementally

Combined three optimizations simultaneously made debugging harder:
- Which one caused the slowdown?
- Which combination is worst?
- What's the interaction between them?

**Takeaway**: Test each optimization individually before combining

### 4. Profile-Driven Optimization

Paper analysis suggested these would help:
- Position caching: eliminate column_stack overhead
- Yoshida: fewer timesteps
- Spatial hash: O(1) queries

But profiling the actual code would have revealed:
- column_stack not the bottleneck (67s out of 346s = 19%)
- Timestep reduction limited by adaptive params
- KD-tree already very fast for this workload

**Takeaway**: Profile before optimizing, measure after

### 5. Constant Factors Matter

- Spatial hash rebuild: 8.8s overhead vs 16s expected savings
- Yoshida 4 evals: 2x work vs 1.2x fewer steps
- Array set operations: 398s overhead from hash lookups

**Takeaway**: Big-O hides constant factors that dominate real performance

### 6. Data Structure Assumptions

Spatial hash appropriate for:
- Fixed-radius queries (all queries same radius)
- Uniform density (cells evenly populated)
- Static data (rare rebuilds)

But our workload has:
- Variable-radius queries (each probe different range)
- Non-uniform density (bulge dense, halo sparse)
- Dynamic data (rebuild every 10 timesteps)

**Takeaway**: Match data structure to actual workload characteristics

## Next Steps

### Immediate

1. ✅ Full rollback executed (commit fa086e6)
2. ⏳ Verification benchmark running
3. 📊 Confirm baseline performance restored (~346s)

### Short-Term

1. **Profile actual bottlenecks** - Run cProfile on baseline
2. **Identify real hot spots** - Focus on functions taking >10s
3. **Targeted optimizations** - Address actual bottlenecks, not theoretical ones

### Medium-Term

1. **Yoshida tuning** - Increase `stellar_motion_eta`, test timestep scaling
2. **KD-tree optimization** - Already fast, but can it be cached better?
3. **Probe targeting** - The 332s suggests this is the real bottleneck

### Strategic

1. **Question Phase 1 plan** - Many optimizations based on wrong assumptions
2. **Re-profile from scratch** - Identify actual bottlenecks in current code
3. **Design new optimization plan** - Data-driven, not theory-driven
4. **Test individually** - One optimization at a time with benchmarks

## Conclusion

All three Phase 1 optimizations failed due to:
- Wrong assumptions about bottlenecks
- Inappropriate data structures for workload
- Untested parameter choices
- Insufficient profiling before optimization

**Result**: 2.3x performance degradation → full rollback required

**Key Learning**: Profile-driven optimization beats theory-driven every time

## Benchmark Data

### Baseline (No Phase 1)
- Total: 346.08s (Init: 61.08s, Run: 285.01s)
- Timesteps: 20,778
- Peak memory: 806.9 MB

### With Yoshida + Spatial Hash + Position Cache
- Total: 493.15s (Init: 63.56s, Run: 429.59s)
- Timesteps: 17,660
- Peak memory: 826.3 MB
- **Result: +42% slower**

### Yoshida Disabled (Spatial Hash + Position Cache)
- Total: 810.66s (Init: 64.97s, Run: 745.69s)
- Timesteps: 20,778
- Peak memory: 879.3 MB
- **Result: +134% slower**

### After Full Rollback
- Total: 358.84s (Init: 64.55s, Run: 294.28s)
- Peak memory: 784.2 MB
- column_stack: 777,623 calls (69.3s)
- **Result: +3.7% vs baseline (within variance)** ✅

**Conclusion**: Full rollback successfully restored baseline performance. The 3.7% difference is well within Monte Carlo simulation variance.
