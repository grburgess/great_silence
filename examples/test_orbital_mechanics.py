"""
Test orbital mechanics implementation.

Verifies that stars remain in stable orbits when gravity is enabled.
"""

import numpy as np
import matplotlib.pyplot as plt
from great_silence import GalaxySimulation, SimulationConfig


def test_orbit_stability():
    """Test that stellar orbits remain stable over long timescales."""
    print("=" * 80)
    print("ORBITAL MECHANICS TEST")
    print("=" * 80)

    # Create small galaxy for faster testing
    config = SimulationConfig()
    config.galaxy.total_stars = 1_000  # Very small for fast velocity initialization
    config.galaxy.include_bulge = True
    config.galaxy.use_metallicity_gradient = True

    # Shorter simulation for quick test
    config.simulation.simulation_duration_gyr = 1.0  # 1 Gyr
    config.simulation.time_step_myr = 10.0  # 10 Myr timesteps
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 100.0  # Every 100 Myr

    # ENABLE stellar motion to test new equilibrium velocities
    config.simulation.enable_stellar_motion = True

    print("\nConfiguration:")
    print(f"  Stars: {config.galaxy.total_stars}")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Time step: {config.simulation.time_step_myr} Myr")
    print(f"  Total steps: {int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.time_step_myr)}")

    # Initialize simulation
    print("\nInitializing galaxy...")
    sim = GalaxySimulation(config, seed=42)
    sim.initialize()

    # Record initial radii
    x0, y0 = sim.galaxy.positions[:, 0], sim.galaxy.positions[:, 1]
    r0 = np.sqrt(x0**2 + y0**2)

    print(f"\nInitial stellar distribution:")
    print(f"  Min radius: {r0.min():.2f} kpc")
    print(f"  Max radius: {r0.max():.2f} kpc")
    print(f"  Mean radius: {r0.mean():.2f} kpc")
    print(f"  Median radius: {np.median(r0):.2f} kpc")

    # Sample a few test stars to track
    n_stars = config.galaxy.total_stars
    test_indices = [100, 500, 1000, 2000, min(5000, n_stars-1)]
    print(f"\nTracking {len(test_indices)} test stars:")
    for idx in test_indices:
        if idx < n_stars:
            r = np.sqrt(sim.galaxy.positions[idx, 0]**2 + sim.galaxy.positions[idx, 1]**2)
            component = "Bulge" if sim.galaxy.component_type[idx] == 0 else "Disk"
            print(f"  Star {idx}: r = {r:.2f} kpc, {component}")

    # Evolve galaxy (without civilizations for speed)
    print("\nEvolving stellar positions...")
    n_steps = int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.time_step_myr)

    # Track radii over time
    radii_history = []
    time_history = []

    for step in range(n_steps):
        # Evolve positions
        sim.galaxy.evolve_positions(
            config.simulation.time_step_myr,
            enable_motion=config.simulation.enable_stellar_motion
        )
        sim.current_time_myr += config.simulation.time_step_myr

        # Record radii every 100 steps
        if step % 100 == 0:
            x, y = sim.galaxy.positions[:, 0], sim.galaxy.positions[:, 1]
            r = np.sqrt(x**2 + y**2)
            radii_history.append(r.copy())
            time_history.append(sim.current_time_myr / 1000.0)  # Convert to Gyr

            print(f"  Step {step}/{n_steps}: t = {sim.current_time_myr/1000:.2f} Gyr, "
                  f"<r> = {r.mean():.2f} kpc, max_r = {r.max():.2f} kpc")

    # Final radii
    xf, yf = sim.galaxy.positions[:, 0], sim.galaxy.positions[:, 1]
    rf = np.sqrt(xf**2 + yf**2)

    print(f"\nFinal stellar distribution:")
    print(f"  Min radius: {rf.min():.2f} kpc")
    print(f"  Max radius: {rf.max():.2f} kpc")
    print(f"  Mean radius: {rf.mean():.2f} kpc")
    print(f"  Median radius: {np.median(rf):.2f} kpc")

    # Check radial drift
    dr = rf - r0
    print(f"\nRadial drift over {config.simulation.simulation_duration_gyr} Gyr:")
    print(f"  Mean drift: {dr.mean():.3f} kpc")
    print(f"  RMS drift: {np.sqrt(np.mean(dr**2)):.3f} kpc")
    print(f"  Max drift: {np.abs(dr).max():.3f} kpc")

    # Check if stars escaped
    escaped = rf > 20.0  # Stars beyond 20 kpc considered escaped
    n_escaped = np.sum(escaped)
    print(f"\nStars beyond 20 kpc: {n_escaped} ({100*n_escaped/len(rf):.2f}%)")

    # Create visualization
    print("\nCreating visualization...")
    fig = plt.figure(figsize=(16, 10))

    # Initial vs final positions
    ax1 = fig.add_subplot(2, 3, 1)
    ax1.scatter(x0, y0, s=0.1, alpha=0.3, c='blue', label='Initial')
    ax1.set_xlabel('X (kpc)')
    ax1.set_ylabel('Y (kpc)')
    ax1.set_title('Initial Positions')
    ax1.set_aspect('equal')
    ax1.set_xlim(-15, 15)
    ax1.set_ylim(-15, 15)
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(2, 3, 2)
    ax2.scatter(xf, yf, s=0.1, alpha=0.3, c='red', label='Final')
    ax2.set_xlabel('X (kpc)')
    ax2.set_ylabel('Y (kpc)')
    ax2.set_title(f'Final Positions (t = {config.simulation.simulation_duration_gyr} Gyr)')
    ax2.set_aspect('equal')
    ax2.set_xlim(-15, 15)
    ax2.set_ylim(-15, 15)
    ax2.grid(True, alpha=0.3)

    # Radial distribution
    ax3 = fig.add_subplot(2, 3, 3)
    bins = np.linspace(0, 15, 50)
    ax3.hist(r0, bins=bins, alpha=0.5, label='Initial', density=True)
    ax3.hist(rf, bins=bins, alpha=0.5, label='Final', density=True)
    ax3.set_xlabel('Radius (kpc)')
    ax3.set_ylabel('Probability Density')
    ax3.set_title('Radial Distribution')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Mean radius over time
    ax4 = fig.add_subplot(2, 3, 4)
    radii_array = np.array(radii_history)
    mean_radii = [r.mean() for r in radii_history]
    ax4.plot(time_history, mean_radii, 'b-', linewidth=2)
    ax4.set_xlabel('Time (Gyr)')
    ax4.set_ylabel('Mean Radius (kpc)')
    ax4.set_title('Mean Radius vs Time')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(r0.mean(), color='gray', linestyle='--', label='Initial')
    ax4.legend()

    # Max radius over time
    ax5 = fig.add_subplot(2, 3, 5)
    max_radii = [r.max() for r in radii_history]
    ax5.plot(time_history, max_radii, 'r-', linewidth=2)
    ax5.set_xlabel('Time (Gyr)')
    ax5.set_ylabel('Max Radius (kpc)')
    ax5.set_title('Max Radius vs Time')
    ax5.grid(True, alpha=0.3)
    ax5.axhline(15.0, color='orange', linestyle='--', label='Galaxy edge')
    ax5.legend()

    # Radial drift histogram
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.hist(dr, bins=50, alpha=0.7, edgecolor='black')
    ax6.set_xlabel('Radial Drift (kpc)')
    ax6.set_ylabel('Number of Stars')
    ax6.set_title(f'Radial Drift Distribution')
    ax6.axvline(0, color='red', linestyle='--', linewidth=2)
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('output/orbital_mechanics_test.png', dpi=150)
    print("   Saved: output/orbital_mechanics_test.png")
    plt.close()

    # Summary
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)

    rms_drift = np.sqrt(np.mean(dr**2))
    drift_per_gyr = rms_drift / config.simulation.simulation_duration_gyr

    print(f"\nOrbital Stability:")
    print(f"  RMS radial drift: {rms_drift:.3f} kpc over {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Drift rate: {drift_per_gyr:.3f} kpc/Gyr")
    print(f"  Stars escaped: {n_escaped} ({100*n_escaped/len(rf):.2f}%)")

    # Pass/fail criteria
    passed = True

    if rms_drift > 2.0:
        print("\n  ❌ FAIL: RMS drift > 2 kpc (orbits not stable)")
        passed = False
    else:
        print(f"\n  ✅ PASS: RMS drift < 2 kpc (orbits stable)")

    if n_escaped > 0.01 * len(rf):
        print(f"  ❌ FAIL: >1% of stars escaped")
        passed = False
    else:
        print(f"  ✅ PASS: <1% of stars escaped")

    if rf.max() > 25.0:
        print(f"  ❌ FAIL: Stars beyond 25 kpc")
        passed = False
    else:
        print(f"  ✅ PASS: All stars within 25 kpc")

    if passed:
        print("\n✅ ALL TESTS PASSED - Orbital mechanics working correctly!")
    else:
        print("\n❌ SOME TESTS FAILED - Orbital mechanics need adjustment")

    return passed


if __name__ == '__main__':
    import os
    os.makedirs('output', exist_ok=True)
    test_orbit_stability()
