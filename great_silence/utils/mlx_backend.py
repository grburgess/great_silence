"""
MLX (Apple GPU) acceleration backend for The Great Silence.

Mirrors the Miyamoto-Nagai disk + Hernquist bulge + isothermal halo math of
``compute_total_acceleration_kernel`` in ``numba_kernels.py`` using ``mlx.core``
array operations. Every caller must fall back to the Numba path when
``mlx_available()`` is False.

Units: positions kpc; accelerations kpc/Myr².
"""

from typing import Optional, Tuple

import numpy as np

_MLX_AVAILABLE: Optional[bool] = None


def mlx_available() -> bool:
    """Return True if the optional ``mlx`` package can be imported."""
    global _MLX_AVAILABLE
    if _MLX_AVAILABLE is None:
        try:
            import mlx.core  # noqa: F401

            _MLX_AVAILABLE = True
        except ImportError:
            _MLX_AVAILABLE = False
    return _MLX_AVAILABLE


def compute_total_acceleration_mlx(positions: np.ndarray, params: Tuple) -> np.ndarray:
    """
    Compute total gravitational acceleration on Apple GPU via MLX.

    Args:
        positions: (N, 3) positions in kpc
        params: potential params matching ``_get_potential_params``:
            (disk_a, disk_b, disk_G_M, bulge_a, bulge_G_M, halo_v_sq, include_bulge)

    Returns:
        (N, 3) acceleration in kpc/Myr² as a NumPy array.
    """
    import mlx.core as mx

    disk_a, disk_b, disk_G_M, bulge_a, bulge_G_M, halo_v_sq, include_bulge = params

    pos = mx.array(np.ascontiguousarray(positions, dtype=np.float32))
    x = pos[:, 0]
    y = pos[:, 1]
    z = pos[:, 2]

    R_sq = x * x + y * y
    R = mx.sqrt(R_sq)
    r = mx.sqrt(R_sq + z * z)

    R_pos = R > 1e-10
    R_safe = mx.where(R_pos, R, 1.0)
    r_pos = r > 1e-10
    r_safe = mx.where(r_pos, r, 1.0)

    sqrt_term = mx.sqrt(z * z + disk_b * disk_b)
    D_sq = R_sq + (disk_a + sqrt_term) * (disk_a + sqrt_term)
    D_cubed = D_sq * mx.sqrt(D_sq) + 1e-30

    a_R_disk = -disk_G_M * R / D_cubed
    a_z_disk = -disk_G_M * (disk_a + sqrt_term) * z / ((sqrt_term + 1e-10) * D_cubed)

    ax = mx.where(R_pos, a_R_disk * x / R_safe, 0.0)
    ay = mx.where(R_pos, a_R_disk * y / R_safe, 0.0)
    az = a_z_disk

    if include_bulge:
        factor_bulge = -bulge_G_M / ((r + bulge_a) * (r + bulge_a) + 1e-30)
        ax = ax + mx.where(r_pos, factor_bulge * x / r_safe, 0.0)
        ay = ay + mx.where(r_pos, factor_bulge * y / r_safe, 0.0)
        az = az + mx.where(r_pos, factor_bulge * z / r_safe, 0.0)

    factor_halo = -halo_v_sq / (r + 1e-10)
    ax = ax + mx.where(r_pos, factor_halo * x / r_safe, 0.0)
    ay = ay + mx.where(r_pos, factor_halo * y / r_safe, 0.0)
    az = az + mx.where(r_pos, factor_halo * z / r_safe, 0.0)

    out = mx.stack([ax, ay, az], axis=1)
    mx.eval(out)
    return np.array(out, dtype=np.float64)
