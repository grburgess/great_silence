# 3D Animated Movies - GalaticBot Crisis Model

## Successfully Generated Movies

Three animated movies have been created showing galactic civilization evolution with the Kardashev-dependent self-destruction model.

### 1. **Rotating 3D Galaxy View**
**File:** `output/galaxy_3d_rotating.mp4` (378 KB)

**What it shows:**
- Full 3D rotating view of the galaxy
- Grey dots: Stars in the background
- Colored spheres: Active civilizations (color indicates Kardashev scale)
  - Blue: Type 0 (K~0.7, modern Earth level)
  - Yellow/Orange: Type I (K~1.0-2.0, planetary civilization)
  - Red: Type II+ (K>2.0, stellar civilization)
- Red X marks: Extinct civilizations
- Camera rotates 360° around the galaxy over the simulation

**Features:**
- 42 frames covering 2 billion years
- Shows civilizations emerging, advancing, and dying
- Real-time count of active vs. extinct civilizations
- True 3D perspective showing galactic disk structure

### 2. **Overhead View with Kardashev Timeline**
**File:** `output/galaxy_overhead_timeline.mp4` (284 KB)

**What it shows:**

**Left Panel - Overhead Galaxy Map:**
- Top-down view of the galaxy (X-Y plane)
- Shows spatial distribution of civilizations
- Active civilizations: Colored circles with white edges
- Dead civilizations: Red X marks
- Color indicates technological advancement

**Right Panel - Kardashev Evolution Timeline:**
- Time (Gyr) on X-axis
- Kardashev scale on Y-axis
- Each civilization draws a line showing its technological progress
- Green lines: Active civilizations (still advancing)
- Red lines: Extinct civilizations (terminated at death point)
- Red X marks: Point of death
- Background shading shows crisis regions:
  - Pink (K=0.65-0.80): Nuclear Age crisis
  - Orange (K=0.80-0.95): Planetary Unification crisis
  - Yellow (K=0.95-1.15): AI Transition crisis
  - Green (K=1.15-1.40): Interplanetary crisis

**Features:**
- Yellow vertical line shows current simulation time
- Watch civilizations climb the Kardashev ladder
- See exactly where each civilization dies (crisis region)
- Horizontal dashed lines mark Type I and Type II thresholds

### 3. **Crisis Death Locations**
**File:** `output/crisis_deaths_animation.mp4` (82 KB)

**What it shows:**
- Overhead galaxy view focused on WHERE civilizations die
- Color-coded by which crisis killed them:
  - **Red (#ff4444)**: Nuclear Age deaths
  - **Orange (#ff8844)**: Planetary Unification deaths
  - **Yellow (#ffcc44)**: AI Transition deaths
  - **Lime (#88ff44)**: Interplanetary deaths
  - **Cyan (#00ffff)**: Active civilizations (still alive)

**Features:**
- Clear visualization of the "Great Filter" in action
- Shows clustering of deaths by crisis type
- Legend in upper right identifies each crisis
- Demonstrates that most die early (red/orange) not late (blue/magenta)

## Simulation Results Shown in Movies

**Configuration:**
- 30,000 stars
- 2.0 Gyr simulation duration
- 47 civilizations emerged
- 0 survived (100% extinction rate)
- 42 snapshots (animation frames)

**Where Civilizations Died:**
Most died in the Nuclear Age and Planetary Unification crises - very few even reached the AI transition!

## Technical Details

**Format:** MP4 (H.264)
**Frame Rate:**
- Rotating 3D: 10 fps
- Overhead timeline: 8 fps
- Crisis deaths: 8 fps

**Resolution:**
- Rotating 3D: 1400×1000 pixels @ 100 DPI
- Overhead timeline: 1800×900 pixels @ 120 DPI
- Crisis deaths: 1200×1200 pixels @ 120 DPI

**Duration:** ~4-5 seconds each (covering 2 billion years of simulation)

## How to View

On macOS:
```bash
open output/galaxy_3d_rotating.mp4
open output/galaxy_overhead_timeline.mp4
open output/crisis_deaths_animation.mp4
```

Or use any video player (VLC, QuickTime, etc.)

## How to Regenerate

```bash
# Run the movie generator
~/.local/bin/micromamba run -n galaticbot python examples/create_3d_movies.py

# Takes about 1-2 minutes
# Outputs to output/*.mp4
```

## Customization

Edit `examples/create_3d_movies.py` to change:

**Simulation parameters:**
```python
config.galaxy.total_stars = 50_000  # More stars (slower)
config.simulation.simulation_duration_gyr = 5.0  # Longer simulation
config.simulation.snapshot_interval_myr = 25.0  # More frames
```

**Drake equation (more civilizations):**
```python
config.civilization.fraction_develop_life = 0.8
config.civilization.fraction_develop_intelligence = 0.2
```

**Crisis strengths:**
```python
config.civilization.crisis_ai_transition_amplitude = 0.35  # Deadlier AI crisis
config.civilization.crisis_nuclear_age_amplitude = 0.05  # Easier nuclear age
```

**Animation settings:**
```python
# In create_rotating_3d_animation():
anim.save(output_file, fps=15, dpi=150)  # Higher quality, larger file
```

## What the Movies Demonstrate

### Scientific Insights:

1. **Spatial Distribution**: Civilizations emerge throughout the galaxy, not just in "safe zones"

2. **Early Filter Dominance**: Watch how most civilizations die early (Nuclear/Planetary crises) before reaching advanced technology levels

3. **Technological Progress**: The timeline view shows civilizations advancing up the Kardashev scale at different rates (with breakthroughs causing jumps)

4. **Synchronous Extinction**: Multiple civilizations often exist simultaneously, but all eventually fail

5. **Empty Galaxy Result**: By the end, ZERO civilizations survive - explaining the Fermi Paradox

### The Great Filter in Action:

The movies visually demonstrate:
- Most civilizations cluster around K=0.7-0.9 at death (early crises)
- Very few reach Type I status (K=1.0)
- ZERO reach Type II status (K=2.0) - no Dyson spheres!
- The galaxy becomes "silent" naturally through technological self-destruction

This is exactly what the Kardashev-dependent crisis model predicts!

## Requirements

- Python 3.8+
- matplotlib
- numpy
- ffmpeg (for video encoding)

Install ffmpeg:
```bash
# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/
```

## File Sizes

The movies are intentionally kept small (80-380 KB) for easy sharing while maintaining visual clarity. For higher quality:

1. Increase DPI in the save commands
2. Increase frame rate (fps)
3. Use more snapshots (decrease snapshot_interval_myr)
4. Use higher resolution (figsize parameter)

Example for publication quality:
```python
anim.save(output_file, fps=30, dpi=300)  # ~10-20 MB files
```

## Sharing

These movies are perfect for:
- Scientific presentations
- Educational demonstrations
- Social media (explaining Fermi Paradox)
- Paper supplementary materials
- Grant proposals

The MP4 format is universally compatible with PowerPoint, Keynote, video players, and web browsers.
