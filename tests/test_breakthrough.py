"""
Tests for breakthrough event system.
"""

import pytest
import numpy as np
from great_silence.civilization.breakthrough import (
    BreakthroughType,
    BreakthroughProbabilities,
    BreakthroughSystem,
    format_breakthrough_summary
)


class TestBreakthroughProbabilities:
    """Tests for BreakthroughProbabilities dataclass."""

    def test_default_values(self):
        """Test default probability parameters."""
        prob = BreakthroughProbabilities()

        assert prob.base_rate == 0.001
        assert prob.stagnation_multiplier == 3.0
        assert prob.post_crisis_multiplier == 5.0
        assert prob.maturity_threshold == 0.8

    def test_custom_values(self):
        """Test creating with custom values."""
        prob = BreakthroughProbabilities(
            base_rate=0.002,
            stagnation_multiplier=4.0,
            post_crisis_multiplier=6.0,
            maturity_threshold=0.9
        )

        assert prob.base_rate == 0.002
        assert prob.stagnation_multiplier == 4.0
        assert prob.post_crisis_multiplier == 6.0
        assert prob.maturity_threshold == 0.9


class TestBreakthroughSystem:
    """Tests for BreakthroughSystem."""

    def test_initialization(self):
        """Test creating breakthrough system."""
        system = BreakthroughSystem(seed=42)

        assert system.probabilities is not None
        assert system.rng is not None

    def test_initialization_with_custom_probabilities(self):
        """Test initialization with custom probabilities."""
        prob = BreakthroughProbabilities(base_rate=0.002)
        system = BreakthroughSystem(probabilities=prob, seed=42)

        assert system.probabilities.base_rate == 0.002

    def test_breakthrough_probability_young_civilization(self):
        """Test probability calculation for young civilization."""
        system = BreakthroughSystem(seed=42)

        prob = system._calculate_breakthrough_probability(
            civilization_age_myr=50.0,  # Young
            maturity_level=0.7,
            stagnation_time_myr=0.0,
            recently_survived_crisis=False
        )

        # Should be close to base rate with maturity modifier
        expected = 0.001 * (0.5 + 0.7)  # base * maturity_factor
        assert prob == pytest.approx(expected, rel=0.1)

    def test_breakthrough_probability_old_civilization(self):
        """Test probability increases with age."""
        system = BreakthroughSystem(seed=42)

        prob_young = system._calculate_breakthrough_probability(
            civilization_age_myr=100.0,
            maturity_level=0.7,
            stagnation_time_myr=0.0,
            recently_survived_crisis=False
        )

        prob_old = system._calculate_breakthrough_probability(
            civilization_age_myr=1000.0,  # 10x older
            maturity_level=0.7,
            stagnation_time_myr=0.0,
            recently_survived_crisis=False
        )

        assert prob_old > prob_young

    def test_breakthrough_probability_with_stagnation(self):
        """Test stagnation increases probability."""
        system = BreakthroughSystem(seed=42)

        prob_no_stagnation = system._calculate_breakthrough_probability(
            civilization_age_myr=500.0,
            maturity_level=0.8,
            stagnation_time_myr=100.0,  # Not stagnant
            recently_survived_crisis=False
        )

        prob_stagnant = system._calculate_breakthrough_probability(
            civilization_age_myr=500.0,
            maturity_level=0.8,
            stagnation_time_myr=600.0,  # Stagnant
            recently_survived_crisis=False
        )

        # Stagnation should multiply probability by 3x
        assert prob_stagnant > prob_no_stagnation
        assert prob_stagnant == pytest.approx(prob_no_stagnation * 3.0, rel=0.1)

    def test_breakthrough_probability_post_crisis(self):
        """Test post-crisis multiplier."""
        system = BreakthroughSystem(seed=42)

        prob_normal = system._calculate_breakthrough_probability(
            civilization_age_myr=500.0,
            maturity_level=0.8,
            stagnation_time_myr=0.0,
            recently_survived_crisis=False
        )

        prob_post_crisis = system._calculate_breakthrough_probability(
            civilization_age_myr=500.0,
            maturity_level=0.8,
            stagnation_time_myr=0.0,
            recently_survived_crisis=True
        )

        # Post-crisis should multiply by 5x
        assert prob_post_crisis > prob_normal
        assert prob_post_crisis == pytest.approx(prob_normal * 5.0, rel=0.1)

    def test_breakthrough_probability_maturity_scaling(self):
        """Test that higher maturity increases probability."""
        system = BreakthroughSystem(seed=42)

        prob_low_maturity = system._calculate_breakthrough_probability(
            civilization_age_myr=500.0,
            maturity_level=0.5,
            stagnation_time_myr=0.0,
            recently_survived_crisis=False
        )

        prob_high_maturity = system._calculate_breakthrough_probability(
            civilization_age_myr=500.0,
            maturity_level=1.5,
            stagnation_time_myr=0.0,
            recently_survived_crisis=False
        )

        assert prob_high_maturity > prob_low_maturity

    def test_select_breakthrough_type_low_maturity(self):
        """Test breakthrough selection for low maturity civilization."""
        system = BreakthroughSystem(seed=42)

        # Run multiple times to check distribution
        types = []
        for _ in range(100):
            bt = system._select_breakthrough_type(
                maturity_level=0.5,  # Low maturity
                stagnation_time_myr=0.0,
                recently_survived_crisis=False
            )
            types.append(bt)

        # Should rarely get philosophical awakening (requires high maturity)
        awakening_count = types.count(BreakthroughType.PHILOSOPHICAL_AWAKENING)
        assert awakening_count < 30  # Should be rare

    def test_select_breakthrough_type_high_maturity(self):
        """Test breakthrough selection for high maturity civilization."""
        system = BreakthroughSystem(seed=42)

        # Run multiple times
        types = []
        for _ in range(100):
            bt = system._select_breakthrough_type(
                maturity_level=1.2,  # High maturity
                stagnation_time_myr=0.0,
                recently_survived_crisis=False
            )
            types.append(bt)

        # Should get some philosophical awakenings
        awakening_count = types.count(BreakthroughType.PHILOSOPHICAL_AWAKENING)
        assert awakening_count > 0

    def test_select_breakthrough_type_stagnant(self):
        """Test breakthrough selection for stagnant civilization."""
        system = BreakthroughSystem(seed=42)

        # Run multiple times
        types = []
        for _ in range(100):
            bt = system._select_breakthrough_type(
                maturity_level=0.8,
                stagnation_time_myr=600.0,  # Stagnant
                recently_survived_crisis=False
            )
            types.append(bt)

        # Should favor unification movement
        unification_count = types.count(BreakthroughType.UNIFICATION_MOVEMENT)
        assert unification_count > 10  # Should be common

    def test_select_breakthrough_type_post_crisis(self):
        """Test breakthrough selection after crisis survival."""
        system = BreakthroughSystem(seed=42)

        # Run multiple times
        types = []
        for _ in range(100):
            bt = system._select_breakthrough_type(
                maturity_level=0.9,  # High enough for ethical enlightenment
                stagnation_time_myr=0.0,
                recently_survived_crisis=True
            )
            types.append(bt)

        # Should favor ethical enlightenment
        ethical_count = types.count(BreakthroughType.ETHICAL_ENLIGHTENMENT)
        assert ethical_count > 0

    def test_check_for_breakthrough_rare(self):
        """Test that breakthroughs are rare events."""
        system = BreakthroughSystem(seed=42)

        # Check 100 timesteps for young, low-maturity civ
        breakthroughs = 0
        for _ in range(100):
            occurred, bt_type = system.check_for_breakthrough(
                civilization_age_myr=100.0,
                maturity_level=0.6,
                stagnation_time_myr=0.0,
                dt_myr=1.0,
                recently_survived_crisis=False
            )
            if occurred:
                breakthroughs += 1

        # Should be very rare (base rate 0.001 per Myr)
        assert breakthroughs < 5  # Expect ~0.12 on average

    def test_check_for_breakthrough_common_post_crisis(self):
        """Test breakthroughs are more common post-crisis."""
        system = BreakthroughSystem(seed=42)

        # Check with post-crisis boost
        breakthroughs = 0
        for _ in range(100):
            occurred, bt_type = system.check_for_breakthrough(
                civilization_age_myr=1000.0,  # Old
                maturity_level=1.0,  # Mature
                stagnation_time_myr=0.0,
                dt_myr=1.0,
                recently_survived_crisis=True  # Post-crisis
            )
            if occurred:
                breakthroughs += 1

        # Should be more common
        assert breakthroughs > 0

    def test_check_for_breakthrough_returns_type(self):
        """Test that breakthrough check returns valid type."""
        system = BreakthroughSystem(seed=42)

        # Force a breakthrough by using high probability
        for _ in range(1000):
            occurred, bt_type = system.check_for_breakthrough(
                civilization_age_myr=10000.0,  # Very old
                maturity_level=2.0,  # Very mature
                stagnation_time_myr=1000.0,  # Very stagnant
                dt_myr=10.0,  # Large timestep
                recently_survived_crisis=True
            )
            if occurred:
                assert bt_type is not None
                assert isinstance(bt_type, BreakthroughType)
                break
        else:
            pytest.fail("No breakthrough occurred in 1000 attempts")

    def test_get_breakthrough_description(self):
        """Test getting descriptions for all types."""
        system = BreakthroughSystem()

        for bt_type in BreakthroughType:
            desc = system.get_breakthrough_description(bt_type)
            assert len(desc) > 0
            assert isinstance(desc, str)

    def test_get_maturity_impact(self):
        """Test getting maturity impact for all types."""
        system = BreakthroughSystem()

        for bt_type in BreakthroughType:
            maturity_boost, growth_boost = system.get_maturity_impact(bt_type)
            assert maturity_boost > 0
            assert growth_boost > 0
            assert isinstance(maturity_boost, float)
            assert isinstance(growth_boost, float)

    def test_maturity_impact_philosophical_awakening_strongest(self):
        """Test that philosophical awakening has strongest impact."""
        system = BreakthroughSystem()

        phil_boost, phil_growth = system.get_maturity_impact(
            BreakthroughType.PHILOSOPHICAL_AWAKENING
        )
        sci_boost, sci_growth = system.get_maturity_impact(
            BreakthroughType.SCIENTIFIC_REVOLUTION
        )

        # Philosophical should have more maturity boost than scientific
        assert phil_boost > sci_boost


class TestBreakthroughSummaries:
    """Tests for breakthrough summary formatting."""

    def test_format_no_breakthroughs(self):
        """Test summary with no breakthroughs."""
        summary = format_breakthrough_summary(0, [])
        assert "No breakthroughs" in summary

    def test_format_single_breakthrough(self):
        """Test summary with one breakthrough."""
        summary = format_breakthrough_summary(
            1,
            [BreakthroughType.PHILOSOPHICAL_AWAKENING]
        )

        assert "1 breakthrough" in summary
        assert "Philosophical Awakening" in summary

    def test_format_multiple_different_breakthroughs(self):
        """Test summary with multiple different types."""
        summary = format_breakthrough_summary(
            3,
            [
                BreakthroughType.PHILOSOPHICAL_AWAKENING,
                BreakthroughType.SOCIAL_REFORM,
                BreakthroughType.CULTURAL_RENAISSANCE
            ]
        )

        assert "3 breakthroughs" in summary
        assert "Philosophical Awakening" in summary
        assert "Social Reform" in summary
        assert "Cultural Renaissance" in summary

    def test_format_multiple_same_breakthroughs(self):
        """Test summary with repeated breakthrough types."""
        summary = format_breakthrough_summary(
            3,
            [
                BreakthroughType.SOCIAL_REFORM,
                BreakthroughType.SOCIAL_REFORM,
                BreakthroughType.SOCIAL_REFORM
            ]
        )

        assert "3 breakthroughs" in summary
        assert "Social Reform (x3)" in summary

    def test_format_mixed_repetitions(self):
        """Test summary with mix of repeated and unique types."""
        summary = format_breakthrough_summary(
            5,
            [
                BreakthroughType.SOCIAL_REFORM,
                BreakthroughType.SOCIAL_REFORM,
                BreakthroughType.PHILOSOPHICAL_AWAKENING,
                BreakthroughType.CULTURAL_RENAISSANCE,
                BreakthroughType.CULTURAL_RENAISSANCE
            ]
        )

        assert "5 breakthroughs" in summary
        assert "Social Reform (x2)" in summary
        assert "Cultural Renaissance (x2)" in summary
        # Philosophical Awakening should appear without count
        assert "Philosophical Awakening" in summary
        assert "(x1)" not in summary  # Should not show x1
