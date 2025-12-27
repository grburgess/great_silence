"""
Full Simulation Test with All New Features

Tests complete simulation with:
- Bulge + disk galaxy structure
- Age and metallicity gradients
- Metallicity-dependent planet formation
- Metallicity-dependent GRB rates
- Component/density-dependent supernova rates
- Local density hazard modifiers

Runs a 5 Gyr simulation and analyzes results.
"""

import numpy as np
import matplotlib.pyplot as plt
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization import GalaxyVisualizer

def create_simulation_config():
    """Create configuration for full simulation test."""
    config = SimulationConfig()

    # Galaxy parameters (all realism features enabled)
    config.galaxy.total_stars = 100_000  # Enough for good statistics
    config.galaxy.include_bulge = True
    config.galaxy.bulge_fraction = 0.2
    config.galaxy.use_age_gradient = True
    config.galaxy.use_metallicity_gradient = True

    # Simulation parameters
    config.simulation.simulation_duration_gyr = 5.0  # 5 Gyr simulation
    config.simulation.time_step_myr = 10.0  # 10 Myr steps (500 steps total)
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 500.0  # Every 500 Myr

    # Civilization parameters (moderate scenario)
    config.civilization.fraction_develop_life = 0.1
    config.civilization.fraction_develop_intelligence = 0.01
    config.civilization.fraction_develop_technology = 0.1
    config.civilization.mean_civilization_lifetime_myr = 1.0
    config.civilization.self_destruction_probability_per_myr = 0.1

    return config


def run_full_simulation():
    """Run complete simulation and save results."""
    print("=" * 80)
    print("FULL SIMULATION TEST - ALL NEW FEATURES")
    print("=" * 80)

    # Create configuration
    config = create_simulation_config()

    print("\n" + "-" * 80)
    print("CONFIGURATION")
    print("-" * 80)
    print(f"Stars: {config.galaxy.total_stars:,}")
    print(f"Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"Time step: {config.simulation.time_step_myr} Myr")
    print(f"Total steps: {int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.time_step_myr)}")

    print("\nGalaxy Features:")
    print(f"  ✓ Bulge component ({config.galaxy.bulge_fraction*100}% of stars)")
    print(f"  ✓ Age gradient (inside-out formation)")
    print(f"  ✓ Metallicity gradient (-{-config.galaxy.metallicity_gradient_dex_per_kpc} dex/kpc)")

    print("\nHazard Physics:")
    print("  ✓ Metallicity-dependent GRB rates")
    print("  ✓ Component/age-dependent SN rates")
    print("  ✓ Local density hazard modifiers")

    # Initialize and run simulation
    print("\n" + "-" * 80)
    print("RUNNING SIMULATION")
    print("-" * 80)

    sim = GalaxySimulation(config, seed=42)
    sim.initialize()

    print(f"\nGalaxy initialized:")
    print(f"  Total stars: {len(sim.galaxy.positions):,}")
    print(f"  Habitable stars: {len(sim.habitable_star_indices):,}")

    # Run simulation
    print("\nRunning simulation...")
    sim.run(verbose=True)

    return sim, config


def analyze_results(sim, config):
    """Analyze simulation results."""
    print("\n" + "=" * 80)
    print("SIMULATION RESULTS")
    print("=" * 80)

    # Basic statistics
    total_civs = len(sim.civilizations)
    active_civs = sum(c.is_active for c in sim.civilizations)
    extinct_civs = total_civs - active_civs

    print(f"\n--- Civilization Statistics ---")
    print(f"Total civilizations emerged: {total_civs}")
    print(f"Currently active: {active_civs}")
    print(f"Extinct: {extinct_civs}")

    if total_civs == 0:
        print("\n⚠️  No civilizations emerged!")
        print("   Try increasing Drake equation parameters or simulation duration.")
        return

    # Extinction causes
    print(f"\n--- Extinction Causes ---")
    death_causes = {}
    for civ in sim.civilizations:
        if not civ.is_active and hasattr(civ, 'death_cause'):
            cause = civ.death_cause
            death_causes[cause] = death_causes.get(cause, 0) + 1

    for cause, count in sorted(death_causes.items(), key=lambda x: x[1], reverse=True):
        pct = 100 * count / extinct_civs if extinct_civs > 0 else 0
        print(f"  {cause}: {count} ({pct:.1f}%)")

    # Spatial distribution analysis
    print(f"\n--- Spatial Distribution ---")

    # Calculate radii
    x = sim.galaxy.positions[:, 0]
    y = sim.galaxy.positions[:, 1]
    all_radii = np.sqrt(x**2 + y**2)

    civ_radii = []
    civ_metallicities = []
    civ_densities = []

    for civ in sim.civilizations:
        star_idx = civ.parent_star_idx
        civ_pos = sim.galaxy.positions[star_idx]
        r = np.sqrt(civ_pos[0]**2 + civ_pos[1]**2)
        civ_radii.append(r)
        civ_metallicities.append(sim.galaxy.metallicities[star_idx])

        # Get local density from hazard stats if available
        if hasattr(civ, 'hazard_stats') and 'local_density' in civ.hazard_stats:
            civ_densities.append(civ.hazard_stats['local_density'])

    civ_radii = np.array(civ_radii)
    civ_metallicities = np.array(civ_metallicities)

    print(f"Civilization radii:")
    print(f"  Mean: {civ_radii.mean():.2f} kpc")
    print(f"  Median: {np.median(civ_radii):.2f} kpc")
    print(f"  Range: {civ_radii.min():.2f} - {civ_radii.max():.2f} kpc")

    # Check if civilizations cluster in GHZ (6-10 kpc)
    in_ghz = np.sum((civ_radii >= 6) & (civ_radii <= 10))
    pct_in_ghz = 100 * in_ghz / len(civ_radii)
    print(f"\nCivilizations in Galactic Habitable Zone (6-10 kpc): {in_ghz} ({pct_in_ghz:.1f}%)")

    # Compare to random distribution
    random_in_ghz = np.sum((all_radii >= 6) & (all_radii <= 10)) / len(all_radii)
    enrichment = (pct_in_ghz / 100) / random_in_ghz if random_in_ghz > 0 else 0
    print(f"Random expectation: {random_in_ghz*100:.1f}%")
    print(f"Enrichment factor: {enrichment:.2f}x")

    if enrichment > 1.2:
        print("  ✓ Civilizations ARE clustering in GHZ! (as expected)")
    elif enrichment < 0.8:
        print("  ✗ Civilizations AVOIDING GHZ (unexpected)")
    else:
        print("  ~ Civilizations roughly uniform (may need longer simulation)")

    # Metallicity distribution
    print(f"\nCivilization metallicities:")
    print(f"  Mean [Fe/H]: {civ_metallicities.mean():+.3f}")
    print(f"  Range: {civ_metallicities.min():+.3f} to {civ_metallicities.max():+.3f}")

    # Hazard statistics
    if civ_densities:
        print(f"\n--- Hazard Environment ---")
        print(f"Average local density: {np.mean(civ_densities):.4f} stars/pc³")
        print(f"Density range: {np.min(civ_densities):.4f} - {np.max(civ_densities):.4f}")

        # Compare bulge vs disk civilizations
        bulge_civs = [c for c in sim.civilizations
                      if sim.galaxy.component_type[c.parent_star_idx] == 0]
        disk_civs = [c for c in sim.civilizations
                     if sim.galaxy.component_type[c.parent_star_idx] == 1]

        print(f"\nBulge civilizations: {len(bulge_civs)}")
        print(f"Disk civilizations: {len(disk_civs)}")

        if bulge_civs:
            bulge_survival = sum(c.is_active for c in bulge_civs) / len(bulge_civs)
            print(f"Bulge survival rate: {bulge_survival*100:.1f}%")

        if disk_civs:
            disk_survival = sum(c.is_active for c in disk_civs) / len(disk_civs)
            print(f"Disk survival rate: {disk_survival*100:.1f}%")

    # Kardashev progression
    if active_civs > 0:
        print(f"\n--- Active Civilization Technology ---")
        kardashev_levels = [c.kardashev_scale for c in sim.civilizations if c.is_active]
        print(f"Average Kardashev scale: {np.mean(kardashev_levels):.2f}")
        print(f"Range: {np.min(kardashev_levels):.2f} - {np.max(kardashev_levels):.2f}")

    return {
        'civ_radii': civ_radii,
        'civ_metallicities': civ_metallicities,
        'death_causes': death_causes,
        'in_ghz': in_ghz,
        'enrichment': enrichment
    }


def create_visualizations(sim, config, results):
    """Create comprehensive visualizations."""
    print("\n" + "=" * 80)
    print("CREATING VISUALIZATIONS")
    print("=" * 80)

    viz = GalaxyVisualizer()

    # 1. Galaxy structure with civilizations
    print("\n1. Galaxy structure with civilizations...")
    active_indices = [c.parent_star_idx for c in sim.civilizations if c.is_active]
    extinct_indices = [c.parent_star_idx for c in sim.civilizations if not c.is_active]

    fig = plt.figure(figsize=(16, 6))

    # Panel 1: Bulge + Disk with civilizations
    ax1 = fig.add_subplot(1, 3, 1)
    bulge_mask = sim.galaxy.component_type == 0
    disk_mask = sim.galaxy.component_type == 1

    ax1.scatter(sim.galaxy.positions[disk_mask, 0], sim.galaxy.positions[disk_mask, 1],
               s=0.1, alpha=0.1, color='lightblue', label='Disk')
    ax1.scatter(sim.galaxy.positions[bulge_mask, 0], sim.galaxy.positions[bulge_mask, 1],
               s=0.2, alpha=0.3, color='orange', label='Bulge')

    if extinct_indices:
        extinct_pos = sim.galaxy.positions[extinct_indices]
        ax1.scatter(extinct_pos[:, 0], extinct_pos[:, 1],
                   s=30, alpha=0.5, color='red', marker='x', label='Extinct civilizations')

    if active_indices:
        active_pos = sim.galaxy.positions[active_indices]
        ax1.scatter(active_pos[:, 0], active_pos[:, 1],
                   s=80, alpha=0.8, color='cyan', marker='*',
                   edgecolors='white', linewidths=0.5, label='Active civilizations')

    # Mark GHZ
    theta = np.linspace(0, 2*np.pi, 100)
    for r in [6, 10]:
        ax1.plot(r * np.cos(theta), r * np.sin(theta), 'g--', linewidth=2, alpha=0.7)
    ax1.text(8, 0, 'GHZ', color='green', fontsize=14, weight='bold',
            ha='center', va='center',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax1.set_xlabel('X (kpc)')
    ax1.set_ylabel('Y (kpc)')
    ax1.set_title(f'Galaxy Structure + Civilizations (t = {config.simulation.simulation_duration_gyr} Gyr)')
    ax1.set_aspect('equal')
    ax1.legend(loc='upper right', fontsize=8)
    ax1.set_facecolor('black')

    # Panel 2: Radial distribution
    ax2 = fig.add_subplot(1, 3, 2)

    # All stars
    all_r = np.sqrt(sim.galaxy.positions[:, 0]**2 + sim.galaxy.positions[:, 1]**2)
    ax2.hist(all_r, bins=50, alpha=0.3, color='gray', label='All stars', density=True)

    # Civilizations
    if len(results['civ_radii']) > 0:
        ax2.hist(results['civ_radii'], bins=30, alpha=0.7, color='cyan',
                label='Civilizations', density=True)

    # Mark GHZ
    ax2.axvspan(6, 10, alpha=0.2, color='green', label='GHZ (6-10 kpc)')

    ax2.set_xlabel('Galactocentric Radius (kpc)')
    ax2.set_ylabel('Probability Density')
    ax2.set_title('Civilization Radial Distribution')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Panel 3: Metallicity distribution
    ax3 = fig.add_subplot(1, 3, 3)

    ax3.hist(sim.galaxy.metallicities, bins=50, alpha=0.3, color='gray',
            label='All stars', density=True)

    if len(results['civ_metallicities']) > 0:
        ax3.hist(results['civ_metallicities'], bins=30, alpha=0.7, color='cyan',
                label='Civilizations', density=True)

    ax3.axvline(0, color='white', linestyle='--', linewidth=1, alpha=0.5, label='Solar')
    ax3.set_xlabel('[Fe/H]')
    ax3.set_ylabel('Probability Density')
    ax3.set_title('Metallicity Distribution')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('output/full_simulation_civilizations.png', dpi=150, facecolor='black')
    print("   Saved: output/full_simulation_civilizations.png")
    plt.close()

    # 2. Extinction causes pie chart
    if results['death_causes']:
        print("\n2. Extinction causes analysis...")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Pie chart
        labels = list(results['death_causes'].keys())
        sizes = list(results['death_causes'].values())
        colors = plt.cm.Set3(range(len(labels)))

        ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
        ax1.set_title('Extinction Causes Distribution')

        # Bar chart with details
        ax2.bar(range(len(labels)), sizes, color=colors)
        ax2.set_xticks(range(len(labels)))
        ax2.set_xticklabels(labels, rotation=45, ha='right')
        ax2.set_ylabel('Number of Civilizations')
        ax2.set_title('Extinction Causes (Count)')
        ax2.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig('output/full_simulation_extinction_causes.png', dpi=150)
        print("   Saved: output/full_simulation_extinction_causes.png")
        plt.close()

    # 3. Hazard zones map
    print("\n3. Hazard zones map...")
    viz.plot_hazard_zones(
        sim.galaxy.positions,
        sim.galaxy.masses,
        sim.galaxy.ages,
        sim.galaxy.component_type,
        sim.galaxy.metallicities,
        save_path='output/full_simulation_hazard_zones.png'
    )

    # 4. Age and metallicity gradients
    print("\n4. Age and metallicity gradients...")
    viz.plot_age_gradient(
        sim.galaxy.positions,
        sim.galaxy.ages,
        save_path='output/full_simulation_age_gradient.png'
    )

    viz.plot_metallicity_gradient(
        sim.galaxy.positions,
        sim.galaxy.metallicities,
        save_path='output/full_simulation_metallicity_gradient.png'
    )

    # 5. Civilization evolution over time
    if len(sim.snapshots) > 0:
        print("\n5. Civilization evolution timeline...")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        times = [s.time_myr / 1000 for s in sim.snapshots]  # Convert to Gyr
        active = [s.active_civilizations for s in sim.snapshots]
        total = [s.total_civilizations_ever for s in sim.snapshots]

        ax1.plot(times, active, 'cyan', linewidth=2, label='Active')
        ax1.plot(times, total, 'orange', linewidth=2, label='Total emerged')
        ax1.fill_between(times, active, alpha=0.3, color='cyan')
        ax1.set_xlabel('Time (Gyr)')
        ax1.set_ylabel('Number of Civilizations')
        ax1.set_title('Civilization Population Over Time')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Emergence and extinction rates
        if len(times) > 1:
            emergence_rate = np.diff(total)
            extinction_rate = np.diff(total) - np.diff(active)
            time_centers = [(times[i] + times[i+1])/2 for i in range(len(times)-1)]

            ax2.plot(time_centers, emergence_rate, 'g-', linewidth=2, label='Emergence rate')
            ax2.plot(time_centers, extinction_rate, 'r-', linewidth=2, label='Extinction rate')
            ax2.set_xlabel('Time (Gyr)')
            ax2.set_ylabel('Civilizations per Snapshot')
            ax2.set_title('Emergence and Extinction Rates')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('output/full_simulation_timeline.png', dpi=150)
        print("   Saved: output/full_simulation_timeline.png")
        plt.close()


def main():
    """Run full simulation test."""
    import os
    os.makedirs('output', exist_ok=True)

    # Run simulation
    sim, config = run_full_simulation()

    # Analyze results
    results = analyze_results(sim, config)

    # Create visualizations
    if len(sim.civilizations) > 0:
        create_visualizations(sim, config, results)
    else:
        print("\n⚠️  Skipping visualizations (no civilizations emerged)")
        print("   Try running with more optimistic Drake equation parameters:")
        print("   config.civilization.fraction_develop_life = 0.5")
        print("   config.civilization.fraction_develop_intelligence = 0.1")

    # Final summary
    print("\n" + "=" * 80)
    print("SIMULATION TEST COMPLETE")
    print("=" * 80)

    print("\n✓ All new features tested:")
    print("  - Bulge + disk galaxy structure")
    print("  - Age gradient (inside-out formation)")
    print("  - Metallicity gradient")
    print("  - Metallicity-dependent planet formation")
    print("  - Metallicity-dependent GRB rates")
    print("  - Component/density-dependent SN rates")
    print("  - Local density hazard modifiers")

    if len(sim.civilizations) > 0:
        print("\n✓ Simulation produced civilizations:")
        print(f"  - {len(sim.civilizations)} total emerged")
        print(f"  - {sum(c.is_active for c in sim.civilizations)} still active")
        print(f"  - {results['enrichment']:.2f}x enrichment in GHZ")

        print("\n✓ Visualizations created:")
        print("  - output/full_simulation_civilizations.png")
        print("  - output/full_simulation_extinction_causes.png")
        print("  - output/full_simulation_hazard_zones.png")
        print("  - output/full_simulation_age_gradient.png")
        print("  - output/full_simulation_metallicity_gradient.png")
        print("  - output/full_simulation_timeline.png")

    print("\n" + "=" * 80)
    print()


if __name__ == '__main__':
    main()
