# Design: GalaticBot Performance + Visual Pass

**Date:** 2026-06-30
**Status:** Approved (design phase)
**Branch:** dev

## Goal

Take another pass at (1) simulation speed on heavy runs, (2) interactive app
responsiveness, (3) Three.js visual polish, and (4) NiceGUI control/dashboard
UX. The user opted into all four tracks.

## Key insight

Stellar motion uses a **fixed, time-constant, axisymmetric analytic potential**
(Miyamoto-Nagai disk + Hernquist bulge + isothermal halo), *not* self-gravity.
Each star's orbit is therefore independent of every other star's — there is no
pairwise N-body force, so a Barnes-Hut tree gives nothing. The remaining
bottleneck (`evolve_positions_adaptive`, ~86s of the run) is integrating N
*independent* ODEs in a smooth field.

That regime is exactly where **action-angle / epicyclic methods** apply (cf.
AGAMA, galpy): characterize each orbit once (guiding radius, epicyclic frequency
κ — already computed — vertical frequency, radial/vertical amplitudes, phases),
then position at *any* time `t` is a closed-form function
`x(t) = f(amplitudes, phases + frequency·t)`. O(1) per star per query, no
stepping. This single idea cascades into all four tracks:

- **Sim speed:** the integrator collapses toward near-zero for the fast tier.
- **Probe targeting:** intercepts become a closed-form root-find instead of
  iterative convergence (removes most of the 19s targeting + 8s `np.linalg.norm`).
- **Viz smoothness:** positions become analytic → GPU shader computes exact
  star positions from a few uniforms → smooth scrub/playback, zero CPU.
- **Stability:** the noted "26% radial drift over 100 Myr" is a leapfrog
  equilibrium artifact; epicyclic orbits are stable by construction.

## Decisions locked

- Numerics appetite: **tiered** — fast approximate default + exact high-fidelity toggle.
- Fast tier: **self-contained epicyclic** orbits in Numba (no new dependency,
  reuses existing κ computation, ~1-2% positional error over a few Gyr).
- Exact tier: **MLX-backed GPU** path on Apple Silicon, Numba fallback.
- Viz: **WebGPU compute rewrite** (WebGPURenderer + TSL), with the existing
  r128 WebGL export kept as a graceful fallback.

## Architecture overview

Four workstreams, sequenced by dependency. **A** is foundational: its analytic
`positions_at_time(t)` is consumed by B (intercepts), C (viz), and snapshots.

```
A. Tiered Orbit Engine ──┬──> B. Analytic Probe Intercepts
                         ├──> C. WebGPU Compute Viz
                         └──> D. NiceGUI Polish
```

## A. Tiered Orbit Engine — `galaxy/orbits.py` (new), `config`

- **Config:** `orbit_mode: "fast" | "exact"` (default `"fast"`),
  `orbit_use_gpu: bool` (auto-detect MLX, else Numba). Existing
  `stellar_motion_adaptive`/`eta`/min_dt/max_dt govern the exact tier only.
- **Fast tier — `EpicyclicOrbitModel`:** at init, per star from
  `(R, φ, z, v_R, v_φ, v_z)` compute guiding radius `R_g` (from `L_z`),
  epicyclic freq `κ(R_g)`, vertical freq `ν(R_g)`, radial amplitude+phase,
  vertical amplitude+phase, guiding angular rate `Ω_g`. Then
  `positions_at_time(t)` is a closed-form Numba kernel
  `epicyclic_positions_kernel` — O(1) per star, evaluable at any `t`.
- **Exact tier — MLX backend:** port `compute_total_acceleration_kernel` math
  to MLX array ops; batch the adaptive kick-drift over active stars on the
  Apple GPU. Fall back to the current Numba kernel if MLX is absent.
- **Tests (TDD):** epicyclic-vs-leapfrog drift under threshold over 2 Gyr;
  `L_z`/energy conservation; circular-orbit closed-form sanity; MLX path
  matches Numba path within tolerance.

## B. Analytic Probe Intercepts — `simulation/engine.py`

- Replace iterative `_calculate_intercept_position` convergence with a 1D
  root-find on `|pos_target(t) − pos_launch| = v_probe·(t − t_launch)` against
  the analytic orbit; vectorize the batch variant. Removes most of the 19s
  targeting + 8s `np.linalg.norm`.
- KD-tree queries run against slowly-varying guiding centers → fewer rebuilds;
  keep the existing boolean-mask exclusion.
- **Tests:** intercept solution matches brute-force sampling; no-solution /
  unreachable target handled.

## C. WebGPU Compute Viz — `visualization/threejs` → WebGPURenderer + TSL

- **GPU-computed positions:** ship per-star orbit params
  (`R_g, a_R, φ_R, κ, Ω_g, a_z, φ_z, ν`) to the GPU; a compute/vertex shader
  evaluates the exact analytic position from a `currentTime` uniform. Zero
  per-frame CPU position upload → smooth playback and scrubbing.
- **Look:** temperature→color stars (from mass/type), additive HDR sprites,
  **selective bloom** (stars/disasters only), ACESFilmic tone mapping,
  volumetric nebula backdrop, upgraded disaster shockwave/glow shaders,
  cinematic intro camera.
- **Payload:** `data_extractor.py` emits orbit params per star instead of
  per-frame position arrays → much smaller HTML exports.
- **Fallback:** keep the current r128 WebGL export when `navigator.gpu` is
  unavailable.
- **Tests:** export-data schema tests; Playwright smoke test (page loads,
  canvas present, no console errors) via the Playwright MCP.

## D. NiceGUI Polish — `webapp/`

- **Smoother:** async run loop, throttled event feed, progress driven by
  sim-time fraction. The fast tier makes runs finish quickly, so progress feels
  instant — directly fixes the stalling progress bar.
- **Premium:** extend `themes.py` — glassmorphism cards, typographic scale,
  motion/transitions, refreshed results dashboard + `parameter_plots`,
  responsive layout. (frontend-design skill applied during implementation.)
- **Tests:** webapp builds/imports; theme application smoke test.

## Build plan (ultracode workflow)

- **Phase 1:** A — orbit engine + benchmark harness extension
  (`benchmark_quick.py` compares fast vs exact tier).
- **Phase 2:** B — analytic intercepts.
- **Phase 3 (parallel):** C — WebGPU viz; D — NiceGUI polish.

## Success criteria

- Fast tier ≥10× on the ~86s integrator; end-to-end 100k / 10 Gyr run well
  under the current 128s.
- Fast-vs-exact positional drift documented and bounded: median per-star radial
  error < 5% of guiding radius `R_g` over 2 Gyr, with `L_z` conserved to
  machine precision by construction. (Number revisitable once measured; it is
  the pass/fail gate for the fast tier's default-on status.)
- Viz: smooth 60 FPS scrub at 100k stars on WebGPU; graceful WebGL fallback.
- App: no progress stalls; refreshed premium theme.
- All existing tests green; new tests per workstream.

## Out of scope

- True N-body / self-gravity (the potential is fixed by design).
- Triaxial / substructure potentials (epicyclic model assumes axisymmetry).
- Full migration of the existing r128 templates to ESM (WebGPU path is new and
  additive; r128 remains only as fallback).
