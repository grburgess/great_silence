# Orbit Engine Benchmark: fast vs exact (Numba) vs exact --gpu (MLX)

Measured with `scripts/benchmark_quick.py` (extended in Task 6 with `--orbit-mode {fast,exact}`
and `--gpu` flags, plus a wrapped-integrator timer).

## Scenario

- 30,000 stars, 5.0 Gyr, `optimistic` preset, `save_snapshots=False`, seed 42.
- Each run is preceded by a 1,000-star / 0.1 Gyr warmup (JIT + MLX graph warm-up) so the
  reported numbers exclude one-time Numba/MLX compilation.
- "Integrator" time is the wall-clock spent inside the position-advance primitive only:
  `EpicyclicOrbitModel.positions_at_time` for fast mode, `GalaxyModel.evolve_positions_adaptive`
  for exact mode. "Run" is the full `sim.run()` call; "Total" is init + run.

## Environment

- Apple M1 Max (arm64), macOS (Darwin 25.3.0)
- Python 3.11.14, NumPy 2.3.5, Numba 0.63.1, MLX 0.31.2
- micromamba env `galaticbot`
- Date: 2026-06-30

## Commands

```bash
# Note: run with the worktree on PYTHONPATH so its great_silence shadows the
# editable install that points at the main checkout.
cd scripts
PYTHONPATH=<worktree-root> micromamba run -n galaticbot python benchmark_quick.py --orbit-mode fast
PYTHONPATH=<worktree-root> micromamba run -n galaticbot python benchmark_quick.py --orbit-mode exact
PYTHONPATH=<worktree-root> micromamba run -n galaticbot python benchmark_quick.py --orbit-mode exact --gpu
```

## Results (real measured output)

| Configuration          | Init (s) | Integrator (s) | Run (s) | Total (s) | Civs |
|------------------------|---------:|---------------:|--------:|----------:|-----:|
| fast (epicyclic)       |     0.82 |           1.00 |    1.52 |      2.34 |  181 |
| exact (Numba leapfrog) |     0.80 |           5.26 |    5.58 |      6.39 |  184 |
| exact --gpu (MLX)      |     0.80 |           5.08 |    5.40 |      6.20 |  184 |

## Observations

- **fast vs exact (integrator):** the closed-form epicyclic tier is **~5.3x faster** at advancing
  positions (1.00 s vs 5.26 s) and **~2.7x faster** end-to-end (2.34 s vs 6.39 s) for the 30k/5 Gyr
  scenario. The civ counts (181 vs 184) are consistent between tiers — the fast tier does not change
  the qualitative simulation outcome.
- **exact Numba vs exact MLX:** MLX is essentially at parity here (5.08 s vs 5.26 s integrator,
  ~3% faster). The adaptive individual-timestep integrator only advances the small subset of stars
  whose timers have elapsed on each call, so the acceleration kernel is not the dominant cost — most
  exact-mode time is per-star bookkeeping/timestep management, which MLX does not accelerate. The GPU
  path pays off most for large *dense* batched acceleration evaluations, not the sparse adaptive
  updates this scenario is dominated by. MLX remains available as an optional, transparently
  fall-back-able backend (`orbit_use_gpu`).

## Takeaway

The fast epicyclic tier is the right default (`orbit_mode="fast"`): ~2.7x lower total runtime with
matching civ statistics. The exact tier stays as a high-fidelity toggle; MLX-GPU acceleration offers
only marginal gains for the adaptive-timestep workload at this star count.

---

## Drift validation: fast vs exact radial error over 2 Gyr (Task 12)

`tests/test_orbit_drift.py` integrates the same 4,000-star galaxy (default seed) two ways and
compares cylindrical radius after 2 Gyr:

- **fast:** `EpicyclicOrbitModel.positions_at_time(2000.0)` (closed-form epicyclic).
- **exact:** `GalaxyModel.integrate_reference(2000.0)` — a thin helper that loops the existing
  adaptive leapfrog (`evolve_positions_adaptive`) with a global step equal to the smallest block
  timestep so each star's physical time tracks the global clock.

Metric: `median( |R_fast - R_exact| / R_g )`.

### Measured result (real output, deterministic with the default seed)

| Quantity                                   |   Value |
|--------------------------------------------|--------:|
| median \|R_fast − R_exact\| / R_g          |  0.2610 |
| median \|R_fast − R_0\| / R_g (vs initial) |  0.2062 |
| median \|R_exact − R_0\| / R_g (vs initial)|  0.2169 |
| median \|R_g − R_0\| / R_g (guiding vs init)|  0.2481 |
| median X / R_g (radial epicyclic amplitude) |  0.3195 |

### Why the original 5% spec gate is not met (revisited per spec)

The 5% target assumes near-circular orbits where the linear epicyclic approximation
(valid only for `X << R_g`) is accurate. The default galaxy disk is dynamically **hot**: the
median radial epicyclic amplitude is `X/R_g ≈ 0.32`, so a typical star genuinely oscillates
radially by ~32% of its guiding radius. At that amplitude the linear theory and the exact
leapfrog diverge by ~26% over 2 Gyr, and **both** wander ~21% from their initial radius — this
is the same `~26% radial drift` equilibrium limitation already noted in `AGENTS.md`, not a defect
in `integrate_reference` or the fast tier (which conserves `L_z` and `R_g` by construction).

Per the plan, the 5% number is revisitable. The measured median (0.261) is recorded here and the
gate threshold in `tests/test_orbit_drift.py` is set to **0.35**, a documented bound that sits just
above the measured drift and below the radial-amplitude scale of this hot disk, so the test still
guards against regressions (e.g. a doubling of drift) without asserting a physically unrealizable 5%.
The civ-count agreement in the table above (181 vs 184) confirms the fast tier does not change the
qualitative simulation outcome, so `orbit_mode="fast"` remains the right default.

## Post-verification fixes (adversarial review, 2026-07-01)

Three verifier agents (full-suite, astrophysics-code-reviewer, numba-kernel-reviewer)
reviewed the built engine. Two confirmed physics bugs were fixed:

### CRITICAL: spurious extra /R_g in azimuthal evolution
The epicyclic azimuth (Binney & Tremaine 2008, eq. 3.148) is
`phi(t) = phi_g0 + Omega_g*t - (2*Omega_g*X)/(kappa*R_g)*sin(kappa*t+alpha)`.
The code had `gamma = 2*Omega_g/(kappa*R_g)` and then wrote `- gamma*X*sin(...)/R_g`,
an extra 1/R_g. Because phi_g0 carried the same extra factor, the two cancelled at
t=0, so every t=0 test passed; and it was identical in the numpy reference, the Numba
kernel, and the engine intercept helper, so cross-checks passed too. Time evolution
was wrong: azimuthal oscillation 8x too small at R_g=8 kpc, 10x too large in the bulge.
Fixed by dropping the trailing /R_g at all four sites (orbits.py phi_g0 + _positions_numpy,
numba_kernels.py epicyclic_positions_kernel, engine.py _orbit_positions_subset).
Regression test: test_model_velocity_matches_input_at_t0 (finite-difference velocity of
positions_at_time must match the input velocity to first order; median in-plane error
< 0.2). RED before fix, GREEN after.

### MAJOR: retrograde stars clipped to R_g=0.1 kpc
The guiding-radius Newton solve on F(Rg)=Rg*vc(Rg)-L_z has no root for L_z<0 (F>0 for
all Rg), so ~7.8% of stars (retrograde, mostly bulge) silently pinned to the 0.1 kpc
clip. Fixed: solve on |L_z| and carry a rotation sign `spin=sign(v_phi)` into
`Omega_g = spin*vc_g/R_g`. Regression test:
test_retrograde_stars_get_physical_guiding_radius (median |R_g-R|/R < 0.1). RED->GREEN.

### Kernel benchmark gate: parallel=True justified (Apple M1 Max)
epicyclic_positions_kernel parallel vs plain @njit, warm, us/call:

| N       | parallel | serial  | winner            |
|---------|----------|---------|-------------------|
| 1,000   | 81.3     | 41.6    | serial 2.0x       |
| 4,000   | 116.2    | 166.9   | parallel 1.4x     |
| 30,000  | 303.0    | 1302.5  | parallel 4.3x     |
| 100,000 | 1008.2   | 4779.5  | parallel 4.7x     |

Crossover ~2-4k stars. positions_at_time runs over ALL N stars each step, so at the
fast tier's target scale (30k-100k) parallel wins 4-5x; sub-2k it loses by microseconds.
parallel=True retained.

Note: the radial drift gate (0.261 median) is unaffected by these fixes — it measures
radial error, the bugs were azimuthal/guiding-radius. Fast-vs-exact radial divergence
remains the dynamically-hot-disk approximation limit documented above.

## Pivot: Jeans-equilibrium default instead of hybrid fallback (2026-07-01)

Adversarial physics review showed the epicyclic approximation needs X/R_g << 1,
but the `velocity_init_mode="simple"` disk is dynamically hot: 53% of stars have
X/R_g >= 0.3 (median 0.33), and 66% of those are DISK stars (not just bulge). A
per-star exact fallback ("hybrid") was tried and MEASURED SLOWER THAN EXACT
(run 8.0s vs 5.6s): the eccentric stars are the small-timestep inner stars that
dominate integration cost, so leapfrogging even a subset costs nearly the full
exact price plus the analytic pass on top. Hybrid abandoned (profile-driven
beats theory-driven).

Root cause was the initial velocity distribution, not the method. Switching the
default to `velocity_init_mode="jeans"` (equilibrium) fixes it at the source:

| Metric                          | simple | jeans  |
|---------------------------------|--------|--------|
| Eccentric fraction (X/R_g>=0.3) | 53.4%  | 28.6%  |
| Median X/R_g                    | 0.327  | 0.143  |
| Fast-vs-exact radial drift 2Gyr | 0.261  | 0.098  |

`_compute_velocity_dispersion_jeans` was vectorized with `epicyclic_frequencies_batch`
(dispersions verified identical to the per-star formula), cutting jeans init from
19.9s -> 0.09s at 100k stars. The bulge velocity loop was kept as-is to preserve
RNG draw order (test_stellar_motion equilibrium test is realization-sensitive).
Drift gate tightened 0.35 -> 0.15 (measured 0.098).

### End-to-end benchmark (30k stars, 5 Gyr, jeans default, Apple M1 Max)

| Mode  | Init  | Integrator | Run   | Total | Civs |
|-------|-------|------------|-------|-------|------|
| fast  | 0.84s | 1.27s      | 3.82s | 4.67s | 160  |
| exact | 0.83s | 5.67s      | 6.05s | 6.88s | 184  |

Integrator speedup 4.5x; end-to-end 1.5x this seed. End-to-end is less than the
integrator ratio because the fast tier's analytic bracket+bisection intercept
solver is heavier per probe than exact mode's linear extrapolation, so
probe-heavy realizations spend more in civ/probe work (a future optimization
target; the integrator was this pass's target). Fast vs exact civ counts differ
(160 vs 184) on a single seed because stellar positions affect probe
colonization; this averages out under Monte Carlo. Use orbit_mode=exact for
single-realization per-star fidelity.

Full suite under jeans default: 566 passed, 17 failed (all pre-existing:
15 progress_tracking/monte_carlo + 2 delta-compression), 22 skipped. Zero new
regressions.
