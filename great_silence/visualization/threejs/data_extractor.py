"""Data extraction for Three.js visualization."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Union, Dict, Any
import numpy as np
import json

from .config import ThreeJSConfig


def _extract_civ_list(snap):
    """Extract civilization list from snapshot."""
    if hasattr(snap, 'civilization_states'):
        return [
            {
                'civ_id': c.civ_id,
                'position': snap.stellar_positions[c.parent_star_idx].tolist() 
                           if hasattr(snap, 'stellar_positions') and snap.stellar_positions is not None 
                           else [0.0, 0.0, 0.0],
                'kardashev': c.kardashev_scale,
                'age': (snap.time_myr - c.birth_time_myr) / 1000.0 
                       if hasattr(snap, 'time_myr') else c.birth_time_myr / 1000.0,
                'is_active': c.is_active
            }
            for c in snap.civilization_states
        ]
    elif hasattr(snap, 'civilizations'):
        return snap.civilizations.copy()
    else:
        return []


def _extract_probe_list(snap):
    """Extract probe list from snapshot."""
    if hasattr(snap, 'active_probes_in_flight'):
        return [
            {
                'probe_id': p.probe_id,
                'position': p.current_position.tolist(),
                'civ_id': p.civ_id,
                'progress': p.progress_fraction
            }
            for p in snap.active_probes_in_flight
        ]
    elif hasattr(snap, 'probes'):
        return snap.probes.copy()
    else:
        return []


def _extract_hazard_list(snap):
    """Extract hazard list from snapshot."""
    if hasattr(snap, 'hazard_events'):
        return [
            {
                'position': h.position.tolist(),
                'type': h.event_type,
                'time': h.time_myr / 1000.0,
                'lethal_radius': h.sterilization_radius_pc / 1000.0
            }
            for h in snap.hazard_events
        ]
    elif hasattr(snap, 'hazards'):
        return snap.hazards.copy()
    else:
        return []


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
        source: Union[str, Path, Any],
        config: Optional[ThreeJSConfig] = None,
    ):
        """Initialize extractor with simulation data source.

        Args:
            source: HDF5 file path, Path, or simulation object
            config: Visualization configuration
        """
        self.source = source
        self.config = config or ThreeJSConfig()
        self.simulation_data: Dict[str, Any] = {}
        self.snapshots: List[Dict] = []
        self._load_source()

    def _load_source(self):
        """Load data from source (HDF5 or simulation object)."""
        if isinstance(self.source, (str, Path)):
            self._load_from_hdf5(Path(self.source))
        else:
            self._extract_from_simulation()

    def _load_from_hdf5(self, path: Path):
        """Load data from HDF5 file."""
        try:
            import h5py

            with h5py.File(path, "r") as f:
                if "galaxy" in f:
                    gal_group = f["galaxy"]
                    self.simulation_data["galaxy_positions"] = np.array(
                        gal_group["positions"]
                    )
                    self.simulation_data["galaxy_colors"] = np.array(
                        gal_group.get("colors", [])
                    )

                if "snapshots" in f:
                    snap_group = f["snapshots"]
                    for key in snap_group.keys():
                        self.snapshots.append(
                            json.loads(snap_group[key][()])
                        )

        except ImportError:
            pass

    def _extract_from_simulation(self) -> dict:
        """Extract data dict from simulation object."""
        if hasattr(self.source, "galaxy"):
            self.simulation_data["galaxy_positions"] = (
                self.source.galaxy.positions.copy()
            )

        if hasattr(self.source, "snapshots"):
            self.snapshots = [
                {
                    "time": snap.time_myr / 1000.0 if hasattr(snap, 'time_myr') else snap.time_gyr,
                    "civilizations": _extract_civ_list(snap),
                    "probes": _extract_probe_list(snap),
                    "hazards": _extract_hazard_list(snap),
                }
                for snap in self.source.snapshots
            ]

        return self.simulation_data

    def extract_galaxy_data(
        self, subsample: int = 10000, seed: int = 42
    ) -> dict:
        """Extract star positions for visualization.

        Args:
            subsample: Number of stars to render
            seed: Random seed for subsampling

        Returns:
            Dict with positions and colors
        """
        positions = self.simulation_data.get("galaxy_positions", np.array([]))

        if len(positions) > subsample:
            rng = np.random.default_rng(seed)
            indices = rng.choice(
                len(positions), subsample, replace=False
            )
            positions = positions[indices]

        colors = self.simulation_data.get("galaxy_colors", np.array([]))
        if len(colors) > 0 and len(colors) != len(positions):
            rng = np.random.default_rng(seed)
            colors = np.random.rand(len(positions), 3)

        return {"positions": positions, "colors": colors}

    def extract_civilization_data(
        self, time_gyr: Optional[float] = None
    ) -> dict:
        """Extract civilization data at given time.

        Args:
            time_gyr: Target time, uses closest snapshot if None

        Returns:
            Dict with active and extinct civilization data
        """
        if not self.snapshots:
            return {
                "active_positions": np.array([]),
                "active_kardashev": np.array([]),
                "extinct_positions": np.array([]),
            }

        if time_gyr is None:
            snapshot = self.snapshots[-1]
        else:
            snapshot = min(
                self.snapshots,
                key=lambda s: abs(s["time"] - time_gyr),
            )

        civilizations = snapshot.get("civilizations", [])

        active_pos = []
        active_kard = []
        extinct_pos = []

        for civ in civilizations:
            if civ.get("is_active", False):
                if "position" in civ:
                    active_pos.append(civ["position"])
                if "kardashev" in civ:
                    active_kard.append(civ["kardashev"])
            else:
                if "position" in civ:
                    extinct_pos.append(civ["position"])

        return {
            "active_positions": np.array(active_pos) if active_pos else np.array([]),
            "active_kardashev": np.array(active_kard) if active_kard else np.array([]),
            "extinct_positions": np.array(extinct_pos) if extinct_pos else np.array([]),
        }

    def extract_trajectory_data(
        self, time_gyr: Optional[float] = None
    ) -> List[dict]:
        """Extract expansion trajectory lines for visualization.

        Args:
            time_gyr: Target time

        Returns:
            List of trajectory segment dicts
        """
        if not self.snapshots:
            return []

        if time_gyr is None:
            target_time = self.snapshots[-1]["time"]
        else:
            target_time = time_gyr

        trajectories = []
        for snapshot in self.snapshots:
            if snapshot["time"] > target_time:
                break

            probes = snapshot.get("probes", [])
            for probe in probes:
                if "trajectory" in probe:
                    trajectories.append(
                        {
                            "start_time": probe.get("launch_time", 0),
                            "end_time": snapshot["time"],
                            "positions": probe["trajectory"],
                            "civ_id": probe.get("civ_id", -1),
                        }
                    )

        return trajectories

    def extract_probe_data(
        self, time_gyr: Optional[float] = None
    ) -> dict:
        """Extract in-flight probe data with interpolation.

        Interpolates probe positions between snapshots (Issue #30).

        Args:
            time_gyr: Target time for interpolation

        Returns:
            Dict with positions, civ_ids, progress, and probe_ids
        """
        if not self.snapshots:
            return {
                "positions": np.array([]),
                "civ_ids": np.array([]),
                "progress": np.array([]),
                "probe_ids": [],
            }

        if time_gyr is None:
            target_time = self.snapshots[-1]["time"]
        else:
            target_time = time_gyr

        snap_before = None
        snap_after = None

        for i, snapshot in enumerate(self.snapshots):
            if snapshot["time"] <= target_time:
                snap_before = snapshot
            if snapshot["time"] >= target_time and snap_after is None:
                snap_after = snapshot
                break

        positions = []
        civ_ids = []
        progress = []
        probe_id_list = []

        if snap_before is None:
            snap_before = self.snapshots[0]
        if snap_after is None:
            snap_after = snap_before

        all_probes = set()

        if "probes" in snap_before:
            for probe in snap_before["probes"]:
                if "id" in probe:
                    all_probes.add(probe["id"])

        if "probes" in snap_after:
            for probe in snap_after["probes"]:
                if "id" in probe:
                    all_probes.add(probe["id"])

        for probe_id in all_probes:
            probe_before = None
            probe_after = None

            if "probes" in snap_before:
                for probe in snap_before["probes"]:
                    if probe.get("id") == probe_id:
                        probe_before = probe
                        break

            if "probes" in snap_after:
                for probe in snap_after["probes"]:
                    if probe.get("id") == probe_id:
                        probe_after = probe
                        break

            if probe_before is not None and probe_after is not None:
                alpha = (target_time - snap_before["time"]) / (
                    snap_after["time"] - snap_before["time"]
                )
                alpha = max(0, min(1, alpha))

                pos_before = np.array(
                    probe_before.get("position", [0, 0, 0])
                )
                pos_after = np.array(probe_after.get("position", [0, 0, 0]))
                pos = (1 - alpha) * pos_before + alpha * pos_after
                positions.append(pos)
                progress.append(alpha)

            elif probe_before is not None:
                pos = np.array(probe_before.get("position", [0, 0, 0]))
                positions.append(pos)
                progress.append(0.0)

            elif probe_after is not None:
                launch_time = probe_after.get("launch_time", snap_before["time"])
                if target_time >= launch_time:
                    alpha = (target_time - launch_time) / (
                        snap_after["time"] - launch_time + 1e-6
                    )
                    alpha = max(0, min(1, alpha))
                    origin = np.array(probe_after.get("origin", [0, 0, 0]))
                    pos_after = np.array(probe_after.get("position", [0, 0, 0]))
                    pos = (1 - alpha) * origin + alpha * pos_after
                    positions.append(pos)
                    progress.append(alpha)

            if probe_before is not None:
                civ_ids.append(probe_before.get("civ_id", -1))
            elif probe_after is not None:
                civ_ids.append(probe_after.get("civ_id", -1))
            else:
                civ_ids.append(-1)

            probe_id_list.append(probe_id)

        return {
            "positions": np.array(positions) if positions else np.array([]),
            "civ_ids": np.array(civ_ids) if civ_ids else np.array([]),
            "progress": np.array(progress) if progress else np.array([]),
            "probe_ids": probe_id_list,
        }

    def extract_hazard_data(
        self, time_gyr: Optional[float] = None
    ) -> dict:
        """Extract hazard data with timing info.

        Includes times_gyr and time_since arrays (Issue #25, #27).

        Args:
            time_gyr: Target time for hazard display

        Returns:
            Dict with positions, types, times_gyr, time_since
        """
        if not self.snapshots:
            return {
                "positions": np.array([]),
                "types": [],
                "times_gyr": np.array([]),
                "time_since": np.array([]),
            }

        if time_gyr is None:
            target_time = self.snapshots[-1]["time"]
        else:
            target_time = time_gyr

        positions = []
        types = []
        times_gyr = []
        time_since = []

        for snapshot in self.snapshots:
            if snapshot["time"] > target_time:
                break

            hazards = snapshot.get("hazards", [])
            for hazard in hazards:
                if "position" in hazard:
                    positions.append(hazard["position"])
                else:
                    positions.append([0, 0, 0])

                types.append(hazard.get("type", "unknown"))
                times_gyr.append(snapshot["time"])
                time_since.append(target_time - snapshot["time"])

        return {
            "positions": np.array(positions) if positions else np.array([]),
            "types": types,
            "times_gyr": np.array(times_gyr) if times_gyr else np.array([]),
            "time_since": np.array(time_since) if time_since else np.array([]),
        }
