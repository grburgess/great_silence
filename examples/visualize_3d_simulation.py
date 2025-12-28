"""
3D visualization and animation for realistic galactic simulation.

Creates:
- 3D scatter plot of civilizations in the galaxy
- Supernova and GRB events in 3D space
- Animated evolution over time
- Color-coded by status (alive/dead/cause of death)
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
from matplotlib.patches import Circle
import matplotlib.patches as mpatches


def load_3d_simulation_data(filepath: str = "realistic_3d_data.json"):
    """Load exported 3D simulation data."""
    with open(filepath, 'r') as f:
        return json.load(f)


def plot_3d_galaxy_snapshot(data, output_path: str = "galaxy_3d_snapshot.png"):
    """
    Create 3D snapshot of galaxy with all civilizations.

    Args:
        data: Exported simulation data
        output_path: Where to save the plot
    """
    fig = plt.figure(figsize=(16, 12), facecolor='black')
    ax = fig.add_subplot(111, projection='3d', facecolor='black')

    # Get civilization positions and status
    civs = data['civilizations']
    metadata = data['metadata']

    if not civs:
        print("No civilization data available")
        return

    # Separate alive and dead
    alive_positions = []
    dead_by_crisis_positions = []
    dead_by_sn_positions = []
    dead_by_grb_positions = []

    alive_ids = []
    dead_crisis_ids = []
    dead_sn_ids = []
    dead_grb_ids = []

    for civ in civs:
        pos = np.array(civ['position'])
        civ_id = civ['id']

        if civ['alive']:
            alive_positions.append(pos)
            alive_ids.append(civ_id)
        else:
            cause = civ.get('cause_of_death', 'unknown')
            if cause == 'supernova':
                dead_by_sn_positions.append(pos)
                dead_sn_ids.append(civ_id)
            elif cause == 'gamma_ray_burst':
                dead_by_grb_positions.append(pos)
                dead_grb_ids.append(civ_id)
            else:
                dead_by_crisis_positions.append(pos)
                dead_crisis_ids.append(civ_id)

    # Plot civilizations
    if alive_positions:
        alive_pos = np.array(alive_positions)
        ax.scatter(alive_pos[:, 0], alive_pos[:, 1], alive_pos[:, 2],
                  c='#2ecc71', s=200, marker='o', edgecolors='white',
                  linewidths=2, alpha=0.9, label=f'Alive ({len(alive_positions)})')

    if dead_by_crisis_positions:
        dead_crisis = np.array(dead_by_crisis_positions)
        ax.scatter(dead_crisis[:, 0], dead_crisis[:, 1], dead_crisis[:, 2],
                  c='#e74c3c', s=200, marker='x', linewidths=3,
                  alpha=0.7, label=f'Dead (Crisis) ({len(dead_by_crisis_positions)})')

    if dead_by_sn_positions:
        dead_sn = np.array(dead_by_sn_positions)
        ax.scatter(dead_sn[:, 0], dead_sn[:, 1], dead_sn[:, 2],
                  c='#f39c12', s=200, marker='*', linewidths=2,
                  alpha=0.7, label=f'Dead (Supernova) ({len(dead_by_sn_positions)})')

    if dead_by_grb_positions:
        dead_grb = np.array(dead_by_grb_positions)
        ax.scatter(dead_grb[:, 0], dead_grb[:, 1], dead_grb[:, 2],
                  c='#9b59b6', s=200, marker='^', linewidths=2,
                  alpha=0.7, label=f'Dead (GRB) ({len(dead_by_grb_positions)})')

    # Plot supernova events
    sn_events = data.get('supernova_events', [])
    if sn_events:
        sn_positions = np.array([evt['position'] for evt in sn_events])
        ax.scatter(sn_positions[:, 0], sn_positions[:, 1], sn_positions[:, 2],
                  c='#f39c12', s=500, marker='*', alpha=0.3,
                  label=f'Supernovae ({len(sn_events)})')

    # Plot GRB events
    grb_events = data.get('grb_events', [])
    if grb_events:
        grb_positions = np.array([evt['position'] for evt in grb_events])
        ax.scatter(grb_positions[:, 0], grb_positions[:, 1], grb_positions[:, 2],
                  c='#9b59b6', s=600, marker='D', alpha=0.3,
                  label=f'GRBs ({len(grb_events)})')

    # Styling
    ax.set_xlabel('X (kpc)', fontsize=12, color='white')
    ax.set_ylabel('Y (kpc)', fontsize=12, color='white')
    ax.set_zlabel('Z (kpc)', fontsize=12, color='white')
    ax.tick_params(colors='white')
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('white')
    ax.yaxis.pane.set_edgecolor('white')
    ax.zaxis.pane.set_edgecolor('white')
    ax.grid(True, alpha=0.2, color='white')

    # Title with statistics
    total = metadata.get('num_civilizations', 0)
    alive_count = len(alive_positions)
    survival_rate = 100 * alive_count / total if total > 0 else 0
    duration = metadata.get('duration_myr', 0)

    ax.set_title(f"3D Galactic Civilization Map\n"
                f"{alive_count}/{total} Alive ({survival_rate:.1f}%) after {duration:.0f} Myr",
                fontsize=16, color='white', weight='bold', pad=20)

    ax.legend(loc='upper left', framealpha=0.9, facecolor='black',
             edgecolor='white', labelcolor='white', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='black')
    plt.close()
    print(f"  🌌 3D galaxy snapshot saved to: {output_path}")


def plot_3d_galaxy_with_hazard_zones(data, output_path: str = "galaxy_hazard_zones.png"):
    """
    Plot 3D galaxy with hazard zones highlighted.

    Shows lethal zones around supernova and GRB events.
    """
    fig = plt.figure(figsize=(16, 12), facecolor='black')
    ax = fig.add_subplot(111, projection='3d', facecolor='black')

    # Get civilization positions
    civs = data['civilizations']
    metadata = data['metadata']

    # Plot civilizations
    for civ in civs:
        pos = np.array(civ['position'])
        civ_id = civ['id']

        if civ['alive']:
            ax.scatter(pos[0], pos[1], pos[2],
                      c='#2ecc71', s=150, marker='o', edgecolors='white',
                      linewidths=2, alpha=0.9)
            ax.text(pos[0], pos[1], pos[2], f"  C{civ_id}",
                   color='white', fontsize=8)
        else:
            cause = civ.get('cause_of_death', 'unknown')
            if 'supernova' in cause:
                color = '#f39c12'
                marker = '*'
            elif 'gamma' in cause or 'grb' in cause:
                color = '#9b59b6'
                marker = '^'
            else:
                color = '#e74c3c'
                marker = 'x'

            ax.scatter(pos[0], pos[1], pos[2],
                      c=color, s=150, marker=marker, linewidths=2, alpha=0.7)
            ax.text(pos[0], pos[1], pos[2], f"  C{civ_id}✗",
                   color=color, fontsize=8, alpha=0.7)

    # Plot supernova hazard zones (10 pc lethal radius)
    sn_events = data.get('supernova_events', [])
    for i, evt in enumerate(sn_events[:10]):  # Limit to first 10 for clarity
        pos = np.array(evt['position'])

        # Draw sphere
        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(0, np.pi, 10)
        x = 0.01 * np.outer(np.cos(u), np.sin(v)) + pos[0]  # 10 pc = 0.01 kpc
        y = 0.01 * np.outer(np.sin(u), np.sin(v)) + pos[1]
        z = 0.01 * np.outer(np.ones(np.size(u)), np.cos(v)) + pos[2]

        ax.plot_surface(x, y, z, color='#f39c12', alpha=0.1, linewidth=0)
        ax.scatter(pos[0], pos[1], pos[2], c='#f39c12', s=400, marker='*',
                  alpha=0.5, edgecolors='white', linewidths=1)

    # Styling
    ax.set_xlabel('X (kpc)', fontsize=12, color='white')
    ax.set_ylabel('Y (kpc)', fontsize=12, color='white')
    ax.set_zlabel('Z (kpc)', fontsize=12, color='white')
    ax.tick_params(colors='white')
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('white')
    ax.yaxis.pane.set_edgecolor('white')
    ax.zaxis.pane.set_edgecolor('white')
    ax.grid(True, alpha=0.2, color='white')

    ax.set_title(f"3D Galaxy with Astrophysical Hazard Zones\n"
                f"Supernova lethal radius: 10 pc (shown as spheres)",
                fontsize=16, color='white', weight='bold', pad=20)

    # Legend
    legend_elements = [
        mpatches.Patch(color='#2ecc71', label='Alive'),
        mpatches.Patch(color='#f39c12', label='Killed by Supernova'),
        mpatches.Patch(color='#9b59b6', label='Killed by GRB'),
        mpatches.Patch(color='#e74c3c', label='Killed by Crisis'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', framealpha=0.9,
             facecolor='black', edgecolor='white', labelcolor='white', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='black')
    plt.close()
    print(f"  ☢️  Hazard zones plot saved to: {output_path}")


def create_evolution_animation(data, output_path: str = "galaxy_evolution.gif"):
    """
    Create animated evolution of civilizations over time.

    Shows civilizations appearing, evolving, and dying in 3D space.
    """
    print(f"  🎬 Creating evolution animation...")

    fig = plt.figure(figsize=(14, 10), facecolor='black')
    ax = fig.add_subplot(111, projection='3d', facecolor='black')

    civs = data['civilizations']
    metadata = data['metadata']

    if not civs:
        print("No civilization data for animation")
        return

    # Get time range
    duration = metadata.get('duration_myr', 1000.0)
    num_frames = 50
    time_points = np.linspace(0, duration, num_frames)

    def update_frame(frame):
        """Update animation frame."""
        ax.cla()

        current_time = time_points[frame]

        # Plot each civilization
        for civ in civs:
            pos = np.array(civ['position'])
            civ_id = civ['id']

            death_time = civ.get('death_time_myr')
            if death_time and death_time <= current_time:
                # Dead
                cause = civ.get('cause_of_death', 'unknown')
                if 'supernova' in cause:
                    color, marker = '#f39c12', '*'
                elif 'gamma' in cause or 'grb' in cause:
                    color, marker = '#9b59b6', '^'
                else:
                    color, marker = '#e74c3c', 'x'

                ax.scatter(pos[0], pos[1], pos[2],
                          c=color, s=100, marker=marker, linewidths=2, alpha=0.5)
            else:
                # Alive
                # Size based on Kardashev level at this time
                snapshots = civ.get('development_history', [])
                if snapshots:
                    # Find closest snapshot
                    times = [s['time_myr'] for s in snapshots]
                    idx = np.searchsorted(times, current_time)
                    if idx < len(snapshots):
                        k_level = snapshots[idx]['kardashev_level']
                        size = 50 + 150 * (k_level - 0.6)  # Scale with K
                    else:
                        size = 100
                else:
                    size = 100

                ax.scatter(pos[0], pos[1], pos[2],
                          c='#2ecc71', s=size, marker='o', edgecolors='white',
                          linewidths=2, alpha=0.9)

        # Plot supernova events that have occurred
        sn_events = [evt for evt in data.get('supernova_events', [])
                     if evt['time_myr'] <= current_time]
        if sn_events:
            sn_pos = np.array([evt['position'] for evt in sn_events])
            ax.scatter(sn_pos[:, 0], sn_pos[:, 1], sn_pos[:, 2],
                      c='#f39c12', s=300, marker='*', alpha=0.4)

        # Styling
        ax.set_xlabel('X (kpc)', fontsize=10, color='white')
        ax.set_ylabel('Y (kpc)', fontsize=10, color='white')
        ax.set_zlabel('Z (kpc)', fontsize=10, color='white')
        ax.tick_params(colors='white', labelsize=8)
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor('white')
        ax.yaxis.pane.set_edgecolor('white')
        ax.zaxis.pane.set_edgecolor('white')
        ax.grid(True, alpha=0.2, color='white')

        # Count alive
        alive_count = sum(1 for civ in civs
                         if not (civ.get('death_time_myr') and
                                civ.get('death_time_myr') <= current_time))

        ax.set_title(f"Galactic Evolution: T={current_time:.0f} Myr\n"
                    f"Alive: {alive_count}/{len(civs)} | "
                    f"Supernovae: {len(sn_events)}",
                    fontsize=14, color='white', weight='bold')

        # Set consistent limits
        ax.set_xlim([-15, 15])
        ax.set_ylim([-15, 15])
        ax.set_zlim([-5, 5])

    anim = animation.FuncAnimation(fig, update_frame, frames=num_frames,
                                   interval=200, blit=False)

    anim.save(output_path, writer='pillow', fps=5, dpi=100)
    plt.close()
    print(f"  ✅ Animation saved to: {output_path}")


def plot_development_in_3d(data, output_path: str = "development_3d_paths.png"):
    """
    Plot development trajectories with 3D positions.

    Shows how Kardashev level evolves for civilizations at different
    positions in the galaxy.
    """
    fig = plt.figure(figsize=(18, 6), facecolor='black')

    # Left plot: X-Y projection with K-level color
    ax1 = fig.add_subplot(131, facecolor='black')
    ax1.set_facecolor('black')

    # Middle plot: X-Z projection
    ax2 = fig.add_subplot(132, facecolor='black')
    ax2.set_facecolor('black')

    # Right plot: K-level vs distance from center
    ax3 = fig.add_subplot(133, facecolor='black')
    ax3.set_facecolor('black')

    civs = data['civilizations']

    for civ in civs:
        pos = np.array(civ['position'])
        snapshots = civ.get('development_history', [])

        if not snapshots:
            continue

        # Get final K-level
        final_k = snapshots[-1]['kardashev_level']

        # Color by K-level
        color = plt.cm.plasma((final_k - 0.6) / 1.5)  # 0.6-2.1 → 0-1

        # Plot position with K-level color
        if civ['alive']:
            marker, alpha, size = 'o', 0.9, 150
        else:
            marker, alpha, size = 'x', 0.5, 100

        ax1.scatter(pos[0], pos[1], c=[color], s=size, marker=marker,
                   alpha=alpha, edgecolors='white', linewidths=1.5)
        ax2.scatter(pos[0], pos[2], c=[color], s=size, marker=marker,
                   alpha=alpha, edgecolors='white', linewidths=1.5)

        # Distance from center vs K-level
        distance = np.linalg.norm(pos)
        ax3.scatter(distance, final_k, c=[color], s=size, marker=marker,
                   alpha=alpha, edgecolors='white', linewidths=1.5)

    # Styling
    for ax in [ax1, ax2]:
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.2, color='white')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')

    ax1.set_xlabel('X (kpc)', color='white', fontsize=11)
    ax1.set_ylabel('Y (kpc)', color='white', fontsize=11)
    ax1.set_title('X-Y Projection\n(color = final K-level)',
                 color='white', fontsize=12, weight='bold')

    ax2.set_xlabel('X (kpc)', color='white', fontsize=11)
    ax2.set_ylabel('Z (kpc)', color='white', fontsize=11)
    ax2.set_title('X-Z Projection\n(color = final K-level)',
                 color='white', fontsize=12, weight='bold')

    ax3.set_xlabel('Distance from Center (kpc)', color='white', fontsize=11)
    ax3.set_ylabel('Final Kardashev Level', color='white', fontsize=11)
    ax3.set_title('Development vs Position',
                 color='white', fontsize=12, weight='bold')
    ax3.grid(True, alpha=0.2, color='white')
    ax3.tick_params(colors='white')
    for spine in ax3.spines.values():
        spine.set_color('white')

    # Color bar
    sm = plt.cm.ScalarMappable(cmap=plt.cm.plasma,
                               norm=plt.Normalize(vmin=0.6, vmax=2.1))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=[ax1, ax2, ax3], orientation='horizontal',
                       pad=0.1, aspect=40)
    cbar.set_label('Kardashev Level', color='white', fontsize=11)
    cbar.ax.tick_params(colors='white')

    plt.suptitle('Civilization Development in 3D Space',
                fontsize=16, color='white', weight='bold', y=0.98)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='black')
    plt.close()
    print(f"  📍 3D development plot saved to: {output_path}")


def main():
    """Generate all 3D visualization plots."""
    print("\n" + "="*70)
    print("GENERATING 3D VISUALIZATION PLOTS")
    print("="*70 + "\n")

    # Load data
    print("Loading 3D simulation data...")
    try:
        data = load_3d_simulation_data()
    except FileNotFoundError:
        print("ERROR: realistic_3d_export.json not found!")
        print("Run the simulation first: python examples/realistic_3d_simulation.py")
        return

    # Create plots
    print("\nGenerating 3D plots...\n")
    plot_3d_galaxy_snapshot(data)
    plot_3d_galaxy_with_hazard_zones(data)
    plot_development_in_3d(data)
    create_evolution_animation(data)

    print("\n" + "="*70)
    print("✅ All 3D visualization plots generated successfully!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
