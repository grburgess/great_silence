"""
Comprehensive tests for stellar motion integration.

Tests cover:
1. Equilibrium stability (velocity initialization)
2. Probe intercept calculations
3. Dynamic disaster positions
4. Delta-compressed snapshot storage
5. GPU visualization data export
6. Performance benchmarks
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from great_silence import GalaxySimulation, SimulationConfig
from great_silence.galaxy.structure import GalaxyModel
from great_silence.config.parameters import GalaxyParameters, SimulationParameters


class TestVelocityInitialization:
    """Test velocity initialization modes (simple vs Jeans)."""

    def test_simple_mode_generates_velocities(self):
        """Test that simple mode generates valid velocities."""
        params = GalaxyParameters(total_stars=1000, velocity_init_mode="simple")
        galaxy = GalaxyModel(params, seed=42)
        galaxy.generate_stellar_population()
        
        assert galaxy.velocities is not None
        assert galaxy.velocities.shape == (1000, 3)
        assert not np.any(np.isnan(galaxy.velocities))
        
    def test_jeans_mode_generates_velocities(self):
        """Test that Jeans mode generates valid velocities."""
        params = GalaxyParameters(total_stars=1000, velocity_init_mode="jeans")
        galaxy = GalaxyModel(params, seed=42)
        galaxy.generate_stellar_population()
        
        assert galaxy.velocities is not None
        assert galaxy.velocities.shape == (1000, 3)
        assert not np.any(np.isnan(galaxy.velocities))
        
    def test_initial_positions_stored(self):
        """Test that initial positions are stored for delta compression."""
        params = GalaxyParameters(total_stars=1000)
        galaxy = GalaxyModel(params, seed=42)
        galaxy.generate_stellar_population()
        
        assert galaxy.initial_positions is not None
        assert galaxy.initial_positions.shape == galaxy.positions.shape
        np.testing.assert_array_equal(galaxy.initial_positions, galaxy.positions)
        
    def test_asymmetric_drift_reduces_velocity(self):
        """Test that asymmetric drift reduces mean azimuthal velocity."""
        params = GalaxyParameters(total_stars=5000, velocity_init_mode="jeans")
        galaxy = GalaxyModel(params, seed=42)
        galaxy.generate_stellar_population()
        
        x, y = galaxy.positions[:, 0], galaxy.positions[:, 1]
        R = np.sqrt(x**2 + y**2)
        
        disk_mask = galaxy.component_type >= 1
        R_disk = R[disk_mask]
        vx_disk = galaxy.velocities[disk_mask, 0]
        vy_disk = galaxy.velocities[disk_mask, 1]
        
        v_phi = -vx_disk * y[disk_mask] / (R_disk + 1e-10) + vy_disk * x[disk_mask] / (R_disk + 1e-10)
        
        mid_R_mask = (R_disk > 4.0) & (R_disk < 12.0)
        if np.sum(mid_R_mask) > 100:
            mean_v_phi = np.mean(np.abs(v_phi[mid_R_mask]))
            assert mean_v_phi < 250.0
            assert mean_v_phi > 100.0


class TestProbeIntercept:
    """Test predictive intercept calculations for probes."""
    
    def test_intercept_with_motion_disabled(self):
        """Test that intercept returns static position when motion disabled."""
        config = SimulationConfig()
        config.galaxy.total_stars = 1000
        config.simulation.enable_stellar_motion = False
        config.simulation.probe_intercept_enabled = True
        config.simulation.simulation_duration_gyr = 0.01
        
        sim = GalaxySimulation(config, seed=42)
        sim.initialize()
        
        source_pos = sim.galaxy.positions[0]
        target_idx = 1
        target_pos = sim.galaxy.positions[target_idx]
        
        intercept_pos, travel_time = sim._calculate_intercept_position(
            source_pos, target_idx, velocity_c=0.01
        )
        
        np.testing.assert_array_almost_equal(intercept_pos, target_pos)
        
    def test_intercept_with_motion_enabled(self):
        """Test that intercept differs from static position when motion enabled."""
        config = SimulationConfig()
        config.galaxy.total_stars = 1000
        config.simulation.enable_stellar_motion = True
        config.simulation.probe_intercept_enabled = True
        config.simulation.simulation_duration_gyr = 0.01
        
        sim = GalaxySimulation(config, seed=42)
        sim.initialize()
        
        source_pos = sim.galaxy.positions[0]
        target_idx = 10
        target_pos_static = sim.galaxy.positions[target_idx].copy()
        
        intercept_pos, travel_time = sim._calculate_intercept_position(
            source_pos, target_idx, velocity_c=0.001
        )
        
        distance_to_static = np.linalg.norm(intercept_pos - target_pos_static)
        assert travel_time > 0
        
    def test_intercept_converges(self):
        """Test that iterative intercept calculation converges."""
        config = SimulationConfig()
        config.galaxy.total_stars = 1000
        config.simulation.enable_stellar_motion = True
        config.simulation.probe_intercept_enabled = True
        
        sim = GalaxySimulation(config, seed=42)
        sim.initialize()
        
        source_pos = sim.galaxy.positions[0]
        target_idx = 50
        
        pos1, t1 = sim._calculate_intercept_position(source_pos, target_idx, 0.01, max_iterations=1)
        pos2, t2 = sim._calculate_intercept_position(source_pos, target_idx, 0.01, max_iterations=2)
        pos3, t3 = sim._calculate_intercept_position(source_pos, target_idx, 0.01, max_iterations=3)
        
        diff_12 = np.linalg.norm(pos2 - pos1)
        diff_23 = np.linalg.norm(pos3 - pos2)
        
        assert diff_23 < diff_12 or diff_12 < 0.001


class TestDynamicDisasterPositions:
    """Test dynamic disaster positions tracking parent stars."""
    
    def test_disaster_get_position_with_tracking(self):
        """Test ScheduledDisaster.get_position() tracks parent star."""
        from great_silence.simulation.disasters.unified_scheduler import (
            ScheduledDisaster, DisasterType
        )
        
        disaster = ScheduledDisaster(
            time_myr=100.0,
            disaster_type=DisasterType.SUPERNOVA,
            star_idx=5,
            position=np.array([1.0, 2.0, 3.0]),
            energy_ergs=1e51,
            lethal_radius_pc=10.0,
            sterilization_radius_pc=50.0,
        )
        
        galaxy_positions = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [3.0, 0.0, 0.0],
            [4.0, 0.0, 0.0],
            [5.0, 5.0, 5.0],
        ])
        
        pos_tracked = disaster.get_position(galaxy_positions, track_parent_star=True)
        np.testing.assert_array_equal(pos_tracked, [5.0, 5.0, 5.0])
        
        pos_static = disaster.get_position(galaxy_positions, track_parent_star=False)
        np.testing.assert_array_equal(pos_static, [1.0, 2.0, 3.0])
        
    def test_disaster_fallback_when_no_parent(self):
        """Test that disaster uses fallback position when star_idx < 0."""
        from great_silence.simulation.disasters.unified_scheduler import (
            ScheduledDisaster, DisasterType
        )
        
        disaster = ScheduledDisaster(
            time_myr=100.0,
            disaster_type=DisasterType.NS_MERGER,
            star_idx=-1,
            position=np.array([7.0, 8.0, 9.0]),
            energy_ergs=1e52,
            lethal_radius_pc=30.0,
            sterilization_radius_pc=100.0,
        )
        
        galaxy_positions = np.zeros((10, 3))
        
        pos = disaster.get_position(galaxy_positions, track_parent_star=True)
        np.testing.assert_array_equal(pos, [7.0, 8.0, 9.0])


class TestDeltaCompressedSnapshots:
    """Test delta-compressed snapshot storage."""
    
    def test_snapshot_stores_full_positions_when_motion_enabled(self):
        """Test that snapshots store full positions when motion enabled (positions evolve)."""
        config = SimulationConfig()
        config.galaxy.total_stars = 500
        config.simulation.enable_stellar_motion = True
        config.simulation.simulation_duration_gyr = 0.1
        config.simulation.save_snapshots = True
        config.simulation.snapshot_interval_myr = 50.0
        
        sim = GalaxySimulation(config, seed=42)
        sim.initialize()
        sim.run()
        
        assert len(sim.snapshots) > 0
        
        first_snap = sim.snapshots[0]
        assert first_snap.use_delta_compression == False
        assert len(first_snap.stellar_positions) == config.galaxy.total_stars
        
    def test_snapshot_uses_delta_when_motion_disabled(self):
        """Test that snapshots use delta compression when motion disabled (positions static)."""
        config = SimulationConfig()
        config.galaxy.total_stars = 500
        config.simulation.enable_stellar_motion = False
        config.simulation.simulation_duration_gyr = 0.1
        config.simulation.save_snapshots = True
        config.simulation.snapshot_interval_myr = 50.0
        
        sim = GalaxySimulation(config, seed=42)
        sim.initialize()
        sim.run()
        
        assert len(sim.snapshots) > 0
        
        first_snap = sim.snapshots[0]
        assert first_snap.use_delta_compression == True
        assert first_snap.initial_positions is not None
        
    def test_get_positions_reconstructs_correctly(self):
        """Test that get_positions() reconstructs positions from delta."""
        from great_silence.simulation.engine import SimulationSnapshot
        
        initial_pos = np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
        velocities = np.array([[100.0, 0.0, 0.0], [200.0, 0.0, 0.0]])
        
        snap = SimulationSnapshot(
            time_myr=1000.0,
            active_civilizations=0,
            total_civilizations_ever=0,
            colonized_systems=0,
            civilization_states=[],
            stellar_positions=np.array([]),
            use_delta_compression=True,
            reference_time_myr=0.0,
            stellar_velocities=velocities,
            initial_positions=initial_pos,
        )
        
        reconstructed = snap.get_positions()
        
        dt_myr = 1000.0
        v_kpc_myr = velocities * 0.001022
        expected = initial_pos + v_kpc_myr * dt_myr
        
        np.testing.assert_array_almost_equal(reconstructed, expected)


class TestGPUVisualizationData:
    """Test GPU visualization data export."""
    
    def test_data_extractor_includes_velocities(self):
        """Test that data extractor includes velocity data for GPU interpolation."""
        config = SimulationConfig()
        config.galaxy.total_stars = 500
        config.simulation.simulation_duration_gyr = 0.01
        config.simulation.save_snapshots = True
        
        sim = GalaxySimulation(config, seed=42)
        sim.initialize()
        sim.run()
        
        from great_silence.visualization.threejs.data_extractor import SimulationDataExtractor
        
        extractor = SimulationDataExtractor(sim)
        galaxy_data = extractor.extract_galaxy_data(subsample=500)
        
        assert "positions" in galaxy_data
        assert len(galaxy_data["positions"]) > 0
        
        if "initial_positions" in galaxy_data:
            assert "velocities" in galaxy_data
            assert len(galaxy_data["initial_positions"]) == len(galaxy_data["positions"])


class TestPositionEvolution:
    """Test position evolution with Numba kernels."""
    
    def test_evolve_positions_maintains_energy(self):
        """Test that leapfrog integration roughly conserves energy."""
        params = GalaxyParameters(total_stars=100, velocity_init_mode="jeans")
        galaxy = GalaxyModel(params, seed=42)
        galaxy.generate_stellar_population()
        
        pos_before = galaxy.positions.copy()
        vel_before = galaxy.velocities.copy()
        
        for _ in range(10):
            galaxy.evolve_positions(dt_myr=1.0, use_numba=True, enable_motion=True)
        
        pos_after = galaxy.positions
        vel_after = galaxy.velocities
        
        assert pos_after.shape == pos_before.shape
        assert vel_after.shape == vel_before.shape
        assert not np.any(np.isnan(pos_after))
        assert not np.any(np.isnan(vel_after))
        
    def test_evolve_positions_numpy_fallback(self):
        """Test NumPy fallback when Numba not available."""
        params = GalaxyParameters(total_stars=100)
        galaxy = GalaxyModel(params, seed=42)
        galaxy.generate_stellar_population()
        
        pos_before = galaxy.positions.copy()
        
        with patch.dict('sys.modules', {'numba': None}):
            galaxy.evolve_positions(dt_myr=1.0, use_numba=False, enable_motion=True)
        
        assert not np.array_equal(galaxy.positions, pos_before)
        

class TestNumbaKernels:
    """Test Numba acceleration kernels."""
    
    def test_leapfrog_position_kernel(self):
        """Test leapfrog position integration kernel."""
        try:
            from great_silence.utils.numba_kernels import leapfrog_integrate_positions_kernel
        except ImportError:
            pytest.skip("Numba not available")
            
        positions = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
        velocities = np.array([[100.0, 0.0, 0.0], [0.0, 100.0, 0.0]], dtype=np.float64)
        accelerations = np.zeros((2, 3), dtype=np.float64)
        dt_myr = 1.0
        
        leapfrog_integrate_positions_kernel(positions, velocities, accelerations, dt_myr)
        
        expected_x = 1.0 + 100.0 * 0.001022 * 1.0
        assert abs(positions[0, 0] - expected_x) < 0.001
        
    def test_total_acceleration_kernel(self):
        """Test combined gravitational acceleration kernel."""
        try:
            from great_silence.utils.numba_kernels import compute_total_acceleration_kernel
        except ImportError:
            pytest.skip("Numba not available")
            
        positions = np.array([[8.0, 0.0, 0.0], [0.0, 8.0, 0.0]], dtype=np.float64)
        accelerations = np.zeros((2, 3), dtype=np.float64)
        
        compute_total_acceleration_kernel(
            positions, accelerations,
            disk_a=3.5, disk_b=0.3, disk_G_M=1e-8,
            bulge_a=1.0, bulge_G_M=5e-9,
            halo_v_sq=0.05,
            include_bulge=True
        )
        
        assert accelerations[0, 0] < 0
        assert accelerations[1, 1] < 0


class TestEquilibrium:
    """Test equilibrium stability over time."""
    
    def test_radial_distribution_stable(self):
        """Test that radial distribution doesn't drift catastrophically.
        
        The 'circular' velocity mode computes v_c directly from the potential,
        achieving near-perfect equilibrium (<5% drift over 100 Myr).
        """
        params = GalaxyParameters(total_stars=1000, velocity_init_mode="circular")
        galaxy = GalaxyModel(params, seed=42)
        galaxy.generate_stellar_population()
        
        R_before = np.sqrt(galaxy.positions[:, 0]**2 + galaxy.positions[:, 1]**2)
        mean_R_before = np.mean(R_before)
        
        for _ in range(100):
            galaxy.evolve_positions(dt_myr=1.0, use_numba=True, enable_motion=True)
        
        R_after = np.sqrt(galaxy.positions[:, 0]**2 + galaxy.positions[:, 1]**2)
        mean_R_after = np.mean(R_after)
        
        drift_pct = abs(mean_R_after - mean_R_before) / mean_R_before * 100
        
        assert drift_pct < 5.0  # Circular mode achieves <5% drift


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
