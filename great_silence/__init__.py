"""
GalaticBot: Monte Carlo simulation of intelligent life spreading through a galaxy.

This package simulates the emergence, expansion, and potential extinction of
civilizations in a 3D galactic model, accounting for astrophysical hazards,
proper stellar motion, and light travel time constraints.
"""

__version__ = "0.1.0"

from .simulation.engine import GalaxySimulation
from .config.parameters import SimulationConfig
from .utils.threading import configure_m1_max_threading

__all__ = ["GalaxySimulation", "SimulationConfig", "configure_m1_max_threading"]
