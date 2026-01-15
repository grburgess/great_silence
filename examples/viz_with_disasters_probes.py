"""Example visualization with disasters and probe expansion."""

from pathlib import Path
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs import export_html


def main():
    """Run simulation with disasters and probes, then export visualization."""
    print("=" * 80)
    print("GALACTIC SIMULATION WITH DISASTERS AND PROBES")
    print("=" * 80)
    print()

    config = SimulationConfig()

    # Galaxy parameters - moderate size for performance
    config.galaxy.total_stars = 15_000
    config.galaxy.include_bulge = True
    config.galaxy.bulge_fraction = 0.15
    config.galaxy.scale_length_kpc = 3.5
    config.galaxy.disk_radius_kpc = 15.0

    # Moderate civilization emergence (enough to see activity)
    config.civilization.fraction_develop_life = 0.5
    config.civilization.fraction_develop_intelligence = 0.1
    config.civilization.fraction_develop_technology = 0.3
    
    # Very long-lived civilizations
    config.civilization.mean_civilization_lifetime_myr = 2000.0
    config.civilization.lifetime_stddev_myr = 500.0

    # Kardashev - start higher and advance quickly
    config.civilization.initial_kardashev_scale_mean = 0.82  # Already close to expansion
    config.civilization.initial_kardashev_scale_stddev = 0.08
    config.civilization.kardashev_advancement_rate_mean = 0.1  # Fast advancement
    config.civilization.kardashev_advancement_rate_stddev = 0.02

    # ENABLE PROBE EXPANSION - lower threshold
    config.civilization.expansion_enabled = True
    config.civilization.min_kardashev_for_expansion = 0.85
    config.civilization.max_colonies_per_civilization = 500

    # VERY LOW self-destruction rates to let civilizations expand
    config.civilization.self_destruction_model_type = "flat"
    config.civilization.self_destruction_probability_per_myr = 0.001  # 0.1% per Myr
    
    # Disable personality evolution to avoid bug in war resolution
    config.civilization.personality_evolution_enabled = False

    # ASTROPHYSICAL HAZARDS - increased rates for visibility
    config.astrophysics.supernova_rate_per_galaxy_gyr = 10.0
    config.astrophysics.supernova_lethal_range_pc = 50.0
    config.astrophysics.grb_rate_per_galaxy_gyr = 5.0
    config.astrophysics.grb_lethal_range_kpc = 5.0

    # Simulation parameters - balanced for performance
    config.simulation.simulation_duration_gyr = 1.0  # Shorter to finish faster
    config.simulation.time_step_myr = 5.0
    config.simulation.adaptive_timestepping = True
    config.simulation.min_timestep_myr = 0.1
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 25.0

    print("Configuration:")
    print(f"  Galaxy: {config.galaxy.total_stars:,} stars")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Expansion enabled: {config.civilization.expansion_enabled}")
    print(f"  Min Kardashev for expansion: {config.civilization.min_kardashev_for_expansion}")
    print(f"  Supernova rate: {config.astrophysics.supernova_rate_per_galaxy_gyr}/Gyr")
    print(f"  GRB rate: {config.astrophysics.grb_rate_per_galaxy_gyr}/Gyr")
    print()

    # Run simulation
    print("=" * 80)
    print("RUNNING SIMULATION")
    print("=" * 80)

    sim = GalaxySimulation(config, seed=42)
    sim.initialize()

    print(f"\nGalaxy initialized:")
    print(f"  Habitable stars: {len(sim.habitable_star_indices):,}")

    print("\nSimulating galactic history...")
    sim.run()

    # Collect statistics
    total_civs = len(sim.civilizations)
    active_civs = sum(1 for c in sim.civilizations if c.is_active)
    expanding_civs = sum(1 for c in sim.civilizations if hasattr(c, 'expansion_program_started') and c.expansion_program_started)
    total_hazards = len(sim.hazard_events) if hasattr(sim, 'hazard_events') else 0
    
    # Count probes
    total_active_probes = 0
    total_archived_probes = 0
    if hasattr(sim, 'active_probes_by_civ'):
        for probes in sim.active_probes_by_civ.values():
            total_active_probes += len(probes)
    if hasattr(sim, 'archived_probes_by_civ'):
        for probes in sim.archived_probes_by_civ.values():
            total_archived_probes += len(probes)

    # Count total colonized stars
    total_colonies = sum(len(c.colonized_stars) for c in sim.civilizations)

    # Sample Kardashev levels
    kardashev_levels = [c.kardashev_scale for c in sim.civilizations[:10]]
    
    print(f"\nSimulation complete!")
    print(f"  Total civilizations emerged: {total_civs}")
    print(f"  Currently active: {active_civs}")
    print(f"  Extinct: {total_civs - active_civs}")
    print(f"  Started expansion: {expanding_civs}")
    print(f"  Total colonies established: {total_colonies}")
    print(f"  Active probes in flight: {total_active_probes}")
    print(f"  Archived probes (arrived): {total_archived_probes}")
    print(f"  Hazard events: {total_hazards}")
    print(f"  Snapshots captured: {len(sim.snapshots)}")
    if kardashev_levels:
        print(f"  Sample K-levels: {[f'{k:.2f}' for k in kardashev_levels]}")

    # Export visualization
    print("\n" + "=" * 80)
    print("EXPORTING THREE.JS VISUALIZATION")
    print("=" * 80)

    output_path = Path("examples/galaxy_disasters_probes.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    export_html(
        sim,
        output_path,
        animated=True,
        show_trajectories=True,
        show_spheres=True,
        show_hazards=True,
        compress=False
    )

    print(f"\n✓ Export complete!")
    print(f"  Saved to: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 80)
    print("VIEW VISUALIZATION")
    print("=" * 80)
    print(f"\n  Start server: python -m http.server 8080")
    print(f"  Open: http://localhost:8080/examples/galaxy_disasters_probes.html")
    print("\n✓ Complete!")


if __name__ == "__main__":
    main()
