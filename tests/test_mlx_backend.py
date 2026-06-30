import numpy as np
import pytest

from great_silence.config import SimulationConfig
from great_silence.galaxy.structure import GalaxyModel
from great_silence.utils.numba_kernels import compute_total_acceleration_kernel

pytest.importorskip("mlx.core")

from great_silence.utils.mlx_backend import compute_total_acceleration_mlx, mlx_available


@pytest.fixture
def galaxy_params():
    cfg = SimulationConfig()
    cfg.galaxy.total_stars = 1000
    g = GalaxyModel(cfg.galaxy, seed=0)
    g.generate_stellar_population()
    return g._get_potential_params()


def test_mlx_available_true():
    assert mlx_available() is True


def test_mlx_matches_numba(galaxy_params):
    pos = np.random.default_rng(0).uniform(-10, 10, (4000, 3))
    out = np.zeros_like(pos)
    compute_total_acceleration_kernel(pos, out, *galaxy_params)
    mlx_out = compute_total_acceleration_mlx(pos, galaxy_params)
    assert mlx_out.shape == pos.shape
    assert np.allclose(out, mlx_out, rtol=1e-4, atol=1e-8)


def test_structure_gpu_dispatch_matches_cpu():
    cfg = SimulationConfig()
    cfg.galaxy.total_stars = 1000
    g = GalaxyModel(cfg.galaxy, seed=0)
    g.generate_stellar_population()

    pos = g.positions
    g._orbit_use_gpu = False
    cpu = g._compute_accel_numba(pos)
    g._orbit_use_gpu = True
    gpu = g._compute_accel_numba(pos)
    assert np.allclose(cpu, gpu, rtol=1e-4, atol=1e-8)
