"""
Path-dependent development tracking system.

Tracks how quickly civilizations develop technologically and how that
development speed affects their outcomes. Fast development can be dangerous
(tech outpaces wisdom), while slower development may be safer but less capable.

Key Concepts:
- Development velocity: Rate of Kardashev scale advancement
- Development acceleration: How velocity changes over time
- Path dependency: Early development speed affects later outcomes
- Crisis timing shifts based on development speed
"""

from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


@dataclass
class DevelopmentSnapshot:
    """
    Snapshot of development state at a point in time.

    Attributes:
        time_myr: Time of this snapshot
        kardashev_level: Kardashev level at this time
        maturity_level: Social maturity at this time
        development_velocity: Rate of Kardashev advancement (K/Myr)
    """
    time_myr: float
    kardashev_level: float
    maturity_level: float
    development_velocity: float


@dataclass
class DevelopmentHistory:
    """
    Historical record of civilization development.

    Tracks development trajectory to identify patterns and path dependencies.

    Attributes:
        snapshots: List of development snapshots over time
        emergence_time_myr: When civilization emerged
        current_development_phase: Current phase of development
            'nascent' (< 0.8 K), 'industrial' (0.8-1.2 K),
            'interplanetary' (1.2-2.0 K), 'interstellar' (> 2.0 K)
        acceleration_events: Times when development accelerated
        stagnation_periods: Periods of very slow development
    """
    snapshots: List[DevelopmentSnapshot] = field(default_factory=list)
    emergence_time_myr: float = 0.0
    current_development_phase: str = "nascent"
    acceleration_events: List[float] = field(default_factory=list)
    stagnation_periods: List[tuple] = field(default_factory=list)

    def get_average_velocity(self, window_myr: Optional[float] = None) -> float:
        """
        Get average development velocity.

        Args:
            window_myr: Time window to average over (None = all time)

        Returns:
            Average velocity (K/Myr)
        """
        if len(self.snapshots) < 2:
            return 0.0

        if window_myr is None:
            # Use all snapshots
            relevant = self.snapshots
        else:
            # Use recent snapshots
            cutoff_time = self.snapshots[-1].time_myr - window_myr
            relevant = [s for s in self.snapshots if s.time_myr >= cutoff_time]

        if len(relevant) < 2:
            return 0.0

        # Average the velocities
        velocities = [s.development_velocity for s in relevant]
        return float(np.mean(velocities))

    def get_velocity_trend(self, window_myr: float = 100.0) -> float:
        """
        Get development velocity trend (acceleration/deceleration).

        Args:
            window_myr: Time window for trend calculation

        Returns:
            Velocity change per Myr (positive = accelerating)
        """
        if len(self.snapshots) < 3:
            return 0.0

        cutoff_time = self.snapshots[-1].time_myr - window_myr
        relevant = [s for s in self.snapshots if s.time_myr >= cutoff_time]

        if len(relevant) < 3:
            return 0.0

        # Linear regression on velocity over time
        times = np.array([s.time_myr for s in relevant])
        velocities = np.array([s.development_velocity for s in relevant])

        # Fit line: velocity = slope * time + intercept
        slope = np.polyfit(times, velocities, 1)[0]

        return float(slope)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'snapshots': [
                {
                    'time_myr': s.time_myr,
                    'kardashev_level': s.kardashev_level,
                    'maturity_level': s.maturity_level,
                    'development_velocity': s.development_velocity
                }
                for s in self.snapshots
            ],
            'emergence_time_myr': self.emergence_time_myr,
            'current_development_phase': self.current_development_phase,
            'acceleration_events': self.acceleration_events.copy(),
            'stagnation_periods': self.stagnation_periods.copy()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DevelopmentHistory':
        """Deserialize from dictionary."""
        snapshots = [
            DevelopmentSnapshot(**s) for s in data['snapshots']
        ]
        return cls(
            snapshots=snapshots,
            emergence_time_myr=data['emergence_time_myr'],
            current_development_phase=data['current_development_phase'],
            acceleration_events=data['acceleration_events'],
            stagnation_periods=data['stagnation_periods']
        )


class DevelopmentTracker:
    """
    Tracks and analyzes civilization development paths.

    Features:
    - Velocity and acceleration tracking
    - Path classification (fast/slow/balanced)
    - Crisis timing adjustments based on development speed
    - Development phase detection
    """

    def __init__(
        self,
        snapshot_interval_myr: float = 10.0,
        velocity_smoothing_window: int = 3,
        seed: Optional[int] = None
    ):
        """
        Initialize development tracker.

        Args:
            snapshot_interval_myr: How often to save snapshots
            velocity_smoothing_window: Number of snapshots to smooth velocity over
            seed: Random seed
        """
        self.snapshot_interval_myr = snapshot_interval_myr
        self.velocity_smoothing_window = velocity_smoothing_window
        self.rng = np.random.default_rng(seed)

    def initialize_history(
        self,
        emergence_time_myr: float,
        initial_kardashev: float,
        initial_maturity: float
    ) -> DevelopmentHistory:
        """
        Initialize development history for new civilization.

        Args:
            emergence_time_myr: When civilization emerged
            initial_kardashev: Starting Kardashev level
            initial_maturity: Starting maturity level

        Returns:
            New DevelopmentHistory
        """
        initial_snapshot = DevelopmentSnapshot(
            time_myr=emergence_time_myr,
            kardashev_level=initial_kardashev,
            maturity_level=initial_maturity,
            development_velocity=0.0
        )

        return DevelopmentHistory(
            snapshots=[initial_snapshot],
            emergence_time_myr=emergence_time_myr,
            current_development_phase=self._classify_phase(initial_kardashev),
            acceleration_events=[],
            stagnation_periods=[]
        )

    def update_history(
        self,
        history: DevelopmentHistory,
        current_time_myr: float,
        current_kardashev: float,
        current_maturity: float
    ) -> DevelopmentHistory:
        """
        Update development history with current state.

        Args:
            history: Current history
            current_time_myr: Current time
            current_kardashev: Current Kardashev level
            current_maturity: Current maturity level

        Returns:
            Updated DevelopmentHistory
        """
        # Check if we should save a snapshot
        last_snapshot_time = history.snapshots[-1].time_myr
        if current_time_myr - last_snapshot_time < self.snapshot_interval_myr:
            return history

        # Calculate development velocity
        dt = current_time_myr - last_snapshot_time
        dk = current_kardashev - history.snapshots[-1].kardashev_level
        velocity = dk / dt if dt > 0 else 0.0

        # Create new snapshot
        new_snapshot = DevelopmentSnapshot(
            time_myr=current_time_myr,
            kardashev_level=current_kardashev,
            maturity_level=current_maturity,
            development_velocity=velocity
        )

        # Update snapshots
        new_snapshots = history.snapshots + [new_snapshot]

        # Update development phase
        new_phase = self._classify_phase(current_kardashev)

        # Detect acceleration events
        new_acceleration_events = history.acceleration_events.copy()
        if self._is_acceleration_event(history, velocity):
            new_acceleration_events.append(current_time_myr)

        # Detect stagnation periods
        new_stagnation_periods = history.stagnation_periods.copy()
        if self._is_stagnation(history, velocity):
            # Check if we're extending existing stagnation or starting new one
            if (new_stagnation_periods and
                current_time_myr - new_stagnation_periods[-1][1] < self.snapshot_interval_myr * 2):
                # Extend existing
                new_stagnation_periods[-1] = (new_stagnation_periods[-1][0], current_time_myr)
            else:
                # Start new stagnation period
                new_stagnation_periods.append((current_time_myr, current_time_myr))

        return DevelopmentHistory(
            snapshots=new_snapshots,
            emergence_time_myr=history.emergence_time_myr,
            current_development_phase=new_phase,
            acceleration_events=new_acceleration_events,
            stagnation_periods=new_stagnation_periods
        )

    def _classify_phase(self, kardashev: float) -> str:
        """Classify development phase based on Kardashev level."""
        if kardashev < 0.8:
            return "nascent"
        elif kardashev < 1.2:
            return "industrial"
        elif kardashev < 2.0:
            return "interplanetary"
        else:
            return "interstellar"

    def _is_acceleration_event(self, history: DevelopmentHistory, current_velocity: float) -> bool:
        """Check if current velocity represents acceleration event."""
        if len(history.snapshots) < 3:
            return False

        # Get recent average velocity
        recent_avg = history.get_average_velocity(window_myr=50.0)

        # Acceleration if current velocity is 2x recent average
        return current_velocity > 2.0 * recent_avg and current_velocity > 0.05

    def _is_stagnation(self, history: DevelopmentHistory, current_velocity: float) -> bool:
        """Check if current velocity represents stagnation."""
        # Stagnation if velocity very low
        return current_velocity < 0.01

    def classify_development_path(self, history: DevelopmentHistory) -> str:
        """
        Classify overall development path.

        Args:
            history: Development history

        Returns:
            Path classification: 'fast', 'slow', 'balanced', 'erratic'
        """
        if len(history.snapshots) < 3:
            return "insufficient_data"

        avg_velocity = history.get_average_velocity()
        velocity_trend = history.get_velocity_trend()

        # Check for erratic development (many accelerations)
        is_erratic = len(history.acceleration_events) > len(history.snapshots) / 5

        if is_erratic:
            return "erratic"

        # Classify by average velocity
        if avg_velocity > 0.10:
            return "fast"
        elif avg_velocity < 0.03:
            return "slow"
        else:
            return "balanced"

    def calculate_crisis_timing_modifier(self, history: DevelopmentHistory) -> float:
        """
        Calculate how development path affects crisis timing.

        Fast development → crises occur earlier (less time to prepare)
        Slow development → crises occur later (more time to mature)

        Args:
            history: Development history

        Returns:
            Kardashev level shift for crisis timing
                Negative = crises occur earlier
                Positive = crises occur later
        """
        path_type = self.classify_development_path(history)

        if path_type == "fast":
            return -0.15  # Crises 0.15 K-levels earlier
        elif path_type == "slow":
            return +0.10  # Crises 0.10 K-levels later
        elif path_type == "erratic":
            return -0.05  # Slightly earlier (instability)
        else:  # balanced
            return 0.0

    def calculate_development_risk_modifier(self, history: DevelopmentHistory) -> float:
        """
        Calculate crisis survival modifier based on development path.

        Fast development is riskier (tech outpaces wisdom).
        Slow development is safer (more maturity per tech level).

        Args:
            history: Development history

        Returns:
            Survival probability multiplier [0.5, 1.5]
        """
        path_type = self.classify_development_path(history)

        if path_type == "fast":
            return 0.7  # 30% penalty to survival
        elif path_type == "slow":
            return 1.3  # 30% bonus to survival
        elif path_type == "erratic":
            return 0.8  # 20% penalty (instability)
        else:  # balanced
            return 1.0


def format_development_summary(history: DevelopmentHistory, tracker: DevelopmentTracker) -> str:
    """
    Get human-readable summary of development history.

    Args:
        history: Development history
        tracker: Development tracker instance

    Returns:
        Descriptive string
    """
    if len(history.snapshots) < 2:
        return "Development history: Insufficient data"

    path_type = tracker.classify_development_path(history)
    avg_velocity = history.get_average_velocity()
    phase = history.current_development_phase

    acceleration_count = len(history.acceleration_events)
    stagnation_count = len(history.stagnation_periods)

    return (f"Development: {path_type} path ({avg_velocity:.3f} K/Myr avg), "
            f"currently {phase} phase, "
            f"{acceleration_count} acceleration events, "
            f"{stagnation_count} stagnation periods")
