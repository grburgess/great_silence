"""Civilization personality modeling with evolution support."""

import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class PersonalityState:
    """Dynamic personality state for a civilization."""

    personality_type: str
    friendliness: float
    aggression_factor: float
    war_trauma: float = 0.0
    victory_confidence: float = 0.5
    evolution_history: list = field(default_factory=list)


def sample_personality(
    kardashev_scale: float,
    rng: np.random.Generator,
    model: str = "kardashev_dependent"
) -> PersonalityState:
    """
    Sample initial personality based on Kardashev scale.

    K-dependent distribution reflects realistic evolution:
    - K < 0.85: Aggressive bias (resource scarcity, competitive)
    - K 0.85-1.5: Mixed (transition phase)
    - K > 1.5: Peaceful bias (energy abundance, post-scarcity)

    Args:
        kardashev_scale: Current technological level
        rng: Random number generator
        model: Personality assignment model ('kardashev_dependent', 'random', 'fixed')

    Returns:
        PersonalityState with sampled traits
    """
    if model == "fixed":
        friendliness = 0.5
        personality_type = "defensive"
    elif model == "random":
        friendliness = rng.uniform(0.1, 0.9)
        personality_type = derive_personality_type(friendliness, rng)
    else:
        mean_friendliness = get_friendliness_distribution_mean(kardashev_scale)
        std_friendliness = 0.15

        friendliness = rng.normal(mean_friendliness, std_friendliness)
        friendliness = np.clip(friendliness, 0.1, 0.9)

        personality_type = derive_personality_type(friendliness, rng)

    aggression_factor = 1.0 - friendliness

    return PersonalityState(
        personality_type=personality_type,
        friendliness=friendliness,
        aggression_factor=aggression_factor
    )


def get_friendliness_distribution_mean(kardashev_scale: float) -> float:
    """
    Get mean friendliness for K-dependent distribution.

    Args:
        kardashev_scale: Current technological level

    Returns:
        Mean friendliness value [0.0, 1.0]
    """
    if kardashev_scale < 0.85:
        return 0.3
    elif kardashev_scale < 1.5:
        return 0.5
    else:
        return 0.7


def derive_personality_type(
    friendliness: float,
    rng: np.random.Generator
) -> str:
    """
    Derive personality type from friendliness.

    Args:
        friendliness: Friendliness value [0.0, 1.0]
        rng: Random number generator

    Returns:
        Personality type string
    """
    if friendliness < 0.3:
        return "expansionist"
    elif friendliness < 0.5:
        return "defensive"
    elif friendliness < 0.7:
        return "isolationist"
    else:
        return "xenophile"


def evolve_personality(
    personality: PersonalityState,
    war_outcome: Optional[str],
    num_wars_lost: int,
    num_wars_won: int,
    rng: np.random.Generator,
    evolution_rate: float = 0.1
) -> PersonalityState:
    """
    Evolve personality based on war outcomes and historical trauma.

    Personality drift mechanisms:
    - War losses increase aggression and reduce friendliness
    - War victories increase confidence
    - Prolonged wars (war trauma) make civs more defensive
    - Xenophiles that lose wars may become isolationist
    - Expansionists that win wars become more aggressive

    Args:
        personality: Current personality state
        war_outcome: Most recent war outcome ('victory', 'defeat', 'stalemate', None)
        num_wars_lost: Total wars lost
        num_wars_won: Total wars won
        rng: Random number generator
        evolution_rate: Rate of personality change per event [0.0, 1.0]

    Returns:
        Updated PersonalityState
    """
    evolved = PersonalityState(
        personality_type=personality.personality_type,
        friendliness=personality.friendliness,
        aggression_factor=personality.aggression_factor,
        war_trauma=personality.war_trauma,
        victory_confidence=personality.victory_confidence,
        evolution_history=personality.evolution_history.copy()
    )

    if war_outcome == "defeat":
        evolved.war_trauma += 0.2 * evolution_rate
        evolved.friendliness -= 0.1 * evolution_rate
        evolved.victory_confidence -= 0.15 * evolution_rate

        if evolved.personality_type == "xenophile":
            evolved.personality_type = "isolationist"
        elif evolved.personality_type == "isolationist":
            evolved.personality_type = "defensive"

    elif war_outcome == "victory":
        evolved.victory_confidence += 0.1 * evolution_rate
        evolved.war_trauma = max(0.0, evolved.war_trauma - 0.1 * evolution_rate)

        if evolved.personality_type == "expansionist":
            evolved.aggression_factor += 0.05 * evolution_rate

    elif war_outcome == "stalemate":
        evolved.war_trauma += 0.1 * evolution_rate
        evolved.victory_confidence -= 0.05 * evolution_rate

    evolved.friendliness = np.clip(evolved.friendliness, 0.1, 0.9)
    evolved.aggression_factor = 1.0 - evolved.friendliness
    evolved.victory_confidence = np.clip(evolved.victory_confidence, 0.1, 0.9)
    evolved.war_trauma = np.clip(evolved.war_trauma, 0.0, 1.0)

    evolved.evolution_history.append({
        'time_step': 'current',
        'outcome': war_outcome,
        'friendliness': evolved.friendliness,
        'type': evolved.personality_type
    })

    return evolved


def get_colony_personality_modifier(
    colony_age_myr: float,
    is_home_world: bool,
    base_personality: PersonalityState
) -> float:
    """
    Get personality modifier for individual colonies.

    Mechanism:
    - Frontiers (young colonies) are more aggressive/expansionist
    - Core colonies (old) are more defensive/peaceful
    - Home worlds have +20% to all traits (cultural center)

    Args:
        colony_age_myr: Age of colony in Myr
        is_home_world: Whether this is the home world
        base_personality: Civilization's base personality

    Returns:
        Modifier multiplier for colony behavior [0.8, 1.2]
    """
    age_factor = np.tanh(colony_age_myr / 0.5)

    if base_personality.personality_type == "expansionist":
        return 1.2 - 0.3 * age_factor
    elif base_personality.personality_type == "xenophile":
        return 0.9 + 0.2 * age_factor
    elif base_personality.personality_type == "defensive":
        return 1.1 + 0.1 * age_factor
    else:
        return 1.0

    if is_home_world:
        return 1.2

    return 1.0
