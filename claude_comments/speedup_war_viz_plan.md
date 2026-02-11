# Speedup + War Completion + War Visualization Plan

**Target**: 100k+ stars, 10+ Gyr, many concurrent wars
**War scope**: Enhanced current (fix bugs, war phases, exhaustion, cooperation hookup). No fleet transit or vassalization.
**Viz scope**: War rendering in Three.js (territory, battles, indicators) + WebGPU migration.

---

## Numerical Libraries & Techniques Reference

### Libraries to Install
```bash
pip install blosc2       # Snapshot compression (bytedelta + zstd), v2.6+
pip install numexpr      # Auto-SIMD array expressions, v2.8+
pip install mlx          # Apple Silicon GPU arrays (NumPy-like API), v0.30+
pip install taichi       # GPU kernels via Metal backend, v1.7+
pip install line_profiler memory_profiler  # Profiling
npm install three@0.171.0  # WebGPU-ready Three.js (r171+)
```

### Technique Priority Ranking (bang-for-buck)
| Rank | Technique | Speedup | Effort | Phase |
|------|-----------|---------|--------|-------|
| 1 | Struct-of-Arrays (SoA) for Numba kernels | 2-4x | Med | 1 |
| 2 | Spatial hash grid (fixed-radius O(1)) | 3-10x | Med | 1 |
| 3 | 4th-order Yoshida integrator | 3x | Low | 1 |
| 4 | WebGPU + TSL compute shaders | 10-150x viz | Med-High | 3 |
| 5 | MLX for gravitational acceleration | 5-20x | Med | 1 |
| 6 | Blosc2 snapshot compression | 5-20x size | Low | 1 |
| 7 | Memory pool for scratch arrays | 10-30% | Low | 0 |
| 8 | Async snapshot I/O | 5-15% | Low | 1 |
| 9 | float16 for viz-only arrays | 4x size | Very Low | 1 |
| 10 | Sector-based civ partitioning | 2-8x | Low | 1 |
| 11 | Branchless Numba kernels | 1.5-3x | Low-Med | 1 |
| 12 | numexpr for array expressions | 2-3x | Very Low | 0 |
| 13 | Parallel arrays for CivState | 5-20x | HIGH | Future |
| 14 | Taichi GPU kernels (Metal) | 5-50x | Med | Future |

### Key Architectural Decisions
- **SoA vs AoS**: Current `positions[N,3]` is Array-of-Structs. Numba NEON SIMD on Apple Silicon loads 4×float32 contiguous. SoA (`pos_x[N], pos_y[N], pos_z[N]`) enables full SIMD utilization + 100% cache line usage
- **float64 vs float32**: Keep float64 for orbital integration and probability calculations. Use float32 for viz arrays, distance comparisons, hazard radius checks (7 digits precision = sub-pc at galaxy scale)
- **fastmath audit**: Remove `fastmath=True` from probability/sampling kernels (breaks IEEE 754). Keep for geometry/physics kernels
- **Leapfrog → Yoshida**: 4th-order symplectic integrator = 3 leapfrog sub-steps with special coefficients. Same accuracy with 4-8x larger dt, net 3x speedup. Still symplectic (energy conserving over 10+ Gyr)
- **MLX over JAX on Apple Silicon**: MLX is Apple's native array framework with unified memory. NumPy-like API, lazy evaluation, direct Metal GPU access. jax-metal is experimental

---

## Phase 0: Baseline + Bug Fixes + Quick Wins

**Goal**: Establish benchmark, fix bugs, grab zero-effort wins

### 0.1 — Benchmark at Target Scale
- Create `scripts/benchmark_war.py`: 100k stars, 10 Gyr, config that forces many civ emergences
- Profile with cProfile, capture top-30 functions
- Document: init time, sim time, peak memory, snapshot count/size, max concurrent civs/wars
- Profile memory: `memory_profiler` on `_save_snapshot()` to measure per-snapshot cost

### 0.2 — Bug Fixes (engine.py)
- [ ] Remove duplicate `HazardEvent` class (~line 169-190, second def overwrites first)
- [ ] Remove dead code after return (~line 2489-2492, unreachable recovery_queue code)
- [ ] Move `from scipy.special import expit` to module-level import (currently imported per battle)
- [ ] Fix `evolve_personality()` return: unpack `PersonalityState` fields into individual `CivilizationState` attrs (`personality_type`, `friendliness`, `aggression_factor`, `war_trauma`, `victory_confidence`)
- [ ] Replace O(N) `next()` scan in `_scan_for_encounters()` (~line 2728) with `_civ_by_id` dict lookup
- [ ] Replace O(N) `next()` scan in `_resolve_wars()` (~line 2893) with `_civ_by_id` dict lookup
- [ ] Replace O(N) probe arrival encounter check (~line 1399) with `_civ_by_star_idx` dict
- [ ] Audit `fastmath=True`: remove from `compute_emergence_probabilities_kernel` and any probability-sampling kernels. Keep for acceleration/distance kernels

### 0.3 — Quick Wins (zero-effort gains)
- [ ] **Memory pool**: Pre-allocate scratch arrays (accel_buffer, dist_buffer, mask_buffer) in `__init__()`, pass to kernels instead of allocating per-timestep. ~10-30% reduction in per-step overhead
- [ ] **numexpr for disk acceleration**: Replace multi-temporary NumPy expressions in `_compute_disk_acceleration()` with `ne.evaluate()` for 2-3x speedup with auto-SIMD threading
- [ ] **Skip inactive civs** in `_manage_strategic_resources()`: filter to active-only (same pattern as reputation decay)

### 0.4 — Tests
- Run full test suite, confirm all pass after fixes
- Re-benchmark to confirm no regression

**Deliverable**: Baseline doc in `claude_comments/benchmark_results.md`, bugs fixed, quick wins applied, tests green

---

## Phase 1: Performance — Numerical Optimization (100k Scale)

**Goal**: Apply best-practice numerical techniques from gaming/simulation for 100k+ stars

### 1.1 — Struct-of-Arrays (SoA) Layout [2-4x for kernels]
- Refactor `GalaxyModel` to store positions as `pos_x[N], pos_y[N], pos_z[N]` (contiguous arrays)
- Keep AoS `positions[N,3]` as a view/property for Python-level code compatibility
- Pass separate x,y,z arrays to Numba kernels for full NEON SIMD utilization
- Apply to: gravitational acceleration kernel (biggest hotspot), distance computation, hazard evaluation
- Apple Silicon NEON: 4×float32 per instruction (vs stride-3 access wasting 2/3 cache line with AoS)

### 1.2 — 4th-Order Yoshida Symplectic Integrator [3x for stellar motion]
- Replace 2nd-order leapfrog with Yoshida 4th-order (3 sub-steps, special coefficients)
- Coefficients (Yoshida 1990):
  ```
  c1 = c4 = 1/(2(2-2^(1/3)))
  c2 = c3 = (1-2^(1/3))/(2(2-2^(1/3)))
  d1 = d3 = 1/(2-2^(1/3))
  d2 = -2^(1/3)/(2-2^(1/3))
  ```
- Same accuracy with 4-8x larger dt; each step costs 3x more = net 3x speedup
- Still symplectic — conserves energy over 10+ Gyr (critical for long runs)
- Implementation: ~50 lines replacing inner leapfrog step. Adaptive timestep infrastructure unchanged

### 1.3 — Spatial Hash Grid for Fixed-Radius Queries [3-10x]
- Replace `scipy.cKDTree` for fixed-radius neighbor queries (hazard radius, encounter detection)
- Grid cell size = max query radius. Each cell holds star indices. Query = check 27 adjacent cells
- O(1) per query vs O(log N) for KD-tree
- Numba-compatible (pure array-based, no Python objects)
- Build cost: O(N) with radix sort on cell indices
- Rebuild only when positions change significantly (every ~10 stellar motion steps)
- Keep KD-tree for variable-radius queries (probe targeting) and one-off queries

### 1.4 — Blosc2 Snapshot Compression [5-20x size reduction]
- `blosc2.pack_array2(positions, cparams=CParams(codec=ZSTD, filters=[BYTEDELTA, SHUFFLE]))`
- Bytedelta filter: splits float bytes, delta-encodes each byte stream — perfect for spatially-correlated position arrays
- 100k × 3 × float64 = 2.4MB → ~200KB per snapshot (adjacent stars have similar positions)
- Async compression on background thread (ThreadPoolExecutor) to not block sim loop
- Float16 quantization for viz-only position snapshots (4x size, 30pc precision at galaxy scale)

### 1.5 — Branchless Numba Kernels [1.5-3x for hazard eval]
- Replace `if` branches in hot loops with arithmetic masks
- SIMD (NEON) cannot vectorize branches — each `if` breaks the pipeline
- Example: `mask = float(mass >= 8.0); rate *= mask` instead of `if mass < 8.0: continue`
- Apply to: `batch_evaluate_hazards_kernel`, `evaluate_sn_effect_on_civs_kernel`, `evaluate_grb_effect_on_civs_kernel`

### 1.6 — float32 for Non-Critical Paths [1.5-2x kernel speed]
- NEON processes 4×float32 vs 2×float64 per instruction, half the memory bandwidth
- Safe for: viz positions, distance comparisons (sterilization radius checks), velocity evolution
- NOT safe for: orbital integration (accumulation errors), Drake probability (very small numbers), time advancement
- `positions_f32 = positions.astype(np.float32)` at kernel boundaries

### 1.7 — Sector-Based Civilization Partitioning [2-8x encounter detection]
- Divide galaxy into sectors (e.g., 8×8 grid in R-phi)
- Only scan for encounters between civs in adjacent sectors
- Civs on opposite sides of galaxy cannot encounter in single timestep
- 64 sectors → ~8x reduction in pairwise checks
- Low complexity: add sector assignment to CivState, filter before encounter check

### 1.8 — Incremental Colony Overlap Detection
- Current `find_territory_overlaps()`: O(C×S) rebuilding star_to_civs dict each call
- Maintain persistent `_star_to_civs` dict, update incrementally on colony gain/loss
- Overlap detection becomes O(new_colonies_this_step) instead of O(total_colonies)

### 1.9 — Adaptive Snapshot Interval
- More snapshots during active periods (wars, encounters), fewer during quiet
- Dynamic: 50 Myr during wars, 200 Myr during quiet
- Reduces total snapshots for 10 Gyr from 100 to ~40-60

### 1.10 — MLX for Gravitational Acceleration (Optional/Experimental) [5-20x]
- Apple's native GPU array framework with NumPy-like API
- `import mlx.core as mx` — drop-in for `np` operations
- Unified memory: no CPU↔GPU copies on Apple Silicon
- Lazy evaluation + automatic Metal GPU dispatch
- Target: `compute_total_acceleration_kernel` — the heaviest computation
- Complexity: Medium. Need to benchmark vs Numba to confirm benefit at 100k scale

**Deliverable**: Re-benchmark all techniques, document cumulative speedup

---

## Phase 2: Enhanced War Mechanics

**Goal**: Complete war system with phases, exhaustion integration, cooperation hookup

### 2.1 — War Phase Transitions
- Implement `WarPhase` progression in `_resolve_wars()`:
  - MOBILIZATION (0-0.5 Myr): No battles, both sides build strength
  - OFFENSIVE (0.5+ Myr): Active battles at disputed territories
  - STALEMATE (triggered by >3 battles with no territory change): Reduced battle frequency
  - PEACE_NEGOTIATIONS (triggered by exhaustion > 0.8 OR stalemate > 2 Myr): Roll for peace each step
  - CONCLUDED: War ends, cleanup
- Track phase duration, transition conditions

### 2.2 — War Exhaustion as Decision Driver
- War exhaustion > 0.5: increases stalemate probability by 2x
- War exhaustion > 0.8: triggers PEACE_NEGOTIATIONS phase
- War exhaustion > 0.95: forced peace (both sides too exhausted)
- Post-war: exhaustion decays at -0.05/Myr, limits ability to start new wars
- Resource debt > 50: increases self-destruction probability by 1.5x during crisis periods

### 2.3 — Cooperation System Integration
- Replace engine.py line 2760 personality-type alliance check with `CooperationSystem`
- Use maturity-based alliance formation (social_maturity threshold)
- Enable aid mechanics: allies share resources during wars
- Track reciprocity scores for alliance stability

### 2.4 — Communication Events
- Populate `communication_events` list:
  - War declaration: send to target + allies (light-cone delayed)
  - Alliance request: send to potential allies within communication range
  - Peace offer: send during PEACE_NEGOTIATIONS phase
  - Battle report: inform allies of outcomes
- Each event has `send_time_myr`, `arrival_time_myr`, `is_within_light_cone` flag
- Events only take effect at `arrival_time_myr` (causality enforcement)

### 2.5 — Config Parameters
- Add: `war_exhaustion_stalemate_threshold: float = 0.5`
- Add: `war_exhaustion_peace_threshold: float = 0.8`
- Add: `war_exhaustion_forced_peace_threshold: float = 0.95`
- Add: `resource_debt_crisis_multiplier: float = 1.5`
- Add: `cooperation_system_enabled: bool = True`

### 2.6 — Tests
- Test war phase transitions
- Test exhaustion-driven peace
- Test cooperation system integration
- Test communication event causality
- Test war + disaster interaction (disaster during war)

**Deliverable**: War mechanics complete, tests green, benchmark with active wars

---

## Phase 3: War Visualization + WebGPU Migration (Three.js)

**Goal**: Render wars in Three.js + migrate to WebGPU for 500k+ particle performance

### 3.1 — WebGPU Migration (Three.js r171+) [10-150x viz performance]
- Update Three.js to r171+ (production WebGPU since Sept 2025)
- Swap import: `import * as THREE from 'three/webgpu'`
- Add `await renderer.init()` before first render
- Convert custom GLSL shaders to TSL (Three Shader Language):
  - TSL compiles to both WGSL (WebGPU) and GLSL (WebGL fallback)
  - Write shaders as JavaScript functions, not raw shader strings
- **Compute shaders for star positions**:
  - Move position update to GPU compute: `instancedArray(starCount, 'vec3')`
  - Update 100k+ positions in <2ms vs 300ms+ CPU-side
  - CPU-based particle updates bottleneck at ~50k; WebGPU handles millions
- **InstancedMesh** over Points (WebGPU doesn't support variable point sizes)
- Automatic WebGL 2 fallback for older browsers

### 3.2 — Data Export for Wars
- Update `data_extractor.py` to export per-frame:
  - Territory ownership: `{civ_id: [star_indices]}` per frame
  - Active wars: `[{aggressor_id, defender_id, phase, disputed_stars}]`
  - Battle events: `[{star_idx, winner_id, loser_id, position}]`
  - War indicators: `[{civ_id, war_exhaustion, is_at_war}]`
  - Alliance pairs: `[{civ_a, civ_b}]`
  - Communication events: `[{sender, receiver, type, arrival_time}]`

### 3.3 — Territory Rendering
- Color colonies by owning civilization (unique color per civ)
- Use InstancedMesh for colony markers (performance at 100k scale)
- Contested zones (disputed stars) rendered in distinct color/pattern
- Consider: simple star-point coloring over expensive convex hulls at 100k scale

### 3.4 — Battle Effects (GPU Particle System)
- Move disaster/battle shockwave animations to GPU compute shaders
- Each disaster: position, time, radius, type in `instancedArray`
- Compute shader expands radius, fades alpha — handles 1000+ simultaneous effects at 60fps
- Flash effect at battle location, color-coded by outcome

### 3.5 — War Status UI
- War panel in sidebar: list active wars with participants, phase, duration
- Color-coded war phase indicator (green=mobilization, red=offensive, yellow=stalemate, white=negotiations)
- War exhaustion bar per civilization
- Alliance lines between allied civs (dashed, colored by strength)
- War events on timeline bar (like disaster events)

### 3.6 — Toggle Controls
- Toggle: Show territories
- Toggle: Show battles
- Toggle: Show alliances
- Toggle: Show communication events
- Panel: War info (like disaster info panel)

**Deliverable**: Wars visible in Three.js WebGPU export, 60fps with 100k+ stars

---

## Phase 4: Integration + Final Benchmark

### 4.1 — Full Integration Test
- 100k stars, 10 Gyr, optimistic preset (many civs)
- Verify: wars occur, phases transition, exhaustion forces peace, alliances form
- Verify: visualization renders all war elements via WebGPU
- Verify: snapshot memory within bounds (~20-50MB for full run with Blosc2)

### 4.2 — Performance Comparison
- Benchmark: original vs Phase 0 vs Phase 1 vs Phase 2+3
- Document cumulative speedup table
- Profile any new hotspots introduced by war mechanics

### 4.3 — Stress Test
- 100k stars, 10 Gyr, aggressive preset (max wars)
- Target: sim completes in <30s
- Target: HTML export <50MB (with Blosc2 + float16)
- Target: 60fps playback in browser (WebGPU compute shaders)

### 4.4 — Energy Conservation Check
- Verify Yoshida integrator conserves energy to <1% over 10 Gyr
- Compare stellar drift: Yoshida vs current leapfrog
- Document acceptable error bounds

**Deliverable**: Final benchmark doc, all tests pass

---

## Future Phase (Optional): Deep Architecture

Items deferred but documented for future sessions:

### F.1 — Parallel Arrays for CivilizationState [5-20x civ evolution]
- Replace `List[CivilizationState]` with parallel NumPy arrays:
  ```python
  civ_kardashev = np.zeros(MAX_CIVS, dtype=np.float64)
  civ_birth_time = np.zeros(MAX_CIVS, dtype=np.float64)
  civ_is_active = np.zeros(MAX_CIVS, dtype=np.bool_)
  ```
- Enables Numba batch ops over ALL civs simultaneously
- Keep Python dicts for variable-size fields (colonized_stars, targeted_stars)
- HIGH effort: major refactor of engine.py CivState usage

### F.2 — ProbeState as Structured NumPy Array [10x probe interpolation]
- Single `np.dtype` structured array for all active probes
- Vectorize `_interpolate_probe_positions()` — currently iterates Python objects

### F.3 — Taichi GPU Kernels via Metal [5-50x for custom kernels]
- `ti.init(arch=ti.gpu)` auto-selects Metal on macOS
- JIT-compiled GPU kernels for: acceleration, spatial hashing, hazard evaluation
- Useful when array-level parallelism (MLX/NumPy) isn't enough

### F.4 — Mixed-Variable Symplectic (Wisdom-Holman) Integrator
- Split Hamiltonian into Keplerian + perturbation
- Integrate Keplerian part exactly, apply perturbation as kick
- 10-100x larger timesteps for outer disk stars (nearly circular orbits)
- Only needed if stellar motion dominates at 500k+ stars

---

## Session Restart Protocol

Each phase is self-contained. To restart:
1. Read this file (`claude_comments/speedup_war_viz_plan.md`)
2. `git log --oneline -20` to see completed work
3. `mamba run -n galaticbot python scripts/benchmark_quick.py` for current state
4. Pick up at next unchecked item

## Phase Dependencies
```
Phase 0 (bugs+quick wins) → Phase 1 (numerical opt) → Phase 2 (war) → Phase 3 (viz+WebGPU) → Phase 4 (integration)
                                                       ↗ (can start 3.1-3.2 data export alongside 2)
```

Phase 3.1-3.2 (WebGPU migration + data export) can begin in parallel with Phase 2 since they're independent.

---

## Unresolved Questions

- What "optimistic" or "aggressive" preset params produce 50+ concurrent wars at 100k stars? Need to tune emergence rate + war probability to stress-test
- Current `encounter_scan_interval_myr = 100.0` — very infrequent. Decrease for more dynamic wars?
- `battle_resolution_interval_myr = 0.5` — one battle per 500k years. Enough?
- Territory rendering: convex hulls expensive at scale. Just color star points by owner instead?
- Communication events: block alliance formation until messages arrive (physical) or just visual/recorded?
- MLX vs Numba at 100k scale: need benchmark to decide. MLX wins for large arrays but has overhead for small ones
- Yoshida vs leapfrog energy conservation: need to verify <1% drift over 10 Gyr before committing

## Sources

- [Taichi Lang - GPU programming in Python](https://github.com/taichi-dev/taichi)
- [MLX - Apple array framework](https://github.com/ml-explore/mlx) | [WWDC25 session](https://developer.apple.com/videos/play/wwdc2025/315/)
- [MLX for scientific computing](https://vincent.codes.finance/posts/apple-mlx/)
- [JAX Metal plugin](https://developer.apple.com/metal/jax/)
- [Three.js WebGPU migration guide (2026)](https://www.utsubo.com/blog/webgpu-threejs-migration-guide)
- [WebGPU Galaxy simulation with compute shaders](https://threejsroadmap.com/blog/galaxy-simulation-webgpu-compute-shaders)
- [TSL and WebGPU field guide](https://blog.maximeheckel.com/posts/field-guide-to-tsl-and-webgpu/)
- [GPGPU particles with TSL](https://wawasensei.dev/courses/react-three-fiber/lessons/tsl-gpgpu)
- [100 Three.js performance tips (2026)](https://www.utsubo.com/blog/threejs-best-practices-100-tips)
- [Blosc2 lossy compression for float arrays](https://blosc.org/posts/blosc2-lossy-compression/)
- [Yoshida (1990) symplectic integrators](https://link.springer.com/article/10.1007/BF00048986)
- [High-order symplectic integrators (Rein & Tamayo 2019)](https://academic.oup.com/mnras/article/489/4/4632/5565063)
- [Numba SIMD autovectorization](https://tbetcke.github.io/hpc_lecture_notes/simd.html)
- [Understanding CPUs for Numba speed](https://pythonspeed.com/articles/speeding-up-numba/)
