"""Jupyter notebook interface for Great Silence simulations."""

from .widgets import SimulationWidget, ResultsExplorer, AnimationBuilder, Galaxy3DExplorer
from .runners import NotebookSimulationRunner
from .helpers import (
    configure_notebook_display,
    load_simulation,
    save_simulation_hdf5,
    export_interactive_plot,
    create_results_summary,
    create_threejs_visualization,
)

__all__ = [
    # Main widgets
    "SimulationWidget",
    "ResultsExplorer",
    "AnimationBuilder",
    "Galaxy3DExplorer",
    # Runner
    "NotebookSimulationRunner",
    # Helper functions
    "configure_notebook_display",
    "load_simulation",
    "save_simulation_hdf5",
    "export_interactive_plot",
    "create_results_summary",
    "create_threejs_visualization",
]
