"""Basic sanity tests for GalaticBot."""

import numpy as np
import pytest

from great_silence import SimulationConfig, GalaxySimulation
from great_silence.galaxy import GalaxyModel, InitialMassFunction, StarFormationHistory
from great_silence.simulation import LightTravelCalculator


class TestConfiguration:
    """Test configuration management."""

    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = SimulationConfig()
        assert config.galaxy.total_stars > 0
        assert config.simulation.simulation_duration_gyr > 0

    def test_config_to_dict(self):
        """Test configuration serialization to dictionary."""
        config = SimulationConfig()
        config_dict = config.to_dict()
        assert 'galaxy' in config_dict
        assert 'simulation' in config_dict
        assert 'civilization' in config_dict
        assert 'astrophysics' in config_dict


class TestGalaxy:
    """Test galaxy generation."""

    def test_galaxy_initialization(self):
        """Test galaxy model initialization."""
        from great_silence.config.parameters import GalaxyParameters
        params = GalaxyParameters(total_stars=1000)
        galaxy = GalaxyModel(params, seed=42)
        assert galaxy.positions is None  # Not generated yet

    def test_stellar_population_generation(self):
        """Test generating stellar population."""
        from great_silence.config.parameters import GalaxyParameters
        params = GalaxyParameters(total_stars=1000)
        galaxy = GalaxyModel(params, seed=42)
        galaxy.generate_stellar_population()

        assert galaxy.positions is not None
        assert len(galaxy.positions) == 1000
        assert galaxy.positions.shape == (1000, 3)
        assert galaxy.velocities is not None
        assert len(galaxy.velocities) == 1000

    def test_imf_sampling(self):
        """Test IMF mass sampling."""
        imf = InitialMassFunction("kroupa")
        masses = imf.sample(1000, seed=42)

        assert len(masses) == 1000
        assert np.all(masses >= 0.08)  # Above hydrogen burning limit
        assert np.all(masses <= 100.0)  # Below upper limit

    def test_star_formation_history(self):
        """Test star formation history."""
        from great_silence.config.parameters import AstrophysicsParameters
        params = AstrophysicsParameters()
        sfh = StarFormationHistory(params)

        # SFR should be positive
        assert sfh.sfr(1.0) > 0
        assert sfh.sfr(10.0) > 0

        # SFR at negative time should be zero
        assert sfh.sfr(-1.0) == 0


class TestPhysics:
    """Test physics calculations."""

    def test_light_travel_time(self):
        """Test light travel time calculation."""
        # 1 parsec should take ~3.26 years
        time = LightTravelCalculator.light_travel_time(1.0)
        assert 3.0 < time < 4.0

    def test_relativistic_time_dilation(self):
        """Test time dilation calculation."""
        # At 0.5c, gamma should be ~1.15
        gamma = LightTravelCalculator.relativistic_time_dilation(0.5)
        assert 1.1 < gamma < 1.2

        # At rest, gamma = 1
        gamma = LightTravelCalculator.relativistic_time_dilation(0.0)
        assert gamma == pytest.approx(1.0)


class TestSimulation:
    """Test simulation engine."""

    def test_simulation_creation(self):
        """Test creating simulation instance."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100  # Small for testing
        sim = GalaxySimulation(config, seed=42)
        assert sim.current_time_myr == 0.0

    def test_simulation_initialization(self):
        """Test simulation initialization."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        sim = GalaxySimulation(config, seed=42)
        sim.initialize()

        assert sim.galaxy.positions is not None
        assert len(sim.galaxy.positions) == 100
        assert sim.habitable_star_indices is not None

    def test_simulation_short_run(self):
        """Test running simulation for short duration."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01  # 10 Myr
        config.simulation.time_step_myr = 1.0
        config.simulation.save_snapshots = False

        sim = GalaxySimulation(config, seed=42)
        sim.run(verbose=False)

        stats = sim.get_statistics()
        assert stats['current_time_gyr'] >= 0.01
        assert stats['total_civilizations'] >= 0  # May or may not emerge


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
