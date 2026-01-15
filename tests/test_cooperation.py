"""
Tests for cooperative survival mechanics.
"""

import pytest
import numpy as np
from great_silence.civilization.cooperation import (
    CooperationType,
    CooperationRecord,
    CooperationHistory,
    CooperationSystem,
    format_cooperation_summary
)


class TestCooperationRecord:
    """Tests for CooperationRecord dataclass."""

    def test_creation(self):
        """Test creating cooperation record."""
        record = CooperationRecord(
            time_myr=1000.0,
            helper_id=1,
            receiver_id=2,
            cooperation_type=CooperationType.KNOWLEDGE_SHARING,
            effectiveness=0.8,
            distance_pc=50.0
        )

        assert record.time_myr == 1000.0
        assert record.helper_id == 1
        assert record.receiver_id == 2
        assert record.effectiveness == 0.8


class TestCooperationHistory:
    """Tests for CooperationHistory dataclass."""

    def test_creation(self):
        """Test creating cooperation history."""
        history = CooperationHistory()

        assert len(history.received_aid) == 0
        assert len(history.given_aid) == 0
        assert len(history.active_allies) == 0

    def test_has_received_aid_from(self):
        """Test checking aid reception."""
        record = CooperationRecord(
            time_myr=1000.0,
            helper_id=5,
            receiver_id=1,
            cooperation_type=CooperationType.CRISIS_INTERVENTION,
            effectiveness=0.7,
            distance_pc=100.0
        )

        history = CooperationHistory(received_aid=[record])

        assert history.has_received_aid_from(5)
        assert not history.has_received_aid_from(3)

    def test_has_given_aid_to(self):
        """Test checking aid given."""
        record = CooperationRecord(
            time_myr=1000.0,
            helper_id=1,
            receiver_id=7,
            cooperation_type=CooperationType.TECHNOLOGY_TRANSFER,
            effectiveness=0.6,
            distance_pc=200.0
        )

        history = CooperationHistory(given_aid=[record])

        assert history.has_given_aid_to(7)
        assert not history.has_given_aid_to(2)

    def test_is_allied_with(self):
        """Test checking alliance status."""
        history = CooperationHistory(active_allies={3, 5, 7})

        assert history.is_allied_with(3)
        assert history.is_allied_with(5)
        assert not history.is_allied_with(2)

    def test_get_aid_counts(self):
        """Test getting aid counts."""
        received = [
            CooperationRecord(1000.0, 5, 1, CooperationType.KNOWLEDGE_SHARING, 0.8, 50.0),
            CooperationRecord(1100.0, 3, 1, CooperationType.CRISIS_INTERVENTION, 0.7, 100.0)
        ]

        given = [
            CooperationRecord(1050.0, 1, 2, CooperationType.TECHNOLOGY_TRANSFER, 0.6, 75.0)
        ]

        history = CooperationHistory(received_aid=received, given_aid=given)

        assert history.get_aid_received_count() == 2
        assert history.get_aid_given_count() == 1


class TestCooperationSystem:
    """Tests for CooperationSystem."""

    def test_initialization(self):
        """Test creating cooperation system."""
        system = CooperationSystem(seed=42)

        assert system.max_cooperation_distance_pc == 1000.0
        assert system.alliance_formation_threshold == 0.7
        assert system.rng is not None

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        system = CooperationSystem(
            max_cooperation_distance_pc=500.0,
            alliance_formation_threshold=0.8,
            reciprocity_bonus=0.4,
            seed=42
        )

        assert system.max_cooperation_distance_pc == 500.0
        assert system.alliance_formation_threshold == 0.8
        assert system.reciprocity_bonus == 0.4

    def test_can_cooperate_too_far(self):
        """Test cooperation blocked by distance."""
        system = CooperationSystem(max_cooperation_distance_pc=1000.0)

        can_coop = system.can_cooperate(
            distance_pc=2000.0,  # Too far
            helper_kardashev=1.5,
            receiver_kardashev=1.0
        )

        assert not can_coop

    def test_can_cooperate_helper_too_primitive(self):
        """Test cooperation blocked by low helper tech."""
        system = CooperationSystem()

        can_coop = system.can_cooperate(
            distance_pc=100.0,
            helper_kardashev=0.5,  # Too low
            receiver_kardashev=0.4
        )

        assert not can_coop

    def test_can_cooperate_receiver_too_advanced(self):
        """Test cooperation blocked by advanced receiver."""
        system = CooperationSystem()

        can_coop = system.can_cooperate(
            distance_pc=100.0,
            helper_kardashev=1.0,
            receiver_kardashev=2.0  # Too far ahead
        )

        assert not can_coop

    def test_can_cooperate_valid(self):
        """Test valid cooperation scenario."""
        system = CooperationSystem()

        can_coop = system.can_cooperate(
            distance_pc=100.0,
            helper_kardashev=1.5,
            receiver_kardashev=1.0
        )

        assert can_coop

    def test_calculate_cooperation_effectiveness_distance(self):
        """Test distance affects effectiveness."""
        system = CooperationSystem(max_cooperation_distance_pc=1000.0)

        # Close cooperation
        eff_close = system.calculate_cooperation_effectiveness(
            distance_pc=50.0,
            helper_maturity=1.0,
            receiver_maturity=0.8,
            helper_kardashev=1.5,
            cooperation_type=CooperationType.KNOWLEDGE_SHARING
        )

        # Far cooperation
        eff_far = system.calculate_cooperation_effectiveness(
            distance_pc=800.0,
            helper_maturity=1.0,
            receiver_maturity=0.8,
            helper_kardashev=1.5,
            cooperation_type=CooperationType.KNOWLEDGE_SHARING
        )

        # Close should be more effective
        assert eff_close > eff_far

    def test_calculate_cooperation_effectiveness_helper_maturity(self):
        """Test helper maturity affects effectiveness."""
        system = CooperationSystem()

        # High maturity helper
        eff_high = system.calculate_cooperation_effectiveness(
            distance_pc=100.0,
            helper_maturity=1.5,
            receiver_maturity=0.8,
            helper_kardashev=1.5,
            cooperation_type=CooperationType.KNOWLEDGE_SHARING
        )

        # Low maturity helper
        eff_low = system.calculate_cooperation_effectiveness(
            distance_pc=100.0,
            helper_maturity=0.5,
            receiver_maturity=0.8,
            helper_kardashev=1.5,
            cooperation_type=CooperationType.KNOWLEDGE_SHARING
        )

        # High maturity should be more effective
        assert eff_high > eff_low

    def test_calculate_cooperation_effectiveness_receiver_maturity(self):
        """Test receiver maturity affects effectiveness."""
        system = CooperationSystem()

        # Mature receiver
        eff_mature = system.calculate_cooperation_effectiveness(
            distance_pc=100.0,
            helper_maturity=1.0,
            receiver_maturity=1.0,
            helper_kardashev=1.5,
            cooperation_type=CooperationType.KNOWLEDGE_SHARING
        )

        # Immature receiver
        eff_immature = system.calculate_cooperation_effectiveness(
            distance_pc=100.0,
            helper_maturity=1.0,
            receiver_maturity=0.3,
            helper_kardashev=1.5,
            cooperation_type=CooperationType.KNOWLEDGE_SHARING
        )

        # Mature receiver should receive aid more effectively
        assert eff_mature > eff_immature

    def test_calculate_cooperation_effectiveness_prior_relationship(self):
        """Test prior relationship increases effectiveness."""
        system = CooperationSystem(reciprocity_bonus=0.3)

        # No prior relationship
        eff_no_prior = system.calculate_cooperation_effectiveness(
            distance_pc=100.0,
            helper_maturity=1.0,
            receiver_maturity=0.8,
            helper_kardashev=1.5,
            cooperation_type=CooperationType.KNOWLEDGE_SHARING,
            has_prior_relationship=False
        )

        # Prior relationship
        eff_with_prior = system.calculate_cooperation_effectiveness(
            distance_pc=100.0,
            helper_maturity=1.0,
            receiver_maturity=0.8,
            helper_kardashev=1.5,
            cooperation_type=CooperationType.KNOWLEDGE_SHARING,
            has_prior_relationship=True
        )

        # Prior relationship should boost effectiveness
        assert eff_with_prior > eff_no_prior

    def test_calculate_cooperation_effectiveness_type_differences(self):
        """Test different cooperation types have different effectiveness."""
        system = CooperationSystem()

        params = dict(
            distance_pc=100.0,
            helper_maturity=1.0,
            receiver_maturity=0.8,
            helper_kardashev=1.5
        )

        eff_knowledge = system.calculate_cooperation_effectiveness(
            **params, cooperation_type=CooperationType.KNOWLEDGE_SHARING
        )

        eff_resource = system.calculate_cooperation_effectiveness(
            **params, cooperation_type=CooperationType.RESOURCE_SHARING
        )

        # Knowledge sharing should be more effective than resource sharing
        assert eff_knowledge > eff_resource

    def test_calculate_crisis_aid_benefit_severity_scaling(self):
        """Test crisis severity affects aid benefit."""
        system = CooperationSystem()

        # Mild crisis
        benefit_mild = system.calculate_crisis_aid_benefit(
            effectiveness=0.8,
            crisis_severity=0.3
        )

        # Severe crisis
        benefit_severe = system.calculate_crisis_aid_benefit(
            effectiveness=0.8,
            crisis_severity=0.9
        )

        # Severe crisis should benefit more from aid
        assert benefit_severe > benefit_mild

    def test_calculate_crisis_aid_benefit_capped(self):
        """Test crisis aid benefit is capped."""
        system = CooperationSystem()

        benefit = system.calculate_crisis_aid_benefit(
            effectiveness=1.0,
            crisis_severity=1.0
        )

        # Should not exceed 0.5
        assert benefit <= 0.5

    def test_should_offer_aid_low_maturity_declines(self):
        """Test low maturity civilizations don't offer aid."""
        system = CooperationSystem(seed=42)

        should_offer = system.should_offer_aid(
            helper_maturity=0.5,  # Too low
            helper_kardashev=1.5,
            receiver_in_crisis=True,
            relationship_history=False,
            helper_resources=1.0
        )

        assert not should_offer

    def test_should_offer_aid_low_tech_declines(self):
        """Test low tech civilizations can't offer aid."""
        system = CooperationSystem(seed=42)

        should_offer = system.should_offer_aid(
            helper_maturity=1.0,
            helper_kardashev=0.5,  # Too low
            receiver_in_crisis=True,
            relationship_history=False,
            helper_resources=1.0
        )

        assert not should_offer

    def test_should_offer_aid_low_resources_declines(self):
        """Test low resources prevent aid."""
        system = CooperationSystem(seed=42)

        should_offer = system.should_offer_aid(
            helper_maturity=1.0,
            helper_kardashev=1.5,
            receiver_in_crisis=True,
            relationship_history=False,
            helper_resources=0.1  # Too low
        )

        assert not should_offer

    def test_should_offer_aid_crisis_increases_likelihood(self):
        """Test crisis increases aid likelihood."""
        system = CooperationSystem(seed=42)

        # Run multiple trials
        offers_no_crisis = 0
        offers_in_crisis = 0

        for _ in range(100):
            if system.should_offer_aid(
                helper_maturity=1.0,
                helper_kardashev=1.5,
                receiver_in_crisis=False,
                relationship_history=False,
                helper_resources=1.0
            ):
                offers_no_crisis += 1

            if system.should_offer_aid(
                helper_maturity=1.0,
                helper_kardashev=1.5,
                receiver_in_crisis=True,
                relationship_history=False,
                helper_resources=1.0
            ):
                offers_in_crisis += 1

        # Crisis should increase offers
        assert offers_in_crisis > offers_no_crisis

    def test_form_alliance_insufficient_maturity(self):
        """Test alliance requires sufficient maturity."""
        system = CooperationSystem(alliance_formation_threshold=0.7)

        hist1 = CooperationHistory()
        hist2 = CooperationHistory()

        # One civilization not mature enough
        updated1, updated2 = system.form_alliance(
            hist1, hist2, civ1_id=1, civ2_id=2,
            civ1_maturity=0.9, civ2_maturity=0.5  # civ2 too low
        )

        # Alliance should not form
        assert not updated1.is_allied_with(2)
        assert not updated2.is_allied_with(1)

    def test_form_alliance_success(self):
        """Test successful alliance formation."""
        system = CooperationSystem(alliance_formation_threshold=0.7)

        hist1 = CooperationHistory()
        hist2 = CooperationHistory()

        # Both civilizations mature enough
        updated1, updated2 = system.form_alliance(
            hist1, hist2, civ1_id=1, civ2_id=2,
            civ1_maturity=0.9, civ2_maturity=0.8
        )

        # Alliance should form
        assert updated1.is_allied_with(2)
        assert updated2.is_allied_with(1)

    def test_record_cooperation_updates_histories(self):
        """Test recording cooperation updates both histories."""
        system = CooperationSystem()

        helper_hist = CooperationHistory()
        receiver_hist = CooperationHistory()

        record = CooperationRecord(
            time_myr=1000.0,
            helper_id=1,
            receiver_id=2,
            cooperation_type=CooperationType.CRISIS_INTERVENTION,
            effectiveness=0.8,
            distance_pc=100.0
        )

        updated_helper, updated_receiver = system.record_cooperation(
            helper_hist, receiver_hist, record, helper_id=1, receiver_id=2
        )

        # Helper should have record in given aid
        assert updated_helper.get_aid_given_count() == 1
        assert updated_helper.has_given_aid_to(2)

        # Receiver should have record in received aid
        assert updated_receiver.get_aid_received_count() == 1
        assert updated_receiver.has_received_aid_from(1)

    def test_record_cooperation_updates_debt(self):
        """Test recording cooperation updates aid debt."""
        system = CooperationSystem()

        helper_hist = CooperationHistory()
        receiver_hist = CooperationHistory()

        record = CooperationRecord(
            time_myr=1000.0,
            helper_id=1,
            receiver_id=2,
            cooperation_type=CooperationType.KNOWLEDGE_SHARING,
            effectiveness=0.7,
            distance_pc=50.0
        )

        updated_helper, updated_receiver = system.record_cooperation(
            helper_hist, receiver_hist, record, helper_id=1, receiver_id=2
        )

        # Helper is owed (positive debt)
        assert updated_helper.aid_debt.get(2, 0.0) > 0

        # Receiver owes (negative debt)
        assert updated_receiver.aid_debt.get(1, 0.0) < 0


class TestCooperationSummaries:
    """Tests for cooperation summary formatting."""

    def test_format_isolated(self):
        """Test formatting for isolated civilization."""
        history = CooperationHistory()

        summary = format_cooperation_summary(history)

        assert "Isolated" in summary
        assert "no cooperation" in summary

    def test_format_received_aid_only(self):
        """Test formatting with only received aid."""
        record = CooperationRecord(
            1000.0, 5, 1, CooperationType.KNOWLEDGE_SHARING, 0.8, 50.0
        )

        history = CooperationHistory(received_aid=[record])

        summary = format_cooperation_summary(history)

        assert "received 1 aid" in summary
        assert "Cooperative" in summary

    def test_format_given_aid_only(self):
        """Test formatting with only given aid."""
        record = CooperationRecord(
            1000.0, 1, 2, CooperationType.TECHNOLOGY_TRANSFER, 0.7, 100.0
        )

        history = CooperationHistory(given_aid=[record])

        summary = format_cooperation_summary(history)

        assert "gave 1 aid" in summary

    def test_format_with_allies(self):
        """Test formatting with allies."""
        history = CooperationHistory(active_allies={3, 5})

        summary = format_cooperation_summary(history)

        assert "2 active allies" in summary

    def test_format_comprehensive(self):
        """Test formatting with all types of cooperation."""
        received = [
            CooperationRecord(1000.0, 5, 1, CooperationType.KNOWLEDGE_SHARING, 0.8, 50.0),
            CooperationRecord(1100.0, 3, 1, CooperationType.CRISIS_INTERVENTION, 0.7, 100.0)
        ]

        given = [
            CooperationRecord(1050.0, 1, 2, CooperationType.TECHNOLOGY_TRANSFER, 0.6, 75.0)
        ]

        history = CooperationHistory(
            received_aid=received,
            given_aid=given,
            active_allies={2, 3}
        )

        summary = format_cooperation_summary(history)

        assert "received 2 aid" in summary
        assert "gave 1 aid" in summary
        assert "2 active allies" in summary
