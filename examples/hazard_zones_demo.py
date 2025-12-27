"""
Hazard Zones Demonstration

Visualizes how metallicity, stellar density, and component type affect
astrophysical hazards (supernovae and GRBs) across the galaxy.
"""

from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization import GalaxyVisualizer

def main():
    print("=" * 70)
    print("GALACTIC HAZARD ZONES DEMONSTRATION")
    print("=" * 70)

    print("\nGenerating realistic Milky Way-like galaxy...")
    config = SimulationConfig()
    config.galaxy.total_stars = 100_000  # Enough for good statistics

    # Enable all realism features
    config.galaxy.include_bulge = True
    config.galaxy.use_age_gradient = True
    config.galaxy.use_metallicity_gradient = True

    sim = GalaxySimulation(config, seed=42)
    sim.initialize()

    print("\n" + "-" * 70)
    print("HAZARD PHYSICS SUMMARY")
    print("-" * 70)

    print("\n1. **Metallicity-Dependent GRB Rates**")
    print("   - Metal-poor stars retain more angular momentum → easier to form GRB jets")
    print("   - Rate ∝ 10^(-0.8 * [Fe/H])")
    print("   - Outer disk ([Fe/H] ~ -0.5): ~3x MORE GRBs than bulge")
    print("   - Bulge ([Fe/H] ~ +0.3):      ~2x FEWER GRBs than solar")

    print("\n2. **Component-Dependent Supernova Rates**")
    print("   - Bulge has older stellar population → more evolved massive stars")
    print("   - Bulge modifier: 2x higher SN rate than pure disk")
    print("   - Stars near end of main sequence lifetime → imminent supernovae")

    print("\n3. **Local Density Hazard Modifier**")
    print("   - Dense regions have more frequent stellar encounters")
    print("   - Hazard ∝ sqrt(local_density / solar_neighborhood_density)")
    print("   - Bulge density (~1 star/pc³):   ~3x more dangerous")
    print("   - Solar neighborhood (~0.1 star/pc³):  baseline")
    print("   - Outer disk (~0.01 star/pc³): ~0.3x less dangerous")

    print("\n" + "-" * 70)
    print("GENERATING HAZARD ZONE VISUALIZATION")
    print("-" * 70)

    viz = GalaxyVisualizer()

    print("\nCreating 6-panel hazard map...")
    print("  [1/6] Stellar density distribution")
    print("  [2/6] Supernova risk zones (density + age-dependent)")
    print("  [3/6] GRB risk zones (metallicity-dependent)")
    print("  [4/6] Combined hazard + Galactic Habitable Zone")
    print("  [5/6] Radial hazard profile")
    print("  [6/6] Safety map for civilizations")

    viz.plot_hazard_zones(
        sim.galaxy.positions,
        sim.galaxy.masses,
        sim.galaxy.ages,
        sim.galaxy.component_type,
        sim.galaxy.metallicities,
        save_path='output/hazard_zones.png'
    )

    print("\n" + "=" * 70)
    print("VISUALIZATION COMPLETE")
    print("=" * 70)

    print("\nKey Findings:")
    print("")
    print("**Hazardous Regions (RED):**")
    print("  - Central bulge: High density + old stars → many supernovae")
    print("  - Stellar density ~1-10 stars/pc³")
    print("  - SN rate elevated by 2-5x due to evolved population")
    print("")
    print("**Galactic Habitable Zone (GREEN RING, r = 6-10 kpc):**")
    print("  - Moderate stellar density (~0.1 stars/pc³)")
    print("  - Mix of ages → lower SN rate")
    print("  - Solar neighborhood at r ~ 8 kpc is in this zone!")
    print("  - Optimal for long-term civilization survival")
    print("")
    print("**Outer Disk (MIXED):**")
    print("  - Low density → fewer supernovae (GOOD)")
    print("  - Low metallicity → more GRBs (BAD)")
    print("  - Young stars → fewer planets (BAD for emergence)")
    print("")
    print("**Scientific Implications:**")
    print("  1. Fermi Paradox: Civilizations should cluster in GHZ")
    print("  2. Self-location bias: We're in GHZ (anthropic principle)")
    print("  3. SETI strategy: Search mid-disk regions preferentially")
    print("")
    print(f"Hazard map saved: output/hazard_zones.png")
    print()


if __name__ == '__main__':
    import os
    os.makedirs('output', exist_ok=True)
    main()
