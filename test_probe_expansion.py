#!/usr/bin/env python3
"""Test self-replicating probe expansion model."""

from great_silence import GalaxySimulation, SimulationConfig, configure_m1_max_threading
import numpy as np

configure_m1_max_threading()

print("="*70)
print("SELF-REPLICATING PROBE EXPANSION TEST")
print("="*70)

# Small test simulation
config = SimulationConfig.with_preset('optimistic')
config.galaxy.total_stars = 5_000
config.simulation.duration_gyr = 0.5  # Short duration
config.simulation.time_step_myr = 0.1  # Fine timesteps to see probe dynamics
config.simulation.num_realizations = 1
config.simulation.save_snapshots = False

# Enable expansion
config.civilization.expansion_enabled = True
config.civilization.min_kardashev_for_expansion = 0.85

# Start civs near threshold for quick testing
config.civilization.initial_kardashev_scale_mean = 0.80
config.civilization.initial_kardashev_scale_stddev = 0.05
config.civilization.kardashev_advancement_rate_mean = 0.05  # Fast advancement

sim = GalaxySimulation(config, seed=42)
print(f"\nRunning: {config.galaxy.total_stars} stars, {config.simulation.duration_gyr} Gyr\n")
sim.run(verbose=True)

print("\n" + "="*70)
print("EXPANSION ANALYSIS")
print("="*70)

# Analyze civilizations
civs = sim.civilizations
expanding_civs = [c for c in civs if c.expansion_program_started]
non_expanding = [c for c in civs if not c.expansion_program_started and c.is_active]

print(f"\nTotal civilizations: {len(civs)}")
print(f"Started expansion: {len(expanding_civs)}")
print(f"Did not expand: {len(non_expanding)}")

# Check non-expanding civs stayed below threshold
if non_expanding:
    max_k = max(c.kardashev_scale for c in non_expanding)
    print(f"  Max Kardashev of non-expanding: {max_k:.2f}")
    if max_k < 0.85:
        print(f"  ✓ Correctly below threshold (K < 0.85)")
    else:
        print(f"  ✗ ERROR: Some civs above K=0.85 didn't expand!")

# Analyze expanding civilizations
if expanding_civs:
    print(f"\n{'='*70}")
    print("EXPANDING CIVILIZATIONS DETAIL")
    print("="*70)

    for i, civ in enumerate(expanding_civs[:3]):  # Show first 3
        print(f"\nCiv {civ.civ_id}:")
        print(f"  Birth time: {civ.birth_time_myr:.2f} Myr")
        print(f"  Expansion start Kardashev: {civ.expansion_start_kardashev:.3f}")
        print(f"  Current Kardashev: {civ.kardashev_scale:.3f}")

        print(f"\n  Probe Design (locked at launch):")
        print(f"    Velocity: {civ.probe_velocity_c:.4f}c ({civ.probe_velocity_c*100:.2f}% light speed)")
        print(f"    Per-hop range: {civ.probe_per_hop_range_pc:.1f} pc")
        print(f"    Offspring per probe: {civ.probe_offspring_count}")
        print(f"    Replication delay: {civ.probe_replication_delay_yr:.1f} years")

        print(f"\n  Expansion Progress:")
        print(f"    Total probes launched: {len(civ.active_probes)}")
        arrived = [p for p in civ.active_probes if p.has_arrived]
        replicated = [p for p in civ.active_probes if p.has_replicated]
        print(f"    Probes arrived: {len(arrived)}")
        print(f"    Probes replicated: {len(replicated)}")
        print(f"    Colonized stars: {len(civ.colonized_stars)} (including home)")

        # Probe generation breakdown
        if civ.active_probes:
            generations = [p.generation for p in civ.active_probes]
            max_gen = max(generations)
            print(f"    Max generation: {max_gen}")
            for gen in range(max_gen + 1):
                count = sum(1 for g in generations if g == gen)
                print(f"      Gen {gen}: {count} probes")

        # Travel time analysis
        if arrived:
            travel_times_myr = [
                (p.arrival_time_myr - p.launch_time_myr)
                for p in arrived
            ]
            avg_travel = np.mean(travel_times_myr)
            print(f"\n  Travel Statistics:")
            print(f"    Avg travel time: {avg_travel:.3f} Myr ({avg_travel*1e6:.0f} years)")
            print(f"    Min: {min(travel_times_myr):.3f} Myr")
            print(f"    Max: {max(travel_times_myr):.3f} Myr")

print("\n" + "="*70)
print("PHYSICS VALIDATION")
print("="*70)

if expanding_civs:
    # Check probe velocities match Kardashev level
    from great_silence.civilization.probe_design import probe_velocity_from_kardashev

    print("\n1. VELOCITY CONSISTENCY")
    for civ in expanding_civs[:3]:
        expected_v = probe_velocity_from_kardashev(civ.expansion_start_kardashev)
        actual_v = civ.probe_velocity_c
        match = "✓" if abs(expected_v - actual_v) < 1e-6 else "✗"
        print(f"  Civ {civ.civ_id}: K={civ.expansion_start_kardashev:.2f} → "
              f"v={actual_v:.4f}c (expected {expected_v:.4f}c) {match}")

    print("\n2. BRANCHING STRUCTURE")
    for civ in expanding_civs[:3]:
        if len(civ.active_probes) > 0:
            # Check if we have branching (multiple generations)
            generations = set(p.generation for p in civ.active_probes)
            if len(generations) > 1:
                print(f"  Civ {civ.civ_id}: ✓ Branching tree ({len(generations)} generations)")
            else:
                print(f"  Civ {civ.civ_id}: Single generation (may need more time)")

    print("\n3. COLONIZATION PATTERN")
    for civ in expanding_civs[:3]:
        if len(civ.colonized_stars) > 1:
            home_pos = sim.galaxy.positions[civ.parent_star_idx]
            colony_positions = sim.galaxy.positions[civ.colonized_stars]

            # Calculate distances from home
            distances_kpc = np.linalg.norm(colony_positions - home_pos, axis=1)
            distances_pc = distances_kpc * 1000.0

            avg_dist = np.mean(distances_pc)
            max_dist = np.max(distances_pc)

            print(f"  Civ {civ.civ_id}:")
            print(f"    Avg colony distance: {avg_dist:.1f} pc")
            print(f"    Max colony distance: {max_dist:.1f} pc")
            print(f"    Per-hop range: {civ.probe_per_hop_range_pc:.1f} pc")

            # Check if pattern is sparse (not dense sphere)
            expected_dense_count = int((max_dist / 10) ** 3 * 0.1)  # Rough estimate
            actual_count = len(civ.colonized_stars)
            if actual_count < expected_dense_count * 0.1:
                print(f"    ✓ Sparse branching pattern ({actual_count} << {expected_dense_count})")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
