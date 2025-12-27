"""
3D ANIMATED VISUALIZATION OF GALACTIC CIVILIZATION EVOLUTION

Creates multiple movie files showing:
1. Rotating 3D galaxy view with civilizations emerging and dying
2. Overhead view showing spatial distribution
3. Timeline showing Kardashev scale evolution and crisis deaths

Requires: matplotlib with animation support, ffmpeg
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
from mpl_toolkits.mplot3d import Axes3D
from great_silence import GalaxySimulation, SimulationConfig
import os


def create_demo_config_for_animation():
    """Create optimized config for animation (smaller, faster)."""
    config = SimulationConfig()

    # Smaller galaxy for faster animation
    config.galaxy.total_stars = 30_000
    config.galaxy.include_bulge = True
    config.galaxy.bulge_fraction = 0.2
    config.galaxy.scale_length_kpc = 3.5
    config.galaxy.disk_radius_kpc = 15.0

    # More optimistic Drake to get visible civilizations
    config.civilization.fraction_develop_life = 0.5
    config.civilization.fraction_develop_intelligence = 0.1
    config.civilization.fraction_develop_technology = 0.5
    # Combined: 2.5% per habitable star

    # Crisis-based extinction
    config.civilization.self_destruction_model_type = "kardashev_dependent"
    config.civilization.baseline_self_destruction_rate = 0.01
    config.civilization.crisis_nuclear_age_amplitude = 0.15
    config.civilization.crisis_planetary_unification_amplitude = 0.12
    config.civilization.crisis_ai_transition_amplitude = 0.20
    config.civilization.crisis_interplanetary_amplitude = 0.10

    # Disable old age for clearer crisis visualization
    config.civilization.mean_civilization_lifetime_myr = 1000.0

    # Kardashev advancement
    config.civilization.initial_kardashev_scale_mean = 0.7
    config.civilization.kardashev_advancement_rate_mean = 0.02  # Faster for visualization

    # Shorter simulation with more snapshots
    config.simulation.simulation_duration_gyr = 2.0  # 2 Gyr
    config.simulation.time_step_myr = 10.0  # 10 Myr
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 50.0  # Every 50 Myr (40 frames)

    return config


def create_rotating_3d_animation(sim, output_file='output/galaxy_3d_rotating.mp4'):
    """
    Create rotating 3D view of galaxy with civilizations.

    Shows:
    - Star positions (grey points)
    - Active civilizations (colored by Kardashev scale)
    - Dead civilizations (red X marks)
    """
    print("\nCreating rotating 3D galaxy animation...")
    print(f"  Snapshots: {len(sim.snapshots)}")

    # Setup figure
    fig = plt.figure(figsize=(14, 10))
    fig.patch.set_facecolor('black')
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor('black')

    # Get stellar positions (sample for performance)
    sample_indices = np.random.choice(len(sim.galaxy.positions),
                                     size=min(5000, len(sim.galaxy.positions)),
                                     replace=False)
    stars_pos = sim.galaxy.positions[sample_indices]

    # Plot stars (static background)
    ax.scatter(stars_pos[:, 0], stars_pos[:, 1], stars_pos[:, 2],
              c='grey', s=0.1, alpha=0.3, label='Stars')

    # Set limits
    ax.set_xlim(-15, 15)
    ax.set_ylim(-15, 15)
    ax.set_zlim(-5, 5)
    ax.set_xlabel('X [kpc]', color='white')
    ax.set_ylabel('Y [kpc]', color='white')
    ax.set_zlabel('Z [kpc]', color='white')
    ax.tick_params(colors='white')

    # Initialize civilization scatter plots
    active_scatter = None
    dead_scatter = None
    title = ax.text2D(0.5, 0.95, '', transform=ax.transAxes,
                     ha='center', fontsize=14, color='cyan', fontweight='bold')
    time_text = ax.text2D(0.5, 0.90, '', transform=ax.transAxes,
                         ha='center', fontsize=12, color='white')

    def init():
        """Initialize animation."""
        return []

    def animate(frame_idx):
        """Update animation for each frame."""
        nonlocal active_scatter, dead_scatter

        # Get snapshot
        snapshot = sim.snapshots[frame_idx]
        time_gyr = snapshot.time_myr / 1000.0

        # Get civilization positions and states
        active_civs = []
        dead_civs = []

        for civ in snapshot.civilization_states:
            pos = sim.galaxy.positions[civ.parent_star_idx]
            kardashev = civ.kardashev_scale

            if civ.is_active:
                active_civs.append((pos, kardashev))
            else:
                dead_civs.append(pos)

        # Clear old scatters
        if active_scatter is not None:
            active_scatter.remove()
        if dead_scatter is not None:
            dead_scatter.remove()

        # Plot active civilizations (colored by Kardashev scale)
        if active_civs:
            active_pos = np.array([c[0] for c in active_civs])
            active_k = np.array([c[1] for c in active_civs])

            # Color map: blue (K=0.7) -> yellow (K=1.0) -> red (K=2.0+)
            colors = plt.cm.plasma(active_k / 2.5)

            active_scatter = ax.scatter(active_pos[:, 0], active_pos[:, 1], active_pos[:, 2],
                                       c=colors, s=100, marker='o',
                                       edgecolors='white', linewidths=1,
                                       alpha=0.9, label='Active')

        # Plot dead civilizations
        if dead_civs:
            dead_pos = np.array(dead_civs)
            dead_scatter = ax.scatter(dead_pos[:, 0], dead_pos[:, 1], dead_pos[:, 2],
                                     c='red', s=50, marker='x',
                                     alpha=0.6, label='Extinct')

        # Rotate view
        angle = frame_idx * 3  # 3 degrees per frame
        ax.view_init(elev=20, azim=angle)

        # Update text
        title.set_text('GALACTIC CIVILIZATION EVOLUTION (3D VIEW)')
        time_text.set_text(f'Time: {time_gyr:.2f} Gyr | Active: {len(active_civs)} | Extinct: {len(dead_civs)}')

        return [active_scatter, dead_scatter, title, time_text] if active_scatter or dead_scatter else []

    # Create animation
    anim = animation.FuncAnimation(fig, animate, init_func=init,
                                  frames=len(sim.snapshots),
                                  interval=200, blit=False)

    # Save to file
    print(f"  Saving to {output_file}...")
    anim.save(output_file, writer='ffmpeg', fps=10, dpi=100,
             extra_args=['-vcodec', 'libx264', '-pix_fmt', 'yuv420p'])

    plt.close(fig)
    print(f"✓ Saved: {output_file}")


def create_overhead_timeline_animation(sim, output_file='output/galaxy_overhead_timeline.mp4'):
    """
    Create overhead view with timeline showing Kardashev evolution.

    Two panels:
    - Left: Overhead galaxy view (X-Y plane)
    - Right: Kardashev scale vs time for all civilizations
    """
    print("\nCreating overhead view with timeline animation...")

    fig = plt.figure(figsize=(18, 9))
    fig.patch.set_facecolor('#0a0a0a')
    gs = GridSpec(1, 2, figure=fig, wspace=0.15)

    # Left panel: Overhead view
    ax_galaxy = fig.add_subplot(gs[0, 0])
    ax_galaxy.set_facecolor('#0a0a0a')
    ax_galaxy.set_aspect('equal')

    # Right panel: Kardashev timeline
    ax_timeline = fig.add_subplot(gs[0, 1])
    ax_timeline.set_facecolor('#0a0a0a')

    # Sample stars for background
    sample_indices = np.random.choice(len(sim.galaxy.positions),
                                     size=min(3000, len(sim.galaxy.positions)),
                                     replace=False)
    stars_pos = sim.galaxy.positions[sample_indices]

    # Plot galaxy background (static)
    ax_galaxy.scatter(stars_pos[:, 0], stars_pos[:, 1],
                     c='grey', s=0.5, alpha=0.2)
    ax_galaxy.set_xlim(-15, 15)
    ax_galaxy.set_ylim(-15, 15)
    ax_galaxy.set_xlabel('X [kpc]', fontsize=12, color='white', fontweight='bold')
    ax_galaxy.set_ylabel('Y [kpc]', fontsize=12, color='white', fontweight='bold')
    ax_galaxy.tick_params(colors='white')
    for spine in ax_galaxy.spines.values():
        spine.set_color('white')
        spine.set_linewidth(2)

    # Timeline setup
    ax_timeline.set_xlim(0, sim.config.simulation.simulation_duration_gyr)
    ax_timeline.set_ylim(0.5, 3.0)
    ax_timeline.set_xlabel('Time [Gyr]', fontsize=12, color='white', fontweight='bold')
    ax_timeline.set_ylabel('Kardashev Scale', fontsize=12, color='white', fontweight='bold')
    ax_timeline.tick_params(colors='white')
    for spine in ax_timeline.spines.values():
        spine.set_color('white')
        spine.set_linewidth(2)

    # Mark crisis regions on timeline
    crisis_regions = [
        (0.65, 0.80, 'Nuclear\nAge', '#ff4444'),
        (0.80, 0.95, 'Planetary\nUnif.', '#ff8844'),
        (0.95, 1.15, 'AI\nTransition', '#ffcc44'),
        (1.15, 1.40, 'Inter-\nplanetary', '#88ff44'),
    ]

    for k_min, k_max, name, color in crisis_regions:
        ax_timeline.axhspan(k_min, k_max, alpha=0.15, color=color)
        ax_timeline.text(sim.config.simulation.simulation_duration_gyr * 0.98,
                        (k_min + k_max) / 2,
                        name, fontsize=8, color=color, ha='right', va='center',
                        fontweight='bold')

    # Mark Kardashev types
    ax_timeline.axhline(1.0, color='lime', linestyle='--', alpha=0.5, linewidth=1, label='Type I')
    ax_timeline.axhline(2.0, color='orange', linestyle='--', alpha=0.5, linewidth=1, label='Type II')
    ax_timeline.legend(loc='upper left', facecolor='black', edgecolor='cyan',
                      labelcolor='white', fontsize=9)

    # Initialize scatter plots
    galaxy_active = None
    galaxy_dead = None
    timeline_lines = {}

    # Title
    title = fig.suptitle('', fontsize=16, color='cyan', fontweight='bold', y=0.98)

    def init():
        """Initialize animation."""
        return []

    def animate(frame_idx):
        """Update animation for each frame."""
        nonlocal galaxy_active, galaxy_dead, timeline_lines

        snapshot = sim.snapshots[frame_idx]
        current_time_gyr = snapshot.time_myr / 1000.0

        # Clear old galaxy scatters
        if galaxy_active is not None:
            galaxy_active.remove()
        if galaxy_dead is not None:
            galaxy_dead.remove()

        # Get civilization positions and states
        active_civs = []
        dead_civs = []

        # Build timeline data for all civilizations up to current time
        for civ in sim.civilizations:
            birth_time = civ.birth_time_myr / 1000.0

            if birth_time <= current_time_gyr:
                pos = sim.galaxy.positions[civ.parent_star_idx]

                # Galaxy view
                if civ.is_active:
                    active_civs.append((pos, civ.kardashev_scale))
                else:
                    if civ.death_time_myr and civ.death_time_myr / 1000.0 <= current_time_gyr:
                        dead_civs.append(pos)

                # Timeline view - draw evolution line
                if civ.civ_id not in timeline_lines:
                    timeline_lines[civ.civ_id] = {
                        'times': [],
                        'kardashev': [],
                        'line': None
                    }

                # Add current state to timeline
                data = timeline_lines[civ.civ_id]

                # Add birth point if not already added
                if len(data['times']) == 0:
                    data['times'].append(birth_time)
                    data['kardashev'].append(0.7)  # Starting Kardashev

                # Add current state if alive
                if civ.is_active and current_time_gyr > birth_time:
                    data['times'].append(current_time_gyr)
                    data['kardashev'].append(civ.kardashev_scale)
                elif not civ.is_active and civ.death_time_myr:
                    death_time = civ.death_time_myr / 1000.0
                    if death_time <= current_time_gyr and len(data['times']) < 3:
                        data['times'].append(death_time)
                        data['kardashev'].append(civ.kardashev_scale)

                # Draw line
                if len(data['times']) >= 2:
                    if data['line'] is not None:
                        data['line'].remove()

                    color = 'lime' if civ.is_active else 'red'
                    alpha = 0.8 if civ.is_active else 0.4
                    linewidth = 2 if civ.is_active else 1

                    data['line'], = ax_timeline.plot(data['times'], data['kardashev'],
                                                     color=color, alpha=alpha, linewidth=linewidth)

                    # Mark death with X
                    if not civ.is_active and len(data['times']) >= 2:
                        ax_timeline.plot(data['times'][-1], data['kardashev'][-1],
                                       'rx', markersize=8, markeredgewidth=2)

        # Plot galaxy view civilizations
        if active_civs:
            active_pos = np.array([c[0] for c in active_civs])
            active_k = np.array([c[1] for c in active_civs])
            colors = plt.cm.plasma(active_k / 2.5)

            galaxy_active = ax_galaxy.scatter(active_pos[:, 0], active_pos[:, 1],
                                             c=colors, s=80, marker='o',
                                             edgecolors='white', linewidths=1,
                                             alpha=0.9)

        if dead_civs:
            dead_pos = np.array(dead_civs)
            galaxy_dead = ax_galaxy.scatter(dead_pos[:, 0], dead_pos[:, 1],
                                           c='red', s=40, marker='x',
                                           alpha=0.5)

        # Current time marker on timeline
        ax_timeline.axvline(current_time_gyr, color='yellow', linestyle=':',
                           alpha=0.7, linewidth=2)

        # Update title
        n_active = len(active_civs)
        n_dead = len(dead_civs)
        title.set_text(f'GALACTIC CIVILIZATION EVOLUTION | Time: {current_time_gyr:.2f} Gyr | Active: {n_active} | Extinct: {n_dead}')

        artists = [title]
        if galaxy_active:
            artists.append(galaxy_active)
        if galaxy_dead:
            artists.append(galaxy_dead)

        return artists

    # Create animation
    anim = animation.FuncAnimation(fig, animate, init_func=init,
                                  frames=len(sim.snapshots),
                                  interval=250, blit=False)

    # Save to file
    print(f"  Saving to {output_file}...")
    anim.save(output_file, writer='ffmpeg', fps=8, dpi=120,
             extra_args=['-vcodec', 'libx264', '-pix_fmt', 'yuv420p'])

    plt.close(fig)
    print(f"✓ Saved: {output_file}")


def create_crisis_death_animation(sim, output_file='output/crisis_deaths_animation.mp4'):
    """
    Create animation focusing on WHERE civilizations die.

    Shows overhead view with civilizations color-coded by crisis region.
    """
    print("\nCreating crisis death animation...")

    fig, ax = plt.subplots(figsize=(12, 12))
    fig.patch.set_facecolor('#0a0a0a')
    ax.set_facecolor('#0a0a0a')
    ax.set_aspect('equal')

    # Sample stars
    sample_indices = np.random.choice(len(sim.galaxy.positions),
                                     size=min(2000, len(sim.galaxy.positions)),
                                     replace=False)
    stars_pos = sim.galaxy.positions[sample_indices]

    # Plot stars
    ax.scatter(stars_pos[:, 0], stars_pos[:, 1],
              c='grey', s=0.3, alpha=0.15)
    ax.set_xlim(-15, 15)
    ax.set_ylim(-15, 15)
    ax.set_xlabel('X [kpc]', fontsize=14, color='white', fontweight='bold')
    ax.set_ylabel('Y [kpc]', fontsize=14, color='white', fontweight='bold')
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_color('white')
        spine.set_linewidth(2)

    # Crisis color mapping
    crisis_colors = {
        'nuclear': '#ff4444',
        'planetary': '#ff8844',
        'ai': '#ffcc44',
        'interplanetary': '#88ff44',
        'stellar': '#4488ff',
        'relativistic': '#ff44ff',
        'active': '#00ffff'
    }

    def get_crisis_type(kardashev):
        """Determine which crisis region a Kardashev scale is in."""
        if 0.65 <= kardashev < 0.80:
            return 'nuclear'
        elif 0.80 <= kardashev < 0.95:
            return 'planetary'
        elif 0.95 <= kardashev < 1.15:
            return 'ai'
        elif 1.15 <= kardashev < 1.40:
            return 'interplanetary'
        elif 1.60 <= kardashev < 2.00:
            return 'stellar'
        elif 2.30 <= kardashev < 2.70:
            return 'relativistic'
        else:
            return 'active'

    scatters = {}
    title = ax.set_title('', fontsize=16, color='cyan', fontweight='bold')

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=crisis_colors['nuclear'], label='Nuclear Age Deaths'),
        Patch(facecolor=crisis_colors['planetary'], label='Planetary Unif. Deaths'),
        Patch(facecolor=crisis_colors['ai'], label='AI Transition Deaths'),
        Patch(facecolor=crisis_colors['interplanetary'], label='Interplanetary Deaths'),
        Patch(facecolor=crisis_colors['active'], label='Active Civilizations'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', facecolor='black',
             edgecolor='cyan', labelcolor='white', fontsize=10)

    def init():
        return []

    def animate(frame_idx):
        nonlocal scatters

        snapshot = sim.snapshots[frame_idx]
        current_time_gyr = snapshot.time_myr / 1000.0

        # Clear old scatters
        for scatter in scatters.values():
            scatter.remove()
        scatters = {}

        # Group civilizations by crisis type
        crisis_groups = {crisis: [] for crisis in crisis_colors.keys()}

        for civ in sim.civilizations:
            birth_time = civ.birth_time_myr / 1000.0

            if birth_time <= current_time_gyr:
                pos = sim.galaxy.positions[civ.parent_star_idx]

                if civ.is_active:
                    crisis_groups['active'].append(pos)
                else:
                    death_time = civ.death_time_myr / 1000.0 if civ.death_time_myr else current_time_gyr
                    if death_time <= current_time_gyr:
                        crisis_type = get_crisis_type(civ.kardashev_scale)
                        crisis_groups[crisis_type].append(pos)

        # Plot each group
        for crisis_type, positions in crisis_groups.items():
            if positions:
                pos_array = np.array(positions)
                marker = 'o' if crisis_type == 'active' else 'x'
                size = 100 if crisis_type == 'active' else 60
                alpha = 0.9 if crisis_type == 'active' else 0.7

                scatters[crisis_type] = ax.scatter(
                    pos_array[:, 0], pos_array[:, 1],
                    c=crisis_colors[crisis_type], s=size, marker=marker,
                    edgecolors='white' if crisis_type == 'active' else 'none',
                    linewidths=1, alpha=alpha
                )

        # Update title
        total_dead = sum(len(crisis_groups[c]) for c in crisis_groups if c != 'active')
        title.set_text(f'WHERE DO CIVILIZATIONS DIE? | Time: {current_time_gyr:.2f} Gyr | ' +
                      f'Active: {len(crisis_groups["active"])} | Dead: {total_dead}')

        return list(scatters.values()) + [title]

    # Create animation
    anim = animation.FuncAnimation(fig, animate, init_func=init,
                                  frames=len(sim.snapshots),
                                  interval=250, blit=False)

    # Save
    print(f"  Saving to {output_file}...")
    anim.save(output_file, writer='ffmpeg', fps=8, dpi=120,
             extra_args=['-vcodec', 'libx264', '-pix_fmt', 'yuv420p'])

    plt.close(fig)
    print(f"✓ Saved: {output_file}")


def main():
    """Run simulation and create all animations."""

    print("=" * 80)
    print(" " * 25 + "3D MOVIE GENERATION")
    print("=" * 80)
    print()
    print("This will create multiple movie files showing galactic civilization evolution.")
    print()

    # Check for ffmpeg
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: ffmpeg not found!")
        print("Please install ffmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt-get install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/")
        return

    # Create configuration
    print("Creating simulation configuration...")
    config = create_demo_config_for_animation()

    print(f"\nSimulation Parameters:")
    print(f"  Galaxy: {config.galaxy.total_stars:,} stars")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Snapshots: {int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.snapshot_interval_myr)}")

    # Run simulation
    print("\n" + "=" * 80)
    print("RUNNING SIMULATION")
    print("=" * 80)

    sim = GalaxySimulation(config, seed=42)
    sim.initialize()

    print(f"\nGalaxy initialized:")
    print(f"  Habitable stars: {len(sim.habitable_star_indices):,}")

    print("\nSimulating galactic history...")
    sim.run()

    total_civs = len(sim.civilizations)
    active_civs = sum(1 for c in sim.civilizations if c.is_active)

    print(f"\nSimulation complete!")
    print(f"  Total civilizations: {total_civs}")
    print(f"  Currently active: {active_civs}")
    print(f"  Extinct: {total_civs - active_civs}")
    print(f"  Snapshots captured: {len(sim.snapshots)}")

    # Create animations
    print("\n" + "=" * 80)
    print("CREATING ANIMATIONS")
    print("=" * 80)

    os.makedirs('output', exist_ok=True)

    # 1. Rotating 3D view
    create_rotating_3d_animation(sim)

    # 2. Overhead view with timeline
    create_overhead_timeline_animation(sim)

    # 3. Crisis death visualization
    create_crisis_death_animation(sim)

    print("\n" + "=" * 80)
    print("COMPLETE!")
    print("=" * 80)
    print("\nGenerated movies:")
    print("  1. output/galaxy_3d_rotating.mp4 - Rotating 3D galaxy view")
    print("  2. output/galaxy_overhead_timeline.mp4 - Overhead view with Kardashev timeline")
    print("  3. output/crisis_deaths_animation.mp4 - Crisis death locations")
    print("\n✓ All animations complete!")


if __name__ == '__main__':
    main()
