import numpy as np

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
