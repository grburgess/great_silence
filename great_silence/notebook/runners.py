"""Notebook-specific simulation runner with progress tracking."""

from typing import Optional, Dict, Any
import sys
from io import StringIO
from pathlib import Path

from great_silence import GalaxySimulation, SimulationConfig
from great_silence.simulation.monte_carlo import MonteCarloRunner
from .helpers import save_simulation_hdf5, create_results_summary


class NotebookSimulationRunner:
    """
    Wrapper for GalaxySimulation with notebook-specific features.

    Provides:
    - Progress tracking via ipywidgets
    - Result packaging
    - Snapshot management
    - HDF5 persistence
    """

    def __init__(self, config: SimulationConfig, seed: Optional[int] = None):
        """
        Initialize notebook simulation runner.

        Args:
            config: SimulationConfig instance
            seed: Random seed for reproducibility
        """
        self.config = config
        self.seed = seed
        self.simulation = None
        self.results = None
        self.output_messages = []

    def run(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Run single simulation with progress tracking.

        Args:
            verbose: Show progress output

        Returns:
            Dictionary with results
        """
        try:
            # Create simulation
            self.simulation = GalaxySimulation(self.config, seed=self.seed)

            # Capture output if not verbose
            if not verbose:
                old_stdout = sys.stdout
                sys.stdout = StringIO()

            # Run simulation
            self.simulation.run(verbose=verbose)

            # Restore stdout
            if not verbose:
                sys.stdout = old_stdout

            # Package results
            self.results = self._package_results()

            return self.results

        except Exception as e:
            # Restore stdout on error
            if not verbose and 'old_stdout' in locals():
                sys.stdout = old_stdout
            raise RuntimeError(f"Simulation failed: {e}") from e

    def run_monte_carlo(self,
                       num_realizations: Optional[int] = None,
                       verbose: bool = True) -> Dict[str, Any]:
        """
        Run Monte Carlo ensemble.

        Args:
            num_realizations: Number of realizations (uses config if None)
            verbose: Show progress

        Returns:
            Dictionary with aggregate results
        """
        if num_realizations is not None:
            self.config.simulation.num_realizations = num_realizations

        # Create Monte Carlo runner
        mc_runner = MonteCarloRunner(self.config)

        # Run ensemble (sequential for simplicity in notebook)
        if verbose:
            print(f"Running {self.config.simulation.num_realizations} realizations...")

        mc_runner.run_sequential()
        results = mc_runner.analyze_results()

        # Store results
        self.results = {
            'mode': 'monte_carlo',
            'num_realizations': self.config.simulation.num_realizations,
            'statistics': results,
            'config': self.config.to_dict()
        }

        return self.results

    def _package_results(self) -> Dict[str, Any]:
        """Package simulation results for widgets."""
        if self.simulation is None:
            return {}

        stats = self.simulation.get_statistics()

        results = {
            'mode': 'single',
            'statistics': stats,
            'simulation': self.simulation,
            'config': self.config.to_dict(),
            'galaxy_positions': self.simulation.galaxy.positions,
            'civilizations': [
                {
                    'parent_star_idx': civ.parent_star_idx,
                    'emergence_time_gyr': civ.emergence_time_gyr,
                    'is_active': civ.is_active,
                    'extinction_time_gyr': getattr(civ, 'extinction_time_gyr', None),
                    'kardashev_level': getattr(civ, 'kardashev_level', 0.7),
                    'death_cause': getattr(civ, 'death_cause', None),
                }
                for civ in self.simulation.civilizations
            ] if self.simulation.civilizations else [],
            'snapshots': getattr(self.simulation, 'snapshots', []),
        }

        return results

    def save(self, path: str, compress: bool = True) -> Path:
        """
        Save results to HDF5.

        Args:
            path: Output path (without extension)
            compress: Use gzip compression

        Returns:
            Path to saved file
        """
        if self.simulation is None:
            raise ValueError("No simulation to save. Run simulation first.")

        return save_simulation_hdf5(self.simulation, path, compress=compress)

    def get_summary_table(self):
        """
        Get formatted summary table.

        Returns:
            pandas DataFrame with statistics
        """
        if self.results is None:
            raise ValueError("No results available. Run simulation first.")

        return create_results_summary(self.results['statistics'])

    def get_civilization_dataframe(self):
        """
        Get civilizations as pandas DataFrame.

        Returns:
            DataFrame with civilization data
        """
        import pandas as pd

        if self.results is None or not self.results.get('civilizations'):
            return pd.DataFrame()

        return pd.DataFrame(self.results['civilizations'])

    def filter_civilizations(self,
                            status: Optional[str] = None,
                            min_kardashev: Optional[float] = None,
                            max_kardashev: Optional[float] = None,
                            death_cause: Optional[str] = None):
        """
        Filter civilizations by criteria.

        Args:
            status: 'active' or 'extinct'
            min_kardashev: Minimum Kardashev level
            max_kardashev: Maximum Kardashev level
            death_cause: Filter by specific death cause

        Returns:
            Filtered list of civilization dicts
        """
        if self.results is None or not self.results.get('civilizations'):
            return []

        civs = self.results['civilizations']

        # Apply filters
        if status == 'active':
            civs = [c for c in civs if c['is_active']]
        elif status == 'extinct':
            civs = [c for c in civs if not c['is_active']]

        if min_kardashev is not None:
            civs = [c for c in civs if c.get('kardashev_level', 0.7) >= min_kardashev]

        if max_kardashev is not None:
            civs = [c for c in civs if c.get('kardashev_level', 0.7) <= max_kardashev]

        if death_cause is not None:
            civs = [c for c in civs if c.get('death_cause') == death_cause]

        return civs

    def plot_3d_galaxy(self, show_civilizations: bool = True, backend: str = 'plotly'):
        """
        Create 3D galaxy visualization.

        Args:
            show_civilizations: Highlight civilizations
            backend: 'plotly', 'threejs', or 'matplotlib'

        Returns:
            Figure object
        """
        if self.simulation is None:
            raise ValueError("No simulation available. Run simulation first.")

        from great_silence.visualization import GalaxyVisualizer

        viz = GalaxyVisualizer()
        positions = self.simulation.galaxy.positions

        if backend == 'matplotlib':
            import matplotlib.pyplot as plt
            viz.plot_galaxy_structure(positions, save_path=None)
            return plt.gcf()  # Return current figure

        elif backend == 'plotly':
            import plotly.graph_objects as go

            # Create 3D scatter
            fig = go.Figure()

            # Add all stars
            fig.add_trace(go.Scatter3d(
                x=positions[:, 0],
                y=positions[:, 1],
                z=positions[:, 2],
                mode='markers',
                marker=dict(
                    size=1,
                    color='white',
                    opacity=0.3
                ),
                name='Stars'
            ))

            # Add civilizations if requested
            if show_civilizations and self.simulation.civilizations:
                civ_indices = [c.parent_star_idx for c in self.simulation.civilizations if c.is_active]
                if civ_indices:
                    civ_pos = positions[civ_indices]
                    fig.add_trace(go.Scatter3d(
                        x=civ_pos[:, 0],
                        y=civ_pos[:, 1],
                        z=civ_pos[:, 2],
                        mode='markers',
                        marker=dict(
                            size=4,
                            color='red',
                            opacity=1.0
                        ),
                        name='Civilizations'
                    ))

            fig.update_layout(
                title='Galaxy Structure',
                scene=dict(
                    xaxis_title='X (kpc)',
                    yaxis_title='Y (kpc)',
                    zaxis_title='Z (kpc)',
                    bgcolor='black'
                ),
                showlegend=True,
                width=900,
                height=700
            )

            return fig

        elif backend == 'threejs':
            from .helpers import create_threejs_visualization
            return create_threejs_visualization(positions)

        else:
            raise ValueError(f"Unknown backend: {backend}")

    def plot_timeline(self):
        """Create timeline visualization."""
        if self.simulation is None:
            raise ValueError("No simulation available. Run simulation first.")

        from great_silence.visualization import TimelineAnimator

        animator = TimelineAnimator(self.simulation)

        # Extract data from simulation
        if hasattr(self.simulation, 'snapshots') and self.simulation.snapshots:
            times_gyr = [s.time_gyr for s in self.simulation.snapshots]
            n_active = [s.active_civilizations for s in self.simulation.snapshots]
            n_total = [len([c for c in self.simulation.civilizations if c.emergence_time_gyr <= t])
                      for t in times_gyr]
            return animator.plot_timeline_statistics(times_gyr, n_active, n_total)
        else:
            print("No snapshots available for timeline visualization.")
            return None

    def plot_extinction_causes(self):
        """Create extinction cause breakdown."""
        if self.simulation is None:
            raise ValueError("No simulation available. Run simulation first.")

        from great_silence.visualization import TimelineAnimator

        animator = TimelineAnimator(self.simulation)

        # Count extinction causes
        causes = {}
        for civ in self.simulation.civilizations:
            if not civ.is_active and hasattr(civ, 'death_cause') and civ.death_cause:
                causes[civ.death_cause] = causes.get(civ.death_cause, 0) + 1

        if causes:
            return animator.plot_extinction_causes(causes)
        else:
            print("No extinction data available.")
            return None
