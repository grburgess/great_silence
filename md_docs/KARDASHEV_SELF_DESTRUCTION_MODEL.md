# Kardashev-Dependent Self-Destruction Model

## Overview

The Kardashev-Dependent Self-Destruction Model implements a scientifically motivated framework for modeling technological civilization extinction that varies with developmental stage. Unlike simple flat-rate extinction models, this approach captures the empirical insight that civilizations face **distinct existential crises** at specific technological transitions.

This model is critical for Fermi Paradox simulations because it provides a plausible mechanism for the "Great Filter" - the explanation for why we don't observe galactic-scale civilizations despite billions of years of cosmic history.

## Physical Motivation

### The Kardashev Scale

The Kardashev scale measures a civilization's technological advancement by energy consumption:

- **Type 0.7** (Modern Earth, 2024): ~10^13 W (fossil fuels, nuclear, renewables)
- **Type I** (K=1.0): ~10^16 W (planetary energy mastery, weather control, full biosphere utilization)
- **Type II** (K=2.0): ~10^26 W (stellar energy mastery via Dyson spheres/swarms)
- **Type III** (K=3.0): ~10^36 W (galactic energy mastery, multi-star coordination)

### Why Technology Level Affects Self-Destruction Risk

1. **Capability Outpaces Wisdom**: Each technological leap provides civilization-ending capabilities before developing corresponding wisdom/governance. Nuclear weapons (1945) arrived before global coordination mechanisms.

2. **Transition Instabilities**: Moving between Kardashev levels requires fundamental restructuring of society, energy infrastructure, and governance - periods of heightened fragility.

3. **Irreversible Thresholds**: Some technologies (AGI, relativistic weapons, stellar manipulation) may have no "trial and error" phase - first mistake is terminal.

4. **Observational Constraint**: The Fermi Paradox demands that SOMETHING prevents >99.9% of civilizations from becoming galaxy-spanning. Technology-dependent extinction provides a natural filter.

## Mathematical Framework

### Hazard Function

The self-destruction hazard rate (probability per unit time) is modeled as:

```
λ(K) = λ_base(K) + Σᵢ Aᵢ × exp(-((K - Kᵢ)² / (2σᵢ²)))
```

Where:
- **λ(K)**: Total hazard rate at Kardashev scale K (units: per Myr)
- **λ_base(K) = λ₀(1 + αK)**: Baseline risk increasing with complexity
  - λ₀ = 0.01 per Myr (baseline at K=0)
  - α = 0.05 (5% increase per Kardashev level)
- **Aᵢ**: Amplitude of crisis peak i (maximum additional hazard)
- **Kᵢ**: Kardashev scale center of crisis i
- **σᵢ**: Width of crisis window (standard deviation)

### Crisis Peaks (Default Parameters)

| Crisis Name | K_center | Width (σ) | Amplitude (A) | Physical Basis |
|-------------|----------|-----------|---------------|----------------|
| **Nuclear Age** | 0.72 | 0.05 | 0.15 | Nuclear weapons, climate collapse, pollution, biosphere degradation. Modern Earth sits HERE. |
| **Planetary Unification** | 0.85 | 0.08 | 0.12 | Failure to achieve global coordination, resource wars, nationalism vs. planetary needs. |
| **AI Transition** | 1.05 | 0.10 | 0.20 | AGI alignment failure, loss of control, value lock-in, AI-driven extinction. **STRONGEST CRISIS BY DEFAULT**. |
| **Interplanetary Expansion** | 1.25 | 0.15 | 0.10 | Space habitat failures, interplanetary resource conflicts, O'Neill cylinder catastrophes. |
| **Stellar Engineering** | 1.80 | 0.20 | 0.08 | Dyson sphere structural failures, star-lifting accidents, fusion containment breaches. |
| **Relativistic Weapons** | 2.50 | 0.25 | 0.06 | Self-annihilation with near-c projectiles, vacuum decay weapons, controlled singularities. |

### Per-Timestep Probability

Given a time step Δt (in Myr), the probability of self-destruction is:

```
P(destruction | Δt, K) = 1 - exp(-λ(K) × Δt)
```

This exact formula ensures proper probability scaling for any time step size (unlike naive linear approximation p = λΔt, which fails for large Δt).

### Survival Probability

The probability of surviving from K₁ to K₂ (assuming constant advancement rate v_K):

```
S(K₁ → K₂) = exp(-∫[K₁ to K₂] (λ(K) / v_K) dK)
```

For default parameters with v_K = 0.01/Myr, survival from K=0.7 → K=3.0 is approximately **1 in 6 million** - explaining Fermi silence.

## Implementation Details

### Configuration Parameters

All crisis parameters are configurable in `CivilizationParameters`:

```python
# Model selection
self_destruction_model_type: str = "kardashev_dependent"  # or "flat"

# Baseline risk
baseline_self_destruction_rate: float = 0.01  # λ₀ at K=0
baseline_risk_scaling: float = 0.05  # α (linear scaling)

# Crisis amplitudes (can be tuned for scenario exploration)
crisis_nuclear_age_amplitude: float = 0.15
crisis_planetary_unification_amplitude: float = 0.12
crisis_ai_transition_amplitude: float = 0.20  # Strongest
crisis_interplanetary_amplitude: float = 0.10
crisis_stellar_engineering_amplitude: float = 0.08
crisis_relativistic_weapons_amplitude: float = 0.06

# Enable/disable individual crises
enable_nuclear_crisis: bool = True
enable_ai_crisis: bool = True
# ... etc for all crises
```

### Code Usage

**Basic usage in simulation engine**:

```python
from great_silence.civilization.extinction import ExtinctionModel, CrisisPeak

# Create model with crisis peaks
extinction_model = ExtinctionModel(
    self_destruction_rate=0.1,  # Fallback for flat model
    mean_lifetime_myr=1.0,
    model_type="kardashev_dependent",
    baseline_rate=0.01,
    baseline_scaling=0.05,
    crisis_peaks=[...]  # List of CrisisPeak objects
)

# Check for self-destruction each timestep
if extinction_model.check_self_destruction(
    dt_myr=1.0,
    rng=np.random.default_rng(seed),
    kardashev_scale=civilization.kardashev_scale
):
    civilization.destroy()
```

**Scenario exploration**:

```python
# Amplify AI crisis to test "Late Filter" hypothesis
extinction_model.set_crisis_amplitude("ai_transition", 0.40)

# Disable nuclear crisis (for post-nuclear civilizations only)
extinction_model.enable_crisis("nuclear_age", enabled=False)

# Get crisis information
crisis_info = extinction_model.get_crisis_info()

# Visualize hazard landscape
extinction_model.plot_hazard_function(k_range=(0.5, 3.0))
```

## Fermi Paradox Implications

### Survival Statistics (Default Parameters)

**Hazard rates at key milestones**:

| Kardashev | Hazard λ [/Myr] | Expected Lifetime [Myr] | Interpretation |
|-----------|-----------------|-------------------------|----------------|
| 0.70 (Pre-nuclear) | 0.170 | 5.9 | Relatively safe, but approaching crisis |
| 0.72 (Modern Earth) | 0.194 | 5.2 | **WE ARE HERE** - in nuclear age crisis |
| 1.05 (AI transition) | 0.257 | 3.9 | Most dangerous period |
| 1.50 (Advanced Type I) | 0.062 | 16.2 | Relative safety between crises |
| 2.00 (Type II) | 0.068 | 14.8 | Mature stellar civilization |
| 3.00 (Type III) | 0.020 | 51.0 | Very stable (survivors are resilient) |

**Cumulative survival probabilities**:

Assuming advancement rate of 0.01/Myr (Kardashev scale +1 every 100 Myr):

- **Nuclear Age** (K=0.65→0.80, 15 Myr): 8.7% survive
- **AI Transition** (K=0.95→1.15, 20 Myr): 0.9% survive ← **GREAT FILTER**
- **Full journey** (K=0.7→3.0, 230 Myr): **0.000016% survive** (1 in 6 million)

### Great Filter Interpretations

1. **AI-Dominated Filter** (Default):
   - AI crisis amplitude >> other crises
   - Most civilizations fail at K~1.0-1.2
   - Predicts: Few Type II+ civilizations, galaxy mostly empty
   - Consistent with: Fermi Paradox, lack of Dyson spheres, SETI silence

2. **Distributed Filter**:
   - Multiple crises with similar amplitudes
   - Compound survival: S_total = S_nuclear × S_AI × S_stellar × ...
   - Each crisis eliminates 50-90%, exponential attrition
   - Predicts: Extremely rare galaxy-spanning civilizations

3. **Early Filter** (Nuclear/Planetary):
   - Nuclear + planetary unification crises amplified
   - Most fail before Type I
   - Predicts: No colonization waves, isolated civilizations

### Testable Predictions

**If Late Filter (AI crisis) dominates**:
- Should find NO evidence of Dyson spheres in JWST/future surveys
- SETI unlikely to succeed (few transmitting civilizations)
- Ruins of failed Type I civilizations possible (if detectable)
- Expect ~10-100 contemporary civilizations in Milky Way, all <Type I

**If Early Filter dominates**:
- Potential Type II/III civilizations could exist
- SETI might detect mature civilizations that survived
- Dyson spheres should be observable if early filter weak

**Current observations favor Late Filter or Distributed Filter** (no Dyson spheres, no SETI detections after 60+ years).

## Usage in GalaticBot Simulations

### Running with Kardashev-Dependent Model

```python
from great_silence import SimulationConfig, GalaxySimulation

# Default configuration uses Kardashev-dependent model
config = SimulationConfig()
config.civilization.self_destruction_model_type = "kardashev_dependent"

# Run simulation
sim = GalaxySimulation(config, seed=42)
sim.initialize()
sim.run()

# Analyze results
active_civs = sim.count_active_civilizations()
max_kardashev = max([civ.kardashev_scale for civ in sim.civilizations])
```

### Scenario Presets

```python
# Late Filter scenario (AI crisis amplified)
config = SimulationConfig.with_preset('late_filter')
# Sets: AI amplitude=0.35, nuclear=0.25, civilizations fail at Type I transition

# Optimistic scenario (low crisis risks)
config = SimulationConfig.with_preset('optimistic')
# Note: NOT Fermi-consistent, for exploration only
```

### Sensitivity Analysis

```python
# Test different AI crisis strengths
ai_amplitudes = [0.05, 0.10, 0.20, 0.40]
results = []

for amp in ai_amplitudes:
    config = SimulationConfig()
    config.civilization.crisis_ai_transition_amplitude = amp

    sim = GalaxySimulation(config, seed=42)
    sim.run()

    results.append({
        'ai_amplitude': amp,
        'total_civs': len(sim.civilizations),
        'max_kardashev': max([c.kardashev_scale for c in sim.civilizations]),
        'reached_type_2': sum(c.kardashev_scale >= 2.0 for c in sim.civilizations)
    })
```

### Comparison to Flat Model

```python
# Kardashev-dependent model
config_kd = SimulationConfig()
config_kd.civilization.self_destruction_model_type = "kardashev_dependent"

# Flat model (constant risk)
config_flat = SimulationConfig()
config_flat.civilization.self_destruction_model_type = "flat"
config_flat.civilization.self_destruction_probability_per_myr = 0.1

# Run both and compare
# Expectation: Flat model underestimates risk at crisis transitions,
# overestimates between crises → different survival curves
```

## Visualization and Analysis

### Hazard Landscape Plot

```bash
python examples/kardashev_crisis_demo.py
```

Generates visualization showing:
- Hazard rate λ(K) vs Kardashev scale
- Crisis peaks marked and labeled
- Expected lifetime vs technology level
- Kardashev type boundaries (I, II, III)
- Modern Earth position

### Key Metrics to Track

1. **Crisis passage rates**: What fraction survive each crisis?
2. **Maximum Kardashev achieved**: Distribution across Monte Carlo runs
3. **Death causes**: Self-destruction vs age vs astrophysical hazards
4. **Timing of extinction**: When do most civilizations fail?
5. **Survival correlation**: Do fast-advancing civs survive better (less time in crisis) or worse (less adaptation time)?

## Scientific Justification

### Why These Specific Crisis Centers?

**K=0.72 (Nuclear Age)**:
- Empirical: Modern Earth (2024) is ~K=0.72
- First existential technology: nuclear weapons (1945)
- Observed near-misses: Cuban Missile Crisis, Able Archer 83
- Climate change approaching irreversible thresholds
- Width σ=0.05: Narrow window (~5 Myr) to achieve global governance or perish

**K=1.05 (AI Transition)**:
- Positioned just after Type I (planetary energy mastery enables advanced AI)
- Unique risk: Potential for rapid, irreversible capability gain ("intelligence explosion")
- Alignment problem: No guarantee AI goals align with survival
- No empirical data (hasn't happened yet), but theoretical arguments strong
- Highest amplitude (0.20) reflects extreme uncertainty and potential severity

**K=1.80 (Stellar Engineering)**:
- Dyson sphere/swarm construction risks: structural failure → loss of stellar energy
- Star lifting accidents: manipulating stellar fusion
- Lower amplitude (0.08): Civilizations at this stage have survived multiple filters
- Wider width (σ=0.20): Gradual transition over tens of Myr

**K=2.50 (Relativistic Weapons)**:
- Near Type III civilizations can accelerate macroscopic objects to >0.9c
- Kinetic energy ~10^32 J (stellar-scale destruction)
- Risk of arms races, first-strike incentives at galactic scales
- Lowest amplitude (0.06): Survivors are presumably wise, but weapons capability is absolute

### Parameter Uncertainties

All crisis amplitudes are **highly uncertain**:

- **Nuclear Age**: Some empirical calibration (1 major crisis survived so far)
- **AI Transition**: Pure theory, could be 10x higher OR much lower
- **Later crises**: Complete speculation, no civilizations observed at these stages

**Recommended approach**: Treat as FREE PARAMETERS for scenario exploration, not ground truth.

## Limitations and Future Enhancements

### Current Limitations

1. **Static Kardashev mapping**: Real civilizations might plateau, regress, or leap discontinuously
2. **No civilization "learning"**: Model doesn't account for risk mitigation improving over time
3. **Gaussian crisis shape**: Assumes symmetric risk curves, reality may be skewed
4. **No crisis interactions**: E.g., AI might SOLVE or EXACERBATE climate/nuclear risks
5. **Homogeneous crises**: All civilizations face same crises (no variation in developmental paths)

### Potential Extensions

1. **Adaptive crisis amplitudes**:
   - Civilizations that survive one crisis become more cautious
   - Implement: `A_effective = A_base × (1 - 0.5 × num_crises_survived)`

2. **Breakthrough technologies**:
   - Some advances REDUCE risk (e.g., fusion solving energy scarcity)
   - Add negative Gaussian peaks

3. **Civilization diversity**:
   - Sample crisis centers from distributions (not all civs face AI at exactly K=1.05)
   - Reflects different developmental pathways

4. **Crisis width variation**:
   - Fast-advancing civilizations experience narrower crises (less time in danger zone)
   - Slow advancement → wider effective crisis

5. **Observational calibration**:
   - If JWST detects Dyson spheres → reduce late crisis amplitudes
   - If AGI developed safely on Earth → reduce AI amplitude
   - Update model with new data

## References and Further Reading

**Kardashev Scale**:
- Kardashev, N. (1964). "Transmission of Information by Extraterrestrial Civilizations"
- Sagan, C. (1973). Fractional Kardashev scale refinement

**Great Filter Theory**:
- Hanson, R. (1998). "The Great Filter - Are We Almost Past It?"
- Bostrom, N. (2002). "Existential Risks: Analyzing Human Extinction Scenarios"

**Fermi Paradox**:
- Webb, S. (2015). "If the Universe Is Teeming with Aliens... WHERE IS EVERYBODY?"
- Ćirković, M. (2018). "The Great Silence: Science and Philosophy of Fermi's Paradox"

**AI Existential Risk**:
- Bostrom, N. (2014). "Superintelligence: Paths, Dangers, Strategies"
- Ord, T. (2020). "The Precipice: Existential Risk and the Future of Humanity"

**Observational Constraints**:
- Wright, J. et al. (2014). "The Search for Infrared Emission from Dyson Spheres"
- Griffith, R. et al. (2015). "The Ĝ Infrared Search for Extraterrestrial Civilizations"

---

**Model Status**: Production-ready as of 2024-12-27

**Maintainer**: GalaticBot Development Team

**License**: MIT (see LICENSE file)
