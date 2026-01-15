"""Spatial indexing for disaster events.

Provides O(k*m) spatial queries using 3D voxel grid.
"""

import numpy as np
from collections import defaultdict
from typing import List, Tuple

from .encoding import DisasterBinary


class DisasterSpatialIndex:
    """3D voxel index for efficient disaster lookup."""

    def __init__(self, kpc_range: float = 20.0, resolution: int = 30):
        """Initialize spatial index.

        Args:
            kpc_range: Half-width of indexed region
            resolution: Voxels per axis (30^3 = 27K default)
        """
        self.voxels = defaultdict(list)
        self.resolution = resolution
        self.kpc_range = kpc_range
        self.voxel_size = 2.0 * kpc_range / resolution
        self.disasters = []
        self.disaster_times = []

    def _position_to_voxel(
        self, position: np.ndarray
    ) -> Tuple[int, int, int]:
        """Convert kpc position to voxel indices.

        Args:
            position: (3,) position in kpc

        Returns:
            (ix, iy, iz) voxel indices
        """
        pos_clamped = np.clip(
            position + self.kpc_range, 0, 2 * self.kpc_range
        )
        normalized = pos_clamped / (2 * self.kpc_range)
        indices = (normalized * self.resolution).astype(int)
        return tuple(indices)

    def add_disaster(self, disaster: DisasterBinary) -> int:
        """Add disaster to index.

        Args:
            disaster: DisasterBinary to add

        Returns:
            Disaster ID (index in disasters list)
        """
        disaster_id = len(self.disasters)
        self.disasters.append(disaster)
        self.disaster_times.append(disaster.time_myr)
        voxel = self._position_to_voxel(disaster.position)
        self.voxels[voxel].append(disaster_id)
        return disaster_id

    def query_spatial(
        self, center: np.ndarray, radius_kpc: float
    ) -> List[DisasterBinary]:
        """Query disasters within radius of center.

        Complexity: O(k * m) where k = touched voxels, m = disasters/voxel

        Args:
            center: (3,) query center in kpc
            radius_kpc: Search radius

        Returns:
            List of disasters within radius
        """
        results = []
        voxels_to_check = int(np.ceil(radius_kpc / self.voxel_size))
        center_voxel = self._position_to_voxel(center)

        for dx in range(-voxels_to_check, voxels_to_check + 1):
            for dy in range(-voxels_to_check, voxels_to_check + 1):
                for dz in range(-voxels_to_check, voxels_to_check + 1):
                    voxel = (
                        center_voxel[0] + dx,
                        center_voxel[1] + dy,
                        center_voxel[2] + dz,
                    )
                    for disaster_id in self.voxels.get(voxel, []):
                        disaster = self.disasters[disaster_id]
                        dist = np.linalg.norm(disaster.position - center)
                        if dist <= radius_kpc:
                            results.append(disaster)
        return results

    def query_temporal(
        self, time_start: float, time_end: float
    ) -> List[DisasterBinary]:
        """Query disasters in time window.

        Uses binary search on sorted times.

        Args:
            time_start: Window start (Myr)
            time_end: Window end (Myr)

        Returns:
            List of disasters in window
        """
        idx_start = np.searchsorted(
            self.disaster_times, time_start, side="left"
        )
        idx_end = np.searchsorted(
            self.disaster_times, time_end, side="right"
        )
        return self.disasters[idx_start:idx_end]

    def query_spatiotemporal(
        self,
        center: np.ndarray,
        radius_kpc: float,
        time_start: float,
        time_end: float,
    ) -> List[DisasterBinary]:
        """Combined spatial and temporal query.

        Args:
            center: (3,) query center in kpc
            radius_kpc: Search radius
            time_start: Window start (Myr)
            time_end: Window end (Myr)

        Returns:
            List of disasters matching both criteria
        """
        results = []
        voxels_to_check = int(np.ceil(radius_kpc / self.voxel_size))
        center_voxel = self._position_to_voxel(center)

        for dx in range(-voxels_to_check, voxels_to_check + 1):
            for dy in range(-voxels_to_check, voxels_to_check + 1):
                for dz in range(-voxels_to_check, voxels_to_check + 1):
                    voxel = (
                        center_voxel[0] + dx,
                        center_voxel[1] + dy,
                        center_voxel[2] + dz,
                    )
                    for disaster_id in self.voxels.get(voxel, []):
                        disaster = self.disasters[disaster_id]
                        if time_start <= disaster.time_myr <= time_end:
                            dist = np.linalg.norm(
                                disaster.position - center
                            )
                            if dist <= radius_kpc:
                                results.append(disaster)
        return results

    def clear(self):
        """Clear all stored disasters."""
        self.voxels.clear()
        self.disasters.clear()
        self.disaster_times.clear()
