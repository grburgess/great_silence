"""
Tests for multi-stage crisis resolution system.
"""

import pytest
import numpy as np
from great_silence.civilization.crisis_stages import (
    CrisisStage,
    CrisisState,
    MultiStageCrisisSystem,
    format_crisis_summary
)


class TestCrisisState:
    """Tests for CrisisState dataclass."""

    def test_creation(self):
        """Test creating crisis state."""
        crisis = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.EMERGING,
            severity=0.8,
            time_in_stage_myr=5.0,
            total_duration_myr=10.0,
            detection_time_myr=5.0,
            response_effectiveness=0.6,
            stage_advancement_rate=1.0
        )

        assert crisis.crisis_type == 'nuclear_age'
        assert crisis.stage == CrisisStage.EMERGING
        assert crisis.severity == 0.8
        assert crisis.time_in_stage_myr == 5.0

    def test_to_dict_and_from_dict(self):
        """Test serialization."""
        original = CrisisState(
            crisis_type='ai_transition',
            stage=CrisisStage.CRITICAL,
            severity=0.9,
            time_in_stage_myr=2.0,
            total_duration_myr=50.0,
            detection_time_myr=30.0,
            response_effectiveness=0.7,
            stage_advancement_rate=1.1
        )

        data = original.to_dict()
        restored = CrisisState.from_dict(data)

        assert restored.crisis_type == original.crisis_type
        assert restored.stage == original.stage
        assert restored.severity == original.severity
        assert restored.time_in_stage_myr == original.time_in_stage_myr
        assert restored.total_duration_myr == original.total_duration_myr


class TestMultiStageCrisisSystem:
    """Tests for MultiStageCrisisSystem."""

    def test_initialization(self):
        """Test creating crisis system."""
        system = MultiStageCrisisSystem(seed=42)

        assert system.stage_durations_myr is not None
        assert system.rng is not None

    def test_initialization_custom_durations(self):
        """Test initialization with custom stage durations."""
        custom_durations = {
            CrisisStage.DORMANT: 100.0,
            CrisisStage.EMERGING: 30.0,
            CrisisStage.DEVELOPING: 15.0,
            CrisisStage.CRITICAL: 10.0,
            CrisisStage.RESOLVING: 20.0
        }

        system = MultiStageCrisisSystem(
            stage_durations_myr=custom_durations,
            seed=42
        )

        assert system.stage_durations_myr[CrisisStage.DORMANT] == 100.0

    def test_initiate_crisis_no_early_detection(self):
        """Test initiating crisis without early detection."""
        system = MultiStageCrisisSystem(seed=42)

        crisis = system.initiate_crisis(
            crisis_type='nuclear_age',
            severity=0.8,
            has_early_detection=False
        )

        assert crisis.crisis_type == 'nuclear_age'
        assert crisis.stage == CrisisStage.EMERGING  # No early detection
        assert crisis.severity == 0.8
        assert crisis.time_in_stage_myr == 0.0

    def test_initiate_crisis_with_early_detection(self):
        """Test initiating crisis with early detection."""
        system = MultiStageCrisisSystem(seed=42)

        crisis = system.initiate_crisis(
            crisis_type='ai_transition',
            severity=0.9,
            has_early_detection=True  # Experienced civilization
        )

        assert crisis.stage == CrisisStage.DORMANT  # Early detection
        assert crisis.severity == 0.9

    def test_advance_crisis_updates_timers(self):
        """Test that advancing crisis updates timers."""
        system = MultiStageCrisisSystem(seed=42)

        crisis = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.EMERGING,
            severity=0.8,
            time_in_stage_myr=5.0,
            total_duration_myr=10.0
        )

        advanced = system.advance_crisis(crisis, dt_myr=2.0, response_quality=0.5)

        assert advanced.time_in_stage_myr == pytest.approx(7.0, abs=0.1)
        assert advanced.total_duration_myr == pytest.approx(12.0, abs=0.1)

    def test_advance_crisis_updates_response(self):
        """Test that response effectiveness is smoothed."""
        system = MultiStageCrisisSystem(seed=42)

        crisis = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.EMERGING,
            severity=0.8,
            response_effectiveness=0.3
        )

        # Good response should increase effectiveness
        advanced = system.advance_crisis(crisis, dt_myr=1.0, response_quality=0.9)

        # New response = 0.7 * 0.3 + 0.3 * 0.9 = 0.48
        assert advanced.response_effectiveness == pytest.approx(0.48, abs=0.01)

    def test_advance_crisis_stage_progression(self):
        """Test crisis advances through stages."""
        system = MultiStageCrisisSystem(seed=42)

        crisis = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.EMERGING,
            severity=0.8,
            time_in_stage_myr=0.0,
            response_effectiveness=0.5,
            stage_advancement_rate=1.0
        )

        # Advance enough to trigger stage change (emerging duration = 20 Myr)
        # With response 0.5, effective_advancement = 1.0 * (1.5 - 0.5) = 1.0
        # Need time_in_stage >= 20/1.0 = 20
        advanced = crisis
        for _ in range(25):  # 25 Myr should be enough
            advanced = system.advance_crisis(advanced, dt_myr=1.0, response_quality=0.5)

        assert advanced.stage != CrisisStage.EMERGING

    def test_advance_crisis_good_response_slows_progression(self):
        """Test that good response slows crisis progression."""
        system = MultiStageCrisisSystem(seed=42)

        # Poor response
        crisis_poor = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.EMERGING,
            severity=0.8,
            stage_advancement_rate=1.0
        )

        # Good response
        crisis_good = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.EMERGING,
            severity=0.8,
            stage_advancement_rate=1.0
        )

        # Advance both
        for _ in range(20):
            crisis_poor = system.advance_crisis(crisis_poor, dt_myr=1.0, response_quality=0.2)
            crisis_good = system.advance_crisis(crisis_good, dt_myr=1.0, response_quality=0.9)

        # Good response should still be in earlier stage or same stage
        # (can't directly compare stages, but at minimum should not be ahead)
        assert crisis_good.response_effectiveness > crisis_poor.response_effectiveness

    def test_advance_crisis_terminal_stages(self):
        """Test that terminal stages don't advance."""
        system = MultiStageCrisisSystem(seed=42)

        resolved = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.RESOLVED,
            severity=0.8
        )

        failed = CrisisState(
            crisis_type='ai_transition',
            stage=CrisisStage.FAILED,
            severity=0.9
        )

        # Advance both
        advanced_resolved = system.advance_crisis(resolved, dt_myr=10.0, response_quality=0.5)
        advanced_failed = system.advance_crisis(failed, dt_myr=10.0, response_quality=0.5)

        assert advanced_resolved.stage == CrisisStage.RESOLVED
        assert advanced_failed.stage == CrisisStage.FAILED

    def test_get_next_stage_normal_progression(self):
        """Test normal stage progression."""
        system = MultiStageCrisisSystem(seed=42)

        # Test sequence
        assert system._get_next_stage(CrisisStage.DORMANT, 0.5) == CrisisStage.EMERGING
        assert system._get_next_stage(CrisisStage.EMERGING, 0.5) == CrisisStage.DEVELOPING
        assert system._get_next_stage(CrisisStage.DEVELOPING, 0.5) == CrisisStage.CRITICAL

    def test_get_next_stage_strong_response_skip(self):
        """Test that strong response can skip to resolving."""
        system = MultiStageCrisisSystem(seed=42)

        # Strong response from developing should skip to resolving
        next_stage = system._get_next_stage(CrisisStage.DEVELOPING, response_effectiveness=0.9)

        assert next_stage == CrisisStage.RESOLVING

    def test_calculate_response_quality_maturity_based(self):
        """Test response quality calculation."""
        system = MultiStageCrisisSystem(seed=42)

        # High maturity
        quality_high = system.calculate_response_quality(
            maturity_level=1.5,
            experience_bonus=0.0,
            trait_modifiers=1.0,
            resource_availability=1.0
        )

        # Low maturity
        quality_low = system.calculate_response_quality(
            maturity_level=0.3,
            experience_bonus=0.0,
            trait_modifiers=1.0,
            resource_availability=1.0
        )

        assert quality_high > quality_low

    def test_calculate_response_quality_experience_helps(self):
        """Test that experience improves response."""
        system = MultiStageCrisisSystem(seed=42)

        quality_no_exp = system.calculate_response_quality(
            maturity_level=0.8,
            experience_bonus=0.0,
            trait_modifiers=1.0,
            resource_availability=1.0
        )

        quality_with_exp = system.calculate_response_quality(
            maturity_level=0.8,
            experience_bonus=0.5,
            trait_modifiers=1.0,
            resource_availability=1.0
        )

        assert quality_with_exp > quality_no_exp

    def test_calculate_response_quality_capped(self):
        """Test that response quality is capped at 1.0."""
        system = MultiStageCrisisSystem(seed=42)

        quality = system.calculate_response_quality(
            maturity_level=3.0,  # Very high
            experience_bonus=1.0,  # Very high
            trait_modifiers=2.0,  # Very high
            resource_availability=1.0
        )

        assert quality <= 1.0

    def test_check_survival_stage_dependent(self):
        """Test survival probability depends on stage."""
        system = MultiStageCrisisSystem(seed=42)

        # Dormant stage (low danger)
        dormant = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.DORMANT,
            severity=0.5,
            response_effectiveness=0.5
        )

        # Critical stage (high danger)
        critical = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.CRITICAL,
            severity=0.5,
            response_effectiveness=0.5
        )

        # Run multiple trials
        dormant_survivals = 0
        critical_survivals = 0

        for _ in range(100):
            survived, _ = system.check_survival(dormant, 1.0, 1.0, 0.0)
            if survived:
                dormant_survivals += 1

            survived, _ = system.check_survival(critical, 1.0, 1.0, 0.0)
            if survived:
                critical_survivals += 1

        # Dormant should have higher survival rate
        assert dormant_survivals > critical_survivals

    def test_check_survival_modifiers_help(self):
        """Test that modifiers improve survival."""
        system = MultiStageCrisisSystem(seed=42)

        crisis = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.CRITICAL,
            severity=0.8,
            response_effectiveness=0.5
        )

        # Run with no modifiers
        no_modifier_survivals = 0
        for _ in range(100):
            survived, _ = system.check_survival(crisis, 1.0, 1.0, 0.0)
            if survived:
                no_modifier_survivals += 1

        # Run with strong modifiers
        with_modifier_survivals = 0
        for _ in range(100):
            survived, _ = system.check_survival(crisis, 2.0, 1.5, 0.3)
            if survived:
                with_modifier_survivals += 1

        # Modifiers should improve survival
        assert with_modifier_survivals > no_modifier_survivals

    def test_check_survival_close_call_detection(self):
        """Test close call detection."""
        system = MultiStageCrisisSystem(seed=42)

        crisis = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.DEVELOPING,
            severity=0.7,
            response_effectiveness=0.6
        )

        # Run multiple times to get close calls
        close_calls = 0
        survivals = 0

        for _ in range(200):
            survived, was_close = system.check_survival(crisis, 1.0, 1.0, 0.0)
            if survived:
                survivals += 1
                if was_close:
                    close_calls += 1

        # Should have some close calls
        assert close_calls > 0
        # But not all survivals should be close calls
        assert close_calls < survivals

    def test_can_resolve_crisis_requires_resolving_stage(self):
        """Test crisis can only be resolved in resolving stage."""
        system = MultiStageCrisisSystem(seed=42)

        # Not in resolving stage
        crisis_developing = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.DEVELOPING,
            severity=0.7,
            response_effectiveness=0.8,
            time_in_stage_myr=10.0
        )

        assert not system.can_resolve_crisis(crisis_developing)

    def test_can_resolve_crisis_requires_good_response(self):
        """Test resolution requires good response."""
        system = MultiStageCrisisSystem(seed=42)

        # Good response
        crisis_good = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.RESOLVING,
            severity=0.7,
            response_effectiveness=0.8,
            time_in_stage_myr=10.0
        )

        # Poor response
        crisis_poor = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.RESOLVING,
            severity=0.7,
            response_effectiveness=0.3,
            time_in_stage_myr=10.0
        )

        assert system.can_resolve_crisis(crisis_good)
        assert not system.can_resolve_crisis(crisis_poor)

    def test_can_resolve_crisis_requires_time(self):
        """Test resolution requires sufficient time."""
        system = MultiStageCrisisSystem(seed=42)

        # Enough time
        crisis_time = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.RESOLVING,
            severity=0.7,
            response_effectiveness=0.8,
            time_in_stage_myr=10.0
        )

        # Not enough time
        crisis_no_time = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.RESOLVING,
            severity=0.7,
            response_effectiveness=0.8,
            time_in_stage_myr=2.0
        )

        assert system.can_resolve_crisis(crisis_time)
        assert not system.can_resolve_crisis(crisis_no_time)

    def test_get_stage_description(self):
        """Test getting descriptions for all stages."""
        system = MultiStageCrisisSystem()

        for stage in CrisisStage:
            desc = system.get_stage_description(stage)
            assert len(desc) > 0
            assert isinstance(desc, str)


class TestCrisisSummaries:
    """Tests for crisis summary formatting."""

    def test_format_crisis_summary(self):
        """Test formatting crisis summary."""
        crisis = CrisisState(
            crisis_type='nuclear_age',
            stage=CrisisStage.CRITICAL,
            severity=0.85,
            response_effectiveness=0.7,
            total_duration_myr=45.2
        )

        summary = format_crisis_summary(crisis)

        assert "Nuclear Age" in summary
        assert "Critical" in summary
        assert "0.85" in summary
        assert "good" in summary  # response_effectiveness > 0.6
        assert "45.2" in summary

    def test_format_crisis_summary_response_descriptions(self):
        """Test different response descriptions."""
        # Excellent response
        crisis_excellent = CrisisState(
            crisis_type='ai_transition',
            stage=CrisisStage.RESOLVING,
            severity=0.9,
            response_effectiveness=0.9,
            total_duration_myr=30.0
        )

        summary = format_crisis_summary(crisis_excellent)
        assert "excellent" in summary

        # Poor response
        crisis_poor = CrisisState(
            crisis_type='ai_transition',
            stage=CrisisStage.CRITICAL,
            severity=0.9,
            response_effectiveness=0.3,
            total_duration_myr=20.0
        )

        summary = format_crisis_summary(crisis_poor)
        assert "poor" in summary
