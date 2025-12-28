"""
Cooperative survival mechanics.

Models civilizations helping each other survive through:
- Knowledge sharing (crisis experience transfer)
- Technology transfer (advancing less developed civilizations)
- Direct intervention (active assistance during crises)
- Alliance formation (groups with shared survival interests)

Key Concepts:
- Distance matters: closer civilizations can cooperate more effectively
- Maturity matters: more mature civilizations give better aid
- Reciprocity: civilizations remember who helped them
- Detection: must be aware of each other to cooperate
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
import numpy as np


class CooperationType(Enum):
    """Types of cooperative interactions."""
    KNOWLEDGE_SHARING = "knowledge_sharing"
    TECHNOLOGY_TRANSFER = "technology_transfer"
    CRISIS_INTERVENTION = "crisis_intervention"
    JOINT_RESEARCH = "joint_research"
    RESOURCE_SHARING = "resource_sharing"


@dataclass
class CooperationRecord:
    """
    Record of a cooperative interaction.

    Attributes:
        time_myr: When cooperation occurred
        helper_id: ID of civilization providing aid
        receiver_id: ID of civilization receiving aid
        cooperation_type: Type of cooperation
        effectiveness: How effective the cooperation was [0, 1]
        distance_pc: Distance between civilizations in parsecs
    """
    time_myr: float
    helper_id: int
    receiver_id: int
    cooperation_type: CooperationType
    effectiveness: float
    distance_pc: float


@dataclass
class CooperationHistory:
    """
    Track cooperation relationships over time.

    Attributes:
        received_aid: Record of aid received from others
        given_aid: Record of aid given to others
        active_allies: Set of civilization IDs currently allied with
        aid_debt: Dict tracking who we owe (positive) or who owes us (negative)
    """
    received_aid: List[CooperationRecord] = field(default_factory=list)
    given_aid: List[CooperationRecord] = field(default_factory=list)
    active_allies: set = field(default_factory=set)
    aid_debt: Dict[int, float] = field(default_factory=dict)

    def has_received_aid_from(self, helper_id: int) -> bool:
        """Check if received aid from specific civilization."""
        return any(r.helper_id == helper_id for r in self.received_aid)

    def has_given_aid_to(self, receiver_id: int) -> bool:
        """Check if given aid to specific civilization."""
        return any(r.receiver_id == receiver_id for r in self.given_aid)

    def is_allied_with(self, civ_id: int) -> bool:
        """Check if allied with civilization."""
        return civ_id in self.active_allies

    def get_aid_received_count(self) -> int:
        """Get total count of aid received."""
        return len(self.received_aid)

    def get_aid_given_count(self) -> int:
        """Get total count of aid given."""
        return len(self.given_aid)


class CooperationSystem:
    """
    Manages cooperative interactions between civilizations.

    Features:
    - Calculates cooperation effectiveness based on multiple factors
    - Tracks cooperation history and relationships
    - Models reciprocity and alliance dynamics
    - Distance-limited cooperation (light-speed constraints)
    """

    def __init__(
        self,
        max_cooperation_distance_pc: float = 1000.0,
        alliance_formation_threshold: float = 0.7,
        reciprocity_bonus: float = 0.3,
        seed: Optional[int] = None
    ):
        """
        Initialize cooperation system.

        Args:
            max_cooperation_distance_pc: Maximum distance for effective cooperation
            alliance_formation_threshold: Maturity threshold for forming alliances
            reciprocity_bonus: Bonus for helping those who helped you
            seed: Random seed
        """
        self.max_cooperation_distance_pc = max_cooperation_distance_pc
        self.alliance_formation_threshold = alliance_formation_threshold
        self.reciprocity_bonus = reciprocity_bonus
        self.rng = np.random.default_rng(seed)

    def can_cooperate(
        self,
        distance_pc: float,
        helper_kardashev: float,
        receiver_kardashev: float
    ) -> bool:
        """
        Check if cooperation is possible between two civilizations.

        Args:
            distance_pc: Distance between civilizations
            helper_kardashev: Tech level of helper
            receiver_kardashev: Tech level of receiver

        Returns:
            True if cooperation is possible
        """
        # Too far to cooperate
        if distance_pc > self.max_cooperation_distance_pc:
            return False

        # Helper must be sufficiently advanced
        if helper_kardashev < 0.9:
            return False

        # Can't help civilizations too far ahead
        if receiver_kardashev > helper_kardashev + 0.5:
            return False

        return True

    def calculate_cooperation_effectiveness(
        self,
        distance_pc: float,
        helper_maturity: float,
        receiver_maturity: float,
        helper_kardashev: float,
        cooperation_type: CooperationType,
        has_prior_relationship: bool = False
    ) -> float:
        """
        Calculate effectiveness of cooperative interaction.

        Args:
            distance_pc: Distance between civilizations
            helper_maturity: Social maturity of helper
            receiver_maturity: Social maturity of receiver
            helper_kardashev: Tech level of helper
            cooperation_type: Type of cooperation
            has_prior_relationship: Whether they've cooperated before

        Returns:
            Effectiveness [0, 1]
        """
        # Base effectiveness from helper maturity
        base_effectiveness = min(1.0, helper_maturity / 1.5)

        # Distance penalty (exponential falloff)
        distance_factor = np.exp(-distance_pc / (self.max_cooperation_distance_pc / 2))

        # Receiver maturity affects ability to receive aid
        receiver_factor = 0.3 + 0.7 * min(1.0, receiver_maturity / 1.0)

        # Tech level of helper matters
        tech_factor = min(1.0, helper_kardashev / 1.5)

        # Cooperation type has different base effectiveness
        type_factors = {
            CooperationType.KNOWLEDGE_SHARING: 1.0,
            CooperationType.TECHNOLOGY_TRANSFER: 0.8,
            CooperationType.CRISIS_INTERVENTION: 0.9,
            CooperationType.JOINT_RESEARCH: 0.85,
            CooperationType.RESOURCE_SHARING: 0.75
        }
        type_factor = type_factors.get(cooperation_type, 0.7)

        # Prior relationship bonus
        relationship_bonus = self.reciprocity_bonus if has_prior_relationship else 0.0

        # Combine factors
        effectiveness = (
            base_effectiveness *
            distance_factor *
            receiver_factor *
            tech_factor *
            type_factor +
            relationship_bonus
        )

        return np.clip(effectiveness, 0.0, 1.0)

    def calculate_crisis_aid_benefit(
        self,
        effectiveness: float,
        crisis_severity: float
    ) -> float:
        """
        Calculate survival probability increase from crisis aid.

        Args:
            effectiveness: Cooperation effectiveness
            crisis_severity: Severity of crisis being faced

        Returns:
            Survival probability boost [0, 0.5]
        """
        # More severe crises benefit more from aid (desperation)
        severity_factor = 0.5 + 0.5 * crisis_severity

        # Aid provides survival boost
        boost = effectiveness * severity_factor * 0.5  # Cap at +50%

        return min(0.5, boost)

    def should_offer_aid(
        self,
        helper_maturity: float,
        helper_kardashev: float,
        receiver_in_crisis: bool,
        relationship_history: bool,
        helper_resources: float = 1.0
    ) -> bool:
        """
        Determine if civilization should offer aid.

        Args:
            helper_maturity: Social maturity of potential helper
            helper_kardashev: Tech level of helper
            receiver_in_crisis: Whether receiver is in crisis
            relationship_history: Whether they have prior relationship
            helper_resources: Available resources [0, 1]

        Returns:
            True if should offer aid
        """
        # Need minimum maturity to be altruistic
        if helper_maturity < 0.7:
            return False

        # Need minimum tech to provide meaningful aid
        if helper_kardashev < 0.9:
            return False

        # Need sufficient resources
        if helper_resources < 0.3:
            return False

        # Calculate willingness probability
        base_willingness = (helper_maturity - 0.7) / 0.5  # [0, 1] for maturity [0.7, 1.2]

        # Crisis increases urgency
        crisis_factor = 2.0 if receiver_in_crisis else 1.0

        # Prior relationship increases willingness
        relationship_factor = 1.5 if relationship_history else 1.0

        # Resource availability
        resource_factor = helper_resources

        willingness = min(
            1.0,
            base_willingness * crisis_factor * relationship_factor * resource_factor
        )

        # Probabilistic decision
        return self.rng.random() < willingness

    def form_alliance(
        self,
        history1: CooperationHistory,
        history2: CooperationHistory,
        civ1_id: int,
        civ2_id: int,
        civ1_maturity: float,
        civ2_maturity: float
    ) -> tuple[CooperationHistory, CooperationHistory]:
        """
        Form alliance between two civilizations.

        Args:
            history1: Cooperation history of civ 1
            history2: Cooperation history of civ 2
            civ1_id: ID of civilization 1
            civ2_id: ID of civilization 2
            civ1_maturity: Maturity of civ 1
            civ2_maturity: Maturity of civ 2

        Returns:
            (updated_history1, updated_history2)
        """
        # Both must be sufficiently mature
        if (civ1_maturity < self.alliance_formation_threshold or
            civ2_maturity < self.alliance_formation_threshold):
            return (history1, history2)

        # Add to each other's ally sets
        new_allies1 = history1.active_allies.copy()
        new_allies1.add(civ2_id)

        new_allies2 = history2.active_allies.copy()
        new_allies2.add(civ1_id)

        # Create updated histories
        updated1 = CooperationHistory(
            received_aid=history1.received_aid.copy(),
            given_aid=history1.given_aid.copy(),
            active_allies=new_allies1,
            aid_debt=history1.aid_debt.copy()
        )

        updated2 = CooperationHistory(
            received_aid=history2.received_aid.copy(),
            given_aid=history2.given_aid.copy(),
            active_allies=new_allies2,
            aid_debt=history2.aid_debt.copy()
        )

        return (updated1, updated2)

    def record_cooperation(
        self,
        helper_history: CooperationHistory,
        receiver_history: CooperationHistory,
        record: CooperationRecord,
        helper_id: int,
        receiver_id: int
    ) -> tuple[CooperationHistory, CooperationHistory]:
        """
        Record cooperative interaction in both histories.

        Args:
            helper_history: History of helper civilization
            receiver_history: History of receiver civilization
            record: Cooperation record to add
            helper_id: ID of helper
            receiver_id: ID of receiver

        Returns:
            (updated_helper_history, updated_receiver_history)
        """
        # Update helper's given aid
        new_given = helper_history.given_aid.copy()
        new_given.append(record)

        # Update helper's debt (they are owed)
        new_debt_helper = helper_history.aid_debt.copy()
        new_debt_helper[receiver_id] = new_debt_helper.get(receiver_id, 0.0) + record.effectiveness

        updated_helper = CooperationHistory(
            received_aid=helper_history.received_aid.copy(),
            given_aid=new_given,
            active_allies=helper_history.active_allies.copy(),
            aid_debt=new_debt_helper
        )

        # Update receiver's received aid
        new_received = receiver_history.received_aid.copy()
        new_received.append(record)

        # Update receiver's debt (they owe)
        new_debt_receiver = receiver_history.aid_debt.copy()
        new_debt_receiver[helper_id] = new_debt_receiver.get(helper_id, 0.0) - record.effectiveness

        updated_receiver = CooperationHistory(
            received_aid=new_received,
            given_aid=receiver_history.given_aid.copy(),
            active_allies=receiver_history.active_allies.copy(),
            aid_debt=new_debt_receiver
        )

        return (updated_helper, updated_receiver)


def format_cooperation_summary(history: CooperationHistory) -> str:
    """
    Get human-readable summary of cooperation history.

    Args:
        history: Cooperation history to summarize

    Returns:
        Descriptive string
    """
    received = history.get_aid_received_count()
    given = history.get_aid_given_count()
    allies = len(history.active_allies)

    if received == 0 and given == 0 and allies == 0:
        return "Isolated (no cooperation)"

    summary_parts = []

    if received > 0:
        summary_parts.append(f"received {received} aid")
    if given > 0:
        summary_parts.append(f"gave {given} aid")
    if allies > 0:
        summary_parts.append(f"{allies} active {'allies' if allies > 1 else 'ally'}")

    return "Cooperative: " + ", ".join(summary_parts)
