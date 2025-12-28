"""
Realistic civilization emergence simulation.

This simulation demonstrates emergence over time based on:
- Exoplanet survey data (Kepler, TESS 2024-2025)
- Stellar habitability constraints
- Age-dependent emergence probability
- Metallicity effects on planet occurrence

Unlike examples that seed a fixed number of civilizations at t=0,
this simulation lets civilizations emerge naturally when stars reach
the right age and conditions.
"""

import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from great_silence.galaxy.structure import GalaxyModel
from great_silence.galaxy.star_formation import InitialMassFunction, StarFormationHistory
from great_silence.astrophysics.supernovae import SupernovaModel
from great_silence.astrophysics.grb import GammaRayBurstModel
from great_silence.civilization.emergence import CivilizationEmergence
from great_silence.config.parameters import (
    GalaxyParameters,
    AstrophysicsParameters,
    CivilizationParameters
)


@dataclass
class CivilizationState:
    """Simplified civilization state for this simulation."""
    id: int
    parent_star_idx: int
    position: np.ndarray  # kpc
    birth_time_myr: float
    age_myr: float
    kardashev_level: float
    social_maturity: float
    alive: bool
    cause_of_death: Optional[str] = None
    death_time_myr: Optional[float] = None


class RealisticEmergenceSimulation:
    """
    Simulation with realistic civilization emergence over time.

    Key features:
    - No fixed number of civilizations at t=0
    - Emergence based on stellar age, mass, and metallicity
    - Civilizations emerge gradually from 1-10 Gyr
    - Peak emergence around 5 Gyr (optimal stellar age)
    - Spatial clustering in metal-rich regions
    """

    def __init__(
        self,
        num_stars: int = 100000,
        seed: Optional[int] = None
    ):
        """
        Initialize simulation.

        Args:
            num_stars: Number of stars in galaxy
            seed: Random seed for reproducibility
        """
        self.num_stars = num_stars
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Initialize galaxy
        print(f"Initializing galaxy with {num_stars:,} stars...")
        galaxy_params = GalaxyParameters()
        galaxy_params.total_stars = num_stars
        galaxy_params.include_bulge = True
        galaxy_params.bulge_fraction = 0.2
        galaxy_params.disk_scale_length_kpc = 3.5
        galaxy_params.disk_scale_height_kpc = 0.3
        self.galaxy = GalaxyModel(galaxy_params, seed=seed)

        # Initialize astrophysics
        astro_params = AstrophysicsParameters()
        astro_params.sn_rate_per_century = 2.0
        astro_params.sn_lethal_range_pc = 8.0  # Conservative estimate
        astro_params.grb_rate_per_century = 0.01
        astro_params.grb_lethal_range_kpc = 2.0
        astro_params.grb_beaming_angle_deg = 10.0

        self.supernova_model = SupernovaModel(astro_params)
        self.grb_model = GammaRayBurstModel(astro_params)

        # Initialize civilization emergence model with UPDATED parameters
        civ_params = CivilizationParameters()
        # Update based on exoplanet research (2024-2025)
        civ_params.fraction_stars_with_planets = 1.0  # Well-established
        civ_params.avg_habitable_planets_per_system = 0.3  # Updated from 0.2

        # Use more optimistic Drake parameters for this demo
        # (conservative defaults produce very few civilizations)
        civ_params.fraction_develop_life = 0.5  # Optimistic: life is common
        civ_params.fraction_develop_intelligence = 0.05  # Some fraction evolve intelligence
        civ_params.fraction_develop_technology = 0.2  # Modest fraction become technological
        # Combined: 1.0 × 0.3 × 0.5 × 0.05 × 0.2 = 0.0015 (0.15% per star per Gyr)
        # This should give hundreds of civilizations over 10 Gyr

        self.emergence_model = CivilizationEmergence(civ_params)

        # Simulation state
        self.civilizations: List[CivilizationState] = []
        self.next_civ_id = 0
        self.current_time_myr = 0.0

        # Event tracking
        self.supernova_events = []
        self.grb_events = []

        # Stellar properties (will be set during initialization)
        self.stellar_positions = None
        self.stellar_ages = None
        self.stellar_masses = None
        self.stellar_metallicities = None
        self.habitable_star_indices = None  # Cache for performance

    def initialize(self):
        """Initialize galaxy and stellar properties."""
        print("Generating stellar population...")

        # Generate stellar positions
        self.galaxy.generate_stellar_population()
        self.stellar_positions = self.galaxy.positions

        # Generate stellar ages from star formation history
        from great_silence.config.parameters import AstrophysicsParameters
        astro_params = AstrophysicsParameters()
        sfh = StarFormationHistory(astro_params)

        self.stellar_ages = sfh.generate_stellar_ages(
            self.num_stars,
            max_age_gyr=13.0,
            seed=self.seed
        )

        # Generate stellar masses from IMF
        imf = InitialMassFunction("kroupa")
        self.stellar_masses = imf.sample(self.num_stars, seed=self.seed)

        # Generate metallicities (simplified: higher in bulge, radial gradient in disk)
        self.stellar_metallicities = self._generate_metallicities()

        # Identify potentially habitable stars (mass range only - age/metallicity checked during emergence)
        habitable_mask = (self.stellar_masses >= 0.5) & (self.stellar_masses <= 1.4)
        self.habitable_star_indices = np.where(habitable_mask)[0]

        print(f"  Stars: {self.num_stars:,}")
        print(f"  Age range: {self.stellar_ages.min():.2f} - {self.stellar_ages.max():.2f} Gyr")
        print(f"  Habitable stars (0.5-1.4 M☉): {len(self.habitable_star_indices):,}")
        print(f"  Metallicity range: [{self.stellar_metallicities.min():.2f}, {self.stellar_metallicities.max():.2f}] [Fe/H]")

    def _generate_metallicities(self) -> np.ndarray:
        """
        Generate stellar metallicities with realistic gradients.

        - Bulge: Metal-rich, [Fe/H] ~ +0.2
        - Inner disk: Near-solar, [Fe/H] ~ 0.0
        - Outer disk: Metal-poor gradient

        Returns:
            Array of metallicities [Fe/H]
        """
        metallicities = np.zeros(self.num_stars)

        # Calculate galactocentric radii
        radii = np.sqrt(self.stellar_positions[:, 0]**2 + self.stellar_positions[:, 1]**2)

        # Metallicity gradient: -0.07 dex/kpc (observational value for Milky Way)
        gradient = -0.07  # dex/kpc

        for i in range(self.num_stars):
            r = radii[i]

            # Base metallicity depends on radius
            # Solar neighborhood (r~8 kpc) has [Fe/H] ~ 0.0
            base = gradient * (r - 8.0)

            # Bulge stars are more metal-rich
            height = abs(self.stellar_positions[i, 2])
            if r < 3.0 and height < 0.5:  # Bulge criterion
                base += 0.3

            # Add scatter
            scatter = self.rng.normal(0, 0.15)

            metallicities[i] = base + scatter

        return metallicities

    def run(self, duration_myr: float = 10000.0, dt_myr: float = 100.0, debug: bool = False):
        """
        Run simulation with realistic emergence over time.

        Args:
            duration_myr: Total simulation duration (Myr)
            dt_myr: Time step size (Myr)
            debug: Print debug information
        """
        print(f"\n🌌 Running simulation for {duration_myr:.0f} Myr...")
        print(f"Time step: {dt_myr:.0f} Myr")

        num_steps = int(duration_myr / dt_myr)
        dt_gyr = dt_myr / 1000.0

        # Debug: Sample emergence probability for a few stars
        if debug and num_steps > 0:
            print("\n🔍 DEBUG: Sampling emergence probabilities at different ages...")
            test_ages = [1.0, 3.0, 5.0, 8.0, 10.0]  # Gyr
            for age in test_ages:
                p = self.emergence_model.emergence_probability(
                    stellar_age_gyr=age,
                    dt_gyr=dt_gyr,
                    stellar_mass=1.0,
                    metallicity_feh=0.0
                )
                print(f"  Age={age:.1f} Gyr: p_emerge={p:.6e} per {dt_myr:.0f} Myr")

        for step in range(num_steps):
            self.current_time_myr = step * dt_myr

            # Check for new civilization emergence
            self._check_emergence(dt_gyr)

            # Evolve existing civilizations
            self._evolve_civilizations(dt_myr)

            # Check astrophysical hazards
            self._check_astrophysical_hazards(dt_myr)

            # Progress report every 10%
            if (step + 1) % (num_steps // 10) == 0:
                alive = sum(1 for c in self.civilizations if c.alive)
                total = len(self.civilizations)
                print(f"  T={self.current_time_myr:6.0f} Myr: {total:4d} total civs, {alive:4d} alive")

        self.print_final_statistics()

    def _check_emergence(self, dt_gyr: float):
        """Check for new civilization emergence based on stellar properties."""
        # Find stars that could potentially host emerging civilizations
        # (haven't already hosted one)
        occupied_stars = set(c.parent_star_idx for c in self.civilizations)

        # Only check habitable stars (performance optimization)
        for star_idx in self.habitable_star_indices:
            if star_idx in occupied_stars:
                continue  # Star already has/had a civilization

            # Get stellar properties
            # IMPORTANT: Stellar ages increase as simulation progresses
            age_at_start_gyr = self.stellar_ages[star_idx]
            current_age_gyr = age_at_start_gyr + (self.current_time_myr / 1000.0)

            mass = self.stellar_masses[star_idx]
            metallicity = self.stellar_metallicities[star_idx]

            # Calculate emergence probability (includes all physical constraints)
            p_emerge = self.emergence_model.emergence_probability(
                stellar_age_gyr=current_age_gyr,
                dt_gyr=dt_gyr,
                stellar_mass=mass,
                metallicity_feh=metallicity
            )

            # Stochastic emergence
            if self.rng.random() < p_emerge:
                self._spawn_civilization(star_idx)

    def _spawn_civilization(self, star_idx: int):
        """
        Spawn a new civilization at the given star.

        Args:
            star_idx: Index of parent star
        """
        civ = CivilizationState(
            id=self.next_civ_id,
            parent_star_idx=star_idx,
            position=self.stellar_positions[star_idx].copy(),
            birth_time_myr=self.current_time_myr,
            age_myr=0.0,
            kardashev_level=0.5,  # Start as Type 0.5 (pre-industrial)
            social_maturity=0.0,
            alive=True
        )

        self.civilizations.append(civ)
        self.next_civ_id += 1

    def _evolve_civilizations(self, dt_myr: float):
        """Evolve existing civilizations (simplified growth model)."""
        for civ in self.civilizations:
            if not civ.alive:
                continue

            civ.age_myr += dt_myr

            # Simple Kardashev progression (logarithmic growth)
            # Real model would be more complex with crises, stagnation, etc.
            growth_rate = 0.001  # K-level increase per Myr
            civ.kardashev_level += growth_rate * dt_myr

            # Social maturity grows with experience
            civ.social_maturity = min(1.0, civ.age_myr / 1000.0)

            # Simple self-destruction model (10% per Gyr baseline)
            p_destroy = 0.0001 * dt_myr  # 0.1% per Myr
            if self.rng.random() < p_destroy:
                civ.alive = False
                civ.cause_of_death = "self_destruction"
                civ.death_time_myr = self.current_time_myr

    def _check_astrophysical_hazards(self, dt_myr: float):
        """Check for supernova and GRB events (simplified)."""
        # This is a placeholder - full implementation would use the hazard models
        pass

    def print_final_statistics(self):
        """Print final simulation statistics."""
        print("\n" + "="*70)
        print("REALISTIC EMERGENCE SIMULATION RESULTS")
        print("="*70)

        total_emerged = len(self.civilizations)
        alive = sum(1 for c in self.civilizations if c.alive)
        dead = total_emerged - alive

        print(f"\n📊 CIVILIZATION STATISTICS:")
        print(f"  Total emerged: {total_emerged}")
        print(f"  Currently alive: {alive} ({100*alive/max(1,total_emerged):.1f}%)")
        print(f"  Extinct: {dead} ({100*dead/max(1,total_emerged):.1f}%)")

        if self.civilizations:
            emergence_times = [c.birth_time_myr for c in self.civilizations]
            print(f"\n⏰ EMERGENCE TIMELINE:")
            print(f"  First emergence: {min(emergence_times):.0f} Myr")
            print(f"  Last emergence: {max(emergence_times):.0f} Myr")
            print(f"  Emergence timespan: {max(emergence_times) - min(emergence_times):.0f} Myr")

            # Emergence histogram
            print(f"\n📈 EMERGENCE BY ERA (1 Gyr bins):")
            bins = np.arange(0, self.current_time_myr + 1000, 1000)
            hist, _ = np.histogram(emergence_times, bins=bins)
            for i, count in enumerate(hist):
                if count > 0:
                    era_start = bins[i]
                    era_end = bins[i+1]
                    bar = "█" * int(count / 5)  # Scale for display
                    print(f"  {era_start:5.0f}-{era_end:5.0f} Myr: {count:4d} {bar}")

        if alive > 0:
            alive_civs = [c for c in self.civilizations if c.alive]
            ages = [c.age_myr for c in alive_civs]
            k_levels = [c.kardashev_level for c in alive_civs]

            print(f"\n🌟 LIVING CIVILIZATIONS:")
            print(f"  Average age: {np.mean(ages):.1f} Myr")
            print(f"  Age range: {min(ages):.1f} - {max(ages):.1f} Myr")
            print(f"  Average Kardashev: {np.mean(k_levels):.2f}")
            print(f"  Kardashev range: {min(k_levels):.2f} - {max(k_levels):.2f}")

        print("\n" + "="*70)


if __name__ == "__main__":
    # Run realistic emergence simulation
    print("🌌 REALISTIC CIVILIZATION EMERGENCE SIMULATION")
    print("Based on exoplanet data from Kepler & TESS (2024-2025)")
    print("="*70)

    sim = RealisticEmergenceSimulation(
        num_stars=100000,  # 100k stars for reasonable runtime
        seed=42
    )

    sim.initialize()
    sim.run(duration_myr=10000.0, dt_myr=100.0, debug=True)  # 10 Gyr total, 100 Myr steps
