"""
Enhanced simulation example with Kardashev scale tracking and comprehensive visualizations.
"""

from great_silence import GalaxySimulation, SimulationConfig, configure_m1_max_threading
from great_silence.visualization import GalaxyVisualizer, TimelineAnimator

# Configure optimal threading for M1 Max
configure_m1_max_threading()
print()


def main():
    """Run enhanced simulation with full visualizations."""
    # Create configuration
    config = SimulationConfig()

    # Galaxy parameters
    config.galaxy.total_stars = 100_000  # Reduced for quick test

    # Simulation parameters
    config.simulation.simulation_duration_gyr = 10.0  # 10 billion years
    config.simulation.time_step_myr = 1.0  # 1 million year steps (smaller for accuracy)
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 100.0

    # Drake equation parameters (using moderate preset)
    config.civilization.fraction_develop_life = 0.1
    config.civilization.fraction_develop_intelligence = 0.01
    config.civilization.fraction_develop_technology = 0.1

    # Civilization parameters - LONGER LIFETIMES
    config.civilization.mean_civilization_lifetime_myr = 100.0  # 100 million years
    config.civilization.self_destruction_probability_per_myr = 0.01  # 1% per Myr

    # Kardashev scale parameters (with randomness!)
    config.civilization.initial_kardashev_scale_mean = 0.7  # Mean starting level
    config.civilization.initial_kardashev_scale_stddev = 0.1  # Variation in starting tech
    config.civilization.kardashev_advancement_rate_mean = 0.01  # Mean advancement rate
    config.civilization.kardashev_advancement_rate_stddev = 0.005  # Variation in rates
    config.civilization.kardashev_stagnation_probability_per_myr = 0.05  # 5% chance of stagnation
    config.civilization.kardashev_breakthrough_probability_per_myr = 0.02  # 2% chance of breakthrough
    config.civilization.kardashev_breakthrough_multiplier = 3.0  # 3x faster during breakthrough
    config.civilization.kardashev_max_scale = 3.0  # Type III maximum

    print("=" * 70)
    print("GalaticBot: Enhanced Galactic Civilization Simulator")
    print("=" * 70)
    print(f"\nSimulation parameters:")
    print(f"  Galaxy stars: {config.galaxy.total_stars:,}")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Time step: {config.simulation.time_step_myr} Myr")
    print(f"\nDrake parameters:")
    print(f"  f_life = {config.civilization.fraction_develop_life}")
    print(f"  f_intel = {config.civilization.fraction_develop_intelligence}")
    print(f"  f_tech = {config.civilization.fraction_develop_technology}")
    print(f"\nKardashev scale (with stochastic advancement):")
    print(f"  Initial: {config.civilization.initial_kardashev_scale_mean} ± {config.civilization.initial_kardashev_scale_stddev}")
    print(f"  Advancement rate: {config.civilization.kardashev_advancement_rate_mean} ± {config.civilization.kardashev_advancement_rate_stddev} per Myr")
    print(f"  Stagnation chance: {config.civilization.kardashev_stagnation_probability_per_myr*100:.1f}% per Myr")
    print(f"  Breakthrough chance: {config.civilization.kardashev_breakthrough_probability_per_myr*100:.1f}% per Myr (x{config.civilization.kardashev_breakthrough_multiplier} speed)")
    print(f"  Maximum: {config.civilization.kardashev_max_scale}")
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
    print(f"  Total colonized systems: {stats['total_colonized_systems']}")
    print(f"  Final time: {stats['current_time_gyr']:.2f} Gyr")

    # Print extinction causes
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
        print(f"    Min: {min(all_scales):.2f}")
        if active_scales:
            print(f"  Active civilizations:")
            print(f"    Mean: {sum(active_scales)/len(active_scales):.2f}")
            print(f"    Max: {max(active_scales):.2f}")
            print(f"    Min: {min(active_scales):.2f}")
    print()

    # Generate visualizations
    print("Generating enhanced visualizations...")
    viz = GalaxyVisualizer()
    timeline_viz = TimelineAnimator()

    # 1. Civilization evolution (Kardashev scale + status)
    if sim.civilizations and sim.galaxy.positions is not None:
        viz.plot_civilization_evolution(
            sim.galaxy.positions,
            sim.civilizations,
            save_path="output/civilization_evolution.png"
        )
        print("  Saved: output/civilization_evolution.png")

    # 2. Extinction causes pie chart
    if extinction_causes:
        timeline_viz.plot_extinction_causes(
            extinction_causes,
            save_path="output/extinction_causes.png"
        )
        print("  Saved: output/extinction_causes.png")

    # 3. Kardashev scale progression
    if sim.civilizations:
        timeline_viz.plot_kardashev_progression(
            sim.civilizations,
            config.simulation.simulation_duration_gyr * 1000.0,  # Convert to Myr
            save_path="output/kardashev_progression.png"
        )
        print("  Saved: output/kardashev_progression.png")

    # 4. Galaxy structure
    if sim.galaxy.positions is not None:
        viz.plot_galaxy_structure(
            sim.galaxy.positions,
            save_path="output/galaxy_structure.png"
        )
        print("  Saved: output/galaxy_structure.png")

    print("\nSimulation complete!")
    print("\nGenerated visualizations:")
    print("  - civilization_evolution.png: Active civs (by Kardashev scale) + all civs (active/extinct)")
    print("  - extinction_causes.png: Pie chart showing how civilizations died")
    print("  - kardashev_progression.png: Distribution of tech levels and lifetime correlation")
    print("  - galaxy_structure.png: 3D galaxy structure")


if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    main()
