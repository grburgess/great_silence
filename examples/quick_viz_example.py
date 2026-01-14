"""Quick example to generate and view Three.js visualization."""

from pathlib import Path
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs import export_html


def create_example_viz():
    """Create quick example visualization."""
    print("=" * 80)
    print("QUICK THREE.JS VISUALIZATION EXAMPLE")
    print("=" * 80)
    print()

    config = SimulationConfig()

    config.galaxy.total_stars = 8_000
    config.galaxy.include_bulge = True
    config.galaxy.bulge_fraction = 0.2
    config.galaxy.scale_length_kpc = 3.5
    config.galaxy.disk_radius_kpc = 15.0

    config.civilization.fraction_develop_life = 0.8
    config.civilization.fraction_develop_intelligence = 0.15
    config.civilization.fraction_develop_technology = 0.6

    config.civilization.mean_civilization_lifetime_myr = 2000.0
    config.civilization.initial_kardashev_scale_mean = 0.7
    config.civilization.kardashev_advancement_rate_mean = 0.025

    config.simulation.simulation_duration_gyr = 1.5
    config.simulation.time_step_myr = 5.0
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 75.0

    config.astrophysics.supernova_rate_per_galaxy_gyr = 3.0
    config.astrophysics.grb_rate_per_galaxy_gyr = 2.0

    print(f"Simulation Parameters:")
    print(f"  Galaxy: {config.galaxy.total_stars:,} stars")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Snapshots: {int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.snapshot_interval_myr)}")
    print()

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
    total_hazards = len(sim.hazard_events)

    print(f"\nSimulation complete!")
    print(f"  Total civilizations: {total_civs}")
    print(f"  Currently active: {active_civs}")
    print(f"  Extinct: {total_civs - active_civs}")
    print(f"  Total hazards: {total_hazards}")
    print(f"  Snapshots captured: {len(sim.snapshots)}")

    print("\n" + "=" * 80)
    print("EXPORTING THREE.JS VISUALIZATION")
    print("=" * 80)

    output_path = Path("examples/galaxy_visualization.html")
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
    print("OPENING IN BROWSER")
    print("=" * 80)

    import subprocess
    import sys
    
    url = f"file://{output_path.absolute()}"
    print(f"\n  URL: {url}")
    print("\n  Opening in browser...")

    if sys.platform == 'darwin':
        subprocess.run(['open', str(output_path)], check=False)
    elif sys.platform == 'linux':
        subprocess.run(['xdg-open', str(output_path)], check=False)
    elif sys.platform == 'win32':
        subprocess.run(['start', str(output_path)], shell=True, check=False)
    else:
        print(f"\n  Open manually: {url}")

    print("\n" + "=" * 80)
    print("VISUALIZATION FEATURES")
    print("=" * 80)
    print("\nControls:")
    print("  Left-click + drag: Rotate view")
    print("  Right-click + drag: Pan")
    print("  Scroll: Zoom in/out")
    print("  Space: Play/Pause")
    print("  Arrow keys: Rotate camera")
    print("  WASD: Pan camera")
    print("  +/-: Zoom")
    print("\nUI Features:")
    print("  - Timeline slider: Scrub through simulation")
    print("  - Speed slider: 0.1x to 10x playback speed")
    print("  - Layer toggles: Show/hide stars, civilizations, probes, hazards")
    print("  - Camera presets: Top, Edge, Angled views")
    print("  - Auto-rotate: Automatic camera rotation")
    print("  - Hover over civilizations: See details (Kardashev, age, status)")
    print("  - Click on civilization: Follow it with camera")
    print("  - Mini-map: 2D galaxy overview")
    print("  - Export Frame: Save current view as PNG")
    print("  - Effects: Toggle post-processing (bloom, film grain)")
    print("\n✓ Complete!")


if __name__ == "__main__":
    create_example_viz()
