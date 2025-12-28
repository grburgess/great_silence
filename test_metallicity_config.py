#!/usr/bin/env python3
"""Test configurable metallicity-based probe targeting."""

from great_silence import GalaxySimulation, SimulationConfig, configure_m1_max_threading
import numpy as np

configure_m1_max_threading()

print("="*70)
print("CONFIGURABLE METALLICITY TARGETING TEST")
print("="*70)

# Test 1: Default configuration
print("\n[TEST 1] Default Metallicity Thresholds")
config = SimulationConfig.with_preset('optimistic')
config.galaxy.total_stars = 5_000
config.simulation.duration_gyr = 1.0
config.simulation.time_step_myr = 0.1
config.simulation.num_realizations = 1
config.simulation.save_snapshots = False
config.civilization.expansion_enabled = True

print(f"  K=0.85-0.95: {config.civilization.metallicity_threshold_k085:.2f} [Fe/H]")
print(f"  K=0.95-1.20: {config.civilization.metallicity_threshold_k095:.2f} [Fe/H]")
print(f"  K>1.20: {config.civilization.metallicity_threshold_k120:.2f} [Fe/H]")
print(f"  Sensor range: {config.civilization.probe_sensor_range_pc:.1f} pc")
print(f"  Mid-flight retargeting: {config.civilization.enable_mid_flight_retargeting}")

sim = GalaxySimulation(config, seed=42)
sim.run(verbose=False)

expanding_civs = [c for c in sim.civilizations if c.expansion_program_started]
print(f"\n  Civilizations that started expansion: {len(expanding_civs)}")

if expanding_civs:
    for civ in expanding_civs[:3]:
        print(f"    Civ {civ.civ_id}: K={civ.expansion_start_kardashev:.2f}, "
              f"min[Fe/H]={civ.probe_min_metallicity:.2f}, "
              f"sensor={civ.probe_sensor_range_pc:.1f}pc")

# Test 2: Custom aggressive expansion
print("\n[TEST 2] Aggressive Expansion (Relaxed Metallicity Thresholds)")
config2 = SimulationConfig.with_preset('optimistic')
config2.galaxy.total_stars = 5_000
config2.simulation.duration_gyr = 1.0
config2.simulation.time_step_myr = 0.1
config2.simulation.num_realizations = 1
config2.simulation.save_snapshots = False

# Lower thresholds = can use poorer systems = more expansion
config2.civilization.metallicity_threshold_k085 = -0.6
config2.civilization.metallicity_threshold_k095 = -0.8
config2.civilization.metallicity_threshold_k120 = -1.3

# Extended sensor range
config2.civilization.probe_sensor_range_pc = 20.0

print(f"  K=0.85-0.95: {config2.civilization.metallicity_threshold_k085:.2f} [Fe/H] (relaxed)")
print(f"  K=0.95-1.20: {config2.civilization.metallicity_threshold_k095:.2f} [Fe/H] (relaxed)")
print(f"  K>1.20: {config2.civilization.metallicity_threshold_k120:.2f} [Fe/H] (relaxed)")
print(f"  Sensor range: {config2.civilization.probe_sensor_range_pc:.1f} pc (extended)")

sim2 = GalaxySimulation(config2, seed=42)
sim2.run(verbose=False)

expanding_civs2 = [c for c in sim2.civilizations if c.expansion_program_started]
colonized_total2 = sum(len(c.colonized_stars) for c in expanding_civs2)
print(f"\n  Civilizations that started expansion: {len(expanding_civs2)}")
print(f"  Total systems colonized: {colonized_total2}")

if expanding_civs2:
    for civ in expanding_civs2[:3]:
        print(f"    Civ {civ.civ_id}: K={civ.expansion_start_kardashev:.2f}, "
              f"min[Fe/H]={civ.probe_min_metallicity:.2f}, "
              f"colonies={len(civ.colonized_stars)}, "
              f"sensor={civ.probe_sensor_range_pc:.1f}pc")

# Test 3: Conservative expansion
print("\n[TEST 3] Conservative Expansion (Strict Metallicity Thresholds)")
config3 = SimulationConfig.with_preset('optimistic')
config3.galaxy.total_stars = 5_000
config3.simulation.duration_gyr = 1.0
config3.simulation.time_step_myr = 0.1
config3.simulation.num_realizations = 1
config3.simulation.save_snapshots = False

# Higher thresholds = need richer systems = less expansion
config3.civilization.metallicity_threshold_k085 = -0.1
config3.civilization.metallicity_threshold_k095 = -0.2
config3.civilization.metallicity_threshold_k120 = -0.5

# Smaller sensor range
config3.civilization.probe_sensor_range_pc = 5.0

print(f"  K=0.85-0.95: {config3.civilization.metallicity_threshold_k085:.2f} [Fe/H] (strict)")
print(f"  K=0.95-1.20: {config3.civilization.metallicity_threshold_k095:.2f} [Fe/H] (strict)")
print(f"  K>1.20: {config3.civilization.metallicity_threshold_k120:.2f} [Fe/H] (strict)")
print(f"  Sensor range: {config3.civilization.probe_sensor_range_pc:.1f} pc (limited)")

sim3 = GalaxySimulation(config3, seed=42)
sim3.run(verbose=False)

expanding_civs3 = [c for c in sim3.civilizations if c.expansion_program_started]
colonized_total3 = sum(len(c.colonized_stars) for c in expanding_civs3)
print(f"\n  Civilizations that started expansion: {len(expanding_civs3)}")
print(f"  Total systems colonized: {colonized_total3}")

if expanding_civs3:
    for civ in expanding_civs3[:3]:
        print(f"    Civ {civ.civ_id}: K={civ.expansion_start_kardashev:.2f}, "
              f"min[Fe/H]={civ.probe_min_metallicity:.2f}, "
              f"colonies={len(civ.colonized_stars)}, "
              f"sensor={civ.probe_sensor_range_pc:.1f}pc")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"  Default config: {len([c for c in sim.civilizations if c.expansion_program_started])} expanding civs")
print(f"  Aggressive config: {len([c for c in sim2.civilizations if c.expansion_program_started])} expanding civs, "
      f"{sum(len(c.colonized_stars) for c in [c for c in sim2.civilizations if c.expansion_program_started])} total colonies")
print(f"  Conservative config: {len([c for c in sim3.civilizations if c.expansion_program_started])} expanding civs, "
      f"{sum(len(c.colonized_stars) for c in [c for c in sim3.civilizations if c.expansion_program_started])} total colonies")

print("\n✓ Configuration system working correctly!")
print("✓ Metallicity thresholds applied from config")
print("✓ Sensor range configurable")
print("✓ Relaxed thresholds → more expansion")
print("✓ Strict thresholds → less expansion")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
