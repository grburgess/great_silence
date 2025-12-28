"""
Production-quality simulation run with comprehensive visualization.

Features:
- Extended duration (10,000 Myr) to observe astrophysical deaths
- Organized output directory structure
- All visualization types (3D, networks, statistics, timelines)
- Timestamped runs for tracking
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patches as mpatches
import matplotlib.animation as animation

# Import from the realistic 3D simulation
from examples.realistic_3d_simulation import Realistic3DSimulation


def create_run_directory(base_dir: str = "outputs") -> Path:
    """Create timestamped run directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(base_dir) / f"run_{timestamp}"

    # Create subdirectories
    (run_dir / "data").mkdir(parents=True, exist_ok=True)
    (run_dir / "plots" / "3d").mkdir(parents=True, exist_ok=True)
    (run_dir / "plots" / "networks").mkdir(parents=True, exist_ok=True)
    (run_dir / "plots" / "statistics").mkdir(parents=True, exist_ok=True)
    (run_dir / "plots" / "timelines").mkdir(parents=True, exist_ok=True)
    (run_dir / "animations").mkdir(parents=True, exist_ok=True)

    print(f"📁 Created run directory: {run_dir}")
    return run_dir


def plot_3d_snapshot(data, output_path):
    """3D scatter plot of all civilizations."""
    fig = plt.figure(figsize=(16, 12), facecolor='black')
    ax = fig.add_subplot(111, projection='3d', facecolor='black')

    civs = data['civilizations']

    alive_pos, dead_crisis_pos, dead_sn_pos, dead_grb_pos = [], [], [], []

    for civ in civs:
        pos = np.array(civ['position'])
        if civ['alive']:
            alive_pos.append(pos)
        else:
            cause = civ.get('cause_of_death', 'unknown')
            if 'supernova' in cause:
                dead_sn_pos.append(pos)
            elif 'gamma' in cause or 'grb' in cause:
                dead_grb_pos.append(pos)
            else:
                dead_crisis_pos.append(pos)

    if alive_pos:
        alive = np.array(alive_pos)
        ax.scatter(alive[:, 0], alive[:, 1], alive[:, 2],
                  c='#2ecc71', s=200, marker='o', edgecolors='white',
                  linewidths=2, alpha=0.9, label=f'Alive ({len(alive_pos)})')

    if dead_crisis_pos:
        dead_c = np.array(dead_crisis_pos)
        ax.scatter(dead_c[:, 0], dead_c[:, 1], dead_c[:, 2],
                  c='#e74c3c', s=200, marker='x', linewidths=3,
                  alpha=0.7, label=f'Dead (Crisis) ({len(dead_crisis_pos)})')

    if dead_sn_pos:
        dead_sn = np.array(dead_sn_pos)
        ax.scatter(dead_sn[:, 0], dead_sn[:, 1], dead_sn[:, 2],
                  c='#f39c12', s=200, marker='*', linewidths=2,
                  alpha=0.7, label=f'Dead (Supernova) ({len(dead_sn_pos)})')

    if dead_grb_pos:
        dead_grb = np.array(dead_grb_pos)
        ax.scatter(dead_grb[:, 0], dead_grb[:, 1], dead_grb[:, 2],
                  c='#9b59b6', s=200, marker='^', linewidths=2,
                  alpha=0.7, label=f'Dead (GRB) ({len(dead_grb_pos)})')

    # Plot SN/GRB events
    for evt in data.get('supernova_events', [])[:20]:  # Limit for visibility
        pos = evt['position']
        ax.scatter(pos[0], pos[1], pos[2], c='#f39c12', s=500, marker='*', alpha=0.3)

    for evt in data.get('grb_events', [])[:20]:
        pos = evt['position']
        ax.scatter(pos[0], pos[1], pos[2], c='#9b59b6', s=600, marker='D', alpha=0.3)

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

    ax.set_title(f"3D Galactic Civilization Map (Final State)\n"
                f"Duration: {data['metadata']['duration_myr']:.0f} Myr",
                fontsize=16, color='white', weight='bold', pad=20)

    ax.legend(loc='upper left', framealpha=0.9, facecolor='black',
             edgecolor='white', labelcolor='white', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='black')
    plt.close()
    print(f"  ✓ 3D snapshot: {output_path.name}")


def plot_crisis_statistics(data, output_path, run_dir):
    """Plot crisis statistics and outcomes."""
    # Load the full export data
    full_export_path = run_dir / "data" / "realistic_3d_export.json"
    with open(full_export_path, 'r') as f:
        export_data = json.load(f)

    fig = plt.figure(figsize=(16, 10), facecolor='black')

    # Crisis types breakdown
    ax1 = fig.add_subplot(2, 3, 1, facecolor='black')
    crisis_types = export_data['summary_stats']['crises_by_type']
    if crisis_types:
        colors = ['#e74c3c', '#f39c12', '#3498db', '#2ecc71', '#9b59b6',
                 '#e67e22', '#1abc9c', '#34495e', '#95a5a6']
        ax1.pie(crisis_types.values(), labels=crisis_types.keys(), autopct='%1.1f%%',
               colors=colors[:len(crisis_types)], textprops={'color': 'white'})
        ax1.set_title('Crisis Types Distribution', color='white', fontsize=12, weight='bold')

    # Survival rate
    ax2 = fig.add_subplot(2, 3, 2, facecolor='black')
    survived = export_data['summary_stats']['crises_survived']
    failed = export_data['summary_stats']['crises_failed']
    ax2.bar(['Survived', 'Failed'], [survived, failed], color=['#2ecc71', '#e74c3c'])
    ax2.set_ylabel('Count', color='white', fontsize=11)
    ax2.set_title(f"Crisis Outcomes (Survival Rate: {export_data['summary_stats']['survival_rate']:.1f}%)",
                 color='white', fontsize=12, weight='bold')
    ax2.tick_params(colors='white')
    for spine in ax2.spines.values():
        spine.set_color('white')

    # Cooperation types
    ax3 = fig.add_subplot(2, 3, 3, facecolor='black')
    coop_types = export_data['summary_stats']['cooperations_by_type']
    if coop_types:
        ax3.bar(range(len(coop_types)), list(coop_types.values()), color='#3498db')
        ax3.set_xticks(range(len(coop_types)))
        ax3.set_xticklabels(coop_types.keys(), rotation=45, ha='right', color='white')
        ax3.set_ylabel('Count', color='white', fontsize=11)
        ax3.set_title(f"Cooperation Events (Total: {export_data['summary_stats']['total_cooperations']})",
                     color='white', fontsize=12, weight='bold')
        ax3.tick_params(colors='white')
        for spine in ax3.spines.values():
            spine.set_color('white')

    # Development paths
    ax4 = fig.add_subplot(2, 3, 4, facecolor='black')
    dev_paths = export_data['summary_stats']['development_paths']
    if dev_paths:
        ax4.bar(range(len(dev_paths)), list(dev_paths.values()), color='#9b59b6')
        ax4.set_xticks(range(len(dev_paths)))
        ax4.set_xticklabels(dev_paths.keys(), rotation=45, ha='right', color='white')
        ax4.set_ylabel('Count', color='white', fontsize=11)
        ax4.set_title('Development Path Types', color='white', fontsize=12, weight='bold')
        ax4.tick_params(colors='white')
        for spine in ax4.spines.values():
            spine.set_color('white')

    # Astrophysical events
    ax5 = fig.add_subplot(2, 3, 5, facecolor='black')
    num_sn = len(data.get('supernova_events', []))
    num_grb = len(data.get('grb_events', []))
    num_alive = data['metadata']['num_alive']
    num_dead = data['metadata']['num_dead']

    ax5.bar(['Supernovae', 'GRBs', 'Alive', 'Dead'],
           [num_sn, num_grb, num_alive, num_dead],
           color=['#f39c12', '#9b59b6', '#2ecc71', '#e74c3c'])
    ax5.set_ylabel('Count', color='white', fontsize=11)
    ax5.set_title('Astrophysical Events & Final Status', color='white', fontsize=12, weight='bold')
    ax5.tick_params(colors='white')
    for spine in ax5.spines.values():
        spine.set_color('white')

    # Summary text
    ax6 = fig.add_subplot(2, 3, 6, facecolor='black')
    ax6.axis('off')
    summary_text = f"""SIMULATION SUMMARY

Duration: {data['metadata']['duration_myr']:.0f} Myr
Civilizations: {data['metadata']['num_civilizations']}
Stars: {data['metadata']['num_stars']:,}

Final Status:
  Alive: {num_alive} ({num_alive/data['metadata']['num_civilizations']*100:.1f}%)
  Dead: {num_dead} ({num_dead/data['metadata']['num_civilizations']*100:.1f}%)

Total Crises: {export_data['summary_stats']['total_crises']}
Survival Rate: {export_data['summary_stats']['survival_rate']:.1f}%

Cooperations: {export_data['summary_stats']['total_cooperations']}
Avg Effectiveness: {export_data['summary_stats']['avg_cooperation_effectiveness']:.2f}

Astrophysical Events:
  Supernovae: {num_sn}
  Gamma-ray Bursts: {num_grb}
"""
    ax6.text(0.1, 0.5, summary_text, color='white', fontsize=10,
            verticalalignment='center', family='monospace')

    plt.suptitle('Comprehensive Crisis & Cooperation Statistics',
                fontsize=16, color='white', weight='bold', y=0.98)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='black')
    plt.close()
    print(f"  ✓ Crisis statistics: {output_path.name}")


def plot_development_timelines(data, output_path):
    """Plot Kardashev and maturity development over time."""
    fig = plt.figure(figsize=(16, 10), facecolor='black')

    # Kardashev evolution
    ax1 = fig.add_subplot(2, 1, 1, facecolor='black')
    for civ in data['civilizations']:
        history = civ.get('development_history', [])
        if history:
            times = [s['time_myr'] for s in history]
            k_levels = [s['kardashev_level'] for s in history]

            if civ['alive']:
                ax1.plot(times, k_levels, color='#2ecc71', alpha=0.6, linewidth=1.5)
            else:
                ax1.plot(times, k_levels, color='#e74c3c', alpha=0.4, linewidth=1)
                # Mark death
                if civ.get('death_time_myr'):
                    ax1.scatter(civ['death_time_myr'], k_levels[-1],
                              color='#e74c3c', s=100, marker='x', zorder=10)

    ax1.set_xlabel('Time (Myr)', color='white', fontsize=12)
    ax1.set_ylabel('Kardashev Level', color='white', fontsize=12)
    ax1.set_title('Kardashev Level Evolution Over Time', color='white', fontsize=14, weight='bold')
    ax1.grid(True, alpha=0.2, color='white')
    ax1.tick_params(colors='white')
    for spine in ax1.spines.values():
        spine.set_color('white')

    # Maturity evolution
    ax2 = fig.add_subplot(2, 1, 2, facecolor='black')
    for civ in data['civilizations']:
        history = civ.get('development_history', [])
        if history:
            times = [s['time_myr'] for s in history]
            maturity = [s['maturity_level'] for s in history]

            if civ['alive']:
                ax2.plot(times, maturity, color='#3498db', alpha=0.6, linewidth=1.5)
            else:
                ax2.plot(times, maturity, color='#e74c3c', alpha=0.4, linewidth=1)
                if civ.get('death_time_myr'):
                    ax2.scatter(civ['death_time_myr'], maturity[-1],
                              color='#e74c3c', s=100, marker='x', zorder=10)

    ax2.set_xlabel('Time (Myr)', color='white', fontsize=12)
    ax2.set_ylabel('Social Maturity Level', color='white', fontsize=12)
    ax2.set_title('Social Maturity Evolution Over Time', color='white', fontsize=14, weight='bold')
    ax2.grid(True, alpha=0.2, color='white')
    ax2.tick_params(colors='white')
    for spine in ax2.spines.values():
        spine.set_color('white')

    # Legend
    alive_patch = mpatches.Patch(color='#2ecc71', label='Survived')
    dead_patch = mpatches.Patch(color='#e74c3c', label='Died')
    ax1.legend(handles=[alive_patch, dead_patch], loc='lower right',
              framealpha=0.9, facecolor='black', edgecolor='white',
              labelcolor='white', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='black')
    plt.close()
    print(f"  ✓ Development timelines: {output_path.name}")


def create_evolution_animation(data, output_path):
    """Animated 3D evolution."""
    print(f"  Creating evolution animation...")

    fig = plt.figure(figsize=(14, 10), facecolor='black')
    ax = fig.add_subplot(111, projection='3d', facecolor='black')

    civs = data['civilizations']
    duration = data['metadata']['duration_myr']
    num_frames = 100  # More frames for longer simulation
    time_points = np.linspace(0, duration, num_frames)

    def update_frame(frame):
        ax.cla()
        current_time = time_points[frame]

        for civ in civs:
            pos = np.array(civ['position'])
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

                ax.scatter(pos[0], pos[1], pos[2], c=color, s=100,
                          marker=marker, linewidths=2, alpha=0.5)
            else:
                # Alive - size by K-level
                history = civ.get('development_history', [])
                if history:
                    times = [s['time_myr'] for s in history]
                    idx = np.searchsorted(times, current_time)
                    if idx < len(history):
                        k = history[idx]['kardashev_level']
                        size = 50 + 150 * (k - 0.6)
                    else:
                        size = 100
                else:
                    size = 100

                ax.scatter(pos[0], pos[1], pos[2], c='#2ecc71', s=size,
                          marker='o', edgecolors='white', linewidths=2, alpha=0.9)

        # Plot recent SN/GRB events
        for evt in data.get('supernova_events', []):
            if evt['time_myr'] <= current_time:
                pos = evt['position']
                ax.scatter(pos[0], pos[1], pos[2], c='#f39c12',
                          s=300, marker='*', alpha=0.4)

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

        alive_count = sum(1 for c in civs
                         if not (c.get('death_time_myr') and
                                c.get('death_time_myr') <= current_time))

        ax.set_title(f"Galactic Evolution | T = {current_time:.0f} Myr | "
                    f"Alive: {alive_count}/{len(civs)}",
                    fontsize=14, color='white', weight='bold', pad=20)

        return []

    anim = animation.FuncAnimation(fig, update_frame, frames=num_frames,
                                  interval=100, blit=False)
    anim.save(output_path, writer='pillow', fps=10, dpi=100)
    plt.close()
    print(f"  ✓ Animation: {output_path.name}")


def main():
    """Run production simulation with comprehensive outputs."""
    print("\n" + "="*70)
    print("PRODUCTION GALACTIC CIVILIZATION SIMULATION")
    print("="*70)
    print("\nConfiguration:")
    print("  Duration: 10,000 Myr (10 Gyr)")
    print("  Civilizations: 20")
    print("  Stars: 100,000")
    print("  Features: 3D positions, astrophysical hazards, adaptive timesteps")
    print("  Output: Organized in timestamped directory")
    print("\n" + "="*70 + "\n")

    # Create run directory
    run_dir = create_run_directory()

    # Run simulation
    print("🚀 Starting simulation...\n")
    sim = Realistic3DSimulation(
        num_stars=100000,
        num_civilizations=20,
        seed=42
    )

    sim.initialize()
    sim.run(duration_myr=10000.0, print_interval_myr=1000.0)

    # Export data
    print("\n📊 Exporting data...")
    data_dir = run_dir / "data"

    sim.export_3d_data(str(data_dir / "simulation_3d_data.json"))
    sim.export_visualization_data(str(data_dir / "realistic_3d_export.json"))

    # Load data for plotting
    with open(data_dir / "simulation_3d_data.json", 'r') as f:
        plot_data = json.load(f)

    # Generate all plots
    print("\n🎨 Generating visualizations...")
    print("\n3D Plots:")
    plot_3d_snapshot(plot_data, run_dir / "plots" / "3d" / "galaxy_snapshot.png")

    print("\nStatistics:")
    plot_crisis_statistics(plot_data, run_dir / "plots" / "statistics" / "crisis_stats.png", run_dir)

    print("\nTimelines:")
    plot_development_timelines(plot_data, run_dir / "plots" / "timelines" / "development_evolution.png")

    print("\nAnimations:")
    create_evolution_animation(plot_data, run_dir / "animations" / "galaxy_evolution.gif")

    # Save summary
    summary_path = run_dir / "SUMMARY.txt"
    with open(summary_path, 'w') as f:
        f.write("="*70 + "\n")
        f.write("PRODUCTION SIMULATION RUN SUMMARY\n")
        f.write("="*70 + "\n\n")
        f.write(f"Run Directory: {run_dir}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Duration: {plot_data['metadata']['duration_myr']:.0f} Myr\n")
        f.write(f"Civilizations: {plot_data['metadata']['num_civilizations']}\n")
        f.write(f"Stars: {plot_data['metadata']['num_stars']:,}\n\n")
        f.write(f"Final Status:\n")
        f.write(f"  Alive: {plot_data['metadata']['num_alive']}\n")
        f.write(f"  Dead: {plot_data['metadata']['num_dead']}\n\n")
        f.write(f"Astrophysical Events:\n")
        f.write(f"  Supernovae: {len(plot_data.get('supernova_events', []))}\n")
        f.write(f"  GRBs: {len(plot_data.get('grb_events', []))}\n\n")
        f.write("Files Generated:\n")
        f.write(f"  Data: data/simulation_3d_data.json\n")
        f.write(f"  Data: data/realistic_3d_export.json\n")
        f.write(f"  Plot: plots/3d/galaxy_snapshot.png\n")
        f.write(f"  Plot: plots/statistics/crisis_stats.png\n")
        f.write(f"  Plot: plots/timelines/development_evolution.png\n")
        f.write(f"  Animation: animations/galaxy_evolution.gif\n")

    print(f"\n✅ Production run complete!")
    print(f"📁 All outputs saved to: {run_dir}")
    print(f"📄 Summary: {summary_path}")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
