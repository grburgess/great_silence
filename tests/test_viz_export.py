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


def test_export_writes_data_sidecars_and_slim_html(tmp_path):
    sim = _run_sim_with_snapshots()

    from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer

    renderer = ThreeJSRenderer(sim)
    renderer.export(str(tmp_path / "viz.html"), animated=True)

    for name in ["viz_animation.js", "viz_galaxy.js", "viz_hrdata.js", "viz_civstats.js"]:
        assert (tmp_path / name).exists(), name

    html = (tmp_path / "viz.html").read_text()
    assert 'src="viz_animation.js' in html
    assert "window.animationData = {" not in html
    assert "window.galaxyData = {" not in html
    assert not (tmp_path / "viz_data.json").exists()
    assert (tmp_path / "viz_animation.js").read_text().startswith("window.animationData = ")


def test_bare_render_stays_self_contained():
    sim = _run_sim_with_snapshots()

    from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer

    html = ThreeJSRenderer(sim).render(animated=True)

    assert "window.animationData = {" in html
    assert "<!-- ANIMATION_DATA -->" not in html


def test_animation_payload_has_union_and_lean_frames():
    import json as _json

    sim = _run_sim_with_snapshots()

    from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer

    renderer = ThreeJSRenderer(sim)
    renderer._load_data(animated=True)
    payload = _json.loads(renderer.data["animation_data"])

    assert set(payload.keys()) == {"frames", "trajectories", "time_range"}
    assert all("trajectories" not in f for f in payload["frames"])


class _FakeProbe:
    def __init__(self, launch, target, arrival, generation=1):
        self.launch_star_idx = launch
        self.target_star_idx = target
        self.arrival_time_myr = arrival
        self.generation = generation


class _FakeCiv:
    def __init__(self, civ_id, home, probes=(), colonies=()):
        self.civ_id = civ_id
        self.parent_star_idx = home
        self.archived_probes = list(probes)
        self.colonized_stars = set(colonies)


class _FakeSnap:
    def __init__(self, time_myr, civs, positions):
        self.time_myr = time_myr
        self.civilization_states = civs
        self.stellar_positions = positions


def test_trajectory_entries_carry_indices_and_source():
    import numpy as np

    from great_silence.visualization.threejs.data_extractor import (
        _extract_expansion_trajectories,
    )

    pos = np.arange(30, dtype=float).reshape(10, 3)
    civ = _FakeCiv(7, home=0, probes=[_FakeProbe(0, 3, arrival=120.0)], colonies=[3, 5])
    snap = _FakeSnap(500.0, [civ], pos)

    entries = _extract_expansion_trajectories(snap)

    probe_entries = [e for e in entries if e["source"] == "probe"]
    colony_entries = [e for e in entries if e["source"] == "colony"]
    assert probe_entries[0]["start_idx"] == 0
    assert probe_entries[0]["end_idx"] == 3
    assert probe_entries[0]["time_myr"] == 120.0
    assert colony_entries[0]["end_idx"] == 5


def test_union_trajectories_dedups_and_keeps_earliest():
    from great_silence.visualization.threejs.data_extractor import build_union_trajectories

    def entry(civ, s, e, t, source="probe", coords=None):
        return {
            "start": coords or [float(s)] * 3,
            "end": [float(e)] * 3,
            "civ_id": civ,
            "generation": 1,
            "time_myr": t,
            "start_idx": s,
            "end_idx": e,
            "source": source,
        }

    snapshots = [
        {"trajectories": [entry(1, 0, 3, 120.0), entry(1, 0, 5, 300.0, source="colony")]},
        {
            "trajectories": [
                entry(1, 0, 3, 120.0, coords=[9.9] * 3),
                entry(1, 0, 5, 200.0, source="colony"),
                entry(2, 4, 6, 400.0),
            ]
        },
    ]

    union = build_union_trajectories(snapshots)

    assert len(union) == 3
    by_key = {(e["civ_id"], e["start_idx"], e["end_idx"]): e for e in union}
    assert by_key[(1, 0, 3)]["start"] == [0.0] * 3
    assert by_key[(1, 0, 5)]["time_myr"] == 200.0


def test_union_prefers_probe_over_colony_on_same_key():
    from great_silence.visualization.threejs.data_extractor import build_union_trajectories

    colony = {
        "start": [0.0] * 3,
        "end": [1.0] * 3,
        "civ_id": 1,
        "generation": 0,
        "time_myr": 50.0,
        "start_idx": 0,
        "end_idx": 1,
        "source": "colony",
    }
    probe = {
        "start": [0.0] * 3,
        "end": [1.0] * 3,
        "civ_id": 1,
        "generation": 1,
        "time_myr": 90.0,
        "start_idx": 0,
        "end_idx": 1,
        "source": "probe",
    }
    union = build_union_trajectories([{"trajectories": [colony]}, {"trajectories": [probe]}])

    assert len(union) == 1
    assert union[0]["source"] == "probe"


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
