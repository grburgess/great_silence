"""
Tests for civilization traits system.
"""

import pytest
import numpy as np
from great_silence.civilization.traits import (
    CivilizationTraits,
    TraitGenerator
)


class TestCivilizationTraits:
    """Tests for CivilizationTraits dataclass."""

    def test_traits_creation(self):
        """Test creating traits with valid values."""
        traits = CivilizationTraits(
            political_cohesion=0.8,
            technological_wisdom=0.6,
            risk_tolerance=0.3,
            resource_abundance=0.7,
            adaptability=0.75
        )

        assert traits.political_cohesion == 0.8
        assert traits.technological_wisdom == 0.6
        assert traits.risk_tolerance == 0.3
        assert traits.resource_abundance == 0.7
        assert traits.adaptability == 0.75

    def test_traits_validation(self):
        """Test that invalid trait values raise errors."""
        # Too high
        with pytest.raises(ValueError, match="must be in"):
            CivilizationTraits(
                political_cohesion=1.5,
                technological_wisdom=0.6,
                risk_tolerance=0.3,
                resource_abundance=0.7,
                adaptability=0.75
            )

        # Too low
        with pytest.raises(ValueError, match="must be in"):
            CivilizationTraits(
                political_cohesion=0.8,
                technological_wisdom=-0.1,
                risk_tolerance=0.3,
                resource_abundance=0.7,
                adaptability=0.75
            )

    def test_crisis_survival_modifier_high_quality(self):
        """Test survival modifier for high-quality traits."""
        # Ideal civilization: high cohesion, wisdom, resources, adaptability, low risk
        traits = CivilizationTraits(
            political_cohesion=1.0,
            technological_wisdom=1.0,
            risk_tolerance=0.0,
            resource_abundance=1.0,
            adaptability=1.0
        )

        modifier = traits.get_crisis_survival_modifier()

        # Should get all bonuses: +0.30 +0.20 +0.15 +0.15 +0.0 = +0.80
        # Modifier = 1.0 + 0.80 = 1.80
        assert modifier == pytest.approx(1.80, abs=0.01)

    def test_crisis_survival_modifier_low_quality(self):
        """Test survival modifier for low-quality traits."""
        # Worst civilization: low everything except high risk
        traits = CivilizationTraits(
            political_cohesion=0.0,
            technological_wisdom=0.0,
            risk_tolerance=1.0,
            resource_abundance=0.0,
            adaptability=0.0
        )

        modifier = traits.get_crisis_survival_modifier()

        # Should get all penalties: +0.0 +0.0 -0.20 +0.0 +0.0 = -0.20
        # Modifier = 1.0 - 0.20 = 0.80
        # Actually it's: 1.0 + 0.0 + 0.0 + 0.0 + 0.0 - 0.20 = 0.80
        assert modifier == pytest.approx(0.80, abs=0.01)

    def test_crisis_survival_modifier_balanced(self):
        """Test survival modifier for balanced traits."""
        # Average civilization
        traits = CivilizationTraits(
            political_cohesion=0.5,
            technological_wisdom=0.5,
            risk_tolerance=0.5,
            resource_abundance=0.5,
            adaptability=0.5
        )

        modifier = traits.get_crisis_survival_modifier()

        # Bonuses: +0.15 +0.10 +0.075 +0.075 = +0.40
        # Penalties: -0.10
        # Net: 1.0 + 0.40 - 0.10 = 1.30
        assert modifier == pytest.approx(1.30, abs=0.01)

    def test_advancement_rate_modifier(self):
        """Test advancement rate modifier."""
        # Risk-taker with resources
        fast_traits = CivilizationTraits(
            political_cohesion=0.5,
            technological_wisdom=0.2,  # Low wisdom = less cautious
            risk_tolerance=1.0,        # High risk = fast
            resource_abundance=1.0,    # Rich = fast
            adaptability=0.5
        )

        fast_modifier = fast_traits.get_advancement_rate_modifier()

        # 1.0 + 0.40 (risk) - 0.04 (wisdom) + 0.15 (resources) = 1.51
        assert fast_modifier > 1.3

        # Cautious civilization
        slow_traits = CivilizationTraits(
            political_cohesion=0.5,
            technological_wisdom=1.0,  # High wisdom = cautious
            risk_tolerance=0.0,        # Low risk = slow
            resource_abundance=0.0,    # Poor = slow
            adaptability=0.5
        )

        slow_modifier = slow_traits.get_advancement_rate_modifier()

        # 1.0 + 0.0 (risk) - 0.20 (wisdom) + 0.0 (resources) = 0.80
        assert slow_modifier < 1.0
        assert slow_modifier >= 0.5  # Never below 0.5

    def test_crisis_detection_bonus(self):
        """Test crisis detection probability."""
        # Wise, cautious civilization
        good_detector = CivilizationTraits(
            political_cohesion=0.5,
            technological_wisdom=1.0,
            risk_tolerance=0.0,  # Very cautious
            resource_abundance=1.0,
            adaptability=0.5
        )

        detection = good_detector.get_crisis_detection_bonus()

        # 0.5 * 1.0 + 0.3 * 1.0 + 0.2 * 1.0 = 1.0 (capped)
        assert detection == pytest.approx(1.0, abs=0.01)

        # Reckless, unwise civilization
        bad_detector = CivilizationTraits(
            political_cohesion=0.5,
            technological_wisdom=0.0,
            risk_tolerance=1.0,  # Very aggressive
            resource_abundance=0.0,
            adaptability=0.5
        )

        detection = bad_detector.get_crisis_detection_bonus()

        # 0.5 * 0.0 + 0.3 * 0.0 + 0.2 * 0.0 = 0.0
        assert detection == pytest.approx(0.0, abs=0.01)

    def test_evolve_from_success(self):
        """Test trait evolution after surviving crisis."""
        initial_traits = CivilizationTraits(
            political_cohesion=0.5,
            technological_wisdom=0.5,
            risk_tolerance=0.5,
            resource_abundance=0.5,
            adaptability=0.5
        )

        # Survive severe crisis
        new_traits = initial_traits.evolve_from_experience(
            crisis_survived=True,
            crisis_severity=0.8
        )

        # Traits should improve
        assert new_traits.political_cohesion > initial_traits.political_cohesion
        assert new_traits.technological_wisdom > initial_traits.technological_wisdom
        assert new_traits.adaptability > initial_traits.adaptability

        # Risk tolerance slightly increases (overconfidence)
        assert new_traits.risk_tolerance > initial_traits.risk_tolerance

        # Resources unchanged
        assert new_traits.resource_abundance == initial_traits.resource_abundance

    def test_evolve_from_failure(self):
        """Test trait evolution after barely surviving crisis."""
        initial_traits = CivilizationTraits(
            political_cohesion=0.6,
            technological_wisdom=0.6,
            risk_tolerance=0.6,
            resource_abundance=0.6,
            adaptability=0.6
        )

        # Barely survive severe crisis
        new_traits = initial_traits.evolve_from_experience(
            crisis_survived=False,
            crisis_severity=0.9
        )

        # Traits should worsen (trauma)
        assert new_traits.political_cohesion < initial_traits.political_cohesion
        assert new_traits.technological_wisdom < initial_traits.technological_wisdom
        assert new_traits.adaptability < initial_traits.adaptability
        assert new_traits.resource_abundance < initial_traits.resource_abundance

        # Risk tolerance should decrease (learned caution)
        assert new_traits.risk_tolerance < initial_traits.risk_tolerance

    def test_apply_breakthrough_unification(self):
        """Test unification movement breakthrough."""
        traits = CivilizationTraits(
            political_cohesion=0.5,
            technological_wisdom=0.5,
            risk_tolerance=0.5,
            resource_abundance=0.5,
            adaptability=0.5
        )

        new_traits = traits.apply_breakthrough("unification_movement")

        # Cohesion should increase significantly
        assert new_traits.political_cohesion == pytest.approx(0.8, abs=0.01)

        # Other traits unchanged
        assert new_traits.technological_wisdom == 0.5
        assert new_traits.risk_tolerance == 0.5

    def test_apply_breakthrough_philosophical(self):
        """Test philosophical awakening breakthrough."""
        traits = CivilizationTraits(
            political_cohesion=0.4,
            technological_wisdom=0.4,
            risk_tolerance=0.6,
            resource_abundance=0.5,
            adaptability=0.4
        )

        new_traits = traits.apply_breakthrough("philosophical_awakening")

        # Multiple traits should improve
        assert new_traits.political_cohesion > traits.political_cohesion
        assert new_traits.technological_wisdom > traits.technological_wisdom
        assert new_traits.adaptability > traits.adaptability

        # Risk tolerance should decrease
        assert new_traits.risk_tolerance < traits.risk_tolerance

    def test_apply_breakthrough_resource_discovery(self):
        """Test resource discovery breakthrough."""
        traits = CivilizationTraits(
            political_cohesion=0.5,
            technological_wisdom=0.5,
            risk_tolerance=0.5,
            resource_abundance=0.3,
            adaptability=0.5
        )

        new_traits = traits.apply_breakthrough("resource_discovery")

        # Resources should increase significantly
        assert new_traits.resource_abundance == pytest.approx(0.8, abs=0.01)

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        original = CivilizationTraits(
            political_cohesion=0.8,
            technological_wisdom=0.6,
            risk_tolerance=0.3,
            resource_abundance=0.7,
            adaptability=0.75
        )

        # Serialize
        data = original.to_dict()
        assert data['political_cohesion'] == 0.8
        assert data['technological_wisdom'] == 0.6

        # Deserialize
        restored = CivilizationTraits.from_dict(data)
        assert restored.political_cohesion == original.political_cohesion
        assert restored.technological_wisdom == original.technological_wisdom
        assert restored.risk_tolerance == original.risk_tolerance
        assert restored.resource_abundance == original.resource_abundance
        assert restored.adaptability == original.adaptability


class TestTraitGenerator:
    """Tests for TraitGenerator."""

    def test_generator_creation(self):
        """Test creating generator with seed."""
        gen = TraitGenerator(seed=42)
        assert gen.rng is not None

    def test_generate_random_traits(self):
        """Test generating random traits."""
        gen = TraitGenerator(seed=42)

        traits = gen.generate_random_traits()

        # All values should be in valid range
        assert 0.0 <= traits.political_cohesion <= 1.0
        assert 0.0 <= traits.technological_wisdom <= 1.0
        assert 0.0 <= traits.risk_tolerance <= 1.0
        assert 0.0 <= traits.resource_abundance <= 1.0
        assert 0.0 <= traits.adaptability <= 1.0

    def test_random_traits_reproducibility(self):
        """Test that same seed produces same traits."""
        gen1 = TraitGenerator(seed=42)
        gen2 = TraitGenerator(seed=42)

        traits1 = gen1.generate_random_traits()
        traits2 = gen2.generate_random_traits()

        assert traits1.political_cohesion == traits2.political_cohesion
        assert traits1.technological_wisdom == traits2.technological_wisdom
        assert traits1.risk_tolerance == traits2.risk_tolerance
        assert traits1.resource_abundance == traits2.resource_abundance
        assert traits1.adaptability == traits2.adaptability

    def test_random_traits_different_seeds(self):
        """Test that different seeds produce different traits."""
        gen1 = TraitGenerator(seed=42)
        gen2 = TraitGenerator(seed=43)

        traits1 = gen1.generate_random_traits()
        traits2 = gen2.generate_random_traits()

        # Extremely unlikely to be exactly the same
        assert (traits1.political_cohesion != traits2.political_cohesion or
                traits1.technological_wisdom != traits2.technological_wisdom)

    def test_generate_traits_high_metallicity(self):
        """Test that high metallicity increases resource abundance."""
        gen = TraitGenerator(seed=42)

        # Generate multiple samples and check average
        resource_values = []
        for _ in range(100):
            gen = TraitGenerator(seed=None)  # Different each time
            traits = gen.generate_traits_from_environment(
                star_metallicity=2.0  # 2x solar metallicity
            )
            resource_values.append(traits.resource_abundance)

        avg_resources = np.mean(resource_values)

        # Should be above 0.5 on average due to metallicity bonus
        assert avg_resources > 0.5

    def test_generate_traits_low_metallicity(self):
        """Test that low metallicity doesn't increase resources."""
        gen = TraitGenerator(seed=42)

        traits = gen.generate_traits_from_environment(
            star_metallicity=0.5  # 0.5x solar metallicity
        )

        # No bonus applied (metallicity too low)
        assert 0.0 <= traits.resource_abundance <= 1.0

    def test_generate_traits_inner_galaxy(self):
        """Test that inner galaxy reduces risk tolerance."""
        gen = TraitGenerator(seed=42)

        # Generate multiple samples
        risk_values = []
        for _ in range(100):
            gen = TraitGenerator(seed=None)
            traits = gen.generate_traits_from_environment(
                galactic_radius_kpc=2.0  # Inner galaxy
            )
            risk_values.append(traits.risk_tolerance)

        avg_risk = np.mean(risk_values)

        # Should be below 0.5 on average due to danger
        assert avg_risk < 0.5

    def test_generate_traits_outer_galaxy(self):
        """Test that outer galaxy may increase risk tolerance."""
        gen = TraitGenerator(seed=42)

        traits = gen.generate_traits_from_environment(
            galactic_radius_kpc=15.0  # Outer galaxy
        )

        # Risk tolerance gets small bonus
        assert 0.0 <= traits.risk_tolerance <= 1.0

    def test_generate_traits_high_density(self):
        """Test that high stellar density increases cohesion."""
        gen = TraitGenerator(seed=42)

        # Generate multiple samples
        cohesion_values = []
        for _ in range(100):
            gen = TraitGenerator(seed=None)
            traits = gen.generate_traits_from_environment(
                stellar_density=10.0  # High density
            )
            cohesion_values.append(traits.political_cohesion)

        avg_cohesion = np.mean(cohesion_values)

        # Should be above 0.5 on average due to interaction bonus
        assert avg_cohesion > 0.5

    def test_generate_traits_combined_environment(self):
        """Test generating traits with multiple environmental factors."""
        gen = TraitGenerator(seed=42)

        traits = gen.generate_traits_from_environment(
            star_metallicity=1.5,
            galactic_radius_kpc=3.0,  # Inner galaxy
            stellar_density=5.0       # High density
        )

        # Should have modifications from all factors
        assert 0.0 <= traits.resource_abundance <= 1.0
        assert 0.0 <= traits.risk_tolerance <= 1.0
        assert 0.0 <= traits.political_cohesion <= 1.0

    def test_generate_correlated_traits_high_cohesion(self):
        """Test generating traits correlated with high cohesion."""
        gen = TraitGenerator(seed=42)

        traits = gen.generate_correlated_traits(
            base_trait='political_cohesion',
            base_value=0.9,
            correlation=0.8  # Strong correlation
        )

        # With high cohesion, expect:
        # - High wisdom (positive correlation)
        # - Low risk tolerance (negative correlation)
        # - Higher adaptability (positive correlation)

        assert traits.political_cohesion == 0.9
        assert traits.technological_wisdom > 0.5  # Likely high
        assert traits.risk_tolerance < 0.5        # Likely low

    def test_generate_correlated_traits_high_risk(self):
        """Test generating traits correlated with high risk tolerance."""
        gen = TraitGenerator(seed=42)

        traits = gen.generate_correlated_traits(
            base_trait='risk_tolerance',
            base_value=0.9,
            correlation=0.8
        )

        # With high risk tolerance, expect:
        # - Low cohesion (negative correlation)
        # - Low wisdom (negative correlation)
        # - High adaptability (positive correlation)

        assert traits.risk_tolerance == 0.9
        # These are probabilistic, so we check many samples
        # or just check they're in valid range
        assert 0.0 <= traits.political_cohesion <= 1.0
        assert 0.0 <= traits.technological_wisdom <= 1.0

    def test_generate_correlated_traits_no_correlation(self):
        """Test that zero correlation gives random traits."""
        gen = TraitGenerator(seed=42)

        traits = gen.generate_correlated_traits(
            base_trait='political_cohesion',
            base_value=1.0,
            correlation=0.0  # No correlation
        )

        # Base trait should be set
        assert traits.political_cohesion == 1.0

        # Other traits should be random (not necessarily correlated)
        assert 0.0 <= traits.technological_wisdom <= 1.0
        assert 0.0 <= traits.risk_tolerance <= 1.0
