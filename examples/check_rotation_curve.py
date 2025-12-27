"""Check rotation curve from gravitational potential."""

import numpy as np
from great_silence.galaxy.structure import GalaxyModel
from great_silence.config.parameters import GalaxyParameters

# Create just the galaxy model
params = GalaxyParameters()
params.include_bulge = True

galaxy = GalaxyModel(params, seed=42)

# Don't generate stars, just check the potential
print("Checking rotation curve from gravitational potential:")
print(f"Target v_circ: {params.rotation_velocity_km_s} km/s\n")

for R in [1, 2, 4, 6, 8, 10, 12, 15]:
    pos = np.array([float(R), 0.0, 0.0])

    # Compute acceleration
    accel = galaxy._compute_gravitational_acceleration(pos.reshape(1, 3))[0]

    # Radial component
    a_R = accel[0]  # Since y=0, z=0, radial direction is just x

    # Circular velocity
    if a_R < 0:
        v_circ_kpc_myr = np.sqrt(R * (-a_R))
        v_circ_km_s = v_circ_kpc_myr / 0.001022
    else:
        v_circ_km_s = 0.0

    print(f"R = {R:2d} kpc: a_R = {a_R:10.6f} kpc/Myr², v_circ = {v_circ_km_s:6.1f} km/s")

print(f"\nConclusion:")
print(f"The potential gives v_circ ≈ {v_circ_km_s:.0f} km/s at R=8 kpc")
print(f"This is {100*v_circ_km_s/params.rotation_velocity_km_s - 100:+.1f}% from target")
