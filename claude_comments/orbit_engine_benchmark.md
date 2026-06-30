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
