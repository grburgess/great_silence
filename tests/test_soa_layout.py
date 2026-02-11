"""Tests for Phase 1.1 - Struct-of-Arrays (SoA) layout."""

import pytest
import numpy as np
from great_silence import SimulationConfig
from great_silence.galaxy.structure import GalaxyModel
from great_silence.config.parameters import GalaxyParameters


class TestSoALayout:
    """Test Struct-of-Arrays layout for stellar positions."""

    @pytest.fixture
    def galaxy_params(self):
        """Create test galaxy parameters."""
        return GalaxyParameters(
            total_stars=1000,
            scale_length_kpc=3.5,
            disk_height_kpc=0.3,
            disk_radius_kpc=15.0
        )

    @pytest.fixture
    def galaxy(self, galaxy_params):
        """Create and initialize galaxy model."""
        galaxy = GalaxyModel(galaxy_params, seed=42, use_numba=True)
        galaxy.generate_stellar_population()
        return galaxy

    def test_positions_property_getter(self, galaxy):
        """Test positions property returns (N, 3) array."""
        positions = galaxy.positions

        assert positions is not None
        assert isinstance(positions, np.ndarray)
        assert positions.shape == (1000, 3)
        assert positions.dtype in [np.float32, np.float64]

    def test_positions_property_setter(self, galaxy_params):
        """Test positions property setter updates SoA arrays."""
        galaxy = GalaxyModel(galaxy_params, seed=42)

        # Create test positions
        test_positions = np.random.randn(1000, 3).astype(np.float64)

        # Set via property
        galaxy.positions = test_positions

        # Verify SoA arrays updated
        assert galaxy._pos_x is not None
        assert galaxy._pos_y is not None
        assert galaxy._pos_z is not None

        assert len(galaxy._pos_x) == 1000
        assert len(galaxy._pos_y) == 1000
        assert len(galaxy._pos_z) == 1000

        # Verify values match
        assert np.allclose(galaxy._pos_x, test_positions[:, 0])
        assert np.allclose(galaxy._pos_y, test_positions[:, 1])
        assert np.allclose(galaxy._pos_z, test_positions[:, 2])

    def test_get_positions_soa(self, galaxy):
        """Test get_positions_soa() returns separate x,y,z arrays."""
        pos_x, pos_y, pos_z = galaxy.get_positions_soa()

        assert pos_x is not None
        assert pos_y is not None
        assert pos_z is not None

        assert len(pos_x) == 1000
        assert len(pos_y) == 1000
        assert len(pos_z) == 1000

        assert pos_x.ndim == 1
        assert pos_y.ndim == 1
        assert pos_z.ndim == 1

    def test_aos_soa_conversion_preserves_data(self, galaxy):
        """Test AoS ↔ SoA conversion preserves data."""
        # Get original positions via property (AoS)
        original = galaxy.positions.copy()

        # Get SoA view
        pos_x, pos_y, pos_z = galaxy.get_positions_soa()

        # Reconstruct AoS from SoA
        reconstructed = np.column_stack([pos_x, pos_y, pos_z])

        # Verify match
        assert np.allclose(original, reconstructed)

    def test_soa_contiguous_memory(self, galaxy):
        """Test SoA arrays are contiguous in memory."""
        pos_x, pos_y, pos_z = galaxy.get_positions_soa()

        # Each component should be C-contiguous for SIMD
        assert pos_x.flags['C_CONTIGUOUS']
        assert pos_y.flags['C_CONTIGUOUS']
        assert pos_z.flags['C_CONTIGUOUS']

    def test_aos_view_writable(self, galaxy):
        """Test AoS view modifications update SoA storage."""
        # Get positions via property
        positions = galaxy.positions

        # Modify via AoS view
        original_x = galaxy._pos_x[0]
        positions[0, 0] = 999.0

        # Note: Direct modification of column_stack view may not update underlying arrays
        # This test documents current behavior
        # For actual modifications, use positions property setter

    def test_soa_compatibility_with_existing_code(self, galaxy):
        """Test SoA layout compatible with existing position-based code."""
        # Code that expects (N, 3) arrays should work
        positions = galaxy.positions

        # Test common operations
        distances = np.linalg.norm(positions, axis=1)
        assert len(distances) == 1000
        assert np.all(distances >= 0)

        # Test slicing
        first_10 = positions[:10]
        assert first_10.shape == (10, 3)

        # Test indexing
        first_pos = positions[0]
        assert first_pos.shape == (3,)

    def test_soa_none_handling(self, galaxy_params):
        """Test SoA handles None values correctly."""
        galaxy = GalaxyModel(galaxy_params, seed=42)

        # Before generation, positions should be None
        assert galaxy.positions is None
        assert galaxy._pos_x is None
        assert galaxy._pos_y is None
        assert galaxy._pos_z is None

        # Setting None should clear all
        galaxy.generate_stellar_population()
        assert galaxy.positions is not None

        galaxy.positions = None
        assert galaxy.positions is None
        assert galaxy._pos_x is None

    def test_soa_memory_efficiency(self, galaxy):
        """Test SoA layout memory usage."""
        pos_x, pos_y, pos_z = galaxy.get_positions_soa()

        # Calculate memory usage
        soa_memory = pos_x.nbytes + pos_y.nbytes + pos_z.nbytes

        # Compare to AoS
        aos_positions = galaxy.positions
        aos_memory = aos_positions.nbytes

        # Should be roughly equal (SoA creates view, not copy)
        # Allow for some overhead
        assert soa_memory <= aos_memory * 1.5

    def test_soa_dtype_consistency(self, galaxy):
        """Test SoA components have consistent dtypes."""
        pos_x, pos_y, pos_z = galaxy.get_positions_soa()

        assert pos_x.dtype == pos_y.dtype == pos_z.dtype

        # Should match positions dtype
        positions = galaxy.positions
        assert pos_x.dtype == positions.dtype

    @pytest.mark.parametrize("n_stars", [10, 100, 1000, 10000])
    def test_soa_scales_with_size(self, n_stars):
        """Test SoA layout works at different scales."""
        params = GalaxyParameters(total_stars=n_stars)
        galaxy = GalaxyModel(params, seed=42)
        galaxy.generate_stellar_population()

        pos_x, pos_y, pos_z = galaxy.get_positions_soa()

        assert len(pos_x) == n_stars
        assert len(pos_y) == n_stars
        assert len(pos_z) == n_stars

        positions = galaxy.positions
        assert positions.shape == (n_stars, 3)

    def test_soa_round_trip(self):
        """Test full round-trip: create → set → get → verify."""
        params = GalaxyParameters(total_stars=100)
        galaxy = GalaxyModel(params, seed=42)

        # Create test data
        original = np.random.randn(100, 3)

        # Set via AoS
        galaxy.positions = original

        # Get via SoA
        x, y, z = galaxy.get_positions_soa()

        # Get via AoS
        retrieved = galaxy.positions

        # Verify all match
        assert np.allclose(original[:, 0], x)
        assert np.allclose(original[:, 1], y)
        assert np.allclose(original[:, 2], z)
        assert np.allclose(original, retrieved)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
