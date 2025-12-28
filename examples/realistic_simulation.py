"""
Realistic Galactic Civilization Simulation

This simulation uses scientifically realistic parameters based on:
- Observed Milky Way galaxy structure
- Conservative estimates for Drake equation parameters
- Known astrophysical hazard rates
- Realistic timescales for cosmic evolution

Expected outcome: Few to moderate civilizations, mostly in the Galactic
Habitable Zone (6-10 kpc), with most going extinct due to astrophysical
hazards or self-destruction rather than old age.
"""

import numpy as np
import matplotlib.pyplot as plt
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization import GalaxyVisualizer


def create_realistic_config():
    """Create scientifically realistic simulation configuration."""
    config = SimulationConfig()

    # ===========================================================================
    # GALAXY STRUCTURE - Based on Milky Way observations
    # ===========================================================================

    config.galaxy.total_stars = 100_000  # Represents ~10^11 stars in Milky Way

    # Multi-component structure
    config.galaxy.include_bulge = True
    config.galaxy.bulge_fraction = 0.2  # ~20% of stars in bulge
    config.galaxy.bulge_radius_kpc = 1.0  # Compact bulge
    config.galaxy.bulge_velocity_dispersion_km_s = 100.0  # Pressure-supported

    # Disk structure
    config.galaxy.scale_length_kpc = 3.5  # Exponential disk scale
    config.galaxy.disk_radius_kpc = 15.0  # Cutoff at 15 kpc
    config.galaxy.disk_height_kpc = 0.3  # Thin disk
    config.galaxy.rotation_velocity_km_s = 220.0  # Solar neighborhood

    # Spiral structure (optional - adds realism but slight overhead)
    config.galaxy.spiral_arm_count = 4  # Like Milky Way
    config.galaxy.spiral_arm_strength = 0.1  # Subtle perturbations

    # Inside-out galaxy formation
    config.galaxy.use_age_gradient = True
    config.galaxy.central_mean_age_gyr = 11.0  # Bulge formed early
    config.galaxy.outer_mean_age_gyr = 3.0  # Outer disk is young
    config.galaxy.age_gradient_scale_kpc = 8.0  # Gradual transition

    # Metallicity gradient (critical for planet formation)
    config.galaxy.use_metallicity_gradient = True
    config.galaxy.central_metallicity_feh = 0.3  # Metal-rich bulge
    config.galaxy.metallicity_gradient_dex_per_kpc = -0.07  # Observed slope

    # ===========================================================================
    # DRAKE EQUATION - Conservative/Realistic Estimates
    # ===========================================================================

    # Probability that life develops (conservative)
    config.civilization.fraction_develop_life = 0.1
    # Life may be rare - we only have one example (Earth)

    # Probability that intelligent life develops (very conservative)
    config.civilization.fraction_develop_intelligence = 0.01
    # Intelligence took ~4 billion years on Earth, may be rare event

    # Probability that technology develops (conservative)
    config.civilization.fraction_develop_technology = 0.2
    # Tool use → radio technology is a big leap

    # Civilization lifetime (pessimistic)
    config.civilization.mean_civilization_lifetime_myr = 5.0
    # Most civilizations may not last long (5 million years average)
    # For reference: humans have had radio for ~100 years

    # Self-destruction probability (realistic)
    config.civilization.self_destruction_probability_per_myr = 0.05
    # ~25% chance of self-destruction over 5 Myr lifetime
    # Nuclear war, climate catastrophe, AI risk, etc.

    # ===========================================================================
    # ASTROPHYSICAL HAZARDS - Based on observations
    # ===========================================================================

    # Supernovae (well-constrained)
    config.astrophysics.supernova_rate_per_century = 2.0  # Milky Way rate
    config.astrophysics.sn_sterilization_range_pc = 10.0  # Conservative
    config.astrophysics.sn_lethal_range_pc = 10.0  # Lethal range in parsecs

    # Gamma-ray bursts (uncertain but potentially deadly)
    config.astrophysics.grb_rate_per_century = 0.01  # Very rare
    config.astrophysics.grb_lethal_range_kpc = 2.0  # Can reach across galaxy
    config.astrophysics.grb_beaming_angle_deg = 10.0  # Narrow jet

    # ===========================================================================
    # CIVILIZATION EXPANSION - Sub-light speed constraints
    # ===========================================================================

    config.civilization.expansion_velocity_c = 0.01  # 1% speed of light
    # Even this is very optimistic - requires massive energy
    # At 0.01c: crossing galaxy (~30 kpc) takes ~1 Gyr

    config.civilization.colonization_probability = 0.1
    # Not all reachable systems are colonized

    config.civilization.max_expansion_range_pc = 100.0
    # Practical limit for first-wave expansion

    # ===========================================================================
    # KARDASHEV SCALE PROGRESSION - Optional advanced features
    # ===========================================================================

    config.civilization.enable_kardashev_progression = True
    config.civilization.kardashev_advancement_rate = 0.001  # 1 type per Gyr
    config.civilization.kardashev_type_1_time_myr = 1.0  # Fast tech growth initially

    # ===========================================================================
    # SIMULATION PARAMETERS
    # ===========================================================================

    # Cosmic timescales
    config.simulation.simulation_duration_gyr = 10.0  # 10 billion years
    # This covers most of galaxy history since star formation peaked

    config.simulation.time_step_myr = 10.0  # 10 million years per step
    # Good balance: captures civilization dynamics without excessive computation
    # Total steps: 10 Gyr / 10 Myr = 1,000 steps

    # Stellar motion (keep disabled for stability)
    config.simulation.enable_stellar_motion = False
    # Static positions are excellent approximation for these timescales

    # Performance
    config.simulation.use_numba = True  # Enable JIT compilation if available
    config.simulation.parallel_processing = True

    # Output
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 500.0  # Every 500 Myr
    # This gives 20 snapshots over 10 Gyr for analyzing evolution

    config.simulation.output_directory = "output"

    return config


def run_realistic_simulation():
    """Run the realistic simulation and analyze results."""
    print("=" * 80)
    print("REALISTIC GALACTIC CIVILIZATION SIMULATION")
    print("=" * 80)
    print("\nBased on:")
    print("  - Milky Way galaxy structure")
    print("  - Conservative Drake equation estimates")
    print("  - Observed astrophysical hazard rates")
    print("  - Sub-light-speed expansion constraints")

    # Create configuration
    config = create_realistic_config()

    print("\n" + "=" * 80)
    print("CONFIGURATION SUMMARY")
    print("=" * 80)

    print(f"\nGalaxy Structure:")
    print(f"  Total stars: {config.galaxy.total_stars:,}")
    print(f"  Bulge fraction: {config.galaxy.bulge_fraction:.1%}")
    print(f"  Metallicity gradient: {config.galaxy.metallicity_gradient_dex_per_kpc:+.3f} dex/kpc")
    print(f"  Age gradient: {config.galaxy.central_mean_age_gyr} → {config.galaxy.outer_mean_age_gyr} Gyr")

    print(f"\nDrake Equation (per habitable star):")
    print(f"  P(life): {config.civilization.fraction_develop_life:.1%}")
    print(f"  P(intelligence | life): {config.civilization.fraction_develop_intelligence:.1%}")
    print(f"  P(technology | intelligence): {config.civilization.fraction_develop_technology:.1%}")
    print(f"  Combined P(civilization): {config.civilization.fraction_develop_life * config.civilization.fraction_develop_intelligence * config.civilization.fraction_develop_technology:.3%}")

    print(f"\nCivilization Dynamics:")
    print(f"  Mean lifetime: {config.civilization.mean_civilization_lifetime_myr} Myr")
    print(f"  Self-destruction risk: {config.civilization.self_destruction_probability_per_myr:.1%} per Myr")
    print(f"  Expansion speed: {config.civilization.expansion_velocity_c * 100:.1f}% of light speed")

    print(f"\nSimulation Parameters:")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Time step: {config.simulation.time_step_myr} Myr")
    print(f"  Total steps: {int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.time_step_myr):,}")
    print(f"  Snapshots: {int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.snapshot_interval_myr)}")

    # Initialize and run simulation
    print("\n" + "=" * 80)
    print("RUNNING SIMULATION")
    print("=" * 80)

    sim = GalaxySimulation(config, seed=42)
    sim.initialize()

    print(f"\nGalaxy initialized:")
    print(f"  Bulge stars: {np.sum(sim.galaxy.component_type == 0):,}")
    print(f"  Disk stars: {np.sum(sim.galaxy.component_type == 1):,}")
    print(f"  Habitable stars: {len(sim.habitable_star_indices):,} ({100*len(sim.habitable_star_indices)/config.galaxy.total_stars:.2f}%)")

    # Run simulation
    sim.run(verbose=True)

    # Analyze results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    total_civs = len(sim.civilizations)
    active_civs = sum(c.is_active for c in sim.civilizations)

    print(f"\nCivilization Statistics:")
    print(f"  Total emerged: {total_civs}")
    print(f"  Currently active: {active_civs}")
    print(f"  Extinct: {total_civs - active_civs}")

    if total_civs == 0:
        print("\n⚠️  No civilizations emerged!")
        print("This is actually a possible outcome with conservative Drake parameters.")
        print("Try increasing f_life, f_intel, or f_tech for more civilizations.")
        return sim

    # Spatial distribution
    print(f"\nSpatial Distribution:")
    civ_radii = []
    for civ in sim.civilizations:
        pos = sim.galaxy.positions[civ.parent_star_idx]
        r = np.sqrt(pos[0]**2 + pos[1]**2)
        civ_radii.append(r)

    civ_radii = np.array(civ_radii)

    print(f"  Mean radius: {civ_radii.mean():.2f} kpc")
    print(f"  Median radius: {np.median(civ_radii):.2f} kpc")
    print(f"  Range: {civ_radii.min():.2f} - {civ_radii.max():.2f} kpc")

    # Galactic Habitable Zone analysis
    in_ghz = np.sum((civ_radii >= 6) & (civ_radii <= 10))
    print(f"\n  In Galactic Habitable Zone (6-10 kpc): {in_ghz}/{total_civs} ({100*in_ghz/total_civs:.1f}%)")

    # Component distribution
    n_bulge = sum(sim.galaxy.component_type[c.parent_star_idx] == 0 for c in sim.civilizations)
    n_disk = total_civs - n_bulge
    print(f"  Bulge: {n_bulge} ({100*n_bulge/total_civs:.1f}%)")
    print(f"  Disk: {n_disk} ({100*n_disk/total_civs:.1f}%)")

    # Extinction analysis
    print(f"\nExtinction Causes:")
    death_causes = {}
    for civ in sim.civilizations:
        if not civ.is_active and hasattr(civ, 'death_cause'):
            cause = civ.death_cause
            death_causes[cause] = death_causes.get(cause, 0) + 1

    for cause, count in sorted(death_causes.items(), key=lambda x: x[1], reverse=True):
        pct = 100 * count / (total_civs - active_civs) if total_civs > active_civs else 0
        print(f"  {cause}: {count} ({pct:.1f}%)")

    # Longevity statistics
    if total_civs > 0:
        lifetimes = []
        for civ in sim.civilizations:
            if not civ.is_active:
                lifetime = civ.death_time_myr - civ.birth_time_myr
                lifetimes.append(lifetime)

        if lifetimes:
            print(f"\nCivilization Lifetimes:")
            print(f"  Mean: {np.mean(lifetimes):.2f} Myr")
            print(f"  Median: {np.median(lifetimes):.2f} Myr")
            print(f"  Max: {np.max(lifetimes):.2f} Myr")

    # Timeline analysis
    if len(sim.snapshots) > 0:
        print(f"\nTemporal Evolution:")
        max_active = max(s.active_civilizations for s in sim.snapshots)
        max_active_time = [s.time_myr for s in sim.snapshots if s.active_civilizations == max_active][0]
        print(f"  Peak simultaneous civilizations: {max_active} at t={max_active_time/1000:.2f} Gyr")

    # Create visualization
    print("\n" + "=" * 80)
    print("CREATING VISUALIZATIONS")
    print("=" * 80)

    viz = GalaxyVisualizer()

    # Main galaxy view
    fig = plt.figure(figsize=(16, 12))

    # Galaxy map with civilizations
    ax1 = fig.add_subplot(2, 3, 1)

    # Plot stars
    bulge_mask = sim.galaxy.component_type == 0
    disk_mask = sim.galaxy.component_type == 1

    ax1.scatter(sim.galaxy.positions[disk_mask, 0], sim.galaxy.positions[disk_mask, 1],
               s=0.05, alpha=0.1, color='lightblue', label='Disk')
    ax1.scatter(sim.galaxy.positions[bulge_mask, 0], sim.galaxy.positions[bulge_mask, 1],
               s=0.1, alpha=0.2, color='orange', label='Bulge')

    # Plot civilizations
    active_idx = [c.parent_star_idx for c in sim.civilizations if c.is_active]
    extinct_idx = [c.parent_star_idx for c in sim.civilizations if not c.is_active]

    if extinct_idx:
        extinct_pos = sim.galaxy.positions[extinct_idx]
        ax1.scatter(extinct_pos[:, 0], extinct_pos[:, 1],
                   s=40, alpha=0.6, color='red', marker='x', label=f'Extinct ({len(extinct_idx)})')

    if active_idx:
        active_pos = sim.galaxy.positions[active_idx]
        ax1.scatter(active_pos[:, 0], active_pos[:, 1],
                   s=100, alpha=0.9, color='cyan', marker='*',
                   edgecolors='white', linewidths=1, label=f'Active ({len(active_idx)})')

    # Mark GHZ
    theta = np.linspace(0, 2*np.pi, 100)
    ax1.plot(6*np.cos(theta), 6*np.sin(theta), 'g--', linewidth=2, alpha=0.6)
    ax1.plot(10*np.cos(theta), 10*np.sin(theta), 'g--', linewidth=2, alpha=0.6)
    ax1.text(8, 0, 'GHZ', color='green', fontsize=12, weight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax1.set_xlabel('X (kpc)')
    ax1.set_ylabel('Y (kpc)')
    ax1.set_title(f'Galaxy at t={config.simulation.simulation_duration_gyr} Gyr')
    ax1.set_aspect('equal')
    ax1.legend(loc='upper right', fontsize=9)
    ax1.set_facecolor('black')
    ax1.set_xlim(-15, 15)
    ax1.set_ylim(-15, 15)
    ax1.grid(True, alpha=0.2, color='white')

    # Radial distribution
    ax2 = fig.add_subplot(2, 3, 2)
    if len(civ_radii) > 0:
        ax2.hist(civ_radii, bins=30, alpha=0.7, color='cyan', edgecolor='black')
        ax2.axvspan(6, 10, alpha=0.2, color='green', label='GHZ')
        ax2.axvline(8, color='yellow', linestyle=':', linewidth=2, label='Solar radius')
        ax2.set_xlabel('Galactocentric Radius (kpc)')
        ax2.set_ylabel('Number of Civilizations')
        ax2.set_title('Radial Distribution')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

    # Component distribution
    ax3 = fig.add_subplot(2, 3, 3)
    if total_civs > 0:
        labels = ['Bulge', 'Disk']
        sizes = [n_bulge, n_disk]
        colors = ['orange', 'lightblue']
        ax3.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
        ax3.set_title('Civilizations by Component')

    # Timeline
    ax4 = fig.add_subplot(2, 3, 4)
    if len(sim.snapshots) > 0:
        times = [s.time_myr / 1000 for s in sim.snapshots]
        active_counts = [s.active_civilizations for s in sim.snapshots]
        total_counts = [s.total_civilizations_ever for s in sim.snapshots]

        ax4.plot(times, active_counts, 'cyan', linewidth=2, marker='o', markersize=4, label='Active')
        ax4.plot(times, total_counts, 'orange', linewidth=2, marker='s', markersize=4, label='Total')
        ax4.fill_between(times, active_counts, alpha=0.3, color='cyan')
        ax4.set_xlabel('Time (Gyr)')
        ax4.set_ylabel('Number of Civilizations')
        ax4.set_title('Evolution Over Time')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

    # Extinction causes
    ax5 = fig.add_subplot(2, 3, 5)
    if death_causes:
        causes = list(death_causes.keys())
        counts = list(death_causes.values())
        colors_death = plt.cm.Set3(np.linspace(0, 1, len(causes)))

        bars = ax5.barh(causes, counts, color=colors_death, edgecolor='black')
        ax5.set_xlabel('Number of Civilizations')
        ax5.set_title('Extinction Causes')
        ax5.grid(True, alpha=0.3, axis='x')

        # Add counts to bars
        for i, (cause, count) in enumerate(zip(causes, counts)):
            ax5.text(count + 0.5, i, str(count), va='center')

    # Lifetime distribution
    ax6 = fig.add_subplot(2, 3, 6)
    if lifetimes:
        ax6.hist(lifetimes, bins=20, alpha=0.7, color='purple', edgecolor='black')
        ax6.axvline(config.civilization.mean_civilization_lifetime_myr,
                   color='red', linestyle='--', linewidth=2, label='Mean expected')
        ax6.set_xlabel('Lifetime (Myr)')
        ax6.set_ylabel('Number of Civilizations')
        ax6.set_title('Civilization Lifetimes')
        ax6.legend()
        ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('output/realistic_simulation.png', dpi=150, facecolor='black')
    print("   Saved: output/realistic_simulation.png")
    plt.close()

    # Summary
    print("\n" + "=" * 80)
    print("SIMULATION COMPLETE")
    print("=" * 80)

    print(f"\n✓ Simulated {config.simulation.simulation_duration_gyr} Gyr of galactic history")
    print(f"✓ {total_civs} civilizations emerged")
    if total_civs > 0:
        print(f"✓ {100*in_ghz/total_civs:.1f}% emerged in Galactic Habitable Zone")
        print(f"✓ Peak of {max_active} civilizations existed simultaneously")
    print(f"✓ Visualization saved to output/realistic_simulation.png")

    print("\nKey Findings:")
    if total_civs == 0:
        print("  • No civilizations emerged (Fermi Paradox: rare life hypothesis)")
    elif active_civs == 0:
        print("  • All civilizations went extinct (Great Filter hypothesis)")
    elif active_civs < 5:
        print(f"  • Very few civilizations survive ({active_civs} active)")
        print("    → Supports 'rare civilization' resolution to Fermi Paradox")
    else:
        print(f"  • Multiple civilizations coexist ({active_civs} active)")
        print("    → Galactic Habitable Zone provides refuge from hazards")

    if death_causes:
        top_cause = max(death_causes, key=death_causes.get)
        print(f"  • Primary extinction cause: {top_cause}")

    return sim


if __name__ == '__main__':
    import os
    os.makedirs('output', exist_ok=True)

    sim = run_realistic_simulation()
