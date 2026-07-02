"""Tests for Three.js visualization data export."""

from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs.data_extractor import SimulationDataExtractor

ORBIT_PARAM_KEYS = ["R_g", "Omega_g", "kappa", "nu", "X", "alpha", "phi_g0", "Z", "beta"]


def _run_sim(n=500, orbit_mode="fast"):
    c = SimulationConfig()
    c.galaxy.total_stars = n
    c.simulation.simulation_duration_gyr = 1.0
    c.simulation.orbit_mode = orbit_mode
    c.simulation.save_snapshots = False
    sim = GalaxySimulation(c)
    sim.initialize()
    sim.run()
    return sim


def test_export_includes_orbit_params():
    sim = _run_sim(n=500, orbit_mode="fast")
    data = SimulationDataExtractor(sim).extract_galaxy_data()

    assert "stellar_orbits" in data
    orbits = data["stellar_orbits"]
    for key in ORBIT_PARAM_KEYS:
        assert key in orbits
        assert len(orbits[key]) == 500
    assert data["reference_time_myr"] == 0.0


def test_export_orbits_match_subsampled_positions():
    sim = _run_sim(n=500, orbit_mode="fast")
    extractor = SimulationDataExtractor(sim)
    data = extractor.extract_galaxy_data()

    assert len(data["stellar_orbits"]["R_g"]) == len(data["positions"])


def test_export_falls_back_when_no_orbit_model():
    sim = _run_sim(n=500, orbit_mode="exact")
    assert sim.orbit_model is None

    data = SimulationDataExtractor(sim).extract_galaxy_data()
    assert "stellar_orbits" not in data


def _run_sim_with_snapshots(n=300):
    c = SimulationConfig()
    c.galaxy.total_stars = n
    c.simulation.simulation_duration_gyr = 1.0
    c.simulation.orbit_mode = "fast"
    c.simulation.save_snapshots = True
    sim = GalaxySimulation(c)
    sim.initialize()
    sim.run()
    return sim


def test_export_loads_data_once(tmp_path, monkeypatch):
    sim = _run_sim_with_snapshots()

    from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer

    renderer = ThreeJSRenderer(sim)
    calls = []
    original = ThreeJSRenderer._load_data

    def counting_load(self, animated=False):
        calls.append(animated)
        return original(self, animated)

    monkeypatch.setattr(ThreeJSRenderer, "_load_data", counting_load)
    renderer.export(str(tmp_path / "viz.html"), animated=True)

    assert len(calls) == 1


def test_render_reloads_when_animated_flag_changes(monkeypatch):
    sim = _run_sim_with_snapshots()

    from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer

    class _StubTemplate:
        def render(self, **kwargs):
            return ""

    monkeypatch.setattr(ThreeJSRenderer, "_get_template", lambda self, *a, **k: _StubTemplate())

    renderer = ThreeJSRenderer(sim)
    renderer.render(animated=True)
    assert "frames" in renderer.data

    renderer.render(animated=False)
    assert "civilizations" in renderer.data
