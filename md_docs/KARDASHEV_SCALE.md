# Kardashev Scale Implementation

GalaticBot now tracks technological advancement using the Kardashev scale with realistic stochastic progression.

## What is the Kardashev Scale?

The Kardashev scale measures a civilization's technological advancement based on energy usage:

- **Type 0** (~0.7): Pre-planetary (modern Earth)
- **Type I** (1.0): Planetary-scale energy control
- **Type II** (2.0): Star-scale energy control (Dyson sphere)
- **Type III** (3.0): Galaxy-scale energy control

## Stochastic Technological Development

Each civilization has **individualized, randomized technological progression**:

### 1. **Random Starting Points**
- Initial Kardashev scale sampled from normal distribution
- Default: mean = 0.7, stddev = 0.1 (clamped to [0.5, 1.0])
- Some civilizations start more advanced, others less

### 2. **Variable Advancement Rates**
- Each civilization has its own advancement rate
- Sampled from: mean = 0.01/Myr, stddev = 0.005/Myr
- "Fast developers" advance 2-3x faster than "slow developers"

### 3. **Stochastic Events**

#### Technological Breakthroughs (2% per Myr)
- Sudden rapid advancement
- 3x normal advancement rate during breakthrough
- Examples: fusion power, AI, FTL communication (if allowed)

#### Technological Stagnation (5% per Myr)
- Periods of no advancement
- Examples: dark ages, resource depletion, political collapse
- Civilization doesn't advance during stagnation

### 4. **Maximum Cap**
- All civilizations cap at Type III (3.0)
- Prevents unrealistic advancement beyond galaxy-scale

## Configuration Parameters

```python
from great_silence import SimulationConfig

config = SimulationConfig()

# Starting technology (random distribution)
config.civilization.initial_kardashev_scale_mean = 0.7
config.civilization.initial_kardashev_scale_stddev = 0.1

# Advancement rate (random per civilization)
config.civilization.kardashev_advancement_rate_mean = 0.01  # per Myr
config.civilization.kardashev_advancement_rate_stddev = 0.005

# Stochastic events
config.civilization.kardashev_stagnation_probability_per_myr = 0.05  # 5%
config.civilization.kardashev_breakthrough_probability_per_myr = 0.02  # 2%
config.civilization.kardashev_breakthrough_multiplier = 3.0  # 3x faster

# Maximum advancement
config.civilization.kardashev_max_scale = 3.0
```

## Example Trajectories

With default parameters over 1 Gyr (1000 Myr):

**Fast Developer** (rate = 0.015/Myr, 2 breakthroughs):
- Start: 0.75
- After 500 Myr: ~1.2 (Type I achieved)
- After 1000 Myr: ~2.1 (Type II achieved)

**Average Developer** (rate = 0.01/Myr, 1 breakthrough, 2 stagnations):
- Start: 0.70
- After 500 Myr: ~0.95 (approaching Type I)
- After 1000 Myr: ~1.4 (Type I+)

**Slow Developer** (rate = 0.005/Myr, multiple stagnations):
- Start: 0.65
- After 500 Myr: ~0.75 (still Type 0)
- After 1000 Myr: ~0.88 (still pre-Type I)

**Short-Lived** (dies after 50 Myr):
- Start: 0.70
- Final: ~0.75 (no significant advancement)

## Visualization

The enhanced simulation shows Kardashev scale in multiple ways:

1. **Galaxy map**: Active civilizations color-coded by tech level
   - Purple/Blue = Type 0
   - Green/Yellow = Type I
   - Orange/Red = Type II-III

2. **Histogram**: Distribution of final tech levels across all civilizations

3. **Scatter plot**: Tech level vs lifetime (longer-lived = more advanced)

## Scientific Rationale

This implementation reflects realistic technological development:

1. **Variable starting points**: Not all civilizations reach spaceflight at same tech level
2. **Individual rates**: Different rates of innovation, resources, culture
3. **Breakthroughs**: Major paradigm shifts (e.g., human invention of agriculture, steam power, computers)
4. **Stagnation**: Historical examples (Bronze Age collapse, Medieval period)
5. **Lifetime correlation**: Longer survival → more advancement opportunities

## Impact on Simulation

Kardashev scale currently affects:
- **Visualization**: See where advanced vs primitive civilizations are
- **Statistics**: Track technological distribution across galaxy

Future enhancements could make tech level affect:
- Self-destruction probability (higher tech = lower risk?)
- Expansion speed (Type II+ expands faster)
- Detection probability (Type II+ more detectable)
- Hazard resistance (Type II+ survives supernovae?)

## Running Examples

```bash
# Run with default stochastic advancement
python examples/enhanced_simulation.py

# Outputs show:
# - Mean/max/min Kardashev scales
# - Distribution histogram
# - Lifetime vs tech level scatter plot
```

## Tips for Exploration

Try different scenarios:

```python
# Rapid advancement (post-singularity scenario)
config.civilization.kardashev_advancement_rate_mean = 0.05
config.civilization.kardashev_breakthrough_probability_per_myr = 0.1

# Stagnant galaxy (frequent dark ages)
config.civilization.kardashev_stagnation_probability_per_myr = 0.2
config.civilization.kardashev_advancement_rate_mean = 0.005

# High variance (some zoom ahead, others stagnate)
config.civilization.kardashev_advancement_rate_stddev = 0.02
config.civilization.initial_kardashev_scale_stddev = 0.2
```

---

**Now technological development is realistic and varied across civilizations!**
