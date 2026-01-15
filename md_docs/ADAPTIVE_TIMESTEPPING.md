# Adaptive Timestepping for GalaticBot

Inspired by computational physics methods: AMR (hydrodynamics), PIC (plasma), N-body (gravity), and Gillespie (chemical kinetics).

## Current Limitation

Fixed timestep simulation:
- **Inefficient** when nothing is happening (early phase, all extinct)
- **Inaccurate** when too much is happening (many rapid events)
- Wastes computation on empty periods
- Forces compromise between accuracy and speed

## Proposed Adaptive Strategies

### **Strategy 1: Adaptive Global Timestep** ⭐ (EASIEST)

**Concept:** Adjust dt based on system "activity level"

**Activity Metrics:**
```python
activity = (
    n_births_last_step +
    n_deaths_last_step +
    n_expansions_last_step +
    n_breakthroughs_last_step
)

# Adaptation rule
if activity > threshold_high:
    dt = dt_min  # Fine resolution needed
elif activity < threshold_low:
    dt = min(dt * 1.5, dt_max)  # Coarsen
else:
    dt = dt  # Keep current
```

**Advantages:**
- ✅ Simple to implement (20 lines of code)
- ✅ Maintains synchronous evolution
- ✅ Works with existing architecture
- ✅ 2-10x speedup expected

**Disadvantages:**
- ❌ Global dt - some waste on inactive regions
- ❌ Can oscillate if not careful

**Implementation Sketch:**
```python
class AdaptiveSimulation(GalaxySimulation):
    def __init__(self, config, seed=None):
        super().__init__(config, seed)
        self.dt_min = 0.1  # Myr
        self.dt_max = 100.0  # Myr
        self.dt_current = 1.0  # Start at 1 Myr
        self.activity_window = []  # Track recent activity

    def _step(self):
        # Count events this step
        n_births = len([c for c in self.civilizations
                       if c.birth_time_myr == self.current_time_myr])
        n_deaths = len([c for c in self.civilizations
                       if c.death_time_myr == self.current_time_myr])

        activity = n_births + n_deaths
        self.activity_window.append(activity)

        # Adapt timestep based on moving average
        avg_activity = np.mean(self.activity_window[-10:])

        if avg_activity > 10:  # High activity
            self.dt_current = max(self.dt_current * 0.8, self.dt_min)
        elif avg_activity < 1:  # Low activity
            self.dt_current = min(self.dt_current * 1.5, self.dt_max)

        # Use adaptive dt for next step
        self.config.simulation.time_step_myr = self.dt_current
```

---

### **Strategy 2: Event-Driven Simulation** ⭐⭐ (MODERATE)

**Concept:** Like Gillespie algorithm - advance to next event, not fixed intervals

**How It Works:**
1. For each civilization, calculate "time to next event":
   - Time to death (sample from exponential distribution)
   - Time to next expansion attempt
   - Time to tech breakthrough/stagnation
2. Advance clock to earliest event
3. Execute that event
4. Recalculate event times

**Advantages:**
- ✅ Exact - no discretization error
- ✅ Huge speedup when events are rare (100x+)
- ✅ Natural handling of multiple timescales

**Disadvantages:**
- ❌ Complex to implement (full refactor)
- ❌ Doesn't work well with continuous processes (stellar evolution)
- ❌ Harder to debug

**Implementation Sketch:**
```python
class EventDrivenSimulation:
    def __init__(self, config, seed=None):
        self.event_queue = []  # Min-heap of (time, event) tuples

    def schedule_death(self, civ):
        # Sample time to death from exponential
        tau = self.config.civilization.mean_civilization_lifetime_myr
        time_to_death = self.rng.exponential(tau)
        death_time = self.current_time_myr + time_to_death

        heapq.heappush(self.event_queue, (death_time, 'death', civ.civ_id))

    def run(self):
        while self.event_queue and self.event_queue[0][0] < self.sim_end_time:
            # Get next event
            event_time, event_type, civ_id = heapq.heappop(self.event_queue)

            # Advance time
            self.current_time_myr = event_time

            # Execute event
            if event_type == 'death':
                self._kill_civilization(civ_id)
            elif event_type == 'birth':
                self._birth_civilization()
            elif event_type == 'expansion':
                self._expand_civilization(civ_id)

            # Schedule next events
            self._schedule_next_events()
```

---

### **Strategy 3: Hierarchical/Subcycling** ⭐⭐⭐ (COMPLEX)

**Concept:** Like N-body gravity codes - different objects on different clocks

**How It Works:**
```
Level 0 (coarse): dt = 100 Myr  - Stellar evolution, galaxy structure
Level 1 (medium): dt = 10 Myr   - Old, stable civilizations
Level 2 (fine):   dt = 1 Myr    - Young, active civilizations
Level 3 (finest): dt = 0.1 Myr  - Civilizations in rapid expansion
```

**Advantages:**
- ✅ Optimal efficiency - each process at natural timescale
- ✅ Handles multi-scale physics naturally
- ✅ Used in production codes (GIZMO, FLASH)

**Disadvantages:**
- ❌ Very complex bookkeeping
- ❌ Synchronization required
- ❌ Interaction between levels tricky

**Implementation Sketch:**
```python
class HierarchicalSimulation:
    def __init__(self, config, seed=None):
        self.dt_levels = [100.0, 10.0, 1.0, 0.1]  # Myr
        self.civ_levels = {}  # civ_id -> level

    def assign_level(self, civ):
        # Young or active civs get fine level
        age = self.current_time_myr - civ.birth_time_myr
        if age < 10:
            return 3  # Finest
        elif age < 100:
            return 2
        else:
            return 1  # Coarse

    def step(self, level):
        dt = self.dt_levels[level]

        # Only evolve civilizations on this level
        for civ in self.civilizations:
            if self.civ_levels[civ.civ_id] == level:
                self._evolve_civilization(civ, dt)

        # Synchronization: when all levels align
        if self.is_sync_point():
            self._synchronize_all_levels()
```

---

### **Strategy 4: Hybrid Spatial-Temporal** ⭐⭐⭐ (VERY COMPLEX)

**Concept:** Combine AMR (spatial) + adaptive timestep (temporal)

**Spatial Binning:**
```
Divide galaxy into cells (e.g., 1 kpc³ cells)
Each cell has:
- Civilization density
- Activity level
- Update frequency
```

**How It Works:**
```python
# High-activity cells (many civs, high interaction)
cell.update_frequency = 'every timestep'
cell.dt = 0.1 Myr

# Low-activity cells (few civs, little interaction)
cell.update_frequency = 'every 10 timesteps'
cell.dt = 10 Myr

# Empty cells (no civs)
cell.update_frequency = 'only check for emergence every 100 timesteps'
cell.dt = 100 Myr
```

**Advantages:**
- ✅ Maximum efficiency
- ✅ Handles both spatial and temporal heterogeneity
- ✅ Scalable to huge galaxies

**Disadvantages:**
- ❌ Extremely complex
- ❌ Interactions across cell boundaries tricky
- ❌ Overkill for current problem size

---

## **Recommended Implementation Plan**

### **Phase 1: Quick Win** (1-2 hours)
Implement **Strategy 1: Adaptive Global Timestep**
- Easy to add to existing code
- 2-5x speedup expected
- Minimal risk

### **Phase 2: Major Improvement** (1-2 days)
Implement **Strategy 2: Event-Driven Simulation**
- Requires refactor but worth it
- 10-100x speedup for sparse scenarios
- More accurate

### **Phase 3: Research-Grade** (1-2 weeks)
Implement **Strategy 3: Hierarchical Timestepping**
- For very large simulations
- Multiple timescales handled naturally
- Publication-quality code

---

## **Practical Considerations**

### **When to Use Each Strategy:**

| Scenario | Best Strategy | Why |
|----------|---------------|-----|
| Testing/development | Strategy 1 | Fast to code, good enough |
| Production runs | Strategy 2 | Best speed/complexity ratio |
| Large galaxies (10M+ stars) | Strategy 3 | Essential for scaling |
| Dense regions (globular clusters) | Strategy 4 | Spatial heterogeneity |

### **Expected Speedups:**

```
Fixed timestep (current):        100% runtime
Strategy 1 (adaptive global):     30-50% runtime (2-3x faster)
Strategy 2 (event-driven):        5-10% runtime (10-20x faster)
Strategy 3 (hierarchical):        5-20% runtime (5-20x faster)
Strategy 4 (hybrid):              2-5% runtime (20-50x faster)
```

### **Complexity vs Benefit:**

```
                 Complexity
                    ↑
Strategy 4 (hybrid) ●
                    │
Strategy 3 (hier.)  ●
                    │
Strategy 2 (event)    ●
                    │
Strategy 1 (adapt)        ●
                    │
Fixed (current)           ●────────────────────→
                                        Speedup
```

---

## **Your Original Question: Backward or Forward?**

Your intuition was **partially backward** but **mostly correct**:

**Backward part:**
- "Less active civilizations need lower resolution"
- Actually: Less activity → can use COARSER resolution (fewer computations needed)

**Correct part:**
- Drawing analogy to AMR/PIC methods is spot-on
- Spatial/temporal adaptation is exactly right approach
- Recognizing fixed timestep is inefficient is key insight

**The refinement:**
- Adapt based on **event rate**, not civilization count
- High event rate → fine dt
- Low event rate → coarse dt
- No events → huge jumps (skip ahead)

---

## **Next Steps**

1. **Profile current code** to find bottlenecks
2. **Implement Strategy 1** as proof-of-concept
3. **Benchmark** speedup vs accuracy
4. **Consider Strategy 2** if speedup insufficient

Want me to implement Strategy 1 right now? It's ~50 lines of code.
