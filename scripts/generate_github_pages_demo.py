#!/usr/bin/env python3
"""
Generate an interactive Three.js demo for GitHub Pages.

This script creates a self-contained HTML visualization that can be
hosted on GitHub Pages or any static file server.

Usage:
    python scripts/generate_github_pages_demo.py

Output:
    docs/demo/index.html - Interactive Three.js visualization
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs import export_html, ThreeJSConfig


def main():
    print("=" * 70)
    print("GREAT SILENCE - GitHub Pages Demo Generator")
    print("=" * 70)
    print()

    config = SimulationConfig.with_preset("optimistic")

    config.galaxy.total_stars = 15_000
    config.galaxy.include_bulge = True
    config.galaxy.bulge_fraction = 0.2
    config.galaxy.scale_length_kpc = 3.5

    config.civilization.fraction_develop_life = 0.5
    config.civilization.fraction_develop_intelligence = 0.1
    config.civilization.fraction_develop_technology = 0.5
    config.civilization.mean_civilization_lifetime_myr = 500.0
    config.civilization.self_destruction_model_type = "kardashev_dependent"

    config.simulation.simulation_duration_gyr = 2.0
    config.simulation.time_step_myr = 10.0
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 25.0

    print("Configuration:")
    print(f"  Stars: {config.galaxy.total_stars:,}")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Snapshots: ~{int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.snapshot_interval_myr)}")
    print()

    print("Running simulation...")
    sim = GalaxySimulation(config, seed=42)
    sim.initialize()

    print(f"  Habitable stars: {len(sim.habitable_star_indices):,}")
    print()

    sim.run()

    total_civs = len(sim.civilizations)
    active_civs = sum(1 for c in sim.civilizations if c.is_active)

    print()
    print(f"Simulation complete:")
    print(f"  Total civilizations: {total_civs}")
    print(f"  Currently active: {active_civs}")
    print(f"  Snapshots: {len(sim.snapshots)}")
    print()

    print("Configuring Three.js visualization...")
    viz_config = ThreeJSConfig()
    viz_config.camera_presets = [
        {
            "name": "Galaxy Overview",
            "position": [0.0, 0.0, 35.0],
            "target": [0.0, 0.0, 0.0],
            "duration": 2.0,
        },
        {
            "name": "Edge-On View",
            "position": [35.0, 0.0, 5.0],
            "target": [0.0, 0.0, 0.0],
            "duration": 2.5,
        },
        {
            "name": "Dramatic Angle",
            "position": [20.0, 20.0, 20.0],
            "target": [0.0, 0.0, 0.0],
            "duration": 2.0,
        },
        {
            "name": "Close-Up Bulge",
            "position": [5.0, 5.0, 8.0],
            "target": [0.0, 0.0, 0.0],
            "duration": 1.5,
        },
    ]

    output_dir = Path(__file__).parent.parent / "docs" / "demo"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"

    print(f"Exporting to: {output_path}")
    print()

    export_html(
        sim,
        output_path,
        config=viz_config,
        animated=True,
        show_trajectories=True,
        show_spheres=True,
        show_hazards=True,
        compress=False,
    )

    file_size_kb = output_path.stat().st_size / 1024
    print("=" * 70)
    print("Export Complete!")
    print("=" * 70)
    print()
    print(f"  Output: {output_path}")
    print(f"  Size: {file_size_kb:.1f} KB")
    print()
    print("To deploy on GitHub Pages:")
    print("  1. Commit the docs/demo/ folder to your repository")
    print("  2. Go to Settings > Pages in your GitHub repository")
    print("  3. Set source to 'Deploy from a branch'")
    print("  4. Select 'main' branch and '/docs' folder")
    print("  5. Your demo will be at: https://USERNAME.github.io/great_silence/demo/")
    print()
    print("To preview locally:")
    print(f"  open {output_path}")
    print()


if __name__ == "__main__":
    main()
