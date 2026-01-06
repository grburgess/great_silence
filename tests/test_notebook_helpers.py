"""Tests for notebook helper functions."""

import numpy as np
import pytest
import tempfile
from pathlib import Path

from great_silence import SimulationConfig, GalaxySimulation
from great_silence.notebook.helpers import (
    save_simulation_hdf5,
    load_simulation,
    create_results_summary,
)


class TestHDF5SaveLoad:
    """Test HDF5 save and load functionality."""

    def test_save_and_load_simulation(self):
        """Test saving and loading simulation results."""
        # Create small simulation
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.time_step_myr = 1.0
        config.simulation.save_snapshots = False

        sim = GalaxySimulation(config, seed=42)
        sim.run(verbose=False)

        # Save to temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_sim"
            h5_path = save_simulation_hdf5(sim, str(save_path), compress=True)

            assert h5_path.exists()
            assert h5_path.suffix == '.h5'

            # Load back
            data = load_simulation(str(save_path))

            # Verify galaxy data
            assert 'galaxy' in data
            assert data['galaxy']['positions'] is not None
            assert len(data['galaxy']['positions']) == 100
            assert data['galaxy']['ages'] is not None
            assert data['galaxy']['metallicities'] is not None

            # Verify statistics
            assert 'statistics' in data
            assert 'total_civilizations' in data['statistics']

            # Verify civilizations
            assert 'civilizations' in data
            if sim.civilizations:
                assert len(data['civilizations']) == len(sim.civilizations)

    def test_save_with_snapshots(self):
        """Test saving simulation with snapshots."""
        config = SimulationConfig()
        config.galaxy.total_stars = 50
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.time_step_myr = 1.0
        config.simulation.save_snapshots = True
        config.simulation.snapshot_interval_myr = 5.0

        sim = GalaxySimulation(config, seed=42)
        sim.run(verbose=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_sim_snapshots"
            h5_path = save_simulation_hdf5(sim, str(save_path))

            # Load and verify snapshots
            data = load_simulation(str(save_path))

            if hasattr(sim, 'snapshots') and sim.snapshots:
                assert 'snapshots' in data
                assert len(data['snapshots']) > 0

    def test_save_without_compression(self):
        """Test saving without compression."""
        config = SimulationConfig()
        config.galaxy.total_stars = 50
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        sim = GalaxySimulation(config, seed=42)
        sim.run(verbose=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_sim_uncompressed"
            h5_path = save_simulation_hdf5(sim, str(save_path), compress=False)

            assert h5_path.exists()

            # Should still load correctly
            data = load_simulation(str(save_path))
            assert data['galaxy']['positions'] is not None

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_simulation('nonexistent_file.h5')

    def test_civilization_data_integrity(self):
        """Test civilization data is preserved correctly."""
        config = SimulationConfig()
        config.galaxy.total_stars = 200
        config.simulation.simulation_duration_gyr = 0.1
        config.civilization.fraction_develop_life = 0.5  # Increase emergence
        config.simulation.save_snapshots = False

        sim = GalaxySimulation(config, seed=42)
        sim.run(verbose=False)

        if not sim.civilizations:
            pytest.skip("No civilizations emerged in test")

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_civs"
            save_simulation_hdf5(sim, str(save_path))

            data = load_simulation(str(save_path))

            # Compare first civilization
            if data['civilizations']:
                loaded_civ = data['civilizations'][0]
                original_civ = sim.civilizations[0]

                assert loaded_civ['parent_star_idx'] == original_civ.parent_star_idx
                assert loaded_civ['emergence_time_gyr'] == pytest.approx(
                    original_civ.birth_time_myr / 1000.0, rel=1e-5
                )
                assert loaded_civ['is_active'] == original_civ.is_active


class TestResultsSummary:
    """Test results summary creation."""

    def test_create_summary_from_simulation(self):
        """Test creating summary from simulation object."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        sim = GalaxySimulation(config, seed=42)
        sim.run(verbose=False)

        summary = create_results_summary(sim)

        # Check DataFrame structure
        assert len(summary) >= 5  # At least 5 basic stats
        assert 'Metric' in summary.columns
        assert 'Value' in summary.columns

        # Check content
        metrics = summary['Metric'].values
        assert 'Total Civilizations' in metrics
        assert 'Active Civilizations' in metrics
        assert 'Extinct Civilizations' in metrics

    def test_create_summary_from_dict(self):
        """Test creating summary from stats dictionary."""
        stats = {
            'total_civilizations': 100,
            'active_civilizations': 20,
            'extinct_civilizations': 80,
            'total_colonized_systems': 50,
            'current_time_gyr': 10.0,
        }

        summary = create_results_summary(stats)

        assert len(summary) >= 5
        assert 'Metric' in summary.columns
        assert 'Value' in summary.columns

        # Verify values
        values_dict = dict(zip(summary['Metric'], summary['Value']))
        assert values_dict['Total Civilizations'] == 100
        assert values_dict['Active Civilizations'] == 20

    def test_summary_with_death_causes(self):
        """Test summary includes death causes when available."""
        stats = {
            'total_civilizations': 100,
            'active_civilizations': 20,
            'extinct_civilizations': 80,
            'total_colonized_systems': 50,
            'current_time_gyr': 10.0,
            'death_causes': {
                'supernova': 30,
                'self_destruction': 40,
                'grb': 10,
            }
        }

        summary = create_results_summary(stats)

        # Should have death cause breakdown
        assert len(summary) > 5
        metrics = summary['Metric'].values

        assert 'Deaths: supernova' in metrics
        assert 'Deaths: self_destruction' in metrics
        assert 'Deaths: grb' in metrics


class TestExportFunctions:
    """Test export and visualization helper functions."""

    def test_export_interactive_plot_invalid_type(self):
        """Test exporting invalid figure type."""
        from great_silence.notebook.helpers import export_interactive_plot

        class DummyFig:
            pass

        fig = DummyFig()

        with tempfile.TemporaryDirectory() as tmpdir:
            output = export_interactive_plot(fig, Path(tmpdir) / "test.html")
            assert output is None  # Should return None on error


class TestThreeJSVisualization:
    """Test Three.js visualization creation."""

    def test_create_threejs_without_pythreejs(self):
        """Test graceful handling when pythreejs not available."""
        from great_silence.notebook.helpers import create_threejs_visualization

        positions = np.random.rand(100, 3) * 20 - 10

        # Should return None if pythreejs not available
        # (or return renderer if it is available)
        result = create_threejs_visualization(positions)

        # Either None (missing pythreejs) or renderer object
        assert result is None or hasattr(result, 'scene')

    def test_create_threejs_with_colors_and_sizes(self):
        """Test creating visualization with custom colors and sizes."""
        from great_silence.notebook.helpers import create_threejs_visualization

        positions = np.random.rand(50, 3) * 20 - 10
        colors = np.random.rand(50, 3)  # RGB values
        sizes = np.ones(50) * 0.2

        # Should handle custom parameters
        result = create_threejs_visualization(positions, colors, sizes)

        # Either None (missing pythreejs) or renderer object
        assert result is None or hasattr(result, 'scene')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
