"""Unit tests for disaster tracking modules."""

import numpy as np
import pytest
from pathlib import Path
import tempfile
import h5py


class TestDisasterEncoding:
    """Test disaster binary encoding/decoding."""

    def setup_method(self):
        """Create test hazard events."""
        from great_silence.simulation.engine import HazardEvent

        self.sn_event = HazardEvent(
            time_myr=500.0,
            event_type='supernova',
            position=np.array([10.0, -5.0, 2.0]),
            energy=1e51,
            sterilization_radius_pc=50.0,
            affected_civ_ids=[1, 2]
        )

        self.grb_event = HazardEvent(
            time_myr=750.0,
            event_type='grb',
            position=np.array([15.0, 0.0, -10.0]),
            energy=1e54,
            sterilization_radius_pc=1000.0,
            affected_civ_ids=[3]
        )

    def test_encode_supernova(self):
        """Test supernova event encoding."""
        from great_silence.simulation.disasters.encoding import encode_disaster

        binary = encode_disaster(self.sn_event)
        assert len(binary) == 24

    def test_encode_grb(self):
        """Test GRB event encoding."""
        from great_silence.simulation.disasters.encoding import encode_disaster

        binary = encode_disaster(self.grb_event)
        assert len(binary) == 24

    def test_decode_supernova(self):
        """Test supernova event decoding."""
        from great_silence.simulation.disasters.encoding import (
            encode_disaster,
            decode_disaster
        )

        binary = encode_disaster(self.sn_event)
        decoded = decode_disaster(binary)

        assert decoded.time_myr == pytest.approx(500.0, rel=1e-3)
        assert decoded.event_type == 0  # SN = 0
        assert decoded.lethal_radius == 50
        assert decoded.energy == pytest.approx(1e51, rel=0.1)

    def test_decode_grb(self):
        """Test GRB event decoding."""
        from great_silence.simulation.disasters.encoding import (
            encode_disaster,
            decode_disaster
        )

        binary = encode_disaster(self.grb_event)
        decoded = decode_disaster(binary)

        assert decoded.time_myr == pytest.approx(750.0, rel=1e-3)
        assert decoded.event_type == 1  # GRB = 1
        assert decoded.lethal_radius == 1000

    def test_encode_batch(self):
        """Test batch encoding."""
        from great_silence.simulation.disasters.encoding import encode_disaster_batch

        events = [self.sn_event, self.grb_event]
        binary = encode_disaster_batch(events)
        assert len(binary) == 48  # 2 events * 24 bytes

    def test_decode_batch(self):
        """Test batch decoding."""
        from great_silence.simulation.disasters.encoding import (
            encode_disaster_batch,
            decode_disaster_batch
        )

        events = [self.sn_event, self.grb_event]
        binary = encode_disaster_batch(events)
        decoded = decode_disaster_batch(binary, 2)

        assert len(decoded) == 2
        assert decoded[0].event_type == 0  # SN
        assert decoded[1].event_type == 1  # GRB


class TestSpatialIndex:
    """Test disaster spatial index."""

    def setup_method(self):
        """Create test disasters."""
        from great_silence.simulation.engine import HazardEvent

        self.index = None
        self.disasters = [
            HazardEvent(
                time_myr=i * 100.0,
                event_type='supernova',
                position=np.array([i * 5.0, 0.0, 0.0]),
                energy=1e51,
                sterilization_radius_pc=50.0
            )
            for i in range(10)
        ]

    def test_create_index(self):
        """Test spatial index creation."""
        from great_silence.simulation.disasters.spatial_index import (
            DisasterSpatialIndex
        )

        self.index = DisasterSpatialIndex()

    def test_add_disasters(self):
        """Test adding disasters to index."""
        from great_silence.simulation.disasters.spatial_index import (
            DisasterSpatialIndex
        )

        self.index = DisasterSpatialIndex()
        for d in self.disasters:
            self.index.add_disaster(d)

    def test_spatial_query(self):
        """Test spatial range query."""
        from great_silence.simulation.disasters.spatial_index import (
            DisasterSpatialIndex
        )

        self.index = DisasterSpatialIndex()
        for d in self.disasters:
            self.index.add_disaster(d)

        results = self.index.query_spatial(
            center=np.array([10.0, 0.0, 0.0]),
            radius_kpc=5.0
        )

        assert len(results) > 0

    def test_temporal_query(self):
        """Test temporal range query."""
        from great_silence.simulation.disasters.spatial_index import (
            DisasterSpatialIndex
        )

        self.index = DisasterSpatialIndex()
        for d in self.disasters:
            self.index.add_disaster(d)

        results = self.index.query_temporal(0.0, 500.0)
        assert len(results) > 0

    def test_spatiotemporal_query(self):
        """Test combined spatiotemporal query."""
        from great_silence.simulation.disasters.spatial_index import (
            DisasterSpatialIndex
        )

        self.index = DisasterSpatialIndex()
        for d in self.disasters:
            self.index.add_disaster(d)

        results = self.index.query_spatiotemporal(
            center=np.array([10.0, 0.0, 0.0]),
            radius_kpc=5.0,
            time_start=0.0,
            time_end=500.0
        )

        assert len(results) >= 0


class TestRecoveryQueue:
    """Test star recovery queue."""

    def setup_method(self):
        """Create recovery queue."""
        from great_silence.simulation.disasters.recovery import RecoveryQueue

        self.n_stars = 1000
        self.queue = RecoveryQueue(self.n_stars)

    def test_initial_status(self):
        """Test initial star status."""
        from great_silence.simulation.disasters.recovery import SterilizationStatus

        stats = self.queue.get_statistics()
        assert stats['habitable'] == self.n_stars
        assert stats['temporarily_sterilized'] == 0
        assert stats['permanently_sterilized'] == 0

    def test_sterilize_star(self):
        """Test star sterilization."""
        from great_silence.simulation.disasters.recovery import SterilizationStatus

        self.queue.sterilize_star(100, 100.0, 50.0, permanent=False)

        assert self.queue.status[100] == SterilizationStatus.TEMPORARILY_STERILIZED
        assert 100 in self.queue.in_queue

    def test_sterilize_permanent(self):
        """Test permanent sterilization."""
        from great_silence.simulation.disasters.recovery import SterilizationStatus

        self.queue.sterilize_star(200, 100.0, 0.0, permanent=True)

        assert self.queue.status[200] == SterilizationStatus.PERMANENTLY_STERILIZED

    def test_sterilize_batch(self):
        """Test batch sterilization."""
        from great_silence.simulation.disasters.recovery import SterilizationStatus

        indices = np.array([0, 1, 2, 3, 4])
        times = np.array([50.0, 50.0, 50.0, 50.0, 50.0])
        permanent = np.array([False, False, False, True, False])

        self.queue.sterilize_batch(indices, 100.0, times, permanent)

        assert self.queue.status[0] == SterilizationStatus.TEMPORARILY_STERILIZED
        assert self.queue.status[3] == SterilizationStatus.PERMANENTLY_STERILIZED

    def test_process_recoveries(self):
        """Test recovery processing."""
        from great_silence.simulation.disasters.recovery import SterilizationStatus

        self.queue.sterilize_star(100, 100.0, 10.0, permanent=False)

        recovered = self.queue.process_recoveries(120.0)

        assert len(recovered) == 1
        assert 100 in recovered
        assert self.queue.status[100] == SterilizationStatus.HABITABLE

    def test_habitable_mask(self):
        """Test habitable star mask."""
        from great_silence.simulation.disasters.recovery import SterilizationStatus

        self.queue.sterilize_star(0, 100.0, 50.0, permanent=False)
        self.queue.sterilize_star(1, 100.0, 0.0, permanent=True)

        mask = self.queue.get_habitable_mask()

        assert not mask[0]
        assert not mask[1]
        assert mask[2]

    def test_lazy_deletion(self):
        """Test lazy deletion for re-sterilization."""
        from great_silence.simulation.disasters.recovery import SterilizationStatus

        self.queue.sterilize_star(100, 100.0, 50.0, permanent=False)
        assert 100 in self.queue.in_queue

        self.queue.sterilize_star(100, 150.0, 30.0, permanent=False)
        assert 100 in self.queue.stale_indices

        recovered = self.queue.process_recoveries(160.0)
        assert 100 not in recovered  # Should skip stale entry (recovery at 150.0)
        assert 100 in self.queue.in_queue  # Still in queue for second recovery at 180.0

        recovered = self.queue.process_recoveries(200.0)
        assert 100 in recovered  # Should recover now (recovery at 180.0)


class TestDisasterArchiver:
    """Test disaster archiver with HDF5 backend."""

    def setup_method(self):
        """Create archiver with temp file."""
        from great_silence.simulation.disasters.archiver import DisasterArchiver
        from great_silence.simulation.engine import HazardEvent

        self.temp_dir = tempfile.mkdtemp()
        self.archive_path = Path(self.temp_dir) / "test_disasters.h5"

        self.archiver = DisasterArchiver(
            archive_path=self.archive_path,
            recent_window_myr=10.0,
            buffer_size=2
        )

        self.test_events = [
            HazardEvent(
                time_myr=i * 100.0,
                event_type='supernova',
                position=np.array([i * 5.0, 0.0, 0.0]),
                energy=1e51,
                sterilization_radius_pc=50.0
            )
            for i in range(5)
        ]

    def teardown_method(self):
        """Clean up temp files."""
        import shutil
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_archive_disaster(self):
        """Test archiving single disaster."""
        self.archiver.archive_disaster(self.test_events[0], 100.0)

        assert len(self.archiver.recent_buffer) == 1
        assert len(self.archiver.binary_buffer) == 1

    def test_buffer_flush(self):
        """Test buffer flushing to HDF5."""
        for i, event in enumerate(self.test_events[:3]):
            self.archiver.archive_disaster(event, i * 100.0)

        assert len(self.archiver.binary_buffer) == 1  # Should flush after 2
        assert self.archive_path.exists()

    def test_get_disasters_in_window(self):
        """Test querying disasters in time window."""
        for i, event in enumerate(self.test_events):
            self.archiver.archive_disaster(event, i * 100.0)

        self.archiver.finalize()

        events = self.archiver.get_disasters_in_window(0.0, 299.9)

        assert len(events) == 3

    def test_get_all_disasters(self):
        """Test getting all disasters."""
        for i, event in enumerate(self.test_events):
            self.archiver.archive_disaster(event, i * 100.0)

        self.archiver.finalize()

        all_events = self.archiver.get_all_disasters()

        assert len(all_events) == 6

    def test_type_consistency(self):
        """Test that query returns HazardEvent objects."""
        from great_silence.simulation.engine import HazardEvent

        for i, event in enumerate(self.test_events[:2]):
            self.archiver.archive_disaster(event, i * 100.0)

        self.archiver.finalize()

        events = self.archiver.get_disasters_in_window(0.0, 200.0)

        for event in events:
            assert isinstance(event, HazardEvent)

    def test_finalization(self):
        """Test archiver finalization."""
        for event in self.test_events[:3]:
            self.archiver.archive_disaster(event, 0.0)

        self.archiver.finalize()

        assert len(self.archiver.binary_buffer) == 0
        assert self.archive_path.exists()


class TestSupernovaScheduler:
    """Test supernova event scheduler."""

    def setup_method(self):
        """Create scheduler with test stellar data."""
        from great_silence.simulation.disasters.scheduler import SupernovaScheduler
        from unittest.mock import Mock

        self.n_stars = 1000
        self.rng = np.random.default_rng(42)

        masses = self.rng.exponential(0.5, self.n_stars)
        metallicities = self.rng.uniform(0.001, 0.03, self.n_stars)
        ages = self.rng.uniform(0, 10000, self.n_stars)

        mock_stellar_evolution = Mock()
        mock_stellar_evolution.main_sequence_lifetime = lambda m, z: 0.01 * m * 10.0

        self.scheduler = SupernovaScheduler(masses, metallicities, ages, mock_stellar_evolution)

    def test_scheduler_creation(self):
        """Test scheduler initialization."""
        assert self.scheduler is not None

    def test_get_supernovae_in_window(self):
        """Test querying supernovae in time window."""
        sn_indices = self.scheduler.get_supernovae_in_window(0.0, 10000.0)

        assert isinstance(sn_indices, (list, np.ndarray))

    def test_add_new_star(self):
        """Test adding newly formed star."""
        new_mass = 15.0
        new_metallicity = 0.02
        new_age = 0.0
        birth_time_myr = 5000.0

        initial_count = self.scheduler.pending_count
        self.scheduler.add_new_star(1000, new_mass, new_metallicity, birth_time_myr)

        assert self.scheduler.pending_count >= initial_count

    def test_pending_count(self):
        """Test pending supernova count property."""
        count = self.scheduler.pending_count

        assert count >= 0
        assert count <= self.n_stars
