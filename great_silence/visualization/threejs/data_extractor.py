"""Data extraction for Three.js visualization."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Union, Dict, Any, Tuple
import numpy as np
import json

from .config import ThreeJSConfig


@dataclass
class StellarKeyframe:
    """Keyframe data for Hermite interpolation of stellar motion."""
    
    time_myr: float
    positions: np.ndarray
    velocities: np.ndarray
    
    def to_dict(self, subsample_indices: Optional[np.ndarray] = None) -> dict:
        """Convert to JSON-serializable dict, optionally subsampling."""
        pos = self.positions
        vel = self.velocities
        
        if subsample_indices is not None:
            pos = pos[subsample_indices]
            vel = vel[subsample_indices]
        
        return {
            "time_myr": self.time_myr,
            "positions": pos.tolist(),
            "velocities": vel.tolist(),
        }


@dataclass  
class EventData:
    """Sparse event data for civs, probes, and disasters."""
    
    civ_births: List[Dict[str, Any]] = field(default_factory=list)
    civ_deaths: List[Dict[str, Any]] = field(default_factory=list)
    civ_updates: List[Dict[str, Any]] = field(default_factory=list)
    disasters: List[Dict[str, Any]] = field(default_factory=list)
    probes: List[Dict[str, Any]] = field(default_factory=list)
    trajectories: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "civ_births": self.civ_births,
            "civ_deaths": self.civ_deaths,
            "civ_updates": self.civ_updates,
            "disasters": self.disasters,
            "probes": self.probes,
            "trajectories": self.trajectories,
        }


def _extract_civ_list(snap, galaxy_positions=None):
    """Extract civilization list from snapshot.
    
    Args:
        snap: Simulation snapshot
        galaxy_positions: Optional fallback positions from galaxy model
    """
    if hasattr(snap, 'civilization_states'):
        # Get positions - prefer stellar_positions, fall back to galaxy_positions
        positions = None
        if hasattr(snap, 'stellar_positions') and snap.stellar_positions is not None and len(snap.stellar_positions) > 0:
            positions = snap.stellar_positions
        elif galaxy_positions is not None and len(galaxy_positions) > 0:
            positions = galaxy_positions
        
        civs = []
        for c in snap.civilization_states:
            if positions is not None and c.parent_star_idx < len(positions):
                pos = positions[c.parent_star_idx].tolist()
            else:
                pos = [0.0, 0.0, 0.0]
            
            # Check if civ has colonies
            has_colonies = False
            if hasattr(c, 'colonized_stars') and c.colonized_stars:
                has_colonies = len(c.colonized_stars) > 1 or (
                    len(c.colonized_stars) == 1 and 
                    c.parent_star_idx not in c.colonized_stars
                )
            
            civs.append({
                'civ_id': c.civ_id,
                'star_idx': c.parent_star_idx,
                'position': pos,
                'kardashev': c.kardashev_scale,
                'age': (snap.time_myr - c.birth_time_myr) / 1000.0 
                       if hasattr(snap, 'time_myr') else c.birth_time_myr / 1000.0,
                'is_active': c.is_active,
                'is_extinct': not c.is_active,
                'has_colonies': has_colonies
            })
        return civs
    elif hasattr(snap, 'civilizations'):
        return snap.civilizations.copy()
    else:
        return []


def _extract_probe_list(snap):
    """Extract probe list from snapshot."""
    if hasattr(snap, 'active_probes_in_flight'):
        probes = []
        for p in snap.active_probes_in_flight:
            probe_data = {
                'probe_id': p.probe_id,
                'position': p.current_position.tolist(),
                'civ_id': p.civ_id,
                'progress': p.progress_fraction
            }
            if hasattr(p, 'launch_star_idx'):
                probe_data['launch_star_idx'] = p.launch_star_idx
            if hasattr(p, 'target_star_idx'):
                probe_data['target_star_idx'] = p.target_star_idx
            probes.append(probe_data)
        return probes
    elif hasattr(snap, 'probes'):
        return snap.probes.copy()
    else:
        return []


def _extract_hazard_list(snap):
    """Extract hazard list from snapshot with full disaster data."""
    if hasattr(snap, 'hazard_events'):
        hazards = []
        for h in snap.hazard_events:
            hazard_data = {
                'position': h.position.tolist(),
                'type': h.event_type,
                'time': h.time_myr / 1000.0,
                'lethal_radius': h.sterilization_radius_pc / 1000.0,
                'energy': getattr(h, 'energy', 1e51),
                'affected_civs': getattr(h, 'affected_civ_ids', []),
            }
            
            if hasattr(h, 'grb_jet_theta'):
                hazard_data['jet_theta'] = h.grb_jet_theta
                hazard_data['jet_phi'] = h.grb_jet_phi
                hazard_data['beaming_angle'] = getattr(h, 'grb_beaming_angle_deg', 10.0)
            
            if hasattr(h, 'sterilization_radius_pc'):
                hazard_data['sterilization_radius'] = h.sterilization_radius_pc / 1000.0
            
            hazards.append(hazard_data)
        return hazards
    elif hasattr(snap, 'hazards'):
        return snap.hazards.copy()
    else:
        return []


def _extract_expansion_trajectories(snap, initial_positions=None, velocities=None):
    """Extract expansion trajectories using actual star positions from snapshot.
    
    Uses current snapshot positions for simplicity - the positions will be
    close to the actual launch/arrival positions for reasonable time spans.
    
    Args:
        snap: Simulation snapshot
        initial_positions: Not used (kept for API compatibility)
        velocities: Not used (kept for API compatibility)
    """
    trajectories = []
    
    if not hasattr(snap, 'civilization_states') or not hasattr(snap, 'stellar_positions'):
        return trajectories
    
    stellar_positions = snap.stellar_positions
    if stellar_positions is None or len(stellar_positions) == 0:
        return trajectories
    
    n_stars = len(stellar_positions)
    current_time = snap.time_myr if hasattr(snap, 'time_myr') else 0
    seen_edges = set()
    
    for civ in snap.civilization_states:
        home_idx = civ.parent_star_idx
        if home_idx >= n_stars:
            continue
        
        has_archived_probes = False
        if hasattr(civ, 'archived_probes') and civ.archived_probes:
            has_archived_probes = True
            for probe in civ.archived_probes:
                launch_idx = probe.launch_star_idx
                target_idx = probe.target_star_idx
                edge_key = (civ.civ_id, launch_idx, target_idx)
                
                if edge_key not in seen_edges and launch_idx < n_stars and target_idx < n_stars:
                    seen_edges.add(edge_key)
                    
                    arrival_time = probe.arrival_time_myr if hasattr(probe, 'arrival_time_myr') else current_time
                    launch_time = probe.launch_time_myr if hasattr(probe, 'launch_time_myr') else (arrival_time - 100)
                    
                    launch_pos = stellar_positions[launch_idx].tolist()
                    intercept_pos = stellar_positions[target_idx].tolist()
                    
                    trajectories.append({
                        'launch_position': launch_pos,
                        'intercept_position': intercept_pos,
                        'launch_star_idx': launch_idx,
                        'target_star_idx': target_idx,
                        'civ_id': civ.civ_id,
                        'generation': probe.generation if hasattr(probe, 'generation') else 0,
                        'time_myr': arrival_time,
                        'launch_time_myr': launch_time,
                    })
        
        if not has_archived_probes and hasattr(civ, 'colonized_stars') and civ.colonized_stars:
            for colony_idx in civ.colonized_stars:
                edge_key = (civ.civ_id, home_idx, colony_idx)
                if edge_key not in seen_edges and colony_idx != home_idx and colony_idx < n_stars:
                    seen_edges.add(edge_key)
                    fallback_launch_time = current_time - 100
                    
                    launch_pos = stellar_positions[home_idx].tolist()
                    intercept_pos = stellar_positions[colony_idx].tolist()
                    
                    trajectories.append({
                        'launch_position': launch_pos,
                        'intercept_position': intercept_pos,
                        'launch_star_idx': home_idx,
                        'target_star_idx': colony_idx,
                        'civ_id': civ.civ_id,
                        'generation': 0,
                        'time_myr': current_time,
                        'launch_time_myr': fallback_launch_time,
                    })
    
    return trajectories


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
            
            if hasattr(self.source.galaxy, "masses") and self.source.galaxy.masses is not None:
                self.simulation_data["galaxy_masses"] = self.source.galaxy.masses.copy()
            
            if hasattr(self.source.galaxy, "ages") and self.source.galaxy.ages is not None:
                self.simulation_data["galaxy_ages"] = self.source.galaxy.ages.copy()
            
            if hasattr(self.source.galaxy, "habitable_indices") and self.source.galaxy.habitable_indices is not None:
                self.simulation_data["habitable_indices"] = self.source.galaxy.habitable_indices.copy()
            
            # Delta compression data for stellar motion
            if hasattr(self.source.galaxy, "initial_positions") and self.source.galaxy.initial_positions is not None:
                self.simulation_data["initial_positions"] = self.source.galaxy.initial_positions.copy()
            
            if hasattr(self.source.galaxy, "velocities") and self.source.galaxy.velocities is not None:
                self.simulation_data["stellar_velocities"] = self.source.galaxy.velocities.copy()

        if hasattr(self.source, "snapshots"):
            galaxy_pos = self.simulation_data.get("galaxy_positions", None)
            initial_pos = self.simulation_data.get("initial_positions", galaxy_pos)
            velocities = self.simulation_data.get("stellar_velocities", None)
            
            stellar_motion_enabled = False
            if hasattr(self.source, 'config') and hasattr(self.source.config, 'simulation'):
                stellar_motion_enabled = getattr(self.source.config.simulation, 'enable_stellar_motion', False)
            
            self.snapshots = []
            for snap in self.source.snapshots:
                snap_data = {
                    "time": snap.time_myr / 1000.0 if hasattr(snap, 'time_myr') else snap.time_gyr,
                    "time_myr": snap.time_myr if hasattr(snap, 'time_myr') else snap.time_gyr * 1000,
                    "civilizations": _extract_civ_list(snap, galaxy_pos),
                    "probes": _extract_probe_list(snap),
                    "hazards": _extract_hazard_list(snap),
                    "trajectories": _extract_expansion_trajectories(snap, initial_pos, velocities),
                    "stellar_ages": snap.stellar_ages.tolist() if hasattr(snap, 'stellar_ages') and snap.stellar_ages is not None else None,
                    "use_delta_compression": getattr(snap, 'use_delta_compression', False),
                }
                
                # Include stellar positions if motion enabled (positions differ each snapshot)
                if stellar_motion_enabled and hasattr(snap, 'stellar_positions') and snap.stellar_positions is not None and len(snap.stellar_positions) > 0:
                    snap_data["stellar_positions"] = snap.stellar_positions.tolist()
                
                self.snapshots.append(snap_data)

        return self.simulation_data

    def extract_galaxy_data(
        self, subsample: int = 10000, seed: int = 42
    ) -> dict:
        """Extract star positions, colors, and sizes for visualization.

        Args:
            subsample: Number of stars to render
            seed: Random seed for subsampling

        Returns:
            Dict with positions, colors, and sizes (as lists for JSON serialization)
        """
        from great_silence.astrophysics.stellar_evolution import StellarEvolution
        
        positions = self.simulation_data.get("galaxy_positions", np.array([]))
        masses = self.simulation_data.get("galaxy_masses", np.array([]))
        
        # Store indices for consistent subsampling across snapshots
        self._subsample_indices = None
        if len(positions) > subsample:
            rng = np.random.default_rng(seed)
            self._subsample_indices = rng.choice(len(positions), subsample, replace=False)
            positions = positions[self._subsample_indices]
            if len(masses) > 0:
                masses = masses[self._subsample_indices]

        if len(masses) > 0 and len(masses) == len(positions):
            colors = StellarEvolution.mass_to_color(masses)
            sizes = StellarEvolution.mass_to_apparent_size(masses, base_size=0.03)
        else:
            colors = self.simulation_data.get("galaxy_colors", np.array([]))
            if len(colors) == 0 or len(colors) != len(positions):
                rng = np.random.default_rng(seed)
                colors = np.ones((len(positions), 3)) * 0.9
            sizes = np.ones(len(positions)) * 0.03

        result = {
            "positions": positions.tolist() if len(positions) > 0 else [],
            "colors": colors.tolist() if len(colors) > 0 else [],
            "sizes": sizes.tolist() if len(sizes) > 0 else [],
        }
        
        # NOTE: GPU-based stellar motion interpolation is disabled because linear
        # extrapolation (pos = initial + vel * t) doesn't model orbital motion.
        # Stars orbit in the galactic potential, not fly in straight lines.
        # 
        # For physically correct motion visualization, the simulation must:
        # 1. Run with enable_stellar_motion=True (uses leapfrog integrator)
        # 2. Save frequent snapshots with evolved positions
        # 3. Visualization shows actual snapshot positions (discrete, not interpolated)
        #
        # To enable experimental GPU motion (will look wrong over long timescales):
        # Set GREAT_SILENCE_GPU_STELLAR_MOTION=1 environment variable
        
        import os
        if os.environ.get('GREAT_SILENCE_GPU_STELLAR_MOTION') == '1':
            stellar_motion_enabled = False
            if hasattr(self.source, 'config') and hasattr(self.source.config, 'simulation'):
                stellar_motion_enabled = getattr(self.source.config.simulation, 'enable_stellar_motion', False)
            
            if stellar_motion_enabled:
                initial_positions = self.simulation_data.get("initial_positions", None)
                velocities = self.simulation_data.get("stellar_velocities", None)
                
                if initial_positions is not None and velocities is not None:
                    if self._subsample_indices is not None:
                        initial_positions = initial_positions[self._subsample_indices]
                        velocities = velocities[self._subsample_indices]
                    
                    result["initial_positions"] = initial_positions.tolist()
                    result["velocities"] = velocities.tolist()
                    result["reference_time"] = 0.0
        
        return result

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
            "active_positions": active_pos if active_pos else [],
            "active_kardashev": active_kard if active_kard else [],
            "extinct_positions": extinct_pos if extinct_pos else [],
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
            "positions": [p.tolist() if hasattr(p, 'tolist') else p for p in positions] if positions else [],
            "civ_ids": civ_ids if civ_ids else [],
            "progress": progress if progress else [],
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
            "positions": positions if positions else [],
            "types": types,
            "times_gyr": times_gyr if times_gyr else [],
            "time_since": time_since if time_since else [],
        }

    def extract_stellar_hr_data(
        self, subsample: int = 2000, seed: int = 42, max_frames: int = 20
    ) -> dict:
        """Extract stellar data for HR diagram visualization.

        Returns per-frame HR data if stellar ages are available in snapshots.

        Args:
            subsample: Number of stars to include
            seed: Random seed for subsampling
            max_frames: Maximum number of frames to include per-frame data (to limit size)

        Returns:
            Dict with temperatures, luminosities, colors, habitable flags, and per-frame data
        """
        from great_silence.astrophysics.stellar_evolution import StellarEvolution

        masses = self.simulation_data.get("galaxy_masses", np.array([]))
        habitable_indices = self.simulation_data.get("habitable_indices", np.array([]))

        if len(masses) == 0:
            return {
                "temperatures": [],
                "luminosities": [],
                "colors": [],
                "is_habitable": [],
                "masses": [],
                "per_frame": [],
            }

        rng = np.random.default_rng(seed)
        if len(masses) > subsample:
            indices = rng.choice(len(masses), subsample, replace=False)
        else:
            indices = np.arange(len(masses))
        
        masses_sub = masses[indices]
        temperatures = StellarEvolution.effective_temperature(masses_sub)
        luminosities = StellarEvolution.luminosity(masses_sub)
        colors = StellarEvolution.temperature_to_rgb(temperatures)

        habitable_set = set(habitable_indices.tolist()) if len(habitable_indices) > 0 else set()
        is_habitable = [int(idx) in habitable_set for idx in indices]

        per_frame_data = []
        if self.snapshots:
            # Subsample snapshots to limit data size
            n_snaps = len(self.snapshots)
            if n_snaps > max_frames:
                step = n_snaps // max_frames
                snap_indices = list(range(0, n_snaps, step))[:max_frames]
                # Always include last frame
                if snap_indices[-1] != n_snaps - 1:
                    snap_indices[-1] = n_snaps - 1
            else:
                snap_indices = list(range(n_snaps))
            
            for snap_idx in snap_indices:
                snap = self.snapshots[snap_idx]
                frame_hr = {"time": snap.get("time", 0)}
                if "stellar_ages" in snap and snap["stellar_ages"] is not None:
                    ages = np.array(snap["stellar_ages"])
                    if len(ages) > 0:
                        ages_sub = ages[indices] if len(ages) > len(indices) else ages
                        
                        temps, lums, phases, colors = StellarEvolution.evolved_properties(
                            masses_sub, ages_sub
                        )
                        
                        frame_hr["temperatures"] = temps.tolist()
                        frame_hr["luminosities"] = lums.tolist()
                        frame_hr["phases"] = phases.tolist()
                        frame_hr["colors"] = colors.tolist()
                per_frame_data.append(frame_hr)

        return {
            "temperatures": temperatures.tolist(),
            "luminosities": luminosities.tolist(),
            "colors": colors.tolist(),
            "is_habitable": is_habitable,
            "masses": masses_sub.tolist(),
            "per_frame": per_frame_data,
            "indices": indices.tolist(),
        }

    def extract_civ_statistics(self) -> dict:
        """Extract civilization statistics for chart visualization.

        Returns:
            Dict with time series data for civilization charts:
            - times: list of time points (Gyr)
            - active_counts: active civs at each time
            - extinct_counts: cumulative extinct civs
            - total_births: cumulative births
            - kardashev_values: all K values per frame (including recently extinct)
            - colony_counts: total colonies per frame
            - lifespans: list of civilization lifespans (Gyr)
        """
        if not self.snapshots:
            return {
                "times": [],
                "active_counts": [],
                "extinct_counts": [],
                "total_births": [],
                "kardashev_values": [],
                "colony_counts": [],
                "lifespans": [],
                "birth_times": [],
                "death_times": [],
                "peak_kardashev": [],
            }

        times = []
        active_counts = []
        extinct_counts = []
        total_births = []
        kardashev_values = []
        colony_counts = []
        peak_kardashev = []

        seen_civs = set()
        dead_civs = set()
        birth_times = {}
        death_times = {}
        civ_peak_k = {}
        lifespans = []

        for snapshot in self.snapshots:
            t = snapshot["time"]
            times.append(t)

            civs = snapshot.get("civilizations", [])
            active = 0
            extinct = 0
            frame_kardashev = []
            frame_colonies = 0

            for civ in civs:
                civ_id = civ.get("civ_id", -1)
                is_active = civ.get("is_active", False)
                k_value = civ.get("kardashev", 0.7)

                if civ_id not in seen_civs:
                    seen_civs.add(civ_id)
                    birth_times[civ_id] = t - civ.get("age", 0)
                    civ_peak_k[civ_id] = k_value

                civ_peak_k[civ_id] = max(civ_peak_k.get(civ_id, 0.7), k_value)

                if is_active:
                    active += 1
                    frame_kardashev.append(k_value)
                else:
                    extinct += 1
                    if civ_id not in dead_civs:
                        dead_civs.add(civ_id)
                        death_times[civ_id] = t
                        if civ_id in birth_times:
                            lifespan = t - birth_times[civ_id]
                            lifespans.append(lifespan)

            if not frame_kardashev and civs:
                for civ in civs:
                    frame_kardashev.append(civ.get("kardashev", 0.7))

            active_counts.append(active)
            extinct_counts.append(extinct)
            total_births.append(len(seen_civs))
            kardashev_values.append(frame_kardashev)
            colony_counts.append(frame_colonies)
            peak_kardashev.append(list(civ_peak_k.values()) if civ_peak_k else [])

        birth_time_list = sorted(birth_times.values())
        death_time_list = sorted(death_times.values())

        return {
            "times": times,
            "active_counts": active_counts,
            "extinct_counts": extinct_counts,
            "total_births": total_births,
            "kardashev_values": kardashev_values,
            "colony_counts": colony_counts,
            "lifespans": lifespans,
            "birth_times": birth_time_list,
            "death_times": death_time_list,
            "peak_kardashev": peak_kardashev,
        }

    def extract_keyframes(
        self,
        max_keyframes: int = 20,
        include_events: bool = True,
        subsample: int = 10000,
        seed: int = 42,
    ) -> Tuple[List[StellarKeyframe], EventData]:
        """Extract stellar keyframes and sparse event data for Hermite interpolation.
        
        This method extracts:
        1. Sparse keyframes with position + velocity for GPU Hermite interpolation
        2. Event-based data for civs, probes, and disasters (stored sparsely)
        
        Args:
            max_keyframes: Maximum number of keyframes to extract
            include_events: Include event-dense frames as keyframes
            subsample: Number of stars to subsample
            seed: Random seed for subsampling
            
        Returns:
            Tuple of (keyframes list, event data)
        """
        import time as time_module
        print(f"[Keyframes] Starting extract_keyframes(max={max_keyframes}, subsample={subsample})", flush=True)
        t0 = time_module.time()
        
        if not hasattr(self.source, "snapshots") or not self.source.snapshots:
            print(f"[Keyframes] No snapshots available", flush=True)
            return [], EventData()
        
        snapshots = self.source.snapshots
        n_snaps = len(snapshots)
        print(f"[Keyframes] Found {n_snaps} snapshots", flush=True)
        
        if n_snaps == 0:
            return [], EventData()
        
        rng = np.random.default_rng(seed)
        n_stars = len(self.simulation_data.get("galaxy_positions", []))
        print(f"[Keyframes] Total stars: {n_stars:,}", flush=True)
        
        if n_stars > subsample:
            subsample_indices = rng.choice(n_stars, subsample, replace=False)
            print(f"[Keyframes] Subsampling to {subsample} stars", flush=True)
        else:
            subsample_indices = None
        
        self._keyframe_subsample_indices = subsample_indices
        
        t1 = time_module.time()
        keyframe_indices = self._select_keyframe_indices(
            snapshots, max_keyframes, include_events
        )
        print(f"[Keyframes] Selected {len(keyframe_indices)} keyframe indices in {time_module.time()-t1:.2f}s", flush=True)
        
        t2 = time_module.time()
        keyframes = []
        for i, idx in enumerate(keyframe_indices):
            snap = snapshots[idx]
            kf = self._extract_single_keyframe(snap, subsample_indices)
            if kf is not None:
                keyframes.append(kf)
            if (i + 1) % 5 == 0:
                print(f"[Keyframes] Extracted {i+1}/{len(keyframe_indices)} keyframes...", flush=True)
        print(f"[Keyframes] Extracted {len(keyframes)} keyframes in {time_module.time()-t2:.2f}s", flush=True)
        
        # Compute velocities from position differences for smooth Hermite interpolation
        # This ensures velocities are consistent with actual position changes
        if len(keyframes) >= 2:
            t3 = time_module.time()
            self._compute_velocities_from_positions(keyframes)
            print(f"[Keyframes] Computed velocities in {time_module.time()-t3:.2f}s, final keyframes: {len(keyframes)}", flush=True)
        
        t4 = time_module.time()
        print(f"[Keyframes] Extracting sparse events from {n_snaps} snapshots...", flush=True)
        event_data = self._extract_sparse_events(snapshots, subsample_indices)
        print(f"[Keyframes] Extracted events in {time_module.time()-t4:.2f}s", flush=True)
        print(f"[Keyframes]   - civ_births: {len(event_data.civ_births)}", flush=True)
        print(f"[Keyframes]   - civ_deaths: {len(event_data.civ_deaths)}", flush=True)
        print(f"[Keyframes]   - disasters: {len(event_data.disasters)}", flush=True)
        print(f"[Keyframes]   - trajectories: {len(event_data.trajectories)}", flush=True)
        
        # Filter to only expanding civs if configured
        if self.config.only_expanding_civs:
            event_data = self._filter_to_expanding_civs(event_data)
            print(f"[Keyframes] After expanding-only filter:", flush=True)
            print(f"[Keyframes]   - civ_births: {len(event_data.civ_births)}", flush=True)
            print(f"[Keyframes]   - civ_deaths: {len(event_data.civ_deaths)}", flush=True)
            print(f"[Keyframes]   - civ_updates: {len(event_data.civ_updates)}", flush=True)
        
        # Limit trajectories to prevent huge files
        max_traj = self.config.max_trajectories
        if len(event_data.trajectories) > max_traj:
            print(f"[Keyframes] ⚠️ Limiting trajectories: {len(event_data.trajectories)} → {max_traj}", flush=True)
            # Sample evenly across the trajectories to preserve diversity
            step = len(event_data.trajectories) // max_traj
            event_data.trajectories = event_data.trajectories[::step][:max_traj]
        
        print(f"[Keyframes] Total time: {time_module.time()-t0:.2f}s", flush=True)
        
        return keyframes, event_data
    
    def _filter_to_expanding_civs(self, events: EventData) -> EventData:
        """Filter event data to only include civilizations that have expanded.
        
        A civilization is considered "expanding" if it has at least one trajectory
        (i.e., has colonized at least one other star).
        """
        # Find civs that have trajectories (expanded)
        expanding_civ_ids = set()
        for traj in events.trajectories:
            civ_id = traj.get('civ_id', -1)
            if civ_id >= 0:
                expanding_civ_ids.add(civ_id)
        
        if not expanding_civ_ids:
            print(f"[Keyframes] No expanding civs found, showing all", flush=True)
            return events
        
        print(f"[Keyframes] Found {len(expanding_civ_ids)} expanding civs", flush=True)
        
        # Filter events to only include expanding civs
        filtered = EventData()
        filtered.civ_births = [b for b in events.civ_births if b.get('civ_id') in expanding_civ_ids]
        filtered.civ_deaths = [d for d in events.civ_deaths if d.get('civ_id') in expanding_civ_ids]
        filtered.civ_updates = [u for u in events.civ_updates if u.get('civ_id') in expanding_civ_ids]
        filtered.disasters = events.disasters  # Keep all disasters
        filtered.probes = [p for p in events.probes if p.get('civ_id') in expanding_civ_ids]
        filtered.trajectories = events.trajectories  # Already only from expanding civs
        
        return filtered
    
    def _compute_velocities_from_positions(self, keyframes: List[StellarKeyframe]) -> None:
        """Compute velocities from position differences between adjacent keyframes.
        
        This replaces the initial velocities with velocities derived from actual
        position changes, ensuring smooth Hermite interpolation that matches
        the actual stellar motion.
        
        Uses central differences for interior keyframes and forward/backward
        differences for endpoints.
        """
        n = len(keyframes)
        if n < 2:
            return
        
        # Remove duplicate keyframes (same time)
        unique_keyframes = [keyframes[0]]
        for kf in keyframes[1:]:
            if abs(kf.time_myr - unique_keyframes[-1].time_myr) > 0.01:  # > 0.01 Myr apart
                unique_keyframes.append(kf)
        
        # Update the list in place
        keyframes.clear()
        keyframes.extend(unique_keyframes)
        n = len(keyframes)
        
        if n < 2:
            return
        
        # Velocity conversion: kpc/Myr to km/s
        # 1 kpc/Myr = 977.8 km/s (inverse of 0.001022)
        kpc_per_myr_to_km_s = 977.8
        
        # Minimum time difference to avoid numerical issues
        min_dt = 1.0  # 1 Myr minimum
        
        for i in range(n):
            if i == 0:
                # Forward difference for first keyframe
                dt_myr = max(keyframes[1].time_myr - keyframes[0].time_myr, min_dt)
                dpos = keyframes[1].positions - keyframes[0].positions
                vel_kpc_per_myr = dpos / dt_myr
                keyframes[i].velocities = (vel_kpc_per_myr * kpc_per_myr_to_km_s).astype(np.float32)
            elif i == n - 1:
                # Backward difference for last keyframe
                dt_myr = max(keyframes[n-1].time_myr - keyframes[n-2].time_myr, min_dt)
                dpos = keyframes[n-1].positions - keyframes[n-2].positions
                vel_kpc_per_myr = dpos / dt_myr
                keyframes[i].velocities = (vel_kpc_per_myr * kpc_per_myr_to_km_s).astype(np.float32)
            else:
                # Central difference for interior keyframes
                dt_myr = max(keyframes[i+1].time_myr - keyframes[i-1].time_myr, min_dt)
                dpos = keyframes[i+1].positions - keyframes[i-1].positions
                vel_kpc_per_myr = dpos / dt_myr
                keyframes[i].velocities = (vel_kpc_per_myr * kpc_per_myr_to_km_s).astype(np.float32)
    
    def _select_keyframe_indices(
        self,
        snapshots: list,
        max_keyframes: int,
        include_events: bool,
    ) -> List[int]:
        """Select which snapshot indices to use as keyframes.
        
        Strategy:
        1. Always include first and last
        2. If include_events, prioritize frames with significant events
        3. Fill remaining with evenly spaced frames
        """
        n_snaps = len(snapshots)
        
        if n_snaps <= max_keyframes:
            return list(range(n_snaps))
        
        selected = set([0, n_snaps - 1])
        
        if include_events:
            event_scores = []
            for i, snap in enumerate(snapshots):
                score = 0
                
                if hasattr(snap, 'hazard_events'):
                    score += len(snap.hazard_events) * 3
                elif isinstance(snap, dict) and 'hazards' in snap:
                    score += len(snap.get('hazards', [])) * 3
                
                if hasattr(snap, 'civilization_states'):
                    for civ in snap.civilization_states:
                        if hasattr(civ, 'is_active'):
                            if not civ.is_active and hasattr(civ, 'death_time_myr'):
                                snap_time = snap.time_myr if hasattr(snap, 'time_myr') else 0
                                if abs(civ.death_time_myr - snap_time) < 100:
                                    score += 2
                elif isinstance(snap, dict) and 'civilizations' in snap:
                    prev_civs = set()
                    if i > 0:
                        prev_snap = snapshots[i-1]
                        if isinstance(prev_snap, dict):
                            prev_civs = set(c.get('civ_id', -1) for c in prev_snap.get('civilizations', []))
                    
                    curr_civs = set(c.get('civ_id', -1) for c in snap.get('civilizations', []))
                    new_civs = curr_civs - prev_civs
                    score += len(new_civs) * 2
                
                event_scores.append((i, score))
            
            event_scores.sort(key=lambda x: -x[1])
            
            event_budget = max_keyframes // 3
            for idx, score in event_scores[:event_budget]:
                if score > 0:
                    selected.add(idx)
        
        remaining = max_keyframes - len(selected)
        if remaining > 0:
            step = n_snaps / (remaining + 1)
            for i in range(1, remaining + 1):
                idx = int(i * step)
                if idx not in selected and idx < n_snaps:
                    selected.add(idx)
        
        return sorted(selected)[:max_keyframes]
    
    def _extract_single_keyframe(
        self,
        snap,
        subsample_indices: Optional[np.ndarray],
    ) -> Optional[StellarKeyframe]:
        """Extract a single keyframe from a snapshot."""
        if hasattr(snap, 'time_myr'):
            time_myr = snap.time_myr
        elif isinstance(snap, dict):
            time_myr = snap.get('time_myr', snap.get('time', 0) * 1000)
        else:
            return None
        
        positions = None
        velocities = None
        
        if hasattr(snap, 'stellar_positions') and snap.stellar_positions is not None:
            positions = snap.stellar_positions
        elif isinstance(snap, dict) and 'stellar_positions' in snap:
            positions = np.array(snap['stellar_positions'])
        else:
            positions = self.simulation_data.get("galaxy_positions")
        
        if positions is None or len(positions) == 0:
            return None
        
        velocities = self.simulation_data.get("stellar_velocities")
        
        if velocities is None:
            velocities = np.zeros_like(positions)
        
        positions = np.asarray(positions, dtype=np.float32)
        velocities = np.asarray(velocities, dtype=np.float32)
        
        if subsample_indices is not None:
            positions = positions[subsample_indices]
            velocities = velocities[subsample_indices]
        
        return StellarKeyframe(
            time_myr=time_myr,
            positions=positions.copy(),
            velocities=velocities.copy(),
        )
    
    def _extract_sparse_events(
        self,
        snapshots: list,
        subsample_indices: Optional[np.ndarray],
    ) -> EventData:
        """Extract sparse event data from all snapshots.
        
        IMPORTANT: For trajectories, we calculate FIXED worldline positions:
        - launch_position: where source star WAS at launch time
        - intercept_position: where target star WILL BE at arrival time
        
        This ensures physically accurate trajectory visualization even when
        stars are moving. The trajectory line represents the probe's actual
        path through absolute space.
        """
        events = EventData()
        
        seen_civs = set()
        dead_civs = set()
        
        galaxy_pos = self.simulation_data.get("galaxy_positions", np.array([]))
        
        initial_positions = None
        if snapshots and hasattr(snapshots[0], 'stellar_positions'):
            initial_positions = snapshots[0].stellar_positions
        elif len(galaxy_pos) > 0:
            initial_positions = galaxy_pos
        
        snapshot_positions_by_time = {}
        for snap in snapshots:
            if hasattr(snap, 'time_myr') and hasattr(snap, 'stellar_positions') and snap.stellar_positions is not None:
                snapshot_positions_by_time[snap.time_myr] = snap.stellar_positions
        
        def get_position_at_time(star_idx, time_myr, positions_by_time, fallback_positions):
            """Get star position at given time from nearest snapshot."""
            if not positions_by_time:
                if fallback_positions is not None and star_idx < len(fallback_positions):
                    return fallback_positions[star_idx]
                return None
            
            closest_time = min(positions_by_time.keys(), key=lambda t: abs(t - time_myr))
            positions = positions_by_time[closest_time]
            if star_idx < len(positions):
                return positions[star_idx]
            return None
        
        for i, snap in enumerate(snapshots):
            if hasattr(snap, 'time_myr'):
                time_myr = snap.time_myr
            elif isinstance(snap, dict):
                time_myr = snap.get('time_myr', snap.get('time', 0) * 1000)
            else:
                continue
            
            if hasattr(snap, 'hazard_events'):
                for h in snap.hazard_events:
                    events.disasters.append({
                        'time_myr': h.time_myr,
                        'type': h.event_type,
                        'position': h.position.tolist(),
                        'lethal_radius_kpc': h.sterilization_radius_pc / 1000.0,
                        'affected_civs': getattr(h, 'affected_civ_ids', []),
                    })
            elif isinstance(snap, dict) and 'hazards' in snap:
                for h in snap.get('hazards', []):
                    events.disasters.append({
                        'time_myr': time_myr,
                        'type': h.get('type', 'unknown'),
                        'position': h.get('position', [0, 0, 0]),
                        'lethal_radius_kpc': h.get('lethal_radius', 0),
                    })
            
            civs = []
            if hasattr(snap, 'civilization_states'):
                civs = snap.civilization_states
            elif isinstance(snap, dict) and 'civilizations' in snap:
                civs = snap.get('civilizations', [])
            
            positions = None
            if hasattr(snap, 'stellar_positions') and snap.stellar_positions is not None:
                positions = snap.stellar_positions
            elif len(galaxy_pos) > 0:
                positions = galaxy_pos
            
            for civ in civs:
                if hasattr(civ, 'civ_id'):
                    civ_id = civ.civ_id
                    star_idx = civ.parent_star_idx
                    kardashev = civ.kardashev_scale
                    is_active = civ.is_active
                    birth_time = civ.birth_time_myr
                else:
                    civ_id = civ.get('civ_id', -1)
                    star_idx = civ.get('parent_star_idx', 0)
                    kardashev = civ.get('kardashev', 0.7)
                    is_active = civ.get('is_active', False)
                    birth_time = civ.get('birth_time_myr', 0)
                
                if civ_id not in seen_civs:
                    seen_civs.add(civ_id)
                    events.civ_births.append({
                        'time_myr': birth_time,
                        'civ_id': civ_id,
                        'star_idx': star_idx,
                        'kardashev': kardashev,
                    })
                
                if not is_active and civ_id not in dead_civs:
                    dead_civs.add(civ_id)
                    death_cause = None
                    if hasattr(civ, 'death_cause'):
                        death_cause = civ.death_cause
                    elif isinstance(civ, dict):
                        death_cause = civ.get('death_cause')
                    
                    events.civ_deaths.append({
                        'time_myr': time_myr,
                        'civ_id': civ_id,
                        'cause': death_cause,
                    })
                
                if is_active:
                    events.civ_updates.append({
                        'time_myr': time_myr,
                        'civ_id': civ_id,
                        'star_idx': star_idx,
                        'kardashev': kardashev,
                    })
            
            probes = []
            if hasattr(snap, 'active_probes_in_flight'):
                probes = snap.active_probes_in_flight
            elif isinstance(snap, dict) and 'probes' in snap:
                probes = snap.get('probes', [])
            
            for p in probes:
                if hasattr(p, 'probe_id'):
                    events.probes.append({
                        'time_myr': time_myr,
                        'probe_id': p.probe_id,
                        'civ_id': p.civ_id,
                        'position': p.current_position.tolist(),
                        'progress': p.progress_fraction,
                    })
                elif isinstance(p, dict):
                    events.probes.append({
                        'time_myr': time_myr,
                        'probe_id': p.get('probe_id', -1),
                        'civ_id': p.get('civ_id', -1),
                        'position': p.get('position', [0, 0, 0]),
                        'progress': p.get('progress', 0),
                    })
            
            # Extract trajectories from SimulationSnapshot objects
            # Use INITIAL positions for consistency with Hermite-interpolated stars
            trajs = []
            if hasattr(snap, 'civilization_states') and initial_positions is not None:
                n_stars = len(initial_positions)
                if n_stars > 0:
                    for civ in snap.civilization_states:
                        home_idx = civ.parent_star_idx
                        if home_idx >= n_stars:
                            continue
                        home_pos = initial_positions[home_idx].tolist()
                        
                        has_archived_probes = False
                        if hasattr(civ, 'archived_probes') and civ.archived_probes:
                            has_archived_probes = True
                            for probe in civ.archived_probes:
                                if hasattr(probe, 'launch_star_idx') and hasattr(probe, 'target_star_idx'):
                                    launch_idx = probe.launch_star_idx
                                    target_idx = probe.target_star_idx
                                    if launch_idx < n_stars and target_idx < n_stars:
                                        arrival_time = probe.arrival_time_myr if hasattr(probe, 'arrival_time_myr') else time_myr
                                        launch_time = probe.launch_time_myr if hasattr(probe, 'launch_time_myr') else (arrival_time - 100)
                                        
                                        launch_pos_arr = get_position_at_time(launch_idx, launch_time, snapshot_positions_by_time, initial_positions)
                                        intercept_pos_arr = get_position_at_time(target_idx, arrival_time, snapshot_positions_by_time, initial_positions)
                                        
                                        if launch_pos_arr is None or intercept_pos_arr is None:
                                            continue
                                        
                                        launch_pos = launch_pos_arr.tolist() if hasattr(launch_pos_arr, 'tolist') else list(launch_pos_arr)
                                        intercept_pos = intercept_pos_arr.tolist() if hasattr(intercept_pos_arr, 'tolist') else list(intercept_pos_arr)
                                        
                                        events.trajectories.append({
                                            'time_myr': arrival_time,
                                            'launch_time_myr': launch_time,
                                            'launch_position': launch_pos,
                                            'intercept_position': intercept_pos,
                                            'launch_star_idx': launch_idx,
                                            'target_star_idx': target_idx,
                                            'civ_id': civ.civ_id,
                                            'generation': probe.generation if hasattr(probe, 'generation') else 0,
                                        })
                        
                        if not has_archived_probes and hasattr(civ, 'colonized_stars') and civ.colonized_stars:
                            for colony_idx in civ.colonized_stars:
                                if colony_idx != home_idx and colony_idx < n_stars:
                                    fallback_launch_time = time_myr - 100
                                    
                                    launch_pos_arr = get_position_at_time(home_idx, fallback_launch_time, snapshot_positions_by_time, initial_positions)
                                    intercept_pos_arr = get_position_at_time(colony_idx, time_myr, snapshot_positions_by_time, initial_positions)
                                    
                                    if launch_pos_arr is None or intercept_pos_arr is None:
                                        continue
                                    
                                    launch_pos = launch_pos_arr.tolist() if hasattr(launch_pos_arr, 'tolist') else list(launch_pos_arr)
                                    intercept_pos = intercept_pos_arr.tolist() if hasattr(intercept_pos_arr, 'tolist') else list(intercept_pos_arr)
                                    
                                    events.trajectories.append({
                                        'time_myr': time_myr,
                                        'launch_time_myr': fallback_launch_time,
                                        'launch_position': launch_pos,
                                        'intercept_position': intercept_pos,
                                        'launch_star_idx': home_idx,
                                        'target_star_idx': colony_idx,
                                        'civ_id': civ.civ_id,
                                        'generation': 0,
                                    })
            elif isinstance(snap, dict) and 'trajectories' in snap:
                trajs = snap.get('trajectories', [])
                for t in trajs:
                    arrival_time = t.get('time_myr', time_myr)
                    launch_time = t.get('launch_time_myr', arrival_time - 100)
                    
                    if 'launch_position' in t and 'intercept_position' in t:
                        launch_pos = t['launch_position']
                        intercept_pos = t['intercept_position']
                    else:
                        launch_idx = t.get('launch_star_idx')
                        target_idx = t.get('target_star_idx')
                        if launch_idx is not None and target_idx is not None:
                            launch_pos_arr = get_position_at_time(launch_idx, launch_time, snapshot_positions_by_time, initial_positions)
                            intercept_pos_arr = get_position_at_time(target_idx, arrival_time, snapshot_positions_by_time, initial_positions)
                            if launch_pos_arr is None or intercept_pos_arr is None:
                                continue
                            launch_pos = launch_pos_arr.tolist() if hasattr(launch_pos_arr, 'tolist') else list(launch_pos_arr)
                            intercept_pos = intercept_pos_arr.tolist() if hasattr(intercept_pos_arr, 'tolist') else list(intercept_pos_arr)
                        else:
                            launch_pos = t.get('start', [0, 0, 0])
                            intercept_pos = t.get('end', [0, 0, 0])
                    
                    events.trajectories.append({
                        'time_myr': arrival_time,
                        'launch_time_myr': launch_time,
                        'launch_position': launch_pos,
                        'intercept_position': intercept_pos,
                        'launch_star_idx': t.get('launch_star_idx'),
                        'target_star_idx': t.get('target_star_idx'),
                        'civ_id': t.get('civ_id', -1),
                        'generation': t.get('generation', 0),
                    })
        
        return events
