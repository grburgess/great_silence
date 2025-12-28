# Parameter Scaling Guide

## The Problem: Why Are All Civilizations Dying?

If you see **all civilizations going extinct** immediately, your parameters aren't scaled correctly for your timestep size.

## Understanding Timesteps

GalaticBot uses **discrete timesteps** where probabilities are applied each step. The key insight:

**Per-timestep probability = per-Myr probability × timestep size (Myr)**

### Example: The Death Trap

```python
# WRONG - Everyone dies immediately!
config.simulation.time_step_myr = 10.0  # 10 Myr timesteps
config.civilization.mean_civilization_lifetime_myr = 1.0  # Mean lifetime 1 Myr
config.civilization.self_destruction_probability_per_myr = 0.1  # 10% per Myr
```

**What actually happens:**
- Self-destruction per step: 0.1 × 10 = **100%** (guaranteed death!)
- Age-based death per step: 1 - exp(-10/1) = **99.995%** (guaranteed death!)
- Result: Every civilization dies in first timestep

### Fixed Version

```python
# CORRECT - Civilizations survive and thrive!
config.simulation.time_step_myr = 1.0  # 1 Myr timesteps
config.civilization.mean_civilization_lifetime_myr = 100.0  # Mean lifetime 100 Myr
config.civilization.self_destruction_probability_per_myr = 0.01  # 1% per Myr
```

**What happens:**
- Self-destruction per step: 0.01 × 1 = **1%** (survivable)
- Age-based death per step: 1 - exp(-1/100) = **0.995%** (survivable)
- Combined survival: ~98% per timestep
- Expected lifetime: ~100 Myr (as intended!)

## Scaling Rules

### Rule 1: Timestep Should Be Much Smaller Than Mean Lifetime

**Good:**
```python
time_step_myr = 1.0
mean_civilization_lifetime_myr = 100.0  # 100x larger ✓
```

**Bad:**
```python
time_step_myr = 10.0
mean_civilization_lifetime_myr = 1.0  # 10x smaller ✗
```

**Guideline:** `mean_lifetime / timestep` should be **at least 10**, preferably **50-100**.

### Rule 2: Per-Step Probabilities Should Be Small

All probabilities per timestep should be < 10% for stability:

```python
p_per_step = p_per_myr × time_step_myr

# Good examples (p_per_step < 0.1):
time_step_myr = 1.0
self_destruction_probability_per_myr = 0.01  # 0.01 × 1 = 1% ✓

time_step_myr = 0.1
self_destruction_probability_per_myr = 0.5  # 0.5 × 0.1 = 5% ✓

# Bad examples (p_per_step > 0.1):
time_step_myr = 10.0
self_destruction_probability_per_myr = 0.1  # 0.1 × 10 = 100% ✗

time_step_myr = 1.0
self_destruction_probability_per_myr = 0.5  # 0.5 × 1 = 50% ✗
```

### Rule 3: Simulation Duration Should Be Long Enough

```python
# See multiple generations of civilizations
simulation_duration_gyr = 10.0  # 10 Gyr = 10,000 Myr
mean_civilization_lifetime_myr = 100.0  # ~100 generations

# Too short - barely any civilizations
simulation_duration_gyr = 0.1  # 100 Myr
mean_civilization_lifetime_myr = 100.0  # Only ~1 generation
```

## Recommended Parameter Sets

### Fast Test Run (1-2 minutes)

```python
config = SimulationConfig()

# Small galaxy, short sim
config.galaxy.total_stars = 10_000
config.simulation.simulation_duration_gyr = 1.0  # 1 Gyr
config.simulation.time_step_myr = 1.0  # 1 Myr

# Moderate civilizations
config.civilization.mean_civilization_lifetime_myr = 50.0
config.civilization.self_destruction_probability_per_myr = 0.02

# Moderate Drake parameters
config.civilization.fraction_develop_life = 0.1
config.civilization.fraction_develop_intelligence = 0.01
```

**Expected:**
- ~50-100 civilizations total
- ~10-20 active at end
- Runtime: 1-2 minutes

### Standard Run (5-10 minutes)

```python
config = SimulationConfig()

# Medium galaxy
config.galaxy.total_stars = 100_000
config.simulation.simulation_duration_gyr = 10.0  # 10 Gyr
config.simulation.time_step_myr = 1.0  # 1 Myr

# Longer-lived civilizations
config.civilization.mean_civilization_lifetime_myr = 100.0
config.civilization.self_destruction_probability_per_myr = 0.01

# Fermi-consistent Drake
config.civilization.fraction_develop_life = 0.1
config.civilization.fraction_develop_intelligence = 0.01
```

**Expected:**
- ~200-500 civilizations total
- ~50-100 active at end
- Runtime: 5-10 minutes

### Long Research Run (30-60 minutes)

```python
config = SimulationConfig()

# Large galaxy
config.galaxy.total_stars = 1_000_000
config.simulation.simulation_duration_gyr = 10.0
config.simulation.time_step_myr = 1.0

# Very long-lived (optimistic scenario)
config.civilization.mean_civilization_lifetime_myr = 1000.0
config.civilization.self_destruction_probability_per_myr = 0.001

# Conservative Drake
config.civilization.fraction_develop_life = 0.01
config.civilization.fraction_develop_intelligence = 0.001
```

**Expected:**
- ~100-500 civilizations total
- ~50-200 active at end
- Runtime: 30-60 minutes

## Checking Your Parameters

Before running, calculate per-step probabilities:

```python
import numpy as np

dt = config.simulation.time_step_myr
tau = config.civilization.mean_civilization_lifetime_myr
p_self = config.civilization.self_destruction_probability_per_myr

# Per-step probabilities
p_self_per_step = p_self * dt
p_age_per_step = 1.0 - np.exp(-dt / tau)

# Total death probability per step
p_death_total = 1 - (1 - p_self_per_step) * (1 - p_age_per_step)

print(f"Self-destruction per step: {p_self_per_step*100:.2f}%")
print(f"Age-based death per step: {p_age_per_step*100:.2f}%")
print(f"Total death per step: {p_death_total*100:.2f}%")
print(f"Expected lifetime: {-tau * np.log(1 - p_death_total):.1f} Myr")

# Warnings
if p_self_per_step > 0.1:
    print("⚠️  WARNING: Self-destruction probability too high!")
if p_age_per_step > 0.1:
    print("⚠️  WARNING: Timestep too large for mean lifetime!")
if dt / tau > 0.1:
    print("⚠️  WARNING: Timestep should be < 10% of mean lifetime!")
```

## Common Scenarios

### "I want civilizations to survive longer"

```python
# Increase mean lifetime
config.civilization.mean_civilization_lifetime_myr = 500.0  # 500 Myr

# Decrease self-destruction
config.civilization.self_destruction_probability_per_myr = 0.005  # 0.5% per Myr

# Or both!
```

### "I want more civilizations to emerge"

```python
# Increase Drake parameters
config.civilization.fraction_develop_life = 0.2
config.civilization.fraction_develop_intelligence = 0.05

# Or increase galaxy size
config.galaxy.total_stars = 1_000_000
```

### "I want faster simulations"

```python
# Larger timesteps (but check scaling!)
config.simulation.time_step_myr = 5.0  # Must increase lifetimes too!
config.civilization.mean_civilization_lifetime_myr = 500.0  # 100x timestep

# Or smaller galaxy
config.galaxy.total_stars = 10_000

# Or shorter duration
config.simulation.simulation_duration_gyr = 1.0
```

### "I want Great Filter scenarios"

```python
# Early Filter (life is rare)
config.civilization.fraction_develop_life = 0.001

# Late Filter (tech civilizations self-destruct)
config.civilization.self_destruction_probability_per_myr = 0.1  # High!
config.simulation.time_step_myr = 0.5  # Smaller timestep needed

# Rare Earth (habitable planets rare)
config.civilization.avg_habitable_planets_per_system = 0.01
```

## Debugging Checklist

If all civilizations are dying:

1. ✓ Check `time_step_myr` is small (≤ 1.0 usually)
2. ✓ Check `mean_civilization_lifetime_myr` >> `time_step_myr` (100x ratio)
3. ✓ Check `self_destruction_probability_per_myr × time_step_myr < 0.1`
4. ✓ Calculate actual per-step probabilities (see code above)
5. ✓ Use the fixed example scripts: `longer_lived_civilizations.py`

---

**Use the examples in `/examples/` as starting points - they have properly scaled parameters!**
