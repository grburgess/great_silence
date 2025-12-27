"""3D visualization tools for galaxy and civilizations."""

import numpy as np
from typing import Optional, List
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


class GalaxyVisualizer:
    """
    Visualize galaxy structure and civilization distribution.
    """

    def __init__(self, figsize: tuple = (12, 10)):
        """
        Initialize visualizer.

        Args:
            figsize: Figure size for plots
        """
        self.figsize = figsize

    def plot_galaxy_structure(
        self,
        stellar_positions: np.ndarray,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot 3D galaxy structure.

        Args:
            stellar_positions: Array of shape (N, 3) with positions in kpc
            save_path: Optional path to save figure
        """
        fig = plt.figure(figsize=self.figsize)

        # Top view
        ax1 = fig.add_subplot(2, 2, 1)
        ax1.scatter(
            stellar_positions[:, 0],
            stellar_positions[:, 1],
            s=0.1,
            alpha=0.3,
            color='white'
        )
        ax1.set_xlabel('X (kpc)')
        ax1.set_ylabel('Y (kpc)')
        ax1.set_title('Top View')
        ax1.set_aspect('equal')
        ax1.set_facecolor('black')

        # Side view
        ax2 = fig.add_subplot(2, 2, 2)
        ax2.scatter(
            stellar_positions[:, 0],
            stellar_positions[:, 2],
            s=0.1,
            alpha=0.3,
            color='white'
        )
        ax2.set_xlabel('X (kpc)')
        ax2.set_ylabel('Z (kpc)')
        ax2.set_title('Side View')
        ax2.set_aspect('equal')
        ax2.set_facecolor('black')

        # 3D view
        ax3 = fig.add_subplot(2, 2, 3, projection='3d')
        ax3.scatter(
            stellar_positions[:, 0],
            stellar_positions[:, 1],
            stellar_positions[:, 2],
            s=0.1,
            alpha=0.2,
            color='white'
        )
        ax3.set_xlabel('X (kpc)')
        ax3.set_ylabel('Y (kpc)')
        ax3.set_zlabel('Z (kpc)')
        ax3.set_title('3D View')
        ax3.set_facecolor('black')

        # Density histogram
        ax4 = fig.add_subplot(2, 2, 4)
        r = np.sqrt(stellar_positions[:, 0]**2 + stellar_positions[:, 1]**2)
        ax4.hist(r, bins=50, color='cyan', alpha=0.7)
        ax4.set_xlabel('Radius (kpc)')
        ax4.set_ylabel('Number of Stars')
        ax4.set_title('Radial Distribution')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, facecolor='black')
        else:
            plt.show()

        plt.close()

    def plot_civilization_distribution(
        self,
        stellar_positions: np.ndarray,
        civilization_indices: List[int],
        colonized_indices: Optional[List[int]] = None,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot civilizations on galaxy map.

        Args:
            stellar_positions: All stellar positions
            civilization_indices: Indices of civilization home stars
            colonized_indices: Optional indices of colonized stars
            save_path: Optional path to save figure
        """
        fig = plt.figure(figsize=self.figsize)

        # Top view with civilizations
        ax = fig.add_subplot(1, 1, 1)

        # Background stars
        ax.scatter(
            stellar_positions[:, 0],
            stellar_positions[:, 1],
            s=0.1,
            alpha=0.1,
            color='gray'
        )

        # Civilizations
        if len(civilization_indices) > 0:
            civ_pos = stellar_positions[civilization_indices]
            ax.scatter(
                civ_pos[:, 0],
                civ_pos[:, 1],
                s=50,
                alpha=0.8,
                color='red',
                marker='*',
                label='Civilizations'
            )

        # Colonized systems
        if colonized_indices is not None and len(colonized_indices) > 0:
            col_pos = stellar_positions[colonized_indices]
            ax.scatter(
                col_pos[:, 0],
                col_pos[:, 1],
                s=10,
                alpha=0.6,
                color='cyan',
                label='Colonies'
            )

        ax.set_xlabel('X (kpc)')
        ax.set_ylabel('Y (kpc)')
        ax.set_title('Civilization Distribution')
        ax.set_aspect('equal')
        ax.set_facecolor('black')
        ax.legend()

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, facecolor='black')
        else:
            plt.show()

        plt.close()

    def plot_density_map(
        self,
        stellar_positions: np.ndarray,
        bins: int = 100,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot 2D density map of galaxy.

        Args:
            stellar_positions: Stellar positions
            bins: Number of bins for 2D histogram
            save_path: Optional path to save figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        h, xedges, yedges = np.histogram2d(
            stellar_positions[:, 0],
            stellar_positions[:, 1],
            bins=bins
        )

        extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]

        im = ax.imshow(
            h.T,
            extent=extent,
            origin='lower',
            cmap='hot',
            aspect='auto'
        )

        ax.set_xlabel('X (kpc)')
        ax.set_ylabel('Y (kpc)')
        ax.set_title('Stellar Density Map')

        plt.colorbar(im, ax=ax, label='Number of Stars')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.show()

        plt.close()

    def plot_civilization_evolution(
        self,
        stellar_positions: np.ndarray,
        civilizations: List,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot civilizations color-coded by Kardashev scale and status.

        Args:
            stellar_positions: All stellar positions
            civilizations: List of CivilizationState objects
            save_path: Optional path to save figure
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # Left panel: Active civilizations by Kardashev scale
        ax1.scatter(
            stellar_positions[:, 0],
            stellar_positions[:, 1],
            s=0.1,
            alpha=0.05,
            color='gray'
        )

        active_civs = [c for c in civilizations if c.is_active]
        if active_civs:
            active_indices = [c.parent_star_idx for c in active_civs]
            active_kardashev = [c.kardashev_scale for c in active_civs]
            active_pos = stellar_positions[active_indices]

            scatter = ax1.scatter(
                active_pos[:, 0],
                active_pos[:, 1],
                c=active_kardashev,
                s=100,
                alpha=0.8,
                cmap='plasma',
                vmin=0.5,
                vmax=3.0,
                marker='*',
                edgecolors='white',
                linewidths=0.5
            )
            plt.colorbar(scatter, ax=ax1, label='Kardashev Scale')

        ax1.set_xlabel('X (kpc)')
        ax1.set_ylabel('Y (kpc)')
        ax1.set_title(f'Active Civilizations ({len(active_civs)})')
        ax1.set_aspect('equal')
        ax1.set_facecolor('black')

        # Right panel: All civilizations (active and extinct)
        ax2.scatter(
            stellar_positions[:, 0],
            stellar_positions[:, 1],
            s=0.1,
            alpha=0.05,
            color='gray'
        )

        extinct_civs = [c for c in civilizations if not c.is_active]
        if extinct_civs:
            extinct_indices = [c.parent_star_idx for c in extinct_civs]
            extinct_pos = stellar_positions[extinct_indices]
            ax2.scatter(
                extinct_pos[:, 0],
                extinct_pos[:, 1],
                s=20,
                alpha=0.4,
                color='red',
                marker='x',
                label=f'Extinct ({len(extinct_civs)})'
            )

        if active_civs:
            ax2.scatter(
                active_pos[:, 0],
                active_pos[:, 1],
                s=50,
                alpha=0.8,
                color='cyan',
                marker='*',
                label=f'Active ({len(active_civs)})'
            )

        ax2.set_xlabel('X (kpc)')
        ax2.set_ylabel('Y (kpc)')
        ax2.set_title(f'All Civilizations ({len(civilizations)} total)')
        ax2.set_aspect('equal')
        ax2.set_facecolor('black')
        ax2.legend()

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, facecolor='black')
        else:
            plt.show()

        plt.close()

    def plot_bulge_and_disk(
        self,
        stellar_positions: np.ndarray,
        component_type: np.ndarray,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot galaxy showing bulge and disk components separately.

        Args:
            stellar_positions: Array of shape (N, 3) with positions in kpc
            component_type: Array of component types (0=bulge, 1=disk)
            save_path: Optional path to save figure
        """
        fig = plt.figure(figsize=self.figsize)

        # Separate bulge and disk
        bulge_mask = component_type == 0
        disk_mask = component_type == 1

        bulge_pos = stellar_positions[bulge_mask]
        disk_pos = stellar_positions[disk_mask]

        # Top view
        ax1 = fig.add_subplot(2, 2, 1)
        ax1.scatter(
            disk_pos[:, 0],
            disk_pos[:, 1],
            s=0.1,
            alpha=0.2,
            color='lightblue',
            label=f'Disk ({len(disk_pos):,})'
        )
        ax1.scatter(
            bulge_pos[:, 0],
            bulge_pos[:, 1],
            s=0.3,
            alpha=0.5,
            color='orange',
            label=f'Bulge ({len(bulge_pos):,})'
        )
        ax1.set_xlabel('X (kpc)')
        ax1.set_ylabel('Y (kpc)')
        ax1.set_title('Top View: Bulge + Disk')
        ax1.set_aspect('equal')
        ax1.set_facecolor('black')
        ax1.legend(loc='upper right')

        # Side view
        ax2 = fig.add_subplot(2, 2, 2)
        ax2.scatter(
            disk_pos[:, 0],
            disk_pos[:, 2],
            s=0.1,
            alpha=0.2,
            color='lightblue'
        )
        ax2.scatter(
            bulge_pos[:, 0],
            bulge_pos[:, 2],
            s=0.3,
            alpha=0.5,
            color='orange'
        )
        ax2.set_xlabel('X (kpc)')
        ax2.set_ylabel('Z (kpc)')
        ax2.set_title('Side View: Bulge + Disk')
        ax2.set_aspect('equal')
        ax2.set_facecolor('black')

        # 3D view
        ax3 = fig.add_subplot(2, 2, 3, projection='3d')
        ax3.scatter(
            disk_pos[:, 0],
            disk_pos[:, 1],
            disk_pos[:, 2],
            s=0.1,
            alpha=0.1,
            color='lightblue'
        )
        ax3.scatter(
            bulge_pos[:, 0],
            bulge_pos[:, 1],
            bulge_pos[:, 2],
            s=0.5,
            alpha=0.4,
            color='orange'
        )
        ax3.set_xlabel('X (kpc)')
        ax3.set_ylabel('Y (kpc)')
        ax3.set_zlabel('Z (kpc)')
        ax3.set_title('3D View: Bulge + Disk')
        ax3.set_facecolor('black')

        # Radial distribution by component
        ax4 = fig.add_subplot(2, 2, 4)
        r_bulge = np.sqrt(bulge_pos[:, 0]**2 + bulge_pos[:, 1]**2)
        r_disk = np.sqrt(disk_pos[:, 0]**2 + disk_pos[:, 1]**2)

        ax4.hist(r_disk, bins=50, color='lightblue', alpha=0.6, label='Disk')
        ax4.hist(r_bulge, bins=50, color='orange', alpha=0.7, label='Bulge')
        ax4.set_xlabel('Radius (kpc)')
        ax4.set_ylabel('Number of Stars')
        ax4.set_title('Radial Distribution by Component')
        ax4.set_yscale('log')
        ax4.legend()

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, facecolor='black')
        else:
            plt.show()

        plt.close()

    def plot_age_gradient(
        self,
        stellar_positions: np.ndarray,
        stellar_ages: np.ndarray,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot stellar age gradient (inside-out formation).

        Args:
            stellar_positions: Array of shape (N, 3) with positions in kpc
            stellar_ages: Array of stellar ages in Gyr
            save_path: Optional path to save figure
        """
        fig = plt.figure(figsize=(14, 10))

        # Calculate galactocentric radius
        r = np.sqrt(stellar_positions[:, 0]**2 + stellar_positions[:, 1]**2)

        # Top view with age color-coding
        ax1 = fig.add_subplot(2, 2, 1)
        scatter = ax1.scatter(
            stellar_positions[:, 0],
            stellar_positions[:, 1],
            c=stellar_ages,
            s=0.5,
            alpha=0.3,
            cmap='coolwarm_r',
            vmin=0,
            vmax=13
        )
        ax1.set_xlabel('X (kpc)')
        ax1.set_ylabel('Y (kpc)')
        ax1.set_title('Age Distribution (Top View)')
        ax1.set_aspect('equal')
        ax1.set_facecolor('black')
        plt.colorbar(scatter, ax=ax1, label='Age (Gyr)')

        # Side view with age color-coding
        ax2 = fig.add_subplot(2, 2, 2)
        scatter2 = ax2.scatter(
            stellar_positions[:, 0],
            stellar_positions[:, 2],
            c=stellar_ages,
            s=0.5,
            alpha=0.3,
            cmap='coolwarm_r',
            vmin=0,
            vmax=13
        )
        ax2.set_xlabel('X (kpc)')
        ax2.set_ylabel('Z (kpc)')
        ax2.set_title('Age Distribution (Side View)')
        ax2.set_aspect('equal')
        ax2.set_facecolor('black')
        plt.colorbar(scatter2, ax=ax2, label='Age (Gyr)')

        # Age vs radius scatter plot
        ax3 = fig.add_subplot(2, 2, 3)
        # Sample to avoid overplotting
        sample_size = min(10000, len(r))
        sample_idx = np.random.choice(len(r), sample_size, replace=False)

        ax3.scatter(
            r[sample_idx],
            stellar_ages[sample_idx],
            s=1,
            alpha=0.1,
            color='cyan'
        )

        # Plot binned mean and std
        bins = np.linspace(0, r.max(), 30)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        bin_means = []
        bin_stds = []

        for i in range(len(bins) - 1):
            mask = (r >= bins[i]) & (r < bins[i+1])
            if np.any(mask):
                bin_means.append(np.mean(stellar_ages[mask]))
                bin_stds.append(np.std(stellar_ages[mask]))
            else:
                bin_means.append(np.nan)
                bin_stds.append(np.nan)

        bin_means = np.array(bin_means)
        bin_stds = np.array(bin_stds)

        ax3.plot(bin_centers, bin_means, 'r-', linewidth=2, label='Mean age')
        ax3.fill_between(
            bin_centers,
            bin_means - bin_stds,
            bin_means + bin_stds,
            color='red',
            alpha=0.3,
            label='±1σ'
        )

        ax3.set_xlabel('Galactocentric Radius (kpc)')
        ax3.set_ylabel('Stellar Age (Gyr)')
        ax3.set_title('Age Gradient (Inside-Out Formation)')
        ax3.grid(True, alpha=0.3)
        ax3.legend()

        # Age histogram by radial bin
        ax4 = fig.add_subplot(2, 2, 4)

        # Define radial bins
        inner_mask = r < 3
        middle_mask = (r >= 3) & (r < 10)
        outer_mask = r >= 10

        ax4.hist(
            stellar_ages[inner_mask],
            bins=30,
            alpha=0.6,
            color='red',
            label=f'Inner (r < 3 kpc, n={np.sum(inner_mask):,})',
            density=True
        )
        ax4.hist(
            stellar_ages[middle_mask],
            bins=30,
            alpha=0.6,
            color='orange',
            label=f'Middle (3-10 kpc, n={np.sum(middle_mask):,})',
            density=True
        )
        ax4.hist(
            stellar_ages[outer_mask],
            bins=30,
            alpha=0.6,
            color='cyan',
            label=f'Outer (r > 10 kpc, n={np.sum(outer_mask):,})',
            density=True
        )

        ax4.set_xlabel('Stellar Age (Gyr)')
        ax4.set_ylabel('Probability Density')
        ax4.set_title('Age Distribution by Galactic Region')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, facecolor='black')
        else:
            plt.show()

        plt.close()

    def plot_metallicity_gradient(
        self,
        stellar_positions: np.ndarray,
        metallicities: np.ndarray,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot stellar metallicity gradient.

        Args:
            stellar_positions: Array of shape (N, 3) with positions in kpc
            metallicities: Array of [Fe/H] metallicities
            save_path: Optional path to save figure
        """
        fig = plt.figure(figsize=(14, 10))

        # Calculate galactocentric radius
        r = np.sqrt(stellar_positions[:, 0]**2 + stellar_positions[:, 1]**2)

        # Top view with metallicity color-coding
        ax1 = fig.add_subplot(2, 2, 1)
        scatter = ax1.scatter(
            stellar_positions[:, 0],
            stellar_positions[:, 1],
            c=metallicities,
            s=0.5,
            alpha=0.3,
            cmap='RdYlBu_r',
            vmin=-1.0,
            vmax=0.5
        )
        ax1.set_xlabel('X (kpc)')
        ax1.set_ylabel('Y (kpc)')
        ax1.set_title('Metallicity Distribution (Top View)')
        ax1.set_aspect('equal')
        ax1.set_facecolor('black')
        cbar = plt.colorbar(scatter, ax=ax1, label='[Fe/H]')

        # Add reference lines
        cbar.ax.axhline(0.0, color='white', linestyle='--', linewidth=1, alpha=0.5)
        cbar.ax.text(0.5, 0.0, ' Solar', color='white', va='center')

        # Side view with metallicity color-coding
        ax2 = fig.add_subplot(2, 2, 2)
        scatter2 = ax2.scatter(
            stellar_positions[:, 0],
            stellar_positions[:, 2],
            c=metallicities,
            s=0.5,
            alpha=0.3,
            cmap='RdYlBu_r',
            vmin=-1.0,
            vmax=0.5
        )
        ax2.set_xlabel('X (kpc)')
        ax2.set_ylabel('Z (kpc)')
        ax2.set_title('Metallicity Distribution (Side View)')
        ax2.set_aspect('equal')
        ax2.set_facecolor('black')
        plt.colorbar(scatter2, ax=ax2, label='[Fe/H]')

        # Metallicity vs radius scatter plot
        ax3 = fig.add_subplot(2, 2, 3)
        # Sample to avoid overplotting
        sample_size = min(10000, len(r))
        sample_idx = np.random.choice(len(r), sample_size, replace=False)

        ax3.scatter(
            r[sample_idx],
            metallicities[sample_idx],
            s=1,
            alpha=0.1,
            color='cyan'
        )

        # Plot binned mean and std
        bins = np.linspace(0, r.max(), 30)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        bin_means = []
        bin_stds = []

        for i in range(len(bins) - 1):
            mask = (r >= bins[i]) & (r < bins[i+1])
            if np.any(mask):
                bin_means.append(np.mean(metallicities[mask]))
                bin_stds.append(np.std(metallicities[mask]))
            else:
                bin_means.append(np.nan)
                bin_stds.append(np.nan)

        bin_means = np.array(bin_means)
        bin_stds = np.array(bin_stds)

        ax3.plot(bin_centers, bin_means, 'r-', linewidth=2, label='Mean [Fe/H]')
        ax3.fill_between(
            bin_centers,
            bin_means - bin_stds,
            bin_means + bin_stds,
            color='red',
            alpha=0.3,
            label='±1σ'
        )

        ax3.axhline(0.0, color='white', linestyle='--', linewidth=1, alpha=0.5, label='Solar')
        ax3.set_xlabel('Galactocentric Radius (kpc)')
        ax3.set_ylabel('[Fe/H]')
        ax3.set_title('Metallicity Gradient')
        ax3.grid(True, alpha=0.3)
        ax3.legend()

        # Metallicity histogram by radial bin
        ax4 = fig.add_subplot(2, 2, 4)

        # Define radial bins
        inner_mask = r < 3
        middle_mask = (r >= 3) & (r < 10)
        outer_mask = r >= 10

        ax4.hist(
            metallicities[inner_mask],
            bins=30,
            alpha=0.6,
            color='red',
            label=f'Inner (r < 3 kpc)',
            density=True
        )
        ax4.hist(
            metallicities[middle_mask],
            bins=30,
            alpha=0.6,
            color='orange',
            label=f'Middle (3-10 kpc)',
            density=True
        )
        ax4.hist(
            metallicities[outer_mask],
            bins=30,
            alpha=0.6,
            color='cyan',
            label=f'Outer (r > 10 kpc)',
            density=True
        )

        ax4.axvline(0.0, color='white', linestyle='--', linewidth=1, alpha=0.5)
        ax4.text(0.0, ax4.get_ylim()[1] * 0.9, ' Solar', color='white', ha='left')

        ax4.set_xlabel('[Fe/H]')
        ax4.set_ylabel('Probability Density')
        ax4.set_title('Metallicity Distribution by Galactic Region')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, facecolor='black')
        else:
            plt.show()

        plt.close()

    def plot_hazard_zones(
        self,
        stellar_positions: np.ndarray,
        stellar_masses: np.ndarray,
        stellar_ages: np.ndarray,
        component_types: np.ndarray,
        metallicities: np.ndarray,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot galactic hazard zones (supernova and GRB risk).

        Shows regions of high astrophysical hazard based on:
        - Local stellar density (more stars → more supernovae)
        - Component type (bulge → higher evolved fraction)
        - Metallicity (metal-poor → more GRBs)

        Args:
            stellar_positions: Array of shape (N, 3) with positions in kpc
            stellar_masses: Stellar masses in solar masses
            stellar_ages: Stellar ages in Gyr
            component_types: Component types (0=bulge, 1=disk)
            metallicities: Stellar metallicities [Fe/H]
            save_path: Optional path to save figure
        """
        from scipy.spatial import cKDTree
        from matplotlib.patches import Patch

        fig = plt.figure(figsize=(16, 12))

        # Build spatial index for density calculation
        tree = cKDTree(stellar_positions)

        # Calculate local density at grid points
        print("  Calculating hazard zones across galaxy...")
        x_grid = np.linspace(-15, 15, 80)
        y_grid = np.linspace(-15, 15, 80)
        X, Y = np.meshgrid(x_grid, y_grid)

        density_grid = np.zeros_like(X)
        sn_risk_grid = np.zeros_like(X)
        grb_risk_grid = np.zeros_like(X)

        # Search radius for local density (30 pc sphere)
        search_radius_kpc = 0.03  # 30 pc

        for i in range(len(x_grid)):
            for j in range(len(y_grid)):
                point = np.array([X[j, i], Y[j, i], 0.0])
                indices = tree.query_ball_point(point, search_radius_kpc)

                if len(indices) > 0:
                    volume_pc3 = (4.0/3.0) * np.pi * (search_radius_kpc * 1000)**3
                    density_grid[j, i] = len(indices) / volume_pc3

                    nearby_masses = stellar_masses[indices]
                    nearby_ages = stellar_ages[indices]
                    nearby_components = component_types[indices]
                    nearby_metals = metallicities[indices]

                    # SN risk
                    massive_mask = nearby_masses > 8.0
                    if np.any(massive_mask):
                        t_ms = 10.0 * (nearby_masses[massive_mask])**(-2.5)
                        near_sn = np.sum(nearby_ages[massive_mask] >= 0.9 * t_ms)
                        bulge_frac = np.sum(nearby_components == 0) / len(nearby_components)
                        sn_risk_grid[j, i] = near_sn * (1.0 + bulge_frac) * np.sqrt(density_grid[j, i] / 0.1)

                    # GRB risk
                    very_massive_mask = nearby_masses > 20.0
                    if np.any(very_massive_mask):
                        avg_met = np.mean(nearby_metals[very_massive_mask])
                        grb_modifier = np.power(10.0, -0.8 * avg_met)
                        grb_risk_grid[j, i] = np.sum(very_massive_mask) * grb_modifier

        # Plot
        ax1 = fig.add_subplot(2, 3, 1)
        ax1.contourf(X, Y, np.log10(density_grid + 1e-6), levels=20, cmap='YlOrRd')
        ax1.scatter(stellar_positions[::100, 0], stellar_positions[::100, 1], s=0.1, alpha=0.1, color='black')
        ax1.set_xlabel('X (kpc)')
        ax1.set_ylabel('Y (kpc)')
        ax1.set_title('Stellar Density')
        ax1.set_aspect('equal')

        ax2 = fig.add_subplot(2, 3, 2)
        ax2.contourf(X, Y, np.log10(sn_risk_grid + 1e-6), levels=20, cmap='Reds')
        ax2.scatter(stellar_positions[::100, 0], stellar_positions[::100, 1], s=0.1, alpha=0.1, color='black')
        ax2.set_xlabel('X (kpc)')
        ax2.set_ylabel('Y (kpc)')
        ax2.set_title('Supernova Risk')
        ax2.set_aspect('equal')

        ax3 = fig.add_subplot(2, 3, 3)
        ax3.contourf(X, Y, np.log10(grb_risk_grid + 1e-6), levels=20, cmap='Purples')
        ax3.scatter(stellar_positions[::100, 0], stellar_positions[::100, 1], s=0.1, alpha=0.1, color='black')
        ax3.set_xlabel('X (kpc)')
        ax3.set_ylabel('Y (kpc)')
        ax3.set_title('GRB Risk (Metallicity-Dependent)')
        ax3.set_aspect('equal')

        ax4 = fig.add_subplot(2, 3, 4)
        combined = sn_risk_grid + grb_risk_grid
        ax4.contourf(X, Y, np.log10(combined + 1e-6), levels=20, cmap='RdPu')
        ax4.scatter(stellar_positions[::100, 0], stellar_positions[::100, 1], s=0.1, alpha=0.1, color='black')
        theta = np.linspace(0, 2*np.pi, 100)
        for r in [6, 10]:
            ax4.plot(r * np.cos(theta), r * np.sin(theta), 'g--', linewidth=2, alpha=0.7)
        ax4.text(8, 0, 'GHZ', color='green', fontsize=12, weight='bold', ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        ax4.set_xlabel('X (kpc)')
        ax4.set_ylabel('Y (kpc)')
        ax4.set_title('Combined Risk + Galactic Habitable Zone')
        ax4.set_aspect('equal')

        ax5 = fig.add_subplot(2, 3, 5)
        r_grid = np.sqrt(X**2 + Y**2)
        r_bins = np.linspace(0, 15, 30)
        r_centers = (r_bins[:-1] + r_bins[1:]) / 2
        dens_prof, sn_prof, grb_prof = [], [], []
        for i in range(len(r_bins) - 1):
            mask = (r_grid >= r_bins[i]) & (r_grid < r_bins[i+1])
            if np.any(mask):
                dens_prof.append(np.mean(density_grid[mask]))
                sn_prof.append(np.mean(sn_risk_grid[mask]))
                grb_prof.append(np.mean(grb_risk_grid[mask]))
            else:
                dens_prof.append(0)
                sn_prof.append(0)
                grb_prof.append(0)
        ax5.plot(r_centers, dens_prof, 'b-', linewidth=2, label='Density')
        ax5.plot(r_centers, np.array(sn_prof)*10, 'r-', linewidth=2, label='SN risk (×10)')
        ax5.plot(r_centers, np.array(grb_prof)*10, 'm-', linewidth=2, label='GRB risk (×10)')
        ax5.axvspan(6, 10, alpha=0.2, color='green', label='GHZ')
        ax5.set_xlabel('Radius (kpc)')
        ax5.set_ylabel('Risk')
        ax5.set_title('Radial Hazard Profile')
        ax5.legend()
        ax5.grid(True, alpha=0.3)

        ax6 = fig.add_subplot(2, 3, 6)
        # Handle case where combined risk might be all zeros
        nonzero_combined = combined[combined > 0]
        if len(nonzero_combined) > 0:
            safe_thresh = np.percentile(nonzero_combined, 25)
            haz_thresh = np.percentile(nonzero_combined, 75)
        else:
            safe_thresh = 0.01
            haz_thresh = 0.1
        safety = np.zeros_like(combined)
        safety[combined <= safe_thresh] = 1
        safety[(combined > safe_thresh) & (combined <= haz_thresh)] = 0.5
        safety[combined > haz_thresh] = 0
        ax6.contourf(X, Y, safety, levels=[0, 0.33, 0.66, 1.0], colors=['red', 'orange', 'green'], alpha=0.6)
        ax6.scatter(stellar_positions[::100, 0], stellar_positions[::100, 1], s=0.1, alpha=0.2, color='black')
        legend_elements = [
            Patch(facecolor='green', alpha=0.6, label='Safe Zone'),
            Patch(facecolor='orange', alpha=0.6, label='Moderate Risk'),
            Patch(facecolor='red', alpha=0.6, label='Hazardous Zone')
        ]
        ax6.legend(handles=legend_elements, loc='upper right')
        ax6.set_xlabel('X (kpc)')
        ax6.set_ylabel('Y (kpc)')
        ax6.set_title('Galactic Safety Map')
        ax6.set_aspect('equal')

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, facecolor='white')
            print(f"  Saved: {save_path}")
        else:
            plt.show()
        plt.close()
