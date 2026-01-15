#!/usr/bin/env python
"""
Baseline profiling script for simulation performance optimization.

Run with:
    mamba run -n galaticbot python scripts/benchmark_baseline.py
"""

import time
import cProfile
import pstats
import io
from pathlib import Path

from great_silence import GalaxySimulation, SimulationConfig


def run_benchmark(n_stars: int = 30_000, duration_gyr: float = 5.0, seed: int = 42, warmup: bool = True):
    """Run simulation and collect timing data."""
    
    print(f"=" * 60)
    print(f"BASELINE BENCHMARK: {n_stars:,} stars, {duration_gyr} Gyr")
    print(f"=" * 60)
    
    if warmup:
        print("\nWarming up Numba kernels...")
        warmup_config = SimulationConfig.with_preset("optimistic")
        warmup_config.galaxy.total_stars = 1000
        warmup_config.simulation.simulation_duration_gyr = 0.1
        warmup_config.simulation.save_snapshots = False
        warmup_sim = GalaxySimulation(warmup_config, seed=seed)
        warmup_sim.initialize()
        warmup_sim.run(verbose=False)
        print("Warmup complete.\n")
    
    # Use optimistic preset
    config = SimulationConfig.with_preset("optimistic")
    config.galaxy.total_stars = n_stars
    config.simulation.simulation_duration_gyr = duration_gyr
    config.simulation.random_seed = seed
    config.simulation.save_snapshots = False  # Skip I/O for pure compute benchmark
    config.simulation.adaptive_timestepping = True
    
    print(f"\nConfiguration:")
    print(f"  Preset: optimistic")
    print(f"  Stars: {config.galaxy.total_stars:,}")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Adaptive timestep: {config.simulation.adaptive_timestepping}")
    print(f"  Max timestep: {config.simulation.max_timestep_myr} Myr")
    print(f"  Min timestep: {config.simulation.min_timestep_myr} Myr")
    
    # Create simulation
    print("\n" + "-" * 60)
    print("INITIALIZATION")
    print("-" * 60)
    
    init_start = time.perf_counter()
    sim = GalaxySimulation(config, seed=seed)
    sim.initialize()
    init_time = time.perf_counter() - init_start
    print(f"Initialization time: {init_time:.2f}s")
    
    # Profile the main run
    print("\n" + "-" * 60)
    print("MAIN SIMULATION (profiled)")
    print("-" * 60)
    
    profiler = cProfile.Profile()
    
    run_start = time.perf_counter()
    profiler.enable()
    sim.run(verbose=True)
    profiler.disable()
    run_time = time.perf_counter() - run_start
    
    # Print results
    print("\n" + "-" * 60)
    print("TIMING SUMMARY")
    print("-" * 60)
    print(f"Initialization: {init_time:.2f}s")
    print(f"Simulation run: {run_time:.2f}s")
    print(f"Total: {init_time + run_time:.2f}s")
    
    # Simulation statistics
    stats = sim.get_statistics()
    print(f"\nSimulation Statistics:")
    print(f"  Total civilizations: {stats['total_civilizations']}")
    print(f"  Active civilizations: {stats['active_civilizations']}")
    print(f"  Extinct civilizations: {stats['extinct_civilizations']}")
    
    # Profile statistics
    print("\n" + "-" * 60)
    print("TOP 20 FUNCTIONS BY CUMULATIVE TIME")
    print("-" * 60)
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    print(s.getvalue())
    
    # Also save to file
    output_dir = Path("output/benchmarks")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    profile_path = output_dir / "baseline_profile.stats"
    profiler.dump_stats(str(profile_path))
    print(f"\nProfile saved to: {profile_path}")
    
    # Print timing breakdown by method
    print("\n" + "-" * 60)
    print("KEY METHOD TIMINGS")
    print("-" * 60)
    
    s2 = io.StringIO()
    ps2 = pstats.Stats(profiler, stream=s2).sort_stats('cumulative')
    ps2.print_stats(
        '_compute_next_timestep',
        '_check_civilization_emergence', 
        '_process_probe_events',
        '_evolve_civilizations',
        '_apply_hazards',
        '_find_nearest_targets',
        'find_causal_groups'
    )
    print(s2.getvalue())
    
    return {
        'init_time': init_time,
        'run_time': run_time,
        'total_time': init_time + run_time,
        'stats': stats,
    }


if __name__ == "__main__":
    results = run_benchmark()
    
    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print(f"Total wall time: {results['total_time']:.2f}s")
