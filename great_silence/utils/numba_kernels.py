"""
Numba-accelerated computational kernels for The Great Silence.

This module contains Numba JIT-compiled functions for performance-critical
operations. All functions are standalone (no class methods) to be compatible
with Numba's nopython mode.

Performance targets on Apple Silicon M1/M2/M3:
- Position evolution: 10-20x speedup vs NumPy
- Distance calculations: 10-30x speedup vs NumPy
- Supernova rates: 15-25x speedup vs Python loops

Usage:
    from great_silence.utils.numba_kernels import evolve_positions_numba

    # Enable Numba in config
    config.simulation.use_numba = True

    # Use in main loop
    positions = evolve_positions_numba(positions, velocities, dt_myr)
"""

import numba
import numpy as np

# =============================================================================
# Position Evolution Kernels
# =============================================================================


@numba.jit(nopython=True, parallel=True, fastmath=True)
def evolve_positions_numba(
    positions: np.ndarray, velocities: np.ndarray, dt_myr: float
) -> np.ndarray:
    """
    Evolve stellar positions forward in time (Numba-accelerated).

    This function parallelizes across stars using prange, achieving 10-20x
    speedup vs NumPy on Apple Silicon.

    Complexity: O(N) parallelized

    Args:
        positions: (N, 3) array of positions in kpc
        velocities: (N, 3) array of velocities in km/s
        dt_myr: Time step in million years

    Returns:
        Updated positions array (N, 3) in kpc
    """
    n_stars = len(positions)

    # Conversion factor: 1 km/s = 0.001022 kpc/Myr
    v_conv = 0.001022

    # Allocate output array
    new_positions = np.empty_like(positions)

    # Parallel loop over stars (uses all P-cores on Apple Silicon)
    for i in numba.prange(n_stars):
        new_positions[i, 0] = positions[i, 0] + velocities[i, 0] * v_conv * dt_myr
        new_positions[i, 1] = positions[i, 1] + velocities[i, 1] * v_conv * dt_myr
        new_positions[i, 2] = positions[i, 2] + velocities[i, 2] * v_conv * dt_myr

    return new_positions


@numba.jit(nopython=True, parallel=True, fastmath=True)
def evolve_positions_inplace_numba(
    positions: np.ndarray, velocities: np.ndarray, dt_myr: float
) -> None:
    """
    In-place version of position evolution (saves memory allocation).

    Complexity: O(N) parallelized

    Args:
        positions: (N, 3) array of positions in kpc (modified in-place)
        velocities: (N, 3) array of velocities in km/s
        dt_myr: Time step in million years
    """
    n_stars = len(positions)
    v_conv = 0.001022

    for i in numba.prange(n_stars):
        positions[i, 0] += velocities[i, 0] * v_conv * dt_myr
        positions[i, 1] += velocities[i, 1] * v_conv * dt_myr
        positions[i, 2] += velocities[i, 2] * v_conv * dt_myr


# =============================================================================
# Distance Calculation Kernels
# =============================================================================


@numba.jit(nopython=True, parallel=True, fastmath=True)
def compute_distances_to_point_numba(positions: np.ndarray, point: np.ndarray) -> np.ndarray:
    """
    Compute distances from all positions to a single point.

    Complexity: O(N) parallelized

    Args:
        positions: (N, 3) array of positions in kpc
        point: (3,) array representing point position in kpc

    Returns:
        distances: (N,) array of distances in kpc
    """
    n_stars = len(positions)
    distances = np.empty(n_stars, dtype=np.float64)

    for i in numba.prange(n_stars):
        dx = positions[i, 0] - point[0]
        dy = positions[i, 1] - point[1]
        dz = positions[i, 2] - point[2]

        distances[i] = np.sqrt(dx * dx + dy * dy + dz * dz)

    return distances


@numba.jit(nopython=True, parallel=True, fastmath=True)
def find_nearby_mask_numba(positions: np.ndarray, point: np.ndarray, radius: float) -> np.ndarray:
    """
    Find all positions within radius of point (returns boolean mask).

    More efficient than computing all distances when you only need
    the boolean mask. Avoids sqrt calculation by comparing squared distances.

    Complexity: O(N) parallelized

    Args:
        positions: (N, 3) array of positions in kpc
        point: (3,) array representing point position in kpc
        radius: Search radius in kpc

    Returns:
        mask: (N,) boolean array, True if within radius
    """
    n_stars = len(positions)
    mask = np.empty(n_stars, dtype=np.bool_)
    radius_sq = radius * radius

    for i in numba.prange(n_stars):
        dx = positions[i, 0] - point[0]
        dy = positions[i, 1] - point[1]
        dz = positions[i, 2] - point[2]

        dist_sq = dx * dx + dy * dy + dz * dz
        mask[i] = dist_sq <= radius_sq

    return mask


@numba.jit(nopython=True, parallel=False, fastmath=True)
def find_nearby_indices_numba(
    positions: np.ndarray, point: np.ndarray, radius: float
) -> np.ndarray:
    """
    Find indices of all positions within radius of point.

    Note: Cannot use parallel=True because output size is variable.
    For large datasets, use find_nearby_mask_numba instead.

    Complexity: O(N)

    Args:
        positions: (N, 3) array of positions in kpc
        point: (3,) array representing point position in kpc
        radius: Search radius in kpc

    Returns:
        indices: (M,) array of indices within radius (M <= N)
    """
    n_stars = len(positions)
    radius_sq = radius * radius

    # First pass: count matches
    count = 0
    for i in range(n_stars):
        dx = positions[i, 0] - point[0]
        dy = positions[i, 1] - point[1]
        dz = positions[i, 2] - point[2]

        dist_sq = dx * dx + dy * dy + dz * dz
        if dist_sq <= radius_sq:
            count += 1

    # Allocate result array
    indices = np.empty(count, dtype=np.int64)

    # Second pass: fill indices
    idx = 0
    for i in range(n_stars):
        dx = positions[i, 0] - point[0]
        dy = positions[i, 1] - point[1]
        dz = positions[i, 2] - point[2]

        dist_sq = dx * dx + dy * dy + dz * dz
        if dist_sq <= radius_sq:
            indices[idx] = i
            idx += 1

    return indices


# =============================================================================
# Astrophysics Kernels
# =============================================================================


@numba.jit(nopython=True, fastmath=True)
def compute_supernova_rates_numba(
    stellar_masses: np.ndarray, stellar_ages: np.ndarray
) -> np.ndarray:
    """
    Compute supernova rates for all stars (vectorized).

    Only massive stars (M > 8 solar masses) can go supernova.
    Rate peaks at end of main sequence lifetime.

    Complexity: O(N)

    Args:
        stellar_masses: (N,) array of masses in solar masses
        stellar_ages: (N,) array of ages in Gyr

    Returns:
        rates: (N,) array of supernova rates (per year)
    """
    n_stars = len(stellar_masses)
    rates = np.zeros(n_stars, dtype=np.float64)

    for i in range(n_stars):
        mass = stellar_masses[i]
        age = stellar_ages[i]

        # Only massive stars go supernova
        if mass < 8.0:
            continue

        # Main sequence lifetime: t_ms ∝ M^(-2.5)
        t_ms_gyr = 10.0 * mass ** (-2.5)

        # Supernova rate peaks at t_ms (Gaussian)
        if age >= t_ms_gyr:
            delta_t = (age - t_ms_gyr) / 0.01  # 10 Myr width
            rates[i] = np.exp(-delta_t * delta_t)

    return rates


@numba.jit(nopython=True, fastmath=True)
def evaluate_supernova_destruction_vectorized(
    stellar_masses: np.ndarray,
    stellar_ages: np.ndarray,
    distances_pc: np.ndarray,
    dt_myr: float,
    lethal_range_pc: float,
    sterilization_range_pc: float,
    random_numbers: np.ndarray,
) -> bool:
    """
    Evaluate if any nearby supernova destroys a civilization (vectorized).

    This combines rate calculation, probability evaluation, and random
    sampling into a single vectorized kernel.

    Complexity: O(M) where M is number of nearby stars

    Args:
        stellar_masses: (M,) array of nearby star masses
        stellar_ages: (M,) array of nearby star ages (Gyr)
        distances_pc: (M,) array of distances to nearby stars (pc)
        dt_myr: Time step in Myr
        lethal_range_pc: Instant death range in pc
        sterilization_range_pc: Partial sterilization range in pc
        random_numbers: (M, 2) array of random numbers in [0, 1]

    Returns:
        destroyed: True if civilization is destroyed
    """
    n_nearby = len(stellar_masses)

    for i in range(n_nearby):
        mass = stellar_masses[i]
        age = stellar_ages[i]
        dist = distances_pc[i]

        # Only check massive stars within sterilization range
        if mass < 8.0 or dist >= sterilization_range_pc:
            continue

        # Main sequence lifetime
        t_ms_gyr = 10.0 * mass ** (-2.5)

        # Supernova rate
        if age >= t_ms_gyr:
            delta_t = (age - t_ms_gyr) / 0.01
            rate = np.exp(-delta_t * delta_t)

            # Probability of supernova during timestep
            p_sn = rate * dt_myr * 1e6  # Convert Myr to years

            # Check if supernova occurs
            if random_numbers[i, 0] < p_sn:
                # Supernova occurred - calculate sterilization probability
                if dist < lethal_range_pc:
                    p_sterilize = 1.0
                else:
                    # Exponential decay
                    r = (dist - lethal_range_pc) / (sterilization_range_pc - lethal_range_pc)
                    p_sterilize = np.exp(-3.0 * r)

                # Check if civilization is destroyed
                if random_numbers[i, 1] < p_sterilize:
                    return True

    return False


# =============================================================================
# Neutron Star Merger Kernels
# =============================================================================


@numba.jit(nopython=True, fastmath=True)
def evaluate_ns_merger_hazard_kernel(
    civ_position: np.ndarray,
    merger_position: np.ndarray,
    jet_theta: float,
    jet_phi: float,
    sgrb_beaming_angle_deg: float,
    sgrb_lethal_range_kpc: float,
    kilonova_lethal_range_pc: float,
    kilonova_sterilization_range_pc: float,
    random_val: float,
) -> int:
    """
    Evaluate NS merger hazard effect on civilization.

    Returns:
        0 = survived
        1 = destroyed by sGRB
        2 = destroyed by kilonova
    """
    jet_dir = np.array(
        [
            np.sin(jet_theta) * np.cos(jet_phi),
            np.sin(jet_theta) * np.sin(jet_phi),
            np.cos(jet_theta),
        ]
    )

    to_civ = civ_position - merger_position
    distance_kpc = np.sqrt(to_civ[0] ** 2 + to_civ[1] ** 2 + to_civ[2] ** 2)
    distance_pc = distance_kpc * 1000.0

    if distance_kpc > 1e-10 and distance_kpc < sgrb_lethal_range_kpc:
        to_civ_unit = to_civ / distance_kpc
        cos_angle = (
            jet_dir[0] * to_civ_unit[0] + jet_dir[1] * to_civ_unit[1] + jet_dir[2] * to_civ_unit[2]
        )
        angle_rad = np.arccos(min(1.0, max(-1.0, cos_angle)))
        angle_deg = angle_rad * 180.0 / 3.14159265358979

        if angle_deg < sgrb_beaming_angle_deg:
            return 1

        cos_angle_opp = (
            -jet_dir[0] * to_civ_unit[0] - jet_dir[1] * to_civ_unit[1] - jet_dir[2] * to_civ_unit[2]
        )
        angle_rad_opp = np.arccos(min(1.0, max(-1.0, cos_angle_opp)))
        angle_deg_opp = angle_rad_opp * 180.0 / 3.14159265358979

        if angle_deg_opp < sgrb_beaming_angle_deg:
            return 1

    if distance_pc < kilonova_lethal_range_pc:
        return 2
    elif distance_pc < kilonova_sterilization_range_pc:
        r = (distance_pc - kilonova_lethal_range_pc) / (
            kilonova_sterilization_range_pc - kilonova_lethal_range_pc
        )
        p_sterilize = np.exp(-3.0 * r)
        if random_val < p_sterilize:
            return 2

    return 0


@numba.jit(nopython=True, fastmath=True)
def compute_ns_merger_probability_kernel(
    stellar_positions: np.ndarray,
    stellar_masses: np.ndarray,
    stellar_ages: np.ndarray,
    civ_position: np.ndarray,
    search_radius_kpc: float,
    galactic_merger_rate_per_myr: float,
    galactic_mass_msun: float,
) -> float:
    """
    Compute NS merger probability for a single civilization location.

    Uses local stellar mass density of evolved massive stars to
    scale the galactic-average merger rate.

    Complexity: O(N) - for use with KD-tree prefiltering

    Args:
        stellar_positions: (N, 3) positions in kpc
        stellar_masses: (N,) masses in solar masses
        stellar_ages: (N,) ages in Gyr
        civ_position: (3,) civilization position in kpc
        search_radius_kpc: Search radius for local rate
        galactic_merger_rate_per_myr: Galaxy-wide rate per Myr
        galactic_mass_msun: Total galactic stellar mass

    Returns:
        Local merger probability per Myr
    """
    n_stars = len(stellar_masses)
    search_radius_sq = search_radius_kpc * search_radius_kpc

    local_evolved_mass = 0.0

    for i in range(n_stars):
        dx = stellar_positions[i, 0] - civ_position[0]
        dy = stellar_positions[i, 1] - civ_position[1]
        dz = stellar_positions[i, 2] - civ_position[2]
        dist_sq = dx * dx + dy * dy + dz * dz

        if dist_sq > search_radius_sq:
            continue

        mass = stellar_masses[i]
        if mass < 8.0:
            continue

        age = stellar_ages[i]
        t_ms_gyr = 10.0 * mass ** (-2.5)

        if age > t_ms_gyr:
            local_evolved_mass += mass

    volume_factor = (search_radius_kpc / 15.0) ** 3
    local_rate = (
        galactic_merger_rate_per_myr * (local_evolved_mass / galactic_mass_msun) * volume_factor
    )

    return local_rate


@numba.jit(nopython=True, parallel=True, fastmath=True)
def batch_evaluate_hazards_kernel(
    civ_positions: np.ndarray,
    stellar_positions: np.ndarray,
    stellar_masses: np.ndarray,
    stellar_ages: np.ndarray,
    sn_lethal_range_pc: float,
    sn_sterilization_range_pc: float,
    dt_myr: float,
    random_values: np.ndarray,
) -> np.ndarray:
    """
    Batch evaluate supernova hazards for multiple civilizations.

    Parallelizes across civilizations for 4-8x speedup on multi-core.

    Complexity: O(C * N / P) where C=civs, N=stars, P=cores

    Args:
        civ_positions: (C, 3) civilization positions in kpc
        stellar_positions: (N, 3) stellar positions in kpc
        stellar_masses: (N,) stellar masses
        stellar_ages: (N,) stellar ages in Gyr
        sn_lethal_range_pc: Supernova lethal range in pc
        sn_sterilization_range_pc: Supernova sterilization range in pc
        dt_myr: Time step in Myr
        random_values: (C,) random values for stochastic evaluation

    Returns:
        (C,) boolean array, True if civilization destroyed
    """
    n_civs = len(civ_positions)
    n_stars = len(stellar_positions)
    results = np.zeros(n_civs, dtype=np.bool_)

    sterilization_range_kpc = sn_sterilization_range_pc / 1000.0
    sterilization_range_kpc_sq = sterilization_range_kpc * sterilization_range_kpc

    for c in numba.prange(n_civs):
        civ_pos = civ_positions[c]

        for i in range(n_stars):
            dx = stellar_positions[i, 0] - civ_pos[0]
            dy = stellar_positions[i, 1] - civ_pos[1]
            dz = stellar_positions[i, 2] - civ_pos[2]
            dist_sq_kpc = dx * dx + dy * dy + dz * dz

            if dist_sq_kpc > sterilization_range_kpc_sq:
                continue

            mass = stellar_masses[i]
            if mass < 8.0:
                continue

            age = stellar_ages[i]
            t_ms_gyr = 10.0 * mass ** (-2.5)

            if age < t_ms_gyr:
                continue

            dt_gyr = dt_myr / 1000.0
            age_end = age + dt_gyr

            if not (age <= t_ms_gyr < age_end):
                continue

            dist_pc = np.sqrt(dist_sq_kpc) * 1000.0

            if dist_pc < sn_lethal_range_pc:
                p_sterilize = 1.0
            else:
                r = (dist_pc - sn_lethal_range_pc) / (
                    sn_sterilization_range_pc - sn_lethal_range_pc
                )
                p_sterilize = np.exp(-3.0 * r)

            if random_values[c] < p_sterilize:
                results[c] = True
                break

    return results


# =============================================================================
# Batch Disaster Effect Evaluation Kernels
# =============================================================================


@numba.jit(nopython=True, fastmath=True)
def evaluate_sn_effect_on_civs_kernel(
    civ_positions: np.ndarray,
    disaster_position: np.ndarray,
    lethal_range_pc: float,
    sterilization_range_pc: float,
    random_values: np.ndarray,
) -> np.ndarray:
    """
    Evaluate supernova effect on multiple civilizations (BRANCHLESS).

    Uses arithmetic masks instead of if branches for SIMD vectorization.

    Args:
        civ_positions: (C, 3) civilization positions in kpc
        disaster_position: (3,) disaster position in kpc
        lethal_range_pc: Instant death range in pc
        sterilization_range_pc: Partial sterilization range in pc
        random_values: (C,) random values for stochastic evaluation

    Returns:
        (C,) int array: 0=survived, 1=destroyed
    """
    n_civs = len(civ_positions)
    results = np.zeros(n_civs, dtype=np.int32)

    lethal_kpc = lethal_range_pc / 1000.0
    sterilization_kpc = sterilization_range_pc / 1000.0

    for c in range(n_civs):
        dx = civ_positions[c, 0] - disaster_position[0]
        dy = civ_positions[c, 1] - disaster_position[1]
        dz = civ_positions[c, 2] - disaster_position[2]
        dist_kpc = np.sqrt(dx * dx + dy * dy + dz * dz)

        dist_pc = dist_kpc * 1000.0

        # Branchless: compute all cases, blend with masks
        # Use comparisons directly (return 0 or 1 in arithmetic context)
        in_range = (dist_kpc <= sterilization_kpc) * 1.0
        in_lethal = (dist_pc < lethal_range_pc) * 1.0

        # Probabilistic sterilization calculation (always computed)
        r = (dist_pc - lethal_range_pc) / (sterilization_range_pc - lethal_range_pc + 1e-10)
        p_sterilize = np.exp(-3.0 * r)
        in_probabilistic = (random_values[c] < p_sterilize) * 1.0

        # Blend: lethal takes precedence, then probabilistic, only if in range
        destroyed = in_range * (in_lethal + (1.0 - in_lethal) * in_probabilistic)

        results[c] = int(destroyed)

    return results


@numba.jit(nopython=True, fastmath=True)
def evaluate_grb_effect_on_civs_kernel(
    civ_positions: np.ndarray,
    disaster_position: np.ndarray,
    jet_theta: float,
    jet_phi: float,
    beaming_angle_deg: float,
    lethal_range_kpc: float,
) -> np.ndarray:
    """
    Evaluate GRB effect on multiple civilizations (BRANCHLESS).

    Uses arithmetic masks for SIMD vectorization.

    Args:
        civ_positions: (C, 3) civilization positions in kpc
        disaster_position: (3,) GRB position in kpc
        jet_theta: Jet polar angle (radians)
        jet_phi: Jet azimuthal angle (radians)
        beaming_angle_deg: Beaming half-angle (degrees)
        lethal_range_kpc: Lethal distance in kpc

    Returns:
        (C,) int array: 0=survived, 1=destroyed
    """
    n_civs = len(civ_positions)
    results = np.zeros(n_civs, dtype=np.int32)

    jet_dir = np.array(
        [
            np.sin(jet_theta) * np.cos(jet_phi),
            np.sin(jet_theta) * np.sin(jet_phi),
            np.cos(jet_theta),
        ]
    )

    beaming_rad = beaming_angle_deg * 3.14159265358979 / 180.0
    cos_beaming = np.cos(beaming_rad)

    for c in range(n_civs):
        dx = civ_positions[c, 0] - disaster_position[0]
        dy = civ_positions[c, 1] - disaster_position[1]
        dz = civ_positions[c, 2] - disaster_position[2]
        dist_kpc = np.sqrt(dx * dx + dy * dy + dz * dz)

        # Branchless: check distance range
        in_range = ((dist_kpc >= 1e-10) * (dist_kpc <= lethal_range_kpc)) * 1.0

        # Always compute normalized direction (safe with small dist guard)
        dist_safe = dist_kpc + 1e-10
        to_civ_x = dx / dist_safe
        to_civ_y = dy / dist_safe
        to_civ_z = dz / dist_safe

        cos_angle = jet_dir[0] * to_civ_x + jet_dir[1] * to_civ_y + jet_dir[2] * to_civ_z

        # Check if in beam (either direction)
        in_beam_forward = (cos_angle > cos_beaming) * 1.0
        in_beam_backward = (-cos_angle > cos_beaming) * 1.0

        # Destroyed if in range AND in either beam direction
        destroyed = in_range * (in_beam_forward + in_beam_backward)

        results[c] = int(destroyed)

    return results


@numba.jit(nopython=True, fastmath=True)
def evaluate_ns_merger_effect_on_civs_kernel(
    civ_positions: np.ndarray,
    disaster_position: np.ndarray,
    jet_theta: float,
    jet_phi: float,
    sgrb_beaming_angle_deg: float,
    sgrb_lethal_range_kpc: float,
    kilonova_lethal_range_pc: float,
    kilonova_sterilization_range_pc: float,
    random_values: np.ndarray,
) -> np.ndarray:
    """
    Evaluate NS merger effect on multiple civilizations.

    Considers both sGRB (beamed) and kilonova (isotropic) effects.

    Args:
        civ_positions: (C, 3) civilization positions in kpc
        disaster_position: (3,) merger position in kpc
        jet_theta: Jet polar angle (radians)
        jet_phi: Jet azimuthal angle (radians)
        sgrb_beaming_angle_deg: sGRB beaming half-angle (degrees)
        sgrb_lethal_range_kpc: sGRB lethal distance in kpc
        kilonova_lethal_range_pc: Kilonova lethal distance in pc
        kilonova_sterilization_range_pc: Kilonova partial sterilization range
        random_values: (C,) random values for stochastic evaluation

    Returns:
        (C,) int array: 0=survived, 1=destroyed by sGRB, 2=destroyed by kilonova
    """
    n_civs = len(civ_positions)
    results = np.zeros(n_civs, dtype=np.int32)

    jet_dir = np.array(
        [
            np.sin(jet_theta) * np.cos(jet_phi),
            np.sin(jet_theta) * np.sin(jet_phi),
            np.cos(jet_theta),
        ]
    )

    beaming_rad = sgrb_beaming_angle_deg * 3.14159265358979 / 180.0
    cos_beaming = np.cos(beaming_rad)

    kilonova_lethal_kpc = kilonova_lethal_range_pc / 1000.0
    kilonova_sterilization_kpc = kilonova_sterilization_range_pc / 1000.0

    for c in range(n_civs):
        dx = civ_positions[c, 0] - disaster_position[0]
        dy = civ_positions[c, 1] - disaster_position[1]
        dz = civ_positions[c, 2] - disaster_position[2]
        dist_kpc = np.sqrt(dx * dx + dy * dy + dz * dz)

        # Branchless sGRB check
        in_sgrb_range = ((dist_kpc > 1e-10) * (dist_kpc < sgrb_lethal_range_kpc)) * 1.0

        dist_safe = dist_kpc + 1e-10
        to_civ_x = dx / dist_safe
        to_civ_y = dy / dist_safe
        to_civ_z = dz / dist_safe

        cos_angle = jet_dir[0] * to_civ_x + jet_dir[1] * to_civ_y + jet_dir[2] * to_civ_z
        in_beam = ((cos_angle > cos_beaming) + (-cos_angle > cos_beaming)) * 1.0

        destroyed_by_sgrb = in_sgrb_range * in_beam

        # Branchless kilonova check (only if not destroyed by sGRB)
        in_kilonova_lethal = (dist_kpc < kilonova_lethal_kpc) * 1.0
        in_kilonova_sterilization = (dist_kpc < kilonova_sterilization_kpc) * 1.0

        # Probabilistic sterilization
        r = (dist_kpc - kilonova_lethal_kpc) / (
            kilonova_sterilization_kpc - kilonova_lethal_kpc + 1e-10
        )
        p_sterilize = np.exp(-3.0 * r)
        probabilistic = (random_values[c] < p_sterilize) * 1.0

        # Kilonova destruction (lethal or probabilistic)
        destroyed_by_kilonova = (
            in_kilonova_lethal
            + (1.0 - in_kilonova_lethal) * in_kilonova_sterilization * probabilistic
        )

        # Priority: sGRB (1) > kilonova (2) > survived (0)
        # Use arithmetic to blend: if sGRB, result=1; elif kilonova, result=2; else result=0
        result = destroyed_by_sgrb * 1.0 + (1.0 - destroyed_by_sgrb) * destroyed_by_kilonova * 2.0

        results[c] = int(result)

    return results


@numba.jit(nopython=True, parallel=True, fastmath=True)
def batch_find_civs_in_range_kernel(
    civ_positions: np.ndarray, disaster_positions: np.ndarray, max_range_kpc: float
) -> np.ndarray:
    """
    Find which civilizations are within range of any disaster.

    Args:
        civ_positions: (C, 3) civilization positions in kpc
        disaster_positions: (D, 3) disaster positions in kpc
        max_range_kpc: Maximum effect range in kpc

    Returns:
        (C,) boolean array, True if civ within range of any disaster
    """
    n_civs = len(civ_positions)
    n_disasters = len(disaster_positions)
    in_range = np.zeros(n_civs, dtype=np.bool_)
    max_range_sq = max_range_kpc * max_range_kpc

    for c in numba.prange(n_civs):
        for d in range(n_disasters):
            dx = civ_positions[c, 0] - disaster_positions[d, 0]
            dy = civ_positions[c, 1] - disaster_positions[d, 1]
            dz = civ_positions[c, 2] - disaster_positions[d, 2]
            dist_sq = dx * dx + dy * dy + dz * dz

            if dist_sq < max_range_sq:
                in_range[c] = True
                break

    return in_range


# =============================================================================
# Stellar Generation Kernels
# =============================================================================


@numba.jit(nopython=True, fastmath=True)
def rejection_sample_exponential_disk_radii(
    n_samples: int, scale_length_kpc: float, max_radius_kpc: float, seed: int
) -> np.ndarray:
    """
    Sample radii from exponential disk using rejection sampling.

    Samples from P(r) ∝ r * exp(-r/h_R) using batch rejection sampling.

    Complexity: O(N) expected (depends on acceptance rate)

    Args:
        n_samples: Number of radii to sample
        scale_length_kpc: Disk scale length h_R in kpc
        max_radius_kpc: Maximum radius to consider
        seed: Random seed for reproducibility

    Returns:
        radii: (n_samples,) array of radii in kpc
    """
    np.random.seed(seed)

    radii = np.empty(n_samples, dtype=np.float64)
    n_accepted = 0
    batch_size = min(n_samples * 2, 1_000_000)

    while n_accepted < n_samples:
        # Generate candidate radii from exponential distribution
        r_candidates = np.random.exponential(scale_length_kpc, batch_size)

        # Acceptance probability: proportional to r
        # (with cutoff at max_radius)
        for i in range(batch_size):
            if n_accepted >= n_samples:
                break

            r = r_candidates[i]

            if r >= max_radius_kpc:
                continue

            # Accept with probability r / max_radius
            accept_prob = r / max_radius_kpc
            if np.random.random() < accept_prob:
                radii[n_accepted] = r
                n_accepted += 1

    return radii


@numba.jit(nopython=True, fastmath=True)
def compute_circular_velocities(
    positions: np.ndarray,
    v_circ: float,
    sigma_r: float,
    sigma_theta: float,
    sigma_z: float,
    disk_height_kpc: float,
    seed: int,
) -> np.ndarray:
    """
    Compute stellar velocities from rotation curve with dispersion.

    Assumes flat rotation curve with velocity dispersion that increases
    with height above disk.

    Complexity: O(N)

    Args:
        positions: (N, 3) array of positions in kpc
        v_circ: Circular velocity in km/s
        sigma_r: Radial velocity dispersion at midplane (km/s)
        sigma_theta: Azimuthal velocity dispersion at midplane (km/s)
        sigma_z: Vertical velocity dispersion at midplane (km/s)
        disk_height_kpc: Disk scale height in kpc
        seed: Random seed

    Returns:
        velocities: (N, 3) array of velocities in km/s
    """
    np.random.seed(seed)

    n_stars = len(positions)
    velocities = np.empty((n_stars, 3), dtype=np.float64)

    for i in range(n_stars):
        x = positions[i, 0]
        y = positions[i, 1]
        z = positions[i, 2]

        # Cylindrical radius
        r = np.sqrt(x * x + y * y)

        # Circular velocity components
        if r > 1e-10:
            v_x = -v_circ * y / r
            v_y = v_circ * x / r
        else:
            v_x = 0.0
            v_y = 0.0

        v_z = 0.0

        # Velocity dispersion (increases with height)
        height_factor = 1.0 + np.abs(z) / disk_height_kpc

        # Add random dispersion
        v_x += np.random.normal(0.0, sigma_r * height_factor)
        v_y += np.random.normal(0.0, sigma_theta * height_factor)
        v_z += np.random.normal(0.0, sigma_z * height_factor)

        velocities[i, 0] = v_x
        velocities[i, 1] = v_y
        velocities[i, 2] = v_z

    return velocities


# =============================================================================
# Civilization Emergence Kernels
# =============================================================================


@numba.jit(nopython=True, cache=True)
def compute_emergence_probabilities_kernel(
    habitable_indices: np.ndarray,
    stellar_ages: np.ndarray,
    metallicities: np.ndarray,
    colonized_mask: np.ndarray,
    min_age_gyr: float,
    f_base: float,
    n_habitable: float,
    f_life: float,
    f_intel: float,
    f_tech: float,
    dt_myr: float,
    use_metallicity_gradient: bool,
    random_values: np.ndarray,
) -> np.ndarray:
    """
    Compute emergence and sample which stars develop civilizations.

    Combines filtering, probability calculation, and random sampling
    in a single Numba kernel for reduced Python overhead.
    Uses cache=True for faster repeated calls.

    Args:
        habitable_indices: Indices of habitable stars
        stellar_ages: Ages of all stars in Gyr
        metallicities: Metallicities of all stars [Fe/H]
        colonized_mask: Boolean mask of colonized stars
        min_age_gyr: Minimum age for civilization development
        f_base: Base fraction of stars with planets
        n_habitable: Average habitable planets per system
        f_life: Fraction developing life
        f_intel: Fraction developing intelligence
        f_tech: Fraction developing technology
        dt_myr: Time step in Myr
        use_metallicity_gradient: Use metallicity-dependent probability
        random_values: Pre-generated random values [0, 1)

    Returns:
        emerged_indices: Indices into habitable_indices of stars that emerged
    """
    n_habitable_stars = len(habitable_indices)
    emerged = np.zeros(n_habitable_stars, dtype=np.bool_)
    dt_gyr = dt_myr / 1000.0

    for i in range(n_habitable_stars):
        star_idx = habitable_indices[i]

        if colonized_mask[star_idx]:
            continue

        age = stellar_ages[star_idx]
        if age <= min_age_gyr:
            continue

        if use_metallicity_gradient:
            feh = metallicities[star_idx]
            f_planets = f_base * (10.0**feh)
            if f_planets < 0.01:
                f_planets = 0.01
            elif f_planets > 1.0:
                f_planets = 1.0
        else:
            f_planets = f_base

        p_emergence_gyr = f_planets * n_habitable * f_life * f_intel * f_tech
        p_emergence = p_emergence_gyr * dt_gyr

        if random_values[i] < p_emergence:
            emerged[i] = True

    return emerged


@numba.jit(nopython=True, fastmath=True)
def count_eligible_stars_kernel(
    habitable_indices: np.ndarray,
    stellar_ages: np.ndarray,
    colonized_mask: np.ndarray,
    min_age_gyr: float,
) -> int:
    """
    Fast count of eligible stars for emergence probability estimation.

    Used by adaptive timestep to estimate emergence rate without
    doing full probability calculation.

    Args:
        habitable_indices: Indices of habitable stars
        stellar_ages: Ages of all stars in Gyr
        colonized_mask: Boolean mask of colonized stars
        min_age_gyr: Minimum age for civilization development

    Returns:
        Number of eligible stars
    """
    count = 0
    for i in range(len(habitable_indices)):
        star_idx = habitable_indices[i]
        if colonized_mask[star_idx]:
            continue
        if stellar_ages[star_idx] > min_age_gyr:
            count += 1
    return count


# =============================================================================
# Utility Functions
# =============================================================================


@numba.jit(nopython=True, fastmath=True)
def count_within_radius(positions: np.ndarray, centers: np.ndarray, radius: float) -> np.ndarray:
    """
    Count how many positions are within radius of each center.

    Useful for computing local stellar density around civilizations.

    Complexity: O(N * M) where N=positions, M=centers

    Args:
        positions: (N, 3) array of positions
        centers: (M, 3) array of center positions
        radius: Search radius

    Returns:
        counts: (M,) array of counts
    """
    n_positions = len(positions)
    n_centers = len(centers)
    counts = np.zeros(n_centers, dtype=np.int64)
    radius_sq = radius * radius

    for j in range(n_centers):
        center = centers[j]

        for i in range(n_positions):
            dx = positions[i, 0] - center[0]
            dy = positions[i, 1] - center[1]
            dz = positions[i, 2] - center[2]

            dist_sq = dx * dx + dy * dy + dz * dz

            if dist_sq <= radius_sq:
                counts[j] += 1

    return counts


# =============================================================================
# Leapfrog Integration with Gravitational Potential
# =============================================================================


@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def leapfrog_integrate_positions_kernel(
    positions: np.ndarray, velocities: np.ndarray, accelerations: np.ndarray, dt_myr: float
) -> None:
    """
    Perform leapfrog position update step (in-place).

    r(t+dt) = r(t) + v(t)×dt + 0.5×a(t)×dt²

    Velocities in km/s, positions in kpc, accelerations in kpc/Myr².

    Args:
        positions: (N, 3) positions in kpc (modified in-place)
        velocities: (N, 3) velocities in km/s
        accelerations: (N, 3) accelerations in kpc/Myr²
        dt_myr: Time step in Myr
    """
    n_stars = len(positions)
    v_conv = 0.001022  # km/s to kpc/Myr
    dt_sq = dt_myr * dt_myr * 0.5

    for i in numba.prange(n_stars):
        positions[i, 0] += velocities[i, 0] * v_conv * dt_myr + accelerations[i, 0] * dt_sq
        positions[i, 1] += velocities[i, 1] * v_conv * dt_myr + accelerations[i, 1] * dt_sq
        positions[i, 2] += velocities[i, 2] * v_conv * dt_myr + accelerations[i, 2] * dt_sq


@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def leapfrog_integrate_velocities_kernel(
    velocities: np.ndarray, accel_old: np.ndarray, accel_new: np.ndarray, dt_myr: float
) -> None:
    """
    Perform leapfrog velocity update step (in-place).

    v(t+dt) = v(t) + 0.5×(a(t) + a(t+dt))×dt

    Accelerations in kpc/Myr², velocities in km/s.

    Args:
        velocities: (N, 3) velocities in km/s (modified in-place)
        accel_old: (N, 3) accelerations at t in kpc/Myr²
        accel_new: (N, 3) accelerations at t+dt in kpc/Myr²
        dt_myr: Time step in Myr
    """
    n_stars = len(velocities)
    v_conv_inv = 1.0 / 0.001022  # kpc/Myr to km/s
    half_dt = 0.5 * dt_myr

    for i in numba.prange(n_stars):
        velocities[i, 0] += (accel_old[i, 0] + accel_new[i, 0]) * half_dt * v_conv_inv
        velocities[i, 1] += (accel_old[i, 1] + accel_new[i, 1]) * half_dt * v_conv_inv
        velocities[i, 2] += (accel_old[i, 2] + accel_new[i, 2]) * half_dt * v_conv_inv


@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def yoshida_integrate_step_kernel(
    positions: np.ndarray,
    velocities: np.ndarray,
    accelerations: np.ndarray,
    dt_myr: float,
    accel_func,
    *accel_args,
) -> None:
    """
    Perform Yoshida 4th-order symplectic integration step.

    Yoshida (1990) 4th-order symplectic integrator uses 3 sub-steps with
    special coefficients. Provides same accuracy as leapfrog with 4-8x larger dt.
    Still symplectic (energy conserving over 10+ Gyr).

    Coefficients:
        w0 = -2^(1/3) / (2 - 2^(1/3))
        w1 = 1 / (2 - 2^(1/3))
        c1 = c4 = w1 / 2
        c2 = c3 = (w0 + w1) / 2
        d1 = d3 = w1
        d2 = w0

    Integration sequence (3 sub-steps):
        1. x += c1 * v * dt
        2. v += d1 * a(x) * dt
        3. x += c2 * v * dt
        4. v += d2 * a(x) * dt
        5. x += c3 * v * dt
        6. v += d3 * a(x) * dt
        7. x += c4 * v * dt

    Args:
        positions: (N, 3) positions in kpc (modified in-place)
        velocities: (N, 3) velocities in km/s (modified in-place)
        accelerations: (N, 3) scratch array for accelerations (overwritten)
        dt_myr: Time step in Myr
        accel_func: Acceleration computation function
        *accel_args: Arguments to pass to accel_func

    References:
        Yoshida (1990): https://doi.org/10.1007/BF00048986
        Rein & Tamayo (2019): https://doi.org/10.1093/mnras/stz2503
    """
    # Yoshida 4th-order coefficients
    cbrt_2 = 1.259921049894873  # 2^(1/3)
    w0 = -cbrt_2 / (2.0 - cbrt_2)
    w1 = 1.0 / (2.0 - cbrt_2)

    c1 = c4 = w1 / 2.0
    c2 = c3 = (w0 + w1) / 2.0
    d1 = d3 = w1
    d2 = w0

    v_conv = 0.001022  # km/s to kpc/Myr
    v_conv_inv = 1.0 / v_conv

    n_stars = len(positions)

    # Sub-step 1: drift + kick
    for i in numba.prange(n_stars):
        positions[i, 0] += velocities[i, 0] * v_conv * c1 * dt_myr
        positions[i, 1] += velocities[i, 1] * v_conv * c1 * dt_myr
        positions[i, 2] += velocities[i, 2] * v_conv * c1 * dt_myr

    accel_func(positions, accelerations, *accel_args)

    for i in numba.prange(n_stars):
        velocities[i, 0] += accelerations[i, 0] * d1 * dt_myr * v_conv_inv
        velocities[i, 1] += accelerations[i, 1] * d1 * dt_myr * v_conv_inv
        velocities[i, 2] += accelerations[i, 2] * d1 * dt_myr * v_conv_inv

    # Sub-step 2: drift + kick
    for i in numba.prange(n_stars):
        positions[i, 0] += velocities[i, 0] * v_conv * c2 * dt_myr
        positions[i, 1] += velocities[i, 1] * v_conv * c2 * dt_myr
        positions[i, 2] += velocities[i, 2] * v_conv * c2 * dt_myr

    accel_func(positions, accelerations, *accel_args)

    for i in numba.prange(n_stars):
        velocities[i, 0] += accelerations[i, 0] * d2 * dt_myr * v_conv_inv
        velocities[i, 1] += accelerations[i, 1] * d2 * dt_myr * v_conv_inv
        velocities[i, 2] += accelerations[i, 2] * d2 * dt_myr * v_conv_inv

    # Sub-step 3: drift + kick
    for i in numba.prange(n_stars):
        positions[i, 0] += velocities[i, 0] * v_conv * c3 * dt_myr
        positions[i, 1] += velocities[i, 1] * v_conv * c3 * dt_myr
        positions[i, 2] += velocities[i, 2] * v_conv * c3 * dt_myr

    accel_func(positions, accelerations, *accel_args)

    for i in numba.prange(n_stars):
        velocities[i, 0] += accelerations[i, 0] * d3 * dt_myr * v_conv_inv
        velocities[i, 1] += accelerations[i, 1] * d3 * dt_myr * v_conv_inv
        velocities[i, 2] += accelerations[i, 2] * d3 * dt_myr * v_conv_inv

    # Final drift
    for i in numba.prange(n_stars):
        positions[i, 0] += velocities[i, 0] * v_conv * c4 * dt_myr
        positions[i, 1] += velocities[i, 1] * v_conv * c4 * dt_myr
        positions[i, 2] += velocities[i, 2] * v_conv * c4 * dt_myr


@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def compute_miyamoto_nagai_acceleration_kernel(
    positions: np.ndarray, out_accel: np.ndarray, a: float, b: float, G_M: float
) -> None:
    """
    Compute Miyamoto-Nagai disk acceleration (in-place).

    Φ_disk(R, z) = -GM / sqrt(R² + (a + sqrt(z² + b²))²)

    Args:
        positions: (N, 3) positions in kpc
        out_accel: (N, 3) output acceleration in kpc/Myr² (added to existing)
        a: Disk scale length in kpc
        b: Disk scale height in kpc
        G_M: G × M_disk in kpc³/Myr²
    """
    n_stars = len(positions)

    for i in numba.prange(n_stars):
        x = positions[i, 0]
        y = positions[i, 1]
        z = positions[i, 2]

        R_sq = x * x + y * y
        R = np.sqrt(R_sq)

        sqrt_term = np.sqrt(z * z + b * b)
        D_sq = R_sq + (a + sqrt_term) * (a + sqrt_term)
        D_cubed = D_sq * np.sqrt(D_sq) + 1e-30

        # Radial component
        a_R = -G_M * R / D_cubed

        # z component
        a_z = -G_M * (a + sqrt_term) * z / ((sqrt_term + 1e-10) * D_cubed)

        # Convert to Cartesian
        if R > 1e-10:
            out_accel[i, 0] += a_R * x / R
            out_accel[i, 1] += a_R * y / R
        out_accel[i, 2] += a_z


@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def compute_hernquist_acceleration_kernel(
    positions: np.ndarray, out_accel: np.ndarray, a_bulge: float, G_M: float
) -> None:
    """
    Compute Hernquist bulge acceleration (in-place).

    Φ_bulge(r) = -GM / (r + a)

    Args:
        positions: (N, 3) positions in kpc
        out_accel: (N, 3) output acceleration in kpc/Myr² (added to existing)
        a_bulge: Bulge scale radius in kpc
        G_M: G × M_bulge in kpc³/Myr²
    """
    n_stars = len(positions)

    for i in numba.prange(n_stars):
        x = positions[i, 0]
        y = positions[i, 1]
        z = positions[i, 2]

        r = np.sqrt(x * x + y * y + z * z)
        factor = -G_M / ((r + a_bulge) * (r + a_bulge) + 1e-30)

        if r > 1e-10:
            out_accel[i, 0] += factor * x / r
            out_accel[i, 1] += factor * y / r
            out_accel[i, 2] += factor * z / r


@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def compute_isothermal_halo_acceleration_kernel(
    positions: np.ndarray, out_accel: np.ndarray, v_halo_sq: float
) -> None:
    """
    Compute isothermal halo acceleration (in-place).

    Gives flat rotation curve: a = v²/r (radially inward)

    Args:
        positions: (N, 3) positions in kpc
        out_accel: (N, 3) output acceleration in kpc/Myr² (added to existing)
        v_halo_sq: v_halo² in kpc²/Myr²
    """
    n_stars = len(positions)

    for i in numba.prange(n_stars):
        x = positions[i, 0]
        y = positions[i, 1]
        z = positions[i, 2]

        r = np.sqrt(x * x + y * y + z * z)
        factor = -v_halo_sq / (r + 1e-10)

        if r > 1e-10:
            out_accel[i, 0] += factor * x / r
            out_accel[i, 1] += factor * y / r
            out_accel[i, 2] += factor * z / r


@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def compute_total_acceleration_kernel(
    positions: np.ndarray,
    out_accel: np.ndarray,
    disk_a: float,
    disk_b: float,
    disk_G_M: float,
    bulge_a: float,
    bulge_G_M: float,
    halo_v_sq: float,
    include_bulge: bool,
) -> None:
    """
    Compute total gravitational acceleration from all components.

    Combines Miyamoto-Nagai disk + Hernquist bulge + isothermal halo.

    Args:
        positions: (N, 3) positions in kpc
        out_accel: (N, 3) output acceleration in kpc/Myr² (overwritten)
        disk_a: Disk scale length (kpc)
        disk_b: Disk scale height (kpc)
        disk_G_M: G × M_disk (kpc³/Myr²)
        bulge_a: Bulge scale radius (kpc)
        bulge_G_M: G × M_bulge (kpc³/Myr²)
        halo_v_sq: v_halo² (kpc²/Myr²)
        include_bulge: Whether to include bulge component
    """
    n_stars = len(positions)

    for i in numba.prange(n_stars):
        x = positions[i, 0]
        y = positions[i, 1]
        z = positions[i, 2]

        # Initialize to zero
        ax = 0.0
        ay = 0.0
        az = 0.0

        R_sq = x * x + y * y
        R = np.sqrt(R_sq)
        r = np.sqrt(R_sq + z * z)

        # Miyamoto-Nagai disk
        sqrt_term = np.sqrt(z * z + disk_b * disk_b)
        D_sq = R_sq + (disk_a + sqrt_term) * (disk_a + sqrt_term)
        D_cubed = D_sq * np.sqrt(D_sq) + 1e-30

        a_R_disk = -disk_G_M * R / D_cubed
        a_z_disk = -disk_G_M * (disk_a + sqrt_term) * z / ((sqrt_term + 1e-10) * D_cubed)

        if R > 1e-10:
            ax += a_R_disk * x / R
            ay += a_R_disk * y / R
        az += a_z_disk

        # Hernquist bulge
        if include_bulge and r > 1e-10:
            factor_bulge = -bulge_G_M / ((r + bulge_a) * (r + bulge_a) + 1e-30)
            ax += factor_bulge * x / r
            ay += factor_bulge * y / r
            az += factor_bulge * z / r

        # Isothermal halo
        if r > 1e-10:
            factor_halo = -halo_v_sq / (r + 1e-10)
            ax += factor_halo * x / r
            ay += factor_halo * y / r
            az += factor_halo * z / r

        out_accel[i, 0] = ax
        out_accel[i, 1] = ay
        out_accel[i, 2] = az


# =============================================================================
# Epicyclic Orbit Positions
# =============================================================================


@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def epicyclic_positions_kernel(
    t_myr: float,
    R_g: np.ndarray,
    Omega_g: np.ndarray,
    kappa: np.ndarray,
    nu: np.ndarray,
    X: np.ndarray,
    alpha: np.ndarray,
    phi_g0: np.ndarray,
    Z: np.ndarray,
    beta: np.ndarray,
    out: np.ndarray,
) -> None:
    """
    Evaluate closed-form epicyclic positions at time t_myr (writes (N, 3) kpc).

    Mirrors EpicyclicOrbitModel._positions_numpy:
        R = R_g + X cos(kappa t + alpha)
        phi = phi_g0 + Omega_g t - gamma X sin(kappa t + alpha) / R_g
        z = Z cos(nu t + beta)
    with gamma = 2 Omega_g / (kappa R_g).

    Frequencies in 1/Myr, radii/positions in kpc, time in Myr.

    Args:
        t_myr: Evaluation time in Myr
        R_g, Omega_g, kappa, nu, X, alpha, phi_g0, Z, beta: (N,) orbit params
        out: (N, 3) output positions in kpc (modified in-place)
    """
    n_stars = len(R_g)
    for i in numba.prange(n_stars):
        ph_R = kappa[i] * t_myr + alpha[i]
        R = R_g[i] + X[i] * np.cos(ph_R)
        gamma = 2.0 * Omega_g[i] / (kappa[i] * R_g[i])
        phi = phi_g0[i] + Omega_g[i] * t_myr - gamma * X[i] * np.sin(ph_R) / R_g[i]
        out[i, 0] = R * np.cos(phi)
        out[i, 1] = R * np.sin(phi)
        out[i, 2] = Z[i] * np.cos(nu[i] * t_myr + beta[i])


# =============================================================================
# Benchmark Utilities
# =============================================================================


def benchmark_kernel(kernel_func, *args, n_runs: int = 10, warmup: int = 2):
    """
    Benchmark a Numba kernel with warmup runs.

    Args:
        kernel_func: Numba-compiled function to benchmark
        *args: Arguments to pass to kernel
        n_runs: Number of benchmark runs
        warmup: Number of warmup runs (for JIT compilation)

    Returns:
        dict with timing statistics
    """
    import time

    # Warmup (triggers JIT compilation)
    for _ in range(warmup):
        _ = kernel_func(*args)

    # Benchmark
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        _ = kernel_func(*args)
        end = time.perf_counter()
        times.append(end - start)

    times = np.array(times)

    return {
        "mean": np.mean(times),
        "std": np.std(times),
        "min": np.min(times),
        "max": np.max(times),
        "median": np.median(times),
    }


if __name__ == "__main__":
    """
    Benchmark kernels on this machine.
    """
    print("GalaticBot Numba Kernels Benchmark")
    print("=" * 60)

    # Test position evolution
    n_stars = 1_000_000
    positions = np.random.randn(n_stars, 3).astype(np.float64)
    velocities = np.random.randn(n_stars, 3).astype(np.float64)
    dt_myr = 1.0

    print(f"\n1. Position Evolution (N={n_stars:,})")
    stats = benchmark_kernel(evolve_positions_numba, positions, velocities, dt_myr)
    print(f"   Time: {stats['mean']*1000:.2f} ± {stats['std']*1000:.2f} ms")
    print(f"   Throughput: {n_stars/stats['mean']/1e6:.2f} M stars/sec")

    # Test distance calculation
    point = np.array([0.0, 0.0, 0.0])
    print(f"\n2. Distance Calculation (N={n_stars:,})")
    stats = benchmark_kernel(compute_distances_to_point_numba, positions, point)
    print(f"   Time: {stats['mean']*1000:.2f} ± {stats['std']*1000:.2f} ms")
    print(f"   Throughput: {n_stars/stats['mean']/1e6:.2f} M distances/sec")

    # Test nearby search
    radius = 1.0
    print(f"\n3. Nearby Search (N={n_stars:,}, r={radius} kpc)")
    stats = benchmark_kernel(find_nearby_mask_numba, positions, point, radius)
    print(f"   Time: {stats['mean']*1000:.2f} ± {stats['std']*1000:.2f} ms")
    n_nearby = np.sum(find_nearby_mask_numba(positions, point, radius))
    print(f"   Found: {n_nearby:,} nearby stars")

    # Test supernova rates
    masses = np.random.lognormal(0.0, 1.0, n_stars) * 2.0  # Random masses
    ages = np.random.uniform(0, 13, n_stars)  # Random ages
    print(f"\n4. Supernova Rates (N={n_stars:,})")
    stats = benchmark_kernel(compute_supernova_rates_numba, masses, ages)
    print(f"   Time: {stats['mean']*1000:.2f} ± {stats['std']*1000:.2f} ms")
    rates = compute_supernova_rates_numba(masses, ages)
    print(f"   Active supernovae: {np.sum(rates > 0.1):,}")

    print("\n" + "=" * 60)
    print("Benchmark complete!")
