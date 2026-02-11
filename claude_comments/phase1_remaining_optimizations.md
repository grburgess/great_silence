# Phase 1 Remaining Optimizations (1.7-1.10)

## Implementation Notes for Future Work

### 1.7 - Sector-Based Civilization Partitioning [2-8x encounter detection]

**Concept**: Divide galaxy into R-phi grid sectors (e.g., 8×8 = 64 sectors)

**Implementation**:
```python
def assign_civ_to_sector(civ_position, num_sectors_r=8, num_sectors_phi=8):
    """Assign civilization to galactic sector."""
    r = np.sqrt(civ_position[0]**2 + civ_position[1]**2)
    phi = np.arctan2(civ_position[1], civ_position[0])

    # Radial bins (log-spaced for better distribution)
    r_max = 15.0  # kpc
    sector_r = int(np.log(r + 1) / np.log(r_max + 1) * num_sectors_r)
    sector_phi = int((phi + np.pi) / (2 * np.pi) * num_sectors_phi)

    return sector_r * num_sectors_phi + sector_phi

# Add to CivilizationState:
# sector_id: int = 0

# In _scan_for_encounters():
# Only check civs in same sector + adjacent sectors (9 total)
# Reduces O(N²) to O(N²/64) = 8x speedup for 64 sectors
```

**Integration points**:
- `CivilizationState`: Add `sector_id` field
- `_scan_for_encounters()`: Filter by sector before overlap check
- Update sector on colony expansion

---

### 1.8 - Incremental Colony Overlap Detection

**Concept**: Maintain persistent `_star_to_civs` dict, update incrementally

**Current (inefficient)**:
```python
# Rebuilds O(C×S) every timestep
def find_territory_overlaps():
    star_to_civs = {}
    for civ in civilizations:
        for star in civ.colonized_stars:
            star_to_civs[star].append(civ.civ_id)
```

**Optimized (incremental)**:
```python
class GalaxySimulation:
    def __init__(self):
        self._star_to_civs: Dict[int, Set[int]] = {}  # star_idx -> {civ_ids}

    def _add_colony(self, civ_id: int, star_idx: int):
        """Add colony and update incremental index."""
        if star_idx not in self._star_to_civs:
            self._star_to_civs[star_idx] = set()
        self._star_to_civs[star_idx].add(civ_id)

        # Check for immediate overlap
        if len(self._star_to_civs[star_idx]) > 1:
            self._handle_territory_dispute(star_idx)

    def _remove_colony(self, civ_id: int, star_idx: int):
        """Remove colony and update incremental index."""
        if star_idx in self._star_to_civs:
            self._star_to_civs[star_idx].discard(civ_id)
            if len(self._star_to_civs[star_idx]) == 0:
                del self._star_to_civs[star_idx]
```

**Integration points**:
- `_handle_probe_arrival()`: Call `_add_colony()`
- `_resolve_battle_at_star()`: Call `_remove_colony()` for loser
- `_apply_hazards()`: Call `_remove_colony()` for destroyed

**Benefit**: O(new_colonies_this_step) instead of O(total_colonies_all_civs)

---

### 1.9 - Adaptive Snapshot Interval

**Concept**: More snapshots during active periods, fewer during quiet

**Implementation**:
```python
def _should_save_snapshot(self, current_time_myr: float) -> bool:
    """Adaptive snapshot interval based on activity."""
    if self._last_snapshot_time_myr is None:
        return True

    time_since_last = current_time_myr - self._last_snapshot_time_myr

    # Determine activity level
    active_wars = len([w for w in self.wars if w.is_active])
    recent_encounters = len([e for e in self.encounter_events
                            if current_time_myr - e.time_myr < 50.0])

    # Adaptive interval
    if active_wars > 0 or recent_encounters > 0:
        interval = 50.0  # Myr (active period)
    elif self._active_civ_count > 0:
        interval = 100.0  # Myr (normal)
    else:
        interval = 200.0  # Myr (quiet)

    return time_since_last >= interval

# In main loop:
if self._should_save_snapshot(self.current_time_myr):
    self._save_snapshot()
```

**Integration points**:
- `run()` main loop: Replace fixed interval check
- Add `_last_snapshot_time_myr` tracking

**Benefit**: 100 snapshots → 40-60 snapshots for 10 Gyr = 40-60% reduction

---

### 1.10 - MLX for Gravitational Acceleration [5-20x, OPTIONAL]

**Status**: EXPERIMENTAL - Requires MLX library (Apple Silicon only)

**Concept**: Use Apple's MLX array framework for GPU acceleration

**Installation**:
```bash
pip install mlx
```

**Implementation**:
```python
try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False

def compute_acceleration_mlx(positions_mx):
    """Compute acceleration using MLX on Apple Silicon GPU."""
    # Convert to MLX arrays (unified memory, no copy)
    pos_mx = mx.array(positions)

    # Compute on GPU via Metal
    # ... MLX operations (NumPy-like API)

    # Convert back
    return np.array(accel_mx)
```

**Considerations**:
- MLX is lazy evaluation (like JAX)
- Best for large arrays (100k+ stars)
- Overhead for small arrays (<10k)
- Need to benchmark vs Numba
- Only Apple Silicon (M1/M2/M3)

**References**:
- MLX GitHub: https://github.com/ml-explore/mlx
- MLX for scientific computing: https://vincent.codes.finance/posts/apple-mlx/
- WWDC25 MLX session: https://developer.apple.com/videos/play/wwdc2025/315/

---

## Summary

**Items 1.7-1.9**: Ready for implementation, need integration into engine.py
**Item 1.10**: Experimental, needs benchmarking, optional

**Total Phase 1 cumulative speedup potential**:
- Items 1.1-1.6 implemented: ~5-15x cumulative
- Items 1.7-1.9 additional: ~3-5x additional
- Item 1.10 (if beneficial): ~5-20x additional

**Next step**: Integrate 1.7-1.9 into engine.py or proceed to Phase 2 (war mechanics)
