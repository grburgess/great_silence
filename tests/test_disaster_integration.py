"""Integration test for disaster modules with simulation."""

import numpy as np
import tempfile
from pathlib import Path
import h5py

from great_silence import SimulationConfig, GalaxySimulation
from great_silence.simulation.engine import HazardEvent
from great_silence.simulation.disasters.archiver import DisasterArchiver


def test_disaster_archiving():
    """Test disaster archiving with simulation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create minimal config
        config = SimulationConfig()
        config.galaxy.total_stars = 1000
        config.simulation.simulation_duration_gyr = 0.1
        config.simulation.time_step_myr = 1.0
        config.simulation.save_snapshots = True
        config.simulation.output_directory = tmpdir
        
        # Run simulation
        sim = GalaxySimulation(config, seed=42)
        sim.run(verbose=False)
        
        # Check disasters.h5
        archive_path = Path(tmpdir) / "disasters.h5"
        
        if archive_path.exists():
            print(f"✓ disasters.h5 created: {archive_path}")
            
            with h5py.File(archive_path, "r") as f:
                dset = f["disasters"]
                print(f"✓ Disaster count: {dset.shape[0]}")
                print(f"✓ Dataset shape: {dset.shape}")
                print(f"✓ Dataset dtype: {dset.dtype}")
        else:
            print("✗ disasters.h5 not created")


def test_archiver_api():
    """Test DisasterArchiver API."""
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = Path(tmpdir) / "test.h5"
        archiver = DisasterArchiver(
            archive_path=archive_path,
            recent_window_myr=10.0,
            buffer_size=2
        )
        
        # Add test disasters
        for i in range(5):
            event = HazardEvent(
                time_myr=i * 100.0,
                event_type='supernova',
                position=np.array([i * 5.0, 0.0, 0.0]),
                energy=1e51,
                sterilization_radius_pc=50.0
            )
            archiver.archive_disaster(event, i * 100.0)
        
        archiver.finalize()
        
        # Query disasters
        all_events = archiver.get_all_disasters()
        print(f"✓ Total disasters: {len(all_events)}")
        
        window_events = archiver.get_disasters_in_window(100.0, 300.0)
        print(f"✓ Disasters in [100, 300] Myr: {len(window_events)}")
        
        # Check type consistency
        for t, event in all_events[:2]:
            print(f"  Event at {t} Myr: type={event.event_type}")


def test_spatial_index():
    """Test disaster spatial index."""
    from great_silence.simulation.disasters.spatial_index import DisasterSpatialIndex
    from great_silence.simulation.disasters.encoding import encode_disaster, decode_disaster
    
    index = DisasterSpatialIndex()
    
    disasters = [
        HazardEvent(
            time_myr=i * 100.0,
            event_type='supernova',
            position=np.array([i * 2.0, i * 2.0, i * 2.0]),
            energy=1e51,
            sterilization_radius_pc=50.0
        )
        for i in range(10)
    ]
    
    for d in disasters:
        binary = encode_disaster(d)
        decoded = decode_disaster(binary)
        index.add_disaster(decoded)
    
    # Spatial query
    results = index.query_spatial(np.array([5.0, 5.0, 5.0]), 5.0)
    print(f"✓ Spatial query results: {len(results)} disasters")
    
    # Temporal query
    results = index.query_temporal(0.0, 500.0)
    print(f"✓ Temporal query results: {len(results)} disasters")
    
    # Spatiotemporal query
    results = index.query_spatiotemporal(
        np.array([5.0, 5.0, 5.0]),
        5.0,
        0.0,
        500.0
    )
    print(f"✓ Spatiotemporal query results: {len(results)} disasters")


def test_recovery_queue():
    """Test star recovery queue."""
    from great_silence.simulation.disasters.recovery import (
        RecoveryQueue,
        SterilizationStatus
    )
    
    queue = RecoveryQueue(100)
    
    # Sterilize stars
    queue.sterilize_star(10, 100.0, 50.0, permanent=False)
    queue.sterilize_star(20, 100.0, 0.0, permanent=True)
    queue.sterilize_star(30, 100.0, 25.0, permanent=False)
    
    # Process recoveries
    recovered = queue.process_recoveries(150.0)
    print(f"✓ Recovered stars: {len(recovered)}")
    print(f"✓ Recovered indices: {recovered}")
    
    # Check statistics
    stats = queue.get_statistics()
    print(f"✓ Habitable: {stats['habitable']}")
    print(f"✓ Temporarily sterilized: {stats['temporarily_sterilized']}")
    print(f"✓ Permanently sterilized: {stats['permanently_sterilized']}")


if __name__ == "__main__":
    print("=" * 70)
    print("Disaster Module Integration Tests")
    print("=" * 70)
    
    print("\n1. Testing disaster archiving with simulation...")
    test_disaster_archiving()
    
    print("\n2. Testing DisasterArchiver API...")
    test_archiver_api()
    
    print("\n3. Testing spatial index...")
    test_spatial_index()
    
    print("\n4. Testing recovery queue...")
    test_recovery_queue()
    
    print("\n" + "=" * 70)
    print("All integration tests completed!")
    print("=" * 70)
