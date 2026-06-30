"""Closed-form epicyclic orbit model for fast stellar position evolution.

The galactic potential is fixed, time-constant, and axisymmetric, so every star
follows an independent epicyclic orbit that can be characterized once at
initialization. Each orbit is described by a guiding-center radius and small
radial/vertical oscillations, giving an analytic ``positions_at_time`` primitive.

Units:
    positions: kpc
    velocities (input): km/s, converted internally to kpc/Myr
    frequencies (Omega, kappa, nu): 1/Myr
    time: Myr
"""

import numpy as np

KMS_TO_KPC_MYR = 0.001022


class EpicyclicOrbitModel:
    """Per-star epicyclic orbit parameters with closed-form time evolution."""

    def __init__(self, R_g, Omega_g, kappa, nu, X, alpha, phi_g0, Z, beta):
        self.R_g, self.Omega_g, self.kappa, self.nu = R_g, Omega_g, kappa, nu
        self.X, self.alpha, self.phi_g0, self.Z, self.beta = X, alpha, phi_g0, Z, beta

    @classmethod
    def from_galaxy(cls, galaxy):
        pos = galaxy.positions
        vel = galaxy.velocities * KMS_TO_KPC_MYR
        x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
        R = np.sqrt(x**2 + y**2)
        R = np.maximum(R, 1e-6)
        phi = np.arctan2(y, x)
        v_R = (vel[:, 0] * x + vel[:, 1] * y) / R
        v_phi = (-vel[:, 0] * y + vel[:, 1] * x) / R
        v_z = vel[:, 2]
        L_z = R * v_phi

        R_g = cls._guiding_radius(galaxy, R, L_z)
        vc_g = (
            galaxy._compute_circular_velocities_batch(
                np.column_stack([R_g, np.zeros_like(R_g), np.zeros_like(R_g)])
            )
            * KMS_TO_KPC_MYR
        )
        Omega_g = vc_g / R_g
        kappa = np.maximum(galaxy.epicyclic_frequencies_batch(R_g) * KMS_TO_KPC_MYR, 1e-9)
        nu = np.maximum(galaxy.vertical_frequencies_batch(R_g), 1e-9)

        dR = R - R_g
        X = np.sqrt(dR**2 + (v_R / kappa) ** 2)
        alpha = np.arctan2(-v_R / kappa, dR)
        gamma = 2.0 * Omega_g / (kappa * R_g)
        phi_g0 = phi + gamma * X * np.sin(alpha) / R_g
        Z = np.sqrt(z**2 + (v_z / nu) ** 2)
        beta = np.arctan2(-v_z / nu, z)
        return cls(R_g, Omega_g, kappa, nu, X, alpha, phi_g0, Z, beta)

    @staticmethod
    def _guiding_radius(galaxy, R0, L_z, iters=12):
        Rg = np.maximum(R0.copy(), 0.1)
        for _ in range(iters):
            vc = (
                galaxy._compute_circular_velocities_batch(
                    np.column_stack([Rg, np.zeros_like(Rg), np.zeros_like(Rg)])
                )
                * KMS_TO_KPC_MYR
            )
            f = Rg * vc - L_z
            dR = 0.05
            vc2 = (
                galaxy._compute_circular_velocities_batch(
                    np.column_stack([Rg + dR, np.zeros_like(Rg), np.zeros_like(Rg)])
                )
                * KMS_TO_KPC_MYR
            )
            df = ((Rg + dR) * vc2 - L_z - f) / dR
            Rg = np.clip(Rg - f / np.where(np.abs(df) < 1e-9, 1e-9, df), 0.1, 50.0)
        return Rg

    def positions_at_time(self, t_myr):
        ph_R = self.kappa * t_myr + self.alpha
        R = self.R_g + self.X * np.cos(ph_R)
        gamma = 2.0 * self.Omega_g / (self.kappa * self.R_g)
        phi = self.phi_g0 + self.Omega_g * t_myr - gamma * self.X * np.sin(ph_R) / self.R_g
        z = self.Z * np.cos(self.nu * t_myr + self.beta)
        return np.column_stack([R * np.cos(phi), R * np.sin(phi), z])

    def params_dict(self):
        return {
            "R_g": self.R_g,
            "Omega_g": self.Omega_g,
            "kappa": self.kappa,
            "nu": self.nu,
            "X": self.X,
            "alpha": self.alpha,
            "phi_g0": self.phi_g0,
            "Z": self.Z,
            "beta": self.beta,
        }
