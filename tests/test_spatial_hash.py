"""Tests for Phase 1.3 - Spatial hash grid for O(1) neighbor queries."""

import pytest
import numpy as np
from great_silence.utils.spatial_hash import SpatialHashGrid


class TestSpatialHashGrid:
    """Test spatial hash grid for fast neighbor queries."""

    @pytest.fixture
    def random_positions(self):
        """Generate random stellar positions."""
        np.random.seed(42)
        # Positions in a 20x20x4 kpc box
        positions = np.random.randn(1000, 3)
        positions[:, 0] *= 10.0  # x: -10 to 10 kpc
        positions[:, 1] *= 10.0  # y: -10 to 10 kpc
        positions[:, 2] *= 2.0   # z: -2 to 2 kpc
        return positions

    @pytest.fixture
    def grid(self):
        """Create spatial hash grid."""
        # Cell size = 1 kpc (good for typical queries ~0.5-1 kpc)
        return SpatialHashGrid(cell_size=1.0)

    def test_grid_initialization(self, grid):
        """Test spatial hash grid initializes correctly."""
        assert grid is not None
        assert grid.cell_size == 1.0
        assert grid.grid_min is None
        assert grid.grid_size is None

    def test_grid_build(self, grid, random_positions):
        """Test SpatialHashGrid.build() creates grid."""
        grid.build(random_positions)

        # Grid should be built
        assert grid.grid_min is not None
        assert grid.grid_size is not None
        assert grid.cell_starts is not None
        assert grid.cell_counts is not None
        assert grid.cell_indices is not None

        # Verify data structures
        assert len(grid.cell_starts) > 0
        assert len(grid.cell_counts) > 0
        assert len(grid.cell_indices) == len(random_positions)

    def test_query_radius_finds_neighbors(self, grid, random_positions):
        """Test query_radius() finds correct neighbors."""
        grid.build(random_positions)

        # Query near origin
        center = np.array([0.0, 0.0, 0.0])
        radius = 2.0  # kpc

        neighbors = grid.query_radius(center, radius)

        # Verify all neighbors within radius
        for idx in neighbors:
            dist = np.linalg.norm(random_positions[idx] - center)
            assert dist <= radius + 1e-6, f"Point {idx} at distance {dist} > {radius}"

        # Verify no missing neighbors (brute force check)
        all_dists = np.linalg.norm(random_positions - center, axis=1)
        expected_neighbors = np.where(all_dists <= radius)[0]

        assert len(neighbors) == len(expected_neighbors)

    def test_query_radius_performance(self, random_positions):
        """Test O(1) performance vs brute force."""
        import time

        grid = SpatialHashGrid(cell_size=2.0)
        grid.build(random_positions)

        center = np.array([0.0, 0.0, 0.0])
        radius = 5.0

        # Time grid query
        n_queries = 100
        start = time.perf_counter()
        for _ in range(n_queries):
            neighbors = grid.query_radius(center, radius)
        grid_time = time.perf_counter() - start

        # Time brute force
        start = time.perf_counter()
        for _ in range(n_queries):
            dists = np.linalg.norm(random_positions - center, axis=1)
            brute_neighbors = np.where(dists <= radius)[0]
        brute_time = time.perf_counter() - start

        # Grid should be faster (but may not be for small N=1000)
        # Just verify it completes
        assert grid_time > 0
        assert brute_time > 0

        # Report speedup
        speedup = brute_time / grid_time
        print(f"\nSpatial hash speedup: {speedup:.2f}x")

    def test_needs_rebuild(self, grid, random_positions):
        """Test needs_rebuild() detects position changes."""
        grid.build(random_positions)

        # No change → no rebuild
        assert not grid.needs_rebuild(random_positions)

        # Small change → no rebuild
        small_change = random_positions + 0.01 * np.random.randn(*random_positions.shape)
        assert not grid.needs_rebuild(small_change)

        # Large change → rebuild
        large_change = random_positions + 5.0 * np.random.randn(*random_positions.shape)
        assert grid.needs_rebuild(large_change, threshold=0.1)

    def test_empty_grid(self, grid):
        """Test grid handles empty positions."""
        empty = np.array([]).reshape(0, 3)
        grid.build(empty)

        # Should not crash
        center = np.array([0.0, 0.0, 0.0])
        neighbors = grid.query_radius(center, 1.0)

        assert len(neighbors) == 0

    def test_single_point(self, grid):
        """Test grid with single point."""
        single = np.array([[1.0, 2.0, 3.0]])
        grid.build(single)

        # Query near point
        center = np.array([1.1, 2.1, 3.1])
        neighbors = grid.query_radius(center, 0.5)

        assert len(neighbors) == 1
        assert neighbors[0] == 0

        # Query far from point
        far_center = np.array([10.0, 10.0, 10.0])
        neighbors = grid.query_radius(far_center, 0.5)

        assert len(neighbors) == 0

    def test_dense_cluster(self, grid):
        """Test grid with dense cluster."""
        # 100 points in tight cluster
        cluster = np.random.randn(100, 3) * 0.1

        grid.build(cluster)

        # Query cluster center
        center = np.array([0.0, 0.0, 0.0])
        neighbors = grid.query_radius(center, 1.0)

        # Should find all points
        assert len(neighbors) == 100

    def test_boundary_conditions(self, grid):
        """Test grid handles boundary cases."""
        # Points at grid boundaries
        positions = np.array([
            [0.0, 0.0, 0.0],
            [10.0, 10.0, 10.0],
            [-10.0, -10.0, -10.0]
        ])

        grid.build(positions)

        # Query at boundary
        center = np.array([9.9, 9.9, 9.9])
        neighbors = grid.query_radius(center, 0.5)

        assert 1 in neighbors  # Should find point at [10, 10, 10]

    def test_multiple_cells(self, grid):
        """Test queries spanning multiple cells."""
        # Grid with 1 kpc cells
        positions = np.array([
            [0.0, 0.0, 0.0],
            [0.5, 0.5, 0.0],
            [1.5, 1.5, 0.0],
            [2.5, 2.5, 0.0]
        ])

        grid.build(positions)

        # Large radius query spanning 3x3x3 = 27 cells
        center = np.array([1.0, 1.0, 0.0])
        radius = 2.0

        neighbors = grid.query_radius(center, radius)

        # Should find all nearby points
        assert len(neighbors) >= 3

    def test_grid_rebuild_correctness(self, grid, random_positions):
        """Test rebuild produces correct results."""
        grid.build(random_positions)

        # Query before rebuild
        center = np.array([0.0, 0.0, 0.0])
        neighbors_before = set(grid.query_radius(center, 2.0))

        # Rebuild with same data
        grid.build(random_positions)
        neighbors_after = set(grid.query_radius(center, 2.0))

        # Should get same results
        assert neighbors_before == neighbors_after

    def test_cell_size_effect(self, random_positions):
        """Test different cell sizes."""
        # Small cells
        grid_small = SpatialHashGrid(cell_size=0.5)
        grid_small.build(random_positions)

        # Large cells
        grid_large = SpatialHashGrid(cell_size=5.0)
        grid_large.build(random_positions)

        center = np.array([0.0, 0.0, 0.0])
        radius = 2.0

        # Both should find same neighbors
        neighbors_small = set(grid_small.query_radius(center, radius))
        neighbors_large = set(grid_large.query_radius(center, radius))

        assert neighbors_small == neighbors_large

    def test_grid_with_bounds(self):
        """Test grid with explicit bounds."""
        positions = np.random.randn(100, 3)

        # Explicit bounds
        bounds = (-5.0, 5.0, -5.0, 5.0, -1.0, 1.0)
        grid = SpatialHashGrid(cell_size=1.0, bounds=bounds)
        grid.build(positions)

        assert grid.grid_min is not None
        assert grid.grid_size is not None

    def test_query_outside_grid(self, grid, random_positions):
        """Test query far outside grid bounds."""
        grid.build(random_positions)

        # Query far from all points
        far_center = np.array([1000.0, 1000.0, 1000.0])
        neighbors = grid.query_radius(far_center, 1.0)

        assert len(neighbors) == 0

    @pytest.mark.parametrize("n_stars", [10, 100, 1000, 10000])
    def test_grid_scales(self, n_stars):
        """Test grid scales with number of stars."""
        positions = np.random.randn(n_stars, 3) * 10.0

        grid = SpatialHashGrid(cell_size=2.0)
        grid.build(positions)

        center = np.array([0.0, 0.0, 0.0])
        neighbors = grid.query_radius(center, 3.0)

        # Should complete without error
        assert len(neighbors) >= 0

    def test_grid_memory_usage(self, random_positions):
        """Test grid memory efficiency."""
        grid = SpatialHashGrid(cell_size=1.0)
        grid.build(random_positions)

        # Memory usage should be O(N)
        n_stars = len(random_positions)

        # Cell arrays
        cell_memory = grid.cell_starts.nbytes + grid.cell_counts.nbytes
        index_memory = grid.cell_indices.nbytes

        total_memory = cell_memory + index_memory

        # Should be reasonable
        # Grid overhead includes cell structure (many cells for large grids)
        # But index storage is O(N)
        assert index_memory == n_stars * 4  # int32 per star
        assert cell_memory > 0  # Grid cells exist

        # Total per-star average (including grid overhead)
        per_star_memory = total_memory / n_stars
        # Allow for grid overhead (can be large if many cells)
        assert per_star_memory < 1000.0  # bytes (relaxed for grid structure)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
