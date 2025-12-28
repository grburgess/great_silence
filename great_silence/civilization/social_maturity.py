"""
Social maturity system for civilizations.

Social maturity represents wisdom, governance quality, and ethical development,
separate from technological power (Kardashev scale). The ratio between social
maturity and technological power is crucial for survival.

Key Concept:
    Civilizations with high tech but low maturity destroy themselves.
    Civilizations with maturity >= technology survive crises better.
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class SocialMaturityState:
    """
    Current social maturity state of a civilization.

    Attributes:
        maturity_level: Absolute maturity level [0, 3+]
            Similar scale to Kardashev but measures social/ethical development.
            0.5 = tribal societies
            0.7 = early civilizations
            1.0 = planetary governance
            2.0 = interstellar ethics
            3.0 = galactic wisdom

        growth_rate: Current rate of maturity growth (per Myr)
            Base rate is much slower than Kardashev growth.
            Accelerates after crisis survival.

        maturity_to_kardashev_ratio: Wisdom/power ratio
            > 1.0: Wisdom exceeds power (safe)
            ~ 1.0: Balanced
            < 0.5: Power exceeds wisdom (dangerous)

        stagnation_time_myr: Time since last significant growth
            Long stagnation indicates cultural/philosophical plateau.
            May trigger decline or need for breakthrough.

    Example:
        >>> state = SocialMaturityState(
        ...     maturity_level=0.8,
        ...     growth_rate=0.01,
        ...     maturity_to_kardashev_ratio=1.1,
        ...     stagnation_time_myr=0.0
        ... )
        >>> state.is_dangerous()
        False
        >>> state.is_wise()
        True
    """

    maturity_level: float
    growth_rate: float
    maturity_to_kardashev_ratio: float
    stagnation_time_myr: float = 0.0

    def is_wise(self, threshold: float = 1.0) -> bool:
        """Check if civilization is wise (maturity >= tech)."""
        return self.maturity_to_kardashev_ratio >= threshold

    def is_dangerous(self, threshold: float = 0.5) -> bool:
        """Check if civilization is dangerous (tech >> maturity)."""
        return self.maturity_to_kardashev_ratio < threshold

    def is_stagnant(self, threshold_myr: float = 500.0) -> bool:
        """Check if social development has stagnated."""
        return self.stagnation_time_myr > threshold_myr


class SocialMaturityEvolution:
    """
    Handles evolution of social maturity over time.

    Social maturity grows through:
    - Natural cultural development (slow baseline)
    - Crisis survival (accelerated learning)
    - Breakthrough events (sudden jumps)
    - Inter-civilization contact (knowledge transfer)

    But can decline through:
    - Technological overconfidence
    - Long stagnation
    - Failed crisis responses
    """

    def __init__(
        self,
        base_growth_rate: float = 0.01,
        crisis_growth_multiplier: float = 5.0,
        stagnation_threshold_myr: float = 500.0,
        seed: Optional[int] = None
    ):
        """
        Initialize social maturity evolution model.

        Args:
            base_growth_rate: Base maturity growth per Myr (default: 0.01)
                Much slower than Kardashev growth (typically 0.05-0.10)
            crisis_growth_multiplier: How much crises accelerate growth
            stagnation_threshold_myr: Time before growth slows from stagnation
            seed: Random seed for reproducibility
        """
        self.base_growth_rate = base_growth_rate
        self.crisis_growth_multiplier = crisis_growth_multiplier
        self.stagnation_threshold_myr = stagnation_threshold_myr
        self.rng = np.random.default_rng(seed)

    def initialize_maturity(
        self,
        initial_kardashev: float,
        traits: Optional[dict] = None
    ) -> SocialMaturityState:
        """
        Initialize social maturity for a new civilization.

        Starting maturity is typically slightly below Kardashev level
        (technology develops faster than wisdom initially).

        Args:
            initial_kardashev: Starting Kardashev scale
            traits: Civilization traits affecting initial maturity

        Returns:
            Initial SocialMaturityState
        """
        # Start slightly below tech level
        # Add some randomness and trait influence
        base_maturity = initial_kardashev * 0.85

        if traits:
            # Wise civilizations start with higher maturity
            wisdom_bonus = traits.get('technological_wisdom', 0.5) * 0.1
            cohesion_bonus = traits.get('political_cohesion', 0.5) * 0.05
            base_maturity += wisdom_bonus + cohesion_bonus

        # Add small random variation
        maturity = base_maturity + self.rng.normal(0, 0.05)
        maturity = max(0.1, maturity)  # Never start at zero

        # Calculate initial growth rate
        growth_rate = self.base_growth_rate
        if traits:
            adaptability = traits.get('adaptability', 0.5)
            growth_rate *= (0.5 + adaptability)  # [0.5x, 1.5x] base rate

        # Calculate initial ratio
        ratio = maturity / initial_kardashev if initial_kardashev > 0 else 1.0

        return SocialMaturityState(
            maturity_level=maturity,
            growth_rate=growth_rate,
            maturity_to_kardashev_ratio=ratio,
            stagnation_time_myr=0.0
        )

    def advance_maturity(
        self,
        state: SocialMaturityState,
        current_kardashev: float,
        dt_myr: float,
        in_crisis: bool = False,
        traits: Optional[dict] = None
    ) -> SocialMaturityState:
        """
        Advance social maturity by one time step.

        Args:
            state: Current maturity state
            current_kardashev: Current Kardashev level
            dt_myr: Time step in Myr
            in_crisis: Whether civilization is currently in crisis
            traits: Civilization traits

        Returns:
            Updated SocialMaturityState
        """
        # Calculate growth this timestep
        growth_rate = state.growth_rate

        # Crisis accelerates growth
        if in_crisis:
            growth_rate *= self.crisis_growth_multiplier

        # Stagnation slows growth
        if state.stagnation_time_myr > self.stagnation_threshold_myr:
            stagnation_penalty = min(
                0.9,
                (state.stagnation_time_myr - self.stagnation_threshold_myr) / 1000.0
            )
            growth_rate *= (1.0 - stagnation_penalty)

        # Trait modifiers
        if traits:
            adaptability = traits.get('adaptability', 0.5)
            growth_rate *= (0.5 + adaptability)

        # Apply growth
        maturity_gain = growth_rate * dt_myr
        new_maturity = state.maturity_level + maturity_gain

        # Update stagnation timer
        if maturity_gain > 0.001:  # Significant growth
            new_stagnation_time = 0.0
        else:
            new_stagnation_time = state.stagnation_time_myr + dt_myr

        # Update ratio
        new_ratio = new_maturity / current_kardashev if current_kardashev > 0 else 1.0

        return SocialMaturityState(
            maturity_level=new_maturity,
            growth_rate=state.growth_rate,  # Keep original growth rate
            maturity_to_kardashev_ratio=new_ratio,
            stagnation_time_myr=new_stagnation_time
        )

    def apply_crisis_survival_boost(
        self,
        state: SocialMaturityState,
        crisis_severity: float
    ) -> SocialMaturityState:
        """
        Apply maturity boost from surviving a crisis.

        Harder crises teach more profound lessons.

        Args:
            state: Current maturity state
            crisis_severity: How severe the crisis was [0, 1]

        Returns:
            Updated SocialMaturityState with boost applied
        """
        # Immediate maturity jump from learning
        maturity_boost = 0.05 + 0.15 * crisis_severity

        # Permanent increase in growth rate
        growth_rate_boost = 0.001 * crisis_severity

        return SocialMaturityState(
            maturity_level=state.maturity_level + maturity_boost,
            growth_rate=state.growth_rate + growth_rate_boost,
            maturity_to_kardashev_ratio=state.maturity_to_kardashev_ratio,
            stagnation_time_myr=0.0  # Reset stagnation
        )

    def apply_crisis_failure_damage(
        self,
        state: SocialMaturityState,
        crisis_severity: float
    ) -> SocialMaturityState:
        """
        Apply maturity damage from crisis failure or near-miss.

        Failed crises can traumatize societies, reducing cohesion and wisdom.

        Args:
            state: Current maturity state
            crisis_severity: How severe the crisis was [0, 1]

        Returns:
            Updated SocialMaturityState with damage applied
        """
        # Maturity decline from trauma
        maturity_loss = 0.02 + 0.08 * crisis_severity

        # Growth rate also declines (disillusionment)
        growth_rate_loss = 0.002 * crisis_severity

        return SocialMaturityState(
            maturity_level=max(0.1, state.maturity_level - maturity_loss),
            growth_rate=max(0.001, state.growth_rate - growth_rate_loss),
            maturity_to_kardashev_ratio=state.maturity_to_kardashev_ratio,
            stagnation_time_myr=state.stagnation_time_myr
        )

    def apply_breakthrough(
        self,
        state: SocialMaturityState,
        breakthrough_type: str
    ) -> SocialMaturityState:
        """
        Apply maturity changes from breakthrough event.

        Args:
            state: Current maturity state
            breakthrough_type: Type of breakthrough

        Returns:
            Updated SocialMaturityState
        """
        maturity_boost = 0.0
        growth_boost = 0.0

        if breakthrough_type == "philosophical_awakening":
            maturity_boost = 0.20
            growth_boost = 0.005

        elif breakthrough_type == "unification_movement":
            maturity_boost = 0.15
            growth_boost = 0.003

        elif breakthrough_type == "social_reform":
            maturity_boost = 0.10
            growth_boost = 0.004

        elif breakthrough_type == "scientific_revolution":
            # Science alone doesn't increase maturity much
            maturity_boost = 0.05
            growth_boost = 0.001

        return SocialMaturityState(
            maturity_level=state.maturity_level + maturity_boost,
            growth_rate=state.growth_rate + growth_boost,
            maturity_to_kardashev_ratio=state.maturity_to_kardashev_ratio,
            stagnation_time_myr=0.0  # Breakthroughs end stagnation
        )

    def calculate_crisis_survival_modifier(
        self,
        state: SocialMaturityState
    ) -> float:
        """
        Calculate survival probability modifier based on maturity/tech ratio.

        The key insight: civilizations with wisdom >= power survive better.

        Args:
            state: Current maturity state

        Returns:
            Survival probability multiplier
        """
        ratio = state.maturity_to_kardashev_ratio

        if ratio >= 1.5:
            # Very wise: 2x survival chance
            return 2.0
        elif ratio >= 1.0:
            # Wise (balanced): 1.5x survival chance
            return 1.5
        elif ratio >= 0.75:
            # Slightly immature: neutral
            return 1.0
        elif ratio >= 0.5:
            # Dangerous imbalance: 0.5x survival
            return 0.5
        else:
            # Very dangerous: 0.2x survival
            return 0.2

    def check_for_collapse_risk(
        self,
        state: SocialMaturityState,
        current_kardashev: float
    ) -> tuple[bool, float]:
        """
        Check if civilization is at risk of spontaneous collapse.

        Civilizations with very low maturity/tech ratio can self-destruct
        even without a formal crisis.

        Args:
            state: Current maturity state
            current_kardashev: Current technology level

        Returns:
            (is_at_risk, collapse_probability_per_myr)
        """
        ratio = state.maturity_to_kardashev_ratio

        if ratio < 0.3:
            # Extreme danger: power far exceeds wisdom
            return (True, 0.01)  # 1% per Myr
        elif ratio < 0.4:
            # High danger
            return (True, 0.005)  # 0.5% per Myr
        elif ratio < 0.5:
            # Moderate danger
            return (True, 0.001)  # 0.1% per Myr
        else:
            # Safe
            return (False, 0.0)

    def calculate_aid_effectiveness(
        self,
        receiver_state: SocialMaturityState,
        helper_maturity: float
    ) -> float:
        """
        Calculate how effective aid from another civilization is.

        More mature civilizations give better aid.
        Receivers with higher maturity can better utilize aid.

        Args:
            receiver_state: Maturity state of civilization receiving aid
            helper_maturity: Maturity level of civilization giving aid

        Returns:
            Aid effectiveness multiplier [0.5, 2.0]
        """
        # Helper maturity determines quality of aid
        helper_factor = min(helper_maturity, 2.0) / 1.0  # [0, 2.0]

        # Receiver maturity determines absorption capacity
        receiver_factor = min(receiver_state.maturity_level, 1.0) / 0.5  # [0, 2.0]

        # Combined effectiveness
        effectiveness = 0.5 + 0.25 * helper_factor + 0.25 * receiver_factor

        return min(2.0, effectiveness)


def format_maturity_description(state: SocialMaturityState) -> str:
    """
    Get human-readable description of social maturity state.

    Args:
        state: Current maturity state

    Returns:
        Descriptive string
    """
    maturity = state.maturity_level
    ratio = state.maturity_to_kardashev_ratio

    # Maturity level description
    if maturity < 0.5:
        level_desc = "primitive"
    elif maturity < 0.7:
        level_desc = "developing"
    elif maturity < 1.0:
        level_desc = "maturing"
    elif maturity < 1.5:
        level_desc = "advanced"
    elif maturity < 2.0:
        level_desc = "enlightened"
    else:
        level_desc = "transcendent"

    # Ratio description
    if ratio >= 1.5:
        ratio_desc = "very wise"
    elif ratio >= 1.0:
        ratio_desc = "balanced"
    elif ratio >= 0.75:
        ratio_desc = "slightly immature"
    elif ratio >= 0.5:
        ratio_desc = "dangerously immature"
    else:
        ratio_desc = "critically immature"

    return f"{level_desc} ({ratio_desc}, ratio={ratio:.2f})"
