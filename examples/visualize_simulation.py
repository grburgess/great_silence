"""
Visualization script for civilization survival simulation results.

Creates plots from exported simulation data:
- Crisis flow chord diagram
- Development trajectory time series
- Cooperation network graph
- Summary statistics dashboard
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
from pathlib import Path


def load_simulation_data(filepath: str = "simulation_export.json"):
    """Load exported simulation data."""
    with open(filepath, 'r') as f:
        return json.load(f)


def plot_crisis_flows(chord_data, output_path: str = "crisis_flows.png"):
    """
    Plot crisis type to outcome flows as a Sankey-style diagram.

    Args:
        chord_data: Chord diagram data from export
        output_path: Where to save the plot
    """
    fig, ax = plt.subplots(figsize=(14, 8), facecolor='black')
    ax.set_facecolor('black')

    nodes = chord_data['nodes']
    matrix = chord_data['matrix']
    total_events = chord_data['total_events']

    if total_events == 0:
        ax.text(0.5, 0.5, "No crisis data available",
                ha='center', va='center', fontsize=20, color='white')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, facecolor='black')
        plt.close()
        return

    # Separate crisis types and outcomes
    crisis_types = [n for n in nodes if n not in ['survived', 'failed']]
    outcomes = [n for n in nodes if n in ['survived', 'failed']]

    # Position crisis types on left, outcomes on right
    left_y_positions = np.linspace(0.1, 0.9, len(crisis_types))
    right_y_positions = np.linspace(0.3, 0.7, len(outcomes))

    # Draw nodes
    node_positions = {}

    # Crisis types (left side)
    for i, crisis in enumerate(crisis_types):
        y = left_y_positions[i]
        node_positions[crisis] = (0.15, y)

        # Count total for this crisis
        crisis_idx = nodes.index(crisis)
        total = sum(matrix[crisis_idx])

        ax.add_patch(FancyBboxPatch((0.05, y-0.03), 0.2, 0.06,
                                     boxstyle="round,pad=0.01",
                                     facecolor='#3498db', edgecolor='white', linewidth=2))
        ax.text(0.15, y, f"{crisis.replace('_', ' ').title()}\n({total})",
                ha='center', va='center', fontsize=10, color='white', weight='bold')

    # Outcomes (right side)
    for i, outcome in enumerate(outcomes):
        y = right_y_positions[i]
        node_positions[outcome] = (0.85, y)

        # Count total for this outcome
        outcome_idx = nodes.index(outcome)
        total = sum(matrix[j][outcome_idx] for j in range(len(nodes)))

        color = '#2ecc71' if outcome == 'survived' else '#e74c3c'
        ax.add_patch(FancyBboxPatch((0.75, y-0.03), 0.2, 0.06,
                                     boxstyle="round,pad=0.01",
                                     facecolor=color, edgecolor='white', linewidth=2))
        ax.text(0.85, y, f"{outcome.title()}\n({total})",
                ha='center', va='center', fontsize=12, color='white', weight='bold')

    # Draw flows
    for i, crisis in enumerate(crisis_types):
        crisis_idx = nodes.index(crisis)
        x1, y1 = node_positions[crisis]

        for j, outcome in enumerate(outcomes):
            outcome_idx = nodes.index(outcome)
            flow_count = matrix[crisis_idx][outcome_idx]

            if flow_count > 0:
                x2, y2 = node_positions[outcome]

                # Flow width proportional to count
                width = 0.002 + 0.015 * (flow_count / total_events)

                # Bezier curve for flow
                path = mpatches.FancyBboxPatch((x1+0.1, y1-width/2), 0.55, width,
                                                boxstyle="round,pad=0",
                                                facecolor='#2ecc71' if outcome == 'survived' else '#e74c3c',
                                                alpha=0.3, edgecolor='none')
                ax.add_patch(path)

                # Label the flow
                mid_x = (x1 + x2) / 2
                mid_y = y1
                ax.text(mid_x, mid_y, str(flow_count),
                       ha='center', va='center', fontsize=9, color='white',
                       bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    ax.set_title(f"Crisis Flows: Type → Outcome\nTotal Events: {total_events}",
                fontsize=16, color='white', weight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='black')
    plt.close()
    print(f"  📊 Crisis flows plot saved to: {output_path}")


def plot_development_trajectories(timeseries_data, output_path: str = "development_trajectories.png"):
    """
    Plot Kardashev level development over time for all civilizations.

    Args:
        timeseries_data: Timeseries data from export
        output_path: Where to save the plot
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), facecolor='black')

    for ax in [ax1, ax2]:
        ax.set_facecolor('black')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.tick_params(colors='white')

    civilizations = timeseries_data['civilizations']

    if not civilizations:
        ax1.text(0.5, 0.5, "No trajectory data available",
                ha='center', va='center', fontsize=20, color='white')
        ax1.axis('off')
        ax2.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, facecolor='black')
        plt.close()
        return

    colors = plt.cm.tab10(np.linspace(0, 1, len(civilizations)))

    # Plot 1: Kardashev levels
    for i, civ in enumerate(civilizations):
        times = civ['times']
        kardashev = civ['kardashev_levels']
        civ_id = civ['id']

        ax1.plot(times, kardashev, color=colors[i], linewidth=2,
                label=f"Civ{civ_id}", alpha=0.8)
        ax1.scatter(times, kardashev, color=colors[i], s=20, alpha=0.6, zorder=5)

    ax1.axhline(y=1.0, color='yellow', linestyle='--', alpha=0.3, linewidth=1)
    ax1.axhline(y=2.0, color='orange', linestyle='--', alpha=0.3, linewidth=1)
    ax1.text(ax1.get_xlim()[1]*0.98, 1.0, 'K=1.0 (Planetary)',
            ha='right', va='bottom', fontsize=9, color='yellow', alpha=0.7)
    ax1.text(ax1.get_xlim()[1]*0.98, 2.0, 'K=2.0 (Stellar)',
            ha='right', va='bottom', fontsize=9, color='orange', alpha=0.7)

    ax1.set_xlabel("Time (Myr)", fontsize=12, color='white')
    ax1.set_ylabel("Kardashev Level", fontsize=12, color='white')
    ax1.set_title("Technological Development Trajectories", fontsize=14, color='white', weight='bold')
    ax1.legend(loc='upper left', framealpha=0.8, facecolor='black', edgecolor='white', labelcolor='white')
    ax1.grid(True, alpha=0.2, color='white')

    # Plot 2: Maturity levels
    for i, civ in enumerate(civilizations):
        times = civ['times']
        maturity = civ['maturity_levels']
        civ_id = civ['id']

        ax2.plot(times, maturity, color=colors[i], linewidth=2,
                label=f"Civ{civ_id}", alpha=0.8)
        ax2.scatter(times, maturity, color=colors[i], s=20, alpha=0.6, zorder=5)

    ax2.set_xlabel("Time (Myr)", fontsize=12, color='white')
    ax2.set_ylabel("Social Maturity", fontsize=12, color='white')
    ax2.set_title("Social Maturity Evolution", fontsize=14, color='white', weight='bold')
    ax2.legend(loc='upper left', framealpha=0.8, facecolor='black', edgecolor='white', labelcolor='white')
    ax2.grid(True, alpha=0.2, color='white')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='black')
    plt.close()
    print(f"  📈 Development trajectories plot saved to: {output_path}")


def plot_cooperation_network(network_data, output_path: str = "cooperation_network.png"):
    """
    Plot cooperation network as a directed graph.

    Args:
        network_data: Network data from export
        output_path: Where to save the plot
    """
    fig, ax = plt.subplots(figsize=(12, 12), facecolor='black')
    ax.set_facecolor('black')

    nodes = network_data['nodes']
    edges = network_data['edges']

    if not nodes:
        ax.text(0.5, 0.5, "No cooperation data available",
               ha='center', va='center', fontsize=20, color='white')
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, facecolor='black')
        plt.close()
        return

    # Arrange nodes in a circle
    n = len(nodes)
    angles = np.linspace(0, 2*np.pi, n, endpoint=False)
    radius = 0.35

    node_positions = {}
    for i, node in enumerate(nodes):
        x = 0.5 + radius * np.cos(angles[i])
        y = 0.5 + radius * np.sin(angles[i])
        node_positions[node['id']] = (x, y)

    # Draw edges (cooperation links)
    for edge in edges:
        source_id = edge['source']
        target_id = edge['target']
        weight = edge['weight']

        x1, y1 = node_positions[source_id]
        x2, y2 = node_positions[target_id]

        # Arrow from source to target
        dx = x2 - x1
        dy = y2 - y1

        # Width based on effectiveness
        linewidth = 0.5 + 3 * weight

        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', lw=linewidth,
                                  color='cyan', alpha=0.3))

    # Draw nodes
    for node in nodes:
        node_id = node['id']
        x, y = node_positions[node_id]

        aid_given = node['aid_given']
        aid_received = node['aid_received']

        # Size based on total cooperation
        total_coop = aid_given + aid_received
        size = 800 + 100 * total_coop

        # Color based on balance
        if aid_given > aid_received * 1.5:
            color = '#2ecc71'  # Green for givers
        elif aid_received > aid_given * 1.5:
            color = '#e74c3c'  # Red for receivers
        else:
            color = '#f39c12'  # Orange for balanced

        ax.scatter(x, y, s=size, c=color, alpha=0.8, edgecolors='white', linewidths=3, zorder=10)

        # Label
        ax.text(x, y, f"Civ{node_id}\nG:{aid_given} R:{aid_received}",
               ha='center', va='center', fontsize=10, color='white', weight='bold', zorder=11)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    ax.set_title(f"Cooperation Network\nTotal Cooperations: {network_data['total_cooperations']}",
                fontsize=16, color='white', weight='bold', pad=20)

    # Legend
    legend_elements = [
        mpatches.Patch(color='#2ecc71', label='Net Giver'),
        mpatches.Patch(color='#f39c12', label='Balanced'),
        mpatches.Patch(color='#e74c3c', label='Net Receiver')
    ]
    ax.legend(handles=legend_elements, loc='upper right', framealpha=0.9,
             facecolor='black', edgecolor='white', labelcolor='white', fontsize=11)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='black')
    plt.close()
    print(f"  🤝 Cooperation network plot saved to: {output_path}")


def plot_summary_dashboard(summary_stats, metadata, output_path: str = "summary_dashboard.png"):
    """
    Create a dashboard with key summary statistics.

    Args:
        summary_stats: Summary statistics from export
        metadata: Simulation metadata
        output_path: Where to save the plot
    """
    fig = plt.figure(figsize=(16, 10), facecolor='black')
    gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)

    # Title
    fig.suptitle(f"Simulation Summary Dashboard\n{metadata.get('num_civilizations', 0)} Civilizations, {metadata.get('duration_myr', 0):.0f} Myr",
                fontsize=18, color='white', weight='bold', y=0.98)

    # Crisis survival rate (large)
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.set_facecolor('black')

    survival_rate = summary_stats.get('survival_rate', 0.0)
    survived = summary_stats.get('crises_survived', 0)
    failed = summary_stats.get('crises_failed', 0)

    colors_bar = ['#2ecc71', '#e74c3c']
    values = [survived, failed]
    labels = [f'Survived\n{survived}', f'Failed\n{failed}']

    bars = ax1.bar(labels, values, color=colors_bar, edgecolor='white', linewidth=2)
    ax1.set_ylabel("Count", fontsize=12, color='white')
    ax1.set_title(f"Crisis Outcomes (Survival Rate: {survival_rate:.1%})",
                 fontsize=14, color='white', weight='bold')
    ax1.tick_params(colors='white')
    for spine in ax1.spines.values():
        spine.set_color('white')
    ax1.grid(True, alpha=0.2, color='white', axis='y')

    # Crises by type
    ax2 = fig.add_subplot(gs[1, :2])
    ax2.set_facecolor('black')

    crisis_types = summary_stats.get('crises_by_type', {})
    if crisis_types:
        types = list(crisis_types.keys())
        counts = list(crisis_types.values())

        bars = ax2.barh(types, counts, color='#3498db', edgecolor='white', linewidth=2)
        ax2.set_xlabel("Count", fontsize=12, color='white')
        ax2.set_title("Crises by Type", fontsize=14, color='white', weight='bold')
        ax2.tick_params(colors='white')
        for spine in ax2.spines.values():
            spine.set_color('white')
        ax2.grid(True, alpha=0.2, color='white', axis='x')

    # Development paths
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor('black')

    dev_paths = summary_stats.get('development_paths', {})
    if dev_paths:
        paths = list(dev_paths.keys())
        counts = list(dev_paths.values())
        colors_pie = ['#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']

        wedges, texts, autotexts = ax3.pie(counts, labels=paths, autopct='%1.0f%%',
                                            colors=colors_pie, startangle=90,
                                            textprops={'color': 'white', 'weight': 'bold'})
        ax3.set_title("Development Paths", fontsize=12, color='white', weight='bold')

    # Cooperation types
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.set_facecolor('black')

    coop_types = summary_stats.get('cooperations_by_type', {})
    if coop_types:
        types = list(coop_types.keys())
        counts = list(coop_types.values())
        colors_pie = ['#3498db', '#2ecc71', '#f39c12', '#9b59b6']

        wedges, texts, autotexts = ax4.pie(counts, labels=[t.replace('_', ' ').title() for t in types],
                                            autopct='%1.0f%%', colors=colors_pie, startangle=90,
                                            textprops={'color': 'white', 'weight': 'bold', 'fontsize': 9})
        ax4.set_title("Cooperation Types", fontsize=12, color='white', weight='bold')

    # Key metrics table
    ax5 = fig.add_subplot(gs[2, :])
    ax5.set_facecolor('black')
    ax5.axis('off')

    metrics_data = [
        ['Total Crises', str(summary_stats.get('total_crises', 0))],
        ['Survival Rate', f"{summary_stats.get('survival_rate', 0):.1%}"],
        ['Avg Development Velocity', f"{summary_stats.get('avg_development_velocity', 0):.4f} K/Myr"],
        ['Total Cooperations', str(summary_stats.get('total_cooperations', 0))],
        ['Avg Cooperation Effectiveness', f"{summary_stats.get('avg_cooperation_effectiveness', 0):.2f}"],
    ]

    table = ax5.table(cellText=metrics_data, cellLoc='left',
                     colWidths=[0.4, 0.2], loc='center',
                     bbox=[0.2, 0.2, 0.6, 0.6])

    table.auto_set_font_size(False)
    table.set_fontsize(12)

    for (i, j), cell in table.get_celld().items():
        cell.set_facecolor('#2c3e50' if i % 2 == 0 else '#34495e')
        cell.set_edgecolor('white')
        cell.set_text_props(color='white', weight='bold')
        cell.set_linewidth(2)

    ax5.set_title("Key Metrics", fontsize=14, color='white', weight='bold', pad=20)

    plt.savefig(output_path, dpi=150, facecolor='black')
    plt.close()
    print(f"  📊 Summary dashboard saved to: {output_path}")


def main():
    """Generate all visualization plots."""
    print("\n" + "="*70)
    print("GENERATING VISUALIZATION PLOTS")
    print("="*70 + "\n")

    # Load data
    print("Loading simulation data...")
    data = load_simulation_data()

    # Create plots
    print("\nGenerating plots...\n")
    plot_crisis_flows(data['chord_data'])
    plot_development_trajectories(data['timeseries_data'])
    plot_cooperation_network(data['network_data'])
    plot_summary_dashboard(data['summary_stats'], data['metadata'])

    print("\n" + "="*70)
    print("✅ All visualization plots generated successfully!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
