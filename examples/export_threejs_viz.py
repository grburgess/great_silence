"""Example script demonstrating Three.js visualization export."""

from pathlib import Path
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs import export_html, ThreeJSConfig


def main():
    """Run simulation and export Three.js visualization."""
    print("=" * 80)
    print("GALACTIC CIVILIZATION THREE.JS VISUALIZATION")
    print("=" * 80)
    print()

    # Create configuration
    config = SimulationConfig()

    # Galaxy parameters
    config.galaxy.total_stars = 15_000
    config.galaxy.include_bulge = True
    config.galaxy.bulge_fraction = 0.2
    config.galaxy.scale_length_kpc = 3.5
    config.galaxy.disk_radius_kpc = 15.0

    # Optimistic Drake equation for visible civilizations
    config.civilization.fraction_develop_life = 0.5
    config.civilization.fraction_develop_intelligence = 0.1
    config.civilization.fraction_develop_technology = 0.5

    # Crisis-based extinction
    config.civilization.self_destruction_model_type = "kardashev_dependent"
    config.civilization.baseline_self_destruction_rate = 0.01
    config.civilization.crisis_nuclear_age_amplitude = 0.15
    config.civilization.crisis_planetary_unification_amplitude = 0.12
    config.civilization.crisis_ai_transition_amplitude = 0.20
    config.civilization.crisis_interplanetary_amplitude = 0.10

    # Disable old age for clearer crisis visualization
    config.civilization.mean_civilization_lifetime_myr = 1000.0

    # Kardashev advancement
    config.civilization.initial_kardashev_scale_mean = 0.7
    config.civilization.kardashev_advancement_rate_mean = 0.02

    # Simulation duration
    config.simulation.simulation_duration_gyr = 2.0  # 2 Gyr
    config.simulation.time_step_myr = 10.0  # 10 Myr
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 50.0  # Every 50 Myr

    # Enable hazards
    config.astrophysics.supernova_rate_per_galaxy_gyr = 2.0
    config.astrophysics.grb_rate_per_galaxy_gyr = 1.0

    print(f"Configuration:")
    print(f"  Galaxy: {config.galaxy.total_stars:,} stars")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Snapshots: {int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.snapshot_interval_myr)}")
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
    
    total_civs = len(sim.civilizations)
    active_civs = sum(1 for c in sim.civilizations if c.is_active)
    
    print(f"\nSimulation complete!")
    print(f"  Total civilizations: {total_civs}")
    print(f"  Currently active: {active_civs}")
    print(f"  Extinct: {total_civs - active_civs}")
    print(f"  Snapshots captured: {len(sim.snapshots)}")

    # Export visualization
    print("\n" + "=" * 80)
    print("EXPORTING THREE.JS VISUALIZATION")
    print("=" * 80)
    
    # Create Three.js config
    viz_config = ThreeJSConfig()
    
    # Camera presets
    viz_config.camera_presets = [
        {
            "name": "Galaxy Top",
            "position": [0.0, 0.0, 40.0],
            "target": [0.0, 0.0, 0.0],
            "duration": 2.0,
        },
        {
            "name": "Galaxy Edge",
            "position": [30.0, 0.0, 0.0],
            "target": [0.0, 0.0, 0.0],
            "duration": 2.0,
        },
        {
            "name": "Galaxy Angled",
            "position": [25.0, 25.0, 15.0],
            "target": [0.0, 0.0, 0.0],
            "duration": 2.5,
        },
    ]
    
    # LOD settings
    viz_config.lod_near_distance = 5.0
    viz_config.lod_far_distance = 15.0
    
    output_path = Path("examples/galactic_civilization_threejs.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    export_html(
        sim,
        output_path,
        config=viz_config,
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
    print("OPENING VISUALIZATION IN BROWSER")
    print("=" * 80)
    
    import subprocess
    import sys
    if sys.platform == 'darwin':
        subprocess.run(['open', str(output_path)])
    elif sys.platform == 'linux':
        subprocess.run(['xdg-open', str(output_path)])
    elif sys.platform == 'win32':
        subprocess.run(['start', str(output_path)])
    
    print("\n✓ Complete!")
    print("\nVisualization features:")
    print("  - Star particle system with custom shaders")
    print("  - Civilization sprites colored by Kardashev scale")
    print("  - Probe trails")
    print("  - Hazard markers (supernovae, GRBs)")
    print("  - Timeline scrubbing (0 to " + f"{config.simulation.simulation_duration_gyr} Gyr)")
    print("  - Playback controls (play/pause, step, reset)")
    print("  - Speed control (0.1x - 10x)")
    print("  - Layer toggles (stars, civilizations, probes, hazards)")
    print("  - Downsample slider (when >20 civs)")
    print("  - Camera presets (Top, Edge, Angled)")
    print("  - Auto-rotate mode")
    print("  - Keyboard controls (WASD, arrows, +/-, Space)")
    print("  - Info panel on hover over civilizations")
    print("  - Mini-map")
    print("  - Export frame button")
    print("  - Post-processing toggle (bloom, film grain, vignette)")
    print("  - Level of Detail system")


if __name__ == "__main__":
    main()
