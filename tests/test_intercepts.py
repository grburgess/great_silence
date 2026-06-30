import numpy as np

from great_silence import GalaxySimulation, SimulationConfig


def test_intercept_arrives_where_target_is():
    c = SimulationConfig()
    c.galaxy.total_stars = 3000
    c.simulation.orbit_mode = "fast"
    sim = GalaxySimulation(c)
    sim.initialize()
    src = sim.galaxy.positions[0]
    pos, tt = sim._calculate_intercept_position(src, target_idx=100, velocity_c=0.01)
    actual = sim.orbit_model.positions_at_time(sim.current_time_myr + tt)[100]
    assert np.linalg.norm(pos - actual) < 1e-3
    assert tt > 0


def test_intercept_batch_matches_scalar():
    c = SimulationConfig()
    c.galaxy.total_stars = 3000
    c.simulation.orbit_mode = "fast"
    sim = GalaxySimulation(c)
    sim.initialize()
    src = sim.galaxy.positions[0]
    targets = [100, 250, 700, 1500]
    pos_batch, tt_batch = sim._calculate_intercept_positions_batch(src, targets, velocity_c=0.01)
    for j, target_idx in enumerate(targets):
        pos_s, tt_s = sim._calculate_intercept_position(src, target_idx=target_idx, velocity_c=0.01)
        assert abs(tt_batch[j] - tt_s) < 1e-3
        assert np.linalg.norm(pos_batch[j] - pos_s) < 1e-3
        actual = sim.orbit_model.positions_at_time(sim.current_time_myr + tt_batch[j])[target_idx]
        assert np.linalg.norm(pos_batch[j] - actual) < 1e-3


def test_intercept_residual_consistent():
    c = SimulationConfig()
    c.galaxy.total_stars = 3000
    c.simulation.orbit_mode = "fast"
    sim = GalaxySimulation(c)
    sim.initialize()
    src = sim.galaxy.positions[0]
    pos, tt = sim._calculate_intercept_position(src, target_idx=400, velocity_c=0.01)
    distance_kpc = np.linalg.norm(pos - src)
    expected_tt = distance_kpc * 1000.0 / (0.01 * 0.306601) / 1e6
    assert abs(tt - expected_tt) < 1e-4
