#!/usr/bin/env python
"""Quick benchmark - single run."""
import argparse
import time

from great_silence import GalaxySimulation, SimulationConfig


def _instrument_integrator(sim):
    """Wrap the active position-advance primitive to accumulate integrator time."""
    timer = {"total": 0.0}

    if sim.orbit_model is not None:
        original = sim.orbit_model.positions_at_time

        def wrapped(t_myr, **kwargs):
            t0 = time.perf_counter()
            result = original(t_myr, **kwargs)
            timer["total"] += time.perf_counter() - t0
            return result

        sim.orbit_model.positions_at_time = wrapped
    else:
        original = sim.galaxy.evolve_positions_adaptive

        def wrapped(dt_myr, use_numba=True):
            t0 = time.perf_counter()
            result = original(dt_myr, use_numba=use_numba)
            timer["total"] += time.perf_counter() - t0
            return result

        sim.galaxy.evolve_positions_adaptive = wrapped

    return timer


def _build_config(stars, duration_gyr, orbit_mode, gpu):
    config = SimulationConfig.with_preset("optimistic")
    config.galaxy.total_stars = stars
    config.simulation.simulation_duration_gyr = duration_gyr
    config.simulation.save_snapshots = False
    config.simulation.orbit_mode = orbit_mode
    config.simulation.orbit_use_gpu = gpu
    return config


def main():
    parser = argparse.ArgumentParser(description="Quick orbit-engine benchmark.")
    parser.add_argument(
        "--orbit-mode",
        choices=["fast", "exact"],
        default="fast",
        help="Stellar orbit tier (fast=epicyclic, exact=leapfrog).",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Use MLX Apple-GPU acceleration for the exact tier.",
    )
    args = parser.parse_args()

    label = f"orbit_mode={args.orbit_mode}, gpu={args.gpu}"
    print(f"Quick benchmark: 30k stars, 5 Gyr, optimistic ({label})", flush=True)

    # Warmup
    print("Warmup...", flush=True)
    c = _build_config(1000, 0.1, args.orbit_mode, args.gpu)
    s = GalaxySimulation(c, seed=0)
    s.initialize()
    s.run(verbose=False)
    print("Warmup done.", flush=True)

    # Main run
    print("\nMain benchmark...", flush=True)
    config = _build_config(30_000, 5.0, args.orbit_mode, args.gpu)

    t0 = time.perf_counter()
    sim = GalaxySimulation(config, seed=42)
    sim.initialize()
    t_init = time.perf_counter() - t0

    timer = _instrument_integrator(sim)

    t1 = time.perf_counter()
    sim.run(verbose=False)
    t_run = time.perf_counter() - t1

    stats = sim.get_statistics()

    print("\nResults:", flush=True)
    print(f"  Orbit mode: {args.orbit_mode} (gpu={args.gpu})", flush=True)
    print(f"  Init: {t_init:.2f}s", flush=True)
    print(f"  Integrator: {timer['total']:.2f}s", flush=True)
    print(f"  Run:  {t_run:.2f}s", flush=True)
    print(f"  Total: {t_init + t_run:.2f}s", flush=True)
    print(f"  Civs: {stats['total_civilizations']}", flush=True)


if __name__ == "__main__":
    main()
