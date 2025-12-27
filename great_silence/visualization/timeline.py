"""Timeline visualization and animation tools."""

import numpy as np
from typing import List, Optional
import matplotlib.pyplot as plt
import matplotlib.animation as animation


class TimelineAnimator:
    """
    Create animations showing civilization evolution over time.
    """

    def __init__(self, figsize: tuple = (12, 10)):
        """
        Initialize animator.

        Args:
            figsize: Figure size for animations
        """
        self.figsize = figsize

    def plot_timeline_statistics(
        self,
        times_gyr: np.ndarray,
        n_active: np.ndarray,
        n_total: np.ndarray,
        n_colonized: Optional[np.ndarray] = None,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot civilization statistics over time.

        Args:
            times_gyr: Time points in Gyr
            n_active: Number of active civilizations
            n_total: Total civilizations ever emerged
            n_colonized: Optional number of colonized systems
            save_path: Optional path to save figure
        """
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))

        # Active vs total civilizations
        ax1 = axes[0]
        ax1.plot(times_gyr, n_total, label='Total Emerged', linewidth=2)
        ax1.plot(times_gyr, n_active, label='Active', linewidth=2)
        ax1.fill_between(times_gyr, 0, n_active, alpha=0.3)
        ax1.set_xlabel('Time (Gyr)')
        ax1.set_ylabel('Number of Civilizations')
        ax1.set_title('Civilization Count Over Time')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Colonized systems
        ax2 = axes[1]
        if n_colonized is not None:
            ax2.plot(times_gyr, n_colonized, color='cyan', linewidth=2)
            ax2.fill_between(times_gyr, 0, n_colonized, alpha=0.3, color='cyan')
        ax2.set_xlabel('Time (Gyr)')
        ax2.set_ylabel('Colonized Systems')
        ax2.set_title('Galactic Colonization Progress')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.show()

        plt.close()

    def plot_extinction_causes(
        self,
        causes: dict,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot pie chart of extinction causes.

        Args:
            causes: Dictionary mapping cause names to counts
            save_path: Optional path to save figure
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        labels = list(causes.keys())
        sizes = list(causes.values())
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']

        ax.pie(
            sizes,
            labels=labels,
            colors=colors[:len(labels)],
            autopct='%1.1f%%',
            startangle=90
        )
        ax.set_title('Causes of Civilization Extinction')

        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.show()

        plt.close()

    def plot_kardashev_progression(
        self,
        civilizations: List,
        simulation_duration_myr: float,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot histogram of Kardashev scales and technological progression.

        Args:
            civilizations: List of CivilizationState objects
            simulation_duration_myr: Total simulation duration in Myr
            save_path: Optional path to save figure
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Left: Histogram of final Kardashev scales
        all_scales = [c.kardashev_scale for c in civilizations]
        active_scales = [c.kardashev_scale for c in civilizations if c.is_active]

        ax1.hist(all_scales, bins=20, alpha=0.5, label='All civilizations', color='blue')
        if active_scales:
            ax1.hist(active_scales, bins=20, alpha=0.7, label='Active civilizations', color='green')
        ax1.set_xlabel('Kardashev Scale')
        ax1.set_ylabel('Number of Civilizations')
        ax1.set_title('Distribution of Kardashev Scales')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Right: Average Kardashev scale vs lifetime
        lifetimes = []
        scales = []
        for civ in civilizations:
            if civ.death_time_myr is not None:
                lifetime_myr = civ.death_time_myr - civ.birth_time_myr
            else:
                lifetime_myr = simulation_duration_myr - civ.birth_time_myr
            lifetimes.append(lifetime_myr)
            scales.append(civ.kardashev_scale)

        ax2.scatter(lifetimes, scales, alpha=0.5, s=20)
        ax2.set_xlabel('Civilization Lifetime (Myr)')
        ax2.set_ylabel('Final Kardashev Scale')
        ax2.set_title('Technological Level vs Lifetime')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.show()

        plt.close()

    def create_animation(
        self,
        snapshots: List,
        output_path: str,
        fps: int = 10
    ) -> None:
        """
        Create animation of simulation progression.

        Args:
            snapshots: List of SimulationSnapshot objects
            output_path: Path to save animation (e.g., 'output.mp4')
            fps: Frames per second
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        def update(frame_idx):
            """Update function for animation."""
            ax.clear()
            snapshot = snapshots[frame_idx]

            # Plot background stars (sample for performance)
            if len(snapshot.stellar_positions) > 10000:
                indices = np.random.choice(
                    len(snapshot.stellar_positions),
                    10000,
                    replace=False
                )
                positions = snapshot.stellar_positions[indices]
            else:
                positions = snapshot.stellar_positions

            ax.scatter(
                positions[:, 0],
                positions[:, 1],
                s=0.1,
                alpha=0.1,
                color='gray'
            )

            # Plot active civilizations
            active_civs = [c for c in snapshot.civilization_states if c.is_active]
            if active_civs:
                civ_indices = [c.parent_star_idx for c in active_civs]
                civ_pos = snapshot.stellar_positions[civ_indices]
                ax.scatter(
                    civ_pos[:, 0],
                    civ_pos[:, 1],
                    s=50,
                    color='red',
                    marker='*',
                    alpha=0.8
                )

            ax.set_xlabel('X (kpc)')
            ax.set_ylabel('Y (kpc)')
            ax.set_title(
                f'Time: {snapshot.time_myr / 1000:.2f} Gyr | '
                f'Active Civs: {snapshot.active_civilizations}'
            )
            ax.set_aspect('equal')
            ax.set_facecolor('black')

        anim = animation.FuncAnimation(
            fig,
            update,
            frames=len(snapshots),
            interval=1000 // fps
        )

        # Save animation
        Writer = animation.writers['ffmpeg']
        writer = Writer(fps=fps, metadata=dict(artist='GalaticBot'), bitrate=1800)
        anim.save(output_path, writer=writer)

        plt.close()
