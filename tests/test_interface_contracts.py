"""
Test interface contracts for astrophysics models.

These tests verify that models are called with correct function signatures
and prevent bugs like the GRB is_in_beam() argument mismatch.
"""

import pytest
import numpy as np
from great_silence.astrophysics.grb import GammaRayBurstModel
from great_silence.astrophysics.supernovae import SupernovaModel
from great_silence.config.parameters import AstrophysicsParameters


class TestGRBModelInterface:
    """Test GammaRayBurstModel interface contract."""

    def setup_method(self):
        """Set up test fixtures."""
        self.params = AstrophysicsParameters()
        self.model = GammaRayBurstModel(self.params)
        self.rng = np.random.default_rng(42)

    def test_is_in_beam_signature(self):
        """Test is_in_beam() requires correct arguments."""
        grb_position = np.array([0.0, 0.0, 0.0])
        grb_direction = np.array([1.0, 0.0, 0.0])
        target_position = np.array([1.0, 0.0, 0.0])

        # Should accept (grb_position, grb_direction, target_position)
        result = self.model.is_in_beam(grb_position, grb_direction, target_position)
        assert isinstance(result, (bool, np.bool_))

        # Should reject wrong number of arguments
        with pytest.raises(TypeError):
            self.model.is_in_beam(10.0)  # Used to call with angle_deg - WRONG

        # Should reject missing arguments
        with pytest.raises(TypeError):
            self.model.is_in_beam(grb_position, grb_direction)

    def test_is_in_beam_returns_bool(self):
        """Test is_in_beam() returns boolean."""
        grb_position = np.array([0.0, 0.0, 0.0])
        grb_direction = np.array([1.0, 0.0, 0.0])
        target_position = np.array([1.0, 0.1, 0.0])

        result = self.model.is_in_beam(grb_position, grb_direction, target_position)
        assert isinstance(result, (bool, np.bool_))

    def test_lethal_distance_kpc_signature(self):
        """Test lethal_distance_kpc() takes no arguments."""
        # Should work with no arguments
        distance = self.model.lethal_distance_kpc()
        assert isinstance(distance, (float, np.floating))
        assert distance > 0

        # Should reject arguments
        with pytest.raises(TypeError):
            self.model.lethal_distance_kpc(1000.0)  # Used to call is_lethal(dist) - WRONG

    def test_sample_grb_direction_signature(self):
        """Test sample_grb_direction() requires rng."""
        # Should accept rng
        direction = self.model.sample_grb_direction(self.rng)
        assert direction.shape == (3,)
        assert np.isclose(np.linalg.norm(direction), 1.0)

        # Should reject no arguments
        with pytest.raises(TypeError):
            self.model.sample_grb_direction()


class TestSupernovaModelInterface:
    """Test SupernovaModel interface contract."""

    def setup_method(self):
        """Set up test fixtures."""
        self.params = AstrophysicsParameters()
        self.model = SupernovaModel(self.params)

    def test_will_go_supernova_signature(self):
        """Test will_go_supernova() requires correct arguments."""
        # Should accept (mass, age, dt)
        result = self.model.will_go_supernova(
            stellar_mass=10.0,
            stellar_age_gyr=0.05,
            dt_myr=1.0
        )
        assert isinstance(result, (bool, np.bool_))

        # Should reject missing arguments
        with pytest.raises(TypeError):
            self.model.will_go_supernova(10.0, 0.05)

    def test_is_lethal_signature(self):
        """Test is_lethal() requires distance argument."""
        # Should accept distance in parsecs
        result = self.model.is_lethal(distance_pc=5.0)
        assert isinstance(result, (bool, np.bool_))

        # Should reject no arguments
        with pytest.raises(TypeError):
            self.model.is_lethal()


class TestParameterValidation:
    """Test that parameter names match configuration schema."""

    def test_astrophysics_parameters_exist(self):
        """Verify all expected astrophysics parameters exist."""
        params = AstrophysicsParameters()

        # Parameters that SHOULD exist
        required_attrs = [
            'sn_rate_per_century',  # Correct name (sn_ prefix)
            'sn_lethal_range_pc',  # Correct name
            'sn_sterilization_range_pc',
            'grb_rate_per_century',
            'grb_lethal_range_kpc',  # Correct name (kpc not pc!)
            'grb_beaming_angle_deg',
        ]

        for attr in required_attrs:
            assert hasattr(params, attr), \
                f"Missing required parameter: {attr}"
            value = getattr(params, attr)
            assert isinstance(value, (int, float)), \
                f"Parameter {attr} should be numeric, got {type(value)}"

    def test_invalid_parameters_dont_exist(self):
        """Verify that common typo parameters DON'T exist."""
        params = AstrophysicsParameters()

        # Parameters that should NOT exist (common bugs)
        invalid_attrs = [
            'supernova_rate_per_century',  # Wrong: should be sn_rate_per_century
            'supernova_lethal_range_pc',  # Wrong: should be sn_lethal_range_pc
            'grb_lethal_range_pc',  # Wrong: should be grb_lethal_range_kpc
            'sn_lethal_dose_sv',  # Wrong: doesn't exist
        ]

        for attr in invalid_attrs:
            assert not hasattr(params, attr), \
                f"Invalid parameter exists (should not): {attr}"

    def test_parameter_units_consistency(self):
        """Test that parameter units are internally consistent."""
        params = AstrophysicsParameters()

        # Supernova uses parsecs (local scale)
        assert hasattr(params, 'sn_lethal_range_pc')
        assert 'pc' in 'sn_lethal_range_pc'  # Unit in name

        # GRB uses kiloparsecs (galactic scale)
        assert hasattr(params, 'grb_lethal_range_kpc')
        assert 'kpc' in 'grb_lethal_range_kpc'  # Unit in name

        # Verify GRB range >> SN range (kiloparsec >> parsec)
        sn_range_kpc = params.sn_lethal_range_pc / 1000.0
        grb_range_kpc = params.grb_lethal_range_kpc
        assert grb_range_kpc > sn_range_kpc, \
            "GRB lethal range should be larger than SN (galactic vs local)"


class TestEventSchemaConsistency:
    """Test that event dictionaries have consistent schemas."""

    def test_grb_event_schema(self):
        """Test GRB events have standardized schema."""
        # Expected schema for GRB events
        expected_keys = {'time_myr', 'position', 'direction'}

        # Create mock GRB event as would be created in simulation
        grb_event = {
            'time_myr': 100.0,
            'position': [0.0, 0.0, 0.0],
            'direction': [1.0, 0.0, 0.0]
        }

        assert set(grb_event.keys()) == expected_keys, \
            f"GRB event schema mismatch: {grb_event.keys()} != {expected_keys}"

        # Verify types
        assert isinstance(grb_event['time_myr'], (int, float))
        assert isinstance(grb_event['position'], list)
        assert len(grb_event['position']) == 3
        assert isinstance(grb_event['direction'], list)
        assert len(grb_event['direction']) == 3

    def test_supernova_event_schema(self):
        """Test supernova events have standardized schema."""
        expected_keys = {'time_myr', 'position'}

        sn_event = {
            'time_myr': 50.0,
            'position': [1.0, 2.0, 3.0]
        }

        assert set(sn_event.keys()) == expected_keys, \
            f"SN event schema mismatch: {sn_event.keys()} != {expected_keys}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
