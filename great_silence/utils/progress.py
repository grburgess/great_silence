"""Progress tracking for simulation runs."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProgressMetrics:
    """Snapshot of simulation progress at a given time."""

    current_time_myr: float
    total_time_myr: float
    step_count: int
    current_dt_myr: float
    active_civs: int
    active_probes: int
    event_queue_size: int
    wall_time_elapsed: float

    @property
    def time_fraction(self) -> float:
        """Calculate time fraction completed."""
        if self.total_time_myr == 0:
            return 0.0
        return self.current_time_myr / self.total_time_myr

    @property
    def time_pct(self) -> float:
        """Calculate time percentage completed."""
        return self.time_fraction * 100.0


class ProgressTracker:
    """Base progress tracker."""

    def __init__(self, total_myr: float):
        """Initialize tracker."""
        self.total_myr = total_myr
        self.current_myr = 0.0
        self.start_time = 0.0
        self.steps = 0

    def start(self, total_myr: float) -> None:
        """Start tracking."""
        self.total_myr = total_myr
        self.current_myr = 0.0
        import time
        self.start_time = time.time()

    def update(self, metrics: ProgressMetrics) -> None:
        """Update progress."""
        self.current_myr = metrics.current_time_myr
        self.steps = metrics.step_count

    def finish(self) -> None:
        """Finish tracking."""
        pass

    def _get_time_pct(self) -> float:
        """Get time percentage."""
        if self.total_myr == 0:
            return 0.0
        return (self.current_myr / self.total_myr) * 100.0


class TqdmProgressTracker(ProgressTracker):
    """Progress tracker using tqdm."""

    def __init__(self, total_myr: float):
        """Initialize with tqdm."""
        super().__init__(total_myr)
        try:
            from tqdm import tqdm
            self.pbar = tqdm(total=100, desc="Simulation")
        except ImportError:
            self.pbar = None

    def update(self, metrics: ProgressMetrics) -> None:
        """Update tqdm bar."""
        super().update(metrics)
        if self.pbar is not None:
            pct = self._get_time_pct()
            self.pbar.n = pct
            self.pbar.refresh()

    def finish(self) -> None:
        """Close tqdm bar."""
        if self.pbar is not None:
            self.pbar.close()


class JupyterProgressTracker(ProgressTracker):
    """Progress tracker for Jupyter notebooks."""

    def __init__(self, total_myr: float):
        """Initialize for Jupyter."""
        super().__init__(total_myr)
        self.widget = None

    def start(self, total_myr: float) -> None:
        """Start Jupyter widget."""
        super().start(total_myr)
        try:
            from IPython.display import display
            from ipywidgets import IntProgress, HTML, VBox
            self.widget = VBox([
                IntProgress(value=0, max=100),
                HTML(value="0.0%")
            ])
            display(self.widget)
        except ImportError:
            self.widget = None

    def update(self, metrics: ProgressMetrics) -> None:
        """Update Jupyter widget."""
        super().update(metrics)
        if self.widget is not None:
            pct = self._get_time_pct()
            try:
                self.widget.children[0].value = pct
                self.widget.children[1].value = f"{pct:.1f}%"
            except Exception:
                pass


def create_progress_tracker(
    environment: str = 'auto',
    show_iteration_rate: bool = True,
    show_probe_count: bool = True,
    **kwargs: Any
) -> ProgressTracker:
    """Create appropriate progress tracker for environment.

    Args:
        environment: 'auto', 'tqdm', 'jupyter', or 'none'
        show_iteration_rate: Show iteration rate (for basic tracker)
        show_probe_count: Show probe count (for basic tracker)
        **kwargs: Additional arguments

    Returns:
        ProgressTracker instance
    """
    if environment == 'auto':
        try:
            import IPython
            from IPython import get_ipython
            if get_ipython() is not None:
                return JupyterProgressTracker(1000.0)
        except ImportError:
            pass

        try:
            import tqdm
            return TqdmProgressTracker(1000.0)
        except ImportError:
            return ProgressTracker(1000.0)

    elif environment == 'tqdm':
        return TqdmProgressTracker(1000.0)
    elif environment == 'jupyter':
        return JupyterProgressTracker(1000.0)
    else:
        return ProgressTracker(1000.0)


__all__ = [
    "ProgressMetrics",
    "ProgressTracker",
    "TqdmProgressTracker",
    "JupyterProgressTracker",
    "create_progress_tracker",
]
