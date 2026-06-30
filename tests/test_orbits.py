import numpy as np
from great_silence.galaxy.orbits import EpicyclicOrbitModel

from great_silence.config import SimulationConfig
from great_silence.galaxy.structure import GalaxyModel


def _make_galaxy(n=2000, seed=1):
    cfg = SimulationConfig()
    cfg.galaxy.total_stars = n
    g = GalaxyModel(cfg.galaxy, seed=seed)
    g.generate_stellar_population()
    return g


def test_epicyclic_frequency_batch_matches_scalar():
    g = _make_galaxy()
    R = np.array([2.0, 4.0, 8.0, 12.0])
    kappa_batch = g.epicyclic_frequencies_batch(R)
    kappa_scalar = np.array([g._compute_epicyclic_frequency(r) for r in R])
    assert np.allclose(kappa_batch, kappa_scalar, rtol=0.05)


def test_vertical_frequency_positive_and_decreasing():
    g = _make_galaxy()
    R = np.array([1.0, 4.0, 8.0, 14.0])
    nu = g.vertical_frequencies_batch(R)
    assert np.all(nu > 0)
    assert nu[0] > nu[-1]


def test_positions_at_zero_match_initial():
    g = _make_galaxy(n=1500)
    orb = EpicyclicOrbitModel.from_galaxy(g)
    pos0 = orb.positions_at_time(0.0)
    assert np.allclose(pos0, g.positions, atol=0.05)


def test_circular_orbit_conserves_radius():
    g = _make_galaxy(n=800)
    g._pos_z[:] = 0.0
    R = np.sqrt(g._pos_x**2 + g._pos_y**2)
    vc = g._compute_circular_velocities_batch(g.positions)
    phi = np.arctan2(g._pos_y, g._pos_x)
    vx = -vc * np.sin(phi)
    vy = vc * np.cos(phi)
    g.velocities = np.column_stack([vx, vy, np.zeros_like(vx)])
    orb = EpicyclicOrbitModel.from_galaxy(g)
    pos = orb.positions_at_time(200.0)
    R_new = np.sqrt(pos[:, 0] ** 2 + pos[:, 1] ** 2)
    assert np.median(np.abs(R_new - R) / R) < 0.05


def test_params_dict_shapes():
    g = _make_galaxy(n=500)
    orb = EpicyclicOrbitModel.from_galaxy(g)
    d = orb.params_dict()
    for k in ["R_g", "Omega_g", "kappa", "nu", "X", "alpha", "phi_g0", "Z", "beta"]:
        assert d[k].shape == (500,)
