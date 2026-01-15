#!/usr/bin/env python
"""Quick benchmark - single run."""
import time
from great_silence import GalaxySimulation, SimulationConfig

print("Quick benchmark: 30k stars, 5 Gyr, optimistic", flush=True)

# Warmup
print("Warmup...", flush=True)
c = SimulationConfig.with_preset("optimistic")
c.galaxy.total_stars = 1000
c.simulation.simulation_duration_gyr = 0.1
c.simulation.save_snapshots = False
s = GalaxySimulation(c, seed=0)
s.initialize()
s.run(verbose=False)
print("Warmup done.", flush=True)

# Main run
print("\nMain benchmark...", flush=True)
config = SimulationConfig.with_preset("optimistic")
config.galaxy.total_stars = 30_000
config.simulation.simulation_duration_gyr = 5.0
config.simulation.save_snapshots = False

t0 = time.perf_counter()
sim = GalaxySimulation(config, seed=42)
sim.initialize()
t_init = time.perf_counter() - t0

t1 = time.perf_counter()
sim.run(verbose=False)
t_run = time.perf_counter() - t1

stats = sim.get_statistics()

print(f"\nResults:", flush=True)
print(f"  Init: {t_init:.2f}s", flush=True)
print(f"  Run:  {t_run:.2f}s", flush=True)
print(f"  Total: {t_init + t_run:.2f}s", flush=True)
print(f"  Civs: {stats['total_civilizations']}", flush=True)
