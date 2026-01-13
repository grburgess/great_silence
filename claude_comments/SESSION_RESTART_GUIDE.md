# CODE RESTORATION - SESSION RESTART GUIDE

**Created:** 2026-01-13
**Purpose:** Complete guide to resume code restoration work

---

## PROJECT CONTEXT

**Project:** The Great Silence - Monte Carlo simulation of galactic civilization emergence and evolution

**Lost Files (2026-01-13):**
- 5 Python modules: `great_silence/simulation/disasters/`
  - encoding.py, spatial_index.py, recovery.py, scheduler.py, archiver.py
- 4 Python modules + templates: `great_silence/visualization/threejs/`
  - config.py, data_extractor.py, html_exporter.py, templates/

**Recovery Sources:**
- Python 3.11/3.14 bytecode in `__pycache__/` directories
- GitHub issues #17-31 (feature descriptions)
- COMPREHENSIVE_RESTORATION_PLAN.md (detailed specs)
- BYTECODE_ANALYSIS.md (extracted function signatures)

---

## COMPLETED WORK (Phases 1-3)

### ✅ Phase 1: Core Disaster Infrastructure
**Commit:** a52f88c
**LOC:** ~600 lines (5 files)

**Files Implemented:**

1. **encoding.py** (24-byte binary disaster format)
   - DisasterBinary dataclass with packed binary layout
   - encode_disaster() - HazardEvent to 24-byte binary
   - decode_disaster() - Binary to DisasterBinary
   - encode_disaster_batch() / decode_disaster_batch()
   - Handles missing HazardEvent fields with hasattr()

2. **spatial_index.py** (O(k*m) voxel queries)
   - DisasterSpatialIndex with 3D voxel grid
   - add_disaster() - Add to spatial index
   - query_spatial() - Range query O(k*m)
   - query_temporal() - Binary search on sorted times
   - query_spatiotemporal() - Combined query
   - Uses defaultdict to avoid shared-list bug

3. **recovery.py** (O(log N) heap operations)
   - SterilizationStatus enum (HABITABLE, TEMPORARILY_STERILIZED, PERMANENTLY_STERILIZED)
   - RecoveryQueue with heapq-based priority queue
   - sterilize_star() - Mark star, schedule recovery
   - sterilize_batch() - Efficient batch processing
   - process_recoveries() - Process recovered stars
   - get_habitable_mask() / get_statistics()

4. **scheduler.py** (O(log N) supernova scheduling)
   - SupernovaScheduler with heap-based event scheduling
   - _build_schedule() - Pre-compute SN times for massive stars (>8 M_sun)
   - get_supernovae_in_window() - Query time window
   - add_new_star() - Add newly formed star
   - pending_count property

5. **archiver.py** (Three-tier HDF5 storage)
   - DisasterArchiver with tiered storage:
     - Tier 1: Recent events (in-memory HazardEvent)
     - Tier 2: Binary buffer (in-memory DisasterBinary)
     - Tier 3: HDF5 file (on-disk, compressed)
   - archive_disaster() - Archive with tiered storage
   - _flush_to_hdf5() - Flush buffer to disk
   - get_disasters_in_window() / get_all_disasters()
   - finalize() - Flush and close HDF5

### ✅ Phase 2: Three.js Data Layer
**Commit:** 84b5ceb
**LOC:** ~631 lines (3 files)

**Files Implemented:**

1. **config.py** (30+ configuration fields)
   - ThreeJSConfig dataclass with all visualization settings
   - Camera: position, fov, near, far
   - Controls: damping, zoom, auto-rotate
   - Appearance: background, star size/opacity
   - Civilizations: active/extinct size/opacity, Kardashev scale
   - Hazards: colors, marker size, opacity
   - Disaster viz: shockwave duration, sterilization opacity
   - Probe trails: length, glow
   - Trajectories: width, opacity, fade window
   - Animation: interpolation factor, frame duration, playback speed
   - Export: Three.js bundle, data embed threshold
   - to_dict() - JSON serialization

2. **data_extractor.py** (Largest file, ~35KB bytecode)
   - FrameData dataclass for animation frames
   - SimulationDataExtractor class
   - _load_source() - Load HDF5 or simulation object
   - extract_galaxy_data() - Subsample star positions
   - extract_civilization_data() - Get civs at time
   - extract_trajectory_data() - Get expansion trajectories
   - **extract_probe_data() - Probe interpolation (Issue #30)**
     - Finds bracketing snapshots
     - Linear interpolation between snapshots
     - Handles launched, arrived, and in-flight probes
     - Returns: positions, civ_ids, progress, probe_ids
   - **extract_hazard_data() - Hazard timing (Issue #25, #27)**
     - Returns: positions, types, times_gyr, time_since

3. **html_exporter.py** (HTML rendering)
   - ThreeJSRenderer class
   - _load_data() - Prepare data for rendering
   - render() - Generate HTML string
   - export() - Save to file with gzip support
   - export_html() - Convenience function
   - _BasicTemplate fallback when Jinja2 not available

### ✅ Phase 3: Three.js Templates
**Commit:** 1c15684
**LOC:** ~235 lines (2 files)

**Files Implemented:**

1. **layers.js.j2** (Disaster visualization)
   - createDisasterShockwaves() - Expanding ring geometry
   - updateShockwaves() - Animate shockwave expansion
     - Radius grows over time
     - Opacity fades over duration
     - Type-specific colors (SN, GRB, NSM)
   - getDisasterColor() - Map disaster type to color
   - createSterilizationZones() - Translucent sphere geometry
   - updateSterilizationZones() - Update sterilization zones
     - Fade opacity during recovery
     - Type-specific colors

2. **animation.js.j2** (Probe trails)
   - trailHistory buffer - probe_id -> [{x,y,z,alpha}, ...]
   - TRAIL_LENGTH = 3 (configurable)
   - createProbeTrails() - Initialize trail geometry
   - updateProbeTrails() - Update trail positions
   - updateTrailGeometry() - Rebuild line mesh
     - Update vertex positions
     - Set draw range based on history length
     - Fade opacity based on progress
     - Additive blending when probe_glow_enabled
   - updateAllProbeTrails() - Update all probes for frame
   - cleanupOldProbeTrails() - Remove trails for inactive probes

---

## PENDING WORK

### ⏭️ Phase 4: Engine Integration
**GitHub Issue:** #35
**Status:** PENDING

**File to Modify:** `great_silence/simulation/engine.py`

**Required Changes:**

1. **Initialize SupernovaScheduler in `initialize()`**
   ```python
   from .disasters import SupernovaScheduler
   self.supernova_scheduler = None
   # After galaxy initialization:
   self.supernova_scheduler = SupernovaScheduler(
       self.galaxy.masses,
       self.galaxy.metallicities,
       self.galaxy.ages_myr,
       self.stellar_evolution
   )
   ```

2. **Initialize RecoveryQueue in `initialize()`**
   ```python
   from .disasters import RecoveryQueue
   self.recovery_queue = None
   # After galaxy initialization:
   n_stars = self.config.galaxy.total_stars
   self.recovery_queue = RecoveryQueue(n_stars)
   ```

3. **Initialize DisasterArchiver in `initialize()`**
   ```python
   from .disasters import DisasterArchiver
   from pathlib import Path
   self.disaster_archiver = None
   # After galaxy initialization:
   if self.config.simulation.save_snapshots:
       archive_path = Path(self.config.simulation.output_dir) / "disasters.h5"
       self.disaster_archiver = DisasterArchiver(
           archive_path=archive_path,
           recent_window_myr=10.0,
           buffer_size=1000
       )
   ```

4. **Replace SN detection in `_detect_disasters_with_scheduler()`**
   ```python
   # Instead of checking massive stars every timestep:
   sn_indices = self.supernova_scheduler.get_supernovae_in_window(
       current_time_myr - dt_myr,
       current_time_myr
   )
   for star_idx in sn_indices:
       # Create supernova hazard
       hazard = self._create_supernova_hazard(star_idx, current_time_myr)
       self.active_hazards.append(hazard)
       # Archive disaster
       if self.disaster_archiver:
           self.disaster_archiver.archive_disaster(hazard, current_time_myr)
   ```

5. **Integrate RecoveryQueue in `_apply_hazards()`**
   ```python
   # For each hazard:
   affected_star_indices = self._find_affected_stars(hazard)
   for star_idx in affected_star_indices:
       recovery_time = hazard.sterilization_radius_pc / 10.0  # Example
       self.recovery_queue.sterilize_star(
           star_idx,
           current_time_myr,
           recovery_time,
           permanent=(hazard.energy > 1e52)  # Example threshold
       )

   # Process recoveries:
   recovered = self.recovery_queue.process_recoveries(current_time_myr)
   # Update habitable stars based on recovered indices
   ```

6. **Update ProgressMetrics for disaster stats**
   ```python
   # In progress tracking:
   if self.recovery_queue:
       stats = self.recovery_queue.get_statistics()
       self.progress.add_metric("habitable_stars", stats["habitable"])
       self.progress.add_metric("sterilized_stars", stats["temporarily_sterilized"] + stats["permanently_sterilized"])
   ```

---

## KNOWN BUGS (To Fix)

### 🐛 Bug #18: Energy Encoding Formula Error (CRITICAL)
**File:** `great_silence/simulation/disasters/encoding.py`
**Location:** Line ~84 in `encode_disaster()`

**Current Code:**
```python
energy_log10 = int(np.clip(
    np.log10(event.energy / 1e50) + 50, 0, 255
))
```

**This is actually CORRECT** - the bug mentioned in COMPREHENSIVE_RESTORATION_PLAN.md was based on incorrect bytecode interpretation. The formula `log10(energy/1e50) + 50` is correct.

**Action:** No fix needed, issue #18 can be closed.

---

### 🐛 Bug #19: RecoveryQueue Re-sterilization O(N) (MEDIUM)
**File:** `great_silence/simulation/disasters/recovery.py`
**Location:** Lines 53-60 in `sterilize_star()`

**Current Code:**
```python
if star_idx in self.in_queue:
    new_heap = [
        (rt, idx)
        for rt, idx in self.recovery_heap
        if idx != star_idx
    ]
    heapq.heapify(new_heap)
    self.recovery_heap = new_heap
```

**Problem:** Full heap rebuild is O(N), making re-sterilization expensive.

**Fix Options:**
1. **Lazy deletion** (recommended):
   ```python
   if star_idx in self.in_queue:
       self.stale_indices.add(star_idx)
   # In process_recoveries(), skip stale indices
   while self.recovery_heap and self.recovery_heap[0][0] <= current_time_myr:
       recovery_time, star_idx = heapq.heappop(self.recovery_heap)
       if star_idx in self.stale_indices:
           self.stale_indices.remove(star_idx)
           continue
       # ... process recovery
   ```

2. **Generation counters**:
   - Track heap version for each star
   - Skip entries with outdated versions

3. **Document limitation**:
   - Add docstring noting O(N) re-sterilization cost
   - Recommend avoiding frequent re-sterilization

**Action:** Implement lazy deletion option 1.

---

### 🐛 Bug #20: DisasterArchiver Inconsistent Return Types (MEDIUM)
**File:** `great_silence/simulation/disasters/archiver.py`
**Location:** Lines 125-132 in `get_disasters_in_window()`

**Current Code:**
```python
events = []

for t, d in self.recent_buffer:
    if start_myr <= t <= end_myr:
        events.append(d)  # HazardEvent objects

if HAS_H5PY and self.archive_path is not None and self.archive_path.exists():
    with h5py.File(self.archive_path, "r") as f:
        dset = f["disasters"]
        for row in dset:
            binary = bytes(row)
            decoded = decode_disaster(binary)
            if start_myr <= decoded.time_myr <= end_myr:
                events.append(decoded)  # DisasterBinary objects!
```

**Problem:** Returns mix of HazardEvent and DisasterBinary objects.

**Fix:** Convert DisasterBinary back to HazardEvent before appending:
```python
if start_myr <= decoded.time_myr <= end_myr:
    # Convert DisasterBinary to HazardEvent
    hazard = HazardEvent(
        time_myr=decoded.time_myr,
        event_type=EVENT_TYPE_REVERSE.get(decoded.event_type, "unknown"),
        position=decoded.position,
        energy=decoded.energy,
        sterilization_radius_pc=float(decoded.lethal_radius)
    )
    events.append(hazard)
```

**Note:** Need to import HazardEvent from ..engine and EVENT_TYPE_REVERSE from .encoding.

**Action:** Implement conversion in get_disasters_in_window() and get_all_disasters().

---

## DOCUMENTATION FILES

### Key Reference Documents

1. **COMPREHENSIVE_RESTORATION_PLAN.md**
   - Full restoration guide with detailed specs
   - Binary format specifications
   - Function signatures
   - Implementation details

2. **BYTECODE_ANALYSIS.md**
   - Extracted function signatures from Python 3.11 bytecode
   - Constants and data structures
   - Implementation patterns

3. **RESTORATION_PROGRESS.md**
   - Phase-by-phase progress tracking
   - GitHub issue links
   - Next steps

4. **RESTORATION_SUMMARY.md**
   - Complete restoration summary
   - Lines of code counts
   - Commit history

5. **SESSION_RESTART_GUIDE.md** (this file)
   - Single document to resume work
   - All context needed for new session

---

## GIT HISTORY

### Commits (in order)

1. `5172517` - Add stub files for disaster and threejs modules
2. `f921921` - Add GitHub issue links to restoration progress
3. `c3c97b3` - Add bytecode analysis for lost modules
4. `7c53c1f` - Update restoration progress with bytecode analysis findings
5. `a52f88c` - feat(Phase 1): implement disaster infrastructure modules
6. `84b5ceb` - feat(Phase 2): implement Three.js data layer
7. `1c15684` - feat(Phase 3): implement Three.js visualization templates
8. `69e8c66` - docs: add comprehensive restoration summary

### Current Branch
- Branch: `dev`
- Status: Phases 1-3 complete, Phase 4 pending

---

## HOW TO RESUME

### Option 1: Continue Phase 4 (Engine Integration)

```bash
# Open engine.py
vim great_silence/simulation/engine.py

# Follow the 6 integration steps documented above
# Test with small simulation after each step
```

### Option 2: Fix Bugs First

```bash
# Fix Bug #19 (lazy deletion in recovery.py)
vim great_silence/simulation/disasters/recovery.py

# Fix Bug #20 (type consistency in archiver.py)
vim great_silence/simulation/disasters/archiver.py

# Test fixes
python -c "from great_silence.simulation.disasters import *"
```

### Option 3: Start New Session Fresh

```bash
# Read this guide
cat claude_comments/SESSION_RESTART_GUIDE.md

# Check current status
git log --oneline -10
git status

# Review completed phases
ls -la great_silence/simulation/disasters/
ls -la great_silence/visualization/threejs/

# Continue with Phase 4 or bug fixes
```

---

## TESTING STRATEGY

### Unit Tests (to create)

```python
# test_disasters.py
def test_encoding_round_trip():
    event = HazardEvent(...)
    binary = encode_disaster(event)
    decoded = decode_disaster(binary)
    assert decoded.time_myr == event.time_myr

def test_spatial_index_queries():
    index = DisasterSpatialIndex()
    # Add disasters
    # Query spatial range
    # Query temporal range
    # Query spatiotemporal

def test_recovery_queue():
    queue = RecoveryQueue(1000)
    # Sterilize stars
    # Process recoveries
    # Check statistics
```

### Integration Tests

```python
# test_disaster_integration.py
def test_scheduler_integration():
    # Initialize simulation with SupernovaScheduler
    # Run simulation
    # Verify supernova detection

def test_archiver_integration():
    # Initialize simulation with DisasterArchiver
    # Run simulation
    # Verify disasters archived
```

### Manual Testing

```bash
# Quick simulation test
python examples/basic_simulation.py

# Check disaster outputs
ls -la data/disasters.h5

# Visualize output
python examples/visualize_disasters.py
```

---

## IMPORTANT NOTES

### Design Decisions

1. **HazardEvent Compatibility**
   - Current HazardEvent in engine.py lacks: jet_direction, beam_angle_deg, flags
   - encoding.py uses hasattr() checks to handle missing fields
   - Consider adding these fields to HazardEvent in future

2. **Spatial Index Resolution**
   - Default 30 voxels per axis (30^3 = 27K voxels)
   - Configurable via kpc_range and resolution parameters
   - Trade-off between memory and query performance

3. **Recovery Queue Performance**
   - O(log N) for initial sterilization
   - O(N) for re-sterilization (Bug #19)
   - Lazy deletion recommended fix

4. **HDF5 Dependency**
   - Optional (graceful degradation without h5py)
   - Compression enabled (gzip, level 4)
   - For large simulations, consider chunking

### Code Style Consistency

- Follow existing patterns in engine.py
- Use type hints where appropriate
- Keep functions under 50 lines
- Use vectorized NumPy operations
- Add docstrings for all public methods

---

## UNRESOLVED QUESTIONS

1. **HDF5 Backward Compatibility**
   - Should old disaster files be readable with new code?
   - Versioning strategy for binary format changes?

2. **Bug Fix Timing**
   - Fix bugs (#19, #20) before or after Phase 4 integration?
   - Recommendation: Fix #20 first (blocks integration), #19 after

3. **Test Coverage Target**
   - Add unit tests for new disaster modules?
   - Integration tests for Phase 4?
   - Recommendation: Add tests after implementation

4. **Performance Benchmarks**
   - Verify claimed speedups from bytecode analysis?
   - Compare spatial index O(k*m) vs linear O(N)
   - Benchmark recovery queue operations

---

## QUICK REFERENCE

### File Locations

```
great_silence/simulation/disasters/
├── __init__.py
├── encoding.py          # 24-byte binary format
├── spatial_index.py     # O(k*m) voxel queries
├── recovery.py          # O(log N) recovery queue
├── scheduler.py         # O(log N) SN scheduling
└── archiver.py          # Three-tier HDF5 storage

great_silence/visualization/threejs/
├── __init__.py
├── config.py            # 30+ config fields
├── data_extractor.py    # Probe interpolation
├── html_exporter.py     # HTML rendering
└── templates/
    ├── layers.js.j2     # Disaster viz
    └── animation.js.j2  # Probe trails

great_silence/simulation/
└── engine.py            # TO MODIFY for Phase 4

claude_comments/
├── COMPREHENSIVE_RESTORATION_PLAN.md  # Detailed specs
├── BYTECODE_ANALYSIS.md              # Extracted details
├── RESTORATION_PROGRESS.md           # Progress tracking
├── RESTORATION_SUMMARY.md            # Summary
└── SESSION_RESTART_GUIDE.md          # This file
```

### Key Constants

```python
# encoding.py
DISASTER_BINARY_FORMAT = '<fBhhhhbbbBBBxxxxx'  # 24 bytes
EVENT_TYPE_MAP = {'sn': 0, 'supernova': 0, 'grb': 1, 'nsm': 2}

# recovery.py
SterilizationStatus.HABITABLE = 0
SterilizationStatus.TEMPORARILY_STERILIZED = 1
SterilizationStatus.PERMANENTLY_STERILIZED = 2

# config.py
TRAIL_LENGTH = 3  # Probe trail length
```

### Import Patterns

```python
# Import disaster modules
from great_silence.simulation.disasters import (
    DisasterBinary,
    encode_disaster,
    decode_disaster,
    DisasterSpatialIndex,
    RecoveryQueue,
    SterilizationStatus,
    SupernovaScheduler,
    DisasterArchiver,
)

# Import threejs modules
from great_silence.visualization.threejs import (
    ThreeJSConfig,
    SimulationDataExtractor,
    ThreeJSRenderer,
    export_html,
)
```

---

## END OF GUIDE

**Next Action:** Implement Phase 4 engine integration or fix Bug #20

**Estimated Time Remaining:**
- Phase 4 integration: 2-3 hours
- Bug fixes: 30-60 minutes
- Testing: 1-2 hours

**Total Estimated Completion Time:** 3.5-6.5 hours

---

**Last Updated:** 2026-01-13
**Session:** ses_4485
**Restoration Progress:** Phases 1-3 Complete (75%), Phase 4 Pending (25%)
