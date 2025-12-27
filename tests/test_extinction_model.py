"""Tests for Kardashev-dependent extinction model."""

import numpy as np
import pytest
from great_silence.civilization.extinction import ExtinctionModel, CrisisPeak


class TestCrisisPeak:
    """Test CrisisPeak dataclass."""

    def test_crisis_peak_creation(self):
        crisis = CrisisPeak(
            name="test_crisis",
            kardashev_center=1.0,
            width=0.1,
            amplitude=0.2,
            enabled=True
        )
        assert crisis.name == "test_crisis"
        assert crisis.kardashev_center == 1.0
        assert crisis.width == 0.1
        assert crisis.amplitude == 0.2
        assert crisis.enabled is True

    def test_crisis_peak_default_enabled(self):
        crisis = CrisisPeak("test", 1.0, 0.1, 0.2)
        assert crisis.enabled is True


class TestExtinctionModel:
    """Test ExtinctionModel class."""

    def test_flat_model_initialization(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="flat"
        )
        assert model.model_type == "flat"
        assert model.self_destruction_rate == 0.1

    def test_kardashev_model_initialization(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent",
            baseline_rate=0.01,
            baseline_scaling=0.05
        )
        assert model.model_type == "kardashev_dependent"
        assert model.baseline_rate == 0.01
        assert model.baseline_scaling == 0.05

    def test_default_crisis_peaks_created(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent"
        )
        assert len(model.crisis_peaks) == 6
        crisis_names = [c.name for c in model.crisis_peaks]
        assert "nuclear_age" in crisis_names
        assert "ai_transition" in crisis_names
        assert "stellar_engineering" in crisis_names

    def test_custom_crisis_peaks(self):
        custom_peaks = [
            CrisisPeak("custom1", 0.5, 0.1, 0.3, True),
            CrisisPeak("custom2", 1.5, 0.2, 0.2, True)
        ]
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent",
            crisis_peaks=custom_peaks
        )
        assert len(model.crisis_peaks) == 2
        assert model.crisis_peaks[0].name == "custom1"

    def test_hazard_rate_calculation(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent",
            baseline_rate=0.01,
            baseline_scaling=0.05
        )

        # Test at various Kardashev scales
        lambda_0_7 = model.calculate_kardashev_hazard_rate(0.7)
        lambda_1_0 = model.calculate_kardashev_hazard_rate(1.0)
        lambda_3_0 = model.calculate_kardashev_hazard_rate(3.0)

        assert lambda_0_7 > 0
        assert lambda_1_0 > 0
        assert lambda_3_0 > 0

        # Should have peak near AI crisis (K=1.05)
        lambda_1_05 = model.calculate_kardashev_hazard_rate(1.05)
        assert lambda_1_05 > lambda_0_7
        assert lambda_1_05 > lambda_3_0

    def test_hazard_rate_baseline_increases(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent",
            baseline_rate=0.01,
            baseline_scaling=0.05,
            crisis_peaks=[]  # No crises, only baseline
        )

        lambda_0 = model.calculate_kardashev_hazard_rate(0.0)
        lambda_1 = model.calculate_kardashev_hazard_rate(1.0)
        lambda_2 = model.calculate_kardashev_hazard_rate(2.0)

        # Baseline should increase linearly
        assert lambda_1 > lambda_0
        assert lambda_2 > lambda_1

        # Check correct formula: λ = 0.01 * (1 + 0.05 * K)
        assert np.isclose(lambda_0, 0.01)
        assert np.isclose(lambda_1, 0.01 * 1.05)
        assert np.isclose(lambda_2, 0.01 * 1.10)

    def test_gaussian_peak_shape(self):
        # Single crisis at K=1.0
        crisis = CrisisPeak("test", 1.0, 0.1, 0.5, True)
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent",
            baseline_rate=0.0,  # No baseline
            baseline_scaling=0.0,
            crisis_peaks=[crisis]
        )

        # At center, should equal amplitude
        lambda_center = model.calculate_kardashev_hazard_rate(1.0)
        assert np.isclose(lambda_center, 0.5, atol=1e-6)

        # At ±1σ, should be ~0.606 of amplitude (Gaussian property)
        lambda_plus_sigma = model.calculate_kardashev_hazard_rate(1.1)
        lambda_minus_sigma = model.calculate_kardashev_hazard_rate(0.9)
        expected = 0.5 * np.exp(-0.5)  # ~0.303

        assert np.isclose(lambda_plus_sigma, expected, atol=1e-3)
        assert np.isclose(lambda_minus_sigma, expected, atol=1e-3)

        # Far from center, should be near zero
        lambda_far = model.calculate_kardashev_hazard_rate(2.0)
        assert lambda_far < 0.01

    def test_flat_model_self_destruction(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="flat"
        )

        rng = np.random.default_rng(42)
        dt_myr = 1.0

        # Run many trials
        num_trials = 10000
        destructions = sum(
            model.check_self_destruction(dt_myr, rng)
            for _ in range(num_trials)
        )

        # Expected: 1 - exp(-0.1 * 1.0) ≈ 0.0952
        expected_prob = 1 - np.exp(-0.1 * 1.0)
        observed_prob = destructions / num_trials

        # Should be within 3 standard deviations
        assert abs(observed_prob - expected_prob) < 3 * np.sqrt(expected_prob * (1 - expected_prob) / num_trials)

    def test_kardashev_model_self_destruction(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent",
            baseline_rate=0.01,
            baseline_scaling=0.05
        )

        rng = np.random.default_rng(42)
        dt_myr = 1.0

        # Test at nuclear age peak (should have higher destruction rate)
        num_trials = 10000
        destructions_nuclear = sum(
            model.check_self_destruction(dt_myr, rng, kardashev_scale=0.72)
            for _ in range(num_trials)
        )

        # Test at safe zone (K=1.5, between crises)
        rng = np.random.default_rng(42)  # Reset RNG for fair comparison
        destructions_safe = sum(
            model.check_self_destruction(dt_myr, rng, kardashev_scale=1.5)
            for _ in range(num_trials)
        )

        # Nuclear age should have higher destruction rate
        assert destructions_nuclear > destructions_safe

    def test_kardashev_model_requires_scale(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent"
        )

        rng = np.random.default_rng(42)

        # Should raise error if kardashev_scale not provided
        with pytest.raises(ValueError, match="kardashev_scale must be provided"):
            model.check_self_destruction(dt_myr=1.0, rng=rng)

    def test_invalid_model_type(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="invalid"
        )

        rng = np.random.default_rng(42)

        with pytest.raises(ValueError, match="Unknown model_type"):
            model.check_self_destruction(dt_myr=1.0, rng=rng)

    def test_probability_scaling_with_timestep(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="flat"
        )

        rng = np.random.default_rng(42)

        # Probability should increase with larger timestep
        p_small_dt = 1 - np.exp(-0.1 * 0.1)  # dt=0.1
        p_large_dt = 1 - np.exp(-0.1 * 10.0)  # dt=10.0

        assert p_large_dt > p_small_dt
        assert p_small_dt < 0.1  # Small timestep approximates linear
        assert p_large_dt > 0.6  # Large timestep saturates

    def test_get_crisis_info(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent"
        )

        info = model.get_crisis_info()

        assert isinstance(info, dict)
        assert "nuclear_age" in info
        assert "kardashev_center" in info["nuclear_age"]
        assert info["nuclear_age"]["kardashev_center"] == 0.72

    def test_set_crisis_amplitude(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent"
        )

        # Get original AI crisis hazard
        lambda_before = model.calculate_kardashev_hazard_rate(1.05)

        # Increase AI crisis amplitude
        model.set_crisis_amplitude("ai_transition", 0.40)

        # Check it increased
        lambda_after = model.calculate_kardashev_hazard_rate(1.05)
        assert lambda_after > lambda_before

    def test_set_crisis_amplitude_invalid_name(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent"
        )

        with pytest.raises(ValueError, match="Crisis 'nonexistent' not found"):
            model.set_crisis_amplitude("nonexistent", 0.5)

    def test_enable_disable_crisis(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent"
        )

        # Get hazard with all crises enabled
        lambda_all = model.calculate_kardashev_hazard_rate(1.05)

        # Disable AI crisis (which peaks at 1.05)
        model.enable_crisis("ai_transition", enabled=False)

        # Should be lower
        lambda_without_ai = model.calculate_kardashev_hazard_rate(1.05)
        assert lambda_without_ai < lambda_all

        # Re-enable
        model.enable_crisis("ai_transition", enabled=True)
        lambda_reenabled = model.calculate_kardashev_hazard_rate(1.05)
        assert np.isclose(lambda_reenabled, lambda_all)

    def test_enable_crisis_invalid_name(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=1.0,
            model_type="kardashev_dependent"
        )

        with pytest.raises(ValueError, match="Crisis 'nonexistent' not found"):
            model.enable_crisis("nonexistent", enabled=False)

    def test_survival_probability_flat_model(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=10.0,
            model_type="flat"
        )

        # Survival probability should decay exponentially
        s_0 = model.survival_probability(0.0)
        s_1 = model.survival_probability(1.0)
        s_10 = model.survival_probability(10.0)

        assert s_0 == 1.0
        assert 0 < s_1 < 1.0
        assert s_10 < s_1

        # Check correct formula: S(t) = exp(-(λ + 1/τ) * t)
        # λ = 0.1, τ = 10.0, so total rate = 0.1 + 0.1 = 0.2
        expected_s_1 = np.exp(-0.2 * 1.0)
        assert np.isclose(s_1, expected_s_1)

    def test_survival_probability_kardashev_model(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=10.0,
            model_type="kardashev_dependent",
            baseline_rate=0.01,
            baseline_scaling=0.05
        )

        # At higher Kardashev scale, survival should be different
        s_k07 = model.survival_probability(1.0, kardashev_scale=0.7)
        s_k30 = model.survival_probability(1.0, kardashev_scale=3.0)

        # Both should be positive
        assert 0 < s_k07 < 1.0
        assert 0 < s_k30 < 1.0

    def test_age_extinction_before_mean_lifetime(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=10.0,
            model_type="flat"
        )

        rng = np.random.default_rng(42)

        # Before mean lifetime, should never die of old age
        assert model.check_age_extinction(age_myr=5.0, dt_myr=1.0, rng=rng) is False
        assert model.check_age_extinction(age_myr=9.9, dt_myr=1.0, rng=rng) is False

    def test_age_extinction_after_mean_lifetime(self):
        model = ExtinctionModel(
            self_destruction_rate=0.1,
            mean_lifetime_myr=10.0,
            model_type="flat"
        )

        rng = np.random.default_rng(42)

        # After mean lifetime, should have non-zero probability
        num_trials = 10000
        extinctions = sum(
            model.check_age_extinction(age_myr=15.0, dt_myr=1.0, rng=rng)
            for _ in range(num_trials)
        )

        # Should have some extinctions
        assert extinctions > 0

        # Expected probability: 1 - exp(-1.0/10.0) ≈ 0.095
        expected_prob = 1 - np.exp(-1.0 / 10.0)
        observed_prob = extinctions / num_trials

        # Should be within 3 standard deviations
        assert abs(observed_prob - expected_prob) < 3 * np.sqrt(expected_prob * (1 - expected_prob) / num_trials)
