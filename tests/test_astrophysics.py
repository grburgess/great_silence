"""Unit tests for astrophysics hazard models."""

import numpy as np
import pytest


class TestNeutronStarMergerModel:
    """Test neutron star merger model."""

    def setup_method(self):
        """Create NS merger model with default parameters."""
        from great_silence.config.parameters import AstrophysicsParameters
        from great_silence.astrophysics.neutron_star_merger import NeutronStarMergerModel

        self.params = AstrophysicsParameters()
        self.model = NeutronStarMergerModel(self.params)
        self.rng = np.random.default_rng(42)

    def test_model_initialization(self):
        """Test model initializes with correct parameters."""
        assert self.model.merger_rate_per_myr == 50.0
        assert self.model.sgrb_beaming_angle_deg == 5.0
        assert self.model.sgrb_lethal_range_kpc == 3.0
        assert self.model.kilonova_lethal_range_pc == 30.0
        assert self.model.kilonova_sterilization_range_pc == 100.0

    def test_sample_merger_direction(self):
        """Test jet direction sampling is isotropic."""
        directions = []
        for _ in range(1000):
            d = self.model.sample_merger_direction(self.rng)
            directions.append(d)

        directions = np.array(directions)
        
        norms = np.linalg.norm(directions, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-10)
        
        mean_dir = np.mean(directions, axis=0)
        assert np.allclose(mean_dir, 0.0, atol=0.1)

    def test_delay_time_distribution(self):
        """Test delay time distribution is within bounds."""
        delays = []
        for _ in range(1000):
            delay = self.model.delay_time_distribution(self.rng)
            delays.append(delay)

        delays = np.array(delays)
        
        assert np.all(delays >= self.model.delay_time_min_gyr)
        assert np.all(delays <= self.model.delay_time_max_gyr)
        
        mean_delay = np.mean(delays)
        assert self.model.delay_time_min_gyr < mean_delay < self.model.delay_time_max_gyr

    def test_merger_probability_empty_stars(self):
        """Test merger probability with empty star arrays."""
        positions = np.empty((0, 3))
        masses = np.empty(0)
        ages = np.empty(0)
        civ_pos = np.array([8.0, 0.0, 0.0])

        p, info = self.model.merger_probability_per_timestep(
            positions, masses, ages, civ_pos, 1.0
        )

        assert p == 0.0
        assert info['n_ns_progenitors'] == 0

    def test_merger_probability_no_massive_stars(self):
        """Test merger probability with only low-mass stars."""
        n_stars = 100
        positions = self.rng.uniform(-10, 10, (n_stars, 3))
        masses = self.rng.uniform(0.5, 2.0, n_stars)  # All low mass
        ages = self.rng.uniform(0, 10, n_stars)
        civ_pos = np.array([0.0, 0.0, 0.0])

        p, info = self.model.merger_probability_per_timestep(
            positions, masses, ages, civ_pos, 1.0
        )

        assert p >= 0.0
        assert info['local_stellar_mass'] >= 0.0

    def test_merger_probability_with_progenitors(self):
        """Test merger probability with NS progenitors present."""
        positions = np.array([
            [0.0, 0.0, 0.0],
            [0.5, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        ])
        masses = np.array([20.0, 25.0, 30.0])  # Massive stars
        ages = np.array([5.0, 5.0, 5.0])  # Old enough to have evolved
        civ_pos = np.array([0.0, 0.0, 0.0])

        p, info = self.model.merger_probability_per_timestep(
            positions, masses, ages, civ_pos, 1.0
        )

        assert p >= 0.0
        assert info['local_stellar_mass'] > 0.0

    def test_evaluate_merger_effects_outside_range(self):
        """Test merger effects evaluation outside lethal range."""
        civ_pos = np.array([100.0, 0.0, 0.0])  # Far away
        merger_pos = np.array([0.0, 0.0, 0.0])

        destroyed, info = self.model.evaluate_merger_effects(
            civ_pos, merger_pos, self.rng
        )

        assert not destroyed
        assert not info['in_sgrb_beam']
        assert not info['in_kilonova_range']

    def test_evaluate_merger_effects_kilonova_range(self):
        """Test merger effects at kilonova lethal range."""
        civ_pos = np.array([0.01, 0.0, 0.0])  # 10 pc = 0.01 kpc
        merger_pos = np.array([0.0, 0.0, 0.0])

        destroyed_count = 0
        for _ in range(100):
            destroyed, info = self.model.evaluate_merger_effects(
                civ_pos, merger_pos, self.rng
            )
            if destroyed:
                destroyed_count += 1

        assert destroyed_count > 0

    def test_sample_merger_position_no_stars(self):
        """Test merger position sampling with no stars."""
        positions = np.empty((0, 3))
        masses = np.empty(0)
        ages = np.empty(0)
        center = np.array([0.0, 0.0, 0.0])

        result = self.model.sample_merger_position(
            positions, masses, ages, center, 5.0, self.rng
        )

        assert result is None

    def test_sample_merger_position_with_stars(self):
        """Test merger position sampling returns valid position."""
        n_stars = 50
        positions = self.rng.uniform(-5, 5, (n_stars, 3))
        masses = self.rng.uniform(1, 30, n_stars)
        ages = self.rng.uniform(0, 10, n_stars)
        center = np.array([0.0, 0.0, 0.0])

        pos = self.model.sample_merger_position(
            positions, masses, ages, center, 10.0, self.rng
        )

        assert pos is not None
        assert len(pos) == 3


class TestSupernovaModel:
    """Test supernova hazard model."""

    def setup_method(self):
        """Create SN model with default parameters."""
        from great_silence.config.parameters import AstrophysicsParameters
        from great_silence.astrophysics.supernovae import SupernovaModel

        self.params = AstrophysicsParameters()
        self.model = SupernovaModel(self.params)

    def test_model_initialization(self):
        """Test model uses config parameters."""
        assert self.model.params.sn_lethal_range_pc == 10.0
        assert self.model.params.sn_sterilization_range_pc == 30.0

    def test_will_go_supernova_low_mass(self):
        """Test low-mass stars don't go supernova."""
        result = self.model.will_go_supernova(
            stellar_mass=1.0,  # Solar mass
            stellar_age_gyr=10.0,
            dt_myr=1.0
        )
        assert not result

    def test_will_go_supernova_massive_young(self):
        """Test young massive stars don't go supernova immediately."""
        result = self.model.will_go_supernova(
            stellar_mass=20.0,
            stellar_age_gyr=0.001,  # Very young
            dt_myr=1.0
        )
        assert not result

    def test_will_go_supernova_massive_at_lifetime(self):
        """Test massive star goes supernova at end of main sequence."""
        mass = 20.0
        t_ms = 10.0 * mass ** (-2.5)
        
        result = self.model.will_go_supernova(
            stellar_mass=mass,
            stellar_age_gyr=t_ms - 0.0001,
            dt_myr=0.2
        )
        assert result

    def test_is_lethal_within_range(self):
        """Test lethal check within range."""
        assert self.model.is_lethal(5.0)  # 5 pc < 10 pc lethal

    def test_is_lethal_outside_range(self):
        """Test lethal check outside range."""
        assert not self.model.is_lethal(15.0)  # 15 pc > 10 pc lethal

    def test_sterilization_probability_lethal(self):
        """Test sterilization probability at lethal distance."""
        p = self.model.sterilization_probability(5.0)
        assert p == 1.0

    def test_sterilization_probability_decay(self):
        """Test sterilization probability decays with distance."""
        p_near = self.model.sterilization_probability(15.0)
        p_far = self.model.sterilization_probability(25.0)
        
        assert 0.0 < p_far < p_near < 1.0

    def test_sterilization_probability_outside_range(self):
        """Test sterilization probability is zero outside range."""
        p = self.model.sterilization_probability(50.0)
        assert p == 0.0

    def test_local_supernova_rate_no_massive(self):
        """Test local rate with no massive stars."""
        masses = np.array([0.5, 1.0, 1.5])
        ages = np.array([5.0, 5.0, 5.0])
        components = np.array([1, 1, 1])

        rate = self.model.local_supernova_rate(masses, ages, components, 0.1)
        assert rate == 0.0

    def test_local_supernova_rate_with_massive(self):
        """Test local rate with massive stars."""
        masses = np.array([0.5, 15.0, 25.0])
        ages = np.array([5.0, 0.01, 0.005])  # Near SN age
        components = np.array([1, 1, 1])

        rate = self.model.local_supernova_rate(masses, ages, components, 0.1)
        assert rate >= 0.0

    def test_metallicity_type_ratio_solar(self):
        """Test supernova type ratios at solar metallicity."""
        ratios = self.model.metallicity_type_ratio(0.0)
        
        assert 'Ia' in ratios
        assert 'II' in ratios
        assert 'PI' in ratios
        assert ratios['PI'] == 0.0  # No pair-instability at solar Z

    def test_metallicity_type_ratio_low_z(self):
        """Test supernova type ratios at very low metallicity."""
        ratios = self.model.metallicity_type_ratio(-2.5)
        
        assert ratios['PI'] == 1.0  # Pair-instability enabled at low Z


class TestGammaRayBurstModel:
    """Test gamma-ray burst hazard model."""

    def setup_method(self):
        """Create GRB model with default parameters."""
        from great_silence.config.parameters import AstrophysicsParameters
        from great_silence.astrophysics.grb import GammaRayBurstModel

        self.params = AstrophysicsParameters()
        self.model = GammaRayBurstModel(self.params)
        self.rng = np.random.default_rng(42)

    def test_model_initialization(self):
        """Test model uses config parameters."""
        assert self.model.params.grb_lethal_range_kpc == 5.0
        assert self.model.params.grb_beaming_angle_deg == 10.0

    def test_sample_grb_direction(self):
        """Test GRB direction sampling."""
        direction = self.model.sample_grb_direction(self.rng)
        
        assert len(direction) == 3
        assert np.isclose(np.linalg.norm(direction), 1.0)

    def test_is_in_beam_aligned(self):
        """Test beam check when aligned with jet."""
        grb_pos = np.array([0.0, 0.0, 0.0])
        grb_dir = np.array([1.0, 0.0, 0.0])  # Points along x-axis
        target_pos = np.array([1.0, 0.0, 0.0])  # Along x-axis

        result = self.model.is_in_beam(grb_pos, grb_dir, target_pos)
        assert result

    def test_is_in_beam_perpendicular(self):
        """Test beam check when perpendicular to jet."""
        grb_pos = np.array([0.0, 0.0, 0.0])
        grb_dir = np.array([1.0, 0.0, 0.0])  # Points along x-axis
        target_pos = np.array([0.0, 1.0, 0.0])  # Along y-axis (perpendicular)

        result = self.model.is_in_beam(grb_pos, grb_dir, target_pos)
        assert not result

    def test_lethal_distance(self):
        """Test lethal distance accessor."""
        distance = self.model.lethal_distance_kpc()
        assert distance == 5.0

    def test_metallicity_rate_modifier_solar(self):
        """Test rate modifier at solar metallicity."""
        modifier = self.model.metallicity_rate_modifier(0.0)
        assert modifier == pytest.approx(1.0)

    def test_metallicity_rate_modifier_metal_poor(self):
        """Test rate modifier increases for metal-poor."""
        modifier = self.model.metallicity_rate_modifier(-0.5)
        assert modifier > 1.0

    def test_metallicity_rate_modifier_metal_rich(self):
        """Test rate modifier decreases for metal-rich."""
        modifier = self.model.metallicity_rate_modifier(0.3)
        assert modifier < 1.0

    def test_grb_probability_low_mass(self):
        """Test GRB probability is zero for low-mass stars."""
        p = self.model.grb_probability_per_star(
            stellar_mass=5.0,  # Too low
            stellar_age_gyr=0.01,
            metallicity_feh=0.0,
            dt_myr=1.0
        )
        assert p == 0.0

    def test_grb_probability_massive_young(self):
        """Test GRB probability for young massive star."""
        p = self.model.grb_probability_per_star(
            stellar_mass=30.0,
            stellar_age_gyr=0.0001,  # Very young
            metallicity_feh=0.0,
            dt_myr=1.0
        )
        assert p == 0.0  # Not at end of life yet


class TestHazardEvaluator:
    """Test combined hazard evaluator."""

    def setup_method(self):
        """Create hazard evaluator."""
        from great_silence.config.parameters import AstrophysicsParameters
        from great_silence.astrophysics.hazards import HazardEvaluator

        self.params = AstrophysicsParameters()
        self.evaluator = HazardEvaluator(self.params, use_numba=True)
        self.rng = np.random.default_rng(42)
        
        n_stars = 100
        self.positions = self.rng.uniform(-10, 10, (n_stars, 3))
        self.masses = self.rng.exponential(1.0, n_stars)
        self.ages = self.rng.uniform(0, 13, n_stars)
        self.metallicities = self.rng.uniform(-1.0, 0.5, n_stars)
        self.component_types = self.rng.choice([0, 1], n_stars)

    def test_evaluator_initialization(self):
        """Test evaluator has all models."""
        assert self.evaluator.sn_model is not None
        assert self.evaluator.grb_model is not None
        assert self.evaluator.ns_merger_model is not None

    def test_evaluate_supernova_hazard(self):
        """Test supernova hazard evaluation returns expected format."""
        civ_pos = np.array([0.0, 0.0, 0.0])

        destroyed, info = self.evaluator.evaluate_supernova_hazard(
            civilization_position=civ_pos,
            stellar_positions=self.positions,
            stellar_masses=self.masses,
            stellar_ages=self.ages,
            component_types=self.component_types,
            dt_myr=1.0,
            rng=self.rng
        )

        assert isinstance(destroyed, bool)
        assert isinstance(info, dict)
        assert 'local_sn_rate' in info
        assert 'n_nearby_stars' in info

    def test_evaluate_grb_hazard(self):
        """Test GRB hazard evaluation returns expected format."""
        civ_pos = np.array([0.0, 0.0, 0.0])

        destroyed, info = self.evaluator.evaluate_grb_hazard(
            civilization_position=civ_pos,
            stellar_positions=self.positions,
            stellar_masses=self.masses,
            stellar_ages=self.ages,
            metallicities=self.metallicities,
            dt_myr=1.0,
            rng=self.rng
        )

        assert isinstance(destroyed, bool)
        assert isinstance(info, dict)
        assert 'n_grb_events' in info

    def test_evaluate_ns_merger_hazard(self):
        """Test NS merger hazard evaluation returns expected format."""
        civ_pos = np.array([0.0, 0.0, 0.0])

        destroyed, info = self.evaluator.evaluate_ns_merger_hazard(
            civilization_position=civ_pos,
            stellar_positions=self.positions,
            stellar_masses=self.masses,
            stellar_ages=self.ages,
            dt_myr=1.0,
            rng=self.rng
        )

        assert isinstance(destroyed, bool)
        assert isinstance(info, dict)
        assert 'local_merger_rate' in info
        assert 'n_merger_events' in info

    def test_evaluate_all_hazards(self):
        """Test combined hazard evaluation."""
        civ_pos = np.array([0.0, 0.0, 0.0])

        destroyed, hazard_type, info = self.evaluator.evaluate_all_hazards(
            civilization_position=civ_pos,
            stellar_positions=self.positions,
            stellar_masses=self.masses,
            stellar_ages=self.ages,
            metallicities=self.metallicities,
            component_types=self.component_types,
            dt_myr=1.0,
            rng=self.rng
        )

        assert isinstance(destroyed, bool)
        assert isinstance(hazard_type, str)
        assert isinstance(info, dict)
        assert 'sn_info' in info
        assert 'grb_info' in info
        assert 'ns_merger_info' in info

    def test_evaluate_all_hazards_types(self):
        """Test that hazard type is valid when destroyed."""
        civ_pos = np.array([0.0, 0.0, 0.0])
        
        valid_types = {'', 'supernova', 'grb', 'ns_merger'}
        
        for _ in range(10):
            destroyed, hazard_type, info = self.evaluator.evaluate_all_hazards(
                civilization_position=civ_pos,
                stellar_positions=self.positions,
                stellar_masses=self.masses,
                stellar_ages=self.ages,
                metallicities=self.metallicities,
                component_types=self.component_types,
                dt_myr=1.0,
                rng=self.rng
            )
            
            assert hazard_type in valid_types


class TestNumbaHazardKernels:
    """Test Numba-accelerated hazard kernels."""

    def setup_method(self):
        """Set up test data."""
        self.rng = np.random.default_rng(42)

    def test_ns_merger_hazard_kernel_import(self):
        """Test kernel imports successfully."""
        try:
            from great_silence.utils.numba_kernels import evaluate_ns_merger_hazard_kernel
            assert evaluate_ns_merger_hazard_kernel is not None
        except ImportError:
            pytest.skip("Numba not available")

    def test_ns_merger_hazard_kernel_survive(self):
        """Test NS merger kernel returns 0 for survival."""
        try:
            from great_silence.utils.numba_kernels import evaluate_ns_merger_hazard_kernel
        except ImportError:
            pytest.skip("Numba not available")

        civ_pos = np.array([100.0, 0.0, 0.0], dtype=np.float64)  # Far away
        merger_pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)

        result = evaluate_ns_merger_hazard_kernel(
            civ_pos, merger_pos,
            jet_theta=0.5, jet_phi=0.5,
            sgrb_beaming_angle_deg=5.0,
            sgrb_lethal_range_kpc=3.0,
            kilonova_lethal_range_pc=30.0,
            kilonova_sterilization_range_pc=100.0,
            random_val=0.9
        )

        assert result == 0  # Survived

    def test_ns_merger_hazard_kernel_kilonova(self):
        """Test NS merger kernel detects kilonova destruction."""
        try:
            from great_silence.utils.numba_kernels import evaluate_ns_merger_hazard_kernel
        except ImportError:
            pytest.skip("Numba not available")

        civ_pos = np.array([0.01, 0.0, 0.0], dtype=np.float64)  # 10 pc away
        merger_pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)

        result = evaluate_ns_merger_hazard_kernel(
            civ_pos, merger_pos,
            jet_theta=1.5, jet_phi=1.5,  # Jet pointing away
            sgrb_beaming_angle_deg=5.0,
            sgrb_lethal_range_kpc=3.0,
            kilonova_lethal_range_pc=30.0,
            kilonova_sterilization_range_pc=100.0,
            random_val=0.5
        )

        assert result == 2  # Destroyed by kilonova

    def test_batch_evaluate_hazards_kernel_import(self):
        """Test batch kernel imports successfully."""
        try:
            from great_silence.utils.numba_kernels import batch_evaluate_hazards_kernel
            assert batch_evaluate_hazards_kernel is not None
        except ImportError:
            pytest.skip("Numba not available")

    def test_batch_evaluate_hazards_kernel(self):
        """Test batch hazard evaluation kernel."""
        try:
            from great_silence.utils.numba_kernels import batch_evaluate_hazards_kernel
        except ImportError:
            pytest.skip("Numba not available")

        n_civs = 10
        n_stars = 100
        
        civ_positions = self.rng.uniform(-10, 10, (n_civs, 3)).astype(np.float64)
        stellar_positions = self.rng.uniform(-10, 10, (n_stars, 3)).astype(np.float64)
        stellar_masses = self.rng.exponential(1.0, n_stars).astype(np.float64)
        stellar_ages = self.rng.uniform(0, 13, n_stars).astype(np.float64)
        random_values = self.rng.uniform(0, 1, n_civs).astype(np.float64)

        results = batch_evaluate_hazards_kernel(
            civ_positions,
            stellar_positions,
            stellar_masses,
            stellar_ages,
            sn_lethal_range_pc=10.0,
            sn_sterilization_range_pc=30.0,
            dt_myr=1.0,
            random_values=random_values
        )

        assert len(results) == n_civs
        assert results.dtype == np.bool_


class TestHazardEventIntegration:
    """Test hazard events in simulation integration."""

    def setup_method(self):
        """Set up simulation test data."""
        from great_silence.simulation.engine import HazardEvent

        self.sn_event = HazardEvent(
            time_myr=100.0,
            event_type='supernova',
            position=np.array([5.0, 0.0, 0.0]),
            energy=1e51,
            sterilization_radius_pc=30.0,
            affected_civ_ids=[1]
        )

        self.grb_event = HazardEvent(
            time_myr=200.0,
            event_type='grb',
            position=np.array([10.0, 0.0, 0.0]),
            energy=1e54,
            sterilization_radius_pc=1000.0,
            affected_civ_ids=[2]
        )

        self.ns_merger_event = HazardEvent(
            time_myr=300.0,
            event_type='ns_merger',
            position=np.array([8.0, 2.0, -1.0]),
            energy=1e52,
            sterilization_radius_pc=100.0,
            affected_civ_ids=[3]
        )

    def test_hazard_event_types(self):
        """Test different hazard event types are tracked."""
        assert self.sn_event.event_type == 'supernova'
        assert self.grb_event.event_type == 'grb'
        assert self.ns_merger_event.event_type == 'ns_merger'

    def test_hazard_event_positions(self):
        """Test hazard event positions are arrays."""
        assert len(self.sn_event.position) == 3
        assert len(self.grb_event.position) == 3
        assert len(self.ns_merger_event.position) == 3

    def test_hazard_event_energies(self):
        """Test hazard event energies are physical."""
        assert self.sn_event.energy == pytest.approx(1e51)
        assert self.grb_event.energy == pytest.approx(1e54)
        assert self.ns_merger_event.energy == pytest.approx(1e52)

    def test_hazard_event_sterilization(self):
        """Test sterilization radii are set."""
        assert self.sn_event.sterilization_radius_pc == 30.0
        assert self.grb_event.sterilization_radius_pc == 1000.0
        assert self.ns_merger_event.sterilization_radius_pc == 100.0


class TestConfigParameters:
    """Test astrophysics configuration parameters."""

    def test_ns_merger_parameters_exist(self):
        """Test NS merger parameters are in config."""
        from great_silence.config.parameters import AstrophysicsParameters

        params = AstrophysicsParameters()
        
        assert hasattr(params, 'ns_merger_rate_per_myr')
        assert hasattr(params, 'ns_sgrb_beaming_angle_deg')
        assert hasattr(params, 'ns_sgrb_lethal_range_kpc')
        assert hasattr(params, 'ns_kilonova_lethal_range_pc')
        assert hasattr(params, 'ns_kilonova_sterilization_range_pc')

    def test_ns_merger_parameters_defaults(self):
        """Test NS merger parameter defaults are physical."""
        from great_silence.config.parameters import AstrophysicsParameters

        params = AstrophysicsParameters()
        
        assert 10.0 <= params.ns_merger_rate_per_myr <= 200.0
        assert 1.0 <= params.ns_sgrb_beaming_angle_deg <= 30.0
        assert 0.1 <= params.ns_sgrb_lethal_range_kpc <= 10.0
        assert 10.0 <= params.ns_kilonova_lethal_range_pc <= 100.0

    def test_supernova_parameters(self):
        """Test supernova parameters exist and have defaults."""
        from great_silence.config.parameters import AstrophysicsParameters

        params = AstrophysicsParameters()
        
        assert params.sn_lethal_range_pc == 10.0
        assert params.sn_sterilization_range_pc == 30.0
        assert params.sn_rate_per_century == 2.0

    def test_grb_parameters(self):
        """Test GRB parameters exist and have defaults."""
        from great_silence.config.parameters import AstrophysicsParameters

        params = AstrophysicsParameters()
        
        assert params.grb_lethal_range_kpc == 5.0
        assert params.grb_beaming_angle_deg == 10.0
        assert params.grb_rate_per_century == 0.01
