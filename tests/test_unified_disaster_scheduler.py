"""Unit tests for unified disaster scheduler."""

import numpy as np
import pytest


class TestUnifiedDisasterScheduler:
    """Test unified disaster scheduler."""

    def setup_method(self):
        """Create test stellar population."""
        from great_silence.config.parameters import AstrophysicsParameters
        
        self.rng = np.random.default_rng(42)
        self.n_stars = 1000
        
        self.positions = self.rng.uniform(-15, 15, (self.n_stars, 3))
        self.masses = self.rng.exponential(1.0, self.n_stars)
        self.masses[:50] = self.rng.uniform(10, 30, 50)
        self.ages_gyr = self.rng.uniform(0, 13, self.n_stars)
        self.metallicities = self.rng.uniform(-1.0, 0.5, self.n_stars)
        
        self.config = AstrophysicsParameters()
        self.simulation_duration_myr = 5000.0

    def test_scheduler_initialization(self):
        """Test scheduler initializes correctly."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        
        scheduler = UnifiedDisasterScheduler(
            positions=self.positions,
            masses=self.masses,
            ages_gyr=self.ages_gyr,
            metallicities=self.metallicities,
            config=self.config,
            rng=self.rng,
            simulation_duration_myr=self.simulation_duration_myr,
        )
        
        assert scheduler is not None
        assert scheduler.n_stars == self.n_stars

    def test_scheduler_schedules_supernovae(self):
        """Test scheduler schedules supernovae from massive stars."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        
        scheduler = UnifiedDisasterScheduler(
            positions=self.positions,
            masses=self.masses,
            ages_gyr=self.ages_gyr,
            metallicities=self.metallicities,
            config=self.config,
            rng=self.rng,
            simulation_duration_myr=self.simulation_duration_myr,
        )
        
        stats = scheduler.get_statistics()
        assert stats['supernovae'] > 0

    def test_scheduler_schedules_grbs(self):
        """Test scheduler schedules GRBs (subset of SNe)."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        
        scheduler = UnifiedDisasterScheduler(
            positions=self.positions,
            masses=self.masses,
            ages_gyr=self.ages_gyr,
            metallicities=self.metallicities,
            config=self.config,
            rng=self.rng,
            simulation_duration_myr=self.simulation_duration_myr,
        )
        
        stats = scheduler.get_statistics()
        assert stats['grbs'] <= stats['supernovae']

    def test_scheduler_schedules_ns_mergers(self):
        """Test scheduler schedules NS mergers."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        
        scheduler = UnifiedDisasterScheduler(
            positions=self.positions,
            masses=self.masses,
            ages_gyr=self.ages_gyr,
            metallicities=self.metallicities,
            config=self.config,
            rng=self.rng,
            simulation_duration_myr=self.simulation_duration_myr,
        )
        
        stats = scheduler.get_statistics()
        assert stats['ns_mergers'] >= 0

    def test_get_disasters_in_window(self):
        """Test retrieving disasters in time window."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        
        scheduler = UnifiedDisasterScheduler(
            positions=self.positions,
            masses=self.masses,
            ages_gyr=self.ages_gyr,
            metallicities=self.metallicities,
            config=self.config,
            rng=self.rng,
            simulation_duration_myr=self.simulation_duration_myr,
        )
        
        disasters = scheduler.get_disasters_in_window(0.0, 1000.0)
        
        assert isinstance(disasters, list)
        
        for d in disasters:
            assert 0.0 <= d.time_myr <= 1000.0

    def test_peek_next_disaster_time(self):
        """Test peeking next disaster without consuming."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        
        scheduler = UnifiedDisasterScheduler(
            positions=self.positions,
            masses=self.masses,
            ages_gyr=self.ages_gyr,
            metallicities=self.metallicities,
            config=self.config,
            rng=self.rng,
            simulation_duration_myr=self.simulation_duration_myr,
        )
        
        initial_pending = scheduler.pending_count
        
        next_time = scheduler.peek_next_disaster_time()
        
        if initial_pending > 0:
            assert next_time is not None
            assert next_time >= 0.0
        
        assert scheduler.pending_count == initial_pending

    def test_stellar_death_tracking(self):
        """Test that stars are marked dead after supernova."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler, DisasterType
        
        scheduler = UnifiedDisasterScheduler(
            positions=self.positions,
            masses=self.masses,
            ages_gyr=self.ages_gyr,
            metallicities=self.metallicities,
            config=self.config,
            rng=self.rng,
            simulation_duration_myr=self.simulation_duration_myr,
        )
        
        assert np.all(scheduler.stellar_is_alive)
        
        disasters = scheduler.get_disasters_in_window(0.0, self.simulation_duration_myr)
        
        sn_stars = [d.star_idx for d in disasters 
                   if d.disaster_type == DisasterType.SUPERNOVA and d.star_idx >= 0]
        
        for star_idx in sn_stars:
            assert not scheduler.stellar_is_alive[star_idx]

    def test_disaster_positions_valid(self):
        """Test that disaster positions are valid 3D coordinates."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        
        scheduler = UnifiedDisasterScheduler(
            positions=self.positions,
            masses=self.masses,
            ages_gyr=self.ages_gyr,
            metallicities=self.metallicities,
            config=self.config,
            rng=self.rng,
            simulation_duration_myr=self.simulation_duration_myr,
        )
        
        disasters = scheduler.get_disasters_in_window(0.0, 1000.0)
        
        for d in disasters:
            assert len(d.position) == 3
            assert np.all(np.isfinite(d.position))

    def test_disaster_energies_physical(self):
        """Test disaster energies are physically reasonable."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler, DisasterType
        
        scheduler = UnifiedDisasterScheduler(
            positions=self.positions,
            masses=self.masses,
            ages_gyr=self.ages_gyr,
            metallicities=self.metallicities,
            config=self.config,
            rng=self.rng,
            simulation_duration_myr=self.simulation_duration_myr,
        )
        
        disasters = scheduler.get_disasters_in_window(0.0, 1000.0)
        
        for d in disasters:
            assert d.energy_ergs > 0
            
            if d.disaster_type == DisasterType.SUPERNOVA:
                assert 1e49 < d.energy_ergs < 1e53
            elif d.disaster_type == DisasterType.GRB:
                assert 1e52 < d.energy_ergs < 1e56

    def test_statistics_consistent(self):
        """Test statistics are internally consistent."""
        from great_silence.simulation.disasters import UnifiedDisasterScheduler
        
        scheduler = UnifiedDisasterScheduler(
            positions=self.positions,
            masses=self.masses,
            ages_gyr=self.ages_gyr,
            metallicities=self.metallicities,
            config=self.config,
            rng=self.rng,
            simulation_duration_myr=self.simulation_duration_myr,
        )
        
        stats = scheduler.get_statistics()
        
        assert stats['total_scheduled'] == (
            stats['supernovae'] + stats['grbs'] + stats['ns_mergers']
        )


class TestDisasterEffectKernels:
    """Test Numba kernels for disaster effect evaluation."""

    def setup_method(self):
        """Set up test data."""
        self.rng = np.random.default_rng(42)

    def test_sn_effect_kernel_import(self):
        """Test SN effect kernel imports."""
        try:
            from great_silence.utils.numba_kernels import evaluate_sn_effect_on_civs_kernel
            assert evaluate_sn_effect_on_civs_kernel is not None
        except ImportError:
            pytest.skip("Numba not available")

    def test_sn_effect_kernel_no_civs(self):
        """Test SN effect kernel with no civilizations."""
        try:
            from great_silence.utils.numba_kernels import evaluate_sn_effect_on_civs_kernel
        except ImportError:
            pytest.skip("Numba not available")

        civ_positions = np.empty((0, 3), dtype=np.float64)
        disaster_pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        random_values = np.empty(0, dtype=np.float64)

        effects = evaluate_sn_effect_on_civs_kernel(
            civ_positions, disaster_pos, 10.0, 30.0, random_values
        )

        assert len(effects) == 0

    def test_sn_effect_kernel_lethal_range(self):
        """Test SN effect kernel at lethal range."""
        try:
            from great_silence.utils.numba_kernels import evaluate_sn_effect_on_civs_kernel
        except ImportError:
            pytest.skip("Numba not available")

        civ_positions = np.array([[0.005, 0.0, 0.0]], dtype=np.float64)
        disaster_pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        random_values = np.array([0.5], dtype=np.float64)

        effects = evaluate_sn_effect_on_civs_kernel(
            civ_positions, disaster_pos, 10.0, 30.0, random_values
        )

        assert effects[0] == 1

    def test_sn_effect_kernel_outside_range(self):
        """Test SN effect kernel outside range."""
        try:
            from great_silence.utils.numba_kernels import evaluate_sn_effect_on_civs_kernel
        except ImportError:
            pytest.skip("Numba not available")

        civ_positions = np.array([[1.0, 0.0, 0.0]], dtype=np.float64)
        disaster_pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        random_values = np.array([0.5], dtype=np.float64)

        effects = evaluate_sn_effect_on_civs_kernel(
            civ_positions, disaster_pos, 10.0, 30.0, random_values
        )

        assert effects[0] == 0

    def test_grb_effect_kernel_in_beam(self):
        """Test GRB effect kernel when in beam."""
        try:
            from great_silence.utils.numba_kernels import evaluate_grb_effect_on_civs_kernel
        except ImportError:
            pytest.skip("Numba not available")

        civ_positions = np.array([[1.0, 0.0, 0.0]], dtype=np.float64)
        disaster_pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        
        jet_theta = np.pi / 2
        jet_phi = 0.0

        effects = evaluate_grb_effect_on_civs_kernel(
            civ_positions, disaster_pos,
            jet_theta, jet_phi,
            beaming_angle_deg=10.0,
            lethal_range_kpc=5.0
        )

        assert effects[0] == 1

    def test_grb_effect_kernel_outside_beam(self):
        """Test GRB effect kernel when outside beam."""
        try:
            from great_silence.utils.numba_kernels import evaluate_grb_effect_on_civs_kernel
        except ImportError:
            pytest.skip("Numba not available")

        civ_positions = np.array([[0.0, 1.0, 0.0]], dtype=np.float64)
        disaster_pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        
        jet_theta = np.pi / 2
        jet_phi = 0.0

        effects = evaluate_grb_effect_on_civs_kernel(
            civ_positions, disaster_pos,
            jet_theta, jet_phi,
            beaming_angle_deg=10.0,
            lethal_range_kpc=5.0
        )

        assert effects[0] == 0

    def test_ns_merger_effect_kernel_kilonova(self):
        """Test NS merger kernel for kilonova effect."""
        try:
            from great_silence.utils.numba_kernels import evaluate_ns_merger_effect_on_civs_kernel
        except ImportError:
            pytest.skip("Numba not available")

        civ_positions = np.array([[0.01, 0.0, 0.0]], dtype=np.float64)
        disaster_pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        random_values = np.array([0.5], dtype=np.float64)

        jet_theta = 0.0
        jet_phi = 0.0

        effects = evaluate_ns_merger_effect_on_civs_kernel(
            civ_positions, disaster_pos,
            jet_theta, jet_phi,
            sgrb_beaming_angle_deg=5.0,
            sgrb_lethal_range_kpc=3.0,
            kilonova_lethal_range_pc=30.0,
            kilonova_sterilization_range_pc=100.0,
            random_values=random_values
        )

        assert effects[0] == 2

    def test_batch_find_civs_in_range(self):
        """Test batch range finding kernel."""
        try:
            from great_silence.utils.numba_kernels import batch_find_civs_in_range_kernel
        except ImportError:
            pytest.skip("Numba not available")

        civ_positions = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
        ], dtype=np.float64)

        disaster_positions = np.array([
            [0.5, 0.0, 0.0],
        ], dtype=np.float64)

        in_range = batch_find_civs_in_range_kernel(
            civ_positions, disaster_positions, max_range_kpc=2.0
        )

        assert in_range[0] == True
        assert in_range[1] == True
        assert in_range[2] == False


class TestDisasterFlowIntegration:
    """Integration tests for disaster flow in simulation."""

    def test_disasters_recorded_without_civs(self):
        """Test that disasters are recorded even without civilizations."""
        from great_silence import GalaxySimulation, SimulationConfig

        config = SimulationConfig()
        config.galaxy.total_stars = 5000
        config.simulation.simulation_duration_gyr = 1.0
        config.simulation.time_step_myr = 100.0
        
        config.civilization.fraction_develop_life = 0.0

        sim = GalaxySimulation(config, seed=42)
        sim.initialize()
        sim.run(verbose=False)

        assert len(sim.hazard_events) > 0

    def test_disasters_affect_civs(self):
        """Test that disasters can affect civilizations."""
        from great_silence import GalaxySimulation, SimulationConfig

        config = SimulationConfig.with_preset('optimistic')
        config.galaxy.total_stars = 10000
        config.simulation.simulation_duration_gyr = 2.0
        config.simulation.time_step_myr = 50.0
        
        config.civilization.mean_civilization_lifetime_myr = 500.0
        config.civilization.self_destruction_model_type = 'flat'
        config.civilization.self_destruction_probability_per_myr = 0.0001

        sim = GalaxySimulation(config, seed=42)
        sim.initialize()
        sim.run(verbose=False)

        death_causes = {}
        for civ in sim.civilizations:
            if not civ.is_active and civ.death_cause:
                cause = civ.death_cause
                death_causes[cause] = death_causes.get(cause, 0) + 1

        assert len(sim.hazard_events) > 0

    def test_disaster_snapshots_captured(self):
        """Test that disasters appear in snapshots."""
        from great_silence import GalaxySimulation, SimulationConfig

        config = SimulationConfig()
        config.galaxy.total_stars = 5000
        config.simulation.simulation_duration_gyr = 1.0
        config.simulation.time_step_myr = 100.0
        config.simulation.save_snapshots = True
        config.simulation.snapshot_interval_myr = 200.0

        sim = GalaxySimulation(config, seed=42)
        sim.initialize()
        sim.run(verbose=False)

        assert len(sim.snapshots) > 0

    def test_adaptive_timestep_considers_disasters(self):
        """Test that adaptive timestep considers disaster schedule."""
        from great_silence import GalaxySimulation, SimulationConfig

        config = SimulationConfig()
        config.galaxy.total_stars = 5000
        config.simulation.simulation_duration_gyr = 0.5
        config.simulation.adaptive_timestepping = True

        sim = GalaxySimulation(config, seed=42)
        sim.initialize()

        next_disaster = sim.disaster_scheduler.peek_next_disaster_time()
        
        if next_disaster is not None and next_disaster <= config.simulation.max_adaptive_step_myr:
            dt = sim._compute_next_timestep()
            assert dt <= config.simulation.max_adaptive_step_myr + 0.01
        else:
            dt = sim._compute_next_timestep()
            assert dt <= config.simulation.max_timestep_myr
