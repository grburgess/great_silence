"""
Realistic 3D galactic civilization simulation with astrophysical hazards.

Features:
- 3D galactic positions for all civilizations
- Supernova and GRB events that can destroy civilizations
- Adaptive time stepping (faster when quiet, slower during crises)
- Realistic mortality rates
- Full integration of all 9 survival mechanics
- 3D visualization and animation

This simulation is MUCH harder than the basic demo - civilizations will die!
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import great_silence
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import json

# Import all the modules we built
from great_silence.civilization.telemetry import CivilizationTelemetry
from great_silence.civilization.traits import CivilizationTraits, TraitGenerator
from great_silence.civilization.social_maturity import SocialMaturityState, SocialMaturityEvolution
from great_silence.civilization.crisis_experience import CrisisExperience, CrisisLearningSystem
from great_silence.civilization.breakthrough import BreakthroughSystem, BreakthroughType
from great_silence.civilization.crisis_stages import CrisisState, MultiStageCrisisSystem, CrisisStage
from great_silence.civilization.development_path import DevelopmentHistory, DevelopmentTracker
from great_silence.civilization.crisis_timing import CrisisTimingSystem, PersonalizedCrisisSchedule, CrisisType
from great_silence.civilization.cooperation import CooperationSystem, CooperationHistory, CooperationType

# Import astrophysics modules
from great_silence.astrophysics.supernovae import SupernovaModel
from great_silence.astrophysics.grb import GammaRayBurstModel
from great_silence.galaxy.structure import GalaxyModel
from great_silence.galaxy.star_formation import StarFormationHistory, InitialMassFunction
from great_silence.config.parameters import GalaxyParameters, AstrophysicsParameters

# Import visualization
from great_silence.visualization.export_utils import VisualizationExporter, print_summary_report


@dataclass
class CivilizationState:
    """Complete state of a civilization in 3D space."""
    id: int
    position: np.ndarray  # (x, y, z) in kpc
    host_star_index: int  # Index in galaxy model

    # Core properties
    kardashev_level: float
    alive: bool
    emergence_time_myr: float

    # All the new systems
    traits: CivilizationTraits
    maturity: SocialMaturityState
    experience: CrisisExperience
    development_history: Optional[DevelopmentHistory]
    cooperation_history: CooperationHistory
    crisis_schedule: PersonalizedCrisisSchedule
    active_crises: Dict[CrisisType, CrisisState] = field(default_factory=dict)

    # Tracking
    last_breakthrough_time: float = 0.0
    cause_of_death: Optional[str] = None
    death_time_myr: Optional[float] = None


class AdaptiveTimestepper:
    """
    Manages adaptive time stepping for the simulation.

    Uses smaller timesteps during active crises and larger timesteps
    during quiet periods to balance accuracy and performance.
    """

    def __init__(
        self,
        min_dt_myr: float = 0.1,  # 100,000 years minimum
        max_dt_myr: float = 10.0,  # 10 million years maximum
        crisis_dt_myr: float = 1.0  # 1 million years during crises
    ):
        self.min_dt_myr = min_dt_myr
        self.max_dt_myr = max_dt_myr
        self.crisis_dt_myr = crisis_dt_myr

    def get_timestep(
        self,
        num_active_crises: int,
        recent_events: int,
        current_dt: float
    ) -> float:
        """
        Calculate adaptive timestep based on simulation state.

        Args:
            num_active_crises: Number of civilizations in crisis
            recent_events: Number of events in last timestep
            current_dt: Current timestep

        Returns:
            Next timestep in Myr
        """
        if num_active_crises > 0:
            # Active crises: use crisis timestep
            return self.crisis_dt_myr
        elif recent_events > 0:
            # Recent activity: moderate timestep
            return min(self.max_dt_myr / 2, current_dt)
        else:
            # Quiet period: gradually increase timestep
            new_dt = current_dt * 1.2
            return min(self.max_dt_myr, new_dt)


class Realistic3DSimulation:
    """
    Realistic 3D simulation with all hazards active.

    MUCH HARDER than the basic demo - expect significant mortality!
    """

    def __init__(
        self,
        num_stars: int = 100000,
        num_civilizations: int = 20,
        seed: Optional[int] = None
    ):
        self.num_stars = num_stars
        self.num_civilizations = num_civilizations
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Initialize galaxy model
        galaxy_params = GalaxyParameters()
        galaxy_params.total_stars = num_stars
        galaxy_params.include_bulge = True
        galaxy_params.spiral_arm_count = 2
        self.galaxy = GalaxyModel(galaxy_params, seed=seed)

        # Initialize astrophysics (ACTIVE HAZARDS!)
        astro_params = AstrophysicsParameters()
        astro_params.supernova_rate_per_century = 2.0
        astro_params.sn_lethal_range_pc = 10.0  # Corrected parameter name
        astro_params.grb_rate_per_century = 0.01
        astro_params.grb_lethal_range_kpc = 1.0  # Corrected parameter name and unit (1 kpc = 1000 pc)
        astro_params.grb_beaming_angle_deg = 10.0

        self.supernova_model = SupernovaModel(astro_params)
        self.grb_model = GammaRayBurstModel(astro_params)

        # Initialize all civilization systems (TOUGHER PARAMETERS)
        self.trait_generator = TraitGenerator(seed=seed)
        self.maturity_evolution = SocialMaturityEvolution(
            base_growth_rate=0.003,  # Slower maturity growth
            crisis_growth_multiplier=2.0
        )
        self.learning_system = CrisisLearningSystem(
            experience_decay_timescale_gyr=2.0  # Faster decay (2 Gyr)
        )
        self.breakthrough_system = BreakthroughSystem(seed=seed)
        self.crisis_system = MultiStageCrisisSystem(seed=seed)
        self.development_tracker = DevelopmentTracker()
        self.crisis_timing = CrisisTimingSystem(seed=seed)
        self.cooperation_system = CooperationSystem(
            max_cooperation_distance_pc=500.0,  # Shorter range
            seed=seed
        )

        # Adaptive timestepping
        self.timestepper = AdaptiveTimestepper()

        # Telemetry
        self.telemetry = CivilizationTelemetry()

        # State
        self.civilizations: List[CivilizationState] = []
        self.current_time_myr: float = 0.0
        self.current_dt_myr: float = 5.0  # Start with moderate timestep

        # Event tracking for this timestep
        self.events_this_step: int = 0

        # Astrophysical event log
        self.supernova_events: List[Dict] = []
        self.grb_events: List[Dict] = []

    def initialize(self):
        """Initialize galaxy and civilizations."""
        print("Initializing 3D galaxy...")
        self.galaxy.generate_stellar_population()

        # Generate stellar ages and masses
        print("Generating stellar ages and masses...")
        astro_params = AstrophysicsParameters()
        sfh = StarFormationHistory(astro_params)
        imf = InitialMassFunction("kroupa")

        self.galaxy.ages = sfh.generate_stellar_ages(self.num_stars, seed=self.seed)
        self.galaxy.masses = imf.sample(self.num_stars, seed=self.seed)

        print(f"Placing {self.num_civilizations} civilizations in galaxy...")

        # Find habitable stars (sun-like, old enough)
        masses = self.galaxy.masses
        ages = self.galaxy.ages

        habitable = (masses > 0.5) & (masses < 1.5) & (ages > 1.0)
        habitable_indices = np.where(habitable)[0]

        if len(habitable_indices) < self.num_civilizations:
            raise ValueError(f"Not enough habitable stars! Found {len(habitable_indices)}, need {self.num_civilizations}")

        # Randomly select habitable stars for civilizations
        selected_indices = self.rng.choice(
            habitable_indices,
            size=self.num_civilizations,
            replace=False
        )

        for i, star_idx in enumerate(selected_indices):
            # Generate traits
            traits = self.trait_generator.generate_random_traits()

            # Initial Kardashev level (0.6-0.8, pre-industrial to early industrial)
            initial_k = 0.6 + 0.2 * self.rng.random()

            # Initial maturity (balanced with some variation)
            initial_maturity_ratio = 0.8 + 0.4 * self.rng.random()  # 0.8-1.2
            initial_maturity_level = initial_k * initial_maturity_ratio

            initial_maturity = SocialMaturityState(
                maturity_level=initial_maturity_level,
                growth_rate=0.003 * (0.5 + traits.adaptability),
                maturity_to_kardashev_ratio=initial_maturity_ratio,
                stagnation_time_myr=0.0
            )

            # Generate personalized crisis schedule
            trait_modifiers = self.crisis_timing.calculate_trait_modifiers(
                technological_wisdom=traits.technological_wisdom,
                risk_tolerance=traits.risk_tolerance,
                resource_abundance=traits.resource_abundance
            )

            crisis_schedule = self.crisis_timing.generate_crisis_schedule(
                trait_modifiers=trait_modifiers
            )

            # Create development history with initial snapshot
            from great_silence.civilization.development_path import DevelopmentSnapshot
            initial_snapshot = DevelopmentSnapshot(
                time_myr=0.0,
                kardashev_level=initial_k,
                maturity_level=initial_maturity_level,
                development_velocity=0.0
            )
            dev_history = DevelopmentHistory(
                emergence_time_myr=0.0,
                snapshots=[initial_snapshot]
            )

            # Create civilization
            civ = CivilizationState(
                id=i,
                position=self.galaxy.positions[star_idx].copy(),
                host_star_index=int(star_idx),
                kardashev_level=initial_k,
                alive=True,
                emergence_time_myr=0.0,
                traits=traits,
                maturity=initial_maturity,
                experience=CrisisExperience(),
                development_history=dev_history,
                cooperation_history=CooperationHistory(),
                crisis_schedule=crisis_schedule
            )

            self.civilizations.append(civ)

            # Log birth
            self.telemetry.log_birth(
                time_myr=0.0,
                civilization_id=i,
                kardashev=initial_k,
                social_maturity=initial_maturity_level,
                traits=traits.to_dict()
            )

        print(f"  ✅ {self.num_civilizations} civilizations initialized")
        print(f"  📍 Galaxy contains {self.num_stars} stars")
        print(f"  🌟 {len(habitable_indices)} habitable stars found")
        print(f"\n⚠️  WARNING: This simulation is HARD - expect casualties!\n")

    def run(self, duration_myr: float = 1000.0, print_interval_myr: float = 100.0):
        """Run the simulation."""
        print(f"\n{'='*70}")
        print(f"RUNNING REALISTIC 3D SIMULATION FOR {duration_myr} MYR")
        print(f"Adaptive timesteps, active astrophysical hazards, tough crises")
        print(f"{'='*70}\n")

        next_print_time = print_interval_myr

        while self.current_time_myr < duration_myr:
            self.events_this_step = 0

            # Process all living civilizations
            alive_civs = [c for c in self.civilizations if c.alive]

            for civ in alive_civs:
                self.process_civilization(civ)

            # Process cooperation between living civilizations
            self.process_cooperation()

            # Check for astrophysical hazards
            self.check_astrophysical_hazards()

            # Adaptive timestep for next iteration
            num_in_crisis = sum(len(c.active_crises) > 0 for c in alive_civs)
            self.current_dt_myr = self.timestepper.get_timestep(
                num_active_crises=num_in_crisis,
                recent_events=self.events_this_step,
                current_dt=self.current_dt_myr
            )

            # Advance time
            self.current_time_myr += self.current_dt_myr

            # Print status
            if self.current_time_myr >= next_print_time:
                alive_count = sum(1 for c in self.civilizations if c.alive)
                in_crisis = sum(1 for c in alive_civs if len(c.active_crises) > 0)
                print(f"  T={self.current_time_myr:.1f} Myr: {alive_count}/{self.num_civilizations} alive, "
                      f"{in_crisis} in crisis, dt={self.current_dt_myr:.2f} Myr, "
                      f"SN:{len(self.supernova_events)}, GRB:{len(self.grb_events)}")
                next_print_time += print_interval_myr

        print(f"\n{'='*70}")
        print("SIMULATION COMPLETE")
        print(f"{'='*70}\n")

        # Print final statistics
        self.print_final_statistics()

    def process_civilization(self, civ: CivilizationState):
        """Process one civilization for this timestep."""
        if not civ.alive:
            return

        # 1. Advance Kardashev level
        base_rate = 0.001  # K/Myr
        velocity_modifier = civ.traits.risk_tolerance * 0.5 + 0.75  # 0.75-1.25
        civ.kardashev_level += base_rate * velocity_modifier * self.current_dt_myr

        # 2. Check for breakthrough
        breakthrough_occurred, breakthrough_type = self.breakthrough_system.check_for_breakthrough(
            civilization_age_myr=self.current_time_myr - civ.emergence_time_myr,
            maturity_level=civ.maturity.maturity_level,
            stagnation_time_myr=civ.maturity.stagnation_time_myr,
            dt_myr=self.current_dt_myr,
            recently_survived_crisis=False
        )

        if breakthrough_occurred and breakthrough_type:
            # Get maturity boost from breakthrough
            boost_min, boost_max = self.breakthrough_system.get_maturity_impact(breakthrough_type)
            boost = self.rng.uniform(min(boost_min, boost_max), max(boost_min, boost_max))

            # Apply maturity boost
            new_maturity_level = civ.maturity.maturity_level + boost
            new_ratio = new_maturity_level / civ.kardashev_level if civ.kardashev_level > 0 else 1.0

            civ.maturity = SocialMaturityState(
                maturity_level=new_maturity_level,
                growth_rate=civ.maturity.growth_rate,
                maturity_to_kardashev_ratio=new_ratio,
                stagnation_time_myr=0.0  # Reset stagnation
            )

            civ.last_breakthrough_time = self.current_time_myr
            self.telemetry.log_breakthrough(
                time_myr=self.current_time_myr,
                civilization_id=civ.id,
                breakthrough_type=breakthrough_type,
                kardashev=civ.kardashev_level
            )
            self.events_this_step += 1

        # 3. Advance maturity
        in_crisis = len(civ.active_crises) > 0
        civ.maturity = self.maturity_evolution.advance_maturity(
            state=civ.maturity,
            current_kardashev=civ.kardashev_level,
            dt_myr=self.current_dt_myr,
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
        triggered = self.crisis_timing.check_crisis_triggers(
            civ.crisis_schedule,
            current_kardashev=civ.kardashev_level
        )

        for crisis_type, severity in triggered:
            if crisis_type not in civ.active_crises:
                self.trigger_crisis(civ, crisis_type, severity)
                civ.crisis_schedule = self.crisis_timing.mark_crisis_triggered(
                    civ.crisis_schedule, crisis_type
                )

        # 6. Advance active crises
        self.advance_active_crises(civ)

    def trigger_crisis(self, civ: CivilizationState, crisis_type: CrisisType, severity: float):
        """Trigger a new crisis for a civilization."""
        # Increase severity based on parameters (make it MUCH harder)
        severity *= 1.5  # 50% harder!
        severity = min(1.0, severity)

        crisis_state = CrisisState(
            crisis_type=crisis_type.value,
            stage=CrisisStage.EMERGING,
            severity=severity,
            response_effectiveness=0.0,
            stage_advancement_rate=0.1
        )

        civ.active_crises[crisis_type] = crisis_state

        self.telemetry.log_crisis_entered(
            time_myr=self.current_time_myr,
            civilization_id=civ.id,
            crisis_type=crisis_type,
            severity=severity,
            kardashev=civ.kardashev_level
        )

        self.events_this_step += 1
        print(f"    ⚠️  Civ{civ.id} enters {crisis_type.value} crisis (severity={severity:.2f})")

    def advance_active_crises(self, civ: CivilizationState):
        """Advance all active crises for a civilization."""
        completed_crises = []

        for crisis_type, crisis_state in list(civ.active_crises.items()):
            # Calculate response quality (MUCH TOUGHER now)
            base_response = civ.maturity.maturity_to_kardashev_ratio * 0.3  # Reduced significantly
            trait_modifier = civ.traits.get_crisis_survival_modifier()
            experience_bonus = civ.experience.get_general_experience_bonus()
            specific_bonus = civ.experience.get_specific_experience_bonus(crisis_type.value)

            response_quality = (base_response * trait_modifier * 0.5 +  # 50% penalty on base
                              experience_bonus * 0.5 +                   # Experience helps less
                              specific_bonus * 0.7) * 0.5                # Overall 50% reduction

            # Advance crisis
            new_state = self.crisis_system.advance_crisis(
                crisis_state,
                response_quality=response_quality,
                dt_myr=self.current_dt_myr
            )

            civ.active_crises[crisis_type] = new_state

            # Check if resolved
            if new_state.stage == CrisisStage.RESOLVED:
                self.civilization_survives_crisis(civ, crisis_type, new_state)
                completed_crises.append(crisis_type)
            elif new_state.stage == CrisisStage.FAILED:
                self.civilization_destroyed(civ, crisis_type, new_state)
                completed_crises.append(crisis_type)

        # Remove completed crises
        for crisis_type in completed_crises:
            del civ.active_crises[crisis_type]

    def civilization_survives_crisis(self, civ: CivilizationState, crisis_type: CrisisType, crisis_state: CrisisState):
        """Handle civilization surviving a crisis."""
        # Update experience
        civ.experience = self.learning_system.record_crisis_success(
            civ.experience,
            crisis_type=crisis_type.value,
            crisis_severity=crisis_state.severity,
            current_time_myr=self.current_time_myr
        )

        # Maturity boost
        civ.maturity = self.maturity_evolution.apply_crisis_survival_boost(
            civ.maturity,
            crisis_severity=crisis_state.severity
        )

        # Mark in schedule
        civ.crisis_schedule = self.crisis_timing.mark_crisis_survived(
            civ.crisis_schedule, crisis_type
        )

        # Log
        self.telemetry.log_crisis_survived(
            time_myr=self.current_time_myr,
            civilization_id=civ.id,
            crisis_type=crisis_type,
            kardashev=civ.kardashev_level,
            social_maturity=civ.maturity.maturity_level,
            severity=crisis_state.severity
        )

        self.events_this_step += 1
        print(f"    ✅ Civ{civ.id} survives {crisis_type.value}!")

    def civilization_destroyed(self, civ: CivilizationState, crisis_type: CrisisType, crisis_state: CrisisState):
        """Handle civilization destruction."""
        civ.alive = False
        civ.cause_of_death = f"crisis_{crisis_type.value}"
        civ.death_time_myr = self.current_time_myr

        self.telemetry.log_death(
            time_myr=self.current_time_myr,
            civilization_id=civ.id,
            kardashev=civ.kardashev_level,
            social_maturity=civ.maturity.maturity_level,
            cause=civ.cause_of_death
        )

        self.telemetry.log_crisis_failed(
            time_myr=self.current_time_myr,
            civilization_id=civ.id,
            crisis_type=crisis_type,
            kardashev=civ.kardashev_level,
            severity=crisis_state.severity
        )

        self.events_this_step += 1
        print(f"    💀 Civ{civ.id} destroyed by {crisis_type.value}!")

    def process_cooperation(self):
        """Check for cooperation opportunities."""
        alive_civs = [c for c in self.civilizations if c.alive]

        if len(alive_civs) < 2:
            return

        # Find civilizations in crisis that could receive aid
        in_crisis = [c for c in alive_civs if len(c.active_crises) > 0]

        for receiver in in_crisis:
            for helper in alive_civs:
                if helper.id == receiver.id:
                    continue

                # Calculate distance
                distance_pc = np.linalg.norm(helper.position - receiver.position) * 1000  # kpc to pc

                if not self.cooperation_system.can_cooperate(
                    distance_pc=distance_pc,
                    helper_kardashev=helper.kardashev_level,
                    receiver_kardashev=receiver.kardashev_level
                ):
                    continue

                # Check if helper wants to offer aid
                has_relationship = (
                    helper.cooperation_history.has_given_aid_to(receiver.id) or
                    receiver.cooperation_history.has_given_aid_to(helper.id)
                )

                if self.cooperation_system.should_offer_aid(
                    helper_maturity=helper.maturity.maturity_level,
                    helper_kardashev=helper.kardashev_level,
                    receiver_in_crisis=True,
                    relationship_history=has_relationship,
                    helper_resources=1.0
                ):
                    # Provide aid
                    effectiveness = self.cooperation_system.calculate_cooperation_effectiveness(
                        distance_pc=distance_pc,
                        helper_maturity=helper.maturity.maturity_level,
                        receiver_maturity=receiver.maturity.maturity_level,
                        helper_kardashev=helper.kardashev_level,
                        cooperation_type=CooperationType.CRISIS_INTERVENTION,
                        has_prior_relationship=has_relationship
                    )

                    # Reduce effectiveness (harder to help)
                    effectiveness *= 0.7

                    # Create cooperation record
                    from great_silence.civilization.cooperation import CooperationRecord
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
                            helper_id=helper.id,
                            receiver_id=receiver.id
                        )

                    # Log
                    self.telemetry.log_aid(
                        time_myr=self.current_time_myr,
                        giver_id=helper.id,
                        receiver_id=receiver.id,
                        kardashev_giver=helper.kardashev_level,
                        cooperation_type=CooperationType.CRISIS_INTERVENTION.value,
                        effectiveness=effectiveness
                    )

    def check_astrophysical_hazards(self):
        """
        Check for supernovae and GRBs that could destroy civilizations.

        THIS IS WHERE THE REAL DANGER COMES FROM!
        """
        # Check each star for supernova
        for i in range(len(self.galaxy.masses)):
            if self.supernova_model.will_go_supernova(
                stellar_mass=self.galaxy.masses[i],
                stellar_age_gyr=self.galaxy.ages[i],
                dt_myr=self.current_dt_myr
            ):
                self.process_supernova(i)

        # Check for GRB events (rarer but devastating)
        if self.rng.random() < (0.01 / 100) * self.current_dt_myr:  # 0.01 per century
            self.process_grb()

    def process_supernova(self, star_index: int):
        """Process a supernova event."""
        sn_position = self.galaxy.positions[star_index]

        # Log event
        self.supernova_events.append({
            'time_myr': self.current_time_myr,
            'position': sn_position.tolist(),
            'star_index': int(star_index)
        })

        # Check for nearby civilizations
        destroyed = []
        for civ in self.civilizations:
            if not civ.alive:
                continue

            distance_pc = np.linalg.norm(civ.position - sn_position) * 1000  # kpc to pc

            if self.supernova_model.is_lethal(distance_pc):
                # Civilization destroyed by supernova
                civ.alive = False
                civ.cause_of_death = "supernova"
                civ.death_time_myr = self.current_time_myr

                self.telemetry.log_death(
                    time_myr=self.current_time_myr,
                    civilization_id=civ.id,
                    kardashev=civ.kardashev_level,
                    social_maturity=civ.maturity.maturity_level,
                    cause="supernova"
                )

                self.events_this_step += 1
                destroyed.append((civ.id, distance_pc))

        if destroyed:
            print(f"    💥 SUPERNOVA at T={self.current_time_myr:.1f} Myr!")
            for civ_id, dist in destroyed:
                print(f"       Destroyed Civ{civ_id} at {dist:.1f} pc")

    def process_grb(self):
        """Process a gamma-ray burst event."""
        # Random location in galaxy
        grb_position = self.rng.normal(0, 5, size=3)  # kpc
        grb_direction = self.rng.normal(0, 1, size=3)
        grb_direction /= np.linalg.norm(grb_direction)

        # Log event
        self.grb_events.append({
            'time_myr': self.current_time_myr,
            'position': grb_position.tolist(),
            'direction': grb_direction.tolist()
        })

        # Check for civilizations in beam
        destroyed = []
        for civ in self.civilizations:
            if not civ.alive:
                continue

            distance_kpc = np.linalg.norm(civ.position - grb_position)
            distance_pc = distance_kpc * 1000

            # Check if in beam and within lethal range
            if (self.grb_model.is_in_beam(grb_position, grb_direction, civ.position) and
                distance_kpc < self.grb_model.lethal_distance_kpc()):
                # Civilization destroyed by GRB
                civ.alive = False
                civ.cause_of_death = "gamma_ray_burst"
                civ.death_time_myr = self.current_time_myr

                self.telemetry.log_death(
                    time_myr=self.current_time_myr,
                    civilization_id=civ.id,
                    kardashev=civ.kardashev_level,
                    social_maturity=civ.maturity.maturity_level,
                    cause="gamma_ray_burst"
                )

                self.events_this_step += 1
                destroyed.append((civ.id, distance_pc))

        if destroyed:
            print(f"    ☄️  GAMMA-RAY BURST at T={self.current_time_myr:.1f} Myr!")
            for civ_id, dist in destroyed:
                print(f"       Destroyed Civ{civ_id} at {dist:.1f} pc (in lethal beam)")

    def print_final_statistics(self):
        """Print final simulation statistics."""
        alive = [c for c in self.civilizations if c.alive]
        dead = [c for c in self.civilizations if not c.alive]

        print(f"Final Status:")
        print(f"  Alive: {len(alive)}/{self.num_civilizations} ({100*len(alive)/self.num_civilizations:.1f}%)")
        print(f"  Dead: {len(dead)}/{self.num_civilizations} ({100*len(dead)/self.num_civilizations:.1f}%)")

        if dead:
            print(f"\nCauses of Death:")
            causes = {}
            for c in dead:
                causes[c.cause_of_death] = causes.get(c.cause_of_death, 0) + 1
            for cause, count in sorted(causes.items(), key=lambda x: -x[1]):
                print(f"  {cause}: {count}")

        print(f"\nAstrophysical Events:")
        print(f"  Supernovae: {len(self.supernova_events)}")
        print(f"  Gamma-ray bursts: {len(self.grb_events)}")

        if alive:
            avg_k = np.mean([c.kardashev_level for c in alive])
            avg_m = np.mean([c.maturity.maturity_level for c in alive])
            print(f"\nSurvivors:")
            print(f"  Avg Kardashev: {avg_k:.2f}")
            print(f"  Avg Maturity: {avg_m:.2f}")

    def export_visualization_data(self, output_path: str = "realistic_3d_export.json"):
        """Export data for 3D visualization."""
        exporter = VisualizationExporter()

        # Gather telemetry data
        telemetry_dict = self.telemetry.export_to_dict()

        # Transform crisis events
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

        # Gather development histories WITH 3D POSITIONS
        civilization_histories = []
        for civ in self.civilizations:
            if civ.development_history:
                hist_dict = civ.development_history.to_dict()
                hist_dict['development_snapshots'] = hist_dict.pop('snapshots', [])
                hist_dict['id'] = civ.id
                hist_dict['development_path_type'] = self.development_tracker.classify_development_path(
                    civ.development_history
                )
                hist_dict['position'] = civ.position.tolist()  # 3D position!
                hist_dict['alive'] = civ.alive
                hist_dict['cause_of_death'] = civ.cause_of_death
                hist_dict['death_time_myr'] = civ.death_time_myr
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

        # Export
        export = exporter.export_all(
            telemetry_data=telemetry_data,
            civilization_histories=civilization_histories,
            cooperation_records=cooperation_records,
            metadata={
                'num_civilizations': self.num_civilizations,
                'num_stars': self.num_stars,
                'duration_myr': self.current_time_myr,
                'seed': self.seed,
                'supernova_events': self.supernova_events,
                'grb_events': self.grb_events
            }
        )

        export.to_json(output_path)
        print(f"\n📁 Visualization data exported to: {output_path}")

        print_summary_report(export)

        return export

    def export_3d_data(self, output_path: str = "realistic_3d_data.json"):
        """Export simplified data structure for 3D visualization."""
        import json

        # Build civilization list with 3D positions
        civilizations = []
        for civ in self.civilizations:
            civ_data = {
                'id': civ.id,
                'position': civ.position.tolist(),  # 3D [x, y, z] in kpc
                'alive': civ.alive,
                'cause_of_death': civ.cause_of_death,
                'death_time_myr': civ.death_time_myr,
                'kardashev_level': civ.kardashev_level,
                'maturity_level': civ.maturity.maturity_level,
            }

            # Add development history snapshots
            if civ.development_history:
                snapshots = []
                for snap in civ.development_history.snapshots:
                    snapshots.append({
                        'time_myr': snap.time_myr,
                        'kardashev_level': snap.kardashev_level,
                        'maturity_level': snap.maturity_level,
                        'development_velocity': snap.development_velocity
                    })
                civ_data['development_history'] = snapshots
            else:
                civ_data['development_history'] = []

            civilizations.append(civ_data)

        # Build supernova events with positions
        supernova_events = []
        for sn in self.supernova_events:
            supernova_events.append({
                'time_myr': sn['time_myr'],
                'position': sn['position'],  # Already a list
                'star_index': sn['star_index']
            })

        # Build GRB events with positions
        grb_events = []
        for grb in self.grb_events:
            grb_events.append({
                'time_myr': grb['time_myr'],
                'position': grb['position'],  # Already a list
                'direction': grb['direction']  # Already a list
            })

        export_data = {
            'civilizations': civilizations,
            'supernova_events': supernova_events,
            'grb_events': grb_events,
            'metadata': {
                'num_civilizations': self.num_civilizations,
                'num_stars': self.num_stars,
                'duration_myr': self.current_time_myr,
                'seed': self.seed,
                'num_alive': sum(1 for c in self.civilizations if c.alive),
                'num_dead': sum(1 for c in self.civilizations if not c.alive)
            }
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"📊 3D visualization data exported to: {output_path}")

        return export_data


def main():
    """Run the realistic 3D simulation."""
    print("\n" + "="*70)
    print("REALISTIC 3D GALACTIC CIVILIZATION SIMULATION")
    print("="*70)
    print("\nFeatures:")
    print("  • 3D galactic positions for all civilizations")
    print("  • Active supernova and GRB hazards")
    print("  • Adaptive time stepping")
    print("  • MUCH tougher survival parameters")
    print("  • Full integration of all 9 survival mechanics")
    print("\n⚠️  This is NOT easy mode - expect casualties!\n")

    sim = Realistic3DSimulation(
        num_stars=100000,
        num_civilizations=20,
        seed=42
    )

    sim.initialize()
    sim.run(duration_myr=1000.0, print_interval_myr=100.0)
    sim.export_visualization_data()
    sim.export_3d_data()  # Export 3D-specific data

    print("\n" + "="*70)
    print("Next step: Run 3D visualization script to see the results!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
