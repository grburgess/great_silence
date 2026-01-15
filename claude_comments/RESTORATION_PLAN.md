# Disaster & Probe Visualization Restoration Plan

## Overview
This document outlines the restoration of disaster visualization and probe enhancement features that were implemented on January 13, 2026 and subsequently lost during git history cleanup.

## Lost Files
### Three.js Visualization Layer
```
great_silence/visualization/threejs/
├── __init__.py
├── config.py                    [LOST]
├── data_extractor.py           [LOST]
├── html_exporter.py            [LOST]
└── templates/
    ├── layers.js.j2            [LOST]
    └── animation.js.j2         [LOST]
```

### Disaster Simulation Module
```
great_silence/simulation/disasters/
├── __init__.py
├── encoding.py                 [LOST]
├── spatial_index.py            [LOST]
├── archiver.py                [LOST]
├── recovery.py                [LOST]
└── scheduler.py               [LOST]
```

## Feature Restoration Plan

### Phase 1: Disaster Data Extension (Issue #27)
**Status**: Lost
**Description**: Add time_since and times_gyr to hazard data extraction for decay calculations

**Implementation Requirements**:
- Extend HazardSnapshot dataclass
- Add `time_since: float` field (time since disaster event in Gyr)
- Add `times_gyr: np.ndarray` field (array of event times in Gyr)
- Modify data extraction to compute these values
- Use in shockwave and sterilization calculations

**Files to Create**:
- `great_silence/simulation/disasters/encoding.py`
  - Class: `DisasterEncoder` or extend existing encoder
  - Method: `extract_hazard_times()` to get event timestamps
  - Method: `compute_time_since()` to calculate elapsed time

### Phase 2: Disaster Shockwave Layer (Issue #28)
**Status**: Lost
**Description**: Implement animated expanding rings for disaster events

**Implementation Requirements**:
- Create shockwave geometry (RingGeometry)
- Animate radius expansion over time
- Type-specific visual effects:
  - SN Type Ia: Bright blue-white rings
  - SN Type II/P: Red-orange rings with slower expansion
  - GRB: Narrow bright beams (cone geometry)
- Constant width: 2.0 kpc
- Fade out based on distance/time
- Update in `applyFrame()` method

**Files to Create**:
- `great_silence/visualization/threejs/templates/layers.js.j2`
  - Function: `createDisasterShockwaves()`
  - Function: `updateShockwaves(frame_index)`
  - Material: ShaderMaterial or MeshBasicMaterial with opacity fade
- `great_silence/visualization/threejs/data_extractor.py`
  - Method: `extract_shockwave_data()` returning positions, radii, types, times

### Phase 3: Sterilization Zone Spheres (Issue #29)
**Status**: Lost
**Description**: Add translucent spheres showing affected areas during recovery

**Implementation Requirements**:
- Create sphere geometry at disaster locations
- DoubleSide rendering for visibility from inside
- Translucent material (opacity ~0.2-0.4)
- Color coding by disaster type
- Radius matches disaster lethal radius
- Disappear when recovery period ends
- Pulsing animation during recovery

**Files to Create**:
- `great_silence/visualization/threejs/templates/layers.js.j2`
  - Function: `createSterilizationZones()`
  - Function: `updateSterilizationZones(frame_index)`
  - Material: MeshBasicMaterial with side: THREE.DoubleSide
- `great_silence/visualization/threejs/data_extractor.py`
  - Method: `extract_sterilization_data()` returning active sterilizations, radii, types

### Phase 4: Smooth Probe Interpolation (Issue #30)
**Status**: Lost
**Description**: Implement interpolation between snapshots for smooth movement

**Implementation Requirements**:
- Linear interpolation between bracketing snapshots
- Match probes by probe_id between snapshots
- Handle probe lifecycle:
  - Launched: Interpolate from launch to current snapshot
  - Arrived: Static at destination
  - Retargeted: Continue from previous position
- Return interpolated positions and progress fractions (alpha)
- Alpha clamped to [0,1] for robustness
- Fix time conversion bug
- Graceful handling of missing probe_id
- Return probe_ids for trail rendering

**Files to Create**:
- `great_silence/visualization/threejs/data_extractor.py`
  - Method: `extract_probe_data()` with interpolation logic
  - Helper: `find_bracketing_snapshots(frame_index)`
  - Helper: `interpolate_probe_position(probe_id, snapshot_before, snapshot_after, alpha)`

**Key Implementation Details** (from issue comment):
```python
def extract_probe_data(self, simulation_data, frame_index):
    # Find bracketing snapshots
    snap_before, snap_after = self.find_bracketing_snapshots(frame_index)

    # Interpolate probe positions
    for probe_id in all_probes:
        if probe_id in snap_before and probe_id in snap_after:
            # Linear interpolation
            alpha = (frame_index - snap_before.index) / (snap_after.index - snap_before.index)
            alpha = max(0, min(1, alpha))  # Clamp to [0,1]
            pos = interpolate(pos_before, pos_after, alpha)
        elif probe_id in snap_before:
            # Probe arrived or retargeted
            pos = snap_before[probe_id].position
        elif probe_id in snap_after:
            # Probe launched - interpolate from origin
            alpha = compute_launch_alpha(frame_index, snap_after.launch_time)
            pos = interpolate(origin, snap_after.position, alpha)
```

### Phase 5: Probe Trails (Issue #31)
**Status**: Lost
**Description**: Add trailing lines behind moving probes for visual feedback

**Implementation Requirements**:
- Store previous positions for trail rendering
- Create lines from previous to current position
- Trail history buffer: 3 segments per probe
- Material caching for performance
- Glow effect based on progress_fraction
- Handle probe color from parent civilization
- Update positions each frame

**Files to Create**:
- `great_silence/visualization/threejs/templates/animation.js.j2`
  - Function: `createProbeTrails()`
  - Function: `updateProbeTrails(probe_data)`
  - Data structure: Trail history buffer array
- `great_silence/visualization/threejs/data_extractor.py`
  - Return probe_ids and trail history positions

**Key Implementation Details** (from issue comment):
```javascript
// Trail history buffer
const trailHistory = {}; // probe_id -> [{x, y, z, alpha}, ...]
const TRAIL_LENGTH = 3;

function updateProbeTrails(probeData) {
    probeData.probe_ids.forEach(probe_id => {
        const pos = probeData.positions[probe_id];
        const alpha = probeData.alpha[probe_id];

        // Add current position to history
        if (!trailHistory[probe_id]) {
            trailHistory[probe_id] = [];
        }
        trailHistory[probe_id].push({x: pos.x, y: pos.y, z: pos.z, alpha: alpha});

        // Limit history length
        if (trailHistory[probe_id].length > TRAIL_LENGTH) {
            trailHistory[probe_id].shift();
        }

        // Update trail geometry
        updateTrailGeometry(probe_id, trailHistory[probe_id]);
    });
}
```

## Additional Lost Components

### Disaster Encoding Module (encoding.py)
**Purpose**: Encode disaster data for visualization and HDF5 storage

**Functions**:
- `encode_disasters(disaster_events)`: Convert disaster events to serializable format
- `decode_disasters(encoded_data)`: Deserialize disaster events
- `extract_hazard_times(snapshot)`: Extract event times from hazard data
- `compute_recovery_periods(hazards)`: Calculate recovery time for each star

### Spatial Index Module (spatial_index.py)
**Purpose**: Efficient spatial queries for disaster effects

**Classes**:
- `DisasterSpatialIndex`: KDTree for fast nearest-neighbor queries
- Methods:
  - `build_index(disaster_events)`: Build spatial index
  - `find_nearby_stars(position, radius)`: Find stars within radius
  - `query_affected_stars(disaster, lethal_radius)`: Find affected stars

### Archiver Module (archiver.py)
**Purpose**: Archive disaster events for later retrieval and analysis

**Functions**:
- `archive_disasters(events, timestamp)`: Store disaster events
- `retrieve_disasters(time_range)`: Get disasters from time period
- `get_disaster_statistics()`: Compute aggregate statistics

### Recovery Module (recovery.py)
**Purpose**: Track recovery from disasters

**Classes**:
- `RecoveryTracker`: Monitor recovery progress
- Methods:
  - `initialize_recovery(star_id, disaster_type, duration)`: Start recovery
  - `update_recovery(dt)`: Advance recovery time
  - `is_recovered(star_id)`: Check if star has recovered
  - `get_recovery_progress(star_id)`: Get recovery fraction [0,1]

### Scheduler Module (scheduler.py)
**Purpose**: Schedule disaster events in time

**Classes**:
- `DisasterScheduler`: Manage disaster event timing
- Methods:
  - `schedule_disaster(event, time)`: Add event to queue
  - `get_next_disaster(current_time)`: Get next upcoming event
  - `process_events(dt)`: Process events in time step

### Three.js Config Module (config.py)
**Purpose**: Configuration for three.js visualization

**Configuration Items**:
- Shockwave expansion rates by disaster type
- Material colors and opacities
- Trail length and segment count
- Sterilization zone opacity
- Animation speeds

### HTML Exporter Module (html_exporter.py)
**Purpose**: Export visualization as self-contained HTML

**Functions**:
- `export_html(data, template)`: Generate HTML from template
- `embed_data(data)`: Embed JSON data in HTML
- `generate_animation_frame(data, frame_index)`: Generate single frame

## Integration Requirements

### Three.js Initialization
- Create disaster layers in `initLayers()`
- Create probe trail layer in `initLayers()`
- Add all layers to scene

### Three.js Animation Loop
- `applyFrame(frame_index)`:
  1. Update shockwave radii
  2. Update sterilization zone visibility (based on recovery)
  3. Update probe positions (interpolated)
  4. Update probe trails

### Data Extraction Pipeline
- From HDF5 snapshots:
  1. Extract hazard events with times
  2. Extract probe positions with timestamps
  3. Extract active recoveries
  4. Compute interpolated positions for current frame
  5. Package data for three.js

## Recovery Priority

1. **CRITICAL**: Phase 4 (Probe Interpolation) - Foundation for trails
2. **HIGH**: Phase 2 & 3 (Disaster visualization) - Core disaster features
3. **MEDIUM**: Phase 5 (Probe Trails) - Enhances interpolation
4. **MEDIUM**: Phase 1 (Disaster Data) - Enables other disaster features
5. **LOW**: Supporting modules (encoding, spatial_index, archiver, recovery, scheduler) - Infrastructure

## Next Steps

1. Attempt bytecode decompilation from `__pycache__` files
2. Reconstruct Three.js template files from issue descriptions and patterns
3. Implement disaster data encoding based on existing patterns
4. Test integration with existing visualization pipeline

## References

- Issue #21: Phase 1 - Smooth Probe Interpolation
- Issue #22: Phase 2 - Probe Trails
- Issue #27: Phase 1 - Disaster Data Extension
- Issue #28: Phase 2 - Disaster Shockwave Layer
- Issue #29: Phase 3 - Sterilization Zone Spheres
- Issue #30: Phase 4 - Smooth Probe Interpolation
- Issue #31: Phase 5 - Probe Trails
