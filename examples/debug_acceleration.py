"""Debug acceleration calculations."""

import numpy as np
from great_silence import GalaxySimulation, SimulationConfig

# Create small galaxy
config = SimulationConfig()
config.galaxy.total_stars = 1000
config.galaxy.include_bulge = True

print("Initializing galaxy...")
sim = GalaxySimulation(config, seed=42)
sim.initialize()

# Check a few test stars
test_indices = [10, 50, 100, 200]

print("\nTest stars:")
for idx in test_indices:
    pos = sim.galaxy.positions[idx]
    vel = sim.galaxy.velocities[idx]

    x, y, z = pos
    vx, vy, vz = vel

    R = np.sqrt(x**2 + y**2)
    r = np.sqrt(x**2 + y**2 + z**2)
    v_mag = np.sqrt(vx**2 + vy**2 + vz**2)

    print(f"\nStar {idx}:")
    print(f"  Position: ({x:.3f}, {y:.3f}, {z:.3f}) kpc")
    print(f"  R (cylindrical): {R:.3f} kpc")
    print(f"  r (spherical): {r:.3f} kpc")
    print(f"  Velocity: ({vx:.3f}, {vy:.3f}, {vz:.3f}) km/s")
    print(f"  |v|: {v_mag:.3f} km/s")

    # Compute acceleration components
    a_disk = sim.galaxy._compute_disk_acceleration(pos.reshape(1, 3))[0]
    a_bulge = sim.galaxy._compute_bulge_acceleration(pos.reshape(1, 3))[0]
    a_halo = sim.galaxy._compute_halo_acceleration(pos.reshape(1, 3))[0]
    a_total = a_disk + a_bulge + a_halo

    # Convert to km/s per Myr for comparison
    a_total_km_s_myr = a_total / 0.001022  # kpc/Myr² → km/s per Myr

    print(f"  a_disk: ({a_disk[0]:.6f}, {a_disk[1]:.6f}, {a_disk[2]:.6f}) kpc/Myr²")
    print(f"  a_bulge: ({a_bulge[0]:.6f}, {a_bulge[1]:.6f}, {a_bulge[2]:.6f}) kpc/Myr²")
    print(f"  a_halo: ({a_halo[0]:.6f}, {a_halo[1]:.6f}, {a_halo[2]:.6f}) kpc/Myr²")
    print(f"  a_total: ({a_total[0]:.6f}, {a_total[1]:.6f}, {a_total[2]:.6f}) kpc/Myr²")
    print(f"  |a_total|: {np.linalg.norm(a_total):.6f} kpc/Myr²")
    print(f"  |a_total| (km/s/Myr): {np.linalg.norm(a_total_km_s_myr):.3f}")

    # Expected centripetal acceleration for circular orbit
    v_circ_kpc_myr = 220 * 0.001022  # 220 km/s in kpc/Myr
    a_expected = v_circ_kpc_myr**2 / R if R > 0 else 0
    print(f"  Expected a_centripetal: {a_expected:.6f} kpc/Myr² (for v=220 km/s)")

    # Check velocity change over 10 Myr
    dt = 10.0  # Myr
    dv = a_total * dt / 0.001022  # Convert to km/s
    print(f"  Δv over {dt} Myr: ({dv[0]:.3f}, {dv[1]:.3f}, {dv[2]:.3f}) km/s")
    print(f"  |Δv|: {np.linalg.norm(dv):.3f} km/s ({100*np.linalg.norm(dv)/v_mag:.1f}% of |v|)")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Compute all accelerations
all_accel = sim.galaxy._compute_gravitational_acceleration(sim.galaxy.positions)
accel_magnitudes = np.linalg.norm(all_accel, axis=1)

print(f"\nAcceleration statistics (kpc/Myr²):")
print(f"  Min: {accel_magnitudes.min():.6f}")
print(f"  Max: {accel_magnitudes.max():.6f}")
print(f"  Mean: {accel_magnitudes.mean():.6f}")
print(f"  Median: {np.median(accel_magnitudes):.6f}")

# Check if any accelerations are abnormally large
large_accel = accel_magnitudes > 0.1
print(f"\nStars with |a| > 0.1 kpc/Myr²: {np.sum(large_accel)} ({100*np.sum(large_accel)/len(accel_magnitudes):.1f}%)")

if np.sum(large_accel) > 0:
    print("  These stars are likely near r=0 and need better handling!")
