"""Build-smoke tests for the NiceGUI web application."""

import pytest

pytest.importorskip("nicegui")

from nicegui import Client
from nicegui.page import page


def test_webapp_imports():
    from great_silence.webapp import app as webapp_app
    from great_silence.webapp.components.simulation_runner import SimulationRunner

    assert callable(webapp_app.main_page)
    assert callable(webapp_app.run_app)
    assert hasattr(SimulationRunner, "_start_simulation")


def test_simulation_runner_is_async():
    import inspect

    from great_silence.webapp.components.simulation_runner import SimulationRunner

    assert inspect.iscoroutinefunction(SimulationRunner._start_simulation)


def test_run_handler_names_resolve():
    from great_silence.webapp.components import simulation_runner as m

    assert hasattr(m, "asyncio")
    assert hasattr(m, "run")


def test_main_page_constructs():
    from great_silence.webapp import app as webapp_app

    client = Client(page("/"), request=None)
    with client:
        webapp_app.main_page()

    assert len(client.elements) > 0


def test_viz_handlers_are_async():
    import inspect

    from great_silence.webapp.components.results_dashboard import ResultsDashboard

    assert inspect.iscoroutinefunction(ResultsDashboard._generate_viz)
    assert inspect.iscoroutinefunction(ResultsDashboard._export_html)


def test_prune_viz_dirs_keeps_newest(tmp_path):
    import os

    from great_silence.webapp.components.results_dashboard import _prune_viz_dirs

    dirs = []
    for i in range(5):
        d = tmp_path / f"run_{i}"
        d.mkdir()
        os.utime(d, (i, i))
        dirs.append(d)

    _prune_viz_dirs(tmp_path, keep=2, exclude=dirs[0])

    remaining = sorted(p.name for p in tmp_path.iterdir())
    assert remaining == ["run_0", "run_3", "run_4"]


def test_run_app_sets_reconnect_timeout(monkeypatch):
    from nicegui import ui

    from great_silence.webapp import app as webapp_app

    captured = {}
    monkeypatch.setattr(ui, "run", lambda **kwargs: captured.update(kwargs))
    webapp_app.run_app()

    assert captured["reconnect_timeout"] == 30.0
