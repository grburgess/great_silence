# Civilization Encounter Behavior Implementation Plan

## Overview
Implement AI civilization encounter behaviors including first contact, war mechanics, reputation system, and personality types. This adds inter-civilization dynamics beyond the existing internal crisis/self-destruction models.

## Architecture Overview

### New Data Structures

**CivilizationState extensions** (`simulation/engine.py:60-91`)
- Add fields to existing `CivilizationState` dataclass:
  - `personality_type: str` - "expansionist", "defensive", "xenophile", "isolationist"
  - `friendliness: float` - 0.0=aggressive to 1.0=peaceful
  - `reputation: Dict[int, float]` - civ_id -> reputation score (-1.0 to +1.0)
  - `known_civilizations: Set[int]` - civs this civ has encountered
  - `allies: Set[int]` - formal alliance partners
  - `enemies: Set[int]` - formal war enemies
  - `war_state: Optional[WarState]` - active war details

**WarState dataclass** (new in `simulation/engine.py`)
```python
@dataclass
class WarState:
    """State of an ongoing war between two civilizations."""
    enemy_civ_id: int
    start_time_myr: float
    last_encounter_time_myr: float
    territory_disputed: Set[int]  # Star indices in contention
    casualties_suffered: float  # Cumulative damage
```

**EncounterEvent dataclass** (new in `simulation/engine.py`)
```python
@dataclass
class EncounterEvent:
    """Record of a civilization encounter event."""
    time_myr: float
    civ_1_id: int
    civ_2_id: int
    encounter_type: str  # "probe_arrival", "shared_colony"
    outcome: str  # "peace", "war_started", "alliance_formed"
    resolution_details: str
```

## Implementation Phases

### Phase 1: Core Infrastructure

#### 1.1 Create Personality Module
**File**: `civilization/personality.py` (new)

Key functions:
- `sample_personality(kardashev_scale: float, rng: np.random.Generator) -> Dict[str, Any]`
  - Samples friendliness from K-dependent truncated normal distribution
  - Returns dict with `personality_type`, `friendliness`, `aggression_factor`
- `get_friendliness_distribution_mean(kardashev_scale: float) -> float`
  - K < 0.85: mean=0.3 (aggressive bias)
  - K 0.85-1.5: mean=0.5 (mixed)
  - K > 1.5: mean=0.7 (peaceful bias)
- `derive_personality_type(friendliness: float, rng: np.random.Generator) -> str`
  - friendliness < 0.3: "expansionist"
  - 0.3-0.5: "defensive"
  - 0.5-0.7: "isolationist"
  - > 0.7: "xenophile"

#### 1.2 Update CivilizationState
**File**: `simulation/engine.py`

Add new fields to `CivilizationState` (line 60-91). Initialize all new fields to appropriate defaults in the dataclass definition.

#### 1.3 Assign Personality at Emergence
**File**: `simulation/engine.py`, method `_check_emergence()` around line 735

After creating new civilization, sample personality:
```python
from ..civilization.personality import sample_personality

personality = sample_personality(kardashev_scale, self.rng)
new_civ.personality_type = personality['personality_type']
new_civ.friendliness = personality['friendliness']
# Initialize empty relationship structures
new_civ.reputation = {}
new_civ.known_civilizations = set()
new_civ.allies = set()
new_civ.enemies = set()
```

#### 1.4 Add Configuration Parameters
**File**: `config/parameters.py`, class `CivilizationParameters` (line 82)

Add after line 176:
```python
# Personality system
personality_assignment_model: str = "kardashev_dependent"
# "kardashev_dependent", "random", "fixed"
personality_fixed_friendliness: float = 0.5  # If model="fixed"

# Encounter mechanics
first_contact_detection_range_pc: float = 100.0
encounter_scan_interval_myr: float = 100.0

# War mechanics
war_outcome_model: str = "winner_takes_territory"
war_duration_max_myr: float = 10.0
war_stalemate_probability: float = 0.1
tech_advantage_sensitivity: float = 0.3

# Reputation system
reputation_enabled: bool = True
reputation_weight_in_war_decision: float = 0.3
reputation_propagation_enabled: bool = True
reputation_decay_rate: float = 0.01
```

### Phase 2: Encounter Detection

#### 2.1 Probe Arrival Detection
**File**: `simulation/engine.py`, method `_process_probe_events()` around line 987

After processing probe arrival, check for overlap:
```python
# Check if star already colonized by another civ
for other_civ in self.civilizations:
    if other_civ.civ_id == civ.civ_id or not other_civ.is_active:
        continue

    if target_star_idx in other_civ.colonized_stars:
        # First contact!
        self._handle_encounter(civ, other_civ, target_star_idx, "probe_arrival")
```

#### 2.2 Periodic Territory Scan
**File**: `simulation/engine.py`, new method `_scan_for_encounters()`

```python
def _scan_for_encounters(self) -> None:
    """Scan all civilizations for territory overlaps, trigger encounters."""
    active_civs = [c for c in self.civilizations if c.is_active]

    for i, civ_a in enumerate(active_civs):
        for civ_b in active_civs[i+1:]:
            # Skip if already encountered
            if civ_b.civ_id in civ_a.known_civilizations:
                continue

            # Check for overlapping colonies
            overlap = civ_a.colonized_stars & civ_b.colonized_stars
            if overlap:
                # Trigger encounter at first overlapping star
                star_idx = next(iter(overlap))
                self._handle_encounter(civ_a, civ_b, star_idx, "shared_colony")
```

Call this in main loop: `simulation/engine.py`, method `run()` around line 435, after `_evolve_civilizations()`.

#### 2.3 Spatial Index Optimization (PRIORITY 3)
**File**: `utils/spatial.py`, new module

Use existing `SpatialIndex` or create new civilization index for O(log N) overlap detection instead of O(N²) scan.

### Phase 3: Encounter Decision Logic

#### 3.1 Core Encounter Handler
**File**: `simulation/engine.py`, new method `_handle_encounter()`

```python
def _handle_encounter(
    self,
    civ_a: CivilizationState,
    civ_b: CivilizationState,
    location_idx: int,
    encounter_type: str
) -> None:
    """Handle first contact between two civilizations."""
    # Record encounter for both
    civ_a.known_civilizations.add(civ_b.civ_id)
    civ_b.known_civilizations.add(civ_a.civ_id)

    # Initialize reputation
    civ_a.reputation[civ_b.civ_id] = 0.0
    civ_b.reputation[civ_a.civ_id] = 0.0

    # Calculate war probability
    p_war = self._calculate_encounter_war_probability(civ_a, civ_b)

    # Roll for outcome
    if self.rng.uniform(0, 1) < p_war:
        self._start_war(civ_a, civ_b, [location_idx])
        outcome = "war_started"
    else:
        # Peaceful contact - check for alliance
        if (civ_a.personality_type == "xenophile" and
            civ_b.personality_type == "xenophile"):
            self._form_alliance(civ_a, civ_b)
            outcome = "alliance_formed"
        else:
            outcome = "peace"

    # Record encounter event
    self.encounter_events.append(EncounterEvent(
        time_myr=self.current_time_myr,
        civ_1_id=civ_a.civ_id,
        civ_2_id=civ_b.civ_id,
        encounter_type=encounter_type,
        outcome=outcome,
        resolution_details=f"K: {civ_a.kardashev_scale:.2f} vs {civ_b.kardashev_scale:.2f}"
    ))
```

#### 3.2 War Probability Calculation
**File**: `simulation/engine.py`, new method `_calculate_encounter_war_probability()`

```python
def _calculate_encounter_war_probability(
    self,
    civ_a: CivilizationState,
    civ_b: CivilizationState
) -> float:
    """Calculate probability that encounter leads to war."""
    # Base probability from friendliness
    base_war_prob = 1.0 - (civ_a.friendliness * civ_b.friendliness)

    # Tech gap factor (larger gap = higher war prob)
    tech_gap = abs(civ_a.kardashev_scale - civ_b.kardashev_scale)
    tech_factor = tech_gap * self.config.civilization.tech_advantage_sensitivity

    # Reputation modifier
    rep_modifier = 0.0
    if self.config.civilization.reputation_enabled:
        civ_a_rep = civ_a.reputation.get(civ_b.civ_id, 0.0)
        civ_b_rep = civ_b.reputation.get(civ_a.civ_id, 0.0)
        rep_modifier = (civ_a_rep + civ_b_rep) * -0.3  # Negative = less war

        # Check reputation of allies (deterrence)
        for ally_id in civ_a.allies:
            if ally_id == civ_b.civ_id:
                # Allied to enemy! Very likely to defend ally
                rep_modifier -= 0.2

    # Combine factors
    p_war = base_war_prob + tech_factor + rep_modifier
    return np.clip(p_war, 0.0, 1.0)
```

### Phase 4: War Mechanics

#### 4.1 Start War
**File**: `simulation/engine.py`, new method `_start_war()`

```python
def _start_war(
    self,
    aggressor: CivilizationState,
    defender: CivilizationState,
    disputed_stars: List[int]
) -> None:
    """Initialize war between two civilizations."""
    # Create war states
    aggressor.war_state = WarState(
        enemy_civ_id=defender.civ_id,
        start_time_myr=self.current_time_myr,
        last_encounter_time_myr=self.current_time_myr,
        territory_disputed=set(disputed_stars),
        casualties_suffered=0.0
    )

    defender.war_state = WarState(
        enemy_civ_id=aggressor.civ_id,
        start_time_myr=self.current_time_myr,
        last_encounter_time_myr=self.current_time_myr,
        territory_disputed=set(disputed_stars),
        casualties_suffered=0.0
    )

    # Mark as enemies
    aggressor.enemies.add(defender.civ_id)
    defender.enemies.add(aggressor.civ_id)

    # Update reputation (aggressor gets penalty)
    aggressor.reputation[defender.civ_id] -= 0.4
```

#### 4.2 War Resolution Per Step
**File**: `simulation/engine.py`, new method `_resolve_wars()`

```python
def _resolve_wars(self) -> None:
    """Resolve ongoing wars for this time step."""
    active_civs = [c for c in self.civilizations if c.is_active]

    for civ in active_civs:
        if civ.war_state is None:
            continue

        # Find enemy
        enemy = next((c for c in active_civs if c.civ_id == civ.war_state.enemy_civ_id), None)
        if enemy is None or not enemy.is_active:
            # Enemy destroyed, war over
            self._end_war(civ, victor=civ)
            continue

        # Check for stalemate (war dragged on too long)
        war_duration = self.current_time_myr - civ.war_state.start_time_myr
        if war_duration > self.config.civilization.war_duration_max_myr:
            if self.rng.uniform(0, 1) < self.config.civilization.war_stalemate_probability:
                self._end_war(civ, enemy, stalemate=True)
                continue

        # Calculate battle outcome
        winner = self._resolve_battle(civ, enemy)

        # Transfer territory (Winner Takes Territory model)
        if winner == civ:
            loser = enemy
        else:
            loser = civ

        # Transfer disputed colonies
        for star_idx in civ.war_state.territory_disputed:
            if star_idx in loser.colonized_stars:
                loser.colonized_stars.remove(star_idx)
                winner.colonized_stars.add(star_idx)

        # Update disputed territory list (add newly overlapping stars)
        new_overlap = civ.colonized_stars & enemy.colonized_stars
        civ.war_state.territory_disputed = new_overlap
        enemy.war_state.territory_disputed = new_overlap

        # Check if war should end (one civ lost all territory)
        if len(loser.colonized_stars) == 0:
            self._end_war(winner, loser, total_destruction=True)
```

Call this in main loop: `simulation/engine.py`, method `run()` around line 435, after `_scan_for_encounters()`.

#### 4.3 Battle Resolution
**File**: `simulation/engine.py`, new method `_resolve_battle()`

```python
def _resolve_battle(
    self,
    civ_a: CivilizationState,
    civ_b: CivilizationState
) -> CivilizationState:
    """Resolve single battle, return winner."""
    # Calculate tech advantage
    tech_gap = civ_a.kardashev_scale - civ_b.kardashev_scale

    # Win probability based on tech advantage (sigmoid)
    from scipy.special import expit
    win_prob_a = 0.5 + 0.4 * expit(tech_gap / self.config.civilization.tech_advantage_sensitivity)

    # Roll for winner
    if self.rng.uniform(0, 1) < win_prob_a:
        winner, loser = civ_a, civ_b
    else:
        winner, loser = civ_b, civ_a

    # Update reputations
    winner.reputation[loser.civ_id] += 0.1
    loser.reputation[winner.civ_id] -= 0.2

    return winner
```

#### 4.4 End War
**File**: `simulation/engine.py`, new method `_end_war()`

```python
def _end_war(
    self,
    civ_a: CivilizationState,
    civ_b: Optional[CivilizationState] = None,
    victor: Optional[CivilizationState] = None,
    stalemate: bool = False,
    total_destruction: bool = False
) -> None:
    """End war between civilizations."""
    # Clear war states
    if civ_a.war_state:
        civ_a.war_state = None

    if civ_b and civ_b.war_state:
        civ_b.war_state = None

    if total_destruction and civ_b and victor:
        # Loser destroyed
        civ_b.is_active = False
        civ_b.death_time_myr = self.current_time_myr
        civ_b.death_cause = 'war'
```

### Phase 5: Reputation System

#### 5.1 Reputation Updates
Already embedded in war methods above. Add additional update points:
- Alliance formation: +0.3 reputation
- Alliance breaking: -0.5 reputation

#### 5.2 Reputation Decay
**File**: `simulation/engine.py`, new method `_decay_reputations()`

```python
def _decay_reputations(self, dt_myr: float) -> None:
    """Decay reputation values towards neutral (0.0) over time."""
    decay = self.config.civilization.reputation_decay_rate * (dt_myr / 1000.0)

    for civ in self.civilizations:
        for other_civ_id in list(civ.reputation.keys()):
            if civ.reputation[other_civ_id] > 0:
                civ.reputation[other_civ_id] = max(0.0, civ.reputation[other_civ_id] - decay)
            else:
                civ.reputation[other_civ_id] = min(0.0, civ.reputation[other_civ_id] + decay)
```

Call this in main loop: `simulation/engine.py`, method `run()` around line 435, each time step.

#### 5.3 Reputation Propagation
**File**: `simulation/engine.py`, new method `_propagate_reputations()`

```python
def _propagate_reputations(self) -> None:
    """Share reputation information between allied/known civilizations."""
    if not self.config.civilization.reputation_propagation_enabled:
        return

    for civ in self.civilizations:
        if not civ.is_active:
            continue

        for known_civ_id in civ.known_civilizations:
            # Find known civ
            known_civ = next((c for c in self.civilizations if c.civ_id == known_civ_id), None)
            if known_civ is None:
                continue

            # Share their reputation with third parties
            for third_civ_id in civ.known_civilizations:
                if third_civ_id == known_civ_id:
                    continue

                # Propagate reputation with weight 0.3
                if third_civ_id in known_civ.reputation:
                    # Weight by trust in known civ
                    trust = civ.reputation.get(known_civ_id, 0.0)
                    propagated_rep = known_civ.reputation[third_civ_id] * 0.3 * (trust + 1.0) / 2.0

                    if third_civ_id not in civ.reputation:
                        civ.reputation[third_civ_id] = propagated_rep
                    else:
                        # Blend with existing (60% existing, 40% new)
                        civ.reputation[third_civ_id] = (
                            0.6 * civ.reputation[third_civ_id] + 0.4 * propagated_rep
                        )
```

Call this periodically: `simulation/engine.py`, method `run()` every 50 Myr.

### Phase 6: Alliance System

#### 6.1 Form Alliance
**File**: `simulation/engine.py`, new method `_form_alliance()`

```python
def _form_alliance(
    self,
    civ_a: CivilizationState,
    civ_b: CivilizationState
) -> None:
    """Form alliance between two civilizations."""
    civ_a.allies.add(civ_b.civ_id)
    civ_b.allies.add(civ_a.civ_id)

    # Boost reputation
    civ_a.reputation[civ_b.civ_id] = 0.8
    civ_b.reputation[civ_a.civ_id] = 0.8

    # Remove from enemies if applicable
    civ_a.enemies.discard(civ_b.civ_id)
    civ_b.enemies.discard(civ_a.civ_id)
```

#### 6.2 Alliance Effects on War
Modify `_calculate_encounter_war_probability()`:
- If civs are allies: p_war = 0.0 (never war with allies)
- If civ A attacks civ B, civ B's allies automatically consider civ A enemy

Modify `_start_war()`:
- When war starts, cascade to allies:
  ```python
  for ally_id in defender.allies:
      ally = next(c for c in self.civilizations if c.civ_id == ally_id)
      ally.enemies.add(aggressor.civ_id)
      aggressor.reputation[ally_id] -= 0.2
  ```

### Phase 7: Integration with Expansion

#### 7.1 Filter Expansion Targets
**File**: `simulation/engine.py`, modify `_find_expansion_targets()`

When selecting probe targets:
- Skip stars owned by allies (peaceful coexistence)
- Prioritize stars owned by enemies (targets of conquest)
- Apply modifier to colonization probability based on owner's relationship

#### 7.2 Home World Capture
In war resolution, if home world (parent_star_idx) is captured:
- Trigger home_world_destruction flags
- Apply fragility period (existing mechanics)
- Consider special "refugee" behavior for surviving colonies

### Phase 8: Testing and Validation

#### 8.1 Unit Tests
**File**: `tests/test_encounters.py` (new)

Test cases:
- Personality assignment at different K levels
- War probability calculation with various friendliness/tech combos
- War territory transfer (Winner Takes Territory)
- Reputation updates and decay
- Alliance formation and effects
- Reputation propagation

#### 8.2 Integration Tests
**File**: `tests/test_simulation_encounters.py` (new)

Test scenarios:
- Two civs with similar K, random personalities → expect some war/peace mix
- High-K xenophiles + high-K xenophiles → alliance likely
- Low-K expansionist vs high-K xenophile → war likely
- Multi-civ chain reaction (A attacks B, B's allies C join)
- Reputation system dampens wars over time

#### 8.3 Visualization
**File**: `visualization/encounters.py` (new)

Add to visualizer:
- Plot war timeline (which civs at war when)
- Reputation heatmap matrix
- Alliance network graph
- Encounter outcomes pie chart

### Phase 9: Performance Optimization

#### 9.1 Spatial Index for Overlap Detection
Use existing `SpatialIndex` from `utils/spatial.py` to find overlapping civilizations in O(log N) instead of O(N²).

#### 9.2 Lazy Reputation Propagation
Limit propagation to 2nd-order connections (friends of friends) to prevent O(N³) blowup.

#### 9.3 War Resolution Parallelization
Since wars between independent civ pairs can be resolved in parallel, use existing parallel infrastructure.

### Phase 10: Documentation

#### 10.1 Update AGENTS.md
Add new section "Civilization Encounter System" with:
- Overview of encounter mechanics
- Personality assignment algorithm
- War resolution rules
- Reputation system description

#### 10.2 Update Code Comments
Add detailed docstrings to all new methods explaining:
- Physical/scientific basis of decisions
- Probability distributions used
- Why specific thresholds were chosen

## Implementation Order

1. **Week 1**: Phase 1 (Core Infrastructure)
2. **Week 2**: Phase 2 (Encounter Detection) + Phase 3 (Encounter Decision Logic)
3. **Week 3**: Phase 4 (War Mechanics) + Phase 5 (Reputation System)
4. **Week 4**: Phase 6 (Alliance System) + Phase 7 (Expansion Integration)
5. **Week 5**: Phase 8 (Testing) + Phase 9 (Performance)
6. **Week 6**: Phase 10 (Documentation) + final integration

## Key Design Decisions Documented

1. **Personality Model**: K-dependent distribution reflects realistic evolution - pre-interstellar civs are competitive due to resource scarcity, post-interstellar civs are peaceful due to energy abundance.

2. **War Outcome - Winner Takes Territory**: Matches game design request, avoids total annihilation (except when all colonies lost). Creates dynamic territory control.

3. **Reputation System**: Enables historical memory and emergent behavior (aggressors get reputations that make others more likely to preemptively attack them).

4. **Tech Gap Effect**: Large tech gaps increase war probability because:
   - Stronger civ fears weaker's potential future threat
   - Weaker civ fears imminent conquest
   - Asymmetric warfare is more tempting to aggressor

5. **Alliance System**: Enables multi-civ conflicts, makes late-game more interesting (empires vs empires, not just 1v1).

6. **Detection Range**: 100 pc balances realism (sensor limits) with gameplay (frequent encounters).

7. **Scan Interval**: 100 Myr balances performance (not checking every step) with detection timeliness.

## Unresolved Issues for Consideration

1. Should probes be automatically destroyed in enemy territory?
2. What happens to home worlds specifically when captured?
3. Technology theft from conquered civilizations?
4. Multi-civ alliances (NATO-style) vs only bilateral?
5. Reputation effects on emergence probability (war-torn galaxy = more aggressive civs)?
6. Should wars have "victory conditions" beyond territory (e.g., "kill X colonies")?
7. Peace treaties with reparations/trade deals?
8. Resource depletion from prolonged wars?

## Configuration Presets to Add

Add to `SimulationConfig.with_preset()`:

**'warlike_galaxy'**: All civs aggressive, high tech gap sensitivity
**'peaceful_coexistence'**: All civs xenophile, low war probability
**'great_filter_war'**: Wars are primary extinction mechanism (set crisis amplitudes low, war amplitudes high)
**'unified_galaxy'**: Alliance formation probability boosted, encourages multi-civ cooperation
