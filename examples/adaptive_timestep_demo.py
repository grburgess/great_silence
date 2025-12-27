"""
Demonstration of adaptive timestepping for efficiency.

Shows how to dynamically adjust dt based on simulation activity.
"""

import numpy as np
from great_silence import GalaxySimulation, SimulationConfig, configure_m1_max_threading
from great_silence.visualization import GalaxyVisualizer, TimelineAnimator

# Configure threading FIRST (before importing numba/numpy heavy operations)
configure_m1_max_threading(
    numba_threads=8,      # Use all 8 P-cores for Numba
    numpy_threads=1,      # Disable NumPy BLAS parallelism (avoid nesting)
    suppress_omp_warnings=True  # Suppress the deprecated warning
)
print()


class AdaptiveGalaxySimulation(GalaxySimulation):
    """
    Extended simulation with adaptive timestepping.

    Adjusts dt based on "activity level" - how many events are happening.
    """

    def __init__(self, config, seed=None):
        super().__init__(config, seed)

        # Adaptive timestep parameters
        self.dt_min = 0.1  # Minimum timestep (Myr)
        self.dt_max = 100.0  # Maximum timestep (Myr)
        self.dt_current = config.simulation.time_step_myr
        self.activity_history = []  # Track recent activity

        # Adaptation thresholds
        self.high_activity_threshold = 5  # Events per timestep
        self.low_activity_threshold = 0.5

        # Statistics
        self.timestep_history = []
        self.activity_log = []

    def _calculate_activity(self):
        """
        Calculate current activity level.

        Activity = number of significant events this timestep:
        - Births
        - Deaths
        - Expansions (simplified: just count active expanding civs)
        """
        # Count births (civilizations born this timestep)
        n_births = len([c for c in self.civilizations
                       if abs(c.birth_time_myr - self.current_time_myr) < 0.01])

        # Count deaths (civilizations that died this timestep)
        n_deaths = len([c for c in self.civilizations
                       if c.death_time_myr is not None and
                       abs(c.death_time_myr - self.current_time_myr) < 0.01])

        # Count active civilizations (proxy for expansion activity)
        n_active = len([c for c in self.civilizations if c.is_active])

        # Combined activity score
        activity = n_births * 2 + n_deaths * 2 + n_active * 0.1

        return activity

    def _adapt_timestep(self):
        """
        Adapt timestep based on recent activity.

        Uses moving average to avoid oscillations.
        """
        current_activity = self._calculate_activity()
        self.activity_history.append(current_activity)

        # Keep only last 10 timesteps
        if len(self.activity_history) > 10:
            self.activity_history = self.activity_history[-10:]

        # Use moving average for stability
        avg_activity = np.mean(self.activity_history)

        # Adaptation logic
        if avg_activity > self.high_activity_threshold:
            # High activity - decrease timestep for accuracy
            self.dt_current = max(self.dt_current * 0.8, self.dt_min)
            adaptation = "REFINE"
        elif avg_activity < self.low_activity_threshold:
            # Low activity - increase timestep for speed
            self.dt_current = min(self.dt_current * 1.5, self.dt_max)
            adaptation = "COARSEN"
        else:
            # Moderate activity - keep current
            adaptation = "MAINTAIN"

        # Log for analysis
        self.timestep_history.append(self.dt_current)
        self.activity_log.append((self.current_time_myr, avg_activity, self.dt_current, adaptation))

        # Update config for next step
        self.config.simulation.time_step_myr = self.dt_current

        return adaptation

    def run(self, verbose: bool = False):
        """Run simulation with adaptive timestepping."""
        print(f"Starting adaptive simulation...")
        print(f"  dt range: [{self.dt_min}, {self.dt_max}] Myr")
        print(f"  Initial dt: {self.dt_current} Myr")
        print()

        self.initialize()

        duration_myr = self.config.simulation.simulation_duration_gyr * 1000.0
        n_steps = 0

        if verbose:
            from tqdm import tqdm
            pbar = tqdm(total=duration_myr, desc="Simulating (adaptive)", unit="Myr")

        while self.current_time_myr < duration_myr:
            # Standard simulation step
            self._step()

            # Adaptive timestepping
            adaptation = self._adapt_timestep()

            n_steps += 1

            if verbose:
                pbar.update(self.config.simulation.time_step_myr)
                pbar.set_postfix({
                    'dt': f'{self.dt_current:.2f}',
                    'activity': f'{self._calculate_activity():.1f}',
                    'adapt': adaptation
                })

            # Save snapshots
            if (self.config.simulation.save_snapshots and
                len(self.snapshots) == 0 or
                self.current_time_myr - self.snapshots[-1].time_myr >=
                self.config.simulation.snapshot_interval_myr):
                self._save_snapshot()

        if verbose:
            pbar.close()

        print(f"\nAdaptive simulation complete!")
        print(f"  Total timesteps: {n_steps}")
        print(f"  Average dt: {np.mean(self.timestep_history):.2f} Myr")
        print(f"  Min dt used: {np.min(self.timestep_history):.2f} Myr")
        print(f"  Max dt used: {np.max(self.timestep_history):.2f} Myr")
        print(f"  Estimated speedup: {duration_myr / (n_steps * np.mean(self.timestep_history)):.1f}x")


def main():
    """Compare fixed vs adaptive timestepping."""
    config = SimulationConfig()

    # Medium-sized test
    config.galaxy.total_stars = 50_000
    config.simulation.simulation_duration_gyr = 5.0  # 5 Gyr
    config.simulation.time_step_myr = 1.0  # Initial dt
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 100.0

    # Moderate parameters
    config.civilization.fraction_develop_life = 0.1
    config.civilization.fraction_develop_intelligence = 0.01
    config.civilization.fraction_develop_technology = 0.1
    config.civilization.mean_civilization_lifetime_myr = 100.0
    config.civilization.self_destruction_probability_per_myr = 0.01

    # Kardashev parameters
    config.civilization.initial_kardashev_scale_mean = 0.7
    config.civilization.initial_kardashev_scale_stddev = 0.1
    config.civilization.kardashev_advancement_rate_mean = 0.01
    config.civilization.kardashev_advancement_rate_stddev = 0.005
    config.civilization.kardashev_stagnation_probability_per_myr = 0.05
    config.civilization.kardashev_breakthrough_probability_per_myr = 0.02
    config.civilization.kardashev_breakthrough_multiplier = 3.0

    print("=" * 70)
    print("Adaptive Timestepping Demonstration")
    print("=" * 70)
    print()

    # Run with adaptive timestepping
    print("Running ADAPTIVE timestep simulation...")
    print()
    sim = AdaptiveGalaxySimulation(config, seed=42)
    sim.run(verbose=True)

    # Results
    stats = sim.get_statistics()
    print(f"\n" + "=" * 70)
    print("Results:")
    print("=" * 70)
    print(f"  Total civilizations: {stats['total_civilizations']}")
    print(f"  Active: {stats['active_civilizations']}")
    print(f"  Extinct: {stats['extinct_civilizations']}")

    # Analyze timestep adaptation
    print(f"\nTimestep Adaptation Analysis:")
    n_refine = len([a for _, _, _, a in sim.activity_log if a == 'REFINE'])
    n_coarsen = len([a for _, _, _, a in sim.activity_log if a == 'COARSEN'])
    n_maintain = len([a for _, _, _, a in sim.activity_log if a == 'MAINTAIN'])

    print(f"  Refinements: {n_refine}")
    print(f"  Coarsenings: {n_coarsen}")
    print(f"  Maintained: {n_maintain}")

    # Plot timestep evolution
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    times = [t for t, _, _, _ in sim.activity_log]
    activities = [a for _, a, _, _ in sim.activity_log]
    dts = [dt for _, _, dt, _ in sim.activity_log]

    # Timestep evolution
    ax1.plot(times, dts, linewidth=1, color='blue')
    ax1.set_ylabel('Timestep (Myr)')
    ax1.set_title('Adaptive Timestep Evolution')
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')

    # Activity level
    ax2.plot(times, activities, linewidth=1, color='red')
    ax2.axhline(sim.high_activity_threshold, color='orange', linestyle='--',
                label='High threshold (refine)')
    ax2.axhline(sim.low_activity_threshold, color='green', linestyle='--',
                label='Low threshold (coarsen)')
    ax2.set_xlabel('Time (Myr)')
    ax2.set_ylabel('Activity Level')
    ax2.set_title('Simulation Activity Level')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('output/adaptive_timestep_analysis.png', dpi=150)
    print(f"\n  Saved: output/adaptive_timestep_analysis.png")

    # Generate civilization visualizations
    print("\nGenerating visualizations...")
    viz = GalaxyVisualizer()

    if sim.civilizations and sim.galaxy.positions is not None:
        viz.plot_civilization_evolution(
            sim.galaxy.positions,
            sim.civilizations,
            save_path="output/adaptive_civilizations.png"
        )
        print("  Saved: output/adaptive_civilizations.png")

    print("\nDone!")


if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    main()
