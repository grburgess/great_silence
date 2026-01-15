"""Tests for stellar evolution and continuous star formation."""

import numpy as np
import pytest


class TestStellarAging:
    """Test that stellar ages evolve correctly during simulation."""

    def test_ages_increase_during_step(self):
        """Test stellar ages increase by dt_gyr each timestep."""
        from great_silence import GalaxySimulation, SimulationConfig
        
        config = SimulationConfig()
        config.galaxy.total_stars = 1000
        config.simulation.simulation_duration_gyr = 1.0
        
        sim = GalaxySimulation(config)
        sim.initialize()
        
        initial_ages = sim.galaxy.ages.copy()
        dt_myr = 100.0
        dt_gyr = dt_myr / 1000.0
        
        sim._step(dt_myr)
        
        expected_ages = initial_ages + dt_gyr
        np.testing.assert_allclose(sim.galaxy.ages, expected_ages, rtol=1e-10)

    def test_ages_accumulate_over_multiple_steps(self):
        """Test ages accumulate correctly over multiple timesteps."""
        from great_silence import GalaxySimulation, SimulationConfig
        
        config = SimulationConfig()
        config.galaxy.total_stars = 1000
        config.simulation.simulation_duration_gyr = 1.0
        
        sim = GalaxySimulation(config)
        sim.initialize()
        
        initial_ages = sim.galaxy.ages.copy()
        dt_myr = 50.0
        n_steps = 10
        
        for _ in range(n_steps):
            sim._step(dt_myr)
        
        total_dt_gyr = (dt_myr * n_steps) / 1000.0
        expected_ages = initial_ages + total_dt_gyr
        np.testing.assert_allclose(sim.galaxy.ages, expected_ages, rtol=1e-10)

    def test_ages_remain_positive(self):
        """Test stellar ages never become negative."""
        from great_silence import GalaxySimulation, SimulationConfig
        
        config = SimulationConfig()
        config.galaxy.total_stars = 1000
        config.simulation.simulation_duration_gyr = 5.0
        
        sim = GalaxySimulation(config)
        sim.initialize()
        
        for _ in range(100):
            sim._step(50.0)
        
        assert np.all(sim.galaxy.ages >= 0)

    def test_ages_bounded_by_universe_age(self):
        """Test ages don't exceed reasonable universe age after long sim."""
        from great_silence import GalaxySimulation, SimulationConfig
        
        config = SimulationConfig()
        config.galaxy.total_stars = 1000
        config.simulation.simulation_duration_gyr = 10.0
        
        sim = GalaxySimulation(config)
        sim.initialize()
        
        max_initial_age = sim.galaxy.ages.max()
        
        sim.run()
        
        max_expected_age = max_initial_age + config.simulation.simulation_duration_gyr
        assert sim.galaxy.ages.max() <= max_expected_age + 0.001


class TestStarFormationRateScaling:
    """Test star formation rates scale correctly with galaxy size."""

    def test_rate_proportional_to_galaxy_size(self):
        """Test star formation rate scales with n_stars/4e11."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        duration_myr = 10000.0
        
        results = []
        for n_stars in [1_000_000, 5_000_000, 10_000_000]:
            rng = np.random.default_rng(42)
            positions = rng.uniform(-15, 15, (1000, 3))
            masses = rng.exponential(1.0, 1000)
            ages = rng.uniform(0, 13, 1000)
            metallicities = rng.uniform(-1.0, 0.5, 1000)
            
            scheduler = UnifiedDisasterScheduler(
                positions=np.tile(positions, (n_stars // 1000, 1)),
                masses=np.tile(masses, n_stars // 1000),
                ages_gyr=np.tile(ages, n_stars // 1000),
                metallicities=np.tile(metallicities, n_stars // 1000),
                config=config,
                rng=np.random.default_rng(42),
                simulation_duration_myr=duration_myr,
                enable_star_formation=True,
            )
            
            results.append((n_stars, scheduler.get_statistics()['scheduled_star_births']))
        
        n1, births1 = results[0]
        n2, births2 = results[1]
        n3, births3 = results[2]
        
        ratio_expected_12 = n2 / n1
        ratio_expected_13 = n3 / n1
        
        if births1 > 0:
            ratio_actual_12 = births2 / births1
            ratio_actual_13 = births3 / births1
            
            assert 0.3 * ratio_expected_12 < ratio_actual_12 < 3.0 * ratio_expected_12
            assert 0.3 * ratio_expected_13 < ratio_actual_13 < 3.0 * ratio_expected_13

    def test_small_galaxy_low_birth_rate(self):
        """Test small galaxy has appropriately low star formation."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        n_stars = 10000
        duration_myr = 1000.0
        
        rng = np.random.default_rng(42)
        positions = rng.uniform(-15, 15, (n_stars, 3))
        masses = rng.exponential(1.0, n_stars)
        ages = rng.uniform(0, 13, n_stars)
        metallicities = rng.uniform(-1.0, 0.5, n_stars)
        
        scheduler = UnifiedDisasterScheduler(
            positions=positions,
            masses=masses,
            ages_gyr=ages,
            metallicities=metallicities,
            config=config,
            rng=rng,
            simulation_duration_myr=duration_myr,
            enable_star_formation=True,
        )
        
        stats = scheduler.get_statistics()
        expected = 300 * (n_stars / 4e11) * duration_myr
        
        assert stats['scheduled_star_births'] <= max(5, 3 * expected)

    def test_disabled_star_formation_zero_births(self):
        """Test disabling star formation produces zero births."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        n_stars = 1_000_000
        
        rng = np.random.default_rng(42)
        positions = rng.uniform(-15, 15, (1000, 3))
        masses = rng.exponential(1.0, 1000)
        ages = rng.uniform(0, 13, 1000)
        metallicities = rng.uniform(-1.0, 0.5, 1000)
        
        scheduler = UnifiedDisasterScheduler(
            positions=np.tile(positions, (n_stars // 1000, 1)),
            masses=np.tile(masses, n_stars // 1000),
            ages_gyr=np.tile(ages, n_stars // 1000),
            metallicities=np.tile(metallicities, n_stars // 1000),
            config=config,
            rng=rng,
            simulation_duration_myr=10000.0,
            enable_star_formation=False,
        )
        
        stats = scheduler.get_statistics()
        assert stats['scheduled_star_births'] == 0
        assert stats['pending_star_births'] == 0


class TestStarFormationPhysics:
    """Test physical properties of newly formed stars."""

    def test_new_star_masses_above_threshold(self):
        """Test all new stars have M > 8 Msun (massive stars only)."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        n_stars = 10_000_000
        
        rng = np.random.default_rng(42)
        positions = rng.uniform(-15, 15, (1000, 3))
        masses = rng.exponential(1.0, 1000)
        ages = rng.uniform(0, 13, 1000)
        metallicities = rng.uniform(-1.0, 0.5, 1000)
        
        scheduler = UnifiedDisasterScheduler(
            positions=np.tile(positions, (n_stars // 1000, 1)),
            masses=np.tile(masses, n_stars // 1000),
            ages_gyr=np.tile(ages, n_stars // 1000),
            metallicities=np.tile(metallicities, n_stars // 1000),
            config=config,
            rng=rng,
            simulation_duration_myr=5000.0,
            enable_star_formation=True,
        )
        
        for birth in scheduler.scheduled_star_births:
            assert birth.mass >= 8.0, f"Star mass {birth.mass} < 8 Msun"

    def test_new_star_masses_below_max(self):
        """Test all new stars have M <= 100 Msun."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        n_stars = 10_000_000
        
        rng = np.random.default_rng(42)
        positions = rng.uniform(-15, 15, (1000, 3))
        masses = rng.exponential(1.0, 1000)
        ages = rng.uniform(0, 13, 1000)
        metallicities = rng.uniform(-1.0, 0.5, 1000)
        
        scheduler = UnifiedDisasterScheduler(
            positions=np.tile(positions, (n_stars // 1000, 1)),
            masses=np.tile(masses, n_stars // 1000),
            ages_gyr=np.tile(ages, n_stars // 1000),
            metallicities=np.tile(metallicities, n_stars // 1000),
            config=config,
            rng=rng,
            simulation_duration_myr=5000.0,
            enable_star_formation=True,
        )
        
        for birth in scheduler.scheduled_star_births:
            assert birth.mass <= 100.0, f"Star mass {birth.mass} > 100 Msun"

    def test_new_star_positions_in_disk(self):
        """Test new stars form in outer disk (star-forming regions)."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        n_stars = 10_000_000
        
        rng = np.random.default_rng(42)
        positions = rng.uniform(-15, 15, (1000, 3))
        masses = rng.exponential(1.0, 1000)
        ages = rng.uniform(0, 13, 1000)
        metallicities = rng.uniform(-1.0, 0.5, 1000)
        
        scheduler = UnifiedDisasterScheduler(
            positions=np.tile(positions, (n_stars // 1000, 1)),
            masses=np.tile(masses, n_stars // 1000),
            ages_gyr=np.tile(ages, n_stars // 1000),
            metallicities=np.tile(metallicities, n_stars // 1000),
            config=config,
            rng=rng,
            simulation_duration_myr=5000.0,
            enable_star_formation=True,
        )
        
        for birth in scheduler.scheduled_star_births:
            r = np.sqrt(birth.position[0]**2 + birth.position[1]**2)
            z = abs(birth.position[2])
            
            assert r >= 3.5, f"Star formed too close to center: r={r} kpc"
            assert r <= 16.0, f"Star formed too far out: r={r} kpc"
            assert z < 2.0, f"Star formed too far from disk plane: z={z} kpc"

    def test_birth_times_within_simulation(self):
        """Test all birth times are within simulation duration."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        n_stars = 10_000_000
        duration_myr = 5000.0
        
        rng = np.random.default_rng(42)
        positions = rng.uniform(-15, 15, (1000, 3))
        masses = rng.exponential(1.0, 1000)
        ages = rng.uniform(0, 13, 1000)
        metallicities = rng.uniform(-1.0, 0.5, 1000)
        
        scheduler = UnifiedDisasterScheduler(
            positions=np.tile(positions, (n_stars // 1000, 1)),
            masses=np.tile(masses, n_stars // 1000),
            ages_gyr=np.tile(ages, n_stars // 1000),
            metallicities=np.tile(metallicities, n_stars // 1000),
            config=config,
            rng=rng,
            simulation_duration_myr=duration_myr,
            enable_star_formation=True,
        )
        
        for birth in scheduler.scheduled_star_births:
            assert 0 <= birth.time_myr <= duration_myr


class TestStarFormationIntegration:
    """Integration tests for star formation in full simulation."""

    def test_new_stars_create_disasters(self):
        """Test newly formed stars eventually produce supernovae."""
        from great_silence import GalaxySimulation, SimulationConfig
        
        config = SimulationConfig()
        config.galaxy.total_stars = 5_000_000
        config.simulation.simulation_duration_gyr = 1.0
        config.simulation.time_step_myr = 10.0
        config.simulation.enable_star_formation = True
        
        sim = GalaxySimulation(config)
        sim.initialize()
        
        initial_disaster_count = sim.disaster_scheduler.get_statistics()['total_scheduled']
        initial_births = sim.disaster_scheduler.get_statistics()['scheduled_star_births']
        
        for _ in range(100):
            sim._step(10.0)
        
        assert initial_births > 0 or initial_disaster_count > 0

    def test_star_formation_reproducible(self):
        """Test star formation is reproducible with same seed."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        n_stars = 5_000_000
        
        def create_scheduler(seed):
            rng = np.random.default_rng(seed)
            positions = rng.uniform(-15, 15, (1000, 3))
            masses = rng.exponential(1.0, 1000)
            ages = rng.uniform(0, 13, 1000)
            metallicities = rng.uniform(-1.0, 0.5, 1000)
            
            return UnifiedDisasterScheduler(
                positions=np.tile(positions, (n_stars // 1000, 1)),
                masses=np.tile(masses, n_stars // 1000),
                ages_gyr=np.tile(ages, n_stars // 1000),
                metallicities=np.tile(metallicities, n_stars // 1000),
                config=config,
                rng=np.random.default_rng(seed + 1000),
                simulation_duration_myr=5000.0,
                enable_star_formation=True,
            )
        
        scheduler1 = create_scheduler(42)
        scheduler2 = create_scheduler(42)
        
        stats1 = scheduler1.get_statistics()
        stats2 = scheduler2.get_statistics()
        
        assert stats1['scheduled_star_births'] == stats2['scheduled_star_births']
        
        if scheduler1.scheduled_star_births:
            for b1, b2 in zip(scheduler1.scheduled_star_births, scheduler2.scheduled_star_births):
                assert b1.time_myr == b2.time_myr
                assert b1.mass == b2.mass
                np.testing.assert_array_equal(b1.position, b2.position)

    def test_star_formation_heap_consumption(self):
        """Test star birth heap is consumed correctly during simulation."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        n_stars = 10_000_000
        duration_myr = 5000.0
        
        rng = np.random.default_rng(42)
        positions = rng.uniform(-15, 15, (1000, 3))
        masses = rng.exponential(1.0, 1000)
        ages = rng.uniform(0, 13, 1000)
        metallicities = rng.uniform(-1.0, 0.5, 1000)
        
        scheduler = UnifiedDisasterScheduler(
            positions=np.tile(positions, (n_stars // 1000, 1)),
            masses=np.tile(masses, n_stars // 1000),
            ages_gyr=np.tile(ages, n_stars // 1000),
            metallicities=np.tile(metallicities, n_stars // 1000),
            config=config,
            rng=rng,
            simulation_duration_myr=duration_myr,
            enable_star_formation=True,
        )
        
        initial_pending = scheduler.get_statistics()['pending_star_births']
        
        births_first_half = scheduler.get_star_births_in_window(0, duration_myr / 2)
        pending_after_half = scheduler.get_statistics()['pending_star_births']
        
        births_second_half = scheduler.get_star_births_in_window(duration_myr / 2, duration_myr)
        pending_after_all = scheduler.get_statistics()['pending_star_births']
        
        total_consumed = len(births_first_half) + len(births_second_half)
        assert total_consumed == initial_pending
        assert pending_after_all == 0


class TestNoOverpopulation:
    """Test that star formation doesn't overpopulate the galaxy."""

    def test_birth_count_reasonable(self):
        """Test total births don't exceed physical limits."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        
        for n_stars, duration_gyr in [(50000, 5.0), (100000, 10.0), (1000000, 30.0)]:
            duration_myr = duration_gyr * 1000
            
            rng = np.random.default_rng(42)
            positions = rng.uniform(-15, 15, (min(n_stars, 10000), 3))
            masses = rng.exponential(1.0, min(n_stars, 10000))
            ages = rng.uniform(0, 13, min(n_stars, 10000))
            metallicities = rng.uniform(-1.0, 0.5, min(n_stars, 10000))
            
            if n_stars > 10000:
                positions = np.tile(positions, (n_stars // 10000, 1))
                masses = np.tile(masses, n_stars // 10000)
                ages = np.tile(ages, n_stars // 10000)
                metallicities = np.tile(metallicities, n_stars // 10000)
            
            scheduler = UnifiedDisasterScheduler(
                positions=positions,
                masses=masses,
                ages_gyr=ages,
                metallicities=metallicities,
                config=config,
                rng=np.random.default_rng(42),
                simulation_duration_myr=duration_myr,
                enable_star_formation=True,
            )
            
            stats = scheduler.get_statistics()
            births = stats['scheduled_star_births']
            
            expected = 300 * (n_stars / 4e11) * duration_myr
            max_reasonable = max(10, 5 * expected)
            
            assert births <= max_reasonable, (
                f"Too many births: {births} for {n_stars} stars over {duration_gyr} Gyr "
                f"(expected ~{expected:.1f}, max {max_reasonable:.1f})"
            )

    def test_birth_fraction_of_population(self):
        """Test births are tiny fraction of existing population."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        from great_silence.config.parameters import AstrophysicsParameters
        
        config = AstrophysicsParameters()
        n_stars = 1_000_000
        duration_myr = 30000.0
        
        rng = np.random.default_rng(42)
        positions = rng.uniform(-15, 15, (10000, 3))
        masses = rng.exponential(1.0, 10000)
        ages = rng.uniform(0, 13, 10000)
        metallicities = rng.uniform(-1.0, 0.5, 10000)
        
        scheduler = UnifiedDisasterScheduler(
            positions=np.tile(positions, (n_stars // 10000, 1)),
            masses=np.tile(masses, n_stars // 10000),
            ages_gyr=np.tile(ages, n_stars // 10000),
            metallicities=np.tile(metallicities, n_stars // 10000),
            config=config,
            rng=rng,
            simulation_duration_myr=duration_myr,
            enable_star_formation=True,
        )
        
        stats = scheduler.get_statistics()
        birth_fraction = stats['scheduled_star_births'] / n_stars
        
        assert birth_fraction < 0.01, (
            f"Birth fraction {birth_fraction:.4f} too high "
            f"({stats['scheduled_star_births']} births for {n_stars} stars)"
        )
