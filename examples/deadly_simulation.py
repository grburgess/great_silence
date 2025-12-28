"""
DEADLY simulation - actually kills civilizations.

Changes from realistic version:
- Cooperation DISABLED (civilizations face crises alone)
- Supernova rate INCREASED 100x
- GRB rate INCREASED 100x
- Crisis difficulty INCREASED dramatically (3x severity, 80% response reduction)
- Added catastrophic failure chance (10% instant death per crisis)
- Reduced crisis resistance
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
from datetime import datetime

# Import the base simulation
from examples.realistic_3d_simulation import (
    Realistic3DSimulation,
    AdaptiveTimestepper
)

# Import production plotting
from examples.production_run import (
    plot_3d_snapshot,
    plot_crisis_statistics,
    plot_development_timelines,
    create_evolution_animation
)


class DeadlySimulation(Realistic3DSimulation):
    """
    DEADLY version - civilizations actually die.

    Key differences:
    - No cooperation (isolated civilizations)
    - 100x astrophysical hazard rates
    - Crises are catastrophically hard
    - Catastrophic failure chance
    """

    def __init__(self, num_stars=100000, num_civilizations=50, seed=42):
        """Initialize with more civilizations to see the carnage."""
        super().__init__(num_stars, num_civilizations, seed)

        # DEADLY PARAMETERS
        self.cooperation_enabled = False  # NO HELP!
        self.sn_rate_multiplier = 100.0  # 100x more supernovae
        self.grb_rate_multiplier = 100.0  # 100x more GRBs
        self.crisis_severity_multiplier = 3.0  # 3x harder crises
        self.response_reduction = 0.8  # 80% worse responses
        self.catastrophic_failure_chance = 0.10  # 10% instant death per crisis

        print(f"\n💀 DEADLY MODE ENABLED 💀")
        print(f"  Cooperation: DISABLED")
        print(f"  Supernova rate: {self.sn_rate_multiplier}x normal")
        print(f"  GRB rate: {self.grb_rate_multiplier}x normal")
        print(f"  Crisis severity: {self.crisis_severity_multiplier}x")
        print(f"  Response quality: {100*(1-self.response_reduction):.0f}% of normal")
        print(f"  Catastrophic failure: {self.catastrophic_failure_chance*100:.0f}% per crisis")
        print()

    def check_astrophysical_hazards(self):
        """Check for supernovae and GRBs with MUCH higher rates."""
        # SUPERNOVAE - Check 100x more frequently
        for i in range(len(self.galaxy.masses)):
            if self.supernova_model.will_go_supernova(
                stellar_mass=self.galaxy.masses[i],
                stellar_age_gyr=self.galaxy.ages[i],
                dt_myr=self.current_dt_myr * self.sn_rate_multiplier  # 100x!
            ):
                self.process_supernova(i)

        # GAMMA-RAY BURSTS - Simplified version
        # Pick a random position in the galaxy and check if any civs are in lethal range
        grb_base_rate = (0.01 / 100)  # per Myr
        grb_probability = grb_base_rate * self.current_dt_myr * self.grb_rate_multiplier

        if self.rng.random() < grb_probability:
            # Random GRB position in galaxy
            grb_pos = self.rng.normal(0, 3.5, 3)  # Random position in disk
            grb_direction = self.rng.normal(0, 1, 3)
            grb_direction /= np.linalg.norm(grb_direction)

            # Record event
            self.grb_events.append({
                'time_myr': self.current_time_myr,
                'position': grb_pos.tolist(),
                'beam_direction': grb_direction.tolist()
            })

            # Check all civilizations
            for civ in self.civilizations:
                if not civ.alive:
                    continue

                # Distance and angle
                to_civ = civ.position - grb_pos
                distance_pc = np.linalg.norm(to_civ) * 1000  # kpc to pc

                # Beam angle (degrees)
                to_civ_norm = to_civ / np.linalg.norm(to_civ)
                angle_rad = np.arccos(np.clip(np.dot(grb_direction, to_civ_norm), -1, 1))
                angle_deg = np.degrees(angle_rad)

                # Check if in lethal beam (10 degree cone, 1000 pc range)
                if angle_deg < 10.0 and distance_pc < 1000.0:
                    civ.alive = False
                    civ.cause_of_death = "gamma_ray_burst"
                    civ.death_time_myr = self.current_time_myr
                    print(f"    ☠️  Civ{civ.id} OBLITERATED by gamma-ray burst!")

    def evaluate_crisis_response(self, civ, crisis_type, crisis_state):
        """Evaluate if civilization survives crisis - MUCH HARDER."""
        # Base response
        base_response = civ.maturity.maturity_to_kardashev_ratio * 0.3

        # Trait modifier (simplified)
        trait_modifier = 1.0

        # Get experience bonus
        experience_bonus = 0.0
        if civ.experience and hasattr(civ.experience, 'crisis_experience'):
            if crisis_type.value in civ.experience.crisis_experience:
                exp = civ.experience.crisis_experience[crisis_type.value]
                experience_bonus = min(0.3, exp.successful_resolutions * 0.05)

        # DEADLY: Apply massive reductions
        response_quality = (
            base_response * trait_modifier * (1 - self.response_reduction) +  # 80% penalty!
            experience_bonus * 0.3  # Experience barely helps
        ) * 0.2  # Overall 80% reduction

        # Apply 3x severity multiplier
        effective_severity = min(1.0, crisis_state.severity * self.crisis_severity_multiplier)

        # CATASTROPHIC FAILURE CHECK - instant death chance
        if self.rng.random() < self.catastrophic_failure_chance:
            return False  # Instant death!

        # Survival probability
        survival_prob = max(0.01, response_quality * (1.0 - effective_severity))

        return self.rng.random() < survival_prob

    def offer_cooperation(self, civ):
        """Cooperation is DISABLED - no help available."""
        # Civilizations are on their own
        return []

    def advance_active_crises(self, civ):
        """Advance crises with NO COOPERATION."""
        if not civ.active_crises:
            return

        for crisis_type, crisis_state in list(civ.active_crises.items()):
            # Calculate response quality (DEADLY version)
            base_response = civ.maturity.maturity_to_kardashev_ratio * 0.3

            # Trait modifier (simplified - just use 1.0)
            trait_modifier = 1.0

            # Experience bonus
            experience_bonus = 0.0
            if civ.experience and hasattr(civ.experience, 'crisis_experience'):
                if crisis_type.value in civ.experience.crisis_experience:
                    exp = civ.experience.crisis_experience[crisis_type.value]
                    experience_bonus = min(0.3, exp.successful_resolutions * 0.05)

            # DEADLY: Massive reductions
            response_quality = (
                base_response * trait_modifier * (1 - self.response_reduction) +
                experience_bonus * 0.3
            ) * 0.2  # 80% overall reduction

            # Advance crisis stage
            new_state = self.crisis_system.advance_crisis(
                crisis_state,
                response_quality=response_quality,
                dt_myr=self.current_dt_myr
            )

            # Check resolution
            if new_state.stage.value == "resolved":
                # Crisis resolved - check if survived
                survived = self.evaluate_crisis_response(civ, crisis_type, new_state)

                if survived:
                    self.civilization_survives_crisis(civ, crisis_type, new_state)
                    del civ.active_crises[crisis_type]
                else:
                    # DEATH
                    self.civilization_dies_from_crisis(civ, crisis_type, new_state)

            elif new_state.stage.value == "failed":
                # Crisis failed - civilization dies
                self.civilization_dies_from_crisis(civ, crisis_type, new_state)

            else:
                # Crisis continues
                civ.active_crises[crisis_type] = new_state

    def civilization_dies_from_crisis(self, civ, crisis_type, crisis_state):
        """Civilization dies from crisis failure."""
        civ.alive = False
        civ.cause_of_death = crisis_type.value
        civ.death_time_myr = self.current_time_myr

        # Remove from active crises
        if crisis_type in civ.active_crises:
            del civ.active_crises[crisis_type]

        print(f"    ☠️  Civ{civ.id} DIES from {crisis_type.value}!")


def main():
    """Run DEADLY simulation."""
    print("\n" + "="*70)
    print("💀 DEADLY GALACTIC CIVILIZATION SIMULATION 💀")
    print("="*70)
    print("\nConfiguration:")
    print("  Duration: 10,000 Myr (10 Gyr)")
    print("  Civilizations: 50 (expect heavy casualties)")
    print("  Stars: 100,000")
    print("  Mode: DEADLY - No cooperation, 100x astrophysical hazards")
    print("\n" + "="*70 + "\n")

    # Create run directory
    run_dir = Path("outputs") / f"deadly_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "data").mkdir(exist_ok=True)
    (run_dir / "plots" / "3d").mkdir(parents=True, exist_ok=True)
    (run_dir / "plots" / "statistics").mkdir(parents=True, exist_ok=True)
    (run_dir / "plots" / "timelines").mkdir(parents=True, exist_ok=True)
    (run_dir / "animations").mkdir(exist_ok=True)

    print(f"📁 Output directory: {run_dir}\n")

    # Run simulation
    print("🚀 Starting DEADLY simulation...\n")
    sim = DeadlySimulation(
        num_stars=100000,
        num_civilizations=50,  # More civs to see deaths
        seed=42
    )

    sim.initialize()
    sim.run(duration_myr=10000.0, print_interval_myr=1000.0)

    # Export data
    print("\n📊 Exporting data...")
    sim.export_3d_data(str(run_dir / "data" / "simulation_3d_data.json"))
    sim.export_visualization_data(str(run_dir / "data" / "realistic_3d_export.json"))

    # Load for plotting
    with open(run_dir / "data" / "simulation_3d_data.json", 'r') as f:
        plot_data = json.load(f)

    # Generate visualizations
    print("\n🎨 Generating visualizations...")
    plot_3d_snapshot(plot_data, run_dir / "plots" / "3d" / "galaxy_snapshot.png")
    plot_crisis_statistics(plot_data, run_dir / "plots" / "statistics" / "crisis_stats.png", run_dir)
    plot_development_timelines(plot_data, run_dir / "plots" / "timelines" / "development_evolution.png")
    create_evolution_animation(plot_data, run_dir / "animations" / "galaxy_evolution.gif")

    # Summary
    num_alive = plot_data['metadata']['num_alive']
    num_dead = plot_data['metadata']['num_dead']
    num_total = plot_data['metadata']['num_civilizations']
    num_sn = len(plot_data.get('supernova_events', []))
    num_grb = len(plot_data.get('grb_events', []))

    summary = f"""
{'='*70}
💀 DEADLY SIMULATION RESULTS 💀
{'='*70}

Duration: 10,000 Myr
Starting Civilizations: {num_total}

FINAL CASUALTY REPORT:
  ✅ Survived: {num_alive} ({num_alive/num_total*100:.1f}%)
  ☠️  Died: {num_dead} ({num_dead/num_total*100:.1f}%)

CAUSES OF DEATH:
"""

    # Count death causes
    death_causes = {}
    for civ in plot_data['civilizations']:
        if not civ['alive']:
            cause = civ.get('cause_of_death', 'unknown')
            death_causes[cause] = death_causes.get(cause, 0) + 1

    for cause, count in sorted(death_causes.items(), key=lambda x: x[1], reverse=True):
        summary += f"  {cause}: {count}\n"

    summary += f"""
ASTROPHYSICAL CARNAGE:
  💥 Supernovae: {num_sn}
  🌟 Gamma-ray Bursts: {num_grb}

Output: {run_dir}
{'='*70}
"""

    print(summary)

    # Save summary
    with open(run_dir / "SUMMARY.txt", 'w') as f:
        f.write(summary)

    print(f"\n✅ DEADLY simulation complete!")
    print(f"📁 All outputs: {run_dir}\n")


if __name__ == "__main__":
    main()
