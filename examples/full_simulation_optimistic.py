"""
Full Simulation with Optimistic Drake Parameters

Uses more optimistic parameters to generate more civilizations
for better statistical analysis of new physics features.
"""

import numpy as np
import matplotlib.pyplot as plt
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization import GalaxyVisualizer

def main():
    """Run optimistic simulation."""
    print("=" * 80)
    print("OPTIMISTIC FULL SIMULATION - MORE CIVILIZATIONS")
    print("=" * 80)

    config = SimulationConfig()

    # Galaxy parameters
    config.galaxy.total_stars = 100_000
    config.galaxy.include_bulge = True
    config.galaxy.use_age_gradient = True
    config.galaxy.use_metallicity_gradient = True

    # Simulation parameters
    config.simulation.simulation_duration_gyr = 3.0  # Shorter but enough
    config.simulation.time_step_myr = 10.0
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 500.0

    # OPTIMISTIC civilization parameters (to get more civilizations)
    config.civilization.fraction_develop_life = 0.5  # Life is common
    config.civilization.fraction_develop_intelligence = 0.1  # 10% develop intelligence
    config.civilization.fraction_develop_technology = 0.5  # 50% get technology
    config.civilization.mean_civilization_lifetime_myr = 10.0  # Long-lived (10 Myr)
    config.civilization.self_destruction_probability_per_myr = 0.01  # Low self-destruction

    print("\nConfiguration:")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Drake parameters (OPTIMISTIC):")
    print(f"    f_life = {config.civilization.fraction_develop_life}")
    print(f"    f_intel = {config.civilization.fraction_develop_intelligence}")
    print(f"    f_tech = {config.civilization.fraction_develop_technology}")
    print(f"    Lifetime = {config.civilization.mean_civilization_lifetime_myr} Myr")

    # Run simulation
    print("\nInitializing and running...")
    sim = GalaxySimulation(config, seed=42)
    sim.initialize()
    sim.run(verbose=True)

    # Results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    total_civs = len(sim.civilizations)
    active = sum(c.is_active for c in sim.civilizations)

    print(f"\nCivilizations emerged: {total_civs}")
    print(f"Currently active: {active}")
    print(f"Extinct: {total_civs - active}")

    if total_civs == 0:
        print("\n⚠️  Still no civilizations! Drake parameters may need further adjustment.")
        return

    # Spatial distribution
    print("\n--- Spatial Distribution ---")
    civ_radii = []
    civ_components = []

    for civ in sim.civilizations:
        star_idx = civ.parent_star_idx
        pos = sim.galaxy.positions[star_idx]
        r = np.sqrt(pos[0]**2 + pos[1]**2)
        civ_radii.append(r)
        civ_components.append(sim.galaxy.component_type[star_idx])

    civ_radii = np.array(civ_radii)
    civ_components = np.array(civ_components)

    print(f"Radii range: {civ_radii.min():.2f} - {civ_radii.max():.2f} kpc")
    print(f"Mean radius: {civ_radii.mean():.2f} kpc")

    # Check GHZ enrichment
    in_ghz = np.sum((civ_radii >= 6) & (civ_radii <= 10))
    pct_ghz = 100 * in_ghz / len(civ_radii)
    print(f"\nIn GHZ (6-10 kpc): {in_ghz}/{len(civ_radii)} ({pct_ghz:.1f}%)")

    # Component distribution
    n_bulge_civs = np.sum(civ_components == 0)
    n_disk_civs = np.sum(civ_components == 1)
    print(f"\nBulge civilizations: {n_bulge_civs}")
    print(f"Disk civilizations: {n_disk_civs}")

    # Death causes
    print("\n--- Extinction Causes ---")
    death_causes = {}
    for civ in sim.civilizations:
        if not civ.is_active and hasattr(civ, 'death_cause'):
            cause = civ.death_cause
            death_causes[cause] = death_causes.get(cause, 0) + 1

    for cause, count in sorted(death_causes.items(), key=lambda x: x[1], reverse=True):
        pct = 100 * count / (total_civs - active) if total_civs > active else 0
        print(f"  {cause}: {count} ({pct:.1f}%)")

    # Create visualization
    print("\n--- Creating Visualization ---")
    viz = GalaxyVisualizer()

    fig = plt.figure(figsize=(14, 10))

    # Main galaxy view with civilizations
    ax1 = fig.add_subplot(2, 2, 1)

    # Plot all stars
    bulge_mask = sim.galaxy.component_type == 0
    disk_mask = sim.galaxy.component_type == 1

    ax1.scatter(sim.galaxy.positions[disk_mask, 0], sim.galaxy.positions[disk_mask, 1],
               s=0.05, alpha=0.1, color='lightblue', label='Disk stars')
    ax1.scatter(sim.galaxy.positions[bulge_mask, 0], sim.galaxy.positions[bulge_mask, 1],
               s=0.1, alpha=0.2, color='orange', label='Bulge stars')

    # Plot civilizations
    active_indices = [c.parent_star_idx for c in sim.civilizations if c.is_active]
    extinct_indices = [c.parent_star_idx for c in sim.civilizations if not c.is_active]

    if extinct_indices:
        extinct_pos = sim.galaxy.positions[extinct_indices]
        ax1.scatter(extinct_pos[:, 0], extinct_pos[:, 1],
                   s=40, alpha=0.6, color='red', marker='x', label=f'Extinct ({len(extinct_indices)})')

    if active_indices:
        active_pos = sim.galaxy.positions[active_indices]
        ax1.scatter(active_pos[:, 0], active_pos[:, 1],
                   s=100, alpha=0.9, color='cyan', marker='*',
                   edgecolors='white', linewidths=1, label=f'Active ({len(active_indices)})')

    # Mark GHZ
    theta = np.linspace(0, 2*np.pi, 100)
    ax1.plot(6 * np.cos(theta), 6 * np.sin(theta), 'g--', linewidth=2, alpha=0.6)
    ax1.plot(10 * np.cos(theta), 10 * np.sin(theta), 'g--', linewidth=2, alpha=0.6)
    ax1.text(8, 0, 'GHZ', color='green', fontsize=12, weight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax1.set_xlabel('X (kpc)')
    ax1.set_ylabel('Y (kpc)')
    ax1.set_title(f'Civilizations in Galaxy (t = {config.simulation.simulation_duration_gyr} Gyr)')
    ax1.set_aspect('equal')
    ax1.legend(loc='upper right', fontsize=9)
    ax1.set_facecolor('black')
    ax1.set_xlim(-15, 15)
    ax1.set_ylim(-15, 15)

    # Radial distribution
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.hist(civ_radii, bins=30, alpha=0.7, color='cyan', edgecolor='black')
    ax2.axvspan(6, 10, alpha=0.2, color='green', label='GHZ')
    ax2.set_xlabel('Galactocentric Radius (kpc)')
    ax2.set_ylabel('Number of Civilizations')
    ax2.set_title('Radial Distribution')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Component distribution
    ax3 = fig.add_subplot(2, 2, 3)
    labels = ['Bulge', 'Disk']
    sizes = [n_bulge_civs, n_disk_civs]
    colors = ['orange', 'lightblue']
    ax3.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
    ax3.set_title('Civilizations by Component')

    # Timeline
    ax4 = fig.add_subplot(2, 2, 4)
    if len(sim.snapshots) > 0:
        times = [s.time_myr / 1000 for s in sim.snapshots]
        active_counts = [s.active_civilizations for s in sim.snapshots]
        total_counts = [s.total_civilizations_ever for s in sim.snapshots]

        ax4.plot(times, active_counts, 'cyan', linewidth=2, marker='o', label='Active')
        ax4.plot(times, total_counts, 'orange', linewidth=2, marker='s', label='Total')
        ax4.fill_between(times, active_counts, alpha=0.3, color='cyan')
        ax4.set_xlabel('Time (Gyr)')
        ax4.set_ylabel('Number of Civilizations')
        ax4.set_title('Evolution Over Time')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('output/full_simulation_optimistic.png', dpi=150, facecolor='black')
    print("   Saved: output/full_simulation_optimistic.png")
    plt.close()

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"\n✓ Generated {total_civs} civilizations")
    print(f"✓ {pct_ghz:.1f}% in Galactic Habitable Zone")
    print(f"✓ Visualization saved")
    print()


if __name__ == '__main__':
    import os
    os.makedirs('output', exist_ok=True)
    main()
