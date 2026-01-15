"""
Breakthrough event system for civilizations.

Breakthroughs are rare, positive events that can accelerate social maturity
and provide survival advantages. They represent pivotal moments in a
civilization's development - philosophical awakenings, social reforms,
unification movements, etc.

Key Concepts:
- Probability increases with civilization age and maturity
- Different breakthrough types have different triggers and effects
- Stagnation increases likelihood of breakthroughs (desperation)
- Breakthroughs can be triggered by crisis survival (post-traumatic growth)
"""

from enum import Enum
from typing import Optional, Tuple
from dataclasses import dataclass
import numpy as np


class BreakthroughType(Enum):
    """Types of breakthrough events."""
    PHILOSOPHICAL_AWAKENING = "philosophical_awakening"
    UNIFICATION_MOVEMENT = "unification_movement"
    SOCIAL_REFORM = "social_reform"
    SCIENTIFIC_REVOLUTION = "scientific_revolution"
    CULTURAL_RENAISSANCE = "cultural_renaissance"
    ETHICAL_ENLIGHTENMENT = "ethical_enlightenment"


@dataclass
class BreakthroughProbabilities:
    """
    Breakthrough probabilities per Myr for different types.

    Attributes:
        base_rate: Base probability per Myr for any breakthrough
        stagnation_multiplier: How much stagnation increases probability
        post_crisis_multiplier: Probability boost after crisis survival
        maturity_threshold: Minimum maturity level for advanced breakthroughs
    """
    base_rate: float = 0.001  # 0.1% per Myr (rare events)
    stagnation_multiplier: float = 3.0
    post_crisis_multiplier: float = 5.0
    maturity_threshold: float = 0.8


class BreakthroughSystem:
    """
    Manages breakthrough event generation and selection.

    Features:
    - Age-dependent probability (older civs more likely to breakthrough)
    - Maturity-dependent type selection
    - Stagnation triggers breakthroughs
    - Post-crisis breakthroughs (growth from adversity)
    """

    def __init__(
        self,
        probabilities: Optional[BreakthroughProbabilities] = None,
        seed: Optional[int] = None
    ):
        """
        Initialize breakthrough system.

        Args:
            probabilities: Breakthrough probability parameters
            seed: Random seed for reproducibility
        """
        self.probabilities = probabilities or BreakthroughProbabilities()
        self.rng = np.random.default_rng(seed)

    def check_for_breakthrough(
        self,
        civilization_age_myr: float,
        maturity_level: float,
        stagnation_time_myr: float,
        dt_myr: float,
        recently_survived_crisis: bool = False
    ) -> Tuple[bool, Optional[BreakthroughType]]:
        """
        Check if a breakthrough occurs this timestep.

        Args:
            civilization_age_myr: Age of civilization in Myr
            maturity_level: Current social maturity level
            stagnation_time_myr: Time since last significant growth
            dt_myr: Time step size in Myr
            recently_survived_crisis: Whether just survived a crisis

        Returns:
            (breakthrough_occurred, breakthrough_type)
        """
        # Calculate breakthrough probability
        prob = self._calculate_breakthrough_probability(
            civilization_age_myr,
            maturity_level,
            stagnation_time_myr,
            recently_survived_crisis
        )

        # Scale by timestep
        prob_this_step = prob * dt_myr

        # Roll for breakthrough
        if self.rng.random() < prob_this_step:
            breakthrough_type = self._select_breakthrough_type(
                maturity_level,
                stagnation_time_myr,
                recently_survived_crisis
            )
            return (True, breakthrough_type)

        return (False, None)

    def _calculate_breakthrough_probability(
        self,
        civilization_age_myr: float,
        maturity_level: float,
        stagnation_time_myr: float,
        recently_survived_crisis: bool
    ) -> float:
        """
        Calculate breakthrough probability per Myr.

        Args:
            civilization_age_myr: Age of civilization
            maturity_level: Current maturity
            stagnation_time_myr: Stagnation time
            recently_survived_crisis: Post-crisis state

        Returns:
            Probability per Myr
        """
        prob = self.probabilities.base_rate

        # Age factor: older civilizations more likely to breakthrough
        # Logarithmic scaling to prevent runaway probability
        if civilization_age_myr > 100:
            age_factor = 1.0 + 0.5 * np.log10(civilization_age_myr / 100.0)
            prob *= age_factor

        # Maturity factor: more mature civs have better infrastructure for breakthroughs
        maturity_factor = 0.5 + maturity_level
        prob *= maturity_factor

        # Stagnation increases probability (desperation/need for change)
        if stagnation_time_myr > 500.0:
            stagnation_factor = self.probabilities.stagnation_multiplier
            prob *= stagnation_factor

        # Post-crisis breakthrough (adversity drives innovation)
        if recently_survived_crisis:
            prob *= self.probabilities.post_crisis_multiplier

        return prob

    def _select_breakthrough_type(
        self,
        maturity_level: float,
        stagnation_time_myr: float,
        recently_survived_crisis: bool
    ) -> BreakthroughType:
        """
        Select which type of breakthrough occurs.

        Different civilization states favor different breakthroughs.

        Args:
            maturity_level: Current maturity level
            stagnation_time_myr: Stagnation time
            recently_survived_crisis: Post-crisis state

        Returns:
            Selected breakthrough type
        """
        # Build weighted probability distribution
        weights = {}

        # Philosophical awakening: most powerful, requires maturity
        if maturity_level >= self.probabilities.maturity_threshold:
            weights[BreakthroughType.PHILOSOPHICAL_AWAKENING] = 1.0
        else:
            weights[BreakthroughType.PHILOSOPHICAL_AWAKENING] = 0.2

        # Unification movement: helps with cohesion, good for stagnant civs
        if stagnation_time_myr > 500:
            weights[BreakthroughType.UNIFICATION_MOVEMENT] = 2.0
        else:
            weights[BreakthroughType.UNIFICATION_MOVEMENT] = 1.0

        # Social reform: general improvement
        weights[BreakthroughType.SOCIAL_REFORM] = 1.5

        # Scientific revolution: tech-focused, less maturity gain
        weights[BreakthroughType.SCIENTIFIC_REVOLUTION] = 1.0

        # Cultural renaissance: creativity boost
        weights[BreakthroughType.CULTURAL_RENAISSANCE] = 1.2

        # Ethical enlightenment: high maturity civs, post-crisis
        if recently_survived_crisis and maturity_level >= 0.7:
            weights[BreakthroughType.ETHICAL_ENLIGHTENMENT] = 2.5
        else:
            weights[BreakthroughType.ETHICAL_ENLIGHTENMENT] = 0.5

        # Sample from weighted distribution
        types = list(weights.keys())
        probs = np.array([weights[t] for t in types])
        probs = probs / probs.sum()  # Normalize

        selected_idx = self.rng.choice(len(types), p=probs)
        return types[selected_idx]

    def get_breakthrough_description(self, breakthrough_type: BreakthroughType) -> str:
        """
        Get human-readable description of breakthrough.

        Args:
            breakthrough_type: Type of breakthrough

        Returns:
            Descriptive string
        """
        descriptions = {
            BreakthroughType.PHILOSOPHICAL_AWAKENING: (
                "Philosophical Awakening: Deep shift in worldview, "
                "fundamental questions about existence and purpose"
            ),
            BreakthroughType.UNIFICATION_MOVEMENT: (
                "Unification Movement: Political/cultural unification, "
                "overcoming divisions and building consensus"
            ),
            BreakthroughType.SOCIAL_REFORM: (
                "Social Reform: Restructuring of institutions, "
                "justice systems, and social contracts"
            ),
            BreakthroughType.SCIENTIFIC_REVOLUTION: (
                "Scientific Revolution: Major paradigm shift in understanding, "
                "new technologies and capabilities"
            ),
            BreakthroughType.CULTURAL_RENAISSANCE: (
                "Cultural Renaissance: Flowering of arts, philosophy, "
                "and creative expression"
            ),
            BreakthroughType.ETHICAL_ENLIGHTENMENT: (
                "Ethical Enlightenment: Fundamental shift in moral reasoning, "
                "expansion of circle of compassion"
            ),
        }
        return descriptions[breakthrough_type]

    def get_maturity_impact(self, breakthrough_type: BreakthroughType) -> Tuple[float, float]:
        """
        Get maturity and growth rate impact for breakthrough type.

        Args:
            breakthrough_type: Type of breakthrough

        Returns:
            (maturity_boost, growth_rate_boost)
        """
        impacts = {
            BreakthroughType.PHILOSOPHICAL_AWAKENING: (0.20, 0.005),
            BreakthroughType.UNIFICATION_MOVEMENT: (0.15, 0.003),
            BreakthroughType.SOCIAL_REFORM: (0.10, 0.004),
            BreakthroughType.SCIENTIFIC_REVOLUTION: (0.05, 0.001),
            BreakthroughType.CULTURAL_RENAISSANCE: (0.12, 0.003),
            BreakthroughType.ETHICAL_ENLIGHTENMENT: (0.18, 0.006),
        }
        return impacts[breakthrough_type]


def format_breakthrough_summary(
    breakthrough_count: int,
    breakthrough_types: list[BreakthroughType]
) -> str:
    """
    Get human-readable summary of breakthroughs.

    Args:
        breakthrough_count: Total number of breakthroughs
        breakthrough_types: List of breakthrough types experienced

    Returns:
        Descriptive string
    """
    if breakthrough_count == 0:
        return "No breakthroughs achieved"

    # Count occurrences of each type
    type_counts = {}
    for bt in breakthrough_types:
        type_counts[bt] = type_counts.get(bt, 0) + 1

    # Format summary
    summary_parts = []
    for bt, count in type_counts.items():
        name = bt.value.replace('_', ' ').title()
        if count > 1:
            summary_parts.append(f"{name} (x{count})")
        else:
            summary_parts.append(name)

    breakthroughs_text = "breakthrough" if breakthrough_count == 1 else "breakthroughs"
    return f"{breakthrough_count} {breakthroughs_text}: {', '.join(summary_parts)}"
