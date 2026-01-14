# Comprehensive Code Restoration Plan

**Created:** 2026-01-13
**Purpose:** Iterative restoration guide for lost code (safe to reference if context is lost)

## Executive Summary

Lost files during git history cleanup (2026-01-13):
- 5 Python modules in `great_silence/simulation/disasters/`
- 4 Python modules + templates in `great_silence/visualization/threejs/`

Recovery sources available:
- __pycache__ bytecode (partial structure extraction)
- GitHub issues #17-31 (feature descriptions)
- Existing codebase patterns (engine.py, hazards.py)

---

## Part 1: Lost Disaster Module Files

### 1.1 encoding.py (CRITICAL - 24-byte binary format)

**Location:** `great_silence/simulation/disasters/encoding.py`
**Bytecode Size:** 7,031 bytes (cpython-311)

**Data Structure - DisasterBinary (24 bytes):**
```
Offset  Type     Field              Notes
0       float32  time_myr           Simulation time
4       uint8    event_type         0=SN, 1=GRB, 2=NSM
5       int16    position_x         kpc * 1000
7       int16    position_y         kpc * 1000
9       int16    position_z         kpc * 1000
11      int16    lethal_radius      pc (integer)
13      int8     jet_dir_x          unit vector * 127
14      int8     jet_dir_y          unit vector * 127
15      int8     jet_dir_z          unit vector * 127
16      uint8    beam_angle_deg     degrees
17      uint8    energy_log10       log10(energy/1e50) + 50
18      uint8    flags              bit flags
19-23   padding  (5 bytes)          alignment
```

**Struct Format:** `'<fBhhhhbbbBBBxxxxx'`

**Functions to implement:**
1. `encode_disaster(event: HazardEvent) -> bytes` (24 bytes)
2. `decode_disaster(data: bytes) -> DisasterBinary`
3. `encode_disaster_batch(events: List[HazardEvent]) -> bytes`
4. `decode_disaster_batch(data: bytes, count: int) -> List[DisasterBinary]`

**Constants:**
```python
DISASTER_BINARY_FORMAT = '<fBhhhhbbbBBBxxxxx'
EVENT_TYPE_MAP = {'sn': 0, 'supernova': 0, 'grb': 1, 'nsm': 2}
EVENT_TYPE_REVERSE = {0: 'sn', 1: 'grb', 2: 'nsm'}
```

**KNOWN BUG (Issue #18):** Energy encoding formula is wrong
- Current (broken): `log10(event.energy) - 50 + 50` (cancels out!)
- Correct: `log10(event.energy / 1e50) + 50`

---

### 1.2 spatial_index.py (O(k*m) queries)

**Location:** `great_silence/simulation/disasters/spatial_index.py`
**Bytecode Size:** 8,599 bytes (cpython-311)

**Class: DisasterSpatialIndex**
```python
class DisasterSpatialIndex:
    """3D voxel index for efficient disaster lookup."""

    def __init__(self, kpc_range: float = 20.0, resolution: int = 30):
        """
        Args:
            kpc_range: Half-width of indexed region (default 20 kpc)
            resolution: Voxels per axis (30^3 = 27K voxels)
        """

    def _position_to_voxel(self, position: np.ndarray) -> Tuple[int, int, int]:
        """Convert kpc position to voxel indices."""

    def add_disaster(self, disaster: DisasterBinary) -> int:
        """Add disaster to index. Returns disaster ID."""

    def query_spatial(self, center: np.ndarray, radius_kpc: float) -> List[DisasterBinary]:
        """Query disasters within radius. O(k*m) where k=touched voxels."""

    def query_temporal(self, time_start: float, time_end: float) -> List[DisasterBinary]:
        """Query disasters in time window. Uses binary search."""

    def query_spatiotemporal(self, center, radius_kpc, time_start, time_end) -> List[DisasterBinary]:
        """Combined spatial and temporal query."""

    def clear(self):
        """Clear all stored disasters."""
```

**Implementation notes:**
- Uses `collections.defaultdict` to avoid shared-list bug
- Stores disasters in list, builds sorted time index for temporal queries
- Voxel formula: `ix = int((pos[0] + kpc_range) / (2*kpc_range) * resolution)`

---

### 1.3 recovery.py (O(log N) heap operations)

**Location:** `great_silence/simulation/disasters/recovery.py`
**Bytecode Size:** 7,169 bytes (cpython-311)

**Class: SterilizationStatus (enum-like)**
```python
class SterilizationStatus:
    HABITABLE = 0
    TEMPORARILY_STERILIZED = 1
    PERMANENTLY_STERILIZED = 2
```

**Class: RecoveryQueue**
```python
class RecoveryQueue:
    """Priority queue for star recovery. O(log N) operations."""

    def __init__(self, n_stars: int):
        """Initialize recovery tracking arrays."""
        # Needs: status array, recovery heap, in_queue set

    def sterilize_star(self, star_idx: int, current_time_myr: float,
                       recovery_time_myr: float, permanent: bool = False):
        """Mark star as sterilized, schedule recovery if temporary."""

    def sterilize_batch(self, star_indices: np.ndarray, current_time_myr: float,
                        recovery_times_myr: np.ndarray, permanent_mask: np.ndarray):
        """Batch sterilization for efficiency."""

    def process_recoveries(self, current_time_myr: float) -> List[int]:
        """Process all stars that have recovered. O(k log N)."""

    def get_habitable_mask(self) -> np.ndarray:
        """Return boolean mask of habitable stars."""

    def get_statistics(self) -> dict:
        """Return sterilization statistics."""
```

**KNOWN BUG (Issue #19):** Re-sterilization is O(N), not O(log N)
- Current: Full heap rebuild on re-sterilization
- Fix options: lazy deletion, generation counters, or document limitation

---

### 1.4 scheduler.py (O(k log N) queries)

**Location:** `great_silence/simulation/disasters/scheduler.py`
**Bytecode Size:** 5,378 bytes (cpython-311)

**Class: SupernovaScheduler**
```python
class SupernovaScheduler:
    """Pre-computed supernova schedule with O(log N) queries."""

    def __init__(self, masses: np.ndarray, metallicities: np.ndarray,
                 ages_myr: np.ndarray, stellar_evolution: 'StellarEvolution'):
        """Initialize scheduler with galaxy data."""

    def _build_schedule(self, masses, metallicities, ages_myr):
        """Pre-compute SN times for all massive stars. O(N_massive log N_massive)."""

    def get_supernovae_in_window(self, start_myr: float, end_myr: float) -> List[int]:
        """Get star indices that go SN in time window. O(k log N)."""

    def add_new_star(self, star_idx: int, mass: float, metallicity: float,
                     birth_time_myr: float):
        """Add newly formed star to schedule."""

    @property
    def pending_count(self) -> int:
        """Number of stars still scheduled to explode."""
```

**Implementation notes:**
- Uses heap for time-ordered events
- Requires StellarEvolution class for main-sequence lifetime calculation
- Only schedules massive stars (> ~8 solar masses)

---

### 1.5 archiver.py (Tiered HDF5 storage)

**Location:** `great_silence/simulation/disasters/archiver.py`
**Bytecode Size:** 8,613 bytes (cpython-311)

**Class: DisasterArchiver**
```python
class DisasterArchiver:
    """Tiered disaster storage with HDF5 backend.

    Tier 1: Recent events (in-memory, full HazardEvent objects)
    Tier 2: Binary buffer (in-memory, compact DisasterBinary)
    Tier 3: HDF5 file (on-disk, compressed)
    """

    def __init__(self, archive_path: Optional[Path], recent_window_myr: float = 10.0,
                 buffer_size: int = 1000):
        """Initialize archiver."""

    def _init_hdf5(self):
        """Initialize HDF5 file with disaster dataset."""

    def archive_disaster(self, disaster: 'HazardEvent', current_time_myr: float):
        """Archive disaster with tiered storage."""

    def _flush_to_hdf5(self):
        """Flush binary buffer to HDF5 file."""

    def get_disasters_in_window(self, start_myr: float, end_myr: float) -> List:
        """Get disasters in time window."""

    def get_all_disasters(self) -> List:
        """Get all archived disasters (for analysis)."""

    def finalize(self):
        """Flush remaining buffer and close HDF5."""
```

**KNOWN BUG (Issue #20):** Returns inconsistent types
- From recent buffer: `List[HazardEvent]`
- From spatial index: `List[DisasterBinary]`
- Fix: Convert DisasterBinary back to HazardEvent before returning

---

## Part 2: Lost Three.js Visualization Files

### 2.1 config.py

**Location:** `great_silence/visualization/threejs/config.py`
**Bytecode Size:** 5,065 bytes (cpython-311)

**Class: ThreeJSConfig (dataclass)**
```python
@dataclass
class ThreeJSConfig:
    """Central configuration for Three.js visualization."""

    # Camera
    camera_position: Tuple[float, float, float] = (0, 0, 30)
    camera_fov: float = 75
    camera_near: float = 0.1
    camera_far: float = 1000

    # Controls
    enable_damping: bool = True
    damping_factor: float = 0.05
    enable_zoom: bool = True
    auto_rotate: bool = False
    auto_rotate_speed: float = 2.0

    # Appearance
    background_color: str = '#000000'
    star_point_size: float = 0.05
    star_opacity: float = 0.8

    # Civilizations
    civ_active_size: float = 0.15
    civ_active_opacity: float = 0.9
    civ_extinct_size: float = 0.1
    civ_extinct_opacity: float = 0.5
    civ_extinct_color: str = '#666666'

    # Kardashev scale
    kardashev_colorscale: str = 'viridis'
    kardashev_min: float = 0.7
    kardashev_max: float = 3.0
    glow_threshold: float = 2.0
    glow_intensity: float = 0.5

    # Death markers
    death_marker_size: float = 0.2
    death_colors: Dict[str, str] = field(default_factory=dict)

    # Hazards
    hazard_supernova_color: str = '#ff4444'
    hazard_grb_color: str = '#ffaa00'
    hazard_nsm_color: str = '#aa44ff'
    hazard_marker_size: float = 0.3
    hazard_opacity: float = 0.7

    # Disaster visualization (from issues #28-29)
    shockwave_duration_myr: float = 50.0
    sterilization_zone_opacity: float = 0.3
    disaster_fade_time_myr: float = 10.0

    # Probe trails (from issues #21-22, #30-31)
    probe_trail_length: int = 3
    probe_glow_enabled: bool = True

    # Trajectories and spheres
    trajectory_width: float = 2.0
    trajectory_opacity: float = 0.6
    trajectory_fade_window_myr: float = 100.0
    sphere_opacity: float = 0.2
    sphere_segments: int = 32
    sphere_color: str = '#4488ff'
    sphere_growth_window_myr: float = 50.0

    # Animation
    interpolation_factor: int = 10
    frame_duration_ms: int = 50
    default_playback_speed: float = 1.0
    min_playback_speed: float = 0.1
    max_playback_speed: float = 10.0

    # Export
    include_threejs_bundle: bool = True
    data_embed_threshold_mb: float = 10.0

    def to_dict(self) -> dict:
        """Convert config to dict for JSON serialization."""
```

---

### 2.2 data_extractor.py

**Location:** `great_silence/visualization/threejs/data_extractor.py`
**Bytecode Size:** 35,475 bytes (cpython-311) - LARGEST FILE

**Class: FrameData (dataclass)**
```python
@dataclass
class FrameData:
    """Data for a single animation frame."""
    time_gyr: float
    active_civ_positions: np.ndarray
    active_civ_kardashev: np.ndarray
    extinct_civ_positions: np.ndarray
    trajectory_segments: List
    hazard_positions: np.ndarray
    hazard_types: List[str]
    probe_positions: np.ndarray
    probe_civ_ids: np.ndarray
    probe_progress: np.ndarray
    probe_ids: List[int]  # For trail rendering (Issue #31)
```

**Class: SimulationDataExtractor**
```python
class SimulationDataExtractor:
    """Extract visualization data from simulation or HDF5 for Three.js."""

    def __init__(self, source: Union[str, Path, 'GalaxySimulation'],
                 config: Optional[ThreeJSConfig] = None):
        """Initialize extractor with simulation data source."""

    def _load_source(self):
        """Load data from source (HDF5 or simulation object)."""

    def _extract_from_simulation(self) -> dict:
        """Extract data dict from simulation object."""

    def extract_galaxy_data(self, subsample: int = 10000, seed: int = 42) -> dict:
        """Extract star positions for visualization."""

    def extract_civilization_data(self, time_gyr: Optional[float] = None) -> dict:
        """Extract civilization data at given time."""

    def extract_trajectory_data(self, time_gyr: Optional[float] = None) -> List[dict]:
        """Extract expansion trajectory lines for visualization."""

    def extract_probe_data(self, time_gyr: Optional[float] = None) -> dict:
        """Extract in-flight probe data with interpolation (Issue #30).

        Returns:
            Dict with positions, civ_ids, progress, and probe_ids
        """

    def extract_hazard_data(self, time_gyr: Optional[float] = None) -> dict:
        """Extract hazard data with timing info (Issue #25, #27).

        Returns:
            Dict with positions, types, times_gyr, time_since
        """
```

**Key implementation for probe interpolation (Issue #30):**
```python
def extract_probe_data(self, time_gyr):
    # Find bracketing snapshots
    snap_before, snap_after = self._find_bracketing_snapshots(time_gyr)

    # Interpolate probe positions
    for probe_id in all_probes:
        if probe_id in snap_before and probe_id in snap_after:
            # Linear interpolation
            alpha = (time_gyr - snap_before.time) / (snap_after.time - snap_before.time)
            alpha = max(0, min(1, alpha))  # Clamp to [0,1]
            pos = lerp(pos_before, pos_after, alpha)
        elif probe_id in snap_before:
            # Probe arrived or retargeted
            pos = snap_before[probe_id].position
        elif probe_id in snap_after:
            # Probe launched - interpolate from origin
            alpha = compute_launch_alpha(time_gyr, snap_after.launch_time)
            pos = lerp(origin, snap_after.position, alpha)
```

---

### 2.3 html_exporter.py

**Location:** `great_silence/visualization/threejs/html_exporter.py`
**Bytecode Size:** 10,276 bytes (cpython-311)

**Class: ThreeJSRenderer**
```python
class ThreeJSRenderer:
    """Render Three.js visualization as self-contained HTML."""

    def __init__(self, source: Union[str, Path, Any],
                 config: Optional[ThreeJSConfig] = None,
                 template_dir: Optional[str] = None):
        """Initialize renderer."""

    def _load_data(self, animated: bool = False):
        """Load data for rendering."""

    def render(self, animated: bool = False,
               show_trajectories: bool = True,
               show_spheres: bool = True,
               show_hazards: bool = True,
               animation_data_url: Optional[str] = None) -> str:
        """Render visualization to HTML string."""

    def export(self, filepath: Union[str, Path], animated: bool = False,
               show_trajectories: bool = True, show_spheres: bool = True,
               show_hazards: bool = True, compress: bool = False):
        """Export to HTML file."""

def export_html(source, output_path, config=None, animated=False,
                show_trajectories=True, show_spheres=True,
                show_hazards=True, compress=False, template_dir=None):
    """Convenience function to export HTML."""
```

---

### 2.4 Templates (Lost Jinja2 files)

**Location:** `great_silence/visualization/threejs/templates/`

#### layers.js.j2 (Issues #23, #24, #28, #29)
```javascript
// Functions needed:
function createDisasterShockwaves() { /* Expanding rings */ }
function updateShockwaves(frame_index) { /* Animate expansion */ }
function getDisasterColor(disaster_type) { /* Type-specific colors */ }
function createSterilizationZones() { /* Translucent spheres */ }
function updateSterilizationZones(frame_index) { /* Fade during recovery */ }
```

#### animation.js.j2 (Issues #22, #31)
```javascript
// Trail history buffer
const trailHistory = {}; // probe_id -> [{x, y, z, alpha}, ...]
const TRAIL_LENGTH = 3;

function createProbeTrails() { /* Line geometry for trails */ }
function updateProbeTrails(probeData) { /* Update trail positions */ }
function updateTrailGeometry(probe_id, history) { /* Rebuild line mesh */ }
```

---

## Part 3: GitHub Issues Reference

### Open Bugs (Must Fix)
- **#18**: Energy encoding formula error (CRITICAL)
- **#19**: RecoveryQueue re-sterilization is O(N) (MEDIUM)
- **#20**: DisasterArchiver returns inconsistent types (MEDIUM)

### Open Enhancements
- **#17**: Disaster Integration Steps 2-5 (blocked by lost code)
- **#11-16**: Performance optimizations (independent)
- **#6-7**: Adaptive timesteps, parallelism (independent)

### Closed Issues (Reference for Implementation)
- **#21**: Probe interpolation (implement in data_extractor.py)
- **#22**: Probe trails (implement in animation.js.j2)
- **#23**: Disaster shockwaves (implement in layers.js.j2)
- **#24**: Sterilization zones (implement in layers.js.j2)
- **#25**: Disaster time data extraction (implement in data_extractor.py)
- **#26**: Wire up new layers (integration)
- **#27-31**: Various disaster/probe features (redundant with #21-26)

---

## Part 4: Restoration Phases

### Phase 1: Core Disaster Infrastructure (4-6 hours)

**Priority Order:**
1. `encoding.py` - Required by all other disaster modules
2. `spatial_index.py` - Required by archiver
3. `recovery.py` - Required by engine integration
4. `scheduler.py` - Required by engine integration
5. `archiver.py` - Required for persistence

**Testing:**
- Unit tests for encode/decode round-trip
- Unit tests for spatial queries
- Unit tests for recovery heap operations
- Integration test with existing HazardEvaluator

### Phase 2: Three.js Data Layer (3-4 hours)

**Priority Order:**
1. `config.py` - Simple dataclass, low risk
2. `data_extractor.py` - Core functionality (largest file)
3. `html_exporter.py` - Depends on data_extractor

**Testing:**
- Unit tests for data extraction
- Integration test with existing visualization code
- Manual verification with sample simulation

### Phase 3: Three.js Templates (2-3 hours)

**Files:**
1. `templates/layers.js.j2` - Shockwaves, sterilization zones
2. `templates/animation.js.j2` - Probe trails

**Testing:**
- Manual browser verification
- Animation playback testing

### Phase 4: Engine Integration (2-3 hours)

**Changes to `great_silence/simulation/engine.py`:**
1. Initialize SupernovaScheduler in `initialize()`
2. Initialize RecoveryQueue in `initialize()`
3. Replace SN detection in `_detect_disasters_with_scheduler()`
4. Integrate RecoveryQueue in `_apply_hazards()`
5. Add DisasterArchiver calls
6. Update ProgressMetrics for disaster stats

---

## Part 5: File Dependencies

```
encoding.py         <- (standalone)
spatial_index.py    <- encoding.py
recovery.py         <- (standalone)
scheduler.py        <- (uses StellarEvolution from astrophysics)
archiver.py         <- encoding.py, spatial_index.py, HazardEvent from engine.py

config.py           <- (standalone)
data_extractor.py   <- config.py, simulation types
html_exporter.py    <- config.py, data_extractor.py, Jinja2 templates
```

---

## Part 6: Quick Reference - Existing Code Patterns

### HazardEvent (from engine.py:123)
```python
@dataclass
class HazardEvent:
    time_myr: float
    event_type: str  # 'supernova', 'grb'
    position: np.ndarray  # 3D in kpc
    energy: float  # ergs
    sterilization_radius_pc: float
    affected_civ_ids: List[int]
```

### Existing Hazard Evaluation (from astrophysics/hazards.py)
- `HazardEvaluator.evaluate_supernova_hazard()` - Uses spatial_index optionally
- `HazardEvaluator.evaluate_grb_hazard()` - Metallicity-dependent rates

### Existing Visualization (from visualization/interactive_3d.py)
- Reference for Three.js integration patterns
- Uses similar data extraction logic

---

## Part 7: Unresolved Questions

1. HDF5 backward compatibility required? (affects encoding format)
2. Should fixes for bugs #18-20 be included during reconstruction?
3. Branch strategy - new branch or continue on dev?
4. Test coverage target - existing tests only or add new?
5. Performance benchmarks - verify claimed speedups?

---

## Appendix A: Bytecode Files Location

```
great_silence/simulation/disasters/__pycache__/
├── encoding.cpython-311.pyc      (7,031 bytes)
├── encoding.cpython-314.pyc      (7,630 bytes)
├── spatial_index.cpython-311.pyc (8,599 bytes)
├── spatial_index.cpython-314.pyc (9,721 bytes)
├── recovery.cpython-311.pyc      (7,169 bytes)
├── recovery.cpython-314.pyc      (8,089 bytes)
├── scheduler.cpython-311.pyc     (5,378 bytes)
├── scheduler.cpython-314.pyc     (5,873 bytes)
├── archiver.cpython-311.pyc      (8,613 bytes)
├── archiver.cpython-314.pyc      (9,148 bytes)

great_silence/visualization/threejs/__pycache__/
├── config.cpython-311.pyc        (5,065 bytes)
├── config.cpython-314.pyc        (5,566 bytes)
├── data_extractor.cpython-311.pyc (35,475 bytes)
├── data_extractor.cpython-314.pyc (32,586 bytes)
├── html_exporter.cpython-311.pyc  (10,276 bytes)
├── html_exporter.cpython-314.pyc  (10,453 bytes)
```

---

## Appendix B: Git Recovery Attempts (Failed)

- `git reflog` - Only 2 entries (cleared)
- `backup/dev` remote - Does not contain disaster/threejs dirs
- No stashes available
- Code was never committed or commits were force-pushed away

---

**Document Version:** 1.0
**Last Updated:** 2026-01-13
