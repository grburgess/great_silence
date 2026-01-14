#!/usr/bin/env python
"""Demo script to test disaster visualization features.

Runs a simulation with many disasters and exports an interactive HTML visualization.
"""

from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs import export_html
from pathlib import Path


def main():
    print("=" * 60)
    print("Disaster Visualization Demo")
    print("=" * 60)
    
    config = SimulationConfig()
    
    config.galaxy.total_stars = 50000
    config.galaxy.include_bulge = True
    config.galaxy.bulge_fraction = 0.2
    
    config.simulation.simulation_duration_gyr = 5.0
    config.simulation.time_step_myr = 50.0
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 100.0
    
    config.civilization.fraction_develop_life = 0.01
    config.civilization.fraction_intelligent = 0.5
    config.civilization.mean_emergence_time_gyr = 4.0
    
    # Boost GRB probability for visualization demo
    # (With 50k stars, only ~3 GRB progenitors exist, so 50% ensures we see some)
    config.astrophysics.grb_fraction_of_sne = 0.5  # 50% of massive SNe produce GRBs
    config.astrophysics.grb_min_progenitor_mass = 15.0  # Lower threshold to include more
    
    print("\nConfiguration:")
    print(f"  Stars: {config.galaxy.total_stars:,}")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Timestep: {config.simulation.time_step_myr} Myr")
    
    print("\nInitializing simulation...")
    sim = GalaxySimulation(config, seed=400)  # Seed 400 gives good disaster spread
    sim.initialize()
    
    stats = sim.disaster_scheduler.get_statistics()
    print(f"\nPrecomputed disasters:")
    print(f"  Supernovae: {stats['supernovae']}")
    print(f"  GRBs: {stats['grbs']}")
    print(f"  NS Mergers: {stats['ns_mergers']}")
    print(f"  Total: {stats['total_scheduled']}")
    
    print("\nRunning simulation...")
    sim.run(verbose=True)
    
    print(f"\nResults:")
    print(f"  Civilizations emerged: {len(sim.civilizations)}")
    print(f"  Active at end: {sum(1 for c in sim.civilizations if c.is_active)}")
    print(f"  Disaster events recorded: {len(sim.hazard_events)}")
    print(f"  Snapshots: {len(sim.snapshots)}")
    
    event_types = {}
    for h in sim.hazard_events:
        event_types[h.event_type] = event_types.get(h.event_type, 0) + 1
    print(f"  Event breakdown: {event_types}")
    
    deaths_by_disaster = {}
    for civ in sim.civilizations:
        if not civ.is_active and civ.death_cause:
            cause = civ.death_cause
            deaths_by_disaster[cause] = deaths_by_disaster.get(cause, 0) + 1
    if deaths_by_disaster:
        print(f"  Civ deaths by cause: {deaths_by_disaster}")
    
    output_path = Path("examples/galaxy_disasters_demo.html")
    print(f"\nExporting visualization to {output_path}...")
    
    export_html(
        sim, 
        output_path, 
        animated=True,
        show_hazards=True,
        show_trajectories=True,
    )
    
    print(f"\n{'=' * 60}")
    print(f"Visualization exported to: {output_path.absolute()}")
    print(f"{'=' * 60}")
    print("\nVisualization features to test:")
    print("  1. Toggle 'History Mode' to see all past disasters")
    print("  2. Toggle 'Exaggerated' scale to see extinction zones")
    print("  3. Filter by disaster type (SN/GRB/NSM)")
    print("  4. Toggle Zones/Beams/Deaths visibility")
    print("  5. Click disaster timeline to jump to events")
    print("  6. Use playback controls to animate through time")
    
    print("\nStarting HTTP server...")
    import http.server
    import socketserver
    import webbrowser
    import os
    import threading
    
    os.chdir(output_path.parent)
    
    PORT = 8888
    handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        url = f"http://localhost:{PORT}/{output_path.name}"
        print(f"\nServer running at: http://localhost:{PORT}")
        print(f"Opening: {url}")
        print("\nPress Ctrl+C to stop the server")
        
        webbrowser.open(url)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
