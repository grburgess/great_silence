"""Configuration for Three.js visualization."""

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class ThreeJSConfig:
    """Central configuration for Three.js visualization."""

    camera_position: Tuple[float, float, float] = (0, 0, 30)
    camera_fov: float = 75
    camera_near: float = 0.1
    camera_far: float = 1000

    enable_damping: bool = True
    damping_factor: float = 0.05
    enable_zoom: bool = True
    auto_rotate: bool = False
    auto_rotate_speed: float = 2.0

    background_color: str = "#000000"
    star_point_size: float = 0.05
    star_opacity: float = 0.8

    civ_active_size: float = 0.15
    civ_active_opacity: float = 0.9
    civ_extinct_size: float = 0.1
    civ_extinct_opacity: float = 0.5
    civ_extinct_color: str = "#666666"

    kardashev_colorscale: str = "viridis"
    kardashev_min: float = 0.7
    kardashev_max: float = 3.0
    glow_threshold: float = 2.0
    glow_intensity: float = 0.5

    death_marker_size: float = 0.2
    death_colors: Dict[str, str] = field(default_factory=dict)

    hazard_supernova_color: str = "#ff4444"
    hazard_grb_color: str = "#ffaa00"
    hazard_nsm_color: str = "#aa44ff"
    hazard_marker_size: float = 0.3
    hazard_opacity: float = 0.7

    shockwave_duration_myr: float = 50.0
    sterilization_zone_opacity: float = 0.3
    disaster_fade_time_myr: float = 10.0

    probe_trail_length: int = 3
    probe_glow_enabled: bool = True

    trajectory_width: float = 2.0
    trajectory_opacity: float = 0.6
    trajectory_fade_window_myr: float = 100.0
    sphere_opacity: float = 0.2
    sphere_segments: int = 32
    sphere_color: str = "#4488ff"
    sphere_growth_window_myr: float = 50.0

    interpolation_factor: int = 10
    frame_duration_ms: int = 50
    default_playback_speed: float = 1.0
    min_playback_speed: float = 0.1
    max_playback_speed: float = 10.0

    include_threejs_bundle: bool = True
    data_embed_threshold_mb: float = 10.0

    def to_dict(self) -> dict:
        """Convert config to dict for JSON serialization."""
        pass
