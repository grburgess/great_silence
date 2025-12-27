"""
Demonstration of Kardashev-Dependent Self-Destruction Model.

This script visualizes the crisis-based extinction model and shows how
self-destruction risk varies with technological advancement.
"""

import numpy as np
import matplotlib.pyplot as plt
from great_silence.civilization.extinction import ExtinctionModel, CrisisPeak


def demo_hazard_landscape():
    """Visualize the self-destruction hazard landscape across Kardashev scale."""
    print("=" * 80)
    print("KARDASHEV-DEPENDENT SELF-DESTRUCTION MODEL DEMO")
    print("=" * 80)

    # Create extinction model with default crisis peaks
    model = ExtinctionModel(
        self_destruction_rate=0.1,  # Fallback (not used in kardashev_dependent mode)
        mean_lifetime_myr=5.0,
        model_type="kardashev_dependent",
        baseline_rate=0.01,
        baseline_scaling=0.05
    )

    print("\nCrisis Peaks Configured:")
    print("-" * 80)
    for crisis in model.crisis_peaks:
        print(f"  {crisis.name:25s} K={crisis.kardashev_center:.2f}  "
              f"width={crisis.width:.2f}  amplitude={crisis.amplitude:.2f}")

    # Calculate hazard rates across Kardashev scale
    K_values = np.linspace(0.5, 3.0, 500)
    hazard_rates = np.array([model.calculate_kardashev_hazard_rate(K) for K in K_values])

    # Calculate expected survival times
    survival_times = 1.0 / (hazard_rates + 1e-10)  # In Myr

    # Baseline hazard (without crisis peaks)
    baseline_hazards = model.baseline_rate * (1.0 + model.baseline_scaling * K_values)

    # Create visualization
    fig = plt.figure(figsize=(16, 12))
    fig.patch.set_facecolor('black')

    # Panel 1: Hazard Rate vs Kardashev Scale
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.set_facecolor('#0a0a0a')
    ax1.plot(K_values, hazard_rates, 'r-', linewidth=2.5, label='Total Hazard')
    ax1.plot(K_values, baseline_hazards, 'b--', linewidth=1.5, alpha=0.6, label='Baseline')

    # Mark crisis peaks
    for crisis in model.crisis_peaks:
        if crisis.enabled:
            ax1.axvline(crisis.kardashev_center, color='orange', linestyle=':',
                       alpha=0.5, linewidth=1)
            ax1.text(crisis.kardashev_center, ax1.get_ylim()[1] * 0.95,
                    crisis.name.replace('_', '\n'),
                    rotation=0, fontsize=7, ha='center', va='top',
                    color='yellow', alpha=0.8)

    ax1.set_xlabel('Kardashev Scale', fontsize=12, color='white')
    ax1.set_ylabel('Hazard Rate λ(K) [per Myr]', fontsize=12, color='white')
    ax1.set_title('Self-Destruction Hazard Landscape', fontsize=14,
                 color='white', fontweight='bold')
    ax1.grid(True, alpha=0.3, color='gray')
    ax1.legend(loc='upper left', facecolor='black', edgecolor='white',
              labelcolor='white', framealpha=0.8)
    ax1.tick_params(colors='white')
    for spine in ax1.spines.values():
        spine.set_color('white')

    # Panel 2: Expected Survival Time
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.set_facecolor('#0a0a0a')
    ax2.plot(K_values, survival_times, 'c-', linewidth=2.5)
    ax2.fill_between(K_values, 0, survival_times, alpha=0.3, color='cyan')

    # Mark dangerous zones
    for crisis in model.crisis_peaks:
        if crisis.enabled and crisis.amplitude > 0.1:
            ax2.axvspan(crisis.kardashev_center - crisis.width,
                       crisis.kardashev_center + crisis.width,
                       alpha=0.2, color='red')

    ax2.set_xlabel('Kardashev Scale', fontsize=12, color='white')
    ax2.set_ylabel('Expected Survival Time [Myr]', fontsize=12, color='white')
    ax2.set_title('Expected Longevity at Each Stage', fontsize=14,
                 color='white', fontweight='bold')
    ax2.set_ylim(0, 50)
    ax2.grid(True, alpha=0.3, color='gray')
    ax2.tick_params(colors='white')
    for spine in ax2.spines.values():
        spine.set_color('white')

    # Panel 3: Cumulative Survival Probability
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.set_facecolor('#0a0a0a')

    # Compute cumulative survival assuming constant advancement rate
    advancement_rate = 0.01  # per Myr (standard rate)
    dK = K_values[1] - K_values[0]
    dt_per_dK = dK / advancement_rate

    # Survival probability through each segment
    survival_prob = np.exp(-hazard_rates * dt_per_dK)
    cumulative_survival = np.cumprod(survival_prob)

    ax3.semilogy(K_values, cumulative_survival, 'g-', linewidth=2.5)
    ax3.fill_between(K_values, 1e-10, cumulative_survival, alpha=0.3, color='green')

    # Mark Kardashev transitions
    ax3.axvline(1.0, color='yellow', linestyle='--', alpha=0.7, label='Type I')
    ax3.axvline(2.0, color='orange', linestyle='--', alpha=0.7, label='Type II')
    ax3.axvline(3.0, color='red', linestyle='--', alpha=0.7, label='Type III')

    ax3.set_xlabel('Kardashev Scale', fontsize=12, color='white')
    ax3.set_ylabel('Cumulative Survival Probability', fontsize=12, color='white')
    ax3.set_title('The Great Filter: Fraction Surviving to Each Stage',
                 fontsize=14, color='white', fontweight='bold')
    ax3.set_ylim(1e-8, 1.0)
    ax3.grid(True, alpha=0.3, color='gray', which='both')
    ax3.legend(loc='upper right', facecolor='black', edgecolor='white',
              labelcolor='white', framealpha=0.8)
    ax3.tick_params(colors='white')
    for spine in ax3.spines.values():
        spine.set_color('white')

    # Panel 4: Crisis Contribution Breakdown
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.set_facecolor('#0a0a0a')

    # Plot individual crisis contributions
    colors = ['red', 'orange', 'yellow', 'lime', 'cyan', 'magenta']
    for i, crisis in enumerate(model.crisis_peaks):
        if crisis.enabled:
            crisis_contribution = crisis.amplitude * np.exp(
                -0.5 * ((K_values - crisis.kardashev_center) / crisis.width) ** 2
            )
            ax4.fill_between(K_values, 0, crisis_contribution,
                           alpha=0.6, color=colors[i % len(colors)],
                           label=crisis.name.replace('_', ' ').title())

    ax4.set_xlabel('Kardashev Scale', fontsize=12, color='white')
    ax4.set_ylabel('Hazard Contribution [per Myr]', fontsize=12, color='white')
    ax4.set_title('Individual Crisis Contributions', fontsize=14,
                 color='white', fontweight='bold')
    ax4.grid(True, alpha=0.3, color='gray')
    ax4.legend(loc='upper right', fontsize=8, facecolor='black',
              edgecolor='white', labelcolor='white', framealpha=0.8)
    ax4.tick_params(colors='white')
    for spine in ax4.spines.values():
        spine.set_color('white')

    plt.tight_layout()
    plt.savefig('output/kardashev_hazard_landscape.png', dpi=150,
               facecolor='black', edgecolor='none')
    print("\n✓ Saved: output/kardashev_hazard_landscape.png")
    plt.close()

    # Print key statistics
    print("\n" + "=" * 80)
    print("KEY STATISTICS")
    print("=" * 80)

    # Modern Earth (K=0.72)
    earth_idx = np.argmin(np.abs(K_values - 0.72))
    earth_hazard = hazard_rates[earth_idx]
    earth_survival_time = survival_times[earth_idx]

    print(f"\nModern Earth (K=0.72):")
    print(f"  Hazard rate: {earth_hazard:.3f} per Myr")
    print(f"  Expected survival time: {earth_survival_time:.1f} Myr")
    print(f"  10-year survival probability: {np.exp(-earth_hazard * 1e-5):.6f}")

    # AI transition peak (K=1.05)
    ai_idx = np.argmin(np.abs(K_values - 1.05))
    ai_hazard = hazard_rates[ai_idx]
    ai_survival_time = survival_times[ai_idx]

    print(f"\nAI Transition Peak (K=1.05):")
    print(f"  Hazard rate: {ai_hazard:.3f} per Myr")
    print(f"  Expected survival time: {ai_survival_time:.1f} Myr")
    print(f"  This is the most dangerous period!")

    # Type II civilization (K=2.0)
    type2_idx = np.argmin(np.abs(K_values - 2.0))
    type2_hazard = hazard_rates[type2_idx]
    type2_cumulative = cumulative_survival[type2_idx]

    print(f"\nType II Civilization (K=2.0):")
    print(f"  Hazard rate: {type2_hazard:.3f} per Myr")
    print(f"  Fraction surviving from K=0.7: {type2_cumulative:.2e}")
    print(f"  (1 in {1/type2_cumulative:.0f} civilizations reach Type II)")

    # Type III civilization (K=3.0)
    type3_cumulative = cumulative_survival[-1]
    print(f"\nType III Civilization (K=3.0):")
    print(f"  Fraction surviving from K=0.7: {type3_cumulative:.2e}")
    print(f"  (1 in {1/type3_cumulative:.0f} civilizations reach Type III)")

    print("\n" + "=" * 80)
    print("FERMI PARADOX INTERPRETATION")
    print("=" * 80)
    print("\nWith default parameters, the AI transition (K~1.0-1.2) acts as the")
    print("primary Great Filter. Most civilizations that survive the nuclear age")
    print("are destroyed during the transition to artificial general intelligence.")
    print("\nThis explains the 'Great Silence' - galaxy-spanning civilizations are")
    print("extraordinarily rare because the filters compound exponentially.")
    print("\n✓ Demo complete!")


if __name__ == '__main__':
    import os
    os.makedirs('output', exist_ok=True)
    demo_hazard_landscape()
