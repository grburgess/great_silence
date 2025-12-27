"""
Basic example of running a galactic civilization simulation.
"""

from great_silence import GalaxySimulation, SimulationConfig, configure_m1_max_threading
from great_silence.visualization import GalaxyVisualizer

# Configure optimal threading for M1 Max
configure_m1_max_threading()
print()


def main():
    """Run a basic simulation."""
    # Create configuration with custom parameters
    config = SimulationConfig()

    # Adjust parameters for quick test
    config.galaxy.total_stars = 100_000  # Reduced for quick test
    config.simulation.simulation_duration_gyr = 10.0  # 10 billion years
    config.simulation.time_step_myr = 1.0  # 1 million year steps (smaller for accuracy)
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 100.0

    # Drake equation parameters
    config.civilization.fraction_develop_life = 0.1
    config.civilization.fraction_develop_intelligence = 0.01
    config.civilization.fraction_develop_technology = 0.1

    # Civilization lifetime - LONGER so they don't all die immediately!
    config.civilization.mean_civilization_lifetime_myr = 100.0  # 100 million years
    config.civilization.self_destruction_probability_per_myr = 0.01  # 1% per Myr

    print("=" * 70)
    print("GalaticBot: Galactic Civilization Simulator")
    print("=" * 70)
    print(f"\nSimulation parameters:")
    print(f"  Galaxy stars: {config.galaxy.total_stars:,}")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Time step: {config.simulation.time_step_myr} Myr")
    print(f"  Drake parameters:")
    print(f"    f_life = {config.civilization.fraction_develop_life}")
    print(f"    f_intel = {config.civilization.fraction_develop_intelligence}")
    print(f"    f_tech = {config.civilization.fraction_develop_technology}")
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
    print()

    # Visualize results
    print("Generating visualizations...")
    viz = GalaxyVisualizer()

    # Plot galaxy structure
    if sim.galaxy.positions is not None:
        viz.plot_galaxy_structure(
            sim.galaxy.positions,
            save_path="output/galaxy_structure.png"
        )
        print("  Saved: output/galaxy_structure.png")

    # Plot civilization distribution
    if sim.civilizations:
        civ_indices = [c.parent_star_idx for c in sim.civilizations if c.is_active]
        if civ_indices and sim.galaxy.positions is not None:
            viz.plot_civilization_distribution(
                sim.galaxy.positions,
                civ_indices,
                save_path="output/civilization_distribution.png"
            )
            print("  Saved: output/civilization_distribution.png")

    print("\nSimulation complete!")


if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    main()
