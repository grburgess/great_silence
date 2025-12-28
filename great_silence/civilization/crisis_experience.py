"""
Crisis learning and experience system.

This module tracks civilization experience with crises and implements
learning mechanics where surviving crises makes future survival more likely.

Key Concepts:
- Experience bonus: Each survived crisis increases general competence
- Crisis-specific memory: Surviving a specific crisis type helps with that type
- Near-miss learning: Even failed crises teach lessons (if civilization survives)
- Experience decay: Old lessons can be forgotten over time
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import numpy as np


@dataclass
class CrisisExperience:
    """
    Record of civilization's crisis experience.

    Attributes:
        crises_survived: Total number of crises overcome
        crisis_scars: List of crisis types survived (with duplicates)
            ['nuclear_age', 'nuclear_age', 'ai_transition']
            Duplicates indicate surviving the same crisis multiple times.

        crisis_type_counts: Count of each crisis type survived
            {'nuclear_age': 2, 'ai_transition': 1}

        last_crisis_time_myr: Time of most recent crisis
            Used to detect experience decay.

        total_severity_overcome: Cumulative severity of all crises survived
            Harder crises contribute more to competence.

        near_misses: Number of crises barely survived
            Teaches caution but indicates vulnerability.

    Example:
        >>> exp = CrisisExperience(
        ...     crises_survived=2,
        ...     crisis_scars=['nuclear_age', 'ai_transition'],
        ...     crisis_type_counts={'nuclear_age': 1, 'ai_transition': 1}
        ... )
        >>> exp.has_survived_before('nuclear_age')
        True
        >>> exp.get_experience_bonus()
        0.2  # 10% per crisis survived
    """

    crises_survived: int = 0
    crisis_scars: List[str] = field(default_factory=list)
    crisis_type_counts: Dict[str, int] = field(default_factory=dict)
    last_crisis_time_myr: float = 0.0
    total_severity_overcome: float = 0.0
    near_misses: int = 0

    def has_survived_before(self, crisis_type: str) -> bool:
        """Check if this crisis type has been survived before."""
        return crisis_type in self.crisis_scars

    def get_crisis_type_count(self, crisis_type: str) -> int:
        """Get number of times this crisis type was survived."""
        return self.crisis_type_counts.get(crisis_type, 0)

    def get_general_experience_bonus(self) -> float:
        """
        Calculate general experience bonus (all crises).

        Returns:
            Survival probability bonus [0.0, 0.5]
        """
        # Base bonus: 10% per crisis survived (capped at 50%)
        base_bonus = min(0.5, 0.10 * self.crises_survived)

        # Severity bonus: harder crises teach more
        severity_bonus = min(0.2, 0.05 * self.total_severity_overcome)

        return base_bonus + severity_bonus

    def get_specific_experience_bonus(self, crisis_type: str) -> float:
        """
        Calculate experience bonus for specific crisis type.

        If you've survived this exact crisis before, you know how to handle it.

        Args:
            crisis_type: Type of crisis being faced

        Returns:
            Additional survival probability bonus [0.0, 0.5]
        """
        count = self.get_crisis_type_count(crisis_type)

        if count == 0:
            return 0.0
        elif count == 1:
            # First time surviving this type: +25% for next time
            return 0.25
        elif count == 2:
            # Second survival: +35% (diminishing returns)
            return 0.35
        else:
            # Multiple survivals: +45% (capped)
            return 0.45

    def get_total_survival_bonus(self, crisis_type: str) -> float:
        """
        Get combined survival bonus from all experience.

        Args:
            crisis_type: Type of crisis being faced

        Returns:
            Total survival probability bonus
        """
        general = self.get_general_experience_bonus()
        specific = self.get_specific_experience_bonus(crisis_type)

        # Don't stack fully (diminishing returns)
        # If both are high, reduce combined bonus slightly
        combined = general + specific * 0.75

        return min(0.8, combined)  # Cap at +80%

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'crises_survived': self.crises_survived,
            'crisis_scars': self.crisis_scars.copy(),
            'crisis_type_counts': self.crisis_type_counts.copy(),
            'last_crisis_time_myr': self.last_crisis_time_myr,
            'total_severity_overcome': self.total_severity_overcome,
            'near_misses': self.near_misses
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CrisisExperience':
        """Deserialize from dictionary."""
        return cls(
            crises_survived=data['crises_survived'],
            crisis_scars=data['crisis_scars'],
            crisis_type_counts=data['crisis_type_counts'],
            last_crisis_time_myr=data['last_crisis_time_myr'],
            total_severity_overcome=data['total_severity_overcome'],
            near_misses=data['near_misses']
        )


class CrisisLearningSystem:
    """
    Manages learning and experience accumulation from crises.

    Features:
    - Experience tracking
    - Adaptive learning rates
    - Experience decay over long timescales
    - Near-miss learning
    """

    def __init__(
        self,
        experience_decay_timescale_gyr: float = 2.0,
        near_miss_learning_rate: float = 0.5,
        seed: Optional[int] = None
    ):
        """
        Initialize crisis learning system.

        Args:
            experience_decay_timescale_gyr: Time for experience to decay by 50%
                Civilizations can forget lessons over billions of years.
            near_miss_learning_rate: How much near-misses contribute to learning
                0.0 = no learning from near-misses
                1.0 = learn as much from near-miss as from clean success
            seed: Random seed
        """
        self.experience_decay_timescale_gyr = experience_decay_timescale_gyr
        self.near_miss_learning_rate = near_miss_learning_rate
        self.rng = np.random.default_rng(seed)

    def record_crisis_success(
        self,
        experience: CrisisExperience,
        crisis_type: str,
        crisis_severity: float,
        current_time_myr: float,
        was_close_call: bool = False
    ) -> CrisisExperience:
        """
        Record successfully overcoming a crisis.

        Args:
            experience: Current experience state
            crisis_type: Type of crisis survived
            crisis_severity: How severe it was [0, 1]
            current_time_myr: Current simulation time
            was_close_call: Whether it was a near-miss

        Returns:
            Updated CrisisExperience
        """
        # Update counts
        new_survived = experience.crises_survived + 1
        new_scars = experience.crisis_scars + [crisis_type]

        new_type_counts = experience.crisis_type_counts.copy()
        new_type_counts[crisis_type] = new_type_counts.get(crisis_type, 0) + 1

        # Update severity (reduced learning from near-misses)
        learning_multiplier = self.near_miss_learning_rate if was_close_call else 1.0
        new_severity = experience.total_severity_overcome + crisis_severity * learning_multiplier

        # Update near-miss count
        new_near_misses = experience.near_misses + (1 if was_close_call else 0)

        return CrisisExperience(
            crises_survived=new_survived,
            crisis_scars=new_scars,
            crisis_type_counts=new_type_counts,
            last_crisis_time_myr=current_time_myr,
            total_severity_overcome=new_severity,
            near_misses=new_near_misses
        )

    def apply_experience_decay(
        self,
        experience: CrisisExperience,
        current_time_myr: float
    ) -> CrisisExperience:
        """
        Apply experience decay over time.

        Long periods without crises cause some forgetting.

        Args:
            experience: Current experience state
            current_time_myr: Current simulation time

        Returns:
            Updated CrisisExperience with decay applied
        """
        if experience.crises_survived == 0:
            return experience  # Nothing to decay

        # Calculate time since last crisis
        time_since_crisis_gyr = (current_time_myr - experience.last_crisis_time_myr) / 1000.0

        if time_since_crisis_gyr < 0.1:
            return experience  # Too recent for decay

        # Exponential decay: effective_experience = original * exp(-t/tau)
        decay_factor = np.exp(-time_since_crisis_gyr / self.experience_decay_timescale_gyr)

        # Decay severity (represents forgetting)
        new_severity = experience.total_severity_overcome * decay_factor

        # Note: Don't decay crisis_scars (specific memory) or counts
        # Only decay the severity accumulation (general competence)

        return CrisisExperience(
            crises_survived=experience.crises_survived,
            crisis_scars=experience.crisis_scars,
            crisis_type_counts=experience.crisis_type_counts,
            last_crisis_time_myr=experience.last_crisis_time_myr,
            total_severity_overcome=new_severity,
            near_misses=experience.near_misses
        )

    def calculate_learning_from_observation(
        self,
        observer_experience: CrisisExperience,
        observed_crisis_type: str,
        observed_severity: float
    ) -> CrisisExperience:
        """
        Learn from observing another civilization's crisis.

        Inter-civilization knowledge transfer.

        Args:
            observer_experience: Experience of observing civilization
            observed_crisis_type: What type of crisis they saw
            observed_severity: How severe it was

        Returns:
            Updated experience with vicarious learning
        """
        # Vicarious learning is weaker than direct experience
        vicarious_learning_rate = 0.3

        # Only learn from crises you haven't survived yourself
        if observer_experience.has_survived_before(observed_crisis_type):
            return observer_experience  # Already know this

        # Add partial severity credit
        new_severity = (observer_experience.total_severity_overcome +
                       observed_severity * vicarious_learning_rate)

        # Don't add to scars (didn't actually survive it)
        # But might add to type counts at fractional value
        new_type_counts = observer_experience.crisis_type_counts.copy()
        current_count = new_type_counts.get(observed_crisis_type, 0.0)
        new_type_counts[observed_crisis_type] = current_count + vicarious_learning_rate

        return CrisisExperience(
            crises_survived=observer_experience.crises_survived,
            crisis_scars=observer_experience.crisis_scars,
            crisis_type_counts=new_type_counts,
            last_crisis_time_myr=observer_experience.last_crisis_time_myr,
            total_severity_overcome=new_severity,
            near_misses=observer_experience.near_misses
        )

    def estimate_crisis_difficulty_perception(
        self,
        experience: CrisisExperience,
        crisis_type: str,
        actual_severity: float
    ) -> float:
        """
        Estimate how difficult civilization perceives this crisis.

        Experienced civilizations perceive crises as less threatening.

        Args:
            experience: Current experience
            crisis_type: Type of crisis
            actual_severity: Objective severity

        Returns:
            Perceived severity [0, 1]
                < actual_severity if experienced
                > actual_severity if inexperienced (fear/uncertainty)
        """
        if experience.has_survived_before(crisis_type):
            # Experienced: perceive as easier
            times_survived = experience.get_crisis_type_count(crisis_type)
            confidence_factor = min(0.5, 0.15 * times_survived)
            perceived = actual_severity * (1.0 - confidence_factor)
        else:
            # Inexperienced: perceive as harder (uncertainty)
            fear_factor = 0.2
            perceived = actual_severity * (1.0 + fear_factor)

        return np.clip(perceived, 0.0, 1.0)

    def should_trigger_preventive_action(
        self,
        experience: CrisisExperience,
        crisis_type: str,
        current_kardashev: float,
        crisis_kardashev_threshold: float
    ) -> tuple[bool, float]:
        """
        Determine if civilization should take preventive action.

        Experienced civilizations try to prevent crises before they occur.

        Args:
            experience: Current experience
            crisis_type: Type of potential crisis
            current_kardashev: Current tech level
            crisis_kardashev_threshold: Kardashev level where crisis typically occurs

        Returns:
            (should_act, detection_advance_in_k_levels)
        """
        if not experience.has_survived_before(crisis_type):
            return (False, 0.0)  # Don't know to look for it

        # How far in advance to detect (based on experience)
        times_survived = experience.get_crisis_type_count(crisis_type)
        detection_advance = 0.05 * times_survived  # 0.05 K-levels per survival

        # Check if we're approaching the danger zone
        distance_to_crisis = crisis_kardashev_threshold - current_kardashev

        if 0 < distance_to_crisis <= detection_advance:
            return (True, detection_advance)
        else:
            return (False, detection_advance)


def format_experience_summary(experience: CrisisExperience) -> str:
    """
    Get human-readable summary of crisis experience.

    Args:
        experience: Experience to summarize

    Returns:
        Descriptive string
    """
    if experience.crises_survived == 0:
        return "inexperienced (no crises survived)"

    # Categorize experience level
    if experience.crises_survived == 1:
        level = "novice"
    elif experience.crises_survived == 2:
        level = "experienced"
    elif experience.crises_survived >= 5:
        level = "veteran"
    else:
        level = "skilled"

    # List unique crisis types
    unique_types = list(experience.crisis_type_counts.keys())

    # Check for near-misses
    near_miss_note = ""
    if experience.near_misses > 0:
        near_miss_note = f", {experience.near_misses} near-miss{'es' if experience.near_misses > 1 else ''}"

    crisis_list = ", ".join(unique_types)

    return (f"{level} ({experience.crises_survived} {'crises' if experience.crises_survived > 1 else 'crisis'} "
            f"survived{near_miss_note}): {crisis_list}")


def calculate_cumulative_survival_improvement(
    experience: CrisisExperience,
    crisis_type: str,
    base_survival_probability: float
) -> float:
    """
    Calculate final survival probability after applying experience.

    Args:
        experience: Current experience
        crisis_type: Type of crisis being faced
        base_survival_probability: Base probability before experience [0, 1]

    Returns:
        Improved survival probability [0, 1]
    """
    # Get experience bonus
    bonus = experience.get_total_survival_bonus(crisis_type)

    # Apply bonus additively (with cap at 1.0)
    improved = min(1.0, base_survival_probability + bonus)

    return improved
