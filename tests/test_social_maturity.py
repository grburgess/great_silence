"""
Tests for social maturity system.
"""

import pytest
import numpy as np
from great_silence.civilization.social_maturity import (
    SocialMaturityState,
    SocialMaturityEvolution,
    format_maturity_description
)


class TestSocialMaturityState:
    """Tests for SocialMaturityState dataclass."""

    def test_state_creation(self):
        """Test creating maturity state."""
        state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.1,
            stagnation_time_myr=0.0
        )

        assert state.maturity_level == 0.8
        assert state.growth_rate == 0.01
        assert state.maturity_to_kardashev_ratio == 1.1
        assert state.stagnation_time_myr == 0.0

    def test_is_wise(self):
        """Test wisdom check."""
        wise_state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.2,
            stagnation_time_myr=0.0
        )

        assert wise_state.is_wise()
        assert wise_state.is_wise(threshold=1.0)
        assert not wise_state.is_wise(threshold=1.5)

    def test_is_dangerous(self):
        """Test danger check."""
        dangerous_state = SocialMaturityState(
            maturity_level=0.4,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=0.4,
            stagnation_time_myr=0.0
        )

        assert dangerous_state.is_dangerous()
        assert dangerous_state.is_dangerous(threshold=0.5)
        assert not dangerous_state.is_dangerous(threshold=0.3)

    def test_is_stagnant(self):
        """Test stagnation check."""
        stagnant_state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=600.0
        )

        assert stagnant_state.is_stagnant()
        assert stagnant_state.is_stagnant(threshold_myr=500.0)
        assert not stagnant_state.is_stagnant(threshold_myr=700.0)


class TestSocialMaturityEvolution:
    """Tests for SocialMaturityEvolution."""

    def test_initialization(self):
        """Test creating evolution model."""
        evolution = SocialMaturityEvolution(
            base_growth_rate=0.01,
            crisis_growth_multiplier=5.0,
            seed=42
        )

        assert evolution.base_growth_rate == 0.01
        assert evolution.crisis_growth_multiplier == 5.0
        assert evolution.rng is not None

    def test_initialize_maturity_basic(self):
        """Test initializing maturity for new civilization."""
        evolution = SocialMaturityEvolution(seed=42)

        state = evolution.initialize_maturity(
            initial_kardashev=0.7,
            traits=None
        )

        # Should start below Kardashev level
        assert state.maturity_level < 0.7
        assert state.maturity_level > 0.0
        assert state.growth_rate > 0.0
        assert state.maturity_to_kardashev_ratio < 1.0

    def test_initialize_maturity_with_traits(self):
        """Test initializing maturity with trait bonuses."""
        evolution = SocialMaturityEvolution(seed=42)

        # High wisdom and cohesion traits
        traits = {
            'technological_wisdom': 0.9,
            'political_cohesion': 0.8,
            'adaptability': 0.7
        }

        state = evolution.initialize_maturity(
            initial_kardashev=0.7,
            traits=traits
        )

        # Should get bonuses from traits
        assert state.maturity_level > 0.6  # Higher due to bonuses
        assert state.growth_rate > evolution.base_growth_rate  # Adaptability bonus

    def test_advance_maturity_normal(self):
        """Test advancing maturity in normal conditions."""
        evolution = SocialMaturityEvolution(seed=42)

        initial_state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=0.0
        )

        new_state = evolution.advance_maturity(
            state=initial_state,
            current_kardashev=0.8,
            dt_myr=10.0,
            in_crisis=False,
            traits=None
        )

        # Should grow
        assert new_state.maturity_level > initial_state.maturity_level
        # Growth should be approximately base_rate * dt
        expected_growth = 0.01 * 10.0  # 0.1
        assert new_state.maturity_level == pytest.approx(0.9, abs=0.05)

    def test_advance_maturity_during_crisis(self):
        """Test that crisis accelerates maturity growth."""
        evolution = SocialMaturityEvolution(
            seed=42,
            crisis_growth_multiplier=5.0
        )

        initial_state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=0.0
        )

        # Advance during crisis
        crisis_state = evolution.advance_maturity(
            state=initial_state,
            current_kardashev=0.8,
            dt_myr=10.0,
            in_crisis=True,
            traits=None
        )

        # Advance normally
        normal_state = evolution.advance_maturity(
            state=initial_state,
            current_kardashev=0.8,
            dt_myr=10.0,
            in_crisis=False,
            traits=None
        )

        # Crisis should cause more growth
        assert crisis_state.maturity_level > normal_state.maturity_level

    def test_advance_maturity_with_stagnation(self):
        """Test that stagnation slows growth."""
        evolution = SocialMaturityEvolution(
            seed=42,
            stagnation_threshold_myr=500.0
        )

        stagnant_state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=800.0  # Long stagnation
        )

        new_state = evolution.advance_maturity(
            state=stagnant_state,
            current_kardashev=0.8,
            dt_myr=10.0,
            in_crisis=False,
            traits=None
        )

        # Growth should be reduced
        # Expected normal growth: 0.01 * 10 = 0.1 → 0.9 total
        # Stagnation penalty: (800-500)/1000 = 0.3 → 0.7x growth
        # With stagnation: 0.01 * 0.7 * 10 = 0.07 → 0.87 total
        assert new_state.maturity_level < 0.9  # Less than normal
        assert new_state.maturity_level == pytest.approx(0.87, abs=0.01)

    def test_advance_maturity_updates_stagnation_timer(self):
        """Test that stagnation timer updates correctly."""
        evolution = SocialMaturityEvolution(seed=42)

        state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=100.0
        )

        # Normal growth should reset stagnation
        new_state = evolution.advance_maturity(
            state=state,
            current_kardashev=0.8,
            dt_myr=10.0,
            in_crisis=False,
            traits=None
        )

        assert new_state.stagnation_time_myr == 0.0

    def test_apply_crisis_survival_boost(self):
        """Test maturity boost from surviving crisis."""
        evolution = SocialMaturityEvolution(seed=42)

        initial_state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=100.0
        )

        # Survive severe crisis
        boosted_state = evolution.apply_crisis_survival_boost(
            state=initial_state,
            crisis_severity=0.9
        )

        # Should get immediate boost
        assert boosted_state.maturity_level > initial_state.maturity_level

        # Growth rate should permanently increase
        assert boosted_state.growth_rate > initial_state.growth_rate

        # Stagnation should reset
        assert boosted_state.stagnation_time_myr == 0.0

    def test_apply_crisis_survival_boost_severity_scaling(self):
        """Test that harder crises give bigger boosts."""
        evolution = SocialMaturityEvolution(seed=42)

        state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=0.0
        )

        # Mild crisis
        mild_boost = evolution.apply_crisis_survival_boost(state, 0.3)

        # Severe crisis
        severe_boost = evolution.apply_crisis_survival_boost(state, 0.9)

        # Severe should give more boost
        assert severe_boost.maturity_level > mild_boost.maturity_level
        assert severe_boost.growth_rate > mild_boost.growth_rate

    def test_apply_crisis_failure_damage(self):
        """Test maturity damage from crisis failure."""
        evolution = SocialMaturityEvolution(seed=42)

        initial_state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=0.0
        )

        # Fail severe crisis
        damaged_state = evolution.apply_crisis_failure_damage(
            state=initial_state,
            crisis_severity=0.9
        )

        # Should lose maturity
        assert damaged_state.maturity_level < initial_state.maturity_level

        # Growth rate should decrease
        assert damaged_state.growth_rate < initial_state.growth_rate

        # Should not go below minimum
        assert damaged_state.maturity_level >= 0.1
        assert damaged_state.growth_rate >= 0.001

    def test_apply_breakthrough_philosophical(self):
        """Test philosophical awakening breakthrough."""
        evolution = SocialMaturityEvolution(seed=42)

        state = SocialMaturityState(
            maturity_level=0.7,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=200.0
        )

        new_state = evolution.apply_breakthrough(state, "philosophical_awakening")

        # Should get large boost
        assert new_state.maturity_level > state.maturity_level + 0.15

        # Growth rate should increase
        assert new_state.growth_rate > state.growth_rate

        # Stagnation should reset
        assert new_state.stagnation_time_myr == 0.0

    def test_apply_breakthrough_social_reform(self):
        """Test social reform breakthrough."""
        evolution = SocialMaturityEvolution(seed=42)

        state = SocialMaturityState(
            maturity_level=0.7,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=0.0
        )

        new_state = evolution.apply_breakthrough(state, "social_reform")

        # Should get moderate boost
        assert new_state.maturity_level > state.maturity_level + 0.05

    def test_calculate_crisis_survival_modifier_wise(self):
        """Test survival modifier for wise civilization."""
        evolution = SocialMaturityEvolution(seed=42)

        # Very wise: maturity >> tech
        wise_state = SocialMaturityState(
            maturity_level=1.5,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.8,  # Much higher than threshold
            stagnation_time_myr=0.0
        )

        modifier = evolution.calculate_crisis_survival_modifier(wise_state)

        # Should get 2x survival chance
        assert modifier == 2.0

    def test_calculate_crisis_survival_modifier_balanced(self):
        """Test survival modifier for balanced civilization."""
        evolution = SocialMaturityEvolution(seed=42)

        balanced_state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=0.0
        )

        modifier = evolution.calculate_crisis_survival_modifier(balanced_state)

        # Should get 1.5x survival chance
        assert modifier == 1.5

    def test_calculate_crisis_survival_modifier_dangerous(self):
        """Test survival modifier for dangerous civilization."""
        evolution = SocialMaturityEvolution(seed=42)

        dangerous_state = SocialMaturityState(
            maturity_level=0.35,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=0.4,  # Tech >> maturity
            stagnation_time_myr=0.0
        )

        modifier = evolution.calculate_crisis_survival_modifier(dangerous_state)

        # Should get 0.2x survival chance (very dangerous)
        assert modifier == 0.2

    def test_check_for_collapse_risk_safe(self):
        """Test collapse risk for safe civilization."""
        evolution = SocialMaturityEvolution(seed=42)

        safe_state = SocialMaturityState(
            maturity_level=0.8,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=0.0
        )

        at_risk, prob = evolution.check_for_collapse_risk(safe_state, 0.8)

        assert not at_risk
        assert prob == 0.0

    def test_check_for_collapse_risk_dangerous(self):
        """Test collapse risk for dangerous civilization."""
        evolution = SocialMaturityEvolution(seed=42)

        dangerous_state = SocialMaturityState(
            maturity_level=0.2,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=0.25,  # Very dangerous
            stagnation_time_myr=0.0
        )

        at_risk, prob = evolution.check_for_collapse_risk(dangerous_state, 0.8)

        assert at_risk
        assert prob > 0.0
        assert prob == pytest.approx(0.01, abs=0.001)  # 1% per Myr

    def test_calculate_aid_effectiveness_high_maturity(self):
        """Test aid effectiveness with mature civilizations."""
        evolution = SocialMaturityEvolution(seed=42)

        # Both mature
        receiver_state = SocialMaturityState(
            maturity_level=1.0,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.0,
            stagnation_time_myr=0.0
        )

        effectiveness = evolution.calculate_aid_effectiveness(
            receiver_state=receiver_state,
            helper_maturity=1.5
        )

        # Should be very effective
        assert effectiveness > 1.0

    def test_calculate_aid_effectiveness_low_maturity(self):
        """Test aid effectiveness with immature receiver."""
        evolution = SocialMaturityEvolution(seed=42)

        # Immature receiver
        receiver_state = SocialMaturityState(
            maturity_level=0.3,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=0.5,
            stagnation_time_myr=0.0
        )

        effectiveness = evolution.calculate_aid_effectiveness(
            receiver_state=receiver_state,
            helper_maturity=1.5
        )

        # Should be less effective (receiver can't absorb well)
        assert effectiveness < 1.5


class TestMaturityDescriptions:
    """Tests for maturity description formatting."""

    def test_format_primitive(self):
        """Test description for primitive civilization."""
        state = SocialMaturityState(
            maturity_level=0.4,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=0.6,
            stagnation_time_myr=0.0
        )

        desc = format_maturity_description(state)

        assert "primitive" in desc
        assert "0.60" in desc

    def test_format_advanced(self):
        """Test description for advanced civilization."""
        state = SocialMaturityState(
            maturity_level=1.2,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=1.1,
            stagnation_time_myr=0.0
        )

        desc = format_maturity_description(state)

        assert "advanced" in desc
        assert "balanced" in desc

    def test_format_dangerous(self):
        """Test description for dangerous civilization."""
        state = SocialMaturityState(
            maturity_level=0.3,
            growth_rate=0.01,
            maturity_to_kardashev_ratio=0.35,
            stagnation_time_myr=0.0
        )

        desc = format_maturity_description(state)

        assert "immature" in desc.lower()
