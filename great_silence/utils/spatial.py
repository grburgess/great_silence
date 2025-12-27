"""Spatial indexing utilities for efficient nearest neighbor searches."""

import numpy as np
from scipy.spatial import cKDTree
from typing import Tuple, Optional


class SpatialIndex:
    """
    Spatial index for fast nearest neighbor queries in 3D.

    Uses KD-tree for efficient spatial queries.
    """

    def __init__(self, positions: np.ndarray):
        """
        Initialize spatial index.

        Args:
            positions: Array of shape (N, 3) with 3D positions
        """
        self.positions = positions
        self.tree = cKDTree(positions)

    def query_radius(
        self,
        center: np.ndarray,
        radius: float,
        return_distances: bool = False
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Find all points within radius of center.

        Args:
            center: Center position (3D)
            radius: Search radius
            return_distances: Whether to return distances

        Returns:
            Indices of points within radius, and optionally their distances
        """
        # query_ball_point returns only indices, not distances
        indices_list = self.tree.query_ball_point(center, radius)
        indices = np.array(indices_list)

        if return_distances:
            # Compute distances manually
            if len(indices) > 0:
                distances = np.linalg.norm(self.positions[indices] - center, axis=1)
            else:
                distances = np.array([])
            return indices, distances
        else:
            return indices, None

    def query_nearest(
        self,
        point: np.ndarray,
        k: int = 1
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find k nearest neighbors to a point.

        Args:
            point: Query point (3D)
            k: Number of neighbors

        Returns:
            Distances and indices of k nearest neighbors
        """
        distances, indices = self.tree.query(point, k=k)
        return distances, indices

    def query_pairs(self, max_distance: float) -> set:
        """
        Find all pairs of points within max_distance of each other.

        Args:
            max_distance: Maximum distance between pairs

        Returns:
            Set of (i, j) index pairs where i < j
        """
        pairs = self.tree.query_pairs(max_distance)
        return pairs
