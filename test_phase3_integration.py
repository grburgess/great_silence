"""Test Phase 3: Integration with real simulation data."""

from pathlib import Path
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs.html_exporter import export_html

def test_real_simulation():
    """Test visualization with real simulation data."""
    print("Creating simulation configuration...")
    config = SimulationConfig()
    
    # Smaller galaxy for faster testing
    config.galaxy.total_stars = 10_000
    config.simulation.simulation_duration_gyr = 0.5
    config.simulation.time_step_myr = 5.0
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 25.0
    
    # Optimistic Drake for visible civilizations
    config.civilization.fraction_develop_life = 0.5
    config.civilization.fraction_develop_intelligence = 0.1
    config.civilization.fraction_develop_technology = 0.5
    
    # Enable hazards
    config.astrophysics.supernova_rate_per_galaxy_gyr = 2.0
    config.astrophysics.grb_rate_per_galaxy_gyr = 1.0
    
    print(f"\nSimulation Parameters:")
    print(f"  Galaxy: {config.galaxy.total_stars:,} stars")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Snapshots: {int(config.simulation.simulation_duration_gyr * 1000 / config.simulation.snapshot_interval_myr)}")
    
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
    total_hazards = len(sim.hazard_events)
    
    print(f"\nSimulation complete!")
    print(f"  Total civilizations: {total_civs}")
    print(f"  Currently active: {active_civs}")
    print(f"  Extinct: {total_civs - active_civs}")
    print(f"  Total hazards: {total_hazards}")
    print(f"  Snapshots captured: {len(sim.snapshots)}")
    
    # Check snapshot fields
    if sim.snapshots:
        first_snap = sim.snapshots[0]
        print(f"\nFirst snapshot fields:")
        print(f"  time_myr: {first_snap.time_myr}")
        print(f"  active_civilizations: {first_snap.active_civilizations}")
        print(f"  has hazard_events: {hasattr(first_snap, 'hazard_events')}")
        print(f"  has colony_positions: {hasattr(first_snap, 'colony_positions')}")
        print(f"  has civ_birth_ages: {hasattr(first_snap, 'civ_birth_ages')}")
        
        if hasattr(first_snap, 'hazard_events'):
            print(f"  hazard_events count: {len(first_snap.hazard_events)}")
        if hasattr(first_snap, 'colony_positions'):
            print(f"  colony_positions count: {len(first_snap.colony_positions)}")
        if hasattr(first_snap, 'civ_birth_ages'):
            print(f"  civ_birth_ages count: {len(first_snap.civ_birth_ages)}")
    
    print("\n" + "=" * 80)
    print("EXPORTING VISUALIZATION")
    print("=" * 80)
    
    output_path = Path("output/test_phase3_real_sim.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    export_html(
        sim,
        output_path,
        animated=True,
        show_trajectories=True,
        show_spheres=True,
        show_hazards=True,
        compress=False
    )
    
    print(f"\n✓ Export complete!")
    print(f"  Saved to: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")
    
    print("\n✓ Phase 3 Integration test complete!")

if __name__ == "__main__":
    test_real_simulation()
