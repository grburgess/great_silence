"""Configuration for Three.js visualization system."""

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
    lod_near_distance: float = 5.0
    lod_far_distance: float = 15.0
    enable_procedural_civ_models: bool = True
    frame_duration_ms: int = 50
    default_playback_speed: float = 1.0
    min_playback_speed: float = 0.1
    max_playback_speed: float = 10.0

    include_threejs_bundle: bool = True
    data_embed_threshold_mb: float = 10.0

    def to_dict(self) -> dict:
        """Convert config to dict for JSON serialization."""
        return {
            "camera_position": self.camera_position,
            "camera_fov": self.camera_fov,
            "camera_near": self.camera_near,
            "camera_far": self.camera_far,
            "enable_damping": self.enable_damping,
            "damping_factor": self.damping_factor,
            "enable_zoom": self.enable_zoom,
            "auto_rotate": self.auto_rotate,
            "auto_rotate_speed": self.auto_rotate_speed,
            "background_color": self.background_color,
            "star_point_size": self.star_point_size,
            "star_opacity": self.star_opacity,
            "civ_active_size": self.civ_active_size,
            "civ_active_opacity": self.civ_active_opacity,
            "civ_extinct_size": self.civ_extinct_size,
            "civ_extinct_opacity": self.civ_extinct_opacity,
            "civ_extinct_color": self.civ_extinct_color,
            "kardashev_colorscale": self.kardashev_colorscale,
            "kardashev_min": self.kardashev_min,
            "kardashev_max": self.kardashev_max,
            "glow_threshold": self.glow_threshold,
            "glow_intensity": self.glow_intensity,
            "death_marker_size": self.death_marker_size,
            "death_colors": self.death_colors,
            "hazard_supernova_color": self.hazard_supernova_color,
            "hazard_grb_color": self.hazard_grb_color,
            "hazard_nsm_color": self.hazard_nsm_color,
            "hazard_marker_size": self.hazard_marker_size,
            "hazard_opacity": self.hazard_opacity,
            "shockwave_duration_myr": self.shockwave_duration_myr,
            "sterilization_zone_opacity": self.sterilization_zone_opacity,
            "disaster_fade_time_myr": self.disaster_fade_time_myr,
            "probe_trail_length": self.probe_trail_length,
            "probe_glow_enabled": self.probe_glow_enabled,
            "trajectory_width": self.trajectory_width,
            "trajectory_opacity": self.trajectory_opacity,
            "trajectory_fade_window_myr": self.trajectory_fade_window_myr,
            "sphere_opacity": self.sphere_opacity,
            "sphere_segments": self.sphere_segments,
            "sphere_color": self.sphere_color,
            "sphere_growth_window_myr": self.sphere_growth_window_myr,
            "interpolation_factor": self.interpolation_factor,
            "frame_duration_ms": self.frame_duration_ms,
            "default_playback_speed": self.default_playback_speed,
            "min_playback_speed": self.min_playback_speed,
            "max_playback_speed": self.max_playback_speed,
            "include_threejs_bundle": self.include_threejs_bundle,
            "data_embed_threshold_mb": self.data_embed_threshold_mb,
        }
