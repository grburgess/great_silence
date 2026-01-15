"""
Comprehensive demonstration of civilization survival mechanics.

This demo showcases all 9 implemented features:
1. Telemetry tracking
2. Civilization traits
3. Social maturity
4. Crisis experience & learning
5. Breakthrough events
6. Multi-stage crisis resolution
7. Path-dependent development
8. Crisis timing variance
9. Cooperative survival

Run this to see realistic civilization dynamics!
"""

import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from great_silence.civilization.telemetry import CivilizationTelemetry, EventType
from great_silence.civilization.traits import TraitGenerator, CivilizationTraits
from great_silence.civilization.social_maturity import SocialMaturityEvolution, SocialMaturityState
from great_silence.civilization.crisis_experience import CrisisLearningSystem, CrisisExperience
from great_silence.civilization.breakthrough import BreakthroughSystem, BreakthroughType
from great_silence.civilization.crisis_stages import MultiStageCrisisSystem, CrisisState, CrisisStage
from great_silence.civilization.development_path import DevelopmentTracker, DevelopmentHistory
from great_silence.civilization.crisis_timing import CrisisTimingSystem, CrisisType, PersonalizedCrisisSchedule
from great_silence.civilization.cooperation import CooperationSystem, CooperationHistory, CooperationType, CooperationRecord
from great_silence.visualization.export_utils import VisualizationExporter, print_summary_report


class Civilization:
    """Represents a single civilization in the simulation."""

    def __init__(
        self,
        civ_id: int,
        traits: CivilizationTraits,
        initial_kardashev: float,
        initial_maturity: float,
        crisis_schedule: PersonalizedCrisisSchedule,
        emergence_time_myr: float
    ):
        self.id = civ_id
        self.traits = traits
        self.kardashev_level = initial_kardashev
        self.maturity = initial_maturity
        self.crisis_schedule = crisis_schedule
        self.emergence_time_myr = emergence_time_myr

        # Histories
        self.experience = CrisisExperience()
        self.development_history = None  # Will be initialized
        self.cooperation_history = CooperationHistory()
        self.active_crises = {}  # crisis_type -> CrisisState

        # State
        self.alive = True
        self.age_myr = 0.0
        self.last_breakthrough_time = 0.0

    def __repr__(self):
        status = "Alive" if self.alive else "Extinct"
        return (f"Civ{self.id} ({status}): K={self.kardashev_level:.2f}, "
                f"M={self.maturity.maturity_level:.2f}, "
                f"Age={self.age_myr:.0f}Myr")


class CivilizationSimulation:
    """Main simulation engine."""

    def __init__(self, num_civilizations: int = 5, seed: int = 42):
        self.num_civilizations = num_civilizations
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Initialize systems
        self.telemetry = CivilizationTelemetry()
        self.trait_generator = TraitGenerator(seed=seed)
        self.maturity_evolution = SocialMaturityEvolution(seed=seed)
        self.learning_system = CrisisLearningSystem(seed=seed)
        self.breakthrough_system = BreakthroughSystem(seed=seed)
        self.crisis_system = MultiStageCrisisSystem(seed=seed)
        self.development_tracker = DevelopmentTracker(seed=seed)
        self.timing_system = CrisisTimingSystem(seed=seed)
        self.cooperation_system = CooperationSystem(seed=seed)

        # Simulation state
        self.civilizations = []
        self.current_time_myr = 0.0
        self.timestep_myr = 10.0

    def initialize(self):
        """Initialize civilizations with diverse traits."""
        print("Initializing civilizations...")

        for i in range(self.num_civilizations):
            # Random traits
            traits = self.trait_generator.generate_random_traits()

            # Starting conditions
            initial_k = self.rng.uniform(0.65, 0.75)
            emergence_time = self.current_time_myr

            # Initialize maturity
            initial_maturity_state = self.maturity_evolution.initialize_maturity(
                initial_kardashev=initial_k,
                traits=traits.to_dict()
            )

            # Generate crisis schedule
            trait_modifiers = self.timing_system.calculate_trait_modifiers(
                technological_wisdom=traits.technological_wisdom,
                risk_tolerance=traits.risk_tolerance,
                resource_abundance=traits.resource_abundance
            )

            crisis_schedule = self.timing_system.generate_crisis_schedule(
                trait_modifiers=trait_modifiers,
                development_path_modifier=0.0,  # Will adjust later
                environmental_modifier=self.rng.uniform(-0.05, 0.05)
            )

            # Create civilization
            civ = Civilization(
                civ_id=i,
                traits=traits,
                initial_kardashev=initial_k,
                initial_maturity=initial_maturity_state.maturity_level,
                crisis_schedule=crisis_schedule,
                emergence_time_myr=emergence_time
            )

            civ.maturity = initial_maturity_state

            # Initialize development history
            civ.development_history = self.development_tracker.initialize_history(
                emergence_time_myr=emergence_time,
                initial_kardashev=initial_k,
                initial_maturity=initial_maturity_state.maturity_level
            )

            self.civilizations.append(civ)

            # Log birth
            self.telemetry.log_birth(
                time_myr=emergence_time,
                civilization_id=i,
                kardashev=initial_k,
                social_maturity=initial_maturity_state.maturity_level,
                traits=traits.to_dict()
            )

            print(f"  {civ}")

    def run(self, duration_myr: float = 500.0):
        """Run simulation for specified duration."""
        print(f"\nRunning simulation for {duration_myr} Myr...")

        steps = int(duration_myr / self.timestep_myr)

        for step in range(steps):
            self.current_time_myr += self.timestep_myr

            # Process each living civilization
            for civ in [c for c in self.civilizations if c.alive]:
                self.process_civilization(civ)

            # Check for cooperation opportunities
            self.process_cooperation()

            # Progress report
            if step % 10 == 0:
                alive_count = sum(1 for c in self.civilizations if c.alive)
                print(f"  T={self.current_time_myr:.0f} Myr: {alive_count}/{self.num_civilizations} alive")

        print(f"\nSimulation complete!")

    def process_civilization(self, civ: Civilization):
        """Process one timestep for a civilization."""
        civ.age_myr += self.timestep_myr

        # 1. Advance development
        growth_rate = 0.001 * (1.0 + civ.traits.adaptability)
        civ.kardashev_level += growth_rate * self.timestep_myr

        # 2. Check for breakthrough
        recently_survived_crisis = (self.current_time_myr - civ.last_breakthrough_time) < 50.0

        breakthrough_occurred, breakthrough_type = self.breakthrough_system.check_for_breakthrough(
            civilization_age_myr=civ.age_myr,
            maturity_level=civ.maturity.maturity_level,
            stagnation_time_myr=civ.maturity.stagnation_time_myr,
            dt_myr=self.timestep_myr,
            recently_survived_crisis=recently_survived_crisis
        )

        if breakthrough_occurred:
            civ.maturity = self.maturity_evolution.apply_breakthrough(
                civ.maturity,
                breakthrough_type.value
            )
            civ.last_breakthrough_time = self.current_time_myr

            self.telemetry.log_breakthrough(
                time_myr=self.current_time_myr,
                civilization_id=civ.id,
                breakthrough_type=breakthrough_type,
                kardashev=civ.kardashev_level,
                maturity_before=civ.maturity.maturity_level - 0.1,
                maturity_after=civ.maturity.maturity_level
            )

        # 3. Advance maturity
        in_crisis = len(civ.active_crises) > 0

        civ.maturity = self.maturity_evolution.advance_maturity(
            state=civ.maturity,
            current_kardashev=civ.kardashev_level,
            dt_myr=self.timestep_myr,
            in_crisis=in_crisis,
            traits=civ.traits.to_dict()
        )

        # 4. Update development history
        civ.development_history = self.development_tracker.update_history(
            civ.development_history,
            current_time_myr=self.current_time_myr,
            current_kardashev=civ.kardashev_level,
            current_maturity=civ.maturity.maturity_level
        )

        # 5. Check for new crises
        triggered_crises = self.timing_system.check_crisis_triggers(
            civ.crisis_schedule,
            civ.kardashev_level
        )

        for crisis_type, severity in triggered_crises:
            self.initiate_crisis(civ, crisis_type, severity)

        # 6. Advance active crises
        self.advance_active_crises(civ)

    def initiate_crisis(self, civ: Civilization, crisis_type: CrisisType, severity: float):
        """Initiate a new crisis for a civilization."""
        # Check if already has this crisis
        if crisis_type in civ.active_crises:
            return

        # Check for early detection based on experience
        has_early_detection = civ.experience.has_survived_before(crisis_type.value)

        # Create crisis state
        crisis_state = self.crisis_system.initiate_crisis(
            crisis_type=crisis_type.value,
            severity=severity,
            has_early_detection=has_early_detection
        )

        civ.active_crises[crisis_type] = crisis_state

        # Mark as triggered
        civ.crisis_schedule = self.timing_system.mark_crisis_triggered(
            civ.crisis_schedule,
            crisis_type
        )

        # Log crisis entry
        self.telemetry.log_crisis_entered(
            time_myr=self.current_time_myr,
            civilization_id=civ.id,
            crisis_type=crisis_type,
            severity=severity,
            kardashev=civ.kardashev_level
        )

        print(f"    ⚠️  Civ{civ.id} enters {crisis_type.value} crisis (severity={severity:.2f})")

    def advance_active_crises(self, civ: Civilization):
        """Advance all active crises for a civilization."""
        completed_crises = []

        for crisis_type, crisis_state in civ.active_crises.items():
            # Calculate response quality
            response_quality = self.crisis_system.calculate_response_quality(
                maturity_level=civ.maturity.maturity_level,
                experience_bonus=civ.experience.get_total_survival_bonus(crisis_state.crisis_type),
                trait_modifiers=civ.traits.get_crisis_survival_modifier(),
                resource_availability=civ.traits.resource_abundance
            )

            # Advance crisis
            new_crisis_state = self.crisis_system.advance_crisis(
                crisis_state,
                dt_myr=self.timestep_myr,
                response_quality=response_quality
            )

            civ.active_crises[crisis_type] = new_crisis_state

            # Check for resolution
            if self.crisis_system.can_resolve_crisis(new_crisis_state):
                # Success!
                self.resolve_crisis_success(civ, crisis_type, new_crisis_state)
                completed_crises.append(crisis_type)

            elif new_crisis_state.stage == CrisisStage.CRITICAL:
                # Survival check at critical stage
                survived, was_close = self.crisis_system.check_survival(
                    new_crisis_state,
                    maturity_modifier=self.maturity_evolution.calculate_crisis_survival_modifier(civ.maturity),
                    trait_modifier=civ.traits.get_crisis_survival_modifier(),
                    experience_bonus=civ.experience.get_total_survival_bonus(crisis_state.crisis_type)
                )

                if not survived:
                    # Civilization destroyed
                    self.civilization_destroyed(civ, crisis_type, new_crisis_state)
                    return  # Don't process further

        # Remove completed crises
        for crisis_type in completed_crises:
            del civ.active_crises[crisis_type]

    def resolve_crisis_success(self, civ: Civilization, crisis_type: CrisisType, crisis_state: CrisisState):
        """Handle successful crisis resolution."""
        print(f"    ✅ Civ{civ.id} survives {crisis_type.value}!")

        # Update experience
        was_close_call = crisis_state.response_effectiveness < 0.7

        civ.experience = self.learning_system.record_crisis_success(
            experience=civ.experience,
            crisis_type=crisis_state.crisis_type,
            crisis_severity=crisis_state.severity,
            current_time_myr=self.current_time_myr,
            was_close_call=was_close_call
        )

        # Boost maturity
        civ.maturity = self.maturity_evolution.apply_crisis_survival_boost(
            civ.maturity,
            crisis_severity=crisis_state.severity
        )

        # Mark as survived in schedule
        civ.crisis_schedule = self.timing_system.mark_crisis_survived(
            civ.crisis_schedule,
            crisis_type
        )

        # Log success
        self.telemetry.log_crisis_survived(
            time_myr=self.current_time_myr,
            civilization_id=civ.id,
            crisis_type=crisis_type,
            kardashev=civ.kardashev_level,
            social_maturity=civ.maturity.maturity_level,
            severity=crisis_state.severity
        )

    def civilization_destroyed(self, civ: Civilization, crisis_type: CrisisType, crisis_state: CrisisState):
        """Handle civilization destruction."""
        print(f"    💀 Civ{civ.id} destroyed by {crisis_type.value}")

        civ.alive = False

        self.telemetry.log_death(
            time_myr=self.current_time_myr,
            civilization_id=civ.id,
            kardashev=civ.kardashev_level,
            social_maturity=civ.maturity.maturity_level,
            cause=f"crisis_{crisis_type.value}"
        )

        self.telemetry.log_crisis_failed(
            time_myr=self.current_time_myr,
            civilization_id=civ.id,
            crisis_type=crisis_type,
            kardashev=civ.kardashev_level,
            severity=crisis_state.severity
        )

    def process_cooperation(self):
        """Check for cooperation opportunities between civilizations."""
        alive_civs = [c for c in self.civilizations if c.alive]

        if len(alive_civs) < 2:
            return

        # Check each pair
        for i, civ1 in enumerate(alive_civs):
            for civ2 in alive_civs[i+1:]:
                # Simple distance model (all at same distance for demo)
                distance_pc = 500.0

                # Check if cooperation is possible
                if not self.cooperation_system.can_cooperate(
                    distance_pc=distance_pc,
                    helper_kardashev=civ1.kardashev_level,
                    receiver_kardashev=civ2.kardashev_level
                ):
                    continue

                # Check if civ2 is in crisis and civ1 should help
                if len(civ2.active_crises) > 0:
                    should_help = self.cooperation_system.should_offer_aid(
                        helper_maturity=civ1.maturity.maturity_level,
                        helper_kardashev=civ1.kardashev_level,
                        receiver_in_crisis=True,
                        relationship_history=civ1.cooperation_history.has_given_aid_to(civ2.id),
                        helper_resources=civ1.traits.resource_abundance
                    )

                    if should_help:
                        self.provide_crisis_aid(civ1, civ2, distance_pc)

    def provide_crisis_aid(self, helper: Civilization, receiver: Civilization, distance_pc: float):
        """Provide crisis aid from one civilization to another."""
        effectiveness = self.cooperation_system.calculate_cooperation_effectiveness(
            distance_pc=distance_pc,
            helper_maturity=helper.maturity.maturity_level,
            receiver_maturity=receiver.maturity.maturity_level,
            helper_kardashev=helper.kardashev_level,
            cooperation_type=CooperationType.CRISIS_INTERVENTION,
            has_prior_relationship=helper.cooperation_history.has_given_aid_to(receiver.id)
        )

        # Create cooperation record
        record = CooperationRecord(
            time_myr=self.current_time_myr,
            helper_id=helper.id,
            receiver_id=receiver.id,
            cooperation_type=CooperationType.CRISIS_INTERVENTION,
            effectiveness=effectiveness,
            distance_pc=distance_pc
        )

        # Update histories
        helper.cooperation_history, receiver.cooperation_history = \
            self.cooperation_system.record_cooperation(
                helper.cooperation_history,
                receiver.cooperation_history,
                record,
                helper.id,
                receiver.id
            )

        # Log cooperation
        self.telemetry.log_aid(
            time_myr=self.current_time_myr,
            giver_id=helper.id,
            receiver_id=receiver.id,
            kardashev_giver=helper.kardashev_level,
            cooperation_type=CooperationType.CRISIS_INTERVENTION.value,
            effectiveness=effectiveness
        )

        print(f"    🤝 Civ{helper.id} aids Civ{receiver.id} (effectiveness={effectiveness:.2f})")

    def export_visualization_data(self, output_path: str = "simulation_export.json"):
        """Export data for visualization."""
        exporter = VisualizationExporter()

        # Gather telemetry data and extract crisis events
        telemetry_dict = self.telemetry.export_to_dict()

        # Transform events into crisis_events format
        crisis_events = []
        for event in telemetry_dict.get('events', []):
            event_type = event.get('event_type')
            if event_type in ['crisis_survived', 'crisis_failed']:
                crisis_events.append({
                    'crisis_type': event.get('crisis_type', 'unknown'),
                    'outcome': 'survived' if event_type == 'crisis_survived' else 'failed',
                    'severity': event.get('metadata', {}).get('severity', 0.0),
                    'time_myr': event.get('time_myr', 0.0),
                    'civilization_id': event.get('civilization_id', -1)
                })

        telemetry_data = {
            'crisis_events': crisis_events,
            'events': telemetry_dict.get('events', []),
            'snapshots': telemetry_dict.get('snapshots', [])
        }

        # Gather development histories
        civilization_histories = []
        for civ in self.civilizations:
            if civ.development_history:
                hist_dict = civ.development_history.to_dict()
                # Rename 'snapshots' to 'development_snapshots' for visualization exporter
                hist_dict['development_snapshots'] = hist_dict.pop('snapshots', [])
                hist_dict['id'] = civ.id
                hist_dict['development_path_type'] = self.development_tracker.classify_development_path(
                    civ.development_history
                )
                civilization_histories.append(hist_dict)

        # Gather cooperation records
        cooperation_records = []
        for civ in self.civilizations:
            for record in civ.cooperation_history.given_aid:
                cooperation_records.append({
                    'time_myr': record.time_myr,
                    'helper_id': record.helper_id,
                    'receiver_id': record.receiver_id,
                    'cooperation_type': record.cooperation_type.value,
                    'effectiveness': record.effectiveness,
                    'distance_pc': record.distance_pc
                })

        # Export all data
        export = exporter.export_all(
            telemetry_data=telemetry_data,
            civilization_histories=civilization_histories,
            cooperation_records=cooperation_records,
            metadata={
                'num_civilizations': self.num_civilizations,
                'duration_myr': self.current_time_myr,
                'seed': self.seed
            }
        )

        # Save to file
        export.to_json(output_path)
        print(f"\n📁 Visualization data exported to: {output_path}")

        # Print summary report
        print_summary_report(export)

        return export


def main():
    """Run the demonstration."""
    print("\n" + "="*70)
    print("CIVILIZATION SURVIVAL MECHANICS DEMONSTRATION")
    print("="*70)
    print("\nThis demo showcases:")
    print("  1. Telemetry tracking")
    print("  2. Civilization traits")
    print("  3. Social maturity evolution")
    print("  4. Crisis experience & learning")
    print("  5. Breakthrough events")
    print("  6. Multi-stage crisis resolution")
    print("  7. Path-dependent development")
    print("  8. Crisis timing variance")
    print("  9. Cooperative survival")
    print("="*70 + "\n")

    # Create and run simulation
    sim = CivilizationSimulation(num_civilizations=5, seed=42)
    sim.initialize()
    sim.run(duration_myr=500.0)

    # Export visualization data
    export = sim.export_visualization_data()

    # Final summary
    print("\n" + "="*70)
    print("FINAL CIVILIZATION STATUS")
    print("="*70)
    for civ in sim.civilizations:
        print(f"\n{civ}")
        if civ.alive:
            print(f"  Experience: {civ.experience.crises_survived} crises survived")
            print(f"  Maturity: {civ.maturity.maturity_level:.2f} "
                  f"(ratio={civ.maturity.maturity_to_kardashev_ratio:.2f})")
            print(f"  Development: {sim.development_tracker.classify_development_path(civ.development_history)}")
            print(f"  Cooperation: {civ.cooperation_history.get_aid_given_count()} given, "
                  f"{civ.cooperation_history.get_aid_received_count()} received")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
