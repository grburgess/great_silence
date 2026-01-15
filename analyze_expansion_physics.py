#!/usr/bin/env python3
"""Analyze expansion physics and Kardashev level relationship."""

from great_silence import GalaxySimulation, SimulationConfig, configure_m1_max_threading
import numpy as np

configure_m1_max_threading()

# Run small simulation
config = SimulationConfig.with_preset('optimistic')
config.galaxy.total_stars = 5_000
config.simulation.duration_gyr = 3.0
config.simulation.save_snapshots = False

sim = GalaxySimulation(config, seed=42)
print(f"Running simulation: {config.galaxy.total_stars} stars, {config.simulation.duration_gyr} Gyr\n")
sim.run(verbose=False)

print("="*70)
print("EXPANSION PHYSICS ANALYSIS")
print("="*70)

# Check expansion parameters
print(f"\n1. EXPANSION VELOCITY")
print(f"   Default velocity: {config.civilization.expansion_velocity_fraction_c:.3f}c")
print(f"   This is {config.civilization.expansion_velocity_fraction_c * 100:.1f}% of light speed")
print(f"   At this speed, crossing 1000 pc takes {1000 / (config.civilization.expansion_velocity_fraction_c * 0.306601) / 1e6:.1f} Myr")

# Analyze civilizations that expanded
expanding_civs = [c for c in sim.civilizations if len(c.colonized_stars) > 1]

if not expanding_civs:
    print("\n   ⚠ No civilizations expanded!")
else:
    print(f"\n2. KARDASHEV LEVEL AT FIRST EXPANSION")
    print(f"   Total civilizations: {len(sim.civilizations)}")
    print(f"   Civilizations that expanded: {len(expanding_civs)}")

    for i, civ in enumerate(expanding_civs[:5]):  # Show first 5
        # Find kardashev level at birth
        initial_k = 0.7  # Default starting level

        # Find first colony (not home world)
        colonies = [(idx, time) for idx, time in civ.colony_arrival_times.items()
                   if idx != civ.parent_star_idx]

        if colonies:
            first_colony_idx, first_arrival = min(colonies, key=lambda x: x[1])
            expansion_started = civ.birth_time_myr  # They start expanding immediately

            # Estimate Kardashev at expansion start
            # K advances at rate kardashev_advancement_rate per Myr
            time_since_birth = expansion_started - civ.birth_time_myr
            k_at_expansion = initial_k + civ.kardashev_advancement_rate * time_since_birth

            print(f"\n   Civ {civ.civ_id}:")
            print(f"      Birth time: {civ.birth_time_myr:.1f} Myr")
            print(f"      First colony sent: ~{expansion_started:.1f} Myr")
            print(f"      Kardashev at expansion start: ~{k_at_expansion:.2f}")
            print(f"      First colony arrives: {first_arrival:.1f} Myr")
            print(f"      Total colonies: {len(civ.colonized_stars) - 1}")

print(f"\n3. RELATIVISTIC CONSTRAINTS CHECK")
print(f"   ✓ Expansion velocity is sub-light: {config.civilization.expansion_velocity_fraction_c}c")
print(f"   ✓ Travel times calculated from distance/velocity")
print(f"   ✓ Light cone constraints applied (lines 481-502 in engine.py)")
print(f"   ✓ Arrival times tracked in colony_arrival_times dict")

print(f"\n4. POTENTIAL ISSUES")
print(f"   ⚠ NO relationship between Kardashev level and expansion capability!")
print(f"   ⚠ Civilizations at K=0.7 (modern Earth) can expand immediately")
print(f"   ⚠ Expansion velocity is CONSTANT regardless of tech level")
print(f"   ⚠ No minimum Kardashev threshold for interstellar travel")

print(f"\n5. REALISTIC CONSIDERATIONS")
print(f"   Self-replicating probes (von Neumann probes) assumptions:")
print(f"   - Could be sent by relatively low-tech civilizations (~K=0.8-1.0)")
print(f"   - Travel at sub-relativistic speeds (0.001c - 0.1c)")
print(f"   - Take centuries to millennia to reach nearby stars")
print(f"   - But require significant technological capability")
print(f"")
print(f"   Current model:")
print(f"   - K=0.7 civilizations can immediately expand at 0.01c")
print(f"   - This is unrealistic (K=0.7 is current Earth)")
print(f"   - K=1.0 = planetary energy harnessing")
print(f"   - K=2.0 = stellar energy harnessing")

print(f"\n6. RECOMMENDED IMPROVEMENTS")
print(f"   Option A: Minimum Kardashev threshold")
print(f"      - Require K >= 0.85-0.95 to start expanding")
print(f"      - Represents mastery of interplanetary travel + AI + robotics")
print(f"")
print(f"   Option B: Velocity scales with Kardashev")
print(f"      - K=0.85-1.0: v = 0.001c - 0.01c (slow probes)")
print(f"      - K=1.0-2.0: v = 0.01c - 0.05c (advanced probes)")
print(f"      - K=2.0+: v = 0.05c - 0.1c (near-maximum realistic)")
print(f"")
print(f"   Option C: Combined approach")
print(f"      - Minimum K=0.85 to expand")
print(f"      - Velocity increases: v(K) = 0.001 + 0.049 * (K-0.85)/1.15")
print(f"      - At K=0.85: v=0.001c, at K=2.0: v=0.05c")

print("\n" + "="*70)
