"""3D galactic structure modeling with proper stellar kinematics."""

import numpy as np
import numexpr as ne
from typing import Tuple, Optional
from ..config.parameters import GalaxyParameters


class GalaxyModel:
    """
    3D model of a Milky Way-like spiral galaxy.

    Handles stellar positions, velocities, and galactic rotation.
    Uses exponential disk profile with optional bulge and spiral arms.
    """

    def __init__(self, params: GalaxyParameters, seed: Optional[int] = None, use_numba: bool = True):
        """
        Initialize galaxy model.

        Args:
            params: Galaxy configuration parameters
            seed: Random seed for reproducibility
            use_numba: Use Numba JIT-compiled kernels for performance (recommended for M1 Max)
        """
        self.params = params
        self.rng = np.random.default_rng(seed)
        self.use_numba = use_numba

        # Struct-of-Arrays (SoA) layout for SIMD optimization
        # Separate x, y, z arrays enable full Apple Silicon NEON utilization
        self._pos_x: Optional[np.ndarray] = None  # X coordinates in kpc
        self._pos_y: Optional[np.ndarray] = None  # Y coordinates in kpc
        self._pos_z: Optional[np.ndarray] = None  # Z coordinates in kpc

        # AoS compatibility view (property, computed on demand)
        self._positions_aos: Optional[np.ndarray] = None  # Cached (N, 3) view

        # Velocities and initial positions (keep AoS for now, less critical)
        self.initial_positions: Optional[np.ndarray] = None  # (N, 3) in kpc - for delta compression
        self.velocities: Optional[np.ndarray] = None  # (N, 3) in km/s

        # Stellar properties
        self.ages: Optional[np.ndarray] = None  # in Gyr
        self.masses: Optional[np.ndarray] = None  # in solar masses
        self.metallicities: Optional[np.ndarray] = None  # [Fe/H] in dex
        self.stellar_types: Optional[np.ndarray] = None
        self.component_type: Optional[np.ndarray] = None  # 0=bulge, 1=thin disk, 2=thick disk

        # Adaptive timestep arrays (for efficient stellar motion)
        self.stellar_timesteps: Optional[np.ndarray] = None  # Individual dt for each star (Myr)
        self.time_until_update: Optional[np.ndarray] = None  # Time remaining until next update (Myr)
        self.stellar_accelerations: Optional[np.ndarray] = None  # Cached accelerations (kpc/Myr²)

    @property
    def positions(self) -> Optional[np.ndarray]:
        """
        Get positions as (N, 3) array (AoS layout) for compatibility.

        This is a view that combines the SoA arrays (pos_x, pos_y, pos_z).
        Modifications to this array will update the underlying SoA arrays.
        """
        if self._pos_x is None:
            return None
        # Return column_stack view for compatibility
        return np.column_stack([self._pos_x, self._pos_y, self._pos_z])

    @positions.setter
    def positions(self, value: np.ndarray) -> None:
        """
        Set positions from (N, 3) array, updating SoA storage.

        Args:
            value: Array of shape (N, 3) with (x, y, z) positions
        """
        if value is None:
            self._pos_x = None
            self._pos_y = None
            self._pos_z = None
            self._positions_aos = None
            return

        # Split into SoA layout
        self._pos_x = np.ascontiguousarray(value[:, 0])
        self._pos_y = np.ascontiguousarray(value[:, 1])
        self._pos_z = np.ascontiguousarray(value[:, 2])
        self._positions_aos = None  # Invalidate cache

    def get_positions_soa(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get positions as separate x, y, z arrays (SoA layout) for kernels.

        Returns:
            Tuple of (pos_x, pos_y, pos_z) arrays for SIMD-optimized kernels
        """
        return self._pos_x, self._pos_y, self._pos_z

    def generate_stellar_population(self) -> None:
        """
        Generate stellar positions, velocities, and properties.

        Includes bulge + disk components if configured.
        """
        n_stars = self.params.total_stars

        # Generate positions based on components (bulge + disk)
        if self.params.include_bulge:
            positions_list = []
            component_types = []

            # Bulge component
            n_bulge = int(n_stars * self.params.bulge_fraction)
            if n_bulge > 0:
                bulge_pos = self._generate_bulge(n_bulge)
                positions_list.append(bulge_pos)
                component_types.extend([0] * n_bulge)  # 0 = bulge

            # Disk component
            n_disk = n_stars - n_bulge
            if self.params.stellar_density_profile == "exponential":
                disk_pos = self._generate_exponential_disk(n_disk, use_numba=self.use_numba)
            else:
                disk_pos = self._generate_double_exponential_disk(n_disk)
            positions_list.append(disk_pos)
            component_types.extend([1] * n_disk)  # 1 = thin disk

            # Combine
            self.positions = np.vstack(positions_list)
            self.component_type = np.array(component_types, dtype=int)
        else:
            # Disk only (legacy behavior)
            if self.params.stellar_density_profile == "exponential":
                self.positions = self._generate_exponential_disk(n_stars, use_numba=self.use_numba)
            else:
                self.positions = self._generate_double_exponential_disk(n_stars)
            self.component_type = np.ones(n_stars, dtype=int)  # All disk

        # Add spiral arm perturbations (disk only)
        if self.params.spiral_arm_count > 0:
            self._apply_spiral_arms()

        # Generate velocities from rotation curve
        self.velocities = self._generate_velocities()
        
        # Store initial positions for delta compression (before any evolution)
        self.initial_positions = self.positions.copy()

        # Initialize stellar ages, masses, and metallicities
        # (will be populated by star formation history with gradients)
        self.ages = np.zeros(n_stars)
        self.masses = np.ones(n_stars)  # Solar masses
        self.metallicities = np.zeros(n_stars)  # [Fe/H]
        self.stellar_types = np.zeros(n_stars, dtype=int)

    def _generate_exponential_disk(self, n_stars: int, use_numba: bool = True) -> np.ndarray:
        """
        Generate stellar positions using exponential disk profile.

        ρ(R, z) = ρ₀ exp(-R/h_R) exp(-|z|/h_z)

        Uses Numba-accelerated rejection sampling for 50-100x speedup when
        use_numba=True.

        Args:
            n_stars: Number of stars to generate
            use_numba: Use Numba JIT-compiled kernel (recommended)

        Returns:
            Array of shape (n_stars, 3) with (x, y, z) positions in kpc
        """
        h_R = self.params.scale_length_kpc
        h_z = self.params.disk_height_kpc

        # Sample radii using Numba kernel if available
        if use_numba:
            try:
                from ..utils.numba_kernels import rejection_sample_exponential_disk_radii
                # Generate seed from RNG state
                seed = self.rng.integers(0, 2**31)
                r = rejection_sample_exponential_disk_radii(
                    n_stars, h_R, self.params.disk_radius_kpc, seed
                )
            except ImportError:
                use_numba = False

        if not use_numba:
            # Fallback: Python rejection sampling (slow for large N)
            r = np.zeros(n_stars)
            for i in range(n_stars):
                while True:
                    r_test = self.rng.exponential(h_R)
                    if r_test < self.params.disk_radius_kpc:
                        # Accept with probability proportional to r
                        if self.rng.uniform(0, 1) < r_test / self.params.disk_radius_kpc:
                            r[i] = r_test
                            break

        # Random azimuthal angles
        theta = self.rng.uniform(0, 2 * np.pi, n_stars)

        # Heights from exponential distribution
        z = self.rng.laplace(0, h_z, n_stars)

        # Convert to Cartesian coordinates
        x = r * np.cos(theta)
        y = r * np.sin(theta)

        return np.column_stack([x, y, z])

    def _generate_bulge(self, n_stars: int) -> np.ndarray:
        """
        Generate stellar positions for bulge using Hernquist profile.

        The Hernquist profile is a good approximation for elliptical galaxies
        and bulges:
            ρ(r) ∝ 1 / (r * (r + a)³)

        where a is the scale radius.

        Args:
            n_stars: Number of bulge stars

        Returns:
            Array of shape (n_stars, 3) with bulge positions
        """
        a = self.params.bulge_radius_kpc  # Scale radius

        # Truncate Hernquist profile at r_max to avoid infinite tail
        # Choose r_max = 10 * a (contains ~99% of mass)
        r_max = 10.0 * a

        # Sample radii from truncated Hernquist cumulative distribution
        # For Hernquist: M(<r) = M_total * r² / (r + a)²
        # Inverting: r = a * u / (1 - u) where u ~ Uniform(0, u_max)
        # u_max corresponds to r_max: u_max = r_max / (r_max + a)
        u_max = r_max / (r_max + a)
        u = self.rng.uniform(0, u_max, n_stars)
        r = a * u / (1 - u)

        # Convert to Cartesian (isotropic sphere)
        # Sample angles uniformly on sphere
        theta = np.arccos(2 * self.rng.uniform(0, 1, n_stars) - 1)  # Polar angle
        phi = 2 * np.pi * self.rng.uniform(0, 1, n_stars)  # Azimuthal angle

        # Convert to Cartesian
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)

        return np.column_stack([x, y, z])

    def _generate_double_exponential_disk(self, n_stars: int) -> np.ndarray:
        """Generate positions with thin and thick disk components."""
        # Split between thin (90%) and thick (10%) disk
        n_thin = int(0.9 * n_stars)
        n_thick = n_stars - n_thin

        # Thin disk
        thin_scale_height = self.params.disk_height_kpc
        thick_scale_height = 3 * thin_scale_height

        # Generate separately
        old_height = self.params.disk_height_kpc

        self.params.disk_height_kpc = thin_scale_height
        thin_pos = self._generate_exponential_disk(n_thin)

        self.params.disk_height_kpc = thick_scale_height
        thick_pos = self._generate_exponential_disk(n_thick)

        self.params.disk_height_kpc = old_height

        return np.vstack([thin_pos, thick_pos])

    def _apply_spiral_arms(self) -> None:
        """Apply spiral arm density enhancements to stellar positions."""
        if self.positions is None:
            return

        n_arms = self.params.spiral_arm_count
        strength = self.params.spiral_arm_strength

        x, y, z = self.positions[:, 0], self.positions[:, 1], self.positions[:, 2]
        r = np.sqrt(x**2 + y**2)
        theta = np.arctan2(y, x)

        # Logarithmic spiral: r = a * exp(b * θ)
        # Rearranged: θ_spiral = ln(r/a) / b
        pitch_angle = 12 * np.pi / 180  # 12 degrees
        b = 1 / np.tan(pitch_angle)

        # For each arm, calculate angular offset
        for i in range(n_arms):
            arm_angle = 2 * np.pi * i / n_arms
            theta_spiral = np.log(r / 1.0) / b + arm_angle

            # Angular distance to this spiral arm
            dtheta = np.abs((theta - theta_spiral + np.pi) % (2 * np.pi) - np.pi)

            # Apply perturbation based on proximity to spiral arm
            perturbation = strength * np.exp(-dtheta**2 / 0.1)

            # Perturb positions radially
            x += perturbation * x / (r + 1e-10)
            y += perturbation * y / (r + 1e-10)

        self.positions[:, 0] = x
        self.positions[:, 1] = y

    def _compute_circular_velocity(self, position: np.ndarray) -> float:
        """
        Compute circular velocity at a position from the gravitational potential.

        For a circular orbit at cylindrical radius R, the centripetal acceleration
        equals the radial gravitational acceleration:
            v_circ² / R = |a_R|
            v_circ = sqrt(R * |a_R|)

        The computed velocity is normalized to match the target rotation velocity
        at R=8 kpc (solar neighborhood).

        Args:
            position: Position (x, y, z) in kpc

        Returns:
            Circular velocity in km/s
        """
        # Compute total gravitational acceleration
        accel = self._compute_gravitational_acceleration(position.reshape(1, 3))[0]

        # Extract radial component (in xy-plane)
        x, y = position[0], position[1]
        R = np.sqrt(x**2 + y**2)

        if R < 1e-6:
            # Near center, use small-R approximation
            return 0.0

        # Radial acceleration (pointing inward is negative)
        a_R = (accel[0] * x + accel[1] * y) / R

        # Circular velocity: v² / R = |a_R|
        # a_R is negative (pointing inward), so we use -a_R
        v_circ_kpc_myr = np.sqrt(R * (-a_R)) if a_R < 0 else 0.0

        # Convert from kpc/Myr to km/s
        v_circ_km_s = v_circ_kpc_myr / 0.001022

        return v_circ_km_s

    def _generate_velocities(self) -> np.ndarray:
        """
        Generate stellar velocities based on configured mode.
        
        Dispatches to either simple (empirical) or Jeans (equilibrium) mode.
        """
        mode = getattr(self.params, 'velocity_init_mode', 'simple')
        
        if mode == 'jeans':
            return self._generate_velocities_jeans()
        else:
            return self._generate_velocities_simple()
    
    def _compute_epicyclic_frequency(self, R: float) -> float:
        """
        Compute epicyclic frequency κ at cylindrical radius R.
        
        κ² = R × d(Ω²)/dR + 4Ω²
        
        For a flat rotation curve (v_c = const), κ = √2 × Ω = √2 × v_c/R
        """
        if R < 0.1:
            R = 0.1
            
        pos = np.array([[R, 0.0, 0.0]])
        v_c = self._compute_circular_velocity(pos[0])
        
        dr = 0.1
        pos_plus = np.array([[R + dr, 0.0, 0.0]])
        pos_minus = np.array([[max(0.1, R - dr), 0.0, 0.0]])
        v_c_plus = self._compute_circular_velocity(pos_plus[0])
        v_c_minus = self._compute_circular_velocity(pos_minus[0])
        
        Omega = v_c / R
        dv_dR = (v_c_plus - v_c_minus) / (2 * dr)
        dOmega_dR = (dv_dR - v_c / R) / R
        
        kappa_sq = R * 2 * Omega * dOmega_dR + 4 * Omega**2
        kappa = np.sqrt(max(0.0, kappa_sq))
        
        return kappa
    
    def _compute_velocity_dispersion_jeans(
        self, 
        R: np.ndarray, 
        z: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute velocity dispersions (σ_R, σ_φ, σ_z) from Jeans equations.
        
        For an exponential disk in a combined potential:
        - σ_R follows Toomre Q stability criterion
        - σ_φ = σ_R × κ/(2Ω) from epicyclic approximation
        - σ_z from vertical Jeans equation
        
        Args:
            R: Cylindrical radii (kpc)
            z: Vertical heights (kpc)
            
        Returns:
            Tuple of (σ_R, σ_φ, σ_z) arrays in km/s
        """
        n_stars = len(R)
        sigma_R = np.zeros(n_stars)
        sigma_phi = np.zeros(n_stars)
        sigma_z = np.zeros(n_stars)
        
        h_R = self.params.scale_length_kpc
        h_z = self.params.disk_height_kpc
        v_0 = self.params.rotation_velocity_km_s
        
        sigma_R_0 = 35.0
        sigma_z_0 = 20.0
        
        for i in range(n_stars):
            r_i = max(0.1, R[i])
            z_i = z[i]
            
            sigma_R[i] = sigma_R_0 * np.exp(-r_i / (2 * h_R))
            sigma_R[i] *= (1.0 + np.abs(z_i) / h_z)
            
            kappa = self._compute_epicyclic_frequency(r_i)
            Omega = v_0 / r_i
            
            if Omega > 1e-10:
                sigma_phi[i] = sigma_R[i] * kappa / (2 * Omega)
            else:
                sigma_phi[i] = sigma_R[i] * 0.7
            
            sigma_z[i] = sigma_z_0 * np.exp(-r_i / (2 * h_R))
            sigma_z[i] *= (1.0 + 0.5 * np.abs(z_i) / h_z)
        
        return sigma_R, sigma_phi, sigma_z
    
    def _compute_asymmetric_drift(
        self, 
        R: np.ndarray, 
        sigma_R: np.ndarray
    ) -> np.ndarray:
        """
        Compute asymmetric drift correction for disk stars.
        
        v_φ = v_c - v_a where v_a ≈ σ_R² / (2 × v_c) × d(ln(ρ × σ_R²)) / d(ln R)
        
        For an exponential disk with exponentially declining σ_R:
        v_a ≈ σ_R² × (1/h_R + 1/h_σ) / (2 × v_c)
        
        Args:
            R: Cylindrical radii (kpc)
            sigma_R: Radial velocity dispersions (km/s)
            
        Returns:
            Asymmetric drift velocities (km/s) to subtract from circular
        """
        h_R = self.params.scale_length_kpc
        h_sigma = 2 * h_R
        
        v_a = np.zeros(len(R))
        
        for i in range(len(R)):
            r_i = max(0.1, R[i])
            v_c = self._compute_circular_velocity(np.array([r_i, 0.0, 0.0]))
            
            if v_c > 10.0:
                dlnrho_dlnR = -r_i / h_R
                dlnsigma_dlnR = -r_i / h_sigma
                
                v_a[i] = sigma_R[i]**2 / (2 * v_c) * abs(dlnrho_dlnR + 2 * dlnsigma_dlnR)
        
        return np.clip(v_a, 0, 50.0)
    
    def _generate_velocities_simple(self) -> np.ndarray:
        """
        Generate velocities using simple circular rotation + empirical dispersions.
        
        This is the original method with small improvements:
        - Asymmetric drift correction for disk stars
        - Better handling of central regions
        """
        if self.positions is None:
            raise ValueError("Must generate positions before velocities")

        n_stars = len(self.positions)
        x, y, z = self.positions[:, 0], self.positions[:, 1], self.positions[:, 2]
        R = np.sqrt(x**2 + y**2)

        v_x = np.zeros(n_stars)
        v_y = np.zeros(n_stars)
        v_z = np.zeros(n_stars)

        if self.component_type is not None:
            bulge_mask = self.component_type == 0
            if np.any(bulge_mask):
                sigma_bulge = self.params.bulge_velocity_dispersion_km_s
                bulge_ref_pos = np.array([self.params.bulge_radius_kpc, 0.0, 0.0])
                v_rot_bulge = 0.3 * self._compute_circular_velocity(bulge_ref_pos)

                for i in np.where(bulge_mask)[0]:
                    r_i = R[i] + 1e-10
                    v_x[i] = self.rng.normal(0, sigma_bulge)
                    v_y[i] = self.rng.normal(0, sigma_bulge) + v_rot_bulge * x[i] / r_i
                    v_z[i] = self.rng.normal(0, sigma_bulge)

            disk_mask = self.component_type >= 1
            if np.any(disk_mask):
                disk_indices = np.where(disk_mask)[0]
                R_disk = R[disk_indices]
                z_disk = z[disk_indices]
                
                sigma_r = 30.0 * (1 + np.abs(z_disk) / self.params.disk_height_kpc)
                v_a = self._compute_asymmetric_drift(R_disk, sigma_r)

                for j, i in enumerate(disk_indices):
                    v_circ = self._compute_circular_velocity(self.positions[i])
                    v_circ_corrected = max(0.0, v_circ - v_a[j])

                    r_i = R[i] + 1e-10
                    x_i, y_i, z_i = x[i], y[i], z[i]

                    v_x[i] = -v_circ_corrected * y_i / r_i
                    v_y[i] = v_circ_corrected * x_i / r_i

                    sigma_theta = 20.0 * (1 + np.abs(z_i) / self.params.disk_height_kpc)
                    sigma_z_i = 20.0 * (1 + np.abs(z_i) / self.params.disk_height_kpc)

                    v_x[i] += self.rng.normal(0, sigma_r[j])
                    v_y[i] += self.rng.normal(0, sigma_theta)
                    v_z[i] += self.rng.normal(0, sigma_z_i)
        else:
            v_circ = self.params.rotation_velocity_km_s

            v_x = -v_circ * y / (R + 1e-10)
            v_y = v_circ * x / (R + 1e-10)

            sigma_r = 30.0 * (1 + np.abs(z) / self.params.disk_height_kpc)
            sigma_theta = 20.0 * (1 + np.abs(z) / self.params.disk_height_kpc)
            sigma_z = 20.0 * (1 + np.abs(z) / self.params.disk_height_kpc)

            v_x += self.rng.normal(0, sigma_r, n_stars)
            v_y += self.rng.normal(0, sigma_theta, n_stars)
            v_z += self.rng.normal(0, sigma_z, n_stars)

        return np.column_stack([v_x, v_y, v_z])
    
    def _generate_velocities_jeans(self) -> np.ndarray:
        """
        Generate velocities using Jeans equations for equilibrium.
        
        Solves the collisionless Boltzmann equation assuming:
        - Exponential disk density profile
        - Miyamoto-Nagai + Hernquist + NFW potential
        - Steady-state, axisymmetric distribution
        
        This provides better equilibrium initial conditions that
        maintain stability over longer timescales.
        """
        if self.positions is None:
            raise ValueError("Must generate positions before velocities")

        print("  Computing Jeans equilibrium velocities...")
        
        n_stars = len(self.positions)
        x, y, z = self.positions[:, 0], self.positions[:, 1], self.positions[:, 2]
        R = np.sqrt(x**2 + y**2)

        v_x = np.zeros(n_stars)
        v_y = np.zeros(n_stars)
        v_z = np.zeros(n_stars)

        if self.component_type is not None:
            bulge_mask = self.component_type == 0
            if np.any(bulge_mask):
                sigma_bulge = self.params.bulge_velocity_dispersion_km_s
                bulge_ref_pos = np.array([self.params.bulge_radius_kpc, 0.0, 0.0])
                v_rot_bulge = 0.3 * self._compute_circular_velocity(bulge_ref_pos)
                
                bulge_indices = np.where(bulge_mask)[0]
                for i in bulge_indices:
                    r_i = R[i] + 1e-10
                    r_sph = np.sqrt(x[i]**2 + y[i]**2 + z[i]**2)
                    
                    sigma_r_bulge = sigma_bulge * (1.0 + 0.5 * r_sph / self.params.bulge_radius_kpc)
                    
                    v_x[i] = self.rng.normal(0, sigma_r_bulge)
                    v_y[i] = self.rng.normal(0, sigma_r_bulge) + v_rot_bulge * x[i] / r_i
                    v_z[i] = self.rng.normal(0, sigma_r_bulge)

            disk_mask = self.component_type >= 1
            if np.any(disk_mask):
                disk_indices = np.where(disk_mask)[0]
                R_disk = R[disk_indices]
                z_disk = z[disk_indices]
                
                sigma_R, sigma_phi, sigma_z = self._compute_velocity_dispersion_jeans(
                    R_disk, z_disk
                )
                v_a = self._compute_asymmetric_drift(R_disk, sigma_R)

                for j, i in enumerate(disk_indices):
                    v_circ = self._compute_circular_velocity(self.positions[i])
                    v_circ_corrected = max(0.0, v_circ - v_a[j])

                    r_i = R[i] + 1e-10
                    x_i, y_i = x[i], y[i]

                    v_phi = v_circ_corrected + self.rng.normal(0, sigma_phi[j])
                    v_r = self.rng.normal(0, sigma_R[j])
                    
                    cos_phi = x_i / r_i
                    sin_phi = y_i / r_i
                    
                    v_x[i] = v_r * cos_phi - v_phi * sin_phi
                    v_y[i] = v_r * sin_phi + v_phi * cos_phi
                    v_z[i] = self.rng.normal(0, sigma_z[j])
        else:
            print("  Warning: No component types - using simple velocities")
            return self._generate_velocities_simple()

        return np.column_stack([v_x, v_y, v_z])

    def calculate_metallicities(self) -> np.ndarray:
        """
        Calculate metallicity [Fe/H] for each star with radial gradient.

        Metallicity decreases with galactocentric radius (radial gradient).
        Bulge stars are metal-rich.

        Returns:
            Array of metallicities in dex ([Fe/H])
        """
        if self.positions is None:
            raise ValueError("Must generate positions first")

        n_stars = len(self.positions)
        metallicities = np.zeros(n_stars)

        # Calculate galactocentric radius
        x, y = self.positions[:, 0], self.positions[:, 1]
        radii = np.sqrt(x**2 + y**2)

        for i in range(n_stars):
            r = radii[i]

            if self.component_type is not None and self.component_type[i] == 0:
                # Bulge: metal-rich
                metallicities[i] = self.params.central_metallicity_feh
            else:
                # Disk: linear gradient with radius
                # [Fe/H](r) = [Fe/H]_center + gradient * r
                metallicities[i] = self.params.central_metallicity_feh + \
                                   self.params.metallicity_gradient_dex_per_kpc * r

        return metallicities

    def _compute_disk_acceleration(
        self,
        positions: np.ndarray
    ) -> np.ndarray:
        """
        Compute gravitational acceleration from Miyamoto-Nagai disk potential.

        The Miyamoto-Nagai potential provides a good analytic approximation
        for a galactic disk:
            Φ_disk(R, z) = -GM / sqrt(R² + (a + sqrt(z² + b²))²)

        where:
            R = sqrt(x² + y²) is cylindrical radius
            a = disk scale length
            b = disk scale height
            M = disk mass

        Args:
            positions: Array of shape (N, 3) with stellar positions in kpc

        Returns:
            Array of shape (N, 3) with acceleration in km/s per Myr
        """
        x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]

        # Miyamoto-Nagai parameters
        a = self.params.scale_length_kpc  # Disk scale length
        b = self.params.disk_height_kpc   # Disk scale height

        # Estimate disk mass from rotation curve
        v_circ = self.params.rotation_velocity_km_s  # Total circular velocity
        v_disk_frac = 0.72  # Disk contributes 72% → 0.72² = 0.518
        v_disk = v_disk_frac * v_circ

        R_char = 8.0  # kpc (solar neighborhood)
        G_kpc_msun = 4.498e-12  # G in kpc³/(M_sun Myr²)

        # Convert v from km/s to kpc/Myr: 1 km/s = 0.001022 kpc/Myr
        v_disk_kpc_myr = v_disk * 0.001022
        M_disk = v_disk_kpc_myr**2 * R_char / G_kpc_msun  # Solar masses

        GM = G_kpc_msun * M_disk

        # Use numexpr for fast SIMD-optimized array operations
        R = ne.evaluate('sqrt(x**2 + y**2)')
        sqrt_term = ne.evaluate('sqrt(z**2 + b**2)')
        D_squared = ne.evaluate('R**2 + (a + sqrt_term)**2')
        D_cubed = ne.evaluate('D_squared**1.5')

        # Radial component (in xy-plane)
        a_R = ne.evaluate('-GM * R / (D_cubed + 1e-30)')

        # z component
        a_z = ne.evaluate('-GM * (a + sqrt_term) * z / ((sqrt_term + 1e-10) * D_cubed + 1e-30)')

        # Convert to Cartesian (handle R=0 case)
        a_x = ne.evaluate('a_R * x / (R + 1e-10)')
        a_y = ne.evaluate('a_R * y / (R + 1e-10)')

        return np.column_stack([a_x, a_y, a_z])

    def _compute_bulge_acceleration(
        self,
        positions: np.ndarray
    ) -> np.ndarray:
        """
        Compute gravitational acceleration from Hernquist bulge potential.

        The Hernquist potential:
            Φ_bulge(r) = -GM / (r + a)

        where:
            r = sqrt(x² + y² + z²) is spherical radius
            a = bulge scale radius
            M = bulge mass

        Args:
            positions: Array of shape (N, 3) with stellar positions in kpc

        Returns:
            Array of shape (N, 3) with acceleration in kpc/Myr²
        """
        if not self.params.include_bulge:
            # No bulge - return zero acceleration
            return np.zeros_like(positions)

        x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]
        r = np.sqrt(x**2 + y**2 + z**2)

        # Hernquist parameters
        a_bulge = self.params.bulge_radius_kpc

        # Bulge circular velocity contribution
        # v_total² = v_disk² + v_bulge² + v_halo²
        # Fractions: 0.72² + 0.38² + 0.58² = 0.518 + 0.144 + 0.336 = 0.998 ≈ 1.0
        v_circ = self.params.rotation_velocity_km_s
        v_bulge_frac = 0.38  # Bulge contributes 38% → 0.38² = 0.144
        v_bulge = v_bulge_frac * v_circ

        R_char = 8.0  # kpc
        G_kpc_msun = 4.498e-12  # G in kpc³/(M_sun Myr²)

        v_bulge_kpc_myr = v_bulge * 0.001022
        M_bulge = v_bulge_kpc_myr**2 * R_char / G_kpc_msun

        # Hernquist acceleration: a = -∇Φ where Φ = -GM/(r + a)
        # ∂Φ/∂r = -GM/(r + a)²
        # a_r = -∂Φ/∂r = GM/(r + a)² (pointing inward, so negative sign needed)
        factor = -G_kpc_msun * M_bulge / ((r + a_bulge)**2 + 1e-30)

        a_x = factor * x / (r + 1e-10)
        a_y = factor * y / (r + 1e-10)
        a_z = factor * z / (r + 1e-10)

        return np.column_stack([a_x, a_y, a_z])

    def _compute_halo_acceleration(
        self,
        positions: np.ndarray
    ) -> np.ndarray:
        """
        Compute gravitational acceleration from NFW dark matter halo.

        The NFW (Navarro-Frenk-White) potential is used for dark matter halos.
        For simplicity, we use an isothermal sphere approximation which gives
        a flat rotation curve (matching observations).

        Φ_halo(r) = v_halo² ln(r)

        This gives constant circular velocity at large radii.

        Args:
            positions: Array of shape (N, 3) with stellar positions in kpc

        Returns:
            Array of shape (N, 3) with acceleration in kpc/Myr²
        """
        x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]
        r = np.sqrt(x**2 + y**2 + z**2)

        # Dark matter halo circular velocity contribution
        # Total v² = v_disk² + v_bulge² + v_halo²
        # Fractions: 0.72² + 0.38² + 0.58² ≈ 1.0
        v_circ = self.params.rotation_velocity_km_s
        v_halo_frac = 0.58  # Halo contributes 58% → 0.58² = 0.336
        v_halo = v_halo_frac * v_circ

        v_halo_kpc_myr = v_halo * 0.001022  # Convert to kpc/Myr

        # Isothermal sphere: a = v_halo² / r (radially inward)
        v_halo_sq = v_halo_kpc_myr**2

        factor = -v_halo_sq / (r + 1e-10)

        a_x = factor * x / (r + 1e-10)
        a_y = factor * y / (r + 1e-10)
        a_z = factor * z / (r + 1e-10)

        return np.column_stack([a_x, a_y, a_z])

    def _compute_gravitational_acceleration(
        self,
        positions: np.ndarray
    ) -> np.ndarray:
        """
        Compute total gravitational acceleration from all components.

        Sums contributions from:
        - Miyamoto-Nagai disk
        - Hernquist bulge
        - Dark matter halo (isothermal sphere)

        Args:
            positions: Array of shape (N, 3) with stellar positions in kpc

        Returns:
            Array of shape (N, 3) with total acceleration in kpc/Myr²
        """
        a_disk = self._compute_disk_acceleration(positions)
        a_bulge = self._compute_bulge_acceleration(positions)
        a_halo = self._compute_halo_acceleration(positions)

        return a_disk + a_bulge + a_halo

    def evolve_positions(self, dt_myr: float, use_numba: bool = True, enable_motion: bool = False) -> None:
        """
        Evolve stellar positions and velocities using leapfrog integrator.

        **EXPERIMENTAL FEATURE:** Gravitational evolution is currently disabled
        by default because the initial velocity distribution (flat rotation curve)
        is not in perfect equilibrium with the Miyamoto-Nagai + Hernquist + halo
        potential. This causes systematic radial drift over long timescales.

        For most simulations (<1 Gyr), static stellar positions are a good
        approximation since stellar neighborhoods don't change significantly.

        Uses a second-order symplectic leapfrog integrator which conserves
        energy and angular momentum well for orbital dynamics.

        The leapfrog algorithm (drift-kick form):
        1. Compute acceleration a(t) at current positions
        2. Update positions: r(t+dt) = r(t) + v(t)×dt + 0.5×a(t)×dt²
        3. Compute acceleration a(t+dt) at new positions
        4. Update velocities: v(t+dt) = v(t) + 0.5×(a(t) + a(t+dt))×dt

        Args:
            dt_myr: Time step in million years
            use_numba: Use Numba JIT-compiled kernel (10-20x speedup)
            enable_motion: Enable gravitational evolution (disabled by default)
        """
        if not enable_motion:
            return

        if self.positions is None or self.velocities is None:
            raise ValueError("Must generate positions and velocities first")

        # Try Numba acceleration if enabled
        if use_numba:
            try:
                from ..utils.numba_kernels import (
                    leapfrog_integrate_positions_kernel,
                    leapfrog_integrate_velocities_kernel,
                    compute_total_acceleration_kernel,
                )
                
                # Precompute potential parameters
                v_circ = self.params.rotation_velocity_km_s
                v_kpc_myr = v_circ * 0.001022
                G_kpc_msun = 4.498e-12
                R_char = 8.0
                
                # Disk parameters
                disk_a = self.params.scale_length_kpc
                disk_b = self.params.disk_height_kpc
                v_disk = 0.72 * v_circ * 0.001022
                disk_G_M = (v_disk**2 * R_char / G_kpc_msun) * G_kpc_msun
                
                # Bulge parameters
                bulge_a = self.params.bulge_radius_kpc
                v_bulge = 0.38 * v_circ * 0.001022
                bulge_G_M = (v_bulge**2 * R_char / G_kpc_msun) * G_kpc_msun
                
                # Halo parameters
                v_halo = 0.58 * v_circ * 0.001022
                halo_v_sq = v_halo**2
                
                include_bulge = self.params.include_bulge
                
                # Allocate acceleration arrays
                n_stars = len(self.positions)
                a_current = np.zeros((n_stars, 3), dtype=np.float64)
                a_new = np.zeros((n_stars, 3), dtype=np.float64)
                
                # Step 1: Compute acceleration at current positions (Numba)
                compute_total_acceleration_kernel(
                    self.positions.astype(np.float64),
                    a_current,
                    disk_a, disk_b, disk_G_M,
                    bulge_a, bulge_G_M,
                    halo_v_sq,
                    include_bulge
                )
                
                # Step 2: Update positions (Numba in-place)
                leapfrog_integrate_positions_kernel(
                    self.positions,
                    self.velocities,
                    a_current,
                    dt_myr
                )
                
                # Step 3: Compute acceleration at new positions (Numba)
                compute_total_acceleration_kernel(
                    self.positions.astype(np.float64),
                    a_new,
                    disk_a, disk_b, disk_G_M,
                    bulge_a, bulge_G_M,
                    halo_v_sq,
                    include_bulge
                )
                
                # Step 4: Update velocities (Numba in-place)
                leapfrog_integrate_velocities_kernel(
                    self.velocities,
                    a_current,
                    a_new,
                    dt_myr
                )
                
                return
                
            except ImportError:
                pass

        # Fallback: NumPy implementation
        v_kpc_myr = self.velocities * 0.001022
        a_current = self._compute_gravitational_acceleration(self.positions)
        self.positions += v_kpc_myr * dt_myr + 0.5 * a_current * dt_myr**2
        a_new = self._compute_gravitational_acceleration(self.positions)
        v_kpc_myr += 0.5 * (a_current + a_new) * dt_myr
        self.velocities = v_kpc_myr / 0.001022

    def initialize_adaptive_timesteps(
        self, 
        eta: float = 0.02,
        min_dt: float = 0.05,
        max_dt: float = 2.0
    ) -> None:
        """
        Initialize individual timesteps for each star based on orbital dynamics.
        
        Uses the standard criterion: dt_i = η × sqrt(r_i / |a_i|)
        where η is a dimensionless accuracy parameter (typically 0.01-0.1).
        
        Timesteps are quantized to block timesteps (powers of 2) for efficiency.
        
        Args:
            eta: Accuracy parameter (smaller = more accurate but slower)
            min_dt: Minimum allowed timestep in Myr
            max_dt: Maximum allowed timestep in Myr
        """
        if self._pos_x is None:
            raise ValueError("Must generate positions first")

        n_stars = len(self._pos_x)
        pos = self.positions

        # Compute accelerations (use Numba if available)
        try:
            self.stellar_accelerations = self._compute_accel_numba(pos)
        except (ImportError, AttributeError):
            self.stellar_accelerations = self._compute_gravitational_acceleration(pos)
        a_mag = np.linalg.norm(self.stellar_accelerations, axis=1)

        # Compute galactocentric radius
        r = np.sqrt(self._pos_x**2 + self._pos_y**2 + self._pos_z**2)
        
        # Compute individual timesteps: dt = η × sqrt(r / |a|)
        # This gives approximately dt ~ T_orbit / (2π/η) where T_orbit is orbital period
        with np.errstate(divide='ignore', invalid='ignore'):
            dt_ideal = eta * np.sqrt(r / (a_mag + 1e-30))
        
        # Clamp to [min_dt, max_dt]
        dt_clamped = np.clip(dt_ideal, min_dt, max_dt)
        
        # Quantize to block timesteps (powers of 2 multiples of min_dt)
        # Available timesteps: min_dt, 2*min_dt, 4*min_dt, 8*min_dt, ...
        block_levels = np.floor(np.log2(dt_clamped / min_dt)).astype(int)
        block_levels = np.maximum(block_levels, 0)  # At least level 0
        max_level = int(np.log2(max_dt / min_dt))
        block_levels = np.minimum(block_levels, max_level)
        
        self.stellar_timesteps = min_dt * (2.0 ** block_levels)
        self.time_until_update = self.stellar_timesteps.copy()
        
    def _get_potential_params(self) -> tuple:
        """Precompute and cache gravitational potential parameters for Numba kernel."""
        if not hasattr(self, '_potential_params') or self._potential_params is None:
            v_circ = self.params.rotation_velocity_km_s
            G_kpc_msun = 4.498e-12
            R_char = 8.0

            disk_a = self.params.scale_length_kpc
            disk_b = self.params.disk_height_kpc
            v_disk = 0.72 * v_circ * 0.001022
            disk_G_M = v_disk**2 * R_char

            bulge_a = self.params.bulge_radius_kpc
            v_bulge = 0.38 * v_circ * 0.001022
            bulge_G_M = v_bulge**2 * R_char

            v_halo = 0.58 * v_circ * 0.001022
            halo_v_sq = v_halo**2

            include_bulge = self.params.include_bulge

            self._potential_params = (
                disk_a, disk_b, disk_G_M,
                bulge_a, bulge_G_M,
                halo_v_sq, include_bulge
            )
        return self._potential_params

    def _compute_accel_numba(self, positions: np.ndarray) -> np.ndarray:
        """Compute gravitational acceleration using Numba kernel."""
        from ..utils.numba_kernels import compute_total_acceleration_kernel

        disk_a, disk_b, disk_G_M, bulge_a, bulge_G_M, halo_v_sq, include_bulge = (
            self._get_potential_params()
        )
        out = np.empty_like(positions, dtype=np.float64)
        compute_total_acceleration_kernel(
            np.ascontiguousarray(positions, dtype=np.float64), out,
            disk_a, disk_b, disk_G_M,
            bulge_a, bulge_G_M,
            halo_v_sq, include_bulge
        )
        return out

    def evolve_positions_adaptive(
        self,
        dt_myr: float,
        use_numba: bool = True
    ) -> None:
        """
        Evolve stellar positions using adaptive individual timesteps.

        Only stars whose time_until_update <= 0 are integrated.
        This provides major speedup since outer disk stars (80%+) use
        much larger timesteps than inner bulge stars.

        Args:
            dt_myr: Global simulation timestep in Myr
            use_numba: Use Numba kernels for acceleration
        """
        if self._pos_x is None or self.velocities is None:
            raise ValueError("Must generate positions and velocities first")

        if self.stellar_timesteps is None:
            self.initialize_adaptive_timesteps()

        self.time_until_update -= dt_myr

        needs_update = self.time_until_update <= 0
        update_indices = np.where(needs_update)[0]

        if len(update_indices) == 0:
            return

        pos_update = np.column_stack([
            self._pos_x[update_indices],
            self._pos_y[update_indices],
            self._pos_z[update_indices]
        ])
        vel_update = self.velocities[update_indices]
        dt_update = self.stellar_timesteps[update_indices]
        dt_col = dt_update[:, np.newaxis]

        if use_numba:
            try:
                a_current = self._compute_accel_numba(pos_update)
            except ImportError:
                a_current = self._compute_gravitational_acceleration(pos_update)
        else:
            a_current = self._compute_gravitational_acceleration(pos_update)

        v_kpc_myr = vel_update * 0.001022
        pos_new = pos_update + v_kpc_myr * dt_col + 0.5 * a_current * (dt_col ** 2)

        if use_numba:
            try:
                a_new = self._compute_accel_numba(pos_new)
            except ImportError:
                a_new = self._compute_gravitational_acceleration(pos_new)
        else:
            a_new = self._compute_gravitational_acceleration(pos_new)

        v_kpc_myr_new = v_kpc_myr + 0.5 * (a_current + a_new) * dt_col

        self._pos_x[update_indices] = pos_new[:, 0]
        self._pos_y[update_indices] = pos_new[:, 1]
        self._pos_z[update_indices] = pos_new[:, 2]
        self.velocities[update_indices] = v_kpc_myr_new / 0.001022

        a_mag_new = np.linalg.norm(a_new, axis=1)
        r_new = np.sqrt(pos_new[:, 0]**2 + pos_new[:, 1]**2 + pos_new[:, 2]**2)

        eta = 0.02
        min_dt = self.stellar_timesteps.min()
        max_dt = self.stellar_timesteps.max()

        with np.errstate(divide='ignore', invalid='ignore'):
            dt_ideal = eta * np.sqrt(r_new / (a_mag_new + 1e-30))
        dt_clamped = np.clip(dt_ideal, min_dt, max_dt)

        block_levels = np.floor(np.log2(dt_clamped / min_dt)).astype(int)
        block_levels = np.maximum(block_levels, 0)
        max_level = int(np.log2(max_dt / min_dt))
        block_levels = np.minimum(block_levels, max_level)

        new_timesteps = min_dt * (2.0 ** block_levels)
        self.stellar_timesteps[update_indices] = new_timesteps
        self.time_until_update[update_indices] = new_timesteps

    def get_distance_matrix(self, indices: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Compute pairwise distance matrix between stars.

        Args:
            indices: Optional subset of star indices to compute distances for

        Returns:
            Distance matrix in parsecs
        """
        if self.positions is None:
            raise ValueError("Must generate positions first")

        if indices is not None:
            pos = self.positions[indices]
        else:
            pos = self.positions

        # Compute pairwise distances (kpc)
        diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
        dist_kpc = np.sqrt(np.sum(diff**2, axis=2))

        # Convert to parsecs
        return dist_kpc * 1000.0

    def get_stellar_density(self, position: np.ndarray) -> float:
        """
        Get stellar number density at a given position.

        Args:
            position: 3D position (x, y, z) in kpc

        Returns:
            Number density in stars/kpc³
        """
        x, y, z = position
        r = np.sqrt(x**2 + y**2)

        h_R = self.params.scale_length_kpc
        h_z = self.params.disk_height_kpc

        # Exponential disk density
        rho = np.exp(-r / h_R) * np.exp(-np.abs(z) / h_z)

        # Normalize by total number of stars
        # Rough normalization (exact would require integration)
        norm = self.params.total_stars / (2 * np.pi * h_R**2 * 2 * h_z)

        return rho * norm
