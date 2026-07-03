"""Reactive state management for the webapp."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from great_silence.config.parameters import SimulationConfig

WEBAPP_MIN_STARS = 10_000
WEBAPP_MAX_STARS = 500_000
WEBAPP_DEFAULT_STARS = 50_000


def _webapp_safe_stars(total_stars: int) -> int:
    """The library default (100M stars) is far beyond what the webapp UI supports."""
    if WEBAPP_MIN_STARS <= total_stars <= WEBAPP_MAX_STARS:
        return total_stars
    return WEBAPP_DEFAULT_STARS


@dataclass
class SimulationEvent:
    """Represents a simulation event for the live feed."""

    time_gyr: float
    event_type: str
    description: str
    location: Optional[tuple] = None


@dataclass
class SimulationProgress:
    """Tracks simulation progress."""

    is_running: bool = False
    current_time_gyr: float = 0.0
    total_time_gyr: float = 10.0
    elapsed_seconds: float = 0.0
    active_civilizations: int = 0
    total_civilizations: int = 0
    total_extinctions: int = 0
    probes_in_flight: int = 0
    iterations_per_second: float = 0.0
    recent_events: List[SimulationEvent] = field(default_factory=list)
    is_complete: bool = False
    error_message: Optional[str] = None


class AppState:
    """Global application state with reactive updates."""

    def __init__(self):
        self.config = SimulationConfig()
        self.config.galaxy.total_stars = _webapp_safe_stars(self.config.galaxy.total_stars)
        self.progress = SimulationProgress()
        self.simulation = None
        self.results = None
        self.current_theme: str = "event_horizon"
        self._update_callbacks: List[callable] = []
        self._theme_callbacks: List[callable] = []
        self._lock = asyncio.Lock()

    def apply_preset(self, preset_name: str) -> None:
        """Apply a named preset to the configuration, preserving the user's star count."""
        total_stars = self.config.galaxy.total_stars
        self.config = SimulationConfig.with_preset(preset_name)
        self.config.galaxy.total_stars = _webapp_safe_stars(total_stars)
        self._notify_update()

    def update_galaxy_param(self, name: str, value: Any) -> None:
        """Update a galaxy parameter."""
        setattr(self.config.galaxy, name, value)
        self._notify_update()

    def update_astrophysics_param(self, name: str, value: Any) -> None:
        """Update an astrophysics parameter."""
        setattr(self.config.astrophysics, name, value)
        self._notify_update()

    def update_civilization_param(self, name: str, value: Any) -> None:
        """Update a civilization parameter."""
        setattr(self.config.civilization, name, value)
        self._notify_update()

    def update_simulation_param(self, name: str, value: Any) -> None:
        """Update a simulation parameter."""
        setattr(self.config.simulation, name, value)
        self._notify_update()

    def reset_progress(self) -> None:
        """Reset progress for a new simulation run."""
        self.progress = SimulationProgress()
        self.progress.total_time_gyr = self.config.simulation.simulation_duration_gyr
        self._notify_update()

    def add_event(self, event: SimulationEvent) -> None:
        """Add a simulation event to the feed."""
        self.progress.recent_events.insert(0, event)
        if len(self.progress.recent_events) > 50:
            self.progress.recent_events = self.progress.recent_events[:50]
        self._notify_update()

    def on_update(self, callback: callable) -> None:
        """Register a callback for state updates."""
        self._update_callbacks.append(callback)

    def on_theme_change(self, callback: callable) -> None:
        """Register a callback for theme changes."""
        self._theme_callbacks.append(callback)

    def set_theme(self, theme_name: str) -> None:
        """Set the current theme."""
        self.current_theme = theme_name
        for callback in self._theme_callbacks:
            try:
                callback(theme_name)
            except Exception:
                pass

    def _notify_update(self) -> None:
        """Notify all registered callbacks of state change."""
        for callback in self._update_callbacks:
            try:
                callback()
            except Exception:
                pass

    def get_config_dict(self) -> Dict[str, Any]:
        """Get the current configuration as a dictionary."""
        return self.config.to_dict()


app_state = AppState()
