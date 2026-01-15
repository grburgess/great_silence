"""UI components for the Great Silence webapp."""

from .preset_selector import PresetSelector
from .basic_settings import BasicSettings
from .simulation_runner import SimulationRunner
from .config_panels import ConfigPanels
from .results_dashboard import ResultsDashboard

__all__ = [
    "PresetSelector",
    "BasicSettings",
    "SimulationRunner",
    "ConfigPanels",
    "ResultsDashboard",
]
