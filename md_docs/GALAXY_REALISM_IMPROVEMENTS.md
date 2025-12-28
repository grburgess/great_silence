# Galaxy Realism Improvements

Documenting missing physical features and implementation plan.

## Current Implementation (Good!)

### ✅ Galactic Rotation
- **Flat rotation curve** at v_circ = 220 km/s (matches Milky Way)
- **Differential rotation**: ω = v/r decreases with radius
- **Velocity dispersion**: σ increases with |z| (thicker disk = hotter)
- **Realistic kinematics**: Circular + random component

**Implementation:**
```python
# Circular velocity (flat curve)
v_circ = 220 km/s (constant)

# Velocity components
v_x = -v_circ * y / r  # Tangential
v_y = v_circ * x / r   # Tangential
v_z = 0                # Planar motion

# Add dispersion (increases with height)
σ_r = 30 * (1 + |z|/h_z) km/s
σ_θ = 20 * (1 + |z|/h_z) km/s
σ_z = 20 * (1 + |z|/h_z) km/s
```

### ✅ Stellar Motion
- Stars evolve positions every timestep: `x(t+dt) = x(t) + v*dt`
- Uses Numba-accelerated kernel (10-20x faster on M1 Max)
- Accounts for proper motion over Gyr timescales

**Why this matters:**
- Civilizations track moving targets
- Expansion must account for stellar drift
- Hazard ranges change as stars move

## Missing Features (To Add)

### ❌ Bulge Component

**What's missing:**
- Central spheroidal component
- Higher stellar density in center (r < 3 kpc)
- Different kinematics (pressure-supported, not rotationally-supported)

**Real Milky Way:**
```
Bulge:
- Mass: ~2 × 10^10 M☉ (~20% of total)
- Scale radius: ~1 kpc
- Velocity dispersion: ~100 km/s
- Older, more metal-rich stars

Disk:
- Mass: ~6 × 10^10 M☉ (~60% of total)
- Scale length: ~3 kpc
- Rotation: ~220 km/s
- Mix of ages
```

**Implementation Plan:**

```python
def _generate_bulge_and_disk(self, n_stars):
    """Generate positions from bulge + disk components."""
    # Partition stars between bulge and disk
    f_bulge = 0.2  # 20% in bulge
    n_bulge = int(n_stars * f_bulge)
    n_disk = n_stars - n_bulge

    # Sample bulge (Hernquist or Plummer profile)
    r_bulge = self._sample_hernquist(n_bulge, a=1.0)  # kpc
    bulge_pos = self._spherical_to_cartesian(r_bulge)

    # Sample disk (exponential)
    disk_pos = self._generate_exponential_disk(n_disk)

    return np.vstack([bulge_pos, disk_pos])
```

**Bulge velocity distribution:**
```python
# Pressure-supported (not rotating)
v_rot_bulge = 0.3 * v_circ  # Slow rotation
σ_bulge = 100 km/s          # High dispersion

# Isotropic velocities
v_x = rng.normal(0, σ_bulge)
v_y = rng.normal(0, σ_bulge) + v_rot_bulge * (x/r)
v_z = rng.normal(0, σ_bulge)
```

### ❌ Radial Age Gradient (Inside-Out Formation)

**What's missing:**
- Central stars should be **older** (formed ~10-13 Gyr ago)
- Outer disk stars should be **younger** (formed ~0-5 Gyr ago)
- "Inside-out" formation: bulge → inner disk → outer disk

**Real Milky Way observations:**
```
r < 3 kpc (bulge):    Age ~12 Gyr, [Fe/H] ~ +0.3
3 < r < 8 kpc:        Age ~8 Gyr,  [Fe/H] ~ 0.0
r > 8 kpc (outer):    Age ~4 Gyr,  [Fe/H] ~ -0.2
```

**Implementation Plan:**

```python
class StarFormationHistory:
    def generate_stellar_ages_with_gradient(
        self, n_stars, radii, max_age_gyr=13.0
    ):
        """
        Generate ages with radial gradient.

        Inner stars older, outer stars younger (inside-out formation).
        """
        ages = np.zeros(n_stars)

        for i, r in enumerate(radii):
            # Mean age decreases with radius
            # Bulge (r < 3): mean age ~11 Gyr
            # Solar circle (r ~ 8): mean age ~6 Gyr
            # Outer disk (r > 12): mean age ~3 Gyr

            mean_age = 12.0 * np.exp(-r / 8.0) + 2.0  # Gyr
            sigma_age = 2.0  # Gyr spread

            # Sample from distribution
            age = rng.normal(mean_age, sigma_age)
            age = np.clip(age, 0.0, max_age_gyr)

            ages[i] = age

        return ages
```

**Why this matters for civilizations:**
1. **Bulge is hazardous**: Old, dense, many supernovae
2. **Inner disk habitable later**: Needed to cool down from early activity
3. **Outer disk** is "frontier": Young, fewer hazards, but fewer stars

### ❌ Metallicity Gradient

**What's missing:**
- [Fe/H] decreases with radius
- Affects planet formation (need metals for rocky planets)
- Should gate habitable planet fraction

**Implementation:**
```python
def generate_metallicities(self, radii):
    """Radial metallicity gradient."""
    # [Fe/H] vs radius (dex)
    # Inner: +0.3
    # Solar: 0.0
    # Outer: -0.5

    metallicity = 0.3 - 0.1 * (radii / 8.0)  # Gradient ~-0.1 dex/kpc
    return metallicity

# Use in Drake equation:
def habitable_fraction(self, metallicity):
    """Metal-rich stars more likely to have rocky planets."""
    # Observed correlation
    # [Fe/H] < -0.5: f_planets ~ 0.01 (metal-poor)
    # [Fe/H] ~ 0.0:  f_planets ~ 0.10 (solar)
    # [Fe/H] > +0.3: f_planets ~ 0.30 (metal-rich)

    f_base = 0.10
    return f_base * 10**(metallicity)  # Factor of 10 per dex
```

## Implementation Priority

### Phase 1: Bulge Component (Moderate Difficulty)
**Effort:** 2-3 hours
**Impact:** High - realistic structure

1. Add Hernquist/Plummer bulge profile
2. Partition stars between bulge and disk
3. Different velocity distribution for bulge
4. Update visualizations to show bulge

### Phase 2: Age Gradient (Easy)
**Effort:** 1 hour
**Impact:** High - affects habitability

1. Modify `generate_stellar_ages()` to take radii
2. Implement exponential age-radius relation
3. Update documentation

### Phase 3: Metallicity Gradient (Easy)
**Effort:** 1 hour
**Impact:** Moderate - realistic planet formation

1. Add metallicity calculation
2. Gate Drake equation on metallicity
3. Visualize metallicity distribution

### Phase 4: Thick Disk (Low Priority)
**Effort:** 2 hours
**Impact:** Low - for completeness

1. Add thick disk component (old, metal-poor, scale height ~1 kpc)
2. Different velocity dispersion

## Scientific Impact

### Without These Features:
- ❌ Bulge stars treated same as disk (unrealistic)
- ❌ No inside-out formation (conflicts with observations)
- ❌ Central region habitable from start (unrealistic)
- ❌ No metallicity effects on planets

### With These Features:
- ✅ Realistic Milky Way structure (bulge + disk)
- ✅ Age gradient matches observations
- ✅ Central region hostile early (dense, supernovae, GRBs)
- ✅ Outer disk is frontier (sparse, low metallicity)
- ✅ Solar neighborhood (~8 kpc) is "Goldilocks zone"

## Technical Considerations

### Performance Impact:
- **Bulge**: Minimal (just different sampling)
- **Age gradient**: Negligible (vectorized operation)
- **Metallicity**: Negligible (simple calculation)

### Backward Compatibility:
- Add as optional features with config flags:
  ```python
  config.galaxy.include_bulge = True
  config.galaxy.use_age_gradient = True
  config.galaxy.use_metallicity_gradient = True
  ```

### Visualization:
- Show bulge in different color
- Age gradient heatmap
- Metallicity gradient overlay

## References

**Milky Way Structure:**
- Bland-Hawthorn & Gerhard (2016) - "The Galaxy" (review)
- Bovy (2017) - Galactic structure from Gaia

**Inside-Out Formation:**
- Matteucci & Francois (1989) - Chemical evolution models
- Bird et al. (2013) - Age gradients from APOGEE

**Bulge:**
- McWilliam & Rich (1994) - Bulge metallicities
- Howard et al. (2009) - Bulge kinematics

## Summary

**Currently implemented (Good!):**
- ✅ Realistic rotation (flat curve, differential)
- ✅ Stellar motion over time
- ✅ Velocity dispersion structure

**Missing (Should add):**
- ❌ Bulge component (20% of stars)
- ❌ Radial age gradient (inside-out)
- ❌ Metallicity gradient (affects planets)

**Recommendation:** Implement Phase 1 (bulge) and Phase 2 (age gradient) for maximum scientific realism with minimal effort.

Want me to implement these now?
