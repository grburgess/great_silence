"""
Tests for path-dependent development tracking system.
"""

import pytest
import numpy as np
from great_silence.civilization.development_path import (
    DevelopmentSnapshot,
    DevelopmentHistory,
    DevelopmentTracker,
    format_development_summary
)


class TestDevelopmentSnapshot:
    """Tests for DevelopmentSnapshot dataclass."""

    def test_creation(self):
        """Test creating development snapshot."""
        snapshot = DevelopmentSnapshot(
            time_myr=1000.0,
            kardashev_level=0.85,
            maturity_level=0.75,
            development_velocity=0.05
        )

        assert snapshot.time_myr == 1000.0
        assert snapshot.kardashev_level == 0.85
        assert snapshot.maturity_level == 0.75
        assert snapshot.development_velocity == 0.05


class TestDevelopmentHistory:
    """Tests for DevelopmentHistory dataclass."""

    def test_creation(self):
        """Test creating development history."""
        snapshot1 = DevelopmentSnapshot(1000.0, 0.7, 0.6, 0.05)
        snapshot2 = DevelopmentSnapshot(1100.0, 0.75, 0.65, 0.05)

        history = DevelopmentHistory(
            snapshots=[snapshot1, snapshot2],
            emergence_time_myr=1000.0,
            current_development_phase="nascent"
        )

        assert len(history.snapshots) == 2
        assert history.emergence_time_myr == 1000.0
        assert history.current_development_phase == "nascent"

    def test_get_average_velocity_all_time(self):
        """Test calculating average velocity over all time."""
        snapshots = [
            DevelopmentSnapshot(1000.0, 0.7, 0.6, 0.05),
            DevelopmentSnapshot(1100.0, 0.75, 0.65, 0.05),
            DevelopmentSnapshot(1200.0, 0.80, 0.70, 0.05)
        ]

        history = DevelopmentHistory(snapshots=snapshots)

        avg_velocity = history.get_average_velocity()

        assert avg_velocity == pytest.approx(0.05, abs=0.001)

    def test_get_average_velocity_windowed(self):
        """Test calculating average velocity in time window."""
        snapshots = [
            DevelopmentSnapshot(1000.0, 0.7, 0.6, 0.05),
            DevelopmentSnapshot(1100.0, 0.75, 0.65, 0.10),  # Faster
            DevelopmentSnapshot(1200.0, 0.85, 0.70, 0.10)   # Faster
        ]

        history = DevelopmentHistory(snapshots=snapshots)

        # Recent window should show higher velocity
        recent_avg = history.get_average_velocity(window_myr=150.0)

        assert recent_avg == 0.10

    def test_get_average_velocity_insufficient_data(self):
        """Test average velocity with insufficient data."""
        snapshot = DevelopmentSnapshot(1000.0, 0.7, 0.6, 0.05)
        history = DevelopmentHistory(snapshots=[snapshot])

        avg_velocity = history.get_average_velocity()

        assert avg_velocity == 0.0

    def test_get_velocity_trend_accelerating(self):
        """Test detecting acceleration trend."""
        snapshots = [
            DevelopmentSnapshot(1000.0, 0.70, 0.6, 0.03),
            DevelopmentSnapshot(1050.0, 0.715, 0.61, 0.04),
            DevelopmentSnapshot(1100.0, 0.73, 0.63, 0.05),
            DevelopmentSnapshot(1150.0, 0.76, 0.65, 0.06),
            DevelopmentSnapshot(1200.0, 0.79, 0.67, 0.07)
        ]

        history = DevelopmentHistory(snapshots=snapshots)

        trend = history.get_velocity_trend(window_myr=250.0)

        # Trend should be positive (accelerating)
        assert trend > 0

    def test_get_velocity_trend_decelerating(self):
        """Test detecting deceleration trend."""
        snapshots = [
            DevelopmentSnapshot(1000.0, 0.70, 0.6, 0.07),
            DevelopmentSnapshot(1050.0, 0.765, 0.62, 0.06),
            DevelopmentSnapshot(1100.0, 0.82, 0.64, 0.05),
            DevelopmentSnapshot(1150.0, 0.86, 0.65, 0.04),
            DevelopmentSnapshot(1200.0, 0.89, 0.66, 0.03)
        ]

        history = DevelopmentHistory(snapshots=snapshots)

        trend = history.get_velocity_trend(window_myr=250.0)

        # Trend should be negative (decelerating)
        assert trend < 0

    def test_to_dict_and_from_dict(self):
        """Test serialization."""
        snapshots = [
            DevelopmentSnapshot(1000.0, 0.7, 0.6, 0.05),
            DevelopmentSnapshot(1100.0, 0.75, 0.65, 0.05)
        ]

        original = DevelopmentHistory(
            snapshots=snapshots,
            emergence_time_myr=1000.0,
            current_development_phase="nascent",
            acceleration_events=[1150.0],
            stagnation_periods=[(1050.0, 1080.0)]
        )

        data = original.to_dict()
        restored = DevelopmentHistory.from_dict(data)

        assert len(restored.snapshots) == len(original.snapshots)
        assert restored.emergence_time_myr == original.emergence_time_myr
        assert restored.current_development_phase == original.current_development_phase
        assert restored.acceleration_events == original.acceleration_events


class TestDevelopmentTracker:
    """Tests for DevelopmentTracker."""

    def test_initialization(self):
        """Test creating development tracker."""
        tracker = DevelopmentTracker(seed=42)

        assert tracker.snapshot_interval_myr == 10.0
        assert tracker.velocity_smoothing_window == 3
        assert tracker.rng is not None

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        tracker = DevelopmentTracker(
            snapshot_interval_myr=20.0,
            velocity_smoothing_window=5,
            seed=42
        )

        assert tracker.snapshot_interval_myr == 20.0
        assert tracker.velocity_smoothing_window == 5

    def test_initialize_history(self):
        """Test initializing development history."""
        tracker = DevelopmentTracker(seed=42)

        history = tracker.initialize_history(
            emergence_time_myr=1000.0,
            initial_kardashev=0.72,
            initial_maturity=0.65
        )

        assert len(history.snapshots) == 1
        assert history.snapshots[0].kardashev_level == 0.72
        assert history.snapshots[0].maturity_level == 0.65
        assert history.emergence_time_myr == 1000.0
        assert history.current_development_phase == "nascent"

    def test_classify_phase(self):
        """Test development phase classification."""
        tracker = DevelopmentTracker()

        assert tracker._classify_phase(0.5) == "nascent"
        assert tracker._classify_phase(0.9) == "industrial"
        assert tracker._classify_phase(1.5) == "interplanetary"
        assert tracker._classify_phase(2.5) == "interstellar"

    def test_update_history_no_snapshot_yet(self):
        """Test update when snapshot interval not reached."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        history = tracker.initialize_history(1000.0, 0.7, 0.6)

        # Update after only 5 Myr (less than interval)
        updated = tracker.update_history(history, 1005.0, 0.72, 0.61)

        # Should still only have 1 snapshot
        assert len(updated.snapshots) == 1

    def test_update_history_creates_snapshot(self):
        """Test update creates snapshot after interval."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        history = tracker.initialize_history(1000.0, 0.7, 0.6)

        # Update after 10 Myr
        updated = tracker.update_history(history, 1010.0, 0.75, 0.62)

        # Should now have 2 snapshots
        assert len(updated.snapshots) == 2
        assert updated.snapshots[1].kardashev_level == 0.75

    def test_update_history_calculates_velocity(self):
        """Test velocity calculation in update."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        history = tracker.initialize_history(1000.0, 0.7, 0.6)
        updated = tracker.update_history(history, 1010.0, 0.75, 0.62)

        # Velocity should be dk/dt = (0.75 - 0.7) / 10 = 0.005
        assert updated.snapshots[1].development_velocity == pytest.approx(0.005, abs=0.001)

    def test_update_history_updates_phase(self):
        """Test phase update when crossing threshold."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        # Start in nascent phase
        history = tracker.initialize_history(1000.0, 0.75, 0.6)
        assert history.current_development_phase == "nascent"

        # Advance to industrial phase
        updated = tracker.update_history(history, 1010.0, 0.85, 0.65)

        assert updated.current_development_phase == "industrial"

    def test_is_acceleration_event_detects_acceleration(self):
        """Test acceleration event detection."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        # Build history with slow development
        history = tracker.initialize_history(1000.0, 0.7, 0.6)
        history = tracker.update_history(history, 1010.0, 0.71, 0.61)  # v=0.01
        history = tracker.update_history(history, 1020.0, 0.72, 0.62)  # v=0.01

        # Check if high velocity is detected as acceleration
        is_accel = tracker._is_acceleration_event(history, 0.15)  # Much faster

        assert is_accel

    def test_is_stagnation_detects_stagnation(self):
        """Test stagnation detection."""
        tracker = DevelopmentTracker()

        history = tracker.initialize_history(1000.0, 0.7, 0.6)

        # Very low velocity
        is_stagnant = tracker._is_stagnation(history, 0.005)

        assert is_stagnant

    def test_classify_development_path_fast(self):
        """Test classifying fast development path."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        # Create fast development snapshots manually (need >0.10 K/Myr avg)
        snapshots = [
            DevelopmentSnapshot(1000.0, 0.7, 0.6, 0.12),
            DevelopmentSnapshot(1010.0, 1.9, 0.7, 0.12),
            DevelopmentSnapshot(1020.0, 3.1, 0.8, 0.12),
            DevelopmentSnapshot(1030.0, 4.3, 0.9, 0.12)
        ]

        history = DevelopmentHistory(
            snapshots=snapshots,
            emergence_time_myr=1000.0,
            current_development_phase="interstellar"
        )

        path_type = tracker.classify_development_path(history)

        assert path_type == "fast"

    def test_classify_development_path_slow(self):
        """Test classifying slow development path."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        history = tracker.initialize_history(1000.0, 0.7, 0.6)

        # Create slow development snapshots
        for i in range(5):
            time = 1000.0 + (i + 1) * 10.0
            kardashev = 0.7 + (i + 1) * 0.02  # Slow growth
            maturity = 0.6 + (i + 1) * 0.02
            history = tracker.update_history(history, time, kardashev, maturity)

        path_type = tracker.classify_development_path(history)

        assert path_type == "slow"

    def test_classify_development_path_balanced(self):
        """Test classifying balanced development path."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        history = tracker.initialize_history(1000.0, 0.7, 0.6)

        # Create balanced development snapshots (0.03 < velocity < 0.10)
        # With dt=10 Myr, need 0.3 < dK < 1.0 per step
        for i in range(5):
            time = 1000.0 + (i + 1) * 10.0
            kardashev = 0.7 + (i + 1) * 0.5  # velocity = 0.5/10 = 0.05 K/Myr
            maturity = 0.6 + (i + 1) * 0.04
            history = tracker.update_history(history, time, kardashev, maturity)

        path_type = tracker.classify_development_path(history)

        assert path_type == "balanced"

    def test_classify_development_path_insufficient_data(self):
        """Test classification with insufficient data."""
        tracker = DevelopmentTracker()

        history = tracker.initialize_history(1000.0, 0.7, 0.6)

        path_type = tracker.classify_development_path(history)

        assert path_type == "insufficient_data"

    def test_calculate_crisis_timing_modifier_fast_development(self):
        """Test crisis timing for fast development."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        # Build fast development history manually
        snapshots = [
            DevelopmentSnapshot(1000.0, 0.7, 0.6, 0.12),
            DevelopmentSnapshot(1010.0, 1.9, 0.7, 0.12),
            DevelopmentSnapshot(1020.0, 3.1, 0.8, 0.12),
            DevelopmentSnapshot(1030.0, 4.3, 0.9, 0.12)
        ]

        history = DevelopmentHistory(
            snapshots=snapshots,
            emergence_time_myr=1000.0,
            current_development_phase="interstellar"
        )

        modifier = tracker.calculate_crisis_timing_modifier(history)

        # Fast development → crises earlier (negative modifier)
        assert modifier < 0

    def test_calculate_crisis_timing_modifier_slow_development(self):
        """Test crisis timing for slow development."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        # Build slow development history
        history = tracker.initialize_history(1000.0, 0.7, 0.6)
        for i in range(5):
            time = 1000.0 + (i + 1) * 10.0
            kardashev = 0.7 + (i + 1) * 0.02
            maturity = 0.6 + (i + 1) * 0.02
            history = tracker.update_history(history, time, kardashev, maturity)

        modifier = tracker.calculate_crisis_timing_modifier(history)

        # Slow development → crises later (positive modifier)
        assert modifier > 0

    def test_calculate_development_risk_modifier_fast_risky(self):
        """Test that fast development is riskier."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        # Build fast development history manually
        snapshots = [
            DevelopmentSnapshot(1000.0, 0.7, 0.6, 0.12),
            DevelopmentSnapshot(1010.0, 1.9, 0.7, 0.12),
            DevelopmentSnapshot(1020.0, 3.1, 0.8, 0.12),
            DevelopmentSnapshot(1030.0, 4.3, 0.9, 0.12)
        ]

        history = DevelopmentHistory(
            snapshots=snapshots,
            emergence_time_myr=1000.0,
            current_development_phase="interstellar"
        )

        modifier = tracker.calculate_development_risk_modifier(history)

        # Fast development should have penalty (< 1.0)
        assert modifier < 1.0

    def test_calculate_development_risk_modifier_slow_safer(self):
        """Test that slow development is safer."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        # Build slow development history
        history = tracker.initialize_history(1000.0, 0.7, 0.6)
        for i in range(5):
            time = 1000.0 + (i + 1) * 10.0
            kardashev = 0.7 + (i + 1) * 0.02
            maturity = 0.6 + (i + 1) * 0.02
            history = tracker.update_history(history, time, kardashev, maturity)

        modifier = tracker.calculate_development_risk_modifier(history)

        # Slow development should have bonus (> 1.0)
        assert modifier > 1.0

    def test_calculate_development_risk_modifier_balanced_neutral(self):
        """Test that balanced development is neutral."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        # Build balanced development history (0.03 < velocity < 0.10)
        history = tracker.initialize_history(1000.0, 0.7, 0.6)
        for i in range(5):
            time = 1000.0 + (i + 1) * 10.0
            kardashev = 0.7 + (i + 1) * 0.5  # velocity = 0.05 K/Myr
            maturity = 0.6 + (i + 1) * 0.04
            history = tracker.update_history(history, time, kardashev, maturity)

        modifier = tracker.calculate_development_risk_modifier(history)

        # Balanced should be neutral (1.0)
        assert modifier == 1.0


class TestDevelopmentSummaries:
    """Tests for development summary formatting."""

    def test_format_development_summary_insufficient_data(self):
        """Test summary with insufficient data."""
        tracker = DevelopmentTracker()
        history = tracker.initialize_history(1000.0, 0.7, 0.6)

        summary = format_development_summary(history, tracker)

        assert "Insufficient data" in summary

    def test_format_development_summary_with_data(self):
        """Test summary with sufficient data."""
        tracker = DevelopmentTracker(snapshot_interval_myr=10.0)

        # Create balanced development snapshots manually
        snapshots = [
            DevelopmentSnapshot(1000.0, 0.7, 0.6, 0.05),
            DevelopmentSnapshot(1010.0, 1.2, 0.64, 0.05),
            DevelopmentSnapshot(1020.0, 1.7, 0.68, 0.05),
            DevelopmentSnapshot(1030.0, 2.2, 0.72, 0.05)
        ]

        history = DevelopmentHistory(
            snapshots=snapshots,
            emergence_time_myr=1000.0,
            current_development_phase="interstellar"
        )

        summary = format_development_summary(history, tracker)

        assert "balanced" in summary  # Should be balanced path
        assert "K/Myr" in summary
        # Should mention some phase
        assert any(phase in summary for phase in ["nascent", "industrial", "interplanetary", "interstellar"])
