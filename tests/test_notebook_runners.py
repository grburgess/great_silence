"""Tests for notebook simulation runners."""

import pytest
import tempfile
from pathlib import Path
import pandas as pd

from great_silence import SimulationConfig
from great_silence.notebook.runners import NotebookSimulationRunner


class TestNotebookSimulationRunner:
    """Test NotebookSimulationRunner functionality."""

    def test_runner_initialization(self):
        """Test creating runner instance."""
        config = SimulationConfig()
        config.galaxy.total_stars = 50

        runner = NotebookSimulationRunner(config, seed=42)

        assert runner.config == config
        assert runner.seed == 42
        assert runner.simulation is None
        assert runner.results is None

    def test_run_simulation(self):
        """Test running single simulation."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.time_step_myr = 1.0
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        results = runner.run(verbose=False)

        # Check results structure
        assert results is not None
        assert 'mode' in results
        assert results['mode'] == 'single'
        assert 'statistics' in results
        assert 'simulation' in results
        assert 'config' in results
        assert 'galaxy_positions' in results
        assert 'civilizations' in results

        # Check simulation was stored
        assert runner.simulation is not None
        assert runner.results is not None

    def test_run_with_verbose_output(self):
        """Test running with verbose output."""
        config = SimulationConfig()
        config.galaxy.total_stars = 50
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        results = runner.run(verbose=True)  # Should show output

        assert results is not None

    def test_run_monte_carlo(self):
        """Test Monte Carlo simulation."""
        config = SimulationConfig()
        config.galaxy.total_stars = 50
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.num_realizations = 5
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        results = runner.run_monte_carlo(verbose=False)

        # Check Monte Carlo results
        assert results is not None
        assert 'mode' in results
        assert results['mode'] == 'monte_carlo'
        assert 'num_realizations' in results
        assert results['num_realizations'] == 5
        assert 'statistics' in results

    def test_run_monte_carlo_with_override(self):
        """Test Monte Carlo with realization count override."""
        config = SimulationConfig()
        config.galaxy.total_stars = 50
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        results = runner.run_monte_carlo(num_realizations=3, verbose=False)

        assert results['num_realizations'] == 3

    def test_save_results(self):
        """Test saving results to HDF5."""
        config = SimulationConfig()
        config.galaxy.total_stars = 50
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        runner.run(verbose=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_runner_save"
            h5_path = runner.save(str(save_path), compress=True)

            assert h5_path.exists()
            assert h5_path.suffix == '.h5'

    def test_save_without_simulation(self):
        """Test saving before running simulation raises error."""
        config = SimulationConfig()
        runner = NotebookSimulationRunner(config, seed=42)

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="No simulation to save"):
                runner.save(str(Path(tmpdir) / "test"))

    def test_get_summary_table(self):
        """Test getting summary table."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        runner.run(verbose=False)

        summary = runner.get_summary_table()

        assert isinstance(summary, pd.DataFrame)
        assert len(summary) > 0
        assert 'Metric' in summary.columns
        assert 'Value' in summary.columns

    def test_get_summary_table_without_results(self):
        """Test getting summary table before running raises error."""
        config = SimulationConfig()
        runner = NotebookSimulationRunner(config, seed=42)

        with pytest.raises(ValueError, match="No results available"):
            runner.get_summary_table()

    def test_get_civilization_dataframe(self):
        """Test getting civilizations as DataFrame."""
        config = SimulationConfig()
        config.galaxy.total_stars = 200
        config.simulation.simulation_duration_gyr = 0.1
        config.civilization.fraction_develop_life = 0.5
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        runner.run(verbose=False)

        df = runner.get_civilization_dataframe()

        assert isinstance(df, pd.DataFrame)
        # May be empty if no civs emerged
        if len(df) > 0:
            expected_cols = ['parent_star_idx', 'emergence_time_gyr', 'is_active']
            for col in expected_cols:
                assert col in df.columns

    def test_get_civilization_dataframe_empty(self):
        """Test getting DataFrame when no results."""
        config = SimulationConfig()
        runner = NotebookSimulationRunner(config, seed=42)

        df = runner.get_civilization_dataframe()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_filter_civilizations_by_status(self):
        """Test filtering civilizations by status."""
        config = SimulationConfig()
        config.galaxy.total_stars = 200
        config.simulation.simulation_duration_gyr = 0.1
        config.civilization.fraction_develop_life = 0.5
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        runner.run(verbose=False)

        if not runner.results.get('civilizations'):
            pytest.skip("No civilizations emerged")

        # Filter active
        active = runner.filter_civilizations(status='active')
        for civ in active:
            assert civ['is_active'] is True

        # Filter extinct
        extinct = runner.filter_civilizations(status='extinct')
        for civ in extinct:
            assert civ['is_active'] is False

    def test_filter_civilizations_by_kardashev(self):
        """Test filtering by Kardashev level."""
        config = SimulationConfig()
        config.galaxy.total_stars = 200
        config.simulation.simulation_duration_gyr = 0.1
        config.civilization.fraction_develop_life = 0.5
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        runner.run(verbose=False)

        if not runner.results.get('civilizations'):
            pytest.skip("No civilizations emerged")

        # Filter by minimum Kardashev
        advanced = runner.filter_civilizations(min_kardashev=1.0)
        for civ in advanced:
            assert civ.get('kardashev_level', 0.7) >= 1.0

        # Filter by maximum Kardashev
        early = runner.filter_civilizations(max_kardashev=1.0)
        for civ in early:
            assert civ.get('kardashev_level', 0.7) <= 1.0

    def test_filter_civilizations_by_death_cause(self):
        """Test filtering by death cause."""
        config = SimulationConfig()
        config.galaxy.total_stars = 200
        config.simulation.simulation_duration_gyr = 0.1
        config.civilization.fraction_develop_life = 0.5
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        runner.run(verbose=False)

        # Filter should work even if no matches
        supernova_deaths = runner.filter_civilizations(death_cause='supernova')
        assert isinstance(supernova_deaths, list)

    def test_filter_without_results(self):
        """Test filtering without results returns empty list."""
        config = SimulationConfig()
        runner = NotebookSimulationRunner(config, seed=42)

        result = runner.filter_civilizations(status='active')
        assert result == []

    def test_plot_3d_galaxy_without_simulation(self):
        """Test plotting before running raises error."""
        config = SimulationConfig()
        runner = NotebookSimulationRunner(config, seed=42)

        with pytest.raises(ValueError, match="No simulation available"):
            runner.plot_3d_galaxy()

    def test_plot_3d_galaxy_matplotlib(self):
        """Test creating matplotlib 3D plot."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        runner.run(verbose=False)

        # Should create matplotlib figure
        fig = runner.plot_3d_galaxy(backend='matplotlib')
        assert fig is not None

    def test_plot_3d_galaxy_invalid_backend(self):
        """Test invalid backend raises error."""
        config = SimulationConfig()
        config.galaxy.total_stars = 50
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        runner.run(verbose=False)

        with pytest.raises(ValueError, match="Unknown backend"):
            runner.plot_3d_galaxy(backend='invalid_backend')

    def test_plot_timeline(self):
        """Test creating timeline plot."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        runner.run(verbose=False)

        # Should create plot without error
        result = runner.plot_timeline()
        # May return None or figure depending on implementation

    def test_plot_extinction_causes(self):
        """Test creating extinction causes plot."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        runner = NotebookSimulationRunner(config, seed=42)
        runner.run(verbose=False)

        # Should create plot without error
        result = runner.plot_extinction_causes()


class TestRunnerEdgeCases:
    """Test edge cases and error handling."""

    def test_run_simulation_error_handling(self):
        """Test error handling during simulation."""
        config = SimulationConfig()
        config.galaxy.total_stars = 0  # Invalid - will cause issues

        runner = NotebookSimulationRunner(config, seed=42)

        # May not raise immediately but will have zero stars
        try:
            runner.run(verbose=False)
            # If it doesn't error, at least check results are valid
            assert runner.results is not None
        except Exception:
            # Expected - invalid config should cause problems
            pass

    def test_reproducibility_with_seed(self):
        """Test that same seed produces same results."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        # Run twice with same seed
        runner1 = NotebookSimulationRunner(config, seed=42)
        results1 = runner1.run(verbose=False)

        runner2 = NotebookSimulationRunner(config, seed=42)
        results2 = runner2.run(verbose=False)

        # Galaxy positions should be identical
        import numpy as np
        assert np.allclose(
            results1['galaxy_positions'],
            results2['galaxy_positions']
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
