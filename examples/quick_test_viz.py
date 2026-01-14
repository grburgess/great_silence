"""Quick test to generate visualization with trajectories."""
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer
import os

config = SimulationConfig()
config.galaxy.total_stars = 1000
config.civilization.expansion_enabled = True
config.civilization.min_kardashev_for_expansion = 0.8
config.civilization.kardashev_advancement_rate_mean = 0.2
config.civilization.mean_civilization_lifetime_myr = 100.0
config.civilization.personality_evolution_enabled = False
config.simulation.simulation_duration_gyr = 0.1
config.simulation.time_step_myr = 5.0
config.simulation.snapshot_interval_myr = 20.0
config.simulation.random_seed = 42

print("Running quick simulation...")
sim = GalaxySimulation(config)
sim.run()

print(f"Civs: {len(sim.all_civilizations)}")
for c in sim.all_civilizations[:3]:
    print(f"  Civ {c.civ_id}: colonies={len(c.colonized_stars)}, archived={len(c.archived_probes)}")

print("\nExporting...")
renderer = ThreeJSRenderer(sim)
renderer.export("examples/test_trajectories.html", animated=True, show_trajectories=True)
print(f"Done! Size: {os.path.getsize('examples/test_trajectories.html')/1024:.1f} KB")
