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


def test_main_page_constructs():
    from great_silence.webapp import app as webapp_app

    client = Client(page("/"), request=None)
    with client:
        webapp_app.main_page()

    assert len(client.elements) > 0
