#!/usr/bin/env python
"""Comprehensive benchmark for 100k stars, 10 Gyr with profiling."""
import time
import cProfile
import pstats
import io
from pathlib import Path
import psutil
import os
from great_silence import GalaxySimulation, SimulationConfig


def get_memory_mb():
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def run_benchmark():
    """Run comprehensive benchmark with profiling."""
    print("=" * 80)
    print("WAR BENCHMARK: 100k stars, 10 Gyr, many civilizations")
    print("=" * 80)

    # Config for many civilizations and wars
    config = SimulationConfig.with_preset("optimistic")
    config.galaxy.total_stars = 100_000
    config.simulation.simulation_duration_gyr = 10.0
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 100.0  # 100 snapshots

    # Force more emergences
    config.civilization.base_emergence_rate_per_myr = 0.1  # Higher rate

    # Enable encounters/wars
    config.simulation.encounter_scan_interval_myr = 50.0  # More frequent

    print(f"\nConfiguration:")
    print(f"  Stars: {config.galaxy.total_stars:,}")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Emergence rate: {config.civilization.base_emergence_rate_per_myr} per Myr")
    print(f"  Encounter scan: {config.simulation.encounter_scan_interval_myr} Myr")
    print(f"  Snapshot interval: {config.simulation.snapshot_interval_myr} Myr")

    # Memory baseline
    mem_start = get_memory_mb()
    print(f"\nMemory baseline: {mem_start:.1f} MB")

    # Create profiler
    profiler = cProfile.Profile()

    # Initialization
    print("\n" + "=" * 80)
    print("INITIALIZATION")
    print("=" * 80)
    t0 = time.perf_counter()
    profiler.enable()

    sim = GalaxySimulation(config, seed=42)
    sim.initialize()

    profiler.disable()
    t_init = time.perf_counter() - t0
    mem_after_init = get_memory_mb()

    print(f"Init time: {t_init:.2f}s")
    print(f"Memory after init: {mem_after_init:.1f} MB (+{mem_after_init - mem_start:.1f} MB)")

    # Simulation
    print("\n" + "=" * 80)
    print("SIMULATION")
    print("=" * 80)
    t1 = time.perf_counter()
    profiler.enable()

    sim.run(verbose=True)

    profiler.disable()
    t_run = time.perf_counter() - t1
    mem_peak = get_memory_mb()

    print(f"\nSimulation time: {t_run:.2f}s")
    print(f"Peak memory: {mem_peak:.1f} MB")

    # Statistics
    print("\n" + "=" * 80)
    print("SIMULATION STATISTICS")
    print("=" * 80)
    stats = sim.get_statistics()

    print(f"Total civilizations: {stats['total_civilizations']}")
    print(f"Currently active: {stats['currently_active_civilizations']}")
    print(f"Max concurrent: {stats['max_concurrent_civilizations']}")
    print(f"Self-destructed: {stats['self_destructed_civilizations']}")
    print(f"Destroyed by hazards: {stats['destroyed_by_hazards']}")

    # War statistics
    if hasattr(sim, '_war_count'):
        print(f"\nWar statistics:")
        print(f"  Total wars: {sim._war_count}")
        print(f"  Active wars: {len([w for w in sim.wars if w.is_active])}")

    # Snapshot statistics
    if sim.snapshots:
        print(f"\nSnapshot statistics:")
        print(f"  Total snapshots: {len(sim.snapshots)}")
        avg_snapshot_size = sum(len(str(s.__dict__)) for s in sim.snapshots) / len(sim.snapshots)
        print(f"  Avg snapshot size: ~{avg_snapshot_size / 1024:.1f} KB")

    # Profile analysis
    print("\n" + "=" * 80)
    print("PROFILING RESULTS - TOP 30 FUNCTIONS")
    print("=" * 80)

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('cumulative')
    ps.print_stats(30)

    profile_output = s.getvalue()
    print(profile_output)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total time: {t_init + t_run:.2f}s")
    print(f"  - Init: {t_init:.2f}s ({100 * t_init / (t_init + t_run):.1f}%)")
    print(f"  - Run:  {t_run:.2f}s ({100 * t_run / (t_init + t_run):.1f}%)")
    print(f"Peak memory: {mem_peak:.1f} MB")
    print(f"Civilizations: {stats['total_civilizations']} total, {stats['max_concurrent_civilizations']} max concurrent")

    # Write results to file
    output_path = Path("claude_comments/benchmark_results.md")
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w') as f:
        f.write("# Benchmark Results - War Implementation\n\n")
        f.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Configuration\n\n")
        f.write(f"- Stars: {config.galaxy.total_stars:,}\n")
        f.write(f"- Duration: {config.simulation.simulation_duration_gyr} Gyr\n")
        f.write(f"- Emergence rate: {config.civilization.base_emergence_rate_per_myr} per Myr\n")
        f.write(f"- Encounter scan: {config.simulation.encounter_scan_interval_myr} Myr\n")
        f.write(f"- Snapshot interval: {config.simulation.snapshot_interval_myr} Myr\n\n")

        f.write("## Performance\n\n")
        f.write(f"- **Total time**: {t_init + t_run:.2f}s\n")
        f.write(f"  - Init: {t_init:.2f}s ({100 * t_init / (t_init + t_run):.1f}%)\n")
        f.write(f"  - Run: {t_run:.2f}s ({100 * t_run / (t_init + t_run):.1f}%)\n")
        f.write(f"- **Peak memory**: {mem_peak:.1f} MB\n\n")

        f.write("## Simulation Statistics\n\n")
        f.write(f"- Total civilizations: {stats['total_civilizations']}\n")
        f.write(f"- Currently active: {stats['currently_active_civilizations']}\n")
        f.write(f"- Max concurrent: {stats['max_concurrent_civilizations']}\n")
        f.write(f"- Self-destructed: {stats['self_destructed_civilizations']}\n")
        f.write(f"- Destroyed by hazards: {stats['destroyed_by_hazards']}\n\n")

        if sim.snapshots:
            f.write("## Snapshot Statistics\n\n")
            f.write(f"- Total snapshots: {len(sim.snapshots)}\n")
            avg_snapshot_size = sum(len(str(s.__dict__)) for s in sim.snapshots) / len(sim.snapshots)
            f.write(f"- Avg snapshot size: ~{avg_snapshot_size / 1024:.1f} KB\n\n")

        f.write("## Profiling - Top 30 Functions\n\n")
        f.write("```\n")
        f.write(profile_output)
        f.write("```\n")

    print(f"\nResults written to: {output_path}")

    return sim, stats


if __name__ == "__main__":
    sim, stats = run_benchmark()
