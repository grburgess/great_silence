"""
Galaxy Realism Demonstration

This script demonstrates the new galaxy realism features:
- Bulge component (central spheroid, 20% of stars)
- Radial age gradient (inside-out galaxy formation)
- Metallicity gradient (affects planet formation probability)

Run this to visualize how these features affect galactic structure
and civilization emergence patterns.
"""

import numpy as np
import matplotlib.pyplot as plt
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization import GalaxyVisualizer

def main():
    """Run galaxy realism demonstration."""

    # Create configuration with galaxy realism features ENABLED
    print("=" * 70)
    print("GALAXY REALISM DEMONSTRATION")
    print("=" * 70)
    print("\nInitializing simulation with realistic Milky Way structure...")
    print("- Bulge component: 20% of stars (Hernquist profile)")
    print("- Age gradient: Inner stars ~11 Gyr, outer stars ~3 Gyr")
    print("- Metallicity gradient: -0.07 dex/kpc (affects planet formation)")
    print()

    config = SimulationConfig()

    # Reduce star count for faster visualization
    config.galaxy.total_stars = 100_000

    # Enable galaxy realism features (should be ON by default)
    config.galaxy.include_bulge = True
    config.galaxy.bulge_fraction = 0.2  # 20% of stars in bulge
    config.galaxy.use_age_gradient = True
    config.galaxy.use_metallicity_gradient = True

    # Create and initialize simulation
    sim = GalaxySimulation(config, seed=42)
    sim.initialize()

    # Print summary statistics
    print("\n" + "-" * 70)
    print("GALAXY STRUCTURE SUMMARY")
    print("-" * 70)

    # Component breakdown
    bulge_count = np.sum(sim.galaxy.component_type == 0)
    disk_count = np.sum(sim.galaxy.component_type == 1)
    print(f"\nStellar Components:")
    print(f"  Bulge stars: {bulge_count:,} ({100*bulge_count/config.galaxy.total_stars:.1f}%)")
    print(f"  Disk stars:  {disk_count:,} ({100*disk_count/config.galaxy.total_stars:.1f}%)")

    # Age statistics by component
    bulge_ages = sim.galaxy.ages[sim.galaxy.component_type == 0]
    disk_ages = sim.galaxy.ages[sim.galaxy.component_type == 1]
    print(f"\nStellar Ages:")
    print(f"  Bulge: {bulge_ages.mean():.2f} ± {bulge_ages.std():.2f} Gyr (older)")
    print(f"  Disk:  {disk_ages.mean():.2f} ± {disk_ages.std():.2f} Gyr (younger)")

    # Metallicity statistics by component
    bulge_metals = sim.galaxy.metallicities[sim.galaxy.component_type == 0]
    disk_metals = sim.galaxy.metallicities[sim.galaxy.component_type == 1]
    print(f"\nMetallicity [Fe/H]:")
    print(f"  Bulge: {bulge_metals.mean():+.3f} ± {bulge_metals.std():.3f} dex (metal-rich)")
    print(f"  Disk:  {disk_metals.mean():+.3f} ± {disk_metals.std():.3f} dex")

    # Radial age gradient
    x, y = sim.galaxy.positions[:, 0], sim.galaxy.positions[:, 1]
    radii = np.sqrt(x**2 + y**2)

    print(f"\nAge Gradient (Inside-Out Formation):")
    inner_mask = radii < 3
    middle_mask = (radii >= 3) & (radii < 10)
    outer_mask = radii >= 10

    print(f"  Inner (r < 3 kpc):   {sim.galaxy.ages[inner_mask].mean():.2f} Gyr")
    print(f"  Middle (3-10 kpc):   {sim.galaxy.ages[middle_mask].mean():.2f} Gyr")
    print(f"  Outer (r > 10 kpc):  {sim.galaxy.ages[outer_mask].mean():.2f} Gyr")

    print(f"\nMetallicity Gradient:")
    print(f"  Inner (r < 3 kpc):   {sim.galaxy.metallicities[inner_mask].mean():+.3f} dex")
    print(f"  Middle (3-10 kpc):   {sim.galaxy.metallicities[middle_mask].mean():+.3f} dex")
    print(f"  Outer (r > 10 kpc):  {sim.galaxy.metallicities[outer_mask].mean():+.3f} dex")

    # Metallicity impact on habitability
    print(f"\nMetallicity Impact on Planet Formation:")
    print(f"  At [Fe/H] = +0.3 (bulge): {1.0 * 10**0.3:.2f}x more planets than solar")
    print(f"  At [Fe/H] = 0.0 (solar):  1.00x (baseline)")
    print(f"  At [Fe/H] = -0.5 (outer): {1.0 * 10**(-0.5):.2f}x fewer planets than solar")

    # Create visualizations
    print("\n" + "-" * 70)
    print("GENERATING VISUALIZATIONS")
    print("-" * 70)

    viz = GalaxyVisualizer(figsize=(12, 10))

    print("\n1. Plotting bulge + disk structure...")
    viz.plot_bulge_and_disk(
        sim.galaxy.positions,
        sim.galaxy.component_type,
        save_path='output/galaxy_bulge_disk.png'
    )
    print("   Saved: output/galaxy_bulge_disk.png")

    print("\n2. Plotting age gradient (inside-out formation)...")
    viz.plot_age_gradient(
        sim.galaxy.positions,
        sim.galaxy.ages,
        save_path='output/galaxy_age_gradient.png'
    )
    print("   Saved: output/galaxy_age_gradient.png")

    print("\n3. Plotting metallicity gradient...")
    viz.plot_metallicity_gradient(
        sim.galaxy.positions,
        sim.galaxy.metallicities,
        save_path='output/galaxy_metallicity_gradient.png'
    )
    print("   Saved: output/galaxy_metallicity_gradient.png")

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nKey Findings:")
    print("- Bulge stars are older and metal-rich (formed early in galaxy history)")
    print("- Age decreases with radius (inside-out formation)")
    print("- Metallicity decreases with radius (-0.07 dex/kpc gradient)")
    print("- Metallicity affects planet formation (metal-rich → more planets)")
    print("\nScientific Implications:")
    print("- Central bulge is hostile early (dense, many supernovae)")
    print("- Solar neighborhood (r ~ 8 kpc) is 'Goldilocks zone'")
    print("- Outer disk has fewer planets (low metallicity)")
    print("\nVisualizations saved to output/ directory.")
    print()


def compare_with_without_realism():
    """
    Compare galaxy with and without realism features.

    This shows the impact of enabling bulge, age gradient, and metallicity.
    """
    print("\n" + "=" * 70)
    print("COMPARISON: WITH vs WITHOUT REALISM")
    print("=" * 70)

    # Configuration WITHOUT realism
    config_basic = SimulationConfig()
    config_basic.galaxy.total_stars = 100_000
    config_basic.galaxy.include_bulge = False
    config_basic.galaxy.use_age_gradient = False
    config_basic.galaxy.use_metallicity_gradient = False

    print("\n[1/2] Generating basic galaxy (disk only, no gradients)...")
    sim_basic = GalaxySimulation(config_basic, seed=42)
    sim_basic.initialize()

    # Configuration WITH realism
    config_real = SimulationConfig()
    config_real.galaxy.total_stars = 100_000
    config_real.galaxy.include_bulge = True
    config_real.galaxy.use_age_gradient = True
    config_real.galaxy.use_metallicity_gradient = True

    print("[2/2] Generating realistic galaxy (bulge + disk, gradients)...")
    sim_real = GalaxySimulation(config_real, seed=42)
    sim_real.initialize()

    # Compare statistics
    print("\n" + "-" * 70)
    print("STATISTICAL COMPARISON")
    print("-" * 70)

    print("\nAge Distribution:")
    print(f"  Basic galaxy:     {sim_basic.galaxy.ages.mean():.2f} ± {sim_basic.galaxy.ages.std():.2f} Gyr")
    print(f"  Realistic galaxy: {sim_real.galaxy.ages.mean():.2f} ± {sim_real.galaxy.ages.std():.2f} Gyr")

    print("\nMetallicity Distribution:")
    print(f"  Basic galaxy:     {sim_basic.galaxy.metallicities.mean():+.3f} ± {sim_basic.galaxy.metallicities.std():.3f} dex")
    print(f"  Realistic galaxy: {sim_real.galaxy.metallicities.mean():+.3f} ± {sim_real.galaxy.metallicities.std():.3f} dex")

    # Create comparison plot
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    # Row 1: Basic galaxy
    ax = axes[0, 0]
    ax.scatter(sim_basic.galaxy.positions[:, 0], sim_basic.galaxy.positions[:, 1],
               s=0.1, alpha=0.2, color='white')
    ax.set_title('Basic: Disk Only', fontsize=12, color='white')
    ax.set_xlabel('X (kpc)')
    ax.set_ylabel('Y (kpc)')
    ax.set_aspect('equal')
    ax.set_facecolor('black')

    ax = axes[0, 1]
    scatter = ax.scatter(sim_basic.galaxy.positions[:, 0], sim_basic.galaxy.positions[:, 1],
                        c=sim_basic.galaxy.ages, s=0.5, alpha=0.3, cmap='coolwarm_r', vmin=0, vmax=13)
    ax.set_title('Basic: Uniform Age', fontsize=12, color='white')
    ax.set_xlabel('X (kpc)')
    ax.set_ylabel('Y (kpc)')
    ax.set_aspect('equal')
    ax.set_facecolor('black')
    plt.colorbar(scatter, ax=ax, label='Age (Gyr)')

    ax = axes[0, 2]
    scatter = ax.scatter(sim_basic.galaxy.positions[:, 0], sim_basic.galaxy.positions[:, 1],
                        c=sim_basic.galaxy.metallicities, s=0.5, alpha=0.3, cmap='RdYlBu_r', vmin=-1, vmax=0.5)
    ax.set_title('Basic: Uniform Metallicity', fontsize=12, color='white')
    ax.set_xlabel('X (kpc)')
    ax.set_ylabel('Y (kpc)')
    ax.set_aspect('equal')
    ax.set_facecolor('black')
    plt.colorbar(scatter, ax=ax, label='[Fe/H]')

    # Row 2: Realistic galaxy
    bulge_mask = sim_real.galaxy.component_type == 0
    disk_mask = sim_real.galaxy.component_type == 1

    ax = axes[1, 0]
    ax.scatter(sim_real.galaxy.positions[disk_mask, 0], sim_real.galaxy.positions[disk_mask, 1],
               s=0.1, alpha=0.2, color='lightblue', label='Disk')
    ax.scatter(sim_real.galaxy.positions[bulge_mask, 0], sim_real.galaxy.positions[bulge_mask, 1],
               s=0.3, alpha=0.5, color='orange', label='Bulge')
    ax.set_title('Realistic: Bulge + Disk', fontsize=12, color='white')
    ax.set_xlabel('X (kpc)')
    ax.set_ylabel('Y (kpc)')
    ax.set_aspect('equal')
    ax.set_facecolor('black')
    ax.legend()

    ax = axes[1, 1]
    scatter = ax.scatter(sim_real.galaxy.positions[:, 0], sim_real.galaxy.positions[:, 1],
                        c=sim_real.galaxy.ages, s=0.5, alpha=0.3, cmap='coolwarm_r', vmin=0, vmax=13)
    ax.set_title('Realistic: Age Gradient', fontsize=12, color='white')
    ax.set_xlabel('X (kpc)')
    ax.set_ylabel('Y (kpc)')
    ax.set_aspect('equal')
    ax.set_facecolor('black')
    plt.colorbar(scatter, ax=ax, label='Age (Gyr)')

    ax = axes[1, 2]
    scatter = ax.scatter(sim_real.galaxy.positions[:, 0], sim_real.galaxy.positions[:, 1],
                        c=sim_real.galaxy.metallicities, s=0.5, alpha=0.3, cmap='RdYlBu_r', vmin=-1, vmax=0.5)
    ax.set_title('Realistic: Metallicity Gradient', fontsize=12, color='white')
    ax.set_xlabel('X (kpc)')
    ax.set_ylabel('Y (kpc)')
    ax.set_aspect('equal')
    ax.set_facecolor('black')
    plt.colorbar(scatter, ax=ax, label='[Fe/H]')

    plt.tight_layout()
    plt.savefig('output/galaxy_comparison.png', dpi=150, facecolor='black')
    print("\nComparison plot saved: output/galaxy_comparison.png")
    plt.close()

    print("\nConclusion:")
    print("  Realistic galaxy shows:")
    print("  - Central bulge component (orange)")
    print("  - Age gradient (red = old, blue = young)")
    print("  - Metallicity gradient (red = metal-rich, blue = metal-poor)")
    print()


if __name__ == '__main__':
    # Create output directory
    import os
    os.makedirs('output', exist_ok=True)

    # Run main demonstration
    main()

    # Run comparison (optional, comment out to skip)
    compare_with_without_realism()
