"""Tests for Phase 1.4 - Blosc2 snapshot compression."""

import pytest
import numpy as np
from great_silence.utils.snapshot_compression import (
    SnapshotCompressor,
    compress_positions,
    decompress_positions,
    BLOSC2_AVAILABLE
)


class TestSnapshotCompression:
    """Test Blosc2 compression for simulation snapshots."""

    @pytest.fixture
    def compressor(self):
        """Create snapshot compressor."""
        return SnapshotCompressor(codec='zstd', clevel=5, use_async=False)

    @pytest.fixture
    def stellar_positions(self):
        """Generate realistic stellar positions."""
        np.random.seed(42)
        # Milky Way-like distribution
        n_stars = 10000
        r = np.random.exponential(3.5, n_stars)  # Scale length 3.5 kpc
        theta = np.random.uniform(0, 2*np.pi, n_stars)
        z = np.random.laplace(0, 0.3, n_stars)  # Scale height 0.3 kpc

        x = r * np.cos(theta)
        y = r * np.sin(theta)

        return np.column_stack([x, y, z])

    def test_compress_array_round_trip(self, compressor, stellar_positions):
        """Test compress_array / decompress_array round-trip."""
        # Compress
        compressed = compressor.compress_array(stellar_positions)

        # Verify metadata
        assert 'data' in compressed
        assert 'shape' in compressed
        assert 'dtype' in compressed
        assert compressed['shape'] == stellar_positions.shape

        # Decompress
        decompressed = compressor.decompress_array(compressed)

        # Verify exact match (lossless)
        assert np.allclose(decompressed, stellar_positions)
        assert decompressed.shape == stellar_positions.shape
        assert decompressed.dtype == stellar_positions.dtype

    def test_compression_without_blosc2(self, stellar_positions):
        """Test compression fallback without blosc2."""
        if BLOSC2_AVAILABLE:
            pytest.skip("blosc2 is installed, cannot test fallback")

        compressor = SnapshotCompressor()
        compressed = compressor.compress_array(stellar_positions)

        # Should fall back to uncompressed
        assert compressed['compressed'] == False

        # Decompression should still work
        decompressed = compressor.decompress_array(compressed)
        assert np.allclose(decompressed, stellar_positions)

    def test_float16_conversion(self, compressor, stellar_positions):
        """Test float16 conversion for viz data."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        # Compress with float16
        compressed = compressor.compress_array(stellar_positions, use_float16=True)

        # Decompress
        decompressed = compressor.decompress_array(compressed)

        # Should be close but not exact (float16 precision)
        assert np.allclose(decompressed, stellar_positions, rtol=1e-3)

        # Original dtype should be restored
        assert decompressed.dtype == stellar_positions.dtype

    def test_compression_ratio(self, compressor, stellar_positions):
        """Test compression achieves good ratio."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        compressed = compressor.compress_array(stellar_positions)

        if 'compression_ratio' in compressed:
            ratio = compressed['compression_ratio']
            # Should achieve at least 2x compression on spatial data
            assert ratio >= 2.0, f"Compression ratio {ratio:.2f}x too low"

            print(f"\nCompression ratio: {ratio:.2f}x")

    def test_compress_snapshot_multiple_arrays(self, compressor):
        """Test compressing snapshot with multiple arrays."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        # Create mock snapshot
        snapshot = {
            'positions': np.random.randn(1000, 3),
            'velocities': np.random.randn(1000, 3),
            'ages': np.random.uniform(0, 13, 1000),
            'masses': np.random.uniform(0.1, 2.0, 1000)
        }

        # Compress
        compressed = compressor.compress_snapshot(snapshot, viz_only_keys=['positions'])

        # Verify all arrays compressed
        assert 'positions' in compressed
        assert 'velocities' in compressed
        assert 'ages' in compressed
        assert 'masses' in compressed

        # Verify compression stats
        if '_compression_stats' in compressed:
            stats = compressed['_compression_stats']
            assert 'compression_ratio' in stats
            assert 'size_reduction_pct' in stats

            print(f"\nSnapshot compression: {stats['compression_ratio']:.2f}x")
            print(f"Size reduction: {stats['size_reduction_pct']:.1f}%")

    def test_async_compression(self, stellar_positions):
        """Test async compression on background thread."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        compressor = SnapshotCompressor(use_async=True)

        snapshot = {'positions': stellar_positions}

        # Submit async job
        future = compressor.compress_snapshot_async(snapshot)

        if hasattr(future, 'result'):
            # Wait for completion
            compressed = future.result(timeout=5.0)

            assert 'positions' in compressed

            # Decompress to verify
            decompressed = compressor.decompress_snapshot(compressed)
            assert np.allclose(decompressed['positions'], stellar_positions)

        compressor.shutdown()

    def test_compression_deterministic(self, compressor, stellar_positions):
        """Test compression is deterministic."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        # Compress twice
        compressed1 = compressor.compress_array(stellar_positions)
        compressed2 = compressor.compress_array(stellar_positions)

        # Should produce same output
        assert compressed1['data'] == compressed2['data']

    def test_compression_different_dtypes(self, compressor):
        """Test compression with different dtypes."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        # Float32
        arr_f32 = np.random.randn(1000, 3).astype(np.float32)
        compressed_f32 = compressor.compress_array(arr_f32)
        decompressed_f32 = compressor.decompress_array(compressed_f32)
        assert decompressed_f32.dtype == np.float32
        assert np.allclose(decompressed_f32, arr_f32)

        # Float64
        arr_f64 = np.random.randn(1000, 3).astype(np.float64)
        compressed_f64 = compressor.compress_array(arr_f64)
        decompressed_f64 = compressor.decompress_array(compressed_f64)
        assert decompressed_f64.dtype == np.float64
        assert np.allclose(decompressed_f64, arr_f64)

    def test_compression_empty_array(self, compressor):
        """Test compression handles empty arrays."""
        empty = np.array([]).reshape(0, 3)

        compressed = compressor.compress_array(empty)
        decompressed = compressor.decompress_array(compressed)

        assert decompressed.shape == (0, 3)

    def test_compression_large_array(self, compressor):
        """Test compression with large array (100k stars)."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        large_positions = np.random.randn(100000, 3)

        compressed = compressor.compress_array(large_positions)
        decompressed = compressor.decompress_array(compressed)

        assert np.allclose(decompressed, large_positions)

        if 'compression_ratio' in compressed:
            print(f"\n100k stars compression: {compressed['compression_ratio']:.2f}x")

    def test_convenience_functions(self, stellar_positions):
        """Test compress_positions / decompress_positions convenience functions."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        # Compress
        compressed = compress_positions(stellar_positions)

        # Decompress
        decompressed = decompress_positions(compressed)

        assert np.allclose(decompressed, stellar_positions)

    def test_compression_stats(self, compressor, stellar_positions):
        """Test compression statistics."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        snapshot = {
            'positions': stellar_positions,
            'velocities': np.random.randn(*stellar_positions.shape)
        }

        compressed = compressor.compress_snapshot(snapshot)

        if '_compression_stats' in compressed:
            stats = compressed['_compression_stats']

            # Verify stats
            assert stats['total_original_bytes'] > 0
            assert stats['total_compressed_bytes'] > 0
            assert stats['compression_ratio'] > 1.0
            assert 0 < stats['size_reduction_pct'] < 100

    @pytest.mark.parametrize("codec", ['zstd', 'lz4', 'blosclz'])
    def test_different_codecs(self, codec, stellar_positions):
        """Test different compression codecs."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        compressor = SnapshotCompressor(codec=codec)

        compressed = compressor.compress_array(stellar_positions)
        decompressed = compressor.decompress_array(compressed)

        assert np.allclose(decompressed, stellar_positions)

    @pytest.mark.parametrize("clevel", [1, 5, 9])
    def test_compression_levels(self, clevel, stellar_positions):
        """Test different compression levels."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        compressor = SnapshotCompressor(clevel=clevel)

        compressed = compressor.compress_array(stellar_positions)
        decompressed = compressor.decompress_array(compressed)

        assert np.allclose(decompressed, stellar_positions)

        if 'compression_ratio' in compressed:
            print(f"\nclevel={clevel}: {compressed['compression_ratio']:.2f}x")

    def test_memory_efficiency(self, compressor, stellar_positions):
        """Test compression reduces memory usage."""
        if not BLOSC2_AVAILABLE:
            pytest.skip("blosc2 not available")

        # Original size
        original_size = stellar_positions.nbytes

        # Compressed size
        compressed = compressor.compress_array(stellar_positions)
        compressed_size = len(compressed['data'])

        # Should be smaller
        assert compressed_size < original_size

        reduction = (1 - compressed_size / original_size) * 100
        print(f"\nMemory reduction: {reduction:.1f}%")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
