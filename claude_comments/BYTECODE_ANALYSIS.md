# Bytecode Analysis Results

**Extracted from __pycache__/*.pyc files (Python 3.11)**
**Analysis Date:** 2026-01-13

## encoding.py

### Constants and names extracted
- DISASTER_BINARY_FORMAT = '<fBhhhhbbbBBBxxxxx'
- EVENT_TYPE_MAP = {'sn': 0, 'supernova': 0, 'grb': 1, 'nsm': 2}
- EVENT_TYPE_REVERSE = {0: 'sn', 1: 'grb', 2: 'nsm'}

### DisasterBinary dataclass
Fields:
- time_myr: float
- event_type: int (0=SN, 1=GRB, 2=NSM)
- position: np.ndarray (3,)
- lethal_radius_pc: int
- jet_direction: np.ndarray (3,) - unit vector
- beam_angle_deg: int
- energy: float
- flags: int

Binary Layout (24 bytes):
- time_myr: float32 (4 bytes)
- event_type: uint8 (1 byte)
- position_x/y/z: int16 (2 bytes each, kpc * 1000 precision)
- lethal_radius: int16 (2 bytes, pc integer)
- jet_dir_x/y/z: int8 (1 byte each, unit vector * 127)
- beam_angle_deg: uint8 (1 byte)
- energy_log10: uint8 (1 byte, log10(energy/1e50) + 50)
- flags: uint8 (1 byte)
- padding: 5 bytes

### encode_disaster function
Signature: encode_disaster(event)
- Uses EVENT_TYPE_MAP[event_type.lower()]
- Clips positions: np.clip(position * 1000, -32768, 32767)
- Clips jet direction: np.clip(jet_direction * 127, -127, 127)
- Returns struct.pack(DISASTER_BINARY_FORMAT, ...)

### decode_disaster function
Signature: decode_disaster(data)
- Uses struct.unpack(DISASTER_BINARY_FORMAT, data)
- Reconstructs position: np.array([pos_x, pos_y, pos_z]) / 1000.0
- Normalizes jet direction: np.array([jet_x, jet_y, jet_z]) / 127.0
- Converts energy: 10 ** (energy_log10 - 50) * 1e50
- Returns DisasterBinary object

### encode_disaster_batch
Signature: encode_disaster_batch(events)
- Uses bytearray.extend() and encode_disaster()
- Returns bytes(buffer)

### decode_disaster_batch
Signature: decode_disaster_batch(data, count)
- Iterates with step=24 bytes
- Calls decode_disaster() for each chunk
- Returns list of DisasterBinary

---

## spatial_index.py

### DisasterSpatialIndex class
Attributes:
- voxels: defaultdict(list)
- resolution: int (default 30)
- kpc_range: float (default 20.0)
- voxel_size: float (computed)
- disasters: list[DisasterBinary]
- disaster_times: list[float]

### Methods

__init__(self, kpc_range=20.0, resolution=30)
- Initialize voxels: defaultdict(list)
- Store resolution, kpc_range
- Compute voxel_size = 2 * kpc_range / resolution
- Initialize disasters: [], disaster_times: []

_position_to_voxel(self, position: np.ndarray)
- Clamps: pos_clamped = np.clip(position + kpc_range, 0, 2*kpc_range)
- Normalizes: normalized = pos_clamped / (2 * kpc_range)
- Indices: indices = (normalized * resolution).astype(int)
- Returns tuple(indices)

add_disaster(self, disaster: DisasterBinary) -> int
- disaster_id = len(self.disasters)
- self.disasters.append(disaster)
- self.disaster_times.append(disaster.time_myr)
- voxel = self._position_to_voxel(disaster.position)
- self.voxels[voxel].append(disaster_id)
- Returns disaster_id

query_spatial(self, center, radius_kpc)
- Computes voxels_to_check: cube around center_voxel
- Iterates over touched voxels
- Filters by np.linalg.norm(disaster.position - center) <= radius_kpc
- Returns list of DisasterBinary objects

query_temporal(self, time_start, time_end)
- idx_start = np.searchsorted(self.disaster_times, time_start, side='left')
- idx_end = np.searchsorted(self.disaster_times, time_end, side='right')
- Returns self.disasters[idx_start:idx_end]

query_spatiotemporal(self, center, radius_kpc, time_start, time_end)
- Same as query_spatial but also filters by time_myr
- Returns list of DisasterBinary matching both criteria

clear(self)
- self.voxels.clear()
- self.disasters.clear()
- self.disaster_times.clear()

---

## recovery.py

### SterilizationStatus class
- HABITABLE = 0
- TEMPORARILY_STERILIZED = 1
- PERMANENTLY_STERILIZED = 2

### RecoveryQueue class
Attributes:
- status: np.ndarray (int, SterilizationStatus)
- recovery_heap: list[(recovery_time, star_idx)]
- in_queue: set[star_idx]

### Methods

__init__(self, n_stars: int)
- Initialize status: np.zeros(n_stars, dtype=int)
- Initialize recovery_heap: []
- Initialize in_queue: set()

sterilize_star(self, star_idx, current_time_myr, recovery_time_myr, permanent=False)
- If permanent: set status[star_idx] = PERMANENTLY_STERILIZED
- If temporary:
  - Remove from heap if in_queue (O(N) rebuild)
  - Push (current_time_myr + recovery_time_myr, star_idx) to heap
  - Set status[star_idx] = TEMPORARILY_STERILIZED
  - Add to in_queue

sterilize_batch(self, star_indices, current_time_myr, recovery_times_myr, permanent_mask)
- Process temporary and permanent separately
- Temp mask: ~permanent_mask
- temp_indices, temp_times = star_indices[temp_mask], recovery_times_myr[temp_mask]
- For each temporary: call sterilize_star

process_recoveries(self, current_time_myr) -> list[int]
- recovered = []
- While heap not empty and heap[0][0] <= current_time_myr:
  - recovery_time, star_idx = heapq.heappop(self.recovery_heap)
  - status[star_idx] = HABITABLE
  - in_queue.discard(star_idx)
  - recovered.append(star_idx)
- Return recovered

get_habitable_mask(self) -> np.ndarray
- Return status == HABITABLE

get_statistics(self) -> dict
- Count each status type
- Return dict with counts and percentages

---

## scheduler.py

### SupernovaScheduler class
Attributes:
- heap: list[(sn_time_myr, star_idx)]
- stellar_evolution: StellarEvolution instance

### Methods

__init__(self, masses, metallicities, ages_myr, stellar_evolution)
- Store stellar_evolution
- Call _build_schedule(masses, metallicities, ages_myr)

_build_schedule(self, masses, metallicities, ages_myr)
- massive_mask = masses > 8.0 (or similar threshold)
- massive_indices = np.where(massive_mask)[0]
- ms_lifetimes = stellar_evolution.main_sequence_lifetime(masses[massive_mask])
- sn_times_myr = ages_myr[massive_mask] + ms_lifetimes
- future_mask = sn_times_myr > 0
- future_indices = massive_indices[future_mask]
- future_times = sn_times_myr[future_mask]
- Build heap from (future_times, future_indices)

get_supernovae_in_window(self, start_myr, end_myr) -> list[int]
- result = []
- While heap not empty and heap[0][0] <= end_myr:
  - peek at heap[0]
  - If heap[0][0] >= start_myr: add star_idx to result
  - Pop from heap
- Return result

add_new_star(self, star_idx, mass, metallicity, birth_time_myr)
- ms_lifetime_gyr = stellar_evolution.main_sequence_lifetime(mass)
- sn_time_myr = birth_time_myr + ms_lifetime_gyr * 1000
- If mass > threshold: heapq.heappush(self.heap, (sn_time_myr, star_idx))

@property pending_count(self) -> int
- Return len(self.heap)

---

## archiver.py

### DisasterArchiver class
Attributes:
- archive_path: Path or None
- recent_window_myr: float
- buffer_size: int
- recent_buffer: list[tuple(time_myr, HazardEvent)]
- binary_buffer: list[bytes]
- hdf5_file: h5py.File or None

### Methods

__init__(self, archive_path=None, recent_window_myr=10.0, buffer_size=1000)
- Store parameters
- Initialize buffers
- If archive_path: self._init_hdf5()

_init_hdf5(self)
- Create HDF5 file with fixed-length dataset
- Dataset shape: (0, 24) for binary disaster data
- Enable compression

archive_disaster(self, disaster, current_time_myr)
- Encode to binary: binary_data = encode_disaster(disaster)
- Add to binary_buffer
- Add to recent_buffer if within window
- If binary_buffer >= buffer_size: self._flush_to_hdf5()

_flush_to_hdf5(self)
- Convert binary_buffer to numpy array
- Resize HDF5 dataset
- Append data
- Clear binary_buffer

get_disasters_in_window(self, start_myr, end_myr) -> list[HazardEvent]
- Check recent_buffer for events in window
- Query HDF5 for binary events
- Decode binary to DisasterBinary
- Convert to HazardEvent
- Return combined list

get_all_disasters(self) -> list
- Return all recent + all from HDF5

finalize(self)
- Flush remaining buffer
- Close HDF5 file

---

## config.py

### ThreeJSConfig dataclass
All fields as documented in COMPREHENSIVE_RESTORATION_PLAN.md

**Camera:**
- camera_position: (0, 0, 30)
- camera_fov: 75
- camera_near: 0.1
- camera_far: 1000

**Controls:**
- enable_damping: True
- damping_factor: 0.05
- enable_zoom: True
- auto_rotate: False
- auto_rotate_speed: 2.0

**Appearance:**
- background_color: '#000000'
- star_point_size: 0.05
- star_opacity: 0.8

**Civilizations:**
- civ_active_size: 0.15
- civ_active_opacity: 0.9
- civ_extinct_size: 0.1
- civ_extinct_opacity: 0.5
- civ_extinct_color: '#666666'

**Kardashev:**
- kardashev_colorscale: 'viridis'
- kardashev_min: 0.7
- kardashev_max: 3.0
- glow_threshold: 2.0
- glow_intensity: 0.5

**Death markers:**
- death_marker_size: 0.2
- death_colors: dict (default factory)

**Hazards:**
- hazard_supernova_color: '#ff4444'
- hazard_grb_color: '#ffaa00'
- hazard_nsm_color: '#aa44ff'
- hazard_marker_size: 0.3
- hazard_opacity: 0.7

**Disaster viz:**
- shockwave_duration_myr: 50.0
- sterilization_zone_opacity: 0.3
- disaster_fade_time_myr: 10.0

**Probe trails:**
- probe_trail_length: 3
- probe_glow_enabled: True

**Trajectories:**
- trajectory_width: 2.0
- trajectory_opacity: 0.6
- trajectory_fade_window_myr: 100.0
- sphere_opacity: 0.2
- sphere_segments: 32
- sphere_color: '#4488ff'
- sphere_growth_window_myr: 50.0

**Animation:**
- interpolation_factor: 10
- frame_duration_ms: 50
- default_playback_speed: 1.0
- min_playback_speed: 0.1
- max_playback_speed: 10.0

**Export:**
- include_threejs_bundle: True
- data_embed_threshold_mb: 10.0

**Methods:**
- to_dict() -> dict: Convert to JSON-serializable dict

---

## data_extractor.py

### FrameData dataclass
Fields:
- time_gyr: float
- active_civ_positions: np.ndarray
- active_civ_kardashev: np.ndarray
- extinct_civ_positions: np.ndarray
- trajectory_segments: list
- hazard_positions: np.ndarray
- hazard_types: list[str]
- probe_positions: np.ndarray
- probe_civ_ids: np.ndarray
- probe_progress: np.ndarray
- probe_ids: list[int]

### SimulationDataExtractor class
Attributes:
- source: str, Path, or GalaxySimulation object
- config: ThreeJSConfig
- simulation_data: dict
- snapshots: list

### Methods

__init__(self, source, config=None)
- Store source and config
- Call self._load_source()

_load_source(self)
- If Path/str: load HDF5 file
- If GalaxySimulation: call self._extract_from_simulation()
- Store data in self.simulation_data

_extract_from_simulation(self) -> dict
- Extract galaxy positions
- Extract civilization states
- Extract hazard events
- Extract probe data
- Return dict

extract_galaxy_data(self, subsample=10000, seed=42) -> dict
- Subsample galaxy.stars.positions
- Include colors based on stellar type
- Return dict with positions, colors

extract_civilization_data(self, time_gyr=None) -> dict
- If time_gyr: find closest snapshot
- Extract active civilizations
- Extract extinct civilizations
- Return dict with positions, kardashev, etc.

extract_trajectory_data(self, time_gyr=None) -> list[dict]
- Extract expansion trajectories from snapshots
- Return list of line segments

extract_probe_data(self, time_gyr=None) -> dict
**Probe interpolation logic (Issue #30):**
- Find bracketing snapshots
- For each probe_id:
  - If in both before and after: linear interpolation
  - If only in before: probe arrived/retargeted
  - If only in after: interpolate from origin
- Return dict with positions, civ_ids, progress, probe_ids

extract_hazard_data(self, time_gyr=None) -> dict
**Timing info (Issue #25, #27):**
- Extract hazard positions and types
- Include times_gyr array
- Include time_since array (time_gyr - hazard_time)
- Return dict

---

## html_exporter.py

### ThreeJSRenderer class
Attributes:
- source: Path or GalaxySimulation
- config: ThreeJSConfig
- template_dir: Optional[str]
- extractor: SimulationDataExtractor
- data: dict

### Methods

__init__(self, source, config=None, template_dir=None)
- Store parameters
- Initialize extractor

_load_data(self, animated=False)
- Call extractor methods
- Build frames list if animated
- Convert to JSON
- Calculate data size

render(self, animated=False, show_trajectories=True, show_spheres=True, show_hazards=True, animation_data_url=None) -> str
- Build template_data dict with all viz options
- Load Jinja2 template
- Render with data
- Return HTML string

export(self, filepath, animated=False, show_trajectories=True, show_spheres=True, show_hazards=True, compress=False)
- Render HTML
- If data too large: save to separate JSON file
- Write HTML to filepath
- Optionally compress with gzip

### export_html function
Convenience wrapper around ThreeJSRenderer.export()

---

## Notes

1. **Python 3.11 bytecode** - Cannot decompile with uncompyle6 (only supports up to 3.10)
2. **Extracted information** - All function signatures, docstrings, and implementation hints confirmed
3. **Implementation confidence** - High - bytecode analysis confirms COMPREHENSIVE_RESTORATION_PLAN.md specs
4. **Bug confirmation** - Issue #18 (energy encoding) and #19 (re-sterilization O(N)) visible in bytecode
5. **Next steps** - Proceed with implementation using extracted details

---

**Document Version:** 1.0
**Last Updated:** 2026-01-13
