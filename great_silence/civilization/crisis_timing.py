"""
Crisis timing variance system.

Instead of universal crisis thresholds (e.g., all civilizations face nuclear age
at K=1.0), this system personalizes crisis timing based on:
- Development path (fast/slow developers face crises at different times)
- Traits (some civilizations are more vulnerable to certain crises)
- Environmental factors (galactic location, stellar environment)
- Random variance (realistic uncertainty in when crises emerge)

Key Concepts:
- Base crisis thresholds (typical Kardashev level for each crisis)
- Personalized modifiers shift timing for each civilization
- Early/late crisis variants affect difficulty
- Crisis windows (not single points, but ranges where crisis can occur)
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum
import numpy as np


class CrisisType(Enum):
    """Types of civilizational crises."""
    NUCLEAR_AGE = "nuclear_age"
    AI_TRANSITION = "ai_transition"
    BIOTECH_HAZARD = "biotech_hazard"
    NANOTECH_GREY_GOO = "nanotech_grey_goo"
    CLIMATE_COLLAPSE = "climate_collapse"
    RESOURCE_DEPLETION = "resource_depletion"
    STELLAR_ENGINEERING = "stellar_engineering"
    SINGULARITY_TRANSITION = "singularity_transition"


@dataclass
class CrisisThreshold:
    """
    Defines when a crisis typically occurs.

    Attributes:
        base_kardashev: Typical Kardashev level for this crisis
        window_width: Range in K-levels where crisis can occur
            Crisis occurs somewhere in [base - width/2, base + width/2]
        severity_base: Base severity of this crisis [0, 1]
        early_penalty: Additional severity if crisis occurs early
        late_bonus: Severity reduction if crisis occurs late
    """
    base_kardashev: float
    window_width: float = 0.2
    severity_base: float = 0.8
    early_penalty: float = 0.2
    late_bonus: float = 0.15


# Default crisis thresholds
DEFAULT_CRISIS_THRESHOLDS = {
    CrisisType.NUCLEAR_AGE: CrisisThreshold(
        base_kardashev=0.75,
        window_width=0.15,
        severity_base=0.7,
        early_penalty=0.25,
        late_bonus=0.20
    ),
    CrisisType.CLIMATE_COLLAPSE: CrisisThreshold(
        base_kardashev=0.85,
        window_width=0.20,
        severity_base=0.65,
        early_penalty=0.15,
        late_bonus=0.10
    ),
    CrisisType.AI_TRANSITION: CrisisThreshold(
        base_kardashev=1.05,
        window_width=0.25,
        severity_base=0.85,
        early_penalty=0.30,
        late_bonus=0.25
    ),
    CrisisType.BIOTECH_HAZARD: CrisisThreshold(
        base_kardashev=1.15,
        window_width=0.20,
        severity_base=0.75,
        early_penalty=0.20,
        late_bonus=0.15
    ),
    CrisisType.RESOURCE_DEPLETION: CrisisThreshold(
        base_kardashev=1.30,
        window_width=0.30,
        severity_base=0.70,
        early_penalty=0.10,
        late_bonus=0.05
    ),
    CrisisType.NANOTECH_GREY_GOO: CrisisThreshold(
        base_kardashev=1.50,
        window_width=0.25,
        severity_base=0.90,
        early_penalty=0.35,
        late_bonus=0.30
    ),
    CrisisType.STELLAR_ENGINEERING: CrisisThreshold(
        base_kardashev=2.10,
        window_width=0.40,
        severity_base=0.80,
        early_penalty=0.25,
        late_bonus=0.20
    ),
    CrisisType.SINGULARITY_TRANSITION: CrisisThreshold(
        base_kardashev=2.50,
        window_width=0.50,
        severity_base=0.95,
        early_penalty=0.40,
        late_bonus=0.35
    ),
}


@dataclass
class PersonalizedCrisisSchedule:
    """
    Personalized crisis timing for a specific civilization.

    Attributes:
        crisis_kardashev_levels: Actual K-level where each crisis will occur
        crisis_severities: Adjusted severity for each crisis
        crises_triggered: Set of crises already triggered
        crises_survived: Set of crises successfully overcome
    """
    crisis_kardashev_levels: Dict[CrisisType, float] = field(default_factory=dict)
    crisis_severities: Dict[CrisisType, float] = field(default_factory=dict)
    crises_triggered: set = field(default_factory=set)
    crises_survived: set = field(default_factory=set)

    def has_triggered(self, crisis_type: CrisisType) -> bool:
        """Check if crisis has been triggered."""
        return crisis_type in self.crises_triggered

    def has_survived(self, crisis_type: CrisisType) -> bool:
        """Check if crisis has been survived."""
        return crisis_type in self.crises_survived

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'crisis_kardashev_levels': {
                k.value: v for k, v in self.crisis_kardashev_levels.items()
            },
            'crisis_severities': {
                k.value: v for k, v in self.crisis_severities.items()
            },
            'crises_triggered': [c.value for c in self.crises_triggered],
            'crises_survived': [c.value for c in self.crises_survived]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PersonalizedCrisisSchedule':
        """Deserialize from dictionary."""
        return cls(
            crisis_kardashev_levels={
                CrisisType(k): v for k, v in data['crisis_kardashev_levels'].items()
            },
            crisis_severities={
                CrisisType(k): v for k, v in data['crisis_severities'].items()
            },
            crises_triggered={CrisisType(c) for c in data['crises_triggered']},
            crises_survived={CrisisType(c) for c in data['crises_survived']}
        )


class CrisisTimingSystem:
    """
    Manages personalized crisis timing for civilizations.

    Features:
    - Generates unique crisis schedule for each civilization
    - Accounts for traits, development path, environment
    - Adjusts severity based on timing (early/late)
    - Tracks triggered and survived crises
    """

    def __init__(
        self,
        crisis_thresholds: Optional[Dict[CrisisType, CrisisThreshold]] = None,
        seed: Optional[int] = None
    ):
        """
        Initialize crisis timing system.

        Args:
            crisis_thresholds: Crisis threshold definitions
            seed: Random seed
        """
        self.crisis_thresholds = crisis_thresholds or DEFAULT_CRISIS_THRESHOLDS
        self.rng = np.random.default_rng(seed)

    def generate_crisis_schedule(
        self,
        trait_modifiers: Optional[Dict[CrisisType, float]] = None,
        development_path_modifier: float = 0.0,
        environmental_modifier: float = 0.0
    ) -> PersonalizedCrisisSchedule:
        """
        Generate personalized crisis schedule for a civilization.

        Args:
            trait_modifiers: Per-crisis K-level shifts from traits
            development_path_modifier: K-level shift from development speed
            environmental_modifier: K-level shift from galactic environment

        Returns:
            PersonalizedCrisisSchedule
        """
        trait_modifiers = trait_modifiers or {}

        kardashev_levels = {}
        severities = {}

        for crisis_type, threshold in self.crisis_thresholds.items():
            # Start with base threshold
            base_k = threshold.base_kardashev

            # Apply development path modifier
            adjusted_k = base_k + development_path_modifier

            # Apply environmental modifier
            adjusted_k += environmental_modifier

            # Apply trait-specific modifier
            if crisis_type in trait_modifiers:
                adjusted_k += trait_modifiers[crisis_type]

            # Add random variance within window
            variance = self.rng.uniform(
                -threshold.window_width / 2,
                threshold.window_width / 2
            )
            final_k = adjusted_k + variance

            # Calculate severity adjustment based on timing
            timing_offset = final_k - base_k

            if timing_offset < -0.05:
                # Early crisis - harder
                severity_adjustment = min(
                    threshold.early_penalty,
                    abs(timing_offset) * 2.0
                )
                final_severity = threshold.severity_base + severity_adjustment
            elif timing_offset > 0.05:
                # Late crisis - easier
                severity_adjustment = min(
                    threshold.late_bonus,
                    timing_offset * 1.5
                )
                final_severity = threshold.severity_base - severity_adjustment
            else:
                # On-time - base severity
                final_severity = threshold.severity_base

            # Clamp severity
            final_severity = np.clip(final_severity, 0.1, 1.0)

            kardashev_levels[crisis_type] = final_k
            severities[crisis_type] = final_severity

        return PersonalizedCrisisSchedule(
            crisis_kardashev_levels=kardashev_levels,
            crisis_severities=severities
        )

    def calculate_trait_modifiers(
        self,
        technological_wisdom: float,
        risk_tolerance: float,
        resource_abundance: float
    ) -> Dict[CrisisType, float]:
        """
        Calculate crisis timing modifiers from civilization traits.

        Args:
            technological_wisdom: Wisdom trait [0, 1]
            risk_tolerance: Risk tolerance trait [0, 1]
            resource_abundance: Resource abundance trait [0, 1]

        Returns:
            Dict mapping crisis types to K-level shifts
        """
        modifiers = {}

        # High wisdom delays tech crises
        wisdom_effect = (technological_wisdom - 0.5) * 0.2
        modifiers[CrisisType.NUCLEAR_AGE] = wisdom_effect
        modifiers[CrisisType.AI_TRANSITION] = wisdom_effect * 1.5
        modifiers[CrisisType.NANOTECH_GREY_GOO] = wisdom_effect * 1.2

        # High risk tolerance accelerates tech crises
        risk_effect = (risk_tolerance - 0.5) * -0.15
        modifiers[CrisisType.NUCLEAR_AGE] = modifiers.get(CrisisType.NUCLEAR_AGE, 0) + risk_effect
        modifiers[CrisisType.AI_TRANSITION] = modifiers.get(CrisisType.AI_TRANSITION, 0) + risk_effect

        # Low resources accelerate resource crises
        resource_effect = (resource_abundance - 0.5) * 0.25
        modifiers[CrisisType.RESOURCE_DEPLETION] = resource_effect
        modifiers[CrisisType.CLIMATE_COLLAPSE] = resource_effect * 0.8

        return modifiers

    def check_crisis_triggers(
        self,
        schedule: PersonalizedCrisisSchedule,
        current_kardashev: float
    ) -> list[tuple[CrisisType, float]]:
        """
        Check which crises should trigger at current development level.

        Args:
            schedule: Civilization's crisis schedule
            current_kardashev: Current Kardashev level

        Returns:
            List of (crisis_type, severity) for triggered crises
        """
        triggered = []

        for crisis_type, threshold_k in schedule.crisis_kardashev_levels.items():
            # Skip if already triggered
            if schedule.has_triggered(crisis_type):
                continue

            # Trigger if reached threshold
            if current_kardashev >= threshold_k:
                severity = schedule.crisis_severities[crisis_type]
                triggered.append((crisis_type, severity))

        return triggered

    def mark_crisis_triggered(
        self,
        schedule: PersonalizedCrisisSchedule,
        crisis_type: CrisisType
    ) -> PersonalizedCrisisSchedule:
        """
        Mark crisis as triggered.

        Args:
            schedule: Current schedule
            crisis_type: Crisis that was triggered

        Returns:
            Updated schedule
        """
        new_triggered = schedule.crises_triggered.copy()
        new_triggered.add(crisis_type)

        return PersonalizedCrisisSchedule(
            crisis_kardashev_levels=schedule.crisis_kardashev_levels.copy(),
            crisis_severities=schedule.crisis_severities.copy(),
            crises_triggered=new_triggered,
            crises_survived=schedule.crises_survived.copy()
        )

    def mark_crisis_survived(
        self,
        schedule: PersonalizedCrisisSchedule,
        crisis_type: CrisisType
    ) -> PersonalizedCrisisSchedule:
        """
        Mark crisis as survived.

        Args:
            schedule: Current schedule
            crisis_type: Crisis that was survived

        Returns:
            Updated schedule
        """
        new_survived = schedule.crises_survived.copy()
        new_survived.add(crisis_type)

        return PersonalizedCrisisSchedule(
            crisis_kardashev_levels=schedule.crisis_kardashev_levels.copy(),
            crisis_severities=schedule.crisis_severities.copy(),
            crises_triggered=schedule.crises_triggered.copy(),
            crises_survived=new_survived
        )


def format_crisis_schedule(schedule: PersonalizedCrisisSchedule) -> str:
    """
    Get human-readable summary of crisis schedule.

    Args:
        schedule: Crisis schedule to summarize

    Returns:
        Descriptive string
    """
    if not schedule.crisis_kardashev_levels:
        return "No crises scheduled"

    # Get upcoming crises (not yet triggered)
    upcoming = []
    for crisis_type, k_level in sorted(
        schedule.crisis_kardashev_levels.items(),
        key=lambda x: x[1]
    ):
        if not schedule.has_triggered(crisis_type):
            severity = schedule.crisis_severities[crisis_type]
            upcoming.append(f"{crisis_type.value} @ K={k_level:.2f} (severity={severity:.2f})")

    triggered_count = len(schedule.crises_triggered)
    survived_count = len(schedule.crises_survived)

    summary = f"Crises: {triggered_count} triggered, {survived_count} survived. "

    if upcoming:
        summary += f"Next: {upcoming[0]}"
    else:
        summary += "All crises triggered"

    return summary
