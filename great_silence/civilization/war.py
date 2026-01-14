"""War mechanics with fleet tracking and causal communication."""

import numpy as np
from typing import Dict, Set, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class BattleOutcome(Enum):
    """Possible outcomes of a battle."""

    ATTACKER_WIN = "attacker_win"
    DEFENDER_WIN = "defender_win"
    STALEMATE = "stalemate"
    MUTUAL_DESTRUCTION = "mutual_destruction"


class WarPhase(Enum):
    """Phases of war."""

    MOBILIZATION = "mobilization"
    OFFENSIVE = "offensive"
    STALEMATE = "stalemate"
    PEACE_NEGOTIATIONS = "peace_negotiations"
    CONCLUDED = "concluded"


@dataclass
class FleetState:
    """State of a military fleet."""

    fleet_id: int
    owner_civ_id: int
    current_star_idx: int
    target_star_idx: Optional[int]
    strength: float
    ships: int
    velocity_c: float
    launch_time_myr: float
    arrival_time_myr: float
    is_in_transit: bool
    mission_type: str  # "attack", "defend", "patrol"


@dataclass
class BattleEvent:
    """Record of a battle."""

    time_myr: float
    star_idx: int
    attacker_civ_id: int
    defender_civ_id: int
    attacker_fleet_id: Optional[int]
    defender_fleet_id: Optional[int]
    outcome: BattleOutcome
    attacker_casualties: float
    defender_casualties: float
    territory_transferred: bool = False


@dataclass
class WarState:
    """State of an ongoing war between two civilizations."""

    enemy_civ_id: int
    start_time_myr: float
    last_encounter_time_myr: float
    phase: WarPhase = WarPhase.MOBILIZATION
    territory_disputed: Set[int] = field(default_factory=set)
    territory_controlled: Dict[int, Set[int]] = field(default_factory=dict)
    casualties_suffered: float = 0.0
    victories: int = 0
    defeats: int = 0
    war_exhaustion: float = 0.0
    peace_proposed: bool = False
    surrender_condition_met: bool = False
    vassalization_offered: bool = False


@dataclass
class CommunicationEvent:
    """Record of a communication between civilizations."""

    time_myr: float
    sender_civ_id: int
    receiver_civ_id: int
    message_type: str  # "peace_offer", "alliance_proposal", "surrender", "war_declaration"
    content: str
    is_within_light_cone: bool
    arrival_time_myr: float


@dataclass
class VassalState:
    """State of a vassal civilization."""

    overlord_civ_id: int
    tribute_rate: float  # Fraction of resources paid to overlord
    military_obligation: bool  # Must provide ships for overlord's wars
    autonomy_level: float  # 0.0 = full control, 1.0 = full independence
    vassal_since_myr: float


def calculate_fleet_strength(
    kardashev_scale: float,
    num_ships: int,
    colony_strength: float,
    fleet_age_myr: float
) -> float:
    """
    Calculate fleet strength.

    Strength depends on:
    - Kardashev scale (higher K = better weapons, shields)
    - Number of ships
    - Colony strength (logistic capacity, shipyards)
    - Fleet experience (older fleets are more experienced)

    Args:
        kardashev_scale: Technological level
        num_ships: Number of ships in fleet
        colony_strength: Strength of supporting colony
        fleet_age_myr: Age of fleet in Myr

    Returns:
        Combined fleet strength
    """
    tech_factor = np.exp(kardashev_scale)
    experience_factor = 1.0 + np.log10(1.0 + fleet_age_myr / 0.1)

    return tech_factor * num_ships * colony_strength * experience_factor


def calculate_colony_strength(
    colony_age_myr: float,
    kardashev_scale: float,
    population: float,
    is_home_world: bool
) -> float:
    """
    Calculate colony strength for defense/offense.

    Older colonies are stronger (more infrastructure).
    Higher K gives better weapons.
    Home worlds have cultural/morale bonus.

    Args:
        colony_age_myr: Age of colony in Myr
        kardashev_scale: Technological level
        population: Colony population (relative units)
        is_home_world: Whether this is the home world

    Returns:
        Colony strength multiplier
    """
    age_factor = 1.0 + np.log10(1.0 + colony_age_myr / 0.05)
    pop_factor = np.log10(1.0 + population)
    tech_factor = np.exp(kardashev_scale * 0.5)
    home_world_bonus = 2.0 if is_home_world else 1.0

    return age_factor * pop_factor * tech_factor * home_world_bonus


def resolve_battle(
    attacker_fleet: FleetState,
    defender_fleet: FleetState,
    colony_strength_defender: float,
    tech_gap: float,
    rng: np.random.Generator
) -> Tuple[BattleOutcome, float, float]:
    """
    Resolve a single battle.

    Battle mechanics:
    - Calculate fleet strengths
    - Apply tech advantage (sigmoid function)
    - Apply defensive terrain bonus (defender in colony gets bonus)
    - Roll for outcome
    - Calculate casualties

    Args:
        attacker_fleet: Attacker's fleet
        defender_fleet: Defender's fleet
        colony_strength_defender: Strength of defending colony
        tech_gap: K_attacker - K_defender
        rng: Random number generator

    Returns:
        (BattleOutcome, attacker_casualties, defender_casualties)
    """
    attacker_strength = calculate_fleet_strength(
        kardashev_scale=1.0,
        num_ships=attacker_fleet.ships,
        colony_strength=1.0,
        fleet_age_myr=0.01
    )

    defender_strength = calculate_fleet_strength(
        kardashev_scale=1.0,
        num_ships=defender_fleet.ships,
        colony_strength=colony_strength_defender,
        fleet_age_myr=0.01
    )

    from scipy.special import expit

    base_win_prob = 0.5 + 0.4 * expit(tech_gap / 0.3)

    terrain_bonus = 1.3

    defender_win_prob = 1.0 - base_win_prob * (1.0 / terrain_bonus)
    defender_win_prob = np.clip(defender_win_prob, 0.0, 1.0)
    attacker_win_prob = 1.0 - defender_win_prob

    roll = rng.uniform(0, 1)

    if roll < attacker_win_prob:
        outcome = BattleOutcome.ATTACKER_WIN
        attacker_casualties = 0.1 + 0.2 * (1.0 - attacker_win_prob)
        defender_casualties = 0.4 + 0.4 * (1.0 - defender_win_prob)
    elif roll < attacker_win_prob + 0.1:
        outcome = BattleOutcome.STALEMATE
        attacker_casualties = 0.2
        defender_casualties = 0.2
    else:
        outcome = BattleOutcome.DEFENDER_WIN
        attacker_casualties = 0.4 + 0.4 * (1.0 - attacker_win_prob)
        defender_casualties = 0.1 + 0.2 * (1.0 - defender_win_prob)

    attacker_casualties *= attacker_fleet.ships
    defender_casualties *= defender_fleet.ships

    return outcome, attacker_casualties, defender_casualties


def calculate_war_duration(
    kardashev_gap: float,
    territory_importance: float,
    initial_strength_ratio: float
) -> float:
    """
    Estimate war duration in Myr.

    Factors:
    - Tech gap: larger gaps = shorter wars (one side dominates)
    - Territory importance: contested core systems = longer wars
    - Initial strength: balanced wars = longer

    Args:
        kardashev_gap: |K_a - K_b|
        territory_importance: 0.0-1.0 (how valuable disputed territory is)
        initial_strength_ratio: strength_a / strength_b

    Returns:
        Expected war duration in Myr
    """
    base_duration = 5.0

    tech_factor = np.exp(-kardashev_gap * 2.0)
    importance_factor = 1.0 + territory_importance * 0.5
    balance_factor = 1.0 + 1.0 / (1.0 + np.log10(initial_strength_ratio))

    return base_duration * tech_factor * importance_factor * balance_factor


def calculate_light_cone_arrival(
    sender_pos: np.ndarray,
    receiver_pos: np.ndarray,
    send_time_myr: float
) -> float:
    """
    Calculate when message arrives given speed of light.

    Args:
        sender_pos: Sender position [x, y, z] in kpc
        receiver_pos: Receiver position [x, y, z] in kpc
        send_time_myr: Time message sent in Myr

    Returns:
        Arrival time in Myr
    """
    distance_kpc = np.linalg.norm(sender_pos - receiver_pos)
    distance_pc = distance_kpc * 1000.0

    c_pc_yr = 0.306601
    travel_time_yr = distance_pc / c_pc_yr
    travel_time_myr = travel_time_yr / 1e6

    return send_time_myr + travel_time_myr


def is_communication_possible(
    sender_pos: np.ndarray,
    receiver_pos: np.ndarray,
    send_time_myr: float,
    receive_time_myr: float
) -> bool:
    """
    Check if communication is causally possible.

    Message must be able to travel at light speed.

    Args:
        sender_pos: Sender position [x, y, z] in kpc
        receiver_pos: Receiver position [x, y, z] in kpc
        send_time_myr: Time message sent in Myr
        receive_time_myr: Time receiver is active in Myr

    Returns:
        True if communication possible
    """
    arrival_time = calculate_light_cone_arrival(sender_pos, receiver_pos, send_time_myr)
    return arrival_time <= receive_time_myr


def check_alliance_cascade_light_cone(
    attacker_civ_id: int,
    defender_civ_id: int,
    ally_positions: Dict[int, np.ndarray],
    war_start_time_myr: float
) -> List[int]:
    """
    Determine which allies can join war based on light cone constraints.

    Allies can only join war if they:
    - Have learned about the war via causal communication
    - Can physically reach the battlefield in reasonable time

    Args:
        attacker_civ_id: Attacker civilization ID
        defender_civ_id: Defender civilization ID
        ally_positions: Dict mapping civ_id -> home world position
        war_start_time_myr: Time war started

    Returns:
        List of ally IDs that can join war
    """
    can_join = []

    if defender_civ_id not in ally_positions:
        return can_join

    defender_pos = ally_positions[defender_civ_id]

    for ally_id, ally_pos in ally_positions.items():
        if ally_id == defender_civ_id:
            continue

        arrival_time = calculate_light_cone_arrival(
            defender_pos, ally_pos, war_start_time_myr
        )

        if arrival_time <= war_start_time_myr + 1.0:
            can_join.append(ally_id)

    return can_join
