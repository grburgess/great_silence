# Disaster Tracking & Visualization Code Map

## Disaster Module Architecture

### Module Exports (`__init__.py`)
- **Purpose**: Central export interface for disaster tracking subsystem
- **Exports**:
  - Binary encoding: `DisasterBinary`, `encode_disaster`, `decode_disaster`, `encode_disaster_batch`, `decode_disaster_batch`, `DISASTER_BINARY_FORMAT`, `EVENT_TYPE_MAP`, `EVENT_TYPE_REVERSE`
  - Spatial indexing: `DisasterSpatialIndex`
  - Recovery tracking: `SterilizationStatus`, `RecoveryQueue`
  - Scheduling: `SupernovaScheduler`
  - Archival: `DisasterArchiver`

### Binary Encoding (`encoding.py`)
- **Purpose**: Compact 24-byte binary format for disaster events
- **Key Components**:
  - `DISASTER_BINARY_FORMAT`: Struct format string `<fBhhhhbbbBBBxxxxx`
  - `EVENT_TYPE_MAP`: Maps event types to integers (sn=0, grb=1, nsm=2)
  - `DisasterBinary`: Dataclass with decoded fields
  - `encode_disaster()`: HazardEvent → 24 bytes
  - `decode_disaster()`: 24 bytes → DisasterBinary
  - Batch functions for bulk encoding/decoding
- **Binary Layout**:
  - time_myr (float32, 4B)
  - event_type (uint8, 1B)
  - position (3×int16, 6B) - kpc × 1000
  - lethal_radius (int16, 2B) - pc
  - jet_direction (3×int8, 3B) - unit vector × 127
  - beam_angle_deg (uint8, 1B)
  - energy_log10 (uint8, 1B) - log10(E/1e50)+50
  - flags (uint8, 1B) - bit 0=permanent, bit 1=opposing_jet
  - padding (5B) - total 24 bytes

### Spatial Indexing (`spatial_index.py`)
- **Purpose**: O(k*m) spatial queries using 3D voxel grid
- **Key Components**:
  - `DisasterSpatialIndex`: Main class
  - `_position_to_voxel()`: Maps kpc position to voxel indices
  - `add_disaster()`: Add disaster, returns disaster ID
  - `query_spatial()`: Find disasters within radius
  - `query_temporal()`: Find disasters in time window (binary search)
  - `query_spatiotemporal()`: Combined spatial + temporal query
  - `clear()`: Reset index
- **Performance**:
  - Default: 30³ = 27K voxels, 40 kpc range
  - Query complexity: O(k × m) where k=touched voxels, m=disasters/voxel
  - Temporal queries use binary search on sorted times

### Recovery Queue (`recovery.py`)
- **Purpose**: Priority queue for star sterilization tracking
- **Key Components**:
  - `SterilizationStatus`: Enumeration (HABITABLE=0, TEMPORARILY_STERILIZED=1, PERMANENTLY_STERILIZED=2)
  - `RecoveryQueue`: Main class with heapq backend
  - `sterilize_star()`: Mark star sterilized, schedule recovery
  - `sterilize_batch()`: Batch sterilization for efficiency
  - `process_recoveries()`: Process all recovered stars, O(k log N)
  - `get_habitable_mask()`: Boolean mask of habitable stars
  - `get_statistics()`: Sterilization counts and percentages
- **Performance**: O(log N) heap operations

### Supernova Scheduler (`scheduler.py`)
- **Purpose**: Pre-computed supernova schedule with O(log N) queries
- **Key Components**:
  - `SupernovaScheduler`: Main class with heapq backend
  - `_build_schedule()`: Pre-compute SN times for massive stars (>8 M_sun)
  - `get_supernovae_in_window()`: Get SNe in time window
  - `add_new_star()`: Add newly formed star to schedule
  - `pending_count`: Number of pending supernovae
- **Performance**:
  - Build: O(N_massive log N_massive)
  - Query: O(k log N) where k=SNe in window

### Archiver (`archiver.py`)
- **Purpose**: Tiered disaster storage with HDF5 backend
- **Key Components**:
  - `DisasterArchiver`: Main class
  - Tier 1: Recent events (in-memory, full objects)
  - Tier 2: Binary buffer (in-memory, compact)
  - Tier 3: HDF5 file (on-disk, compressed)
  - `archive_disaster()`: Archive with tiered storage
  - `_flush_to_hdf5()`: Flush binary buffer to disk
  - `get_disasters_in_window()`: Retrieve disasters from all tiers
  - `get_all_disasters()`: Retrieve all disasters for analysis
  - `finalize()`: Flush buffer and close HDF5
- **Configuration**:
  - recent_window_myr: Time window for tier 1 (default 10 Myr)
  - buffer_size: Buffer size before flush (default 1000)
  - HDF5 compression: gzip level 4

## Three.js Visualization Modules

### Module Exports (`__init__.py`)
- **Exports**:
  - `ThreeJSConfig`: Configuration dataclass
  - `SimulationDataExtractor`: Data extraction class
  - `FrameData`: Frame data dataclass
  - `ThreeJSRenderer`: HTML renderer class
  - `export_html()`: Convenience export function

### Configuration (`config.py`)
- **Purpose**: Central configuration for Three.js visualization
- **Key Settings**:
  - **Camera**: position, fov, near, far, damping, zoom, auto_rotate
  - **Stars**: point_size, opacity
  - **Civilizations**: active_size, extinct_size, kardashev_colorscale, glow
  - **Hazards**: colors (SN, GRB, NSM), marker_size, opacity
  - **Shockwaves**: duration_myr, sterilization_zone_opacity, fade_time_myr
  - **Probes**: trail_length, glow_enabled
  - **Trajectories**: width, opacity, fade_window_myr
  - **Spheres**: opacity, segments, color, growth_window_myr
  - **Animation**: interpolation_factor, frame_duration_ms, playback_speed
  - **Export**: include_threejs_bundle, data_embed_threshold_mb
- **Method**: `to_dict()` for JSON serialization

### Data Extractor (`data_extractor.py`)
- **Purpose**: Extract visualization data from simulation or HDF5
- **Key Components**:
  - `SimulationDataExtractor`: Main extractor class
  - `FrameData`: Dataclass for single animation frame
  - `_load_from_hdf5()`: Load data from HDF5 file
  - `_extract_from_simulation()`: Extract from simulation object
- **Extraction Methods**:
  - `extract_galaxy_data()`: Star positions with optional subsampling
  - `extract_civilization_data()`: Active and extinct civilization data
  - `extract_trajectory_data()`: Expansion trajectory lines
  - `extract_probe_data()`: In-flight probe data with interpolation (Issue #30)
  - `extract_hazard_data()`: Hazard data with times_gyr and time_since arrays (Issue #25, #27)
- **Data Flow**: Extracts from snapshots or HDF5, returns numpy arrays + metadata

### HTML Exporter (`html_exporter.py`)
- **Purpose**: Render Three.js visualization as self-contained HTML
- **Key Components**:
  - `ThreeJSRenderer`: Main renderer class
  - `_load_data()`: Prepare data for template rendering
  - `render()`: Render to HTML string
  - `export()`: Export to HTML file with optional gzip
  - `_get_template()`: Load Jinja2 template or fallback to basic template
  - `export_html()`: Convenience export function
- **Features**:
  - Animation support with frame interpolation
  - External or embedded animation data
  - Toggle visibility: trajectories, spheres, hazards
  - Gzip compression option
  - Jinja2 template system with fallback

### Templates (`templates/`)
- **Partial Templates**:
  - `animation.js.j2`: Probe trail animation logic
  - `layers.js.j2`: Visualization layer rendering
- **Template Loading**:
  - Loads from `templates/` directory or custom path
  - Falls back to `_BasicTemplate` if Jinja2 unavailable
  - Template file: `index.html.j2` (expected but not found in current codebase)

## Engine Integration Points

### Initialization (`engine.py:255-353`)
```python
# Disaster tracking modules (initialized in initialize())
self.supernova_scheduler: Optional[Any] = None
self.recovery_queue: Optional[Any] = None
self.disaster_archiver: Optional[Any] = None

# Initialize disaster tracking modules (line 325-352)
from .disasters import SupernovaScheduler, RecoveryQueue, DisasterArchiver

self.supernova_scheduler = SupernovaScheduler(
    self.galaxy.masses,
    self.galaxy.metallicities,
    self.galaxy.ages,
    self.sfh
)

self.recovery_queue = RecoveryQueue(n_stars)

if self.config.simulation.save_snapshots:
    archive_path = Path(self.config.simulation.output_directory) / "disasters.h5"
    self.disaster_archiver = DisasterArchiver(
        archive_path=archive_path,
        recent_window_myr=10.0,
        buffer_size=1000
    )
```

### Disaster Archiving (`engine.py:1715-1730, 1776-1798`)
```python
# Archive disaster (SN event)
if self.disaster_archiver is not None:
    self.disaster_archiver.archive_disaster(hazard, self.current_time_myr)

# Sterilize star in recovery queue
if self.recovery_queue is not None:
    sterilization_radius = hazard.sterilization_radius_pc
    recovery_time = sterilization_radius / 10.0  # Recovery rate of 10 pc/Myr
    self.recovery_queue.sterilize_star(
        civ.parent_star_idx,
        self.current_time_myr,
        recovery_time,
        permanent=(hazard.energy > 1e52)  # Permanent for very energetic events
    )
```

### Recovery Processing (`engine.py:1794-1798`)
```python
# Process star recoveries
if self.recovery_queue is not None:
    recovered = self.recovery_queue.process_recoveries(self.current_time_myr)
```

### Finalization (`engine.py:521-523`)
```python
# Finalize disaster archiver
if self.disaster_archiver is not None:
    self.disaster_archiver.finalize()
```

### Spatial Index Integration (`engine.py:317-323, 1478-1493`)
```python
# Build spatial index for efficient hazard and expansion queries
if self.config.simulation.use_numba:
    from ..utils.spatial import SpatialIndex
    self._spatial_index = SpatialIndex(self.galaxy.positions)

# Use in hazard evaluation
if self._spatial_index is not None:
    nearby_indices, nearby_distances_kpc = self._spatial_index.query_radius(...)
```

## Data Flow

### Disaster Event Flow
```
Simulation Event (SN/GRB/NSM)
    ↓
HazardEvent Created
    ↓
Binary Encoding (24 bytes) → encode_disaster()
    ↓
Tier 1: Recent Buffer (full objects)
    ↓
Tier 2: Binary Buffer (compact)
    ↓
Tier 3: HDF5 Archive (compressed)
```

### Spatial Query Flow
```
DisasterBinary Objects
    ↓
DisasterSpatialIndex.add_disaster()
    ↓
Voxel Assignment (_position_to_voxel)
    ↓
query_spatial() / query_spatiotemporal()
    ↓
Filter by distance + time
    ↓
Return matching disasters
```

### Recovery Flow
```
Hazard Event (sterilization)
    ↓
RecoveryQueue.sterilize_star()
    ↓
Mark as TEMPORARILY_STERILIZED or PERMANENTLY_STERILIZED
    ↓
Schedule recovery time (heap push)
    ↓
RecoveryQueue.process_recoveries() at each timestep
    ↓
Mark as HABITABLE when time elapsed
    ↓
get_habitable_mask() returns updated state
```

### Visualization Data Flow
```
Simulation / HDF5 Snapshots
    ↓
SimulationDataExtractor
    ├─ extract_galaxy_data()
    ├─ extract_civilization_data()
    ├─ extract_trajectory_data()
    ├─ extract_probe_data() (with interpolation)
    └─ extract_hazard_data() (with times_gyr, time_since)
    ↓
FrameData or Full Dataset
    ↓
ThreeJSRenderer._load_data()
    ↓
Jinja2 Template Rendering
    ↓
HTML Export (embedded or external data)
```

## Module Dependencies

### Disaster Modules
```
engine.py
    ↓
├─ SupernovaScheduler
│   └─ stellar_evolution (main_sequence_lifetime)
├─ RecoveryQueue
│   └─ None (self-contained)
└─ DisasterArchiver
    ├─ encoding (encode_disaster, decode_disaster)
    └─ h5py (optional)

encoding.py
    └─ struct, numpy

spatial_index.py
    ├─ encoding (DisasterBinary)
    └─ numpy, collections

recovery.py
    └─ numpy, heapq

scheduler.py
    ├─ stellar_evolution
    └─ numpy, heapq
```

### Visualization Modules
```
visualization/
├─ config.py
│   └─ dataclasses, typing
├─ data_extractor.py
│   ├─ config.py
│   └─ h5py (optional)
├─ html_exporter.py
│   ├─ config.py
│   ├─ data_extractor.py
│   └─ jinja2 (optional)
└─ templates/
    ├─ animation.js.j2
    └─ layers.js.j2
```

## Integration with Simulation Engine

### Initialization Order
1. Generate galaxy stellar population
2. Assign stellar properties (ages, masses, metallicities)
3. Build spatial index (if numba enabled)
4. Initialize supernova scheduler (pre-compute SN times)
5. Initialize recovery queue
6. Initialize disaster archiver (if snapshots enabled)

### Per-Timestep Integration
1. **Hazard Generation**: SN/GRB/NSM events occur
2. **Impact Evaluation**: Check affected civilizations
3. **Archiving**: `disaster_archiver.archive_disaster(hazard, current_time_myr)`
4. **Sterilization**: `recovery_queue.sterilize_star(star_idx, time, recovery_time)`
5. **Recovery Processing**: `recovery_queue.process_recoveries(current_time_myr)`
6. **Snapshot Saving**: Include hazard events in snapshot data

### Visualization Pipeline
1. Run simulation with `save_snapshots=True`
2. Snapshots saved to HDF5 with hazards data
3. `SimulationDataExtractor` loads HDF5 or simulation object
4. Extract frame data or full animation frames
5. `ThreeJSRenderer` generates HTML with embedded/external data
6. Browser renders interactive 3D visualization

## Key Performance Considerations

1. **Binary Encoding**: 24 bytes per disaster (vs full object serialization)
2. **Spatial Index**: Voxel grid reduces query complexity from O(N) to O(k*m)
3. **Recovery Queue**: Heap-based O(log N) operations
4. **SN Scheduler**: Pre-computed schedule, heap-based queries
5. **Tiered Storage**: Recent events in memory, older events on disk
6. **Batch Operations**: `sterilize_batch()`, `encode_disaster_batch()` for efficiency
7. **Subsampling**: Galaxy stars subsampled for visualization (default 10K)
8. **Interpolation**: Probe positions interpolated between snapshots (Issue #30)

## File Locations

- **Disaster Modules**: `great_silence/simulation/disasters/`
  - `__init__.py`, `encoding.py`, `spatial_index.py`
  - `recovery.py`, `scheduler.py`, `archiver.py`

- **Visualization Modules**: `great_silence/visualization/threejs/`
  - `__init__.py`, `config.py`, `data_extractor.py`, `html_exporter.py`
  - `templates/animation.js.j2`, `templates/layers.js.j2`

- **Engine Integration**: `great_silence/simulation/engine.py`
  - Lines 255-353: Initialization
  - Lines 1715-1798: Hazard handling and archiving
  - Lines 521-523: Finalization

## Unresolved Questions

- Missing `index.html.j2` template in `templates/` directory (falls back to basic template)
- Spatial index in `utils/spatial.py` vs `disasters/spatial_index.py` - relationship unclear
- Supernova scheduler integration with actual hazard evaluation not fully documented
- GRB and NSM scheduling not implemented (only SN scheduler exists)
