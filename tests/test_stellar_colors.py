"""Regression tests for vectorized stellar color conversion."""

import numpy as np

from great_silence.astrophysics.stellar_evolution import StellarEvolution

GOLDEN = {
    500.0: [1.0, 0.2663545845364998, 0.0],
    1000.0: [1.0, 0.2663545845364998, 0.0],
    1900.0: [1.0, 0.516729961793658, 0.0],
    3000.0: [1.0, 0.6949030005552019, 0.4310480202110507],
    5778.0: [1.0, 0.9505801431936411, 0.9041131611607817],
    6600.0: [1.0, 1.0, 1.0],
    10000.0: [0.7909974347833513, 0.8551792944545848, 1.0],
    40000.0: [0.5948014942531991, 0.7275657510810973, 1.0],
    50000.0: [0.5948014942531991, 0.7275657510810973, 1.0],
}


def test_temperature_to_rgb_matches_golden_values():
    temps = np.array(sorted(GOLDEN))
    rgb = StellarEvolution.temperature_to_rgb(temps)

    expected = np.array([GOLDEN[t] for t in sorted(GOLDEN)])
    np.testing.assert_allclose(rgb, expected, rtol=0, atol=1e-12)


def test_temperature_to_rgb_shape_and_bounds():
    rng = np.random.default_rng(42)
    temps = rng.uniform(500, 50000, size=5000)
    rgb = StellarEvolution.temperature_to_rgb(temps)

    assert rgb.shape == (5000, 3)
    assert np.all(rgb >= 0.0)
    assert np.all(rgb <= 1.0)


def test_temperature_to_rgb_is_fast_at_frame_scale():
    import time

    temps = np.linspace(1000, 40000, 5000)
    StellarEvolution.temperature_to_rgb(temps)

    t0 = time.perf_counter()
    for _ in range(10):
        StellarEvolution.temperature_to_rgb(temps)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.2, f"10 frame-scale conversions took {elapsed:.2f}s"
