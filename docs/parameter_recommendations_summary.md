# Quick Reference: Recommended Parameter Updates
## Based on 2024-2025 Exoplanet Data

### Immediate Changes (High Confidence)

```python
# In CivilizationParameters (parameters.py):

# UPDATE THIS:
avg_habitable_planets_per_system: float = 0.3  # Changed from 0.2
# Justification: 2024 NASA data shows ~50% of Sun-like stars have
# potentially habitable planets; average across all types ≈ 30%

# ADD THESE NEW PARAMETERS:
habitable_mass_min_msun: float = 0.5  # K-dwarfs and above
habitable_mass_max_msun: float = 1.4  # Early F-type upper limit
m_dwarf_habitability_penalty: float = 0.25  # Tidal locking concerns

use_age_dependent_emergence: bool = True
emergence_peak_age_gyr: float = 5.0  # Earth-like timeline
emergence_age_sigma_gyr: float = 3.0  # Broad distribution

use_metallicity_scaling: bool = True
metallicity_scaling_strength: float = 0.5  # Observationally constrained
```

### Keep These (Already Correct)

```python
fraction_stars_with_planets: float = 1.0  # ✓ Kepler confirmed ~100%
fraction_develop_life: float = 0.1  # ✓ Reasonable moderate estimate
fraction_develop_intelligence: float = 0.01  # ✓ Conservative
fraction_develop_technology: float = 0.1  # ✓ Plausible
```

### Expected Results

**With Current Code (flat emergence):**
- All civilizations seed at t=0
- Unrealistic temporal distribution
- Total emerged: depends on fixed seeding

**With Realistic Emergence:**
- Gradual emergence 1-10 Gyr
- Peak emergence at t=5-6 Gyr (when stars reach optimal age)
- Total civilizations over 10 Gyr: ~30,000-50,000 (100M stars)
- Active at any time: ~1,000-5,000 (depends on lifetime)
- Spatial clustering in inner galaxy (higher metallicity)

### Implementation Files

1. `/Users/jburgess/coding/projects/galaticbot/great_silence/civilization/emergence.py`
   - Add `age_scaling_factor()`, `metallicity_scaling_factor()`, `m_dwarf_penalty()`
   - Update `emergence_probability()` signature to include mass and metallicity

2. `/Users/jburgess/coding/projects/galaticbot/great_silence/config/parameters.py`
   - Add new fields to `CivilizationParameters` dataclass

3. `/Users/jburgess/coding/projects/galaticbot/great_silence/simulation/engine.py`
   - Update `initialize()` to compute stellar metallicities
   - Update `_check_for_emergence()` to pass mass and metallicity

### Full Details

See `/Users/jburgess/coding/projects/galaticbot/docs/exoplanet_research_2025.md` for:
- Complete literature review with citations
- Detailed parameter justifications
- Full Python implementation code
- Unit tests
- Expected simulation results analysis

### Quick Test

```python
from great_silence import GalaxySimulation, SimulationConfig

config = SimulationConfig()
config.galaxy.total_stars = 10_000
config.simulation.simulation_duration_gyr = 10.0
config.civilization.use_age_dependent_emergence = True
config.civilization.avg_habitable_planets_per_system = 0.3

sim = GalaxySimulation(config, seed=42)
sim.run(verbose=True)
print(f"Total civilizations: {len(sim.civilizations)}")
```
