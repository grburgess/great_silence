"""Tests for progress tracking infrastructure."""

import pytest
import time
from great_silence.utils.progress import (
    ProgressMetrics,
    ProgressTracker,
    TqdmProgressTracker,
    JupyterProgressTracker,
    create_progress_tracker
)


class TestProgressMetrics:
    """Test ProgressMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating progress metrics."""
        metrics = ProgressMetrics(
            current_time_myr=500.0,
            total_time_myr=10000.0,
            step_count=100,
            current_dt_myr=0.1,
            active_civs=5,
            active_probes=50,
            event_queue_size=100,
            wall_time_elapsed=10.0
        )

        assert metrics.current_time_myr == 500.0
        assert metrics.total_time_myr == 10000.0
        assert metrics.step_count == 100

    def test_time_fraction(self):
        """Test time fraction calculation."""
        metrics = ProgressMetrics(
            current_time_myr=2500.0,
            total_time_myr=10000.0,
            step_count=100,
            current_dt_myr=0.1,
            active_civs=5,
            active_probes=50,
            event_queue_size=100,
            wall_time_elapsed=10.0
        )

        assert metrics.time_fraction == 0.25
        assert metrics.time_pct == 25.0

    def test_time_conversion(self):
        """Test Myr to Gyr conversion."""
        metrics = ProgressMetrics(
            current_time_myr=5000.0,
            total_time_myr=10000.0,
            step_count=100,
            current_dt_myr=0.1,
            active_civs=5,
            active_probes=50,
            event_queue_size=100,
            wall_time_elapsed=10.0
        )

        assert metrics.current_time_gyr == 5.0
        assert metrics.total_time_gyr == 10.0

    def test_iteration_rate(self):
        """Test iteration rate calculation."""
        metrics = ProgressMetrics(
            current_time_myr=1000.0,
            total_time_myr=10000.0,
            step_count=100,
            current_dt_myr=0.1,
            active_civs=5,
            active_probes=50,
            event_queue_size=100,
            wall_time_elapsed=10.0
        )

        assert metrics.iteration_rate == 10.0  # 100 steps / 10 seconds

    def test_zero_wall_time(self):
        """Test iteration rate with zero wall time."""
        metrics = ProgressMetrics(
            current_time_myr=0.0,
            total_time_myr=10000.0,
            step_count=0,
            current_dt_myr=0.1,
            active_civs=0,
            active_probes=0,
            event_queue_size=0,
            wall_time_elapsed=0.0
        )

        assert metrics.iteration_rate == 0.0


class TestTqdmProgressTracker:
    """Test CLI progress tracker."""

    def test_initialization(self):
        """Test tracker initialization."""
        tracker = TqdmProgressTracker()
        assert not tracker.started
        assert not tracker.finished

    def test_start(self):
        """Test starting progress tracker."""
        tracker = TqdmProgressTracker()
        tracker.start(10000.0)

        assert tracker.started
        assert tracker.pbar is not None

        # Clean up
        tracker.finish()

    def test_update(self):
        """Test updating progress."""
        tracker = TqdmProgressTracker()
        tracker.start(10000.0)

        metrics = ProgressMetrics(
            current_time_myr=1000.0,
            total_time_myr=10000.0,
            step_count=100,
            current_dt_myr=0.1,
            active_civs=5,
            active_probes=50,
            event_queue_size=100,
            wall_time_elapsed=10.0
        )

        tracker.update(metrics)

        # Should have updated percentage
        assert tracker.last_pct == 10.0

        # Clean up
        tracker.finish()

    def test_finish(self):
        """Test finishing progress tracker."""
        tracker = TqdmProgressTracker()
        tracker.start(10000.0)
        tracker.finish()

        assert tracker.finished

    def test_multiple_updates(self):
        """Test multiple progress updates."""
        tracker = TqdmProgressTracker()
        tracker.start(10000.0)

        # First update - 10%
        metrics1 = ProgressMetrics(
            current_time_myr=1000.0,
            total_time_myr=10000.0,
            step_count=100,
            current_dt_myr=0.1,
            active_civs=5,
            active_probes=50,
            event_queue_size=100,
            wall_time_elapsed=10.0
        )
        tracker.update(metrics1)

        # Second update - 50%
        metrics2 = ProgressMetrics(
            current_time_myr=5000.0,
            total_time_myr=10000.0,
            step_count=500,
            current_dt_myr=0.1,
            active_civs=10,
            active_probes=200,
            event_queue_size=300,
            wall_time_elapsed=50.0
        )
        tracker.update(metrics2)

        assert tracker.last_pct == 50.0

        # Clean up
        tracker.finish()


class TestJupyterProgressTracker:
    """Test Jupyter progress tracker."""

    def test_initialization(self):
        """Test tracker initialization."""
        tracker = JupyterProgressTracker()
        assert not tracker.started
        assert not tracker.finished

    def test_start_without_ipywidgets(self):
        """Test starting without ipywidgets (should fallback to tqdm)."""
        tracker = JupyterProgressTracker()

        # This will fallback to tqdm since we're not in Jupyter
        tracker.start(10000.0)

        # Should have started
        assert tracker.started

        # Clean up
        tracker.finish()

    def test_format_time(self):
        """Test time formatting."""
        # Less than 1 hour
        formatted = JupyterProgressTracker._format_time(125.0)
        assert formatted == "02:05"

        # More than 1 hour
        formatted = JupyterProgressTracker._format_time(3665.0)
        assert formatted == "01:01:05"

        # Edge cases
        formatted = JupyterProgressTracker._format_time(0.0)
        assert formatted == "00:00"


class TestProgressTrackerFactory:
    """Test progress tracker factory function."""

    def test_create_cli_tracker(self):
        """Test creating CLI tracker."""
        tracker = create_progress_tracker(environment='cli')
        assert isinstance(tracker, TqdmProgressTracker)

    def test_create_jupyter_tracker(self):
        """Test creating Jupyter tracker."""
        tracker = create_progress_tracker(environment='jupyter')
        assert isinstance(tracker, JupyterProgressTracker)

    def test_auto_detection(self):
        """Test auto-detection of environment."""
        # In test environment, should detect CLI
        tracker = create_progress_tracker(environment='auto')
        assert isinstance(tracker, TqdmProgressTracker)

    def test_with_options(self):
        """Test creating tracker with options."""
        tracker = create_progress_tracker(
            environment='cli',
            show_iteration_rate=False,
            show_probe_count=False
        )

        assert isinstance(tracker, TqdmProgressTracker)
        assert not tracker.show_iteration_rate
        assert not tracker.show_probe_count


def test_progress_tracking_overhead():
    """Test that progress tracking has minimal overhead."""
    # Create tracker
    tracker = TqdmProgressTracker()
    tracker.start(10000.0)

    # Measure update time
    start_time = time.time()
    for i in range(1000):
        metrics = ProgressMetrics(
            current_time_myr=float(i * 10),
            total_time_myr=10000.0,
            step_count=i,
            current_dt_myr=0.1,
            active_civs=5,
            active_probes=50,
            event_queue_size=100,
            wall_time_elapsed=float(i) * 0.01
        )
        tracker.update(metrics)

    elapsed = time.time() - start_time
    tracker.finish()

    # 1000 updates should take less than 1 second (overhead < 1ms per update)
    assert elapsed < 1.0, f"Progress tracking too slow: {elapsed:.3f}s for 1000 updates"
