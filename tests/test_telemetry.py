"""
Tests for civilization telemetry and tracking system.
"""

import pytest
import numpy as np
from great_silence.civilization.telemetry import (
    CivilizationTelemetry,
    CivilizationEvent,
    CivilizationSnapshot,
    EventType,
    CrisisType,
    BreakthroughType
)


class TestCivilizationEvent:
    """Tests for CivilizationEvent dataclass."""

    def test_event_creation(self):
        """Test creating a basic event."""
        event = CivilizationEvent(
            time_myr=1000.0,
            civilization_id=0,
            event_type=EventType.BIRTH,
            kardashev_level=0.7
        )

        assert event.time_myr == 1000.0
        assert event.civilization_id == 0
        assert event.event_type == EventType.BIRTH
        assert event.kardashev_level == 0.7

    def test_event_to_dict(self):
        """Test event serialization."""
        event = CivilizationEvent(
            time_myr=1000.0,
            civilization_id=0,
            event_type=EventType.CRISIS_ENTERED,
            crisis_type=CrisisType.NUCLEAR_AGE,
            severity=0.8,
            metadata={'test': 'value'}
        )

        d = event.to_dict()
        assert d['time_myr'] == 1000.0
        assert d['event_type'] == 'crisis_entered'
        assert d['crisis_type'] == 'nuclear_age'
        assert d['severity'] == 0.8
        assert d['metadata']['test'] == 'value'


class TestCivilizationSnapshot:
    """Tests for CivilizationSnapshot dataclass."""

    def test_snapshot_creation(self):
        """Test creating a state snapshot."""
        snapshot = CivilizationSnapshot(
            time_myr=1000.0,
            civilization_id=0,
            kardashev_level=0.7,
            social_maturity=0.5,
            is_active=True,
            political_cohesion=0.6,
            technological_wisdom=0.4,
            risk_tolerance=0.5,
            resource_abundance=0.7,
            adaptability=0.6,
            crises_survived=0,
            crisis_scars=[],
            advancement_rate=0.05,
            time_alive_myr=100.0
        )

        assert snapshot.kardashev_level == 0.7
        assert snapshot.social_maturity == 0.5
        assert snapshot.political_cohesion == 0.6
        assert snapshot.is_active is True

    def test_snapshot_with_crisis(self):
        """Test snapshot during crisis."""
        snapshot = CivilizationSnapshot(
            time_myr=1050.0,
            civilization_id=0,
            kardashev_level=0.72,
            social_maturity=0.55,
            is_active=True,
            political_cohesion=0.6,
            technological_wisdom=0.4,
            risk_tolerance=0.5,
            resource_abundance=0.7,
            adaptability=0.6,
            crises_survived=0,
            crisis_scars=[],
            advancement_rate=0.05,
            time_alive_myr=150.0,
            in_crisis=True,
            current_crisis_type=CrisisType.NUCLEAR_AGE,
            time_in_current_crisis_myr=10.0,
            crisis_severity=0.8
        )

        assert snapshot.in_crisis is True
        assert snapshot.current_crisis_type == CrisisType.NUCLEAR_AGE
        assert snapshot.crisis_severity == 0.8

    def test_snapshot_to_dict(self):
        """Test snapshot serialization."""
        position = np.array([1.0, 2.0, 0.1])
        snapshot = CivilizationSnapshot(
            time_myr=1000.0,
            civilization_id=0,
            kardashev_level=0.7,
            social_maturity=0.5,
            is_active=True,
            political_cohesion=0.6,
            technological_wisdom=0.4,
            risk_tolerance=0.5,
            resource_abundance=0.7,
            adaptability=0.6,
            crises_survived=1,
            crisis_scars=['nuclear_age'],
            advancement_rate=0.05,
            time_alive_myr=100.0,
            position_kpc=position,
            parent_star_idx=42
        )

        d = snapshot.to_dict()
        assert d['kardashev_level'] == 0.7
        assert d['crises_survived'] == 1
        assert d['crisis_scars'] == ['nuclear_age']
        assert d['position_kpc'] == [1.0, 2.0, 0.1]
        assert d['parent_star_idx'] == 42


class TestCivilizationTelemetry:
    """Tests for CivilizationTelemetry tracking system."""

    def test_telemetry_initialization(self):
        """Test creating empty telemetry."""
        telemetry = CivilizationTelemetry()
        assert len(telemetry.events) == 0
        assert len(telemetry.snapshots) == 0
        assert len(telemetry.get_civilization_ids()) == 0

    def test_log_birth(self):
        """Test logging birth event."""
        telemetry = CivilizationTelemetry()

        telemetry.log_birth(
            time_myr=1000.0,
            civilization_id=0,
            kardashev=0.7,
            social_maturity=0.5,
            traits={
                'political_cohesion': 0.6,
                'technological_wisdom': 0.4
            }
        )

        assert len(telemetry.events) == 1
        assert telemetry.events[0].event_type == EventType.BIRTH
        assert telemetry.events[0].civilization_id == 0
        assert telemetry.events[0].kardashev_level == 0.7
        assert telemetry.events[0].metadata['traits']['political_cohesion'] == 0.6

    def test_log_death(self):
        """Test logging death event."""
        telemetry = CivilizationTelemetry()

        telemetry.log_death(
            time_myr=2000.0,
            civilization_id=0,
            kardashev=0.85,
            social_maturity=0.4,
            cause='nuclear_war'
        )

        assert len(telemetry.events) == 1
        assert telemetry.events[0].event_type == EventType.DEATH
        assert telemetry.events[0].metadata['cause'] == 'nuclear_war'

    def test_log_crisis_sequence(self):
        """Test logging a complete crisis sequence."""
        telemetry = CivilizationTelemetry()

        # Enter crisis
        telemetry.log_crisis_entered(
            time_myr=1500.0,
            civilization_id=0,
            crisis_type=CrisisType.NUCLEAR_AGE,
            severity=0.8,
            kardashev=0.72
        )

        # Survive crisis
        telemetry.log_crisis_survived(
            time_myr=1550.0,
            civilization_id=0,
            crisis_type=CrisisType.NUCLEAR_AGE,
            kardashev=0.75,
            social_maturity=0.6
        )

        assert len(telemetry.events) == 2
        assert telemetry.events[0].event_type == EventType.CRISIS_ENTERED
        assert telemetry.events[1].event_type == EventType.CRISIS_SURVIVED

    def test_log_breakthrough(self):
        """Test logging breakthrough event."""
        telemetry = CivilizationTelemetry()

        telemetry.log_breakthrough(
            time_myr=1520.0,
            civilization_id=0,
            breakthrough_type=BreakthroughType.PHILOSOPHICAL_AWAKENING,
            kardashev=0.73,
            impact={'social_maturity': +0.2}
        )

        assert len(telemetry.events) == 1
        assert telemetry.events[0].event_type == EventType.BREAKTHROUGH
        assert telemetry.events[0].breakthrough_type == BreakthroughType.PHILOSOPHICAL_AWAKENING

    def test_log_aid(self):
        """Test logging inter-civilization aid."""
        telemetry = CivilizationTelemetry()

        telemetry.log_aid(
            time_myr=1600.0,
            giver_id=1,
            receiver_id=0,
            kardashev_giver=1.5,
            aid_amount=0.1
        )

        # Should create 2 events (one for giver, one for receiver)
        assert len(telemetry.events) == 2
        assert telemetry.events[0].event_type == EventType.AID_SENT
        assert telemetry.events[0].civilization_id == 1
        assert telemetry.events[0].helper_civilization_id == 0

        assert telemetry.events[1].event_type == EventType.AID_RECEIVED
        assert telemetry.events[1].civilization_id == 0
        assert telemetry.events[1].helper_civilization_id == 1

    def test_log_snapshot(self):
        """Test logging state snapshots."""
        telemetry = CivilizationTelemetry()

        snapshot = CivilizationSnapshot(
            time_myr=1000.0,
            civilization_id=0,
            kardashev_level=0.7,
            social_maturity=0.5,
            is_active=True,
            political_cohesion=0.6,
            technological_wisdom=0.4,
            risk_tolerance=0.5,
            resource_abundance=0.7,
            adaptability=0.6,
            crises_survived=0,
            crisis_scars=[],
            advancement_rate=0.05,
            time_alive_myr=100.0
        )

        telemetry.log_snapshot(snapshot)

        assert len(telemetry.snapshots) == 1
        assert telemetry.snapshots[0].civilization_id == 0

    def test_get_events_for_civilization(self):
        """Test querying events for specific civilization."""
        telemetry = CivilizationTelemetry()

        # Log events for civ 0
        telemetry.log_birth(1000.0, 0, 0.7, 0.5, {})
        telemetry.log_crisis_entered(1500.0, 0, CrisisType.NUCLEAR_AGE, 0.8, 0.72)

        # Log events for civ 1
        telemetry.log_birth(2000.0, 1, 0.7, 0.5, {})

        # Query
        civ0_events = telemetry.get_events_for_civilization(0)
        civ1_events = telemetry.get_events_for_civilization(1)

        assert len(civ0_events) == 2
        assert len(civ1_events) == 1
        assert all(e.civilization_id == 0 for e in civ0_events)

    def test_get_events_by_type(self):
        """Test querying events by type."""
        telemetry = CivilizationTelemetry()

        telemetry.log_birth(1000.0, 0, 0.7, 0.5, {})
        telemetry.log_birth(2000.0, 1, 0.7, 0.5, {})
        telemetry.log_death(3000.0, 0, 0.85, 0.4, 'self_destruction')

        births = telemetry.get_events_by_type(EventType.BIRTH)
        deaths = telemetry.get_events_by_type(EventType.DEATH)

        assert len(births) == 2
        assert len(deaths) == 1

    def test_get_events_in_time_range(self):
        """Test querying events in time range."""
        telemetry = CivilizationTelemetry()

        telemetry.log_birth(1000.0, 0, 0.7, 0.5, {})
        telemetry.log_crisis_entered(1500.0, 0, CrisisType.NUCLEAR_AGE, 0.8, 0.72)
        telemetry.log_birth(2000.0, 1, 0.7, 0.5, {})
        telemetry.log_death(3000.0, 0, 0.85, 0.4, 'self_destruction')

        # Query events between 1400 and 2100 Myr
        events = telemetry.get_events_in_time_range(1400.0, 2100.0)

        assert len(events) == 2  # Crisis entry and second birth
        assert 1400.0 <= events[0].time_myr <= 2100.0
        assert 1400.0 <= events[1].time_myr <= 2100.0

    def test_get_civilization_ids(self):
        """Test getting all tracked civilization IDs."""
        telemetry = CivilizationTelemetry()

        telemetry.log_birth(1000.0, 0, 0.7, 0.5, {})
        telemetry.log_birth(2000.0, 1, 0.7, 0.5, {})
        telemetry.log_birth(3000.0, 5, 0.7, 0.5, {})

        civ_ids = set(telemetry.get_civilization_ids())
        assert civ_ids == {0, 1, 5}

    def test_crisis_survival_rate(self):
        """Test calculating crisis survival rate."""
        telemetry = CivilizationTelemetry()

        # 2 survived
        telemetry.log_crisis_survived(1500.0, 0, CrisisType.NUCLEAR_AGE, 0.75, 0.6)
        telemetry.log_crisis_survived(1600.0, 1, CrisisType.NUCLEAR_AGE, 0.75, 0.6)

        # 3 failed
        telemetry.log_crisis_failed(1700.0, 2, CrisisType.NUCLEAR_AGE, 0.72)
        telemetry.log_crisis_failed(1800.0, 3, CrisisType.NUCLEAR_AGE, 0.72)
        telemetry.log_crisis_failed(1900.0, 4, CrisisType.NUCLEAR_AGE, 0.72)

        # Overall rate
        rate_all = telemetry.get_crisis_survival_rate()
        assert rate_all == 2.0 / 5.0  # 40%

        # Nuclear age specific
        rate_nuclear = telemetry.get_crisis_survival_rate(CrisisType.NUCLEAR_AGE)
        assert rate_nuclear == 2.0 / 5.0  # 40%

        # Different crisis type (no events)
        rate_ai = telemetry.get_crisis_survival_rate(CrisisType.AI_TRANSITION)
        assert rate_ai == 0.0

    def test_average_trait_by_outcome(self):
        """Test calculating average traits for survivors vs non-survivors."""
        telemetry = CivilizationTelemetry()

        # Civ 0: high cohesion, survives
        telemetry.log_birth(1000.0, 0, 0.7, 0.5, {
            'political_cohesion': 0.8,
            'technological_wisdom': 0.6
        })
        telemetry.log_crisis_survived(1500.0, 0, CrisisType.NUCLEAR_AGE, 0.75, 0.6)

        # Civ 1: low cohesion, dies
        telemetry.log_birth(2000.0, 1, 0.7, 0.5, {
            'political_cohesion': 0.2,
            'technological_wisdom': 0.3
        })
        telemetry.log_crisis_failed(2500.0, 1, CrisisType.NUCLEAR_AGE, 0.72)

        # Civ 2: medium cohesion, dies
        telemetry.log_birth(3000.0, 2, 0.7, 0.5, {
            'political_cohesion': 0.4,
            'technological_wisdom': 0.4
        })
        telemetry.log_crisis_failed(3500.0, 2, CrisisType.NUCLEAR_AGE, 0.72)

        stats = telemetry.get_average_trait_by_outcome('political_cohesion')

        assert stats['survived'] == 0.8
        assert stats['died'] == pytest.approx(0.3, abs=0.01)  # (0.2 + 0.4) / 2
        assert stats['n_survived'] == 1
        assert stats['n_died'] == 2

    def test_export_for_chord_diagram(self):
        """Test exporting data for chord diagram."""
        telemetry = CivilizationTelemetry()

        # Add some events
        telemetry.log_crisis_survived(1500.0, 0, CrisisType.NUCLEAR_AGE, 0.75, 0.6)
        telemetry.log_crisis_failed(1600.0, 1, CrisisType.NUCLEAR_AGE, 0.72)
        telemetry.log_crisis_failed(1700.0, 2, CrisisType.AI_TRANSITION, 1.05)

        # Add breakthrough
        telemetry.log_birth(1000.0, 0, 0.7, 0.5, {})
        telemetry.log_breakthrough(1200.0, 0, BreakthroughType.PHILOSOPHICAL_AWAKENING, 0.71)

        chord_data = telemetry.export_for_chord_diagram()

        assert 'nodes' in chord_data
        assert 'links' in chord_data

        # Check nodes include crisis types and outcomes
        node_ids = [n['id'] for n in chord_data['nodes']]
        assert 'nuclear_age' in node_ids
        assert 'survived' in node_ids
        assert 'failed' in node_ids

        # Check links
        links = chord_data['links']
        assert len(links) > 0

        # Find nuclear age -> survived link
        nuclear_survived = [l for l in links
                          if l['source'] == 'nuclear_age' and l['target'] == 'survived']
        assert len(nuclear_survived) == 1
        assert nuclear_survived[0]['value'] == 1

    def test_export_to_dict(self):
        """Test exporting all telemetry to dictionary."""
        telemetry = CivilizationTelemetry()

        telemetry.log_birth(1000.0, 0, 0.7, 0.5, {})
        telemetry.log_crisis_entered(1500.0, 0, CrisisType.NUCLEAR_AGE, 0.8, 0.72)

        snapshot = CivilizationSnapshot(
            time_myr=1000.0,
            civilization_id=0,
            kardashev_level=0.7,
            social_maturity=0.5,
            is_active=True,
            political_cohesion=0.6,
            technological_wisdom=0.4,
            risk_tolerance=0.5,
            resource_abundance=0.7,
            adaptability=0.6,
            crises_survived=0,
            crisis_scars=[],
            advancement_rate=0.05,
            time_alive_myr=100.0
        )
        telemetry.log_snapshot(snapshot)

        data = telemetry.export_to_dict()

        assert 'events' in data
        assert 'snapshots' in data
        assert 'metadata' in data

        assert len(data['events']) == 2
        assert len(data['snapshots']) == 1
        assert data['metadata']['num_civilizations'] == 1
        assert data['metadata']['num_events'] == 2
