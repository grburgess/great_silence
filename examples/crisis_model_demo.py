"""
GREAT FILTER DEMONSTRATION

This script showcases the Kardashev-dependent self-destruction model in action.
It runs a full galactic simulation and analyzes where civilizations fail on their
technological journey - demonstrating the "Great Filter" hypothesis.

Key Questions Explored:
1. At what technological level do most civilizations die?
2. Which crises are the deadliest?
3. How rare are Type II and Type III civilizations?
4. Does this explain the Fermi Paradox?
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from great_silence import GalaxySimulation, SimulationConfig


def create_demo_config():
    """Create configuration optimized for demonstrating crisis model."""
    config = SimulationConfig()

    # Galaxy structure - medium size for reasonable runtime
    config.galaxy.total_stars = 100_000
    config.galaxy.include_bulge = True
    config.galaxy.bulge_fraction = 0.2
    config.galaxy.scale_length_kpc = 3.5
    config.galaxy.disk_radius_kpc = 15.0
    config.galaxy.rotation_velocity_km_s = 220.0

    # More optimistic Drake parameters to get enough civilizations to analyze
    config.civilization.fraction_develop_life = 0.3  # 30% of habitable stars
    config.civilization.fraction_develop_intelligence = 0.1  # 10% develop intelligence
    config.civilization.fraction_develop_technology = 0.5  # 50% develop technology
    # Combined: 0.3 * 0.1 * 0.5 = 1.5% per habitable star (fairly optimistic)

    # Crisis-based self-destruction model (THE KEY FEATURE)
    config.civilization.self_destruction_model_type = "kardashev_dependent"
    config.civilization.baseline_self_destruction_rate = 0.01  # Low baseline
    config.civilization.baseline_risk_scaling = 0.05

    # Crisis amplitudes (default values show standard Great Filter)
    config.civilization.crisis_nuclear_age_amplitude = 0.15
    config.civilization.crisis_planetary_unification_amplitude = 0.12
    config.civilization.crisis_ai_transition_amplitude = 0.20  # Strongest
    config.civilization.crisis_interplanetary_amplitude = 0.10
    config.civilization.crisis_stellar_engineering_amplitude = 0.08
    config.civilization.crisis_relativistic_weapons_amplitude = 0.06

    # Disable old age extinction for this demo (focus on crisis deaths)
    config.civilization.mean_civilization_lifetime_myr = 1000.0  # Very long

    # Kardashev advancement
    config.civilization.initial_kardashev_scale_mean = 0.7  # Start at modern Earth
    config.civilization.initial_kardashev_scale_stddev = 0.05
    config.civilization.kardashev_advancement_rate_mean = 0.015  # per Myr
    config.civilization.kardashev_advancement_rate_stddev = 0.005
    config.civilization.kardashev_breakthrough_probability_per_myr = 0.01
    config.civilization.kardashev_breakthrough_boost = 0.05
    config.civilization.kardashev_max_scale = 3.0

    # Simulation parameters - longer to see more advancement
    config.simulation.simulation_duration_gyr = 5.0  # 5 Gyr
    config.simulation.time_step_myr = 5.0  # 5 Myr timesteps
    config.simulation.enable_stellar_motion = False  # Static positions
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 250.0  # Every 250 Myr

    return config


def analyze_crisis_deaths(sim):
    """Analyze which crises killed the most civilizations."""

    # Extract Kardashev scales at death
    kardashev_at_death = []
    death_causes = {}

    for civ in sim.civilizations:
        if not civ.is_active:
            kardashev_at_death.append(civ.kardashev_scale)
            cause = civ.death_cause or "unknown"
            death_causes[cause] = death_causes.get(cause, 0) + 1

    if len(kardashev_at_death) == 0:
        return None, death_causes

    kardashev_at_death = np.array(kardashev_at_death)

    # Define crisis regions
    crisis_regions = {
        "Nuclear Age (0.65-0.80)": (0.65, 0.80),
        "Planetary Unif. (0.80-0.95)": (0.80, 0.95),
        "AI Transition (0.95-1.15)": (0.95, 1.15),
        "Interplanetary (1.15-1.40)": (1.15, 1.40),
        "Stellar Eng. (1.60-2.00)": (1.60, 2.00),
        "Relativistic (2.30-2.70)": (2.30, 2.70),
    }

    crisis_deaths = {}
    for name, (kmin, kmax) in crisis_regions.items():
        count = np.sum((kardashev_at_death >= kmin) & (kardashev_at_death < kmax))
        crisis_deaths[name] = count

    return kardashev_at_death, death_causes, crisis_deaths


def create_visualization(sim, kardashev_at_death, death_causes, crisis_deaths):
    """Create comprehensive visualization of results."""

    fig = plt.figure(figsize=(20, 12))
    fig.patch.set_facecolor('#0a0a0a')
    gs = GridSpec(3, 4, figure=fig, hspace=0.3, wspace=0.3)

    # Title
    fig.suptitle('THE GREAT FILTER: Kardashev-Dependent Civilization Extinction',
                 fontsize=20, fontweight='bold', color='cyan', y=0.98)

    # === Panel 1: Kardashev Scale at Death Distribution ===
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.set_facecolor('#0a0a0a')

    if kardashev_at_death is not None and len(kardashev_at_death) > 0:
        bins = np.linspace(0.5, 3.0, 50)
        counts, edges, patches = ax1.hist(kardashev_at_death, bins=bins,
                                         alpha=0.8, color='red', edgecolor='white')

        # Mark crisis peaks
        crisis_centers = [0.72, 0.85, 1.05, 1.25, 1.80, 2.50]
        crisis_names = ['Nuclear\nAge', 'Planetary\nUnif.', 'AI\nTransition',
                       'Inter-\nplanetary', 'Stellar\nEng.', 'Relativistic\nWeapons']

        for k, name in zip(crisis_centers, crisis_names):
            ax1.axvline(k, color='yellow', linestyle=':', alpha=0.7, linewidth=2)
            ax1.text(k, ax1.get_ylim()[1] * 0.95, name,
                    rotation=0, fontsize=8, ha='center', va='top',
                    color='yellow', fontweight='bold',
                    bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

        # Mark Kardashev types
        ax1.axvline(1.0, color='lime', linestyle='--', alpha=0.5, linewidth=1.5, label='Type I')
        ax1.axvline(2.0, color='orange', linestyle='--', alpha=0.5, linewidth=1.5, label='Type II')
        ax1.axvline(3.0, color='red', linestyle='--', alpha=0.5, linewidth=1.5, label='Type III')

    ax1.set_xlabel('Kardashev Scale at Death', fontsize=12, color='white', fontweight='bold')
    ax1.set_ylabel('Number of Civilizations', fontsize=12, color='white', fontweight='bold')
    ax1.set_title('WHERE DO CIVILIZATIONS DIE?', fontsize=14, color='cyan', fontweight='bold')
    ax1.legend(loc='upper right', facecolor='black', edgecolor='cyan', labelcolor='white')
    ax1.grid(True, alpha=0.3, color='gray')
    ax1.tick_params(colors='white')
    for spine in ax1.spines.values():
        spine.set_color('cyan')
        spine.set_linewidth(2)

    # === Panel 2: Crisis Death Count ===
    ax2 = fig.add_subplot(gs[0, 2:])
    ax2.set_facecolor('#0a0a0a')

    if crisis_deaths:
        names = list(crisis_deaths.keys())
        counts = list(crisis_deaths.values())
        colors = ['#ff4444', '#ff8844', '#ffcc44', '#44ff44', '#4444ff', '#ff44ff']

        bars = ax2.barh(names, counts, color=colors, edgecolor='white', linewidth=1.5)

        # Add count labels
        for i, (bar, count) in enumerate(zip(bars, counts)):
            if count > 0:
                ax2.text(count + max(counts) * 0.02, i, str(count),
                        va='center', ha='left', color='white', fontweight='bold', fontsize=10)

    ax2.set_xlabel('Number of Deaths', fontsize=12, color='white', fontweight='bold')
    ax2.set_title('DEADLIEST CRISES', fontsize=14, color='cyan', fontweight='bold')
    ax2.grid(True, alpha=0.3, color='gray', axis='x')
    ax2.tick_params(colors='white')
    for spine in ax2.spines.values():
        spine.set_color('cyan')
        spine.set_linewidth(2)

    # === Panel 3: Civilization Timeline ===
    ax3 = fig.add_subplot(gs[1, :2])
    ax3.set_facecolor('#0a0a0a')

    times = [s.time_myr / 1000.0 for s in sim.snapshots]
    active_count = [s.active_civilizations for s in sim.snapshots]
    total_emerged = [s.total_civilizations_ever for s in sim.snapshots]

    ax3.plot(times, total_emerged, 'cyan', linewidth=2.5, label='Total Emerged', alpha=0.9)
    ax3.plot(times, active_count, 'lime', linewidth=2.5, label='Active', alpha=0.9)
    ax3.fill_between(times, 0, total_emerged, color='cyan', alpha=0.2)
    ax3.fill_between(times, 0, active_count, color='lime', alpha=0.3)

    ax3.set_xlabel('Time [Gyr]', fontsize=12, color='white', fontweight='bold')
    ax3.set_ylabel('Number of Civilizations', fontsize=12, color='white', fontweight='bold')
    ax3.set_title('CIVILIZATION EVOLUTION OVER TIME', fontsize=14, color='cyan', fontweight='bold')
    ax3.legend(loc='upper left', facecolor='black', edgecolor='cyan', labelcolor='white', fontsize=11)
    ax3.grid(True, alpha=0.3, color='gray')
    ax3.tick_params(colors='white')
    for spine in ax3.spines.values():
        spine.set_color('cyan')
        spine.set_linewidth(2)

    # === Panel 4: Kardashev Distribution of All Civilizations ===
    ax4 = fig.add_subplot(gs[1, 2:])
    ax4.set_facecolor('#0a0a0a')

    all_kardashev = [civ.kardashev_scale for civ in sim.civilizations]

    if len(all_kardashev) > 0:
        bins = np.linspace(0.5, 3.0, 40)
        ax4.hist(all_kardashev, bins=bins, alpha=0.7, color='orange',
                edgecolor='white', linewidth=1.5)

        # Mark types
        ax4.axvline(1.0, color='lime', linestyle='--', alpha=0.7, linewidth=2)
        ax4.axvline(2.0, color='orange', linestyle='--', alpha=0.7, linewidth=2)
        ax4.axvline(3.0, color='red', linestyle='--', alpha=0.7, linewidth=2)

    ax4.set_xlabel('Final Kardashev Scale', fontsize=12, color='white', fontweight='bold')
    ax4.set_ylabel('Number of Civilizations', fontsize=12, color='white', fontweight='bold')
    ax4.set_title('FINAL TECHNOLOGY LEVELS', fontsize=14, color='cyan', fontweight='bold')
    ax4.grid(True, alpha=0.3, color='gray')
    ax4.tick_params(colors='white')
    for spine in ax4.spines.values():
        spine.set_color('cyan')
        spine.set_linewidth(2)

    # === Panel 5: Statistics Summary ===
    ax5 = fig.add_subplot(gs[2, :2])
    ax5.set_facecolor('#0a0a0a')
    ax5.axis('off')

    total_civs = len(sim.civilizations)
    active_civs = sum(1 for c in sim.civilizations if c.is_active)
    extinct_civs = total_civs - active_civs

    # Count by Kardashev type
    type_0 = sum(1 for c in sim.civilizations if c.kardashev_scale < 1.0)
    type_1 = sum(1 for c in sim.civilizations if 1.0 <= c.kardashev_scale < 2.0)
    type_2 = sum(1 for c in sim.civilizations if 2.0 <= c.kardashev_scale < 3.0)
    type_3 = sum(1 for c in sim.civilizations if c.kardashev_scale >= 3.0)

    stats_text = f"""
    ╔══════════════════════════════════════════════════╗
    ║            SIMULATION STATISTICS                  ║
    ╚══════════════════════════════════════════════════╝

    Galaxy Parameters:
      • Total Stars: {sim.config.galaxy.total_stars:,}
      • Habitable Stars: {len(sim.habitable_star_indices):,}

    Civilization Emergence:
      • Total Emerged: {total_civs}
      • Currently Active: {active_civs}
      • Extinct: {extinct_civs} ({100*extinct_civs/max(total_civs,1):.1f}%)

    Kardashev Scale Distribution:
      • Type 0 (K<1.0):    {type_0:3d} ({100*type_0/max(total_civs,1):5.1f}%)
      • Type I (K=1.0-2.0): {type_1:3d} ({100*type_1/max(total_civs,1):5.1f}%)
      • Type II (K=2.0-3.0): {type_2:3d} ({100*type_2/max(total_civs,1):5.1f}%)
      • Type III (K≥3.0):   {type_3:3d} ({100*type_3/max(total_civs,1):5.1f}%)

    Great Filter Analysis:
      • Survival to Type I: {100*(type_1+type_2+type_3)/max(total_civs,1):.2f}%
      • Survival to Type II: {100*(type_2+type_3)/max(total_civs,1):.2f}%
      • Survival to Type III: {100*type_3/max(total_civs,1):.2f}%
    """

    ax5.text(0.05, 0.95, stats_text, transform=ax5.transAxes,
            fontsize=11, verticalalignment='top', color='white',
            family='monospace',
            bbox=dict(boxstyle='round', facecolor='#1a1a1a',
                     edgecolor='cyan', linewidth=2, alpha=0.9))

    # === Panel 6: Fermi Paradox Interpretation ===
    ax6 = fig.add_subplot(gs[2, 2:])
    ax6.set_facecolor('#0a0a0a')
    ax6.axis('off')

    # Determine dominant crisis
    if crisis_deaths:
        deadliest_crisis = max(crisis_deaths.items(), key=lambda x: x[1])[0]
    else:
        deadliest_crisis = "Unknown"

    survival_to_type_2 = 100 * (type_2 + type_3) / max(total_civs, 1)

    if survival_to_type_2 < 1.0:
        filter_strength = "VERY STRONG"
        color = '#ff4444'
    elif survival_to_type_2 < 5.0:
        filter_strength = "STRONG"
        color = '#ffaa44'
    else:
        filter_strength = "MODERATE"
        color = '#44ff44'

    interpretation = f"""
    ╔═══════════════════════════════════════════════╗
    ║        FERMI PARADOX INTERPRETATION            ║
    ╚═══════════════════════════════════════════════╝

    KEY FINDINGS:

    1. THE GREAT FILTER IS {filter_strength}
       Only {survival_to_type_2:.2f}% of civilizations reach
       Type II (detectable across galaxy)

    2. DEADLIEST CRISIS: {deadliest_crisis}
       Most civilizations die at this stage

    3. WHY THE SILENCE?
       {"Galaxy-spanning civilizations are" if type_3 == 0 else "Advanced civilizations are"}
       {"EXTREMELY RARE" if type_3 == 0 else "VERY RARE"}
       {f"({type_3} Type III in this simulation)" if type_3 > 0 else "(ZERO Type III civilizations emerged)"}

    4. IMPLICATIONS:
       • Multiple crisis peaks compound
       • AI transition appears critical
       • Most die before Type I
       • Empty galaxy is expected outcome

    CONCLUSION: The crisis-based extinction model
    successfully explains the Fermi Paradox without
    requiring rare Earth or rare life hypotheses.
    """

    ax6.text(0.05, 0.95, interpretation, transform=ax6.transAxes,
            fontsize=10, verticalalignment='top', color='yellow',
            family='monospace', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#1a0000',
                     edgecolor=color, linewidth=3, alpha=0.95))

    plt.savefig('output/great_filter_demo.png', dpi=150,
               facecolor='black', edgecolor='none', bbox_inches='tight')
    print("\n✓ Saved: output/great_filter_demo.png")
    plt.close()


def run_demo():
    """Run the complete Great Filter demonstration."""

    print("=" * 80)
    print(" " * 20 + "THE GREAT FILTER DEMONSTRATION")
    print("=" * 80)
    print()
    print("This simulation explores the Kardashev-dependent self-destruction model,")
    print("showing where civilizations fail on their journey to galactic dominance.")
    print()

    # Create configuration
    print("Creating simulation configuration...")
    config = create_demo_config()

    print(f"\nSimulation Parameters:")
    print(f"  Galaxy: {config.galaxy.total_stars:,} stars")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Time step: {config.simulation.time_step_myr} Myr")
    print(f"  Total steps: {int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.time_step_myr)}")

    print(f"\nDrake Equation:")
    p_life = config.civilization.fraction_develop_life
    p_intel = config.civilization.fraction_develop_intelligence
    p_tech = config.civilization.fraction_develop_technology
    p_combined = p_life * p_intel * p_tech
    print(f"  P(life) = {100*p_life:.1f}%")
    print(f"  P(intelligence | life) = {100*p_intel:.1f}%")
    print(f"  P(technology | intelligence) = {100*p_tech:.1f}%")
    print(f"  Combined P(civilization) = {100*p_combined:.2f}%")

    print(f"\nExtinction Model:")
    print(f"  Type: {config.civilization.self_destruction_model_type}")
    print(f"  Crisis Amplitudes:")
    print(f"    Nuclear Age: {config.civilization.crisis_nuclear_age_amplitude:.2f}")
    print(f"    AI Transition: {config.civilization.crisis_ai_transition_amplitude:.2f} ← STRONGEST")
    print(f"    Interplanetary: {config.civilization.crisis_interplanetary_amplitude:.2f}")

    # Initialize and run simulation
    print("\n" + "=" * 80)
    print("RUNNING SIMULATION")
    print("=" * 80)

    sim = GalaxySimulation(config, seed=42)
    sim.initialize()

    print(f"\nGalaxy initialized:")
    print(f"  Habitable stars: {len(sim.habitable_star_indices):,}")
    print(f"  Expected civilizations: ~{int(len(sim.habitable_star_indices) * p_combined)}")

    print("\nSimulating galactic history...")
    sim.run()

    # Analyze results
    print("\n" + "=" * 80)
    print("ANALYZING RESULTS")
    print("=" * 80)

    total_civs = len(sim.civilizations)
    active_civs = sum(1 for c in sim.civilizations if c.is_active)

    print(f"\nCivilization Emergence:")
    print(f"  Total emerged: {total_civs}")
    print(f"  Currently active: {active_civs}")
    print(f"  Extinct: {total_civs - active_civs}")

    if total_civs > 0:
        kardashev_at_death, death_causes, crisis_deaths = analyze_crisis_deaths(sim)

        print(f"\nExtinction Causes:")
        for cause, count in sorted(death_causes.items(), key=lambda x: x[1], reverse=True):
            pct = 100 * count / (total_civs - active_civs) if total_civs > active_civs else 0
            print(f"  {cause}: {count} ({pct:.1f}%)")

        print(f"\nCrisis Analysis:")
        if crisis_deaths:
            for crisis_name, count in crisis_deaths.items():
                if count > 0:
                    print(f"  {crisis_name}: {count} deaths")

        # Kardashev statistics
        all_kardashev = [c.kardashev_scale for c in sim.civilizations]
        type_1_plus = sum(1 for k in all_kardashev if k >= 1.0)
        type_2_plus = sum(1 for k in all_kardashev if k >= 2.0)
        type_3_plus = sum(1 for k in all_kardashev if k >= 3.0)

        print(f"\nKardashev Scale Achievement:")
        print(f"  Reached Type I: {type_1_plus} ({100*type_1_plus/total_civs:.1f}%)")
        print(f"  Reached Type II: {type_2_plus} ({100*type_2_plus/total_civs:.1f}%)")
        print(f"  Reached Type III: {type_3_plus} ({100*type_3_plus/total_civs:.1f}%)")

        if kardashev_at_death is not None and len(kardashev_at_death) > 0:
            print(f"\nWhere Civilizations Died:")
            print(f"  Mean Kardashev at death: {np.mean(kardashev_at_death):.2f}")
            print(f"  Median Kardashev at death: {np.median(kardashev_at_death):.2f}")
            print(f"  Range: {np.min(kardashev_at_death):.2f} - {np.max(kardashev_at_death):.2f}")

        # Create visualization
        print("\n" + "=" * 80)
        print("CREATING VISUALIZATION")
        print("=" * 80)
        create_visualization(sim, kardashev_at_death, death_causes, crisis_deaths)

        print("\n" + "=" * 80)
        print("FERMI PARADOX INTERPRETATION")
        print("=" * 80)

        if type_2_plus == 0:
            print("\n⚠️  CRITICAL FINDING:")
            print("    ZERO civilizations reached Type II (Dyson sphere level)")
            print("    This explains why SETI and JWST find no technosignatures!")
        elif type_2_plus < 5:
            print("\n⚠️  SIGNIFICANT FINDING:")
            print(f"    Only {type_2_plus} civilization(s) reached Type II")
            print("    Galaxy-spanning civilizations are extremely rare!")

        if type_3_plus == 0:
            print("\n⚠️  GREAT SILENCE EXPLAINED:")
            print("    ZERO civilizations reached Type III (galactic level)")
            print("    The Great Filter prevents galactic colonization!")

        print("\nThe crisis-based extinction model successfully explains")
        print("the Fermi Paradox: civilizations fail at specific technological")
        print("transitions before they can expand across the galaxy.")

    else:
        print("\n⚠️  WARNING: No civilizations emerged!")
        print("Try adjusting Drake equation parameters for more optimistic simulation.")

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print(f"\n✓ Results saved to: output/great_filter_demo.png")
    print("✓ Simulation complete!")


if __name__ == '__main__':
    import os
    os.makedirs('output', exist_ok=True)
    run_demo()
