"""
Demonstration of Kardashev-dependent self-destruction model.

This script visualizes the hazard function and runs comparative simulations
to show how different crisis scenarios affect civilization survival.
"""

import numpy as np
import matplotlib.pyplot as plt
from great_silence import SimulationConfig
from great_silence.civilization.extinction import ExtinctionModel, CrisisPeak


def plot_hazard_landscape():
    """
    Visualize the self-destruction hazard function across Kardashev scales.
    """
    # Create default extinction model
    config = SimulationConfig()

    # Build crisis peaks from config
    crisis_peaks = [
        CrisisPeak(
            name="nuclear_age",
            kardashev_center=0.72,
            width=0.05,
            amplitude=config.civilization.crisis_nuclear_age_amplitude,
            enabled=True
        ),
        CrisisPeak(
            name="planetary_unification",
            kardashev_center=0.85,
            width=0.08,
            amplitude=config.civilization.crisis_planetary_unification_amplitude,
            enabled=True
        ),
        CrisisPeak(
            name="ai_transition",
            kardashev_center=1.05,
            width=0.10,
            amplitude=config.civilization.crisis_ai_transition_amplitude,
            enabled=True
        ),
        CrisisPeak(
            name="interplanetary_expansion",
            kardashev_center=1.25,
            width=0.15,
            amplitude=config.civilization.crisis_interplanetary_amplitude,
            enabled=True
        ),
        CrisisPeak(
            name="stellar_engineering",
            kardashev_center=1.80,
            width=0.20,
            amplitude=config.civilization.crisis_stellar_engineering_amplitude,
            enabled=True
        ),
        CrisisPeak(
            name="relativistic_weapons",
            kardashev_center=2.50,
            width=0.25,
            amplitude=config.civilization.crisis_relativistic_weapons_amplitude,
            enabled=True
        ),
    ]

    extinction_model = ExtinctionModel(
        self_destruction_rate=config.civilization.self_destruction_probability_per_myr,
        mean_lifetime_myr=config.civilization.mean_civilization_lifetime_myr,
        model_type="kardashev_dependent",
        baseline_rate=config.civilization.baseline_self_destruction_rate,
        baseline_scaling=config.civilization.baseline_risk_scaling,
        crisis_peaks=crisis_peaks
    )

    # Calculate hazard rates
    k_values = np.linspace(0.5, 3.0, 1000)
    lambda_values = np.array([
        extinction_model.calculate_kardashev_hazard_rate(k) for k in k_values
    ])

    # Calculate survival probabilities (assuming 1 Myr at each K level)
    survival_1myr = np.exp(-lambda_values * 1.0)
    expected_lifetime = 1.0 / lambda_values  # in Myr

    # Create figure with subplots
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), facecolor='black')

    # --- Plot 1: Hazard Rate ---
    ax1 = axes[0]
    ax1.set_facecolor('black')

    # Plot hazard function
    ax1.plot(k_values, lambda_values, color='cyan', linewidth=2.5, label='Total hazard λ(K)')

    # Fill area under curve to emphasize danger zones
    ax1.fill_between(k_values, 0, lambda_values, alpha=0.3, color='cyan')

    # Mark crisis peaks
    crisis_colors = ['red', 'orange', 'darkred', 'orangered', 'coral', 'salmon']
    for i, crisis in enumerate(crisis_peaks):
        if crisis.enabled:
            ax1.axvline(
                crisis.kardashev_center,
                color=crisis_colors[i % len(crisis_colors)],
                linestyle='--',
                alpha=0.7,
                linewidth=1.5
            )
            # Add crisis labels
            y_pos = lambda_values.max() * (0.85 - (i % 3) * 0.1)
            ax1.text(
                crisis.kardashev_center + 0.02,
                y_pos,
                crisis.name.replace('_', ' ').title(),
                rotation=0,
                va='center',
                ha='left',
                color='white',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='black', edgecolor=crisis_colors[i % len(crisis_colors)], alpha=0.8)
            )

    # Mark Kardashev type boundaries
    ax1.axvline(1.0, color='yellow', linestyle=':', alpha=0.5, linewidth=2, label='Type I')
    ax1.axvline(2.0, color='yellow', linestyle=':', alpha=0.5, linewidth=2, label='Type II')
    ax1.axvline(3.0, color='yellow', linestyle=':', alpha=0.5, linewidth=2, label='Type III')

    # Mark modern Earth
    ax1.axvline(0.72, color='lime', linestyle='-', alpha=0.8, linewidth=2, label='Modern Earth (2024)')

    ax1.set_xlabel('Kardashev Scale', color='white', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Hazard Rate λ(K) [per Myr]', color='white', fontsize=13, fontweight='bold')
    ax1.set_title('Self-Destruction Hazard Landscape', color='white', fontsize=15, fontweight='bold')
    ax1.tick_params(colors='white', labelsize=11)
    ax1.legend(loc='upper right', facecolor='black', edgecolor='cyan', labelcolor='white', fontsize=10)
    ax1.grid(True, alpha=0.15, color='white', linestyle='-', linewidth=0.5)
    ax1.set_xlim(0.5, 3.0)

    # --- Plot 2: Expected Lifetime ---
    ax2 = axes[1]
    ax2.set_facecolor('black')

    # Plot expected lifetime (capped at 100 Myr for visualization)
    expected_lifetime_capped = np.minimum(expected_lifetime, 100.0)
    ax2.plot(k_values, expected_lifetime_capped, color='lime', linewidth=2.5, label='Expected Lifetime')
    ax2.fill_between(k_values, 0, expected_lifetime_capped, alpha=0.3, color='lime')

    # Mark crisis peaks
    for i, crisis in enumerate(crisis_peaks):
        if crisis.enabled:
            ax2.axvline(
                crisis.kardashev_center,
                color=crisis_colors[i % len(crisis_colors)],
                linestyle='--',
                alpha=0.4,
                linewidth=1.5
            )

    # Mark Kardashev boundaries
    ax2.axvline(1.0, color='yellow', linestyle=':', alpha=0.5, linewidth=2)
    ax2.axvline(2.0, color='yellow', linestyle=':', alpha=0.5, linewidth=2)
    ax2.axvline(3.0, color='yellow', linestyle=':', alpha=0.5, linewidth=2)
    ax2.axvline(0.72, color='lime', linestyle='-', alpha=0.8, linewidth=2)

    ax2.set_xlabel('Kardashev Scale', color='white', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Expected Survival Time [Myr]', color='white', fontsize=13, fontweight='bold')
    ax2.set_title('Expected Civilization Lifetime vs Technology Level', color='white', fontsize=15, fontweight='bold')
    ax2.tick_params(colors='white', labelsize=11)
    ax2.legend(loc='upper right', facecolor='black', edgecolor='lime', labelcolor='white', fontsize=10)
    ax2.grid(True, alpha=0.15, color='white', linestyle='-', linewidth=0.5)
    ax2.set_xlim(0.5, 3.0)
    ax2.set_ylim(0, 100)

    plt.tight_layout()

    # Save figure
    plt.savefig('/Users/jburgess/coding/projects/galaticbot/kardashev_hazard_landscape.png',
                dpi=150, facecolor='black', edgecolor='none')
    print("Hazard landscape saved to: /Users/jburgess/coding/projects/galaticbot/kardashev_hazard_landscape.png")

    plt.show()


def calculate_survival_statistics():
    """
    Calculate survival probabilities through various crisis scenarios.
    """
    config = SimulationConfig()

    # Build crisis peaks
    crisis_peaks = [
        CrisisPeak("nuclear_age", 0.72, 0.05, config.civilization.crisis_nuclear_age_amplitude, True),
        CrisisPeak("planetary_unification", 0.85, 0.08, config.civilization.crisis_planetary_unification_amplitude, True),
        CrisisPeak("ai_transition", 1.05, 0.10, config.civilization.crisis_ai_transition_amplitude, True),
        CrisisPeak("interplanetary_expansion", 1.25, 0.15, config.civilization.crisis_interplanetary_amplitude, True),
        CrisisPeak("stellar_engineering", 1.80, 0.20, config.civilization.crisis_stellar_engineering_amplitude, True),
        CrisisPeak("relativistic_weapons", 2.50, 0.25, config.civilization.crisis_relativistic_weapons_amplitude, True),
    ]

    extinction_model = ExtinctionModel(
        self_destruction_rate=config.civilization.self_destruction_probability_per_myr,
        mean_lifetime_myr=config.civilization.mean_civilization_lifetime_myr,
        model_type="kardashev_dependent",
        baseline_rate=config.civilization.baseline_self_destruction_rate,
        baseline_scaling=config.civilization.baseline_risk_scaling,
        crisis_peaks=crisis_peaks
    )

    print("\n" + "="*70)
    print("KARDASHEV CRISIS MODEL - SURVIVAL STATISTICS")
    print("="*70)

    # Key milestones
    milestones = [
        (0.70, "Pre-Nuclear (Early 20th Century)"),
        (0.72, "Nuclear Age Peak (Modern Earth)"),
        (0.85, "Planetary Unification Crisis"),
        (1.00, "Type I Civilization (Planetary Energy Mastery)"),
        (1.05, "AI Transition Peak (MOST DANGEROUS)"),
        (1.25, "Interplanetary Expansion Crisis"),
        (1.50, "Advanced Type I"),
        (1.80, "Stellar Engineering Crisis"),
        (2.00, "Type II Civilization (Stellar Energy Mastery)"),
        (2.50, "Relativistic Weapons Crisis"),
        (3.00, "Type III Civilization (Galactic Energy Mastery)")
    ]

    print("\nHazard Rates and Expected Lifetimes:")
    print("-" * 70)
    print(f"{'Kardashev':^12} | {'Description':^35} | {'λ [/Myr]':^10} | {'E[Life] [Myr]':^15}")
    print("-" * 70)

    for k, desc in milestones:
        lambda_k = extinction_model.calculate_kardashev_hazard_rate(k)
        expected_life = 1.0 / lambda_k
        print(f"{k:^12.2f} | {desc:<35} | {lambda_k:^10.4f} | {expected_life:^15.2f}")

    # Calculate cumulative survival probability through entire journey
    print("\n" + "="*70)
    print("SURVIVAL PROBABILITY THROUGH GREAT FILTER")
    print("="*70)

    # Simulate a civilization advancing from K=0.7 to K=3.0 at rate 0.01/Myr
    k_start = 0.7
    k_end = 3.0
    advancement_rate = 0.01  # per Myr

    total_time = (k_end - k_start) / advancement_rate  # 230 Myr
    dt = 0.1  # Myr time step
    num_steps = int(total_time / dt)

    k_trajectory = np.linspace(k_start, k_end, num_steps)

    # Calculate cumulative survival
    cumulative_survival = 1.0
    for k in k_trajectory:
        lambda_k = extinction_model.calculate_kardashev_hazard_rate(k)
        survival_this_step = np.exp(-lambda_k * dt)
        cumulative_survival *= survival_this_step

    print(f"\nAssuming steady advancement at {advancement_rate}/Myr:")
    print(f"  Journey duration: K={k_start} → K={k_end} takes {total_time:.1f} Myr")
    print(f"  Cumulative survival probability: {cumulative_survival*100:.4f}%")
    print(f"  Odds of reaching Type III: 1 in {int(1/cumulative_survival)}")

    # Calculate survival through individual crises
    print("\n" + "-"*70)
    print("Survival Probability Through Individual Crises:")
    print("-"*70)

    crisis_windows = [
        (0.65, 0.80, "Nuclear Age"),
        (0.75, 0.95, "Planetary Unification"),
        (0.95, 1.15, "AI Transition"),
        (1.10, 1.40, "Interplanetary Expansion"),
        (1.60, 2.00, "Stellar Engineering"),
        (2.25, 2.75, "Relativistic Weapons")
    ]

    for k_min, k_max, name in crisis_windows:
        crisis_time = (k_max - k_min) / advancement_rate
        k_crisis = np.linspace(k_min, k_max, int(crisis_time / dt))

        survival = 1.0
        for k in k_crisis:
            lambda_k = extinction_model.calculate_kardashev_hazard_rate(k)
            survival *= np.exp(-lambda_k * dt)

        print(f"  {name:^30}: {survival*100:>6.2f}% survival ({crisis_time:>5.1f} Myr window)")

    print("\n" + "="*70 + "\n")


def compare_scenarios():
    """
    Compare different Great Filter scenarios.
    """
    print("\n" + "="*70)
    print("SCENARIO COMPARISON: Different Great Filter Hypotheses")
    print("="*70)

    scenarios = {
        'Default (Moderate Filter)': {
            'ai_amplitude': 0.20,
            'nuclear_amplitude': 0.15,
            'description': 'Balanced crisis risks'
        },
        'AI Dominates (Late Filter)': {
            'ai_amplitude': 0.40,
            'nuclear_amplitude': 0.15,
            'description': 'AI transition is the primary Great Filter'
        },
        'Nuclear Age Dominates': {
            'ai_amplitude': 0.10,
            'nuclear_amplitude': 0.35,
            'description': 'Early technology crisis is hardest'
        },
        'Optimistic': {
            'ai_amplitude': 0.05,
            'nuclear_amplitude': 0.05,
            'description': 'Low crisis risks (life is common)'
        }
    }

    for scenario_name, params in scenarios.items():
        # Create custom extinction model
        crisis_peaks = [
            CrisisPeak("nuclear_age", 0.72, 0.05, params['nuclear_amplitude'], True),
            CrisisPeak("ai_transition", 1.05, 0.10, params['ai_amplitude'], True),
        ]

        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent",
            baseline_rate=0.01,
            baseline_scaling=0.05,
            crisis_peaks=crisis_peaks
        )

        # Calculate survival K=0.7 → K=3.0
        k_trajectory = np.linspace(0.7, 3.0, 2300)
        dt = 0.1
        survival = 1.0
        for k in k_trajectory:
            lambda_k = model.calculate_kardashev_hazard_rate(k)
            survival *= np.exp(-lambda_k * dt)

        print(f"\n{scenario_name}:")
        print(f"  Description: {params['description']}")
        print(f"  Survival to Type III: {survival*100:.4f}% (1 in {int(1/survival) if survival > 0 else 'infinity'})")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("GALATICBOT: KARDASHEV-DEPENDENT SELF-DESTRUCTION MODEL")
    print("="*70)
    print("\nThis demonstration shows how technological civilizations face")
    print("distinct existential crises at specific developmental stages.")
    print("\nBased on Great Filter theory and the Fermi Paradox.")
    print("="*70)

    # Generate visualizations
    print("\n[1/3] Generating hazard landscape visualization...")
    plot_hazard_landscape()

    # Calculate statistics
    print("\n[2/3] Calculating survival statistics...")
    calculate_survival_statistics()

    # Compare scenarios
    print("\n[3/3] Comparing Great Filter scenarios...")
    compare_scenarios()

    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nKey Findings:")
    print("  - AI transition (K~1.05) is the most dangerous crisis by default")
    print("  - Only ~0.1-1% of civilizations survive to become Type III")
    print("  - This explains the Fermi Paradox: galactic colonization is extremely rare")
    print("  - Crisis parameters can be tuned to explore different scenarios")
    print("\nNext Steps:")
    print("  - Run full Monte Carlo simulation with: python examples/realistic_simulation.py")
    print("  - Modify crisis amplitudes in SimulationConfig for sensitivity analysis")
    print("  - Use self_destruction_model_type='flat' for comparison to simple model")
    print("="*70 + "\n")
