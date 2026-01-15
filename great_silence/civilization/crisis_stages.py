"""
Multi-stage crisis resolution system.

Models crises as processes that unfold over time rather than instant events.
Civilizations can detect, respond to, and potentially resolve crises before
they become lethal.

Key Concepts:
- Crises progress through stages: dormant → emerging → developing → critical
- Early detection allows preventive action
- Response effectiveness determines outcome
- Multiple survival checks throughout crisis
- Experience enables earlier detection and better response
"""

from enum import Enum
from typing import Optional, Tuple
from dataclasses import dataclass
import numpy as np


class CrisisStage(Enum):
    """Stages of crisis development."""
    DORMANT = "dormant"  # Early warning signs, only detected by experienced civs
    EMERGING = "emerging"  # Crisis beginning, widely detectable
    DEVELOPING = "developing"  # Crisis intensifying
    CRITICAL = "critical"  # Peak danger, survival threatened
    RESOLVING = "resolving"  # Active resolution in progress
    RESOLVED = "resolved"  # Successfully overcome
    FAILED = "failed"  # Civilization destroyed


@dataclass
class CrisisState:
    """
    Current state of an ongoing crisis.

    Attributes:
        crisis_type: Type of crisis (e.g., 'nuclear_age', 'ai_transition')
        stage: Current stage of crisis
        severity: Base severity [0, 1] - how dangerous this crisis is
        time_in_stage_myr: How long crisis has been in current stage
        total_duration_myr: Total time crisis has been active
        detection_time_myr: When crisis was first detected
        response_effectiveness: How well civilization is responding [0, 1]
            0 = no response, 1 = perfect response
        stage_advancement_rate: How quickly crisis advances through stages
            Higher = faster progression (worse)
    """
    crisis_type: str
    stage: CrisisStage
    severity: float
    time_in_stage_myr: float = 0.0
    total_duration_myr: float = 0.0
    detection_time_myr: float = 0.0
    response_effectiveness: float = 0.0
    stage_advancement_rate: float = 1.0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'crisis_type': self.crisis_type,
            'stage': self.stage.value,
            'severity': self.severity,
            'time_in_stage_myr': self.time_in_stage_myr,
            'total_duration_myr': self.total_duration_myr,
            'detection_time_myr': self.detection_time_myr,
            'response_effectiveness': self.response_effectiveness,
            'stage_advancement_rate': self.stage_advancement_rate
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CrisisState':
        """Deserialize from dictionary."""
        return cls(
            crisis_type=data['crisis_type'],
            stage=CrisisStage(data['stage']),
            severity=data['severity'],
            time_in_stage_myr=data['time_in_stage_myr'],
            total_duration_myr=data['total_duration_myr'],
            detection_time_myr=data['detection_time_myr'],
            response_effectiveness=data['response_effectiveness'],
            stage_advancement_rate=data['stage_advancement_rate']
        )


class MultiStageCrisisSystem:
    """
    Manages multi-stage crisis progression and resolution.

    Features:
    - Stage-based progression with time delays
    - Early detection for experienced civilizations
    - Response effectiveness affects outcomes
    - Multiple intervention points
    """

    def __init__(
        self,
        stage_durations_myr: Optional[dict] = None,
        seed: Optional[int] = None
    ):
        """
        Initialize multi-stage crisis system.

        Args:
            stage_durations_myr: Expected duration for each stage
                Default: dormant=50, emerging=20, developing=10, critical=5
            seed: Random seed for reproducibility
        """
        self.stage_durations_myr = stage_durations_myr or {
            CrisisStage.DORMANT: 50.0,
            CrisisStage.EMERGING: 20.0,
            CrisisStage.DEVELOPING: 10.0,
            CrisisStage.CRITICAL: 5.0,
            CrisisStage.RESOLVING: 15.0
        }
        self.rng = np.random.default_rng(seed)

    def initiate_crisis(
        self,
        crisis_type: str,
        severity: float,
        has_early_detection: bool = False
    ) -> CrisisState:
        """
        Initiate a new crisis.

        Args:
            crisis_type: Type of crisis
            severity: Base severity [0, 1]
            has_early_detection: Whether civilization detected early (from experience)

        Returns:
            New CrisisState
        """
        # Experienced civilizations detect in dormant stage
        initial_stage = CrisisStage.DORMANT if has_early_detection else CrisisStage.EMERGING

        # Advancement rate varies slightly
        advancement_rate = self.rng.uniform(0.8, 1.2)

        return CrisisState(
            crisis_type=crisis_type,
            stage=initial_stage,
            severity=severity,
            time_in_stage_myr=0.0,
            total_duration_myr=0.0,
            detection_time_myr=0.0,
            response_effectiveness=0.0,
            stage_advancement_rate=advancement_rate
        )

    def advance_crisis(
        self,
        crisis: CrisisState,
        dt_myr: float,
        response_quality: float
    ) -> CrisisState:
        """
        Advance crisis by one timestep.

        Args:
            crisis: Current crisis state
            dt_myr: Time step size
            response_quality: Quality of civilization's response [0, 1]

        Returns:
            Updated CrisisState
        """
        # Don't advance if already terminal
        if crisis.stage in [CrisisStage.RESOLVED, CrisisStage.FAILED]:
            return crisis

        # Update response effectiveness (smoothed)
        new_response = 0.7 * crisis.response_effectiveness + 0.3 * response_quality

        # Update timers
        new_time_in_stage = crisis.time_in_stage_myr + dt_myr
        new_total_duration = crisis.total_duration_myr + dt_myr

        # Check if stage should advance
        expected_duration = self.stage_durations_myr[crisis.stage]

        # Good response slows progression
        effective_advancement = crisis.stage_advancement_rate * (1.5 - new_response)

        should_advance = new_time_in_stage >= (expected_duration / effective_advancement)

        if should_advance:
            new_stage = self._get_next_stage(crisis.stage, new_response)
            new_time_in_stage = 0.0
        else:
            new_stage = crisis.stage

        return CrisisState(
            crisis_type=crisis.crisis_type,
            stage=new_stage,
            severity=crisis.severity,
            time_in_stage_myr=new_time_in_stage,
            total_duration_myr=new_total_duration,
            detection_time_myr=crisis.detection_time_myr,
            response_effectiveness=new_response,
            stage_advancement_rate=crisis.stage_advancement_rate
        )

    def _get_next_stage(
        self,
        current_stage: CrisisStage,
        response_effectiveness: float
    ) -> CrisisStage:
        """
        Determine next stage based on current stage and response.

        Args:
            current_stage: Current stage
            response_effectiveness: How well civilization is responding

        Returns:
            Next stage
        """
        # Strong response can skip to resolving
        if response_effectiveness > 0.8 and current_stage != CrisisStage.CRITICAL:
            return CrisisStage.RESOLVING

        # Normal progression
        stage_sequence = [
            CrisisStage.DORMANT,
            CrisisStage.EMERGING,
            CrisisStage.DEVELOPING,
            CrisisStage.CRITICAL,
            CrisisStage.RESOLVING,
            CrisisStage.RESOLVED
        ]

        try:
            current_idx = stage_sequence.index(current_stage)
            # Skip dormant → emerging if we're already past it
            if current_idx < len(stage_sequence) - 1:
                return stage_sequence[current_idx + 1]
            return current_stage
        except ValueError:
            return current_stage

    def calculate_response_quality(
        self,
        maturity_level: float,
        experience_bonus: float,
        trait_modifiers: float,
        resource_availability: float = 1.0
    ) -> float:
        """
        Calculate quality of civilization's crisis response.

        Args:
            maturity_level: Social maturity level
            experience_bonus: Bonus from past crisis experience
            trait_modifiers: Trait-based modifiers
            resource_availability: Available resources [0, 1]

        Returns:
            Response quality [0, 1]
        """
        # Base response from maturity
        base_response = min(1.0, maturity_level / 1.5)

        # Experience helps
        experience_factor = min(0.3, experience_bonus)

        # Traits affect response
        trait_factor = (trait_modifiers - 1.0) * 0.2  # Convert multiplier to additive

        # Resources enable better response
        resource_factor = resource_availability * 0.2

        # Combine factors
        quality = base_response + experience_factor + trait_factor + resource_factor

        return np.clip(quality, 0.0, 1.0)

    def check_survival(
        self,
        crisis: CrisisState,
        maturity_modifier: float,
        trait_modifier: float,
        experience_bonus: float
    ) -> Tuple[bool, bool]:
        """
        Check if civilization survives this crisis stage.

        Args:
            crisis: Current crisis state
            maturity_modifier: Multiplier from social maturity
            trait_modifier: Multiplier from traits
            experience_bonus: Additive bonus from experience

        Returns:
            (survived, was_close_call)
        """
        # Base survival probability depends on stage
        stage_survival = {
            CrisisStage.DORMANT: 0.99,      # Almost no danger
            CrisisStage.EMERGING: 0.95,     # Low danger
            CrisisStage.DEVELOPING: 0.85,   # Moderate danger
            CrisisStage.CRITICAL: 0.50,     # High danger
            CrisisStage.RESOLVING: 0.90,    # Danger receding
        }

        base_survival = stage_survival.get(crisis.stage, 0.95)

        # Severity reduces survival
        severity_penalty = crisis.severity * 0.3
        adjusted_survival = base_survival * (1.0 - severity_penalty)

        # Response effectiveness helps
        response_bonus = crisis.response_effectiveness * 0.2
        adjusted_survival += response_bonus

        # Apply modifiers
        adjusted_survival *= maturity_modifier
        adjusted_survival *= trait_modifier
        adjusted_survival += experience_bonus

        # Cap at reasonable values
        final_survival = np.clip(adjusted_survival, 0.01, 0.99)

        # Roll for survival
        roll = self.rng.random()
        survived = roll < final_survival

        # Close call if survived but was close
        was_close_call = survived and (final_survival - roll < 0.1)

        return (survived, was_close_call)

    def can_resolve_crisis(
        self,
        crisis: CrisisState
    ) -> bool:
        """
        Check if crisis can be resolved (successful outcome).

        Args:
            crisis: Current crisis state

        Returns:
            True if crisis successfully resolved
        """
        if crisis.stage != CrisisStage.RESOLVING:
            return False

        # Need good response and enough time
        return (crisis.response_effectiveness > 0.6 and
                crisis.time_in_stage_myr > 5.0)

    def get_stage_description(self, stage: CrisisStage) -> str:
        """
        Get human-readable description of crisis stage.

        Args:
            stage: Crisis stage

        Returns:
            Descriptive string
        """
        descriptions = {
            CrisisStage.DORMANT: "Early warning signs detected",
            CrisisStage.EMERGING: "Crisis beginning to emerge",
            CrisisStage.DEVELOPING: "Crisis intensifying",
            CrisisStage.CRITICAL: "Peak danger - survival threatened",
            CrisisStage.RESOLVING: "Crisis being actively addressed",
            CrisisStage.RESOLVED: "Crisis successfully overcome",
            CrisisStage.FAILED: "Civilization destroyed"
        }
        return descriptions[stage]


def format_crisis_summary(crisis: CrisisState) -> str:
    """
    Get human-readable summary of crisis state.

    Args:
        crisis: Crisis to summarize

    Returns:
        Descriptive string
    """
    stage_name = crisis.stage.value.replace('_', ' ').title()
    response_desc = "excellent" if crisis.response_effectiveness > 0.8 else \
                   "good" if crisis.response_effectiveness > 0.6 else \
                   "moderate" if crisis.response_effectiveness > 0.4 else \
                   "poor" if crisis.response_effectiveness > 0.2 else "none"

    return (f"{crisis.crisis_type.replace('_', ' ').title()}: "
            f"{stage_name} (severity={crisis.severity:.2f}, "
            f"response={response_desc}, "
            f"duration={crisis.total_duration_myr:.1f} Myr)")
