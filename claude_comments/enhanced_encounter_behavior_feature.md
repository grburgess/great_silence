# Enhanced Encounter Behavior Feature

## Overview
Inter-civilization dynamics with personality-driven AI, war mechanics, reputation system, alliance cascades, and light-cone causal communication.

## Architecture

### New Modules

**civilization/personality.py**
- `PersonalityState`: Dynamic personality dataclass
- `sample_personality()`: K-dependent personality sampling
- `evolve_personality()`: Personality drift based on war outcomes
- `get_colony_personality_modifier()`: Colony-specific behavior

**civilization/war.py**
- `FleetState`: Military fleet tracking with movement
- `WarState`: Enhanced war state with phases
- `BattleEvent`: Individual battle records
- `CommunicationEvent`: Causal communication tracking
- `VassalState`: Vassal civilization data
- `resolve_battle()`: Combat mechanics with colony strength
- `calculate_light_cone_arrival()`: Causal communication timing
- `check_alliance_cascade_light_cone()`: Alliance causality checks

**utils/civ_spatial_index.py**
- `CivilizationSpatialIndex`: O(log N) territory queries
- `add_colony()`: Register colony in spatial index
- `find_territory_overlaps()`: Fast overlap detection
- `find_frontier_colonies()`: Identify contested borders

### Updated Data Structures

**CivilizationState** additions:
```python
# Personality
personality_type: str          # "expansionist", "defensive", "xenophile", "isolationist"
friendliness: float             # [0.0, 1.0] aggression <-> peaceful
aggression_factor: float
war_trauma: float
victory_confidence: float

# Relations
known_civilizations: Set[int]
reputation: Dict[int, float]    # civ_id -> [-1.0, 1.0]
allies: Set[int]
enemies: Set[int]
vassals: Dict[int, VassalState]
overlord: Optional[int]

# War
war_state: Optional[WarState]
battles_fought: int
wars_won: int
wars_lost: int

# Military
active_fleets: List[FleetState]
archived_fleets: List[FleetState]
next_fleet_id: int

# Economy
strategic_resource_stockpile: float
resource_debt: float
war_exhaustion: float

# Colonies
colony_strengths: Dict[int, float]  # star_idx -> dynamic strength
```

**SimulationSnapshot** additions:
```python
encounter_events: List[EncounterEvent]
communication_events: List[CommunicationEvent]
battle_events: List[BattleEvent]
```

## Key Mechanics

### Personality Assignment
- K < 0.85: Aggressive bias (mean_friendliness=0.3)
- K 0.85-1.5: Mixed (mean_friendliness=0.5)
- K > 1.5: Peaceful bias (mean_friendliness=0.7)
- Evolution: Defeats increase aggression, victories increase confidence

### War Resolution Per Timestep
- Battles occur at `battle_resolution_interval_myr` intervals
- Colony strength: age_factor × K_bonus × home_world_bonus
- Tech advantage affects win probability via sigmoid
- Territory transfers only after winning battles
- Wars end: victory, stalemate, or total destruction

### Light Cone Constraints
- Alliance cascades respect causality
- Communication events track arrival times
- Allies can only join war if they can causally learn about it
- `is_within_light_cone` flag on all events

### Reputation System
- Dynamic reputation [-1.0, 1.0] with each known civ
- Decay over time (configurable rate)
- Reputation modifier: (rep_a + rep_b) × -0.3 reduces war probability
- Ally deterrence: aggressing allies costs -0.2 reputation

### Strategic Resources
- Generation: `resource_generation_rate × dt_myr`
- War cost: `war_resource_cost_myr × dt_myr`
- War exhaustion accumulates during conflict
- Low resources increase war probability for aggressive civs

## Configuration Parameters

```python
# Personality
personality_assignment_model: str = "kardashev_dependent"
personality_evolution_enabled: bool = True
personality_evolution_rate: float = 0.1

# Encounters
first_contact_detection_range_pc: float = 100.0
encounter_scan_interval_myr: float = 100.0

# War
war_duration_max_myr: float = 10.0
tech_advantage_sensitivity: float = 0.3
fleet_velocity_multiplier: float = 0.01
battle_resolution_interval_myr: float = 0.5

# Reputation
reputation_enabled: bool = True
reputation_propagation_enabled: bool = True
reputation_decay_rate: float = 0.01

# Alliance
alliance_formation_enabled: bool = True
alliance_light_cone_constraint: bool = True

# Resources
resource_generation_rate: float = 10.0
war_resource_cost_myr: float = 5.0
```

## Simulation Loop Integration

**Added to `_step()` method:**
```python
# After _evolve_civilizations()
self._update_colony_strengths(dt_myr)
self._scan_for_encounters(dt_myr)
self._resolve_wars(dt_myr)
self._manage_strategic_resources(dt_myr)
self._decay_reputations(dt_myr)
```

**Added to `_handle_probe_arrival()`:**
- Check for overlap with other civs → trigger encounter
- Update spatial index with new colony

## Performance Optimizations

- **Spatial Index**: cKDTree for O(log N) overlap queries
- **Set-based Lookups**: O(1) colony membership checks
- **Vectorized Strength Updates**: NumPy operations
- **Chunked Battle Resolution**: Multiple battles per timestep

## Visualization Data

Snapshots now include:
- Complete civ states (personality, relations, war status)
- Event history (encounters, battles, communications)
- Colony positions per civ

## Implementation Timeline

**Phase 1**: Core infrastructure (personality, war dataclasses, spatial index)
**Phase 2**: Encounter detection, war mechanics, resolution
**Phase 3**: Main loop integration, snapshot tracking

## Future Enhancements

- Vassal mechanics (tribute, military obligations)
- Trade deals between allies
- Multi-civ peace treaties
- Fleet movement visualization
- Diplomatic AI (negotiations, conditional surrenders)
