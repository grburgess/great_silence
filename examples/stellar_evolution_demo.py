#!/usr/bin/env python
"""Demo visualization showing stellar evolution and star formation.

This demo runs a simulation with a larger galaxy to show:
- Stars aging over time
- New massive stars being born in the disk
- Those stars eventually exploding as supernovae/GRBs

Run with: mamba run -n galaticbot python examples/stellar_evolution_demo.py
"""

import sys
import os
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

sys.path.insert(0, str(Path(__file__).parent.parent))

from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs import export_html


def main():
    print("=" * 60)
    print("Stellar Evolution & Star Formation Demo")
    print("=" * 60)
    print()

    config = SimulationConfig()
    
    config.galaxy.total_stars = 500_000
    config.simulation.simulation_duration_gyr = 10.0
    config.simulation.time_step_myr = 100.0
    config.simulation.save_snapshots = True
    config.simulation.enable_star_formation = True
    config.simulation.random_seed = 12345
    
    # VISUALIZATION MODE: Spread disasters across the simulation
    # In reality, all massive stars die within ~55 Myr (their short lifetimes)
    # This setting artificially spreads them for better visualization
    config.simulation.spread_initial_disasters = True
    
    config.astrophysics.grb_fraction_of_sne = 0.3
    config.astrophysics.grb_min_progenitor_mass = 15.0
    
    config.civilization.emergence_rate_per_star_per_myr = 1e-8
    
    print("Configuration:")
    print(f"  Stars: {config.galaxy.total_stars:,}")
    print(f"  Duration: {config.simulation.simulation_duration_gyr} Gyr")
    print(f"  Star formation: ENABLED")
    print(f"  Spread disasters: ENABLED (visualization mode)")
    print(f"  GRB fraction: {config.astrophysics.grb_fraction_of_sne * 100:.0f}%")
    print()

    print("Initializing simulation...")
    sim = GalaxySimulation(config)
    sim.initialize()
    
    stats = sim.disaster_scheduler.get_statistics()
    print()
    print("Pre-scheduled events:")
    print(f"  Supernovae: {stats['supernovae']}")
    print(f"  GRBs: {stats['grbs']}")
    print(f"  NS mergers: {stats['ns_mergers']}")
    print(f"  Star births: {stats['scheduled_star_births']}")
    print()

    print("Running simulation...")
    sim.run()
    print()
    
    print(f"Simulation complete!")
    print(f"  Final time: {sim.current_time_myr / 1000:.1f} Gyr")
    print(f"  Snapshots: {len(sim.snapshots)}")
    
    total_hazards = sum(len(s.hazard_events) for s in sim.snapshots)
    print(f"  Total disaster events recorded: {total_hazards}")
    print()

    output_dir = Path(__file__).parent
    output_file = output_dir / "stellar_evolution_viz.html"
    
    print(f"Exporting visualization to {output_file}...")
    export_html(sim, str(output_file), animated=True)
    print("Export complete!")
    print()

    port = 8889
    os.chdir(output_dir)
    
    handler = SimpleHTTPRequestHandler
    httpd = HTTPServer(("", port), handler)
    
    def serve():
        httpd.serve_forever()
    
    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()
    
    url = f"http://localhost:{port}/stellar_evolution_viz.html"
    print(f"Starting HTTP server on port {port}...")
    print(f"Opening: {url}")
    print()
    print("=" * 60)
    print("VISUALIZATION FEATURES:")
    print("=" * 60)
    print()
    print("1. DISASTERS PANEL (bottom left):")
    print("   - Toggle 'History' to see all past disasters")
    print("   - Toggle 'Exaggerated' for 50x scale visibility")
    print("   - Filter by type: SN (red), GRB (cyan), NSM (magenta)")
    print()
    print("2. TIMELINE (bottom):")
    print("   - Scrub through 10 Gyr of galactic history")
    print("   - Disaster markers show when events occurred")
    print("   - Click markers to jump to specific disasters")
    print()
    print("3. STAR FORMATION:")
    print(f"   - {stats['scheduled_star_births']} new massive stars born")
    print("   - These create NEW disasters as they age and die")
    print("   - Watch for SNe appearing from newly formed stars")
    print()
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    webbrowser.open(url)
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nShutting down...")
        httpd.shutdown()


if __name__ == "__main__":
    main()
