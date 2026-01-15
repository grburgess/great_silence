"""Tiered disaster storage archiver with HDF5 backend."""

from pathlib import Path
from typing import List, Optional
import numpy as np

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False

from .encoding import (
    DisasterBinary,
    encode_disaster,
    decode_disaster,
    EVENT_TYPE_REVERSE,
)


class DisasterArchiver:
    """Tiered disaster storage with HDF5 backend.

    Tier 1: Recent events (in-memory, full objects)
    Tier 2: Binary buffer (in-memory, compact)
    Tier 3: HDF5 file (on-disk, compressed)
    """

    def __init__(
        self,
        archive_path: Optional[Path] = None,
        recent_window_myr: float = 10.0,
        buffer_size: int = 1000,
    ):
        """Initialize archiver.

        Args:
            archive_path: Path to HDF5 file (None = memory only)
            recent_window_myr: Time window for tier 1 storage (Myr)
            buffer_size: Buffer size before flush to disk
        """
        self.archive_path = archive_path
        self.recent_window_myr = recent_window_myr
        self.buffer_size = buffer_size
        self.recent_buffer: List[tuple[float, object]] = []
        self.binary_buffer: List[bytes] = []
        self.hdf5_file = None

        if self.archive_path is not None and HAS_H5PY:
            self._init_hdf5()

    def _init_hdf5(self):
        """Initialize HDF5 file with disaster dataset."""
        if not HAS_H5PY:
            return

        with h5py.File(self.archive_path, "w") as f:
            f.create_dataset(
                "disasters",
                shape=(0, 24),
                dtype=np.uint8,
                maxshape=(None, 24),
                compression="gzip",
                compression_opts=4,
            )
            f.attrs["version"] = "1.0"

    def archive_disaster(self, disaster, current_time_myr: float):
        """Archive disaster with tiered storage.

        Args:
            disaster: HazardEvent to archive
            current_time_myr: Current simulation time (Myr)
        """
        binary_data = encode_disaster(disaster)
        self.binary_buffer.append(binary_data)

        self.recent_buffer.append((current_time_myr, disaster))

        if len(self.binary_buffer) >= self.buffer_size:
            self._flush_to_hdf5()

        self._prune_recent_buffer(current_time_myr)

    def _flush_to_hdf5(self):
        """Flush binary buffer to HDF5 file."""
        if not HAS_H5PY or len(self.binary_buffer) == 0:
            return

        records = np.array(
            [list(b) for b in self.binary_buffer], dtype=np.uint8
        )

        with h5py.File(self.archive_path, "a") as f:
            dset = f["disasters"]
            old_size = dset.shape[0]
            dset.resize(old_size + len(records), axis=0)
            dset[old_size:] = records

        self.binary_buffer.clear()

    def _prune_recent_buffer(self, current_time_myr: float):
        """Remove events outside recent window."""
        cutoff = current_time_myr - self.recent_window_myr
        self.recent_buffer = [
            (t, d) for t, d in self.recent_buffer if t >= cutoff
        ]

    def get_disasters_in_window(
        self, start_myr: float, end_myr: float
    ) -> List:
        """Get disasters in time window.

        Returns HazardEvent objects from recent buffer if available,
        otherwise decodes from binary storage.

        Args:
            start_myr: Window start (Myr)
            end_myr: Window end (Myr)

        Returns:
            List of HazardEvent objects
        """
        events = []

        for t, d in self.recent_buffer:
            if start_myr <= t <= end_myr:
                events.append(d)

        if (
            HAS_H5PY
            and self.archive_path is not None
            and self.archive_path.exists()
        ):
            from ..engine import HazardEvent

            with h5py.File(self.archive_path, "r") as f:
                dset = f["disasters"]
                for row in dset:
                    binary = bytes(row)
                    decoded = decode_disaster(binary)
                    if start_myr <= decoded.time_myr <= end_myr:
                        event_type = EVENT_TYPE_REVERSE.get(
                            decoded.event_type, "unknown"
                        )
                        hazard = HazardEvent(
                            time_myr=decoded.time_myr,
                            event_type=event_type,
                            position=decoded.position,
                            energy=decoded.energy,
                            sterilization_radius_pc=float(
                                decoded.lethal_radius
                            ),
                        )
                        events.append(hazard)

        return events

    def get_all_disasters(self) -> List:
        """Get all archived disasters (for analysis).

        Returns:
            List of all disasters as (time, HazardEvent) tuples
        """
        all_events = []

        for t, d in self.recent_buffer:
            all_events.append((t, d))

        if (
            HAS_H5PY
            and self.archive_path is not None
            and self.archive_path.exists()
        ):
            from ..engine import HazardEvent

            with h5py.File(self.archive_path, "r") as f:
                dset = f["disasters"]
                for row in dset:
                    binary = bytes(row)
                    decoded = decode_disaster(binary)
                    event_type = EVENT_TYPE_REVERSE.get(
                        decoded.event_type, "unknown"
                    )
                    hazard = HazardEvent(
                        time_myr=decoded.time_myr,
                        event_type=event_type,
                        position=decoded.position,
                        energy=decoded.energy,
                        sterilization_radius_pc=float(
                            decoded.lethal_radius
                        ),
                    )
                    all_events.append((decoded.time_myr, hazard))

        return all_events

    def finalize(self):
        """Flush remaining buffer and close HDF5."""
        if len(self.binary_buffer) > 0:
            self._flush_to_hdf5()

        if self.hdf5_file is not None:
            self.hdf5_file.close()
            self.hdf5_file = None
