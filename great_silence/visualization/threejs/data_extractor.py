"""Data extraction for Three.js visualization."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Union

import numpy as np

from .config import ThreeJSConfig


@dataclass
class FrameData:
    """Data for a single animation frame."""

    time_gyr: float
    active_civ_positions: np.ndarray
    active_civ_kardashev: np.ndarray
    extinct_civ_positions: np.ndarray
    trajectory_segments: List
    hazard_positions: np.ndarray
    hazard_types: List[str]
    probe_positions: np.ndarray
    probe_civ_ids: np.ndarray
    probe_progress: np.ndarray
    probe_ids: List[int]


class SimulationDataExtractor:
    """Extract visualization data from simulation or HDF5 for Three.js."""

    def __init__(
        self,
        source: Union[str, Path, "GalaxySimulation"],
        config: Optional[ThreeJSConfig] = None,
    ):
        """Initialize extractor with simulation data source."""
        pass

    def _load_source(self):
        """Load data from source (HDF5 or simulation object)."""
        pass

    def _extract_from_simulation(self) -> dict:
        """Extract data dict from simulation object."""
        return {}

    def extract_galaxy_data(self, subsample: int = 10000, seed: int = 42) -> dict:
        """Extract star positions for visualization."""
        return {}

    def extract_civilization_data(
        self, time_gyr: Optional[float] = None
    ) -> dict:
        """Extract civilization data at given time."""
        return {}

    def extract_trajectory_data(
        self, time_gyr: Optional[float] = None
    ) -> List[dict]:
        """Extract expansion trajectory lines for visualization."""
        return []

    def extract_probe_data(self, time_gyr: Optional[float] = None) -> dict:
        """Extract in-flight probe data with interpolation.

        Returns:
            Dict with positions, civ_ids, progress, and probe_ids
        """
        return {}

    def extract_hazard_data(self, time_gyr: Optional[float] = None) -> dict:
        """Extract hazard data with timing info.

        Returns:
            Dict with positions, types, times_gyr, time_since
        """
        return {}
