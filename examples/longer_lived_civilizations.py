"""
Example with longer-lived civilizations that don't all self-destruct immediately.
"""

from great_silence import GalaxySimulation, SimulationConfig, configure_m1_max_threading
from great_silence.visualization import GalaxyVisualizer, TimelineAnimator

# Configure optimal threading for M1 Max
configure_m1_max_threading()
print()


def main():
    """Run simulation with properly scaled parameters."""
    config = SimulationConfig()

    # Galaxy parameters
    config.galaxy.total_stars = 100_000

    # Simulation parameters - SMALLER TIMESTEP
    config.simulation.simulation_duration_gyr = 10.0
    config.simulation.time_step_myr = 1.0  # 1 Myr instead of 10 Myr
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 100.0

    # Drake equation parameters
    config.civilization.fraction_develop_life = 0.1
    config.civilization.fraction_develop_intelligence = 0.01
    config.civilization.fraction_develop_technology = 0.1

    # Civilization lifetime - MUCH LONGER
    config.civilization.mean_civilization_lifetime_myr = 100.0  # 100 Myr (not 1!)

    # Self-destruction - LOWER RATE
    config.civilization.self_destruction_probability_per_myr = 0.01  # 1% per Myr (not 10%)

    # Kardashev scale parameters
    config.civilization.initial_kardashev_scale_mean = 0.7
    config.civilization.initial_kardashev_scale_stddev = 0.1
    config.civilization.kardashev_advancement_rate_mean = 0.01
    config.civilization.kardashev_advancement_rate_stddev = 0.005
    config.civilization.kardashev_stagnation_probability_per_myr = 0.05
    config.civilization.kardashev_breakthrough_probability_per_myr = 0.02
    config.civilization.kardashev_breakthrough_multiplier = 3.0
    config.civilization.kardashev_max_scale = 3.0

    print("=" * 70)
    print("GalaticBot: Longer-Lived Civilizations")
    print("=" * 70)
    print(f"\nSimulation parameters:")
    print(f"  Galaxy stars: {config.galaxy.total_stars:,}")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Time step: {config.simulation.time_step_myr} Myr (smaller for accuracy)")
    print(f"\nCivilization parameters:")
    print(f"  Mean lifetime: {config.civilization.mean_civilization_lifetime_myr} Myr")
    print(f"  Self-destruction: {config.civilization.self_destruction_probability_per_myr*100:.1f}% per Myr")
    print(f"    → {config.civilization.self_destruction_probability_per_myr * config.simulation.time_step_myr * 100:.1f}% per timestep")

    # Calculate survival probability
    import numpy as np
    tau = config.civilization.mean_civilization_lifetime_myr
    dt = config.simulation.time_step_myr
    p_age_death = 1.0 - np.exp(-dt / tau)
    p_self_destruct = config.civilization.self_destruction_probability_per_myr * dt
    p_survive = (1 - p_age_death) * (1 - p_self_destruct)

    print(f"  Age-based death: {p_age_death*100:.2f}% per timestep")
    print(f"  Survival chance: {p_survive*100:.1f}% per timestep")
    print(f"  Expected lifetime: ~{-tau * np.log(p_survive):.1f} Myr")
    print()

    # Create and run simulation
    sim = GalaxySimulation(config, seed=42)
    sim.run(verbose=True)

    # Print results
    stats = sim.get_statistics()
    print(f"\n" + "=" * 70)
    print("Simulation Results:")
    print("=" * 70)
    print(f"  Total civilizations emerged: {stats['total_civilizations']}")
    print(f"  Active civilizations: {stats['active_civilizations']}")
    print(f"  Extinct civilizations: {stats['extinct_civilizations']}")
    print(f"  Survival rate: {stats['active_civilizations']/stats['total_civilizations']*100:.1f}%")
    print(f"  Total colonized systems: {stats['total_colonized_systems']}")
    print(f"  Final time: {stats['current_time_gyr']:.2f} Gyr")

    # Print extinction causes
    if stats['extinct_civilizations'] > 0:
        print(f"\nExtinction causes:")
        extinction_causes = {}
        for civ in sim.civilizations:
            if not civ.is_active and civ.death_cause:
                extinction_causes[civ.death_cause] = extinction_causes.get(civ.death_cause, 0) + 1
        for cause, count in sorted(extinction_causes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cause}: {count} ({100*count/stats['extinct_civilizations']:.1f}%)")

    # Print Kardashev scale statistics
    if sim.civilizations:
        active_civs = [c for c in sim.civilizations if c.is_active]
        all_scales = [c.kardashev_scale for c in sim.civilizations]
        active_scales = [c.kardashev_scale for c in active_civs] if active_civs else []

        print(f"\nKardashev scale statistics:")
        print(f"  All civilizations:")
        print(f"    Mean: {sum(all_scales)/len(all_scales):.2f}")
        print(f"    Max: {max(all_scales):.2f}")
        if active_scales:
            print(f"  Active civilizations:")
            print(f"    Mean: {sum(active_scales)/len(active_scales):.2f}")
            print(f"    Max: {max(active_scales):.2f}")
            print(f"    Min: {min(active_scales):.2f}")
    print()

    # Generate visualizations
    print("Generating visualizations...")
    viz = GalaxyVisualizer()
    timeline_viz = TimelineAnimator()

    if sim.civilizations and sim.galaxy.positions is not None:
        viz.plot_civilization_evolution(
            sim.galaxy.positions,
            sim.civilizations,
            save_path="output/longer_lived_evolution.png"
        )
        print("  Saved: output/longer_lived_evolution.png")

    if stats['extinct_civilizations'] > 0:
        extinction_causes = {}
        for civ in sim.civilizations:
            if not civ.is_active and civ.death_cause:
                extinction_causes[civ.death_cause] = extinction_causes.get(civ.death_cause, 0) + 1

        timeline_viz.plot_extinction_causes(
            extinction_causes,
            save_path="output/longer_lived_extinction_causes.png"
        )
        print("  Saved: output/longer_lived_extinction_causes.png")

    if sim.civilizations:
        timeline_viz.plot_kardashev_progression(
            sim.civilizations,
            config.simulation.simulation_duration_gyr * 1000.0,
            save_path="output/longer_lived_kardashev.png"
        )
        print("  Saved: output/longer_lived_kardashev.png")

    print("\nSimulation complete!")
    print(f"\nNow you should see active civilizations at the end!")


if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    main()
