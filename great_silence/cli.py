"""Command-line interface for GalaticBot."""

import argparse
import sys
from pathlib import Path

from .simulation.engine import GalaxySimulation
from .simulation.monte_carlo import MonteCarloRunner
from .config.parameters import SimulationConfig
from .visualization import GalaxyVisualizer


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GalaticBot: Monte Carlo simulation of galactic civilizations"
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to YAML configuration file"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["single", "monte-carlo"],
        default="single",
        help="Simulation mode: single run or Monte Carlo ensemble"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="Output directory for results"
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility"
    )

    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate visualizations after simulation"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test simulation (reduced stars and duration)"
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load configuration
    if args.config:
        config = SimulationConfig.from_yaml(args.config)
        print(f"Loaded configuration from: {args.config}")
    else:
        config = SimulationConfig()
        print("Using default configuration")

    # Apply quick mode adjustments
    if args.quick:
        print("\nQuick mode enabled - reducing parameters for fast test run")
        config.galaxy.total_stars = 10_000
        config.simulation.simulation_duration_gyr = 1.0
        config.simulation.time_step_myr = 10.0
        config.simulation.num_realizations = 10

    # Override seed if provided
    if args.seed is not None:
        config.simulation.random_seed = args.seed

    # Set output directory
    config.simulation.output_directory = str(output_dir)

    print("\n" + "=" * 70)
    print("GalaticBot Simulation")
    print("=" * 70)
    print(f"\nMode: {args.mode}")
    print(f"Stars: {config.galaxy.total_stars:,}")
    print(f"Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"Time step: {config.simulation.time_step_myr} Myr")
    print(f"Random seed: {config.simulation.random_seed}")

    if args.mode == "single":
        # Run single simulation
        print("\nRunning single simulation...")
        sim = GalaxySimulation(config, seed=config.simulation.random_seed)
        sim.run(verbose=True)

        # Print statistics
        stats = sim.get_statistics()
        print("\n" + "=" * 70)
        print("Results:")
        print("=" * 70)
        print(f"Total civilizations: {stats['total_civilizations']}")
        print(f"Active civilizations: {stats['active_civilizations']}")
        print(f"Extinct civilizations: {stats['extinct_civilizations']}")
        print(f"Colonized systems: {stats['total_colonized_systems']}")

        # Visualize if requested
        if args.visualize and sim.galaxy.positions is not None:
            print("\nGenerating visualizations...")
            viz = GalaxyVisualizer()

            # Galaxy structure
            viz.plot_galaxy_structure(
                sim.galaxy.positions,
                save_path=str(output_dir / "galaxy_structure.png")
            )
            print(f"  Saved: {output_dir / 'galaxy_structure.png'}")

            # Civilization distribution
            if sim.civilizations:
                civ_indices = [c.parent_star_idx for c in sim.civilizations if c.is_active]
                if civ_indices:
                    viz.plot_civilization_distribution(
                        sim.galaxy.positions,
                        civ_indices,
                        save_path=str(output_dir / "civilizations.png")
                    )
                    print(f"  Saved: {output_dir / 'civilizations.png'}")

    elif args.mode == "monte-carlo":
        # Run Monte Carlo ensemble
        print(f"\nRunning {config.simulation.num_realizations} Monte Carlo realizations...")

        runner = MonteCarloRunner(config)

        if config.simulation.parallel_processing:
            results = runner.run_parallel()
        else:
            results = runner.run_sequential()

        # Analyze results
        analysis = runner.analyze_results()

        print("\n" + "=" * 70)
        print("Monte Carlo Analysis:")
        print("=" * 70)
        print(f"Realizations: {analysis['n_realizations']}")
        print("\nTotal Civilizations:")
        print(f"  Mean: {analysis['total_civilizations']['mean']:.1f}")
        print(f"  Std:  {analysis['total_civilizations']['std']:.1f}")
        print(f"  Median: {analysis['total_civilizations']['median']:.1f}")
        print(f"  Range: [{analysis['total_civilizations']['min']}, "
              f"{analysis['total_civilizations']['max']}]")
        print("\nActive Civilizations:")
        print(f"  Mean: {analysis['active_civilizations']['mean']:.1f}")
        print(f"  Std:  {analysis['active_civilizations']['std']:.1f}")
        print(f"  Median: {analysis['active_civilizations']['median']:.1f}")
        print(f"  Range: [{analysis['active_civilizations']['min']}, "
              f"{analysis['active_civilizations']['max']}]")
        print(f"\nExtinction Rate: {analysis['extinction_rate']['mean']:.2%} "
              f"± {analysis['extinction_rate']['std']:.2%}")

    print("\n" + "=" * 70)
    print("Simulation complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
