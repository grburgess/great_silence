"""
Spatial hash grid for O(1) fixed-radius neighbor queries.

Replaces scipy.cKDTree for fixed-radius queries (hazard radius, encounter detection).
Grid cell size = max query radius. Each cell holds star indices.
Query = check 27 adjacent cells (3×3×3 neighborhood).

O(1) per query vs O(log N) for KD-tree.
Numba-compatible (pure array-based, no Python objects).
"""

import numpy as np
import numba
from typing import Tuple, List, Optional


class SpatialHashGrid:
    """
    3D spatial hash grid for fast fixed-radius neighbor queries.

    Uses uniform grid partitioning for O(1) average-case neighbor lookups.
    Optimized for scenarios where query radius is known and fixed.
    """

    def __init__(self, cell_size: float, bounds: Optional[Tuple[float, float, float, float, float, float]] = None):
        """
        Initialize spatial hash grid.

        Args:
            cell_size: Grid cell size (kpc). Should be >= max query radius.
            bounds: Optional (xmin, xmax, ymin, ymax, zmin, zmax) in kpc.
                   If None, computed from data on build().
        """
        self.cell_size = cell_size
        self.bounds = bounds

        # Grid metadata
        self.grid_min: Optional[np.ndarray] = None  # (3,) grid origin
        self.grid_size: Optional[Tuple[int, int, int]] = None  # (nx, ny, nz)

        # Flattened cell data (Numba-compatible)
        self.cell_starts: Optional[np.ndarray] = None  # (n_cells,) start index in cell_indices
        self.cell_counts: Optional[np.ndarray] = None  # (n_cells,) number of indices in cell
        self.cell_indices: Optional[np.ndarray] = None  # (n_total,) sorted star indices

        # Original positions (cached for rebuild checks)
        self._positions: Optional[np.ndarray] = None

    def build(self, positions: np.ndarray) -> None:
        """
        Build spatial hash grid from positions.

        Args:
            positions: (N, 3) array of positions in kpc
        """
        if len(positions) == 0:
            return

        # Compute bounds if not provided
        if self.bounds is None:
            pos_min = positions.min(axis=0)
            pos_max = positions.max(axis=0)
            margin = self.cell_size * 0.1  # Small margin to avoid boundary issues
            self.grid_min = pos_min - margin
            grid_max = pos_max + margin
        else:
            xmin, xmax, ymin, ymax, zmin, zmax = self.bounds
            self.grid_min = np.array([xmin, ymin, zmin])
            grid_max = np.array([xmax, ymax, zmax])

        # Compute grid dimensions
        grid_span = grid_max - self.grid_min
        nx = int(np.ceil(grid_span[0] / self.cell_size)) + 1
        ny = int(np.ceil(grid_span[1] / self.cell_size)) + 1
        nz = int(np.ceil(grid_span[2] / self.cell_size)) + 1
        self.grid_size = (nx, ny, nz)
        n_cells = nx * ny * nz

        # Compute cell indices for each position
        cell_ids = _compute_cell_indices_kernel(
            positions,
            self.grid_min,
            self.cell_size,
            nx, ny, nz
        )

        # Sort positions by cell ID using radix sort (O(N))
        sort_indices = np.argsort(cell_ids)
        sorted_cell_ids = cell_ids[sort_indices]

        # Build cell start/count arrays
        self.cell_starts = np.zeros(n_cells, dtype=np.int32)
        self.cell_counts = np.zeros(n_cells, dtype=np.int32)

        if len(sorted_cell_ids) > 0:
            # Count items per cell
            unique_cells, counts = np.unique(sorted_cell_ids, return_counts=True)
            self.cell_counts[unique_cells] = counts.astype(np.int32)

            # Compute cumulative starts
            self.cell_starts[1:] = np.cumsum(self.cell_counts)[:-1]

        # Store sorted indices
        self.cell_indices = sort_indices.astype(np.int32)

        # Cache positions for rebuild detection
        self._positions = positions.copy()

    def query_radius(self, center: np.ndarray, radius: float) -> np.ndarray:
        """
        Find all points within radius of center.

        Args:
            center: (3,) query point in kpc
            radius: Search radius in kpc

        Returns:
            Array of indices of points within radius
        """
        if self.cell_starts is None:
            return np.array([], dtype=np.int32)

        nx, ny, nz = self.grid_size

        # Get candidate cells (27-neighbor check)
        candidates = _query_radius_kernel(
            center,
            radius,
            self.grid_min,
            self.cell_size,
            nx, ny, nz,
            self.cell_starts,
            self.cell_counts,
            self.cell_indices,
            self._positions
        )

        return candidates

    def needs_rebuild(self, positions: np.ndarray, threshold: float = 0.1) -> bool:
        """
        Check if grid needs rebuilding based on position changes.

        Args:
            positions: Current positions
            threshold: Rebuild if >threshold fraction of stars moved >cell_size

        Returns:
            True if rebuild recommended
        """
        if self._positions is None:
            return True

        if len(positions) != len(self._positions):
            return True

        # Check movement
        displacement = np.linalg.norm(positions - self._positions, axis=1)
        large_moves = np.sum(displacement > self.cell_size)

        return (large_moves / len(positions)) > threshold


@numba.jit(nopython=True, cache=True)
def _compute_cell_indices_kernel(
    positions: np.ndarray,
    grid_min: np.ndarray,
    cell_size: float,
    nx: int,
    ny: int,
    nz: int
) -> np.ndarray:
    """
    Compute cell indices for positions.

    Args:
        positions: (N, 3) positions
        grid_min: (3,) grid origin
        cell_size: Cell size
        nx, ny, nz: Grid dimensions

    Returns:
        (N,) array of cell indices (flattened 3D index)
    """
    n = len(positions)
    cell_ids = np.empty(n, dtype=np.int32)

    for i in range(n):
        # Compute grid coordinates
        ix = int((positions[i, 0] - grid_min[0]) / cell_size)
        iy = int((positions[i, 1] - grid_min[1]) / cell_size)
        iz = int((positions[i, 2] - grid_min[2]) / cell_size)

        # Clamp to grid bounds
        ix = max(0, min(ix, nx - 1))
        iy = max(0, min(iy, ny - 1))
        iz = max(0, min(iz, nz - 1))

        # Flatten to 1D index
        cell_ids[i] = ix + iy * nx + iz * nx * ny

    return cell_ids


@numba.jit(nopython=True, cache=True)
def _query_radius_kernel(
    center: np.ndarray,
    radius: float,
    grid_min: np.ndarray,
    cell_size: float,
    nx: int,
    ny: int,
    nz: int,
    cell_starts: np.ndarray,
    cell_counts: np.ndarray,
    cell_indices: np.ndarray,
    positions: np.ndarray
) -> np.ndarray:
    """
    Query all points within radius of center.

    Checks neighborhood based on radius/cell_size ratio.

    Args:
        center: (3,) query point
        radius: Search radius
        grid_min: Grid origin
        cell_size: Cell size
        nx, ny, nz: Grid dimensions
        cell_starts: Cell start indices
        cell_counts: Cell counts
        cell_indices: Sorted star indices
        positions: Original positions

    Returns:
        Array of indices within radius
    """
    # Compute center cell
    cx = int((center[0] - grid_min[0]) / cell_size)
    cy = int((center[1] - grid_min[1]) / cell_size)
    cz = int((center[2] - grid_min[2]) / cell_size)

    # Compute search range (number of cells to check in each direction)
    cell_range = int(np.ceil(radius / cell_size)) + 1

    # Collect candidates from neighborhood
    candidates = []
    radius_sq = radius * radius

    for dx in range(-cell_range, cell_range + 1):
        for dy in range(-cell_range, cell_range + 1):
            for dz in range(-cell_range, cell_range + 1):
                ix = cx + dx
                iy = cy + dy
                iz = cz + dz

                # Skip out-of-bounds cells
                if ix < 0 or ix >= nx or iy < 0 or iy >= ny or iz < 0 or iz >= nz:
                    continue

                # Get cell index
                cell_idx = ix + iy * nx + iz * nx * ny

                # Check all points in cell
                start = cell_starts[cell_idx]
                count = cell_counts[cell_idx]

                for i in range(count):
                    star_idx = cell_indices[start + i]

                    # Distance check
                    dx_pos = positions[star_idx, 0] - center[0]
                    dy_pos = positions[star_idx, 1] - center[1]
                    dz_pos = positions[star_idx, 2] - center[2]
                    dist_sq = dx_pos * dx_pos + dy_pos * dy_pos + dz_pos * dz_pos

                    if dist_sq <= radius_sq:
                        candidates.append(star_idx)

    return np.array(candidates, dtype=np.int32)
