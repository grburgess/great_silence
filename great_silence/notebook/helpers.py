"""Helper utilities for Jupyter notebook interfaces."""

import h5py
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import json


def configure_notebook_display():
    """Configure display settings for notebook environment."""
    try:
        from IPython.display import display, HTML
        import matplotlib.pyplot as plt

        # Set matplotlib backend for inline plotting
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['figure.dpi'] = 100

        # Configure plotly for JupyterLab
        try:
            import plotly.io as pio
            # Use 'jupyterlab' renderer for JupyterLab, falls back to 'notebook' for classic Jupyter
            pio.renderers.default = 'jupyterlab'
        except ImportError:
            pass  # plotly not installed

        # Display confirmation
        display(HTML("<p style='color: #28a745;'>✓ Notebook display configured (matplotlib + plotly)</p>"))

    except ImportError:
        print("Warning: IPython not available. Display configuration skipped.")


def save_simulation_hdf5(simulation, path: str, compress: bool = True):
    """
    Save simulation results to HDF5 format.

    Args:
        simulation: GalaxySimulation instance
        path: Output path (without .h5 extension)
        compress: Whether to use gzip compression
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    h5_path = path.with_suffix('.h5')

    compression = 'gzip' if compress else None

    with h5py.File(h5_path, 'w') as f:
        # Save galaxy data
        galaxy_grp = f.create_group('galaxy')
        if simulation.galaxy.positions is not None:
            galaxy_grp.create_dataset('positions', data=simulation.galaxy.positions,
                                     compression=compression)
            galaxy_grp.create_dataset('ages', data=simulation.galaxy.ages,
                                     compression=compression)
            galaxy_grp.create_dataset('metallicities', data=simulation.galaxy.metallicities,
                                     compression=compression)

        # Save civilization data
        civ_grp = f.create_group('civilizations')
        if simulation.civilizations:
            civ_data = []
            for civ in simulation.civilizations:
                civ_data.append({
                    'parent_star_idx': civ.parent_star_idx,
                    'emergence_time_gyr': civ.birth_time_myr / 1000.0,  # Convert Myr to Gyr
                    'is_active': civ.is_active,
                    'extinction_time_gyr': civ.death_time_myr / 1000.0 if civ.death_time_myr else None,
                    'kardashev_level': civ.kardashev_scale,
                    'death_cause': civ.death_cause if civ.death_cause else None,
                })

            # Convert to structured arrays
            civ_grp.create_dataset('parent_star_idx',
                                  data=np.array([c['parent_star_idx'] for c in civ_data]))
            civ_grp.create_dataset('emergence_time_gyr',
                                  data=np.array([c['emergence_time_gyr'] for c in civ_data]))
            civ_grp.create_dataset('is_active',
                                  data=np.array([c['is_active'] for c in civ_data]))

            # Optional fields with None handling
            extinction_times = np.array([c['extinction_time_gyr'] if c['extinction_time_gyr'] is not None else -1.0
                                        for c in civ_data])
            civ_grp.create_dataset('extinction_time_gyr', data=extinction_times)

            kardashev_levels = np.array([c['kardashev_level'] for c in civ_data])
            civ_grp.create_dataset('kardashev_level', data=kardashev_levels)

            # Death causes as strings
            death_causes = [c['death_cause'] if c['death_cause'] is not None else ''
                          for c in civ_data]
            civ_grp.create_dataset('death_cause', data=np.array(death_causes, dtype='S50'))

            # Save colonized stars for each civilization (for expansion visualization)
            max_colonies = max(len(civ.colonized_stars) for civ in simulation.civilizations)
            if max_colonies > 0:
                # Pad with -1 to create fixed-size array
                colonized_arrays = []
                for civ in simulation.civilizations:
                    padded = list(civ.colonized_stars) + [-1] * (max_colonies - len(civ.colonized_stars))
                    colonized_arrays.append(padded)
                civ_grp.create_dataset('colonized_stars',
                                      data=np.array(colonized_arrays, dtype=np.int32),
                                      compression=compression)

            # Save colony arrival times for trajectory/sphere visualization
            # Store as parallel arrays: colony indices and arrival times
            if max_colonies > 0:
                arrival_indices = []
                arrival_times = []

                for civ in simulation.civilizations:
                    # Extract (star_idx, arrival_time_myr) pairs from dict
                    indices = list(civ.colony_arrival_times.keys())
                    times = [civ.colony_arrival_times[idx] for idx in indices]

                    # Pad to max_colonies length
                    padded_indices = indices + [-1] * (max_colonies - len(indices))
                    padded_times = times + [-1.0] * (max_colonies - len(times))

                    arrival_indices.append(padded_indices)
                    arrival_times.append(padded_times)

                civ_grp.create_dataset('colony_arrival_indices',
                                      data=np.array(arrival_indices, dtype=np.int32),
                                      compression=compression)
                civ_grp.create_dataset('colony_arrival_times_myr',
                                      data=np.array(arrival_times, dtype=np.float32),
                                      compression=compression)

        # Save statistics
        stats = simulation.get_statistics()
        stats_grp = f.create_group('statistics')
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                stats_grp.attrs[key] = value
            elif isinstance(value, dict):
                stats_grp.create_dataset(key, data=json.dumps(value).encode())

        # Save snapshots if available
        if hasattr(simulation, 'snapshots') and simulation.snapshots:
            snap_grp = f.create_group('snapshots')
            for i, snapshot in enumerate(simulation.snapshots):
                s_grp = snap_grp.create_group(f'snapshot_{i}')
                # Handle both dict and object snapshots
                if hasattr(snapshot, 'time_myr'):
                    # SimulationSnapshot object with time in Myr
                    s_grp.attrs['time_gyr'] = snapshot.time_myr / 1000.0
                    s_grp.attrs['active_civilizations'] = snapshot.active_civilizations

                    # Save probe data if available
                    if hasattr(snapshot, 'active_probes_in_flight') and snapshot.active_probes_in_flight:
                        probes = snapshot.active_probes_in_flight

                        # Convert probe snapshots to arrays
                        probe_ids = np.array([p.probe_id for p in probes], dtype=np.int32)
                        civ_ids = np.array([p.civ_id for p in probes], dtype=np.int32)
                        launch_star_idxs = np.array([p.launch_star_idx for p in probes], dtype=np.int32)
                        target_star_idxs = np.array([p.target_star_idx for p in probes], dtype=np.int32)
                        current_positions = np.array([p.current_position for p in probes], dtype=np.float32)
                        launch_times = np.array([p.launch_time_myr for p in probes], dtype=np.float32)
                        arrival_times = np.array([p.arrival_time_myr for p in probes], dtype=np.float32)
                        progress_fractions = np.array([p.progress_fraction for p in probes], dtype=np.float32)
                        velocities = np.array([p.velocity_c for p in probes], dtype=np.float32)
                        generations = np.array([p.generation for p in probes], dtype=np.int32)

                        # Store probe datasets
                        s_grp.create_dataset('probe_ids', data=probe_ids, compression=compression)
                        s_grp.create_dataset('probe_civ_ids', data=civ_ids, compression=compression)
                        s_grp.create_dataset('probe_launch_star_idxs', data=launch_star_idxs, compression=compression)
                        s_grp.create_dataset('probe_target_star_idxs', data=target_star_idxs, compression=compression)
                        s_grp.create_dataset('probe_current_positions', data=current_positions, compression=compression)
                        s_grp.create_dataset('probe_launch_times_myr', data=launch_times, compression=compression)
                        s_grp.create_dataset('probe_arrival_times_myr', data=arrival_times, compression=compression)
                        s_grp.create_dataset('probe_progress_fractions', data=progress_fractions, compression=compression)
                        s_grp.create_dataset('probe_velocities_c', data=velocities, compression=compression)
                        s_grp.create_dataset('probe_generations', data=generations, compression=compression)

                elif isinstance(snapshot, dict):
                    # Dict with time already in Gyr
                    s_grp.attrs['time_gyr'] = snapshot.get('time_gyr', 0.0)
                    s_grp.attrs['active_civilizations'] = snapshot.get('active_civilizations', 0)

        # Save hazard events if available
        if hasattr(simulation, 'hazard_events') and simulation.hazard_events:
            hazard_grp = f.create_group('hazard_events')

            # Convert to arrays for HDF5 storage
            times_myr = np.array([e.time_myr for e in simulation.hazard_events])
            event_types = np.array([e.event_type.encode('utf-8') for e in simulation.hazard_events], dtype='S20')
            energies = np.array([e.energy for e in simulation.hazard_events])
            radii_pc = np.array([e.sterilization_radius_pc for e in simulation.hazard_events])

            # Positions as N x 3 array
            positions = np.array([e.position for e in simulation.hazard_events])

            # Store datasets
            hazard_grp.create_dataset('time_myr', data=times_myr, compression=compression)
            hazard_grp.create_dataset('event_type', data=event_types)
            hazard_grp.create_dataset('position', data=positions, compression=compression)
            hazard_grp.create_dataset('energy', data=energies, compression=compression)
            hazard_grp.create_dataset('sterilization_radius_pc', data=radii_pc, compression=compression)

            # Store affected civilization IDs as variable-length datasets
            affected_civ_ids = [e.affected_civ_ids for e in simulation.hazard_events]
            max_len = max(len(ids) for ids in affected_civ_ids) if affected_civ_ids else 0
            if max_len > 0:
                # Pad to fixed length for HDF5
                padded_ids = np.array([ids + [-1] * (max_len - len(ids)) for ids in affected_civ_ids])
                hazard_grp.create_dataset('affected_civ_ids', data=padded_ids, compression=compression)

    return h5_path


def load_simulation(path: str) -> Dict[str, Any]:
    """
    Load simulation results from HDF5 file.

    Args:
        path: Path to .h5 file

    Returns:
        Dictionary containing simulation data
    """
    path = Path(path).with_suffix('.h5')

    if not path.exists():
        raise FileNotFoundError(f"Simulation file not found: {path}")

    data = {}

    with h5py.File(path, 'r') as f:
        # Load galaxy data
        if 'galaxy' in f:
            data['galaxy'] = {
                'positions': f['galaxy/positions'][:] if 'positions' in f['galaxy'] else None,
                'ages': f['galaxy/ages'][:] if 'ages' in f['galaxy'] else None,
                'metallicities': f['galaxy/metallicities'][:] if 'metallicities' in f['galaxy'] else None,
            }

        # Load civilization data
        if 'civilizations' in f:
            civ_grp = f['civilizations']
            data['civilizations'] = []

            # Check if there are any civilizations
            if 'parent_star_idx' in civ_grp:
                n_civs = len(civ_grp['parent_star_idx'])

                for i in range(n_civs):
                    civ = {
                        'parent_star_idx': int(civ_grp['parent_star_idx'][i]),
                        'emergence_time_gyr': float(civ_grp['emergence_time_gyr'][i]),
                        'is_active': bool(civ_grp['is_active'][i]),
                        'extinction_time_gyr': float(civ_grp['extinction_time_gyr'][i])
                                              if civ_grp['extinction_time_gyr'][i] >= 0 else None,
                        'kardashev_level': float(civ_grp['kardashev_level'][i])
                                          if 'kardashev_level' in civ_grp else 0.7,
                        'death_cause': civ_grp['death_cause'][i].decode()
                                      if 'death_cause' in civ_grp and civ_grp['death_cause'][i]
                                      else None,
                    }

                    # Load colonized stars if available
                    if 'colonized_stars' in civ_grp:
                        colonized = civ_grp['colonized_stars'][i]
                        # Remove padding (-1 values)
                        civ['colonized_stars'] = [int(idx) for idx in colonized if idx >= 0]
                    else:
                        civ['colonized_stars'] = [civ['parent_star_idx']]  # At least home world

                    # Load colony arrival times if available
                    if 'colony_arrival_indices' in civ_grp and 'colony_arrival_times_myr' in civ_grp:
                        indices = civ_grp['colony_arrival_indices'][i]
                        times = civ_grp['colony_arrival_times_myr'][i]

                        # Reconstruct dict, removing padding (-1 values)
                        civ['colony_arrival_times'] = {}
                        for idx, time in zip(indices, times):
                            if idx >= 0 and time >= 0:
                                civ['colony_arrival_times'][int(idx)] = float(time)
                    # Don't set key if data doesn't exist - let reconstruct function handle fallback

                    data['civilizations'].append(civ)
        else:
            data['civilizations'] = []

        # Load statistics
        if 'statistics' in f:
            data['statistics'] = dict(f['statistics'].attrs)
            for key in f['statistics'].keys():
                try:
                    data['statistics'][key] = json.loads(f['statistics'][key][()].decode())
                except:
                    pass

        # Load snapshots
        if 'snapshots' in f:
            data['snapshots'] = []
            # Sort snapshot names numerically (snapshot_0, snapshot_1, snapshot_2, ...)
            # Not alphabetically (which would give snapshot_0, snapshot_1, snapshot_10, ...)
            snap_names = sorted(f['snapshots'].keys(),
                               key=lambda x: int(x.split('_')[1]) if '_' in x else 0)
            for snap_name in snap_names:
                s_grp = f['snapshots'][snap_name]
                snapshot = {
                    'time_gyr': s_grp.attrs.get('time_gyr', 0.0),
                    'active_civilizations': s_grp.attrs.get('active_civilizations', 0),
                    'positions': s_grp['positions'][:] if 'positions' in s_grp else None,
                }

                # Load probe data if available
                if 'probe_ids' in s_grp:
                    n_probes = len(s_grp['probe_ids'])
                    probes = []

                    for i in range(n_probes):
                        probe = {
                            'probe_id': int(s_grp['probe_ids'][i]),
                            'civ_id': int(s_grp['probe_civ_ids'][i]),
                            'launch_star_idx': int(s_grp['probe_launch_star_idxs'][i]),
                            'target_star_idx': int(s_grp['probe_target_star_idxs'][i]),
                            'current_position': s_grp['probe_current_positions'][i].tolist(),
                            'launch_time_myr': float(s_grp['probe_launch_times_myr'][i]),
                            'arrival_time_myr': float(s_grp['probe_arrival_times_myr'][i]),
                            'progress_fraction': float(s_grp['probe_progress_fractions'][i]),
                            'velocity_c': float(s_grp['probe_velocities_c'][i]),
                            'generation': int(s_grp['probe_generations'][i]),
                        }
                        probes.append(probe)

                    snapshot['probes'] = probes

                data['snapshots'].append(snapshot)

        # Load hazard events
        if 'hazard_events' in f:
            hazard_grp = f['hazard_events']
            data['hazard_events'] = []

            if 'time_myr' in hazard_grp:
                n_events = len(hazard_grp['time_myr'])

                for i in range(n_events):
                    # Extract affected civ IDs (remove padding -1s)
                    affected_ids = []
                    if 'affected_civ_ids' in hazard_grp:
                        ids = hazard_grp['affected_civ_ids'][i].tolist()
                        affected_ids = [cid for cid in ids if cid >= 0]

                    event = {
                        'time_myr': float(hazard_grp['time_myr'][i]),
                        'time_gyr': float(hazard_grp['time_myr'][i]) / 1000.0,
                        'event_type': hazard_grp['event_type'][i].decode('utf-8'),
                        'position': hazard_grp['position'][i].tolist(),
                        'energy': float(hazard_grp['energy'][i]),
                        'sterilization_radius_pc': float(hazard_grp['sterilization_radius_pc'][i]),
                        'affected_civ_ids': affected_ids
                    }
                    data['hazard_events'].append(event)
        else:
            data['hazard_events'] = []

    return data


def export_interactive_plot(fig, path: str, auto_open: bool = False):
    """
    Export plotly or three.js figure to standalone HTML.

    Args:
        fig: Plotly figure or three.js renderer
        path: Output HTML path
        auto_open: Whether to open in browser
    """
    path = Path(path).with_suffix('.html')
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Try plotly export
        if hasattr(fig, 'write_html'):
            fig.write_html(str(path), auto_open=auto_open)
        # Try pythreejs export
        elif hasattr(fig, 'html'):
            with open(path, 'w') as f:
                f.write(fig.html())
        else:
            raise ValueError(f"Unknown figure type: {type(fig)}")

        return path

    except Exception as e:
        print(f"Error exporting plot: {e}")
        return None


def reconstruct_simulation_from_hdf5(path: str):
    """
    Reconstruct a GalaxySimulation object from HDF5 file for visualization.

    Args:
        path: Path to .h5 file

    Returns:
        GalaxySimulation object suitable for visualization

    Note:
        This recreates the simulation state from saved data but won't have
        all internal state (e.g., spatial indices, running simulation).
        Suitable for visualization and analysis only.
    """
    from ..simulation.engine import GalaxySimulation, CivilizationState
    from ..galaxy.structure import GalaxyModel
    from ..config.parameters import SimulationConfig

    # Load raw data
    data = load_simulation(path)

    # Create minimal config
    config = SimulationConfig()
    config.galaxy.total_stars = len(data['galaxy']['positions'])

    # Create galaxy model from loaded data
    galaxy = GalaxyModel(config.galaxy)
    galaxy.positions = data['galaxy']['positions']
    galaxy.ages = data['galaxy']['ages']
    galaxy.metallicities = data['galaxy']['metallicities']

    # Need to set other required attributes for visualization
    # Use placeholder values since we only need positions for viz
    galaxy.stellar_types = np.ones(len(galaxy.positions), dtype=int)  # All habitable
    galaxy.velocities = np.zeros_like(galaxy.positions)

    # Create simulation object
    sim = GalaxySimulation(config, seed=42)
    sim.galaxy = galaxy

    # Reconstruct civilization states
    sim.civilizations = []
    for civ_data in data['civilizations']:
        # Create minimal CivilizationState
        civ = CivilizationState(
            civ_id=len(sim.civilizations),
            parent_star_idx=civ_data['parent_star_idx'],
            birth_time_myr=civ_data['emergence_time_gyr'] * 1000.0,
            kardashev_scale=civ_data.get('kardashev_level', 0.7)
        )

        civ.is_active = civ_data['is_active']
        if civ_data['extinction_time_gyr'] is not None:
            civ.death_time_myr = civ_data['extinction_time_gyr'] * 1000.0
        civ.death_cause = civ_data.get('death_cause')

        # Load colonized stars if available
        if 'colonized_stars' in civ_data:
            civ.colonized_stars = set(civ_data['colonized_stars'])
        else:
            civ.colonized_stars = {civ.parent_star_idx}

        # Load colony arrival times if available
        if 'colony_arrival_times' in civ_data:
            civ.colony_arrival_times = civ_data['colony_arrival_times']
        else:
            # Fallback for old h5 files: assume all colonies arrived shortly after birth
            # This allows old files to show trajectories/spheres
            # Use birth time + small offset for each colony
            civ.colony_arrival_times = {}
            for idx, star_idx in enumerate(sorted(civ.colonized_stars)):
                # Stagger arrival times slightly to avoid all at once
                civ.colony_arrival_times[star_idx] = civ.birth_time_myr + (idx * 10.0)

        sim.civilizations.append(civ)

    # Reconstruct hazard events if available
    if 'hazard_events' in data and data['hazard_events']:
        from ..simulation.engine import HazardEvent
        sim.hazard_events = []
        for event_data in data['hazard_events']:
            event = HazardEvent(
                time_myr=event_data['time_myr'],
                event_type=event_data['event_type'],
                position=np.array(event_data['position']),
                energy=event_data['energy'],
                sterilization_radius_pc=event_data['sterilization_radius_pc'],
                affected_civ_ids=event_data['affected_civ_ids']
            )
            sim.hazard_events.append(event)

    # Set simulation time
    if 'statistics' in data:
        sim.current_time_myr = data['statistics'].get('current_time_gyr', 0.0) * 1000.0

    # Reconstruct snapshots if available
    if 'snapshots' in data and data['snapshots']:
        from ..simulation.engine import SimulationSnapshot, ProbeSnapshot
        sim.snapshots = []
        for snap_data in data['snapshots']:
            # Reconstruct probe snapshots if available
            probe_snapshots = []
            if 'probes' in snap_data:
                for probe_data in snap_data['probes']:
                    probe = ProbeSnapshot(
                        probe_id=probe_data['probe_id'],
                        civ_id=probe_data['civ_id'],
                        launch_star_idx=probe_data['launch_star_idx'],
                        target_star_idx=probe_data['target_star_idx'],
                        current_position=np.array(probe_data['current_position']),
                        launch_time_myr=probe_data['launch_time_myr'],
                        arrival_time_myr=probe_data['arrival_time_myr'],
                        progress_fraction=probe_data['progress_fraction'],
                        velocity_c=probe_data['velocity_c'],
                        generation=probe_data['generation']
                    )
                    probe_snapshots.append(probe)

            snapshot = SimulationSnapshot(
                time_myr=snap_data['time_gyr'] * 1000.0,
                active_civilizations=snap_data['active_civilizations'],
                total_civilizations_ever=len(sim.civilizations),
                colonized_systems=sum(len(c.colonized_stars) for c in sim.civilizations),
                civilization_states=[],  # Not stored in snapshots
                stellar_positions=galaxy.positions,  # Use current galaxy positions
                active_probes_in_flight=probe_snapshots,
                total_active_probes=len(probe_snapshots)
            )
            sim.snapshots.append(snapshot)

    return sim


def create_results_summary(simulation) -> pd.DataFrame:
    """
    Create formatted summary table of simulation results.

    Args:
        simulation: GalaxySimulation instance or stats dict

    Returns:
        DataFrame with summary statistics
    """
    if hasattr(simulation, 'get_statistics'):
        stats = simulation.get_statistics()
    elif isinstance(simulation, dict):
        stats = simulation
    else:
        raise ValueError("Invalid simulation input")

    # Build summary rows
    rows = [
        ('Total Civilizations', stats.get('total_civilizations', 0)),
        ('Active Civilizations', stats.get('active_civilizations', 0)),
        ('Extinct Civilizations', stats.get('extinct_civilizations', 0)),
        ('Colonized Systems', stats.get('total_colonized_systems', 0)),
        ('Simulation Duration (Gyr)', f"{stats.get('current_time_gyr', 0):.2f}"),
    ]

    # Add death cause breakdown if available
    if 'death_causes' in stats and stats['death_causes']:
        for cause, count in stats['death_causes'].items():
            rows.append((f'Deaths: {cause}', count))

    df = pd.DataFrame(rows, columns=['Metric', 'Value'])
    return df


def create_threejs_visualization(positions: np.ndarray,
                                 colors: Optional[np.ndarray] = None,
                                 sizes: Optional[np.ndarray] = None) -> Any:
    """
    Create interactive 3D visualization using pythreejs.

    Args:
        positions: Nx3 array of positions
        colors: Nx3 array of RGB colors (0-1 range), optional
        sizes: N array of point sizes, optional

    Returns:
        pythreejs renderer object
    """
    try:
        import pythreejs as p3
        from IPython.display import display

        # Default colors (white) and sizes
        if colors is None:
            colors = np.ones((len(positions), 3)) * 0.8
        if sizes is None:
            sizes = np.ones(len(positions)) * 0.1

        # Create geometry
        geometry = p3.BufferGeometry(
            attributes={
                'position': p3.BufferAttribute(positions.astype('float32')),
                'color': p3.BufferAttribute(colors.astype('float32')),
            }
        )

        # Create material
        material = p3.PointsMaterial(
            size=0.05,
            vertexColors='VertexColors',
            transparent=True,
            opacity=0.8
        )

        # Create points
        points = p3.Points(geometry=geometry, material=material)

        # Create scene
        scene = p3.Scene(children=[points], background='#000000')

        # Create camera
        camera = p3.PerspectiveCamera(position=[0, 0, 30], aspect=16/9)

        # Create controls
        controls = p3.OrbitControls(controlling=camera)

        # Create renderer
        renderer = p3.Renderer(
            scene=scene,
            camera=camera,
            controls=[controls],
            width=960,
            height=540
        )

        return renderer

    except ImportError:
        print("Warning: pythreejs not available. Install with: pip install pythreejs")
        return None
