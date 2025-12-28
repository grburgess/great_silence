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

        # Display confirmation
        display(HTML("<p style='color: #28a745;'>✓ Notebook display configured</p>"))

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
                    'emergence_time_gyr': civ.emergence_time_gyr,
                    'is_active': civ.is_active,
                    'extinction_time_gyr': civ.extinction_time_gyr if hasattr(civ, 'extinction_time_gyr') else None,
                    'kardashev_level': civ.kardashev_level if hasattr(civ, 'kardashev_level') else 0.7,
                    'death_cause': civ.death_cause if hasattr(civ, 'death_cause') else None,
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
                s_grp.attrs['time_gyr'] = snapshot.get('time_gyr', 0.0)
                s_grp.attrs['active_civilizations'] = snapshot.get('active_civilizations', 0)
                # Store snapshot data efficiently
                if 'positions' in snapshot and snapshot['positions'] is not None:
                    s_grp.create_dataset('positions', data=snapshot['positions'],
                                       compression=compression)

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
            n_civs = len(civ_grp['parent_star_idx'])
            data['civilizations'] = []

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
                data['civilizations'].append(civ)

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
            for snap_name in sorted(f['snapshots'].keys()):
                s_grp = f['snapshots'][snap_name]
                snapshot = {
                    'time_gyr': s_grp.attrs.get('time_gyr', 0.0),
                    'active_civilizations': s_grp.attrs.get('active_civilizations', 0),
                    'positions': s_grp['positions'][:] if 'positions' in s_grp else None,
                }
                data['snapshots'].append(snapshot)

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
