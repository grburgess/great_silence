"""
Tests for crisis learning and experience system.
"""

import pytest
import numpy as np
from great_silence.civilization.crisis_experience import (
    CrisisExperience,
    CrisisLearningSystem,
    format_experience_summary,
    calculate_cumulative_survival_improvement
)


class TestCrisisExperience:
    """Tests for CrisisExperience dataclass."""

    def test_experience_creation(self):
        """Test creating experience record."""
        exp = CrisisExperience(
            crises_survived=2,
            crisis_scars=['nuclear_age', 'ai_transition'],
            crisis_type_counts={'nuclear_age': 1, 'ai_transition': 1},
            total_severity_overcome=1.5
        )

        assert exp.crises_survived == 2
        assert len(exp.crisis_scars) == 2
        assert exp.crisis_type_counts['nuclear_age'] == 1

    def test_has_survived_before(self):
        """Test checking if crisis type was survived."""
        exp = CrisisExperience(
            crisis_scars=['nuclear_age', 'ai_transition']
        )

        assert exp.has_survived_before('nuclear_age')
        assert exp.has_survived_before('ai_transition')
        assert not exp.has_survived_before('stellar_engineering')

    def test_get_crisis_type_count(self):
        """Test getting count for specific crisis type."""
        exp = CrisisExperience(
            crisis_type_counts={'nuclear_age': 2, 'ai_transition': 1}
        )

        assert exp.get_crisis_type_count('nuclear_age') == 2
        assert exp.get_crisis_type_count('ai_transition') == 1
        assert exp.get_crisis_type_count('unknown') == 0

    def test_general_experience_bonus_scaling(self):
        """Test that general bonus scales with experience."""
        # No experience
        exp0 = CrisisExperience(crises_survived=0)
        assert exp0.get_general_experience_bonus() == 0.0

        # One crisis
        exp1 = CrisisExperience(crises_survived=1, total_severity_overcome=0.8)
        bonus1 = exp1.get_general_experience_bonus()
        assert bonus1 > 0.0

        # Multiple crises
        exp3 = CrisisExperience(crises_survived=3, total_severity_overcome=2.4)
        bonus3 = exp3.get_general_experience_bonus()
        assert bonus3 > bonus1

        # Check cap
        exp10 = CrisisExperience(crises_survived=10, total_severity_overcome=8.0)
        bonus10 = exp10.get_general_experience_bonus()
        assert bonus10 <= 0.7  # Base cap 0.5 + severity cap 0.2

    def test_specific_experience_bonus(self):
        """Test crisis-specific experience bonus."""
        # Never survived this type
        exp0 = CrisisExperience(crisis_type_counts={})
        assert exp0.get_specific_experience_bonus('nuclear_age') == 0.0

        # Survived once
        exp1 = CrisisExperience(crisis_type_counts={'nuclear_age': 1})
        assert exp1.get_specific_experience_bonus('nuclear_age') == 0.25

        # Survived twice
        exp2 = CrisisExperience(crisis_type_counts={'nuclear_age': 2})
        assert exp2.get_specific_experience_bonus('nuclear_age') == 0.35

        # Survived many times
        exp5 = CrisisExperience(crisis_type_counts={'nuclear_age': 5})
        assert exp5.get_specific_experience_bonus('nuclear_age') == 0.45

    def test_total_survival_bonus(self):
        """Test combined survival bonus."""
        exp = CrisisExperience(
            crises_survived=2,
            crisis_type_counts={'nuclear_age': 1},
            total_severity_overcome=1.5
        )

        # For nuclear age (has specific experience)
        bonus_nuclear = exp.get_total_survival_bonus('nuclear_age')
        assert bonus_nuclear > 0.0

        # For different crisis (only general experience)
        bonus_ai = exp.get_total_survival_bonus('ai_transition')
        assert bonus_ai > 0.0
        assert bonus_nuclear > bonus_ai  # Specific experience helps more

    def test_to_dict_and_from_dict(self):
        """Test serialization."""
        original = CrisisExperience(
            crises_survived=2,
            crisis_scars=['nuclear_age', 'ai_transition'],
            crisis_type_counts={'nuclear_age': 1, 'ai_transition': 1},
            last_crisis_time_myr=1500.0,
            total_severity_overcome=1.5,
            near_misses=1
        )

        data = original.to_dict()
        restored = CrisisExperience.from_dict(data)

        assert restored.crises_survived == original.crises_survived
        assert restored.crisis_scars == original.crisis_scars
        assert restored.crisis_type_counts == original.crisis_type_counts
        assert restored.last_crisis_time_myr == original.last_crisis_time_myr
        assert restored.total_severity_overcome == original.total_severity_overcome
        assert restored.near_misses == original.near_misses


class TestCrisisLearningSystem:
    """Tests for CrisisLearningSystem."""

    def test_initialization(self):
        """Test creating learning system."""
        system = CrisisLearningSystem(
            experience_decay_timescale_gyr=2.0,
            near_miss_learning_rate=0.5,
            seed=42
        )

        assert system.experience_decay_timescale_gyr == 2.0
        assert system.near_miss_learning_rate == 0.5
        assert system.rng is not None

    def test_record_crisis_success_first_time(self):
        """Test recording first crisis survival."""
        system = CrisisLearningSystem(seed=42)

        initial = CrisisExperience()

        updated = system.record_crisis_success(
            experience=initial,
            crisis_type='nuclear_age',
            crisis_severity=0.8,
            current_time_myr=1500.0,
            was_close_call=False
        )

        assert updated.crises_survived == 1
        assert 'nuclear_age' in updated.crisis_scars
        assert updated.crisis_type_counts['nuclear_age'] == 1
        assert updated.last_crisis_time_myr == 1500.0
        assert updated.total_severity_overcome == 0.8
        assert updated.near_misses == 0

    def test_record_crisis_success_multiple_times(self):
        """Test recording multiple crisis survivals."""
        system = CrisisLearningSystem(seed=42)

        exp = CrisisExperience()

        # First crisis
        exp = system.record_crisis_success(exp, 'nuclear_age', 0.8, 1500.0, False)

        # Second crisis (different type)
        exp = system.record_crisis_success(exp, 'ai_transition', 0.9, 1600.0, False)

        # Third crisis (same as first)
        exp = system.record_crisis_success(exp, 'nuclear_age', 0.7, 1700.0, False)

        assert exp.crises_survived == 3
        assert exp.crisis_type_counts['nuclear_age'] == 2
        assert exp.crisis_type_counts['ai_transition'] == 1
        assert len(exp.crisis_scars) == 3

    def test_record_crisis_near_miss(self):
        """Test recording near-miss crisis."""
        system = CrisisLearningSystem(
            near_miss_learning_rate=0.5,
            seed=42
        )

        exp = CrisisExperience()

        exp = system.record_crisis_success(
            exp, 'nuclear_age', 0.8, 1500.0, was_close_call=True
        )

        # Should record survival
        assert exp.crises_survived == 1
        assert exp.near_misses == 1

        # But learn less (0.5x learning rate)
        assert exp.total_severity_overcome == pytest.approx(0.4, abs=0.01)

    def test_apply_experience_decay_no_decay(self):
        """Test that recent experience doesn't decay."""
        system = CrisisLearningSystem(seed=42)

        exp = CrisisExperience(
            crises_survived=2,
            last_crisis_time_myr=1500.0,
            total_severity_overcome=1.5
        )

        # Only 50 Myr later (0.05 Gyr)
        decayed = system.apply_experience_decay(exp, 1550.0)

        # Too recent for decay
        assert decayed.total_severity_overcome == exp.total_severity_overcome

    def test_apply_experience_decay_long_time(self):
        """Test experience decay over long time."""
        system = CrisisLearningSystem(
            experience_decay_timescale_gyr=2.0,
            seed=42
        )

        exp = CrisisExperience(
            crises_survived=2,
            last_crisis_time_myr=1000.0,
            total_severity_overcome=2.0
        )

        # 2 Gyr later (half-life)
        decayed = system.apply_experience_decay(exp, 3000.0)

        # Should decay by ~50%
        assert decayed.total_severity_overcome < exp.total_severity_overcome
        assert decayed.total_severity_overcome == pytest.approx(2.0 * np.exp(-1), abs=0.1)

        # But scars and counts remain
        assert decayed.crises_survived == exp.crises_survived

    def test_learning_from_observation(self):
        """Test vicarious learning from observing other civilizations."""
        system = CrisisLearningSystem(seed=42)

        observer = CrisisExperience()

        # Observe another civilization survive AI crisis
        updated = system.calculate_learning_from_observation(
            observer_experience=observer,
            observed_crisis_type='ai_transition',
            observed_severity=0.9
        )

        # Should gain some experience
        assert updated.total_severity_overcome > 0
        assert updated.total_severity_overcome < 0.9  # Less than direct experience

        # Should get fractional count
        assert updated.crisis_type_counts.get('ai_transition', 0) > 0

        # But no scar (didn't survive it ourselves)
        assert 'ai_transition' not in updated.crisis_scars

    def test_learning_from_observation_already_experienced(self):
        """Test that we don't learn from crises we already survived."""
        system = CrisisLearningSystem(seed=42)

        observer = CrisisExperience(
            crisis_scars=['ai_transition']
        )

        # Try to learn from observing AI crisis (already know it)
        updated = system.calculate_learning_from_observation(
            observer, 'ai_transition', 0.9
        )

        # No change
        assert updated.total_severity_overcome == observer.total_severity_overcome

    def test_estimate_difficulty_perception_experienced(self):
        """Test perceived difficulty for experienced civilization."""
        system = CrisisLearningSystem(seed=42)

        exp = CrisisExperience(
            crisis_scars=['nuclear_age', 'nuclear_age'],
            crisis_type_counts={'nuclear_age': 2}
        )

        perceived = system.estimate_crisis_difficulty_perception(
            exp, 'nuclear_age', 0.8
        )

        # Should perceive as easier (2 survivals * 0.15 = 0.3 confidence)
        # 0.8 * (1 - 0.3) = 0.56
        assert perceived < 0.8
        assert perceived == pytest.approx(0.56, abs=0.01)

    def test_estimate_difficulty_perception_inexperienced(self):
        """Test perceived difficulty for inexperienced civilization."""
        system = CrisisLearningSystem(seed=42)

        exp = CrisisExperience()

        perceived = system.estimate_crisis_difficulty_perception(
            exp, 'nuclear_age', 0.8
        )

        # Should perceive as harder (fear/uncertainty)
        assert perceived > 0.8

    def test_should_trigger_preventive_action_inexperienced(self):
        """Test that inexperienced civs don't take preventive action."""
        system = CrisisLearningSystem(seed=42)

        exp = CrisisExperience()  # Never survived this crisis

        should_act, advance = system.should_trigger_preventive_action(
            exp,
            crisis_type='ai_transition',
            current_kardashev=0.95,
            crisis_kardashev_threshold=1.05
        )

        assert not should_act

    def test_should_trigger_preventive_action_experienced(self):
        """Test that experienced civs take preventive action."""
        system = CrisisLearningSystem(seed=42)

        exp = CrisisExperience(
            crisis_scars=['ai_transition', 'ai_transition'],  # Survived twice
            crisis_type_counts={'ai_transition': 2}
        )

        # Approaching the crisis threshold
        should_act, advance = system.should_trigger_preventive_action(
            exp,
            crisis_type='ai_transition',
            current_kardashev=0.96,
            crisis_kardashev_threshold=1.05
        )

        # Should detect in advance (2 survivals * 0.05 = 0.10 advance detection)
        assert should_act
        assert advance == pytest.approx(0.10, abs=0.01)

    def test_should_trigger_preventive_action_too_far(self):
        """Test that preventive action only triggers when close enough."""
        system = CrisisLearningSystem(seed=42)

        exp = CrisisExperience(
            crisis_type_counts={'ai_transition': 1}
        )

        # Too far from crisis
        should_act, advance = system.should_trigger_preventive_action(
            exp,
            crisis_type='ai_transition',
            current_kardashev=0.80,  # Far below threshold
            crisis_kardashev_threshold=1.05
        )

        assert not should_act


class TestExperienceSummaries:
    """Tests for experience summary functions."""

    def test_format_inexperienced(self):
        """Test summary for inexperienced civilization."""
        exp = CrisisExperience()

        summary = format_experience_summary(exp)

        assert "inexperienced" in summary

    def test_format_novice(self):
        """Test summary for novice (1 crisis)."""
        exp = CrisisExperience(
            crises_survived=1,
            crisis_scars=['nuclear_age'],
            crisis_type_counts={'nuclear_age': 1}
        )

        summary = format_experience_summary(exp)

        assert "novice" in summary
        assert "nuclear_age" in summary

    def test_format_veteran(self):
        """Test summary for veteran (many crises)."""
        exp = CrisisExperience(
            crises_survived=6,
            crisis_scars=['nuclear_age', 'ai_transition'] * 3,
            crisis_type_counts={'nuclear_age': 3, 'ai_transition': 3},
            near_misses=2
        )

        summary = format_experience_summary(exp)

        assert "veteran" in summary
        assert "6 crises" in summary
        assert "2 near-misses" in summary

    def test_calculate_cumulative_survival_improvement(self):
        """Test final survival probability calculation."""
        exp = CrisisExperience(
            crises_survived=2,
            crisis_type_counts={'nuclear_age': 1},
            total_severity_overcome=1.5
        )

        # Base 50% survival
        base = 0.5

        # With experience (should improve)
        improved = calculate_cumulative_survival_improvement(
            exp, 'nuclear_age', base
        )

        assert improved > base
        assert improved <= 1.0

    def test_calculate_cumulative_survival_improvement_capped(self):
        """Test that survival probability caps at 1.0."""
        exp = CrisisExperience(
            crises_survived=10,
            crisis_type_counts={'nuclear_age': 5},
            total_severity_overcome=8.0
        )

        # Base 80% survival with massive experience
        improved = calculate_cumulative_survival_improvement(
            exp, 'nuclear_age', 0.8
        )

        # Should cap at 1.0
        assert improved == 1.0

    def test_calculate_cumulative_survival_improvement_no_experience(self):
        """Test that no experience means no improvement."""
        exp = CrisisExperience()

        improved = calculate_cumulative_survival_improvement(
            exp, 'nuclear_age', 0.5
        )

        # No change
        assert improved == 0.5
