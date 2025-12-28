"""
Telemetry and tracking system for civilization evolution.

This module provides comprehensive event logging and state tracking for
visualization, analysis, and debugging of civilization dynamics.

Key Features:
- Event logging (births, deaths, crises, breakthroughs)
- State snapshots at regular intervals
- Time-series tracking of all civilization attributes
- Export formats suitable for chord plots, Sankey diagrams, etc.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum
import numpy as np


class EventType(Enum):
    """Types of events that can occur in civilization evolution."""

    BIRTH = "birth"
    DEATH = "death"
    CRISIS_ENTERED = "crisis_entered"
    CRISIS_SURVIVED = "crisis_survived"
    CRISIS_FAILED = "crisis_failed"
    BREAKTHROUGH = "breakthrough"
    TRAIT_CHANGE = "trait_change"
    SOCIAL_MATURITY_GAIN = "social_maturity_gain"
    KARDASHEV_ADVANCEMENT = "kardashev_advancement"
    AID_SENT = "aid_sent"
    AID_RECEIVED = "aid_received"


class CrisisType(Enum):
    """Types of crises civilizations can face."""

    NUCLEAR_AGE = "nuclear_age"
    PLANETARY_UNIFICATION = "planetary_unification"
    AI_TRANSITION = "ai_transition"
    INTERPLANETARY = "interplanetary"
    STELLAR_ENGINEERING = "stellar_engineering"
    RELATIVISTIC_WEAPONS = "relativistic_weapons"


class BreakthroughType(Enum):
    """Types of breakthroughs that can help civilizations."""

    UNIFICATION_MOVEMENT = "unification_movement"
    SCIENTIFIC_REVOLUTION = "scientific_revolution"
    PHILOSOPHICAL_AWAKENING = "philosophical_awakening"
    RESOURCE_DISCOVERY = "resource_discovery"
    SOCIAL_REFORM = "social_reform"
    TECHNOLOGICAL_LEAP = "technological_leap"


@dataclass
class CivilizationEvent:
    """Record of a single event in civilization history."""

    time_myr: float
    civilization_id: int
    event_type: EventType

    # Optional details depending on event type
    kardashev_level: Optional[float] = None
    social_maturity: Optional[float] = None
    crisis_type: Optional[CrisisType] = None
    breakthrough_type: Optional[BreakthroughType] = None
    severity: Optional[float] = None

    # For aid events
    helper_civilization_id: Optional[int] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        # Convert enums to strings
        result['event_type'] = self.event_type.value if self.event_type else None
        result['crisis_type'] = self.crisis_type.value if self.crisis_type else None
        result['breakthrough_type'] = self.breakthrough_type.value if self.breakthrough_type else None
        return result


@dataclass
class CivilizationSnapshot:
    """Complete state snapshot of a civilization at a point in time."""

    time_myr: float
    civilization_id: int

    # Core attributes
    kardashev_level: float
    social_maturity: float
    is_active: bool

    # Traits
    political_cohesion: float
    technological_wisdom: float
    risk_tolerance: float
    resource_abundance: float
    adaptability: float

    # Experience
    crises_survived: int
    crisis_scars: List[str]

    # Development metrics
    advancement_rate: float  # Recent rate of Kardashev advancement
    time_alive_myr: float

    # Current crisis (if any)
    in_crisis: bool = False
    current_crisis_type: Optional[CrisisType] = None
    time_in_current_crisis_myr: float = 0.0
    crisis_severity: float = 0.0

    # Position in galaxy
    position_kpc: Optional[np.ndarray] = None
    parent_star_idx: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['current_crisis_type'] = self.current_crisis_type.value if self.current_crisis_type else None
        if self.position_kpc is not None:
            result['position_kpc'] = self.position_kpc.tolist()
        return result


class CivilizationTelemetry:
    """
    Comprehensive tracking system for civilization evolution.

    This class maintains a complete history of all events and state changes
    for all civilizations in a simulation, enabling detailed analysis and
    visualization.

    Example:
        >>> telemetry = CivilizationTelemetry()
        >>> telemetry.log_birth(time_myr=1000, civ_id=0, kardashev=0.7)
        >>> telemetry.log_crisis_entered(time_myr=1050, civ_id=0,
        ...                              crisis_type=CrisisType.NUCLEAR_AGE)
        >>> telemetry.log_crisis_survived(time_myr=1100, civ_id=0)
        >>> events = telemetry.get_events_for_civilization(0)
    """

    def __init__(self):
        self.events: List[CivilizationEvent] = []
        self.snapshots: List[CivilizationSnapshot] = []

        # Quick lookup indices
        self._events_by_civ: Dict[int, List[int]] = {}
        self._snapshots_by_civ: Dict[int, List[int]] = {}

    def log_event(self, event: CivilizationEvent) -> None:
        """Log a civilization event."""
        event_idx = len(self.events)
        self.events.append(event)

        # Update index
        civ_id = event.civilization_id
        if civ_id not in self._events_by_civ:
            self._events_by_civ[civ_id] = []
        self._events_by_civ[civ_id].append(event_idx)

    def log_snapshot(self, snapshot: CivilizationSnapshot) -> None:
        """Log a civilization state snapshot."""
        snapshot_idx = len(self.snapshots)
        self.snapshots.append(snapshot)

        # Update index
        civ_id = snapshot.civilization_id
        if civ_id not in self._snapshots_by_civ:
            self._snapshots_by_civ[civ_id] = []
        self._snapshots_by_civ[civ_id].append(snapshot_idx)

    # Convenience methods for logging common events

    def log_birth(self, time_myr: float, civilization_id: int,
                  kardashev: float, social_maturity: float,
                  traits: Dict[str, float], **metadata) -> None:
        """Log civilization birth event."""
        event = CivilizationEvent(
            time_myr=time_myr,
            civilization_id=civilization_id,
            event_type=EventType.BIRTH,
            kardashev_level=kardashev,
            social_maturity=social_maturity,
            metadata={'traits': traits, **metadata}
        )
        self.log_event(event)

    def log_death(self, time_myr: float, civilization_id: int,
                  kardashev: float, social_maturity: float,
                  cause: str, **metadata) -> None:
        """Log civilization death event."""
        event = CivilizationEvent(
            time_myr=time_myr,
            civilization_id=civilization_id,
            event_type=EventType.DEATH,
            kardashev_level=kardashev,
            social_maturity=social_maturity,
            metadata={'cause': cause, **metadata}
        )
        self.log_event(event)

    def log_crisis_entered(self, time_myr: float, civilization_id: int,
                          crisis_type: CrisisType, severity: float,
                          kardashev: float, **metadata) -> None:
        """Log entering a crisis."""
        event = CivilizationEvent(
            time_myr=time_myr,
            civilization_id=civilization_id,
            event_type=EventType.CRISIS_ENTERED,
            crisis_type=crisis_type,
            severity=severity,
            kardashev_level=kardashev,
            metadata=metadata
        )
        self.log_event(event)

    def log_crisis_survived(self, time_myr: float, civilization_id: int,
                           crisis_type: CrisisType, kardashev: float,
                           social_maturity: float, **metadata) -> None:
        """Log surviving a crisis."""
        event = CivilizationEvent(
            time_myr=time_myr,
            civilization_id=civilization_id,
            event_type=EventType.CRISIS_SURVIVED,
            crisis_type=crisis_type,
            kardashev_level=kardashev,
            social_maturity=social_maturity,
            metadata=metadata
        )
        self.log_event(event)

    def log_crisis_failed(self, time_myr: float, civilization_id: int,
                         crisis_type: CrisisType, kardashev: float,
                         **metadata) -> None:
        """Log failing a crisis (leads to death)."""
        event = CivilizationEvent(
            time_myr=time_myr,
            civilization_id=civilization_id,
            event_type=EventType.CRISIS_FAILED,
            crisis_type=crisis_type,
            kardashev_level=kardashev,
            metadata=metadata
        )
        self.log_event(event)

    def log_breakthrough(self, time_myr: float, civilization_id: int,
                        breakthrough_type: BreakthroughType,
                        kardashev: float, **metadata) -> None:
        """Log a breakthrough event."""
        event = CivilizationEvent(
            time_myr=time_myr,
            civilization_id=civilization_id,
            event_type=EventType.BREAKTHROUGH,
            breakthrough_type=breakthrough_type,
            kardashev_level=kardashev,
            metadata=metadata
        )
        self.log_event(event)

    def log_aid(self, time_myr: float, giver_id: int, receiver_id: int,
                kardashev_giver: float, **metadata) -> None:
        """Log inter-civilization aid event."""
        # Log for giver
        event_sent = CivilizationEvent(
            time_myr=time_myr,
            civilization_id=giver_id,
            event_type=EventType.AID_SENT,
            helper_civilization_id=receiver_id,
            kardashev_level=kardashev_giver,
            metadata=metadata
        )
        self.log_event(event_sent)

        # Log for receiver
        event_received = CivilizationEvent(
            time_myr=time_myr,
            civilization_id=receiver_id,
            event_type=EventType.AID_RECEIVED,
            helper_civilization_id=giver_id,
            metadata=metadata
        )
        self.log_event(event_received)

    # Query methods

    def get_events_for_civilization(self, civilization_id: int) -> List[CivilizationEvent]:
        """Get all events for a specific civilization."""
        if civilization_id not in self._events_by_civ:
            return []
        indices = self._events_by_civ[civilization_id]
        return [self.events[i] for i in indices]

    def get_snapshots_for_civilization(self, civilization_id: int) -> List[CivilizationSnapshot]:
        """Get all state snapshots for a specific civilization."""
        if civilization_id not in self._snapshots_by_civ:
            return []
        indices = self._snapshots_by_civ[civilization_id]
        return [self.snapshots[i] for i in indices]

    def get_events_by_type(self, event_type: EventType) -> List[CivilizationEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_in_time_range(self, start_myr: float, end_myr: float) -> List[CivilizationEvent]:
        """Get all events within a time range."""
        return [e for e in self.events if start_myr <= e.time_myr <= end_myr]

    def get_civilization_ids(self) -> List[int]:
        """Get all civilization IDs that have been tracked."""
        return list(self._events_by_civ.keys())

    # Analysis methods

    def get_crisis_survival_rate(self, crisis_type: Optional[CrisisType] = None) -> float:
        """
        Calculate survival rate for crises.

        Args:
            crisis_type: Specific crisis type, or None for all crises

        Returns:
            Fraction of crises survived (0.0 to 1.0)
        """
        if crisis_type:
            survived = len([e for e in self.events
                          if e.event_type == EventType.CRISIS_SURVIVED
                          and e.crisis_type == crisis_type])
            failed = len([e for e in self.events
                        if e.event_type == EventType.CRISIS_FAILED
                        and e.crisis_type == crisis_type])
        else:
            survived = len([e for e in self.events
                          if e.event_type == EventType.CRISIS_SURVIVED])
            failed = len([e for e in self.events
                        if e.event_type == EventType.CRISIS_FAILED])

        total = survived + failed
        return survived / total if total > 0 else 0.0

    def get_average_trait_by_outcome(self, trait_name: str) -> Dict[str, float]:
        """
        Get average trait value for civilizations that survived vs died.

        Args:
            trait_name: Name of trait (e.g., 'political_cohesion')

        Returns:
            Dictionary with 'survived' and 'died' averages
        """
        # Get all civilizations and their outcomes
        all_civs = self.get_civilization_ids()

        survived_traits = []
        died_traits = []

        for civ_id in all_civs:
            # Get birth event to get initial traits
            birth_events = [e for e in self.get_events_for_civilization(civ_id)
                          if e.event_type == EventType.BIRTH]
            if not birth_events:
                continue

            traits = birth_events[0].metadata.get('traits', {})
            trait_value = traits.get(trait_name)
            if trait_value is None:
                continue

            # Check if survived any crisis
            civ_events = self.get_events_for_civilization(civ_id)
            survived_any = any(e.event_type == EventType.CRISIS_SURVIVED for e in civ_events)

            if survived_any:
                survived_traits.append(trait_value)
            else:
                died_traits.append(trait_value)

        return {
            'survived': np.mean(survived_traits) if survived_traits else 0.0,
            'died': np.mean(died_traits) if died_traits else 0.0,
            'survived_std': np.std(survived_traits) if survived_traits else 0.0,
            'died_std': np.std(died_traits) if died_traits else 0.0,
            'n_survived': len(survived_traits),
            'n_died': len(died_traits)
        }

    def export_for_chord_diagram(self) -> Dict[str, Any]:
        """
        Export data formatted for chord diagram visualization.

        Shows relationships between:
        - Crisis types and outcomes
        - Breakthrough types and survival
        - Trait levels and outcomes

        Returns:
            Dictionary with nodes and links for chord diagram
        """
        # Build crisis -> outcome flows
        crisis_outcomes = {}
        for event in self.events:
            if event.event_type == EventType.CRISIS_SURVIVED:
                key = (event.crisis_type.value, 'survived')
                crisis_outcomes[key] = crisis_outcomes.get(key, 0) + 1
            elif event.event_type == EventType.CRISIS_FAILED:
                key = (event.crisis_type.value, 'failed')
                crisis_outcomes[key] = crisis_outcomes.get(key, 0) + 1

        # Build breakthrough -> survival flows
        breakthrough_survival = {}
        for civ_id in self.get_civilization_ids():
            civ_events = self.get_events_for_civilization(civ_id)
            breakthroughs = [e for e in civ_events if e.event_type == EventType.BREAKTHROUGH]
            survived_any = any(e.event_type == EventType.CRISIS_SURVIVED for e in civ_events)

            for bt_event in breakthroughs:
                bt_type = bt_event.breakthrough_type.value
                outcome = 'survived' if survived_any else 'failed'
                key = (bt_type, outcome)
                breakthrough_survival[key] = breakthrough_survival.get(key, 0) + 1

        # Format for chord diagram
        nodes = []
        links = []

        # Add crisis type nodes
        for crisis_type in CrisisType:
            nodes.append({'id': crisis_type.value, 'group': 'crisis'})

        # Add outcome nodes
        nodes.append({'id': 'survived', 'group': 'outcome'})
        nodes.append({'id': 'failed', 'group': 'outcome'})

        # Add breakthrough nodes
        for bt_type in BreakthroughType:
            nodes.append({'id': bt_type.value, 'group': 'breakthrough'})

        # Add links
        for (source, target), value in crisis_outcomes.items():
            links.append({'source': source, 'target': target, 'value': value})

        for (source, target), value in breakthrough_survival.items():
            links.append({'source': source, 'target': target, 'value': value})

        return {'nodes': nodes, 'links': links}

    def export_to_dict(self) -> Dict[str, Any]:
        """Export all telemetry data to dictionary for serialization."""
        return {
            'events': [e.to_dict() for e in self.events],
            'snapshots': [s.to_dict() for s in self.snapshots],
            'metadata': {
                'num_civilizations': len(self.get_civilization_ids()),
                'num_events': len(self.events),
                'num_snapshots': len(self.snapshots),
                'time_range_myr': (
                    min(e.time_myr for e in self.events) if self.events else 0,
                    max(e.time_myr for e in self.events) if self.events else 0
                )
            }
        }
