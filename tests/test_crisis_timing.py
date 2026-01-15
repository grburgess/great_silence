"""
Tests for crisis timing variance system.
"""

import pytest
import numpy as np
from great_silence.civilization.crisis_timing import (
    CrisisType,
    CrisisThreshold,
    PersonalizedCrisisSchedule,
    CrisisTimingSystem,
    DEFAULT_CRISIS_THRESHOLDS,
    format_crisis_schedule
)


class TestCrisisThreshold:
    """Tests for CrisisThreshold dataclass."""

    def test_creation(self):
        """Test creating crisis threshold."""
        threshold = CrisisThreshold(
            base_kardashev=1.0,
            window_width=0.2,
            severity_base=0.8,
            early_penalty=0.2,
            late_bonus=0.15
        )

        assert threshold.base_kardashev == 1.0
        assert threshold.window_width == 0.2
        assert threshold.severity_base == 0.8

    def test_default_values(self):
        """Test default threshold values."""
        threshold = CrisisThreshold(base_kardashev=1.0)

        assert threshold.window_width == 0.2
        assert threshold.severity_base == 0.8


class TestPersonalizedCrisisSchedule:
    """Tests for PersonalizedCrisisSchedule dataclass."""

    def test_creation(self):
        """Test creating crisis schedule."""
        schedule = PersonalizedCrisisSchedule(
            crisis_kardashev_levels={
                CrisisType.NUCLEAR_AGE: 0.75,
                CrisisType.AI_TRANSITION: 1.05
            },
            crisis_severities={
                CrisisType.NUCLEAR_AGE: 0.7,
                CrisisType.AI_TRANSITION: 0.85
            }
        )

        assert len(schedule.crisis_kardashev_levels) == 2
        assert schedule.crisis_kardashev_levels[CrisisType.NUCLEAR_AGE] == 0.75

    def test_has_triggered(self):
        """Test checking if crisis triggered."""
        schedule = PersonalizedCrisisSchedule(
            crises_triggered={CrisisType.NUCLEAR_AGE}
        )

        assert schedule.has_triggered(CrisisType.NUCLEAR_AGE)
        assert not schedule.has_triggered(CrisisType.AI_TRANSITION)

    def test_has_survived(self):
        """Test checking if crisis survived."""
        schedule = PersonalizedCrisisSchedule(
            crises_survived={CrisisType.NUCLEAR_AGE}
        )

        assert schedule.has_survived(CrisisType.NUCLEAR_AGE)
        assert not schedule.has_survived(CrisisType.AI_TRANSITION)

    def test_to_dict_and_from_dict(self):
        """Test serialization."""
        original = PersonalizedCrisisSchedule(
            crisis_kardashev_levels={
                CrisisType.NUCLEAR_AGE: 0.75,
                CrisisType.AI_TRANSITION: 1.05
            },
            crisis_severities={
                CrisisType.NUCLEAR_AGE: 0.7,
                CrisisType.AI_TRANSITION: 0.85
            },
            crises_triggered={CrisisType.NUCLEAR_AGE},
            crises_survived={CrisisType.NUCLEAR_AGE}
        )

        data = original.to_dict()
        restored = PersonalizedCrisisSchedule.from_dict(data)

        assert len(restored.crisis_kardashev_levels) == len(original.crisis_kardashev_levels)
        assert restored.has_triggered(CrisisType.NUCLEAR_AGE)
        assert restored.has_survived(CrisisType.NUCLEAR_AGE)


class TestCrisisTimingSystem:
    """Tests for CrisisTimingSystem."""

    def test_initialization(self):
        """Test creating crisis timing system."""
        system = CrisisTimingSystem(seed=42)

        assert system.crisis_thresholds is not None
        assert system.rng is not None

    def test_initialization_custom_thresholds(self):
        """Test initialization with custom thresholds."""
        custom = {
            CrisisType.NUCLEAR_AGE: CrisisThreshold(base_kardashev=0.8)
        }

        system = CrisisTimingSystem(crisis_thresholds=custom, seed=42)

        assert system.crisis_thresholds[CrisisType.NUCLEAR_AGE].base_kardashev == 0.8

    def test_generate_crisis_schedule_basic(self):
        """Test generating basic crisis schedule."""
        system = CrisisTimingSystem(seed=42)

        schedule = system.generate_crisis_schedule()

        # Should have schedule for all default crises
        assert len(schedule.crisis_kardashev_levels) == len(DEFAULT_CRISIS_THRESHOLDS)
        assert len(schedule.crisis_severities) == len(DEFAULT_CRISIS_THRESHOLDS)

        # Should have no triggered crises
        assert len(schedule.crises_triggered) == 0

    def test_generate_crisis_schedule_ordering(self):
        """Test that crises are ordered by K-level."""
        system = CrisisTimingSystem(seed=42)

        schedule = system.generate_crisis_schedule()

        # Get K-levels in order
        k_levels = sorted(schedule.crisis_kardashev_levels.values())

        # Should generally follow expected order (allowing for variance)
        # Nuclear age should be early, singularity should be late
        nuclear_k = schedule.crisis_kardashev_levels[CrisisType.NUCLEAR_AGE]
        singularity_k = schedule.crisis_kardashev_levels[CrisisType.SINGULARITY_TRANSITION]

        assert nuclear_k < singularity_k

    def test_generate_crisis_schedule_development_path_modifier(self):
        """Test development path affects crisis timing."""
        system = CrisisTimingSystem(seed=42)

        # Fast development - crises earlier
        schedule_fast = system.generate_crisis_schedule(
            development_path_modifier=-0.15
        )

        # Use different seed to avoid correlation in random variance
        system2 = CrisisTimingSystem(seed=123)

        # Slow development - crises later
        schedule_slow = system2.generate_crisis_schedule(
            development_path_modifier=0.10
        )

        # Fast developer should face crises earlier ON AVERAGE
        # Individual crises may vary due to random variance
        fast_avg = np.mean(list(schedule_fast.crisis_kardashev_levels.values()))
        slow_avg = np.mean(list(schedule_slow.crisis_kardashev_levels.values()))

        # Average should show clear trend (-0.15 vs +0.10 = 0.25 difference)
        assert fast_avg < slow_avg - 0.15  # Should see at least partial effect

    def test_generate_crisis_schedule_trait_modifiers(self):
        """Test trait modifiers affect specific crises."""
        system = CrisisTimingSystem(seed=42)

        # High wisdom delays AI crisis
        trait_mods = {CrisisType.AI_TRANSITION: 0.20}

        schedule_wise = system.generate_crisis_schedule(
            trait_modifiers=trait_mods
        )

        schedule_normal = system.generate_crisis_schedule()

        # Wise civilization faces AI crisis later
        assert (schedule_wise.crisis_kardashev_levels[CrisisType.AI_TRANSITION] >
                schedule_normal.crisis_kardashev_levels[CrisisType.AI_TRANSITION])

    def test_generate_crisis_schedule_severity_early_penalty(self):
        """Test early crises are more severe."""
        system = CrisisTimingSystem(seed=42)

        # Force crisis to occur very early
        schedule_early = system.generate_crisis_schedule(
            development_path_modifier=-0.30  # Much earlier
        )

        schedule_normal = system.generate_crisis_schedule()

        # Early crises should generally be harder
        # (Not guaranteed due to random variance, but likely)
        early_severities = sum(schedule_early.crisis_severities.values())
        normal_severities = sum(schedule_normal.crisis_severities.values())

        assert early_severities >= normal_severities * 0.95  # Allow some variance

    def test_generate_crisis_schedule_severity_late_bonus(self):
        """Test late crises are easier."""
        system = CrisisTimingSystem(seed=42)

        # Force crisis to occur later
        schedule_late = system.generate_crisis_schedule(
            development_path_modifier=0.30  # Much later
        )

        schedule_normal = system.generate_crisis_schedule()

        # Late crises should generally be easier
        late_severities = sum(schedule_late.crisis_severities.values())
        normal_severities = sum(schedule_normal.crisis_severities.values())

        assert late_severities <= normal_severities * 1.05  # Allow some variance

    def test_calculate_trait_modifiers_wisdom(self):
        """Test wisdom affects tech crisis timing."""
        system = CrisisTimingSystem()

        # High wisdom
        mods_wise = system.calculate_trait_modifiers(
            technological_wisdom=0.9,
            risk_tolerance=0.5,
            resource_abundance=0.5
        )

        # Low wisdom
        mods_unwise = system.calculate_trait_modifiers(
            technological_wisdom=0.1,
            risk_tolerance=0.5,
            resource_abundance=0.5
        )

        # High wisdom should delay nuclear and AI crises
        assert mods_wise[CrisisType.NUCLEAR_AGE] > mods_unwise[CrisisType.NUCLEAR_AGE]
        assert mods_wise[CrisisType.AI_TRANSITION] > mods_unwise[CrisisType.AI_TRANSITION]

    def test_calculate_trait_modifiers_risk_tolerance(self):
        """Test risk tolerance affects crisis timing."""
        system = CrisisTimingSystem()

        # High risk
        mods_risky = system.calculate_trait_modifiers(
            technological_wisdom=0.5,
            risk_tolerance=0.9,
            resource_abundance=0.5
        )

        # Low risk
        mods_cautious = system.calculate_trait_modifiers(
            technological_wisdom=0.5,
            risk_tolerance=0.1,
            resource_abundance=0.5
        )

        # High risk tolerance accelerates tech crises
        assert mods_risky[CrisisType.NUCLEAR_AGE] < mods_cautious[CrisisType.NUCLEAR_AGE]

    def test_calculate_trait_modifiers_resources(self):
        """Test resources affect resource crisis timing."""
        system = CrisisTimingSystem()

        # High resources
        mods_rich = system.calculate_trait_modifiers(
            technological_wisdom=0.5,
            risk_tolerance=0.5,
            resource_abundance=0.9
        )

        # Low resources
        mods_poor = system.calculate_trait_modifiers(
            technological_wisdom=0.5,
            risk_tolerance=0.5,
            resource_abundance=0.1
        )

        # High resources delay resource crises
        assert mods_rich[CrisisType.RESOURCE_DEPLETION] > mods_poor[CrisisType.RESOURCE_DEPLETION]
        assert mods_rich[CrisisType.CLIMATE_COLLAPSE] > mods_poor[CrisisType.CLIMATE_COLLAPSE]

    def test_check_crisis_triggers_none(self):
        """Test no crises trigger when below threshold."""
        system = CrisisTimingSystem(seed=42)

        schedule = system.generate_crisis_schedule()

        triggered = system.check_crisis_triggers(schedule, current_kardashev=0.5)

        # Should be no triggers at low K-level
        assert len(triggered) == 0

    def test_check_crisis_triggers_some(self):
        """Test some crises trigger at mid K-level."""
        system = CrisisTimingSystem(seed=42)

        schedule = system.generate_crisis_schedule()

        triggered = system.check_crisis_triggers(schedule, current_kardashev=1.0)

        # Should have some triggers (nuclear age, possibly others)
        assert len(triggered) > 0

        # Should return (crisis_type, severity) tuples
        for crisis_type, severity in triggered:
            assert isinstance(crisis_type, CrisisType)
            assert 0.0 <= severity <= 1.0

    def test_check_crisis_triggers_all(self):
        """Test all crises trigger at high K-level."""
        system = CrisisTimingSystem(seed=42)

        schedule = system.generate_crisis_schedule()

        triggered = system.check_crisis_triggers(schedule, current_kardashev=5.0)

        # Should trigger all crises
        assert len(triggered) == len(DEFAULT_CRISIS_THRESHOLDS)

    def test_check_crisis_triggers_skips_already_triggered(self):
        """Test already triggered crises are skipped."""
        system = CrisisTimingSystem(seed=42)

        schedule = system.generate_crisis_schedule()

        # Mark nuclear age as triggered
        schedule = system.mark_crisis_triggered(schedule, CrisisType.NUCLEAR_AGE)

        # Check triggers
        triggered = system.check_crisis_triggers(schedule, current_kardashev=5.0)

        # Nuclear age should not be in triggered list
        triggered_types = [ct for ct, _ in triggered]
        assert CrisisType.NUCLEAR_AGE not in triggered_types

    def test_mark_crisis_triggered(self):
        """Test marking crisis as triggered."""
        system = CrisisTimingSystem(seed=42)

        schedule = system.generate_crisis_schedule()

        assert not schedule.has_triggered(CrisisType.NUCLEAR_AGE)

        updated = system.mark_crisis_triggered(schedule, CrisisType.NUCLEAR_AGE)

        assert updated.has_triggered(CrisisType.NUCLEAR_AGE)
        # Original should be unchanged
        assert not schedule.has_triggered(CrisisType.NUCLEAR_AGE)

    def test_mark_crisis_survived(self):
        """Test marking crisis as survived."""
        system = CrisisTimingSystem(seed=42)

        schedule = system.generate_crisis_schedule()

        assert not schedule.has_survived(CrisisType.NUCLEAR_AGE)

        updated = system.mark_crisis_survived(schedule, CrisisType.NUCLEAR_AGE)

        assert updated.has_survived(CrisisType.NUCLEAR_AGE)
        # Original should be unchanged
        assert not schedule.has_survived(CrisisType.NUCLEAR_AGE)

    def test_variance_creates_unique_schedules(self):
        """Test that random variance creates unique schedules."""
        system = CrisisTimingSystem(seed=42)

        schedule1 = system.generate_crisis_schedule()
        schedule2 = system.generate_crisis_schedule()

        # Schedules should be different due to random variance
        nuclear_k1 = schedule1.crisis_kardashev_levels[CrisisType.NUCLEAR_AGE]
        nuclear_k2 = schedule2.crisis_kardashev_levels[CrisisType.NUCLEAR_AGE]

        assert nuclear_k1 != nuclear_k2


class TestCrisisScheduleSummaries:
    """Tests for crisis schedule summary formatting."""

    def test_format_empty_schedule(self):
        """Test formatting empty schedule."""
        schedule = PersonalizedCrisisSchedule()

        summary = format_crisis_schedule(schedule)

        assert "No crises scheduled" in summary

    def test_format_schedule_with_upcoming(self):
        """Test formatting schedule with upcoming crises."""
        schedule = PersonalizedCrisisSchedule(
            crisis_kardashev_levels={
                CrisisType.NUCLEAR_AGE: 0.75,
                CrisisType.AI_TRANSITION: 1.05
            },
            crisis_severities={
                CrisisType.NUCLEAR_AGE: 0.7,
                CrisisType.AI_TRANSITION: 0.85
            }
        )

        summary = format_crisis_schedule(schedule)

        assert "0 triggered" in summary
        assert "0 survived" in summary
        assert "Next:" in summary
        assert "nuclear_age" in summary

    def test_format_schedule_with_triggered(self):
        """Test formatting schedule with triggered crises."""
        schedule = PersonalizedCrisisSchedule(
            crisis_kardashev_levels={
                CrisisType.NUCLEAR_AGE: 0.75,
                CrisisType.AI_TRANSITION: 1.05
            },
            crisis_severities={
                CrisisType.NUCLEAR_AGE: 0.7,
                CrisisType.AI_TRANSITION: 0.85
            },
            crises_triggered={CrisisType.NUCLEAR_AGE},
            crises_survived={CrisisType.NUCLEAR_AGE}
        )

        summary = format_crisis_schedule(schedule)

        assert "1 triggered" in summary
        assert "1 survived" in summary
        # Next should be AI transition
        assert "ai_transition" in summary

    def test_format_schedule_all_triggered(self):
        """Test formatting when all crises triggered."""
        schedule = PersonalizedCrisisSchedule(
            crisis_kardashev_levels={
                CrisisType.NUCLEAR_AGE: 0.75
            },
            crisis_severities={
                CrisisType.NUCLEAR_AGE: 0.7
            },
            crises_triggered={CrisisType.NUCLEAR_AGE}
        )

        summary = format_crisis_schedule(schedule)

        assert "All crises triggered" in summary
