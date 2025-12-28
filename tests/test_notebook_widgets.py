"""Tests for notebook widgets."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from great_silence import SimulationConfig


# Skip all widget tests if ipywidgets not available
pytest.importorskip("ipywidgets")

from great_silence.notebook.widgets import (
    SimulationWidget,
    ResultsExplorer,
    AnimationBuilder,
)


class TestSimulationWidget:
    """Test SimulationWidget initialization and configuration."""

    def test_widget_initialization(self):
        """Test creating widget instance."""
        widget = SimulationWidget()

        # Check widget components exist
        assert widget.preset_selector is not None
        assert widget.num_stars_slider is not None
        assert widget.duration_slider is not None
        assert widget.seed_input is not None
        assert widget.monte_carlo_checkbox is not None
        assert widget.num_realizations_slider is not None
        assert widget.run_button is not None
        assert widget.output_area is not None

    def test_widget_default_values(self):
        """Test widget default values."""
        widget = SimulationWidget()

        assert widget.preset_selector.value == 'moderate'
        assert widget.num_stars_slider.value == 100_000
        assert widget.duration_slider.value == 10.0
        assert widget.seed_input.value == 42
        assert widget.monte_carlo_checkbox.value is False
        assert widget.num_realizations_slider.disabled is True

    def test_monte_carlo_toggle(self):
        """Test Monte Carlo checkbox enables/disables realizations slider."""
        widget = SimulationWidget()

        # Initially disabled
        assert widget.num_realizations_slider.disabled is True

        # Enable Monte Carlo
        widget.monte_carlo_checkbox.value = True
        assert widget.num_realizations_slider.disabled is False

        # Disable Monte Carlo
        widget.monte_carlo_checkbox.value = False
        assert widget.num_realizations_slider.disabled is True

    def test_create_config_from_widgets(self):
        """Test creating config from widget values."""
        widget = SimulationWidget()

        # Set widget values
        widget.preset_selector.value = 'optimistic'
        widget.num_stars_slider.value = 50_000
        widget.duration_slider.value = 5.0

        # Create config
        config = widget._create_config()

        assert config.galaxy.total_stars == 50_000
        assert config.simulation.simulation_duration_gyr == 5.0
        assert config.simulation.save_snapshots is True  # Always enabled

    def test_create_config_all_presets(self):
        """Test config creation with all presets."""
        widget = SimulationWidget()

        presets = ['moderate', 'optimistic', 'early_filter', 'late_filter', 'rare_earth']

        for preset in presets:
            widget.preset_selector.value = preset
            config = widget._create_config()

            # Should create valid config
            assert config is not None
            assert isinstance(config, SimulationConfig)

    def test_export_results_without_simulation(self):
        """Test exporting before running raises error."""
        widget = SimulationWidget()

        with pytest.raises(ValueError, match="No simulation to export"):
            widget.export_results("output/test")


class TestResultsExplorer:
    """Test ResultsExplorer widget."""

    def test_explorer_initialization(self):
        """Test creating explorer instance."""
        explorer = ResultsExplorer()

        # Check widget components
        assert explorer.status_filter is not None
        assert explorer.kardashev_min is not None
        assert explorer.kardashev_max is not None
        assert explorer.apply_button is not None
        assert explorer.output is not None

    def test_explorer_default_state(self):
        """Test explorer default state."""
        explorer = ResultsExplorer()

        # Filters should be disabled initially
        assert explorer.status_filter.disabled is True
        assert explorer.kardashev_min.disabled is True
        assert explorer.kardashev_max.disabled is True
        assert explorer.apply_button.disabled is True

    def test_explorer_with_path(self):
        """Test creating explorer with results path."""
        # Create dummy simulation and save
        from great_silence import GalaxySimulation

        config = SimulationConfig()
        config.galaxy.total_stars = 50
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        sim = GalaxySimulation(config, seed=42)
        sim.run(verbose=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            from great_silence.notebook.helpers import save_simulation_hdf5

            save_path = Path(tmpdir) / "test_results"
            h5_path = save_simulation_hdf5(sim, str(save_path))

            # Create explorer
            explorer = ResultsExplorer(str(h5_path))

            # Should have loaded data
            assert explorer.data is not None
            assert explorer.results_path == str(h5_path)

    def test_explorer_from_directory(self):
        """Test creating explorer from directory."""
        # Create dummy simulation
        from great_silence import GalaxySimulation
        from great_silence.notebook.helpers import save_simulation_hdf5

        config = SimulationConfig()
        config.galaxy.total_stars = 50
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = False

        sim = GalaxySimulation(config, seed=42)
        sim.run(verbose=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save simulation
            save_path = Path(tmpdir) / "test_results"
            save_simulation_hdf5(sim, str(save_path))

            # Create explorer from directory
            explorer = ResultsExplorer.from_directory(tmpdir)

            # Should have file selector
            assert hasattr(explorer, 'file_selector')
            assert hasattr(explorer, 'load_button')

    def test_explorer_from_empty_directory(self):
        """Test creating explorer from directory with no files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="No .h5 files found"):
                ResultsExplorer.from_directory(tmpdir)


class TestAnimationBuilder:
    """Test AnimationBuilder widget."""

    def test_builder_initialization(self):
        """Test creating builder instance."""
        builder = AnimationBuilder()

        # Check widget components
        assert builder.fps_slider is not None
        assert builder.duration_slider is not None
        assert builder.output_path is not None
        assert builder.create_button is not None
        assert builder.output is not None

    def test_builder_default_values(self):
        """Test builder default values."""
        builder = AnimationBuilder()

        assert builder.fps_slider.value == 30
        assert builder.duration_slider.value == 60
        assert builder.output_path.value == 'output/animation.mp4'

    def test_builder_with_data(self):
        """Test creating builder with simulation data."""
        # Create dummy simulation
        from great_silence import GalaxySimulation

        config = SimulationConfig()
        config.galaxy.total_stars = 50
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = True
        config.simulation.snapshot_interval_myr = 5.0

        sim = GalaxySimulation(config, seed=42)
        sim.run(verbose=False)

        # Package data
        data = {
            'simulation': sim,
            'mode': 'single',
        }

        builder = AnimationBuilder(data)

        assert builder.data is not None
        assert builder.data == data


class TestWidgetInteractions:
    """Test widget interaction flows."""

    @patch('great_silence.notebook.runners.GalaxySimulation')
    def test_simulation_widget_run_flow(self, mock_sim_class):
        """Test running simulation through widget."""
        # Mock simulation
        mock_sim = Mock()
        mock_sim.run = Mock()
        mock_sim.get_statistics = Mock(return_value={
            'total_civilizations': 10,
            'active_civilizations': 5,
            'extinct_civilizations': 5,
        })
        mock_sim.civilizations = []
        mock_sim.galaxy = Mock()
        mock_sim.galaxy.positions = [[0, 0, 0]]
        mock_sim_class.return_value = mock_sim

        widget = SimulationWidget()

        # Simulate button click
        widget._on_run_clicked(None)

        # Should have created runner
        assert widget.runner is not None

    def test_widget_layout_exists(self):
        """Test that widget layouts are created."""
        widget = SimulationWidget()

        assert hasattr(widget, 'main_layout')
        assert widget.main_layout is not None

    def test_explorer_layout_exists(self):
        """Test that explorer layout can be created."""
        explorer = ResultsExplorer()

        # Display should create layout
        # (We can't actually test display without Jupyter)
        assert explorer.output is not None

    def test_builder_layout_exists(self):
        """Test that builder layout can be created."""
        builder = AnimationBuilder()

        # Should have output widget
        assert builder.output is not None


class TestWidgetValidation:
    """Test widget input validation."""

    def test_widget_value_ranges(self):
        """Test widget value ranges are valid."""
        widget = SimulationWidget()

        # Test slider ranges
        assert widget.num_stars_slider.min >= 10_000
        assert widget.num_stars_slider.max <= 500_000
        assert widget.duration_slider.min >= 1.0
        assert widget.duration_slider.max <= 20.0
        assert widget.num_realizations_slider.min >= 1
        assert widget.num_realizations_slider.max <= 1000

    def test_preset_options_valid(self):
        """Test that all preset options are valid."""
        widget = SimulationWidget()

        valid_presets = ['moderate', 'optimistic', 'early_filter', 'late_filter', 'rare_earth']

        # All options should be valid
        for option in widget.preset_selector.options:
            assert option in valid_presets

    def test_kardashev_filter_ranges(self):
        """Test Kardashev filter ranges."""
        explorer = ResultsExplorer()

        assert explorer.kardashev_min.min == 0.0
        assert explorer.kardashev_min.max == 3.0
        assert explorer.kardashev_max.min == 0.0
        assert explorer.kardashev_max.max == 3.0

    def test_fps_slider_range(self):
        """Test FPS slider has reasonable range."""
        builder = AnimationBuilder()

        assert builder.fps_slider.min >= 10
        assert builder.fps_slider.max <= 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
