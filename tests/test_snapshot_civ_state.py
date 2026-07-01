"""Regression tests for per-snapshot civilization state capture.

Snapshots must record each civilization's state *at snapshot time*, not a live
reference that reflects the end-of-simulation state. Storing references caused
per-frame ``is_active`` (and ``kardashev_scale``) to read as the final value in
every frame, so the visualization never showed any active civilizations.
"""

from great_silence import GalaxySimulation, SimulationConfig


def _run_sim_with_civs():
    config = SimulationConfig()
    config.galaxy.total_stars = 3000
    config.simulation.simulation_duration_gyr = 4.0
    config.simulation.save_snapshots = True
    config.simulation.snapshot_interval_myr = 50.0
    config.civilization.fraction_stars_with_planets = 1.0
    config.civilization.fraction_develop_life = 0.9
    config.civilization.fraction_develop_intelligence = 0.6
    config.civilization.fraction_develop_technology = 0.6
    sim = GalaxySimulation(config)
    sim.initialize()
    sim.run(verbose=False)
    return sim


def test_snapshot_active_count_matches_stored_states():
    """Per-civ is_active in each snapshot must agree with its active count."""
    sim = _run_sim_with_civs()
    assert len(sim.snapshots) > 0

    for snap in sim.snapshots:
        recomputed = sum(c.is_active for c in snap.civilization_states)
        assert recomputed == snap.active_civilizations, (
            f"snapshot t={snap.time_myr:.1f} Myr: stored active count "
            f"{snap.active_civilizations} != is_active sum {recomputed} "
            "(civilization_states holds stale/aliased references)"
        )


def test_some_snapshot_shows_active_civilizations():
    """At least one snapshot must expose an active civilization to the viz layer."""
    sim = _run_sim_with_civs()

    max_active_via_states = max(
        sum(c.is_active for c in snap.civilization_states) for snap in sim.snapshots
    )
    max_active_via_count = max(snap.active_civilizations for snap in sim.snapshots)

    # Sanity: the simulation did produce active civs at some point.
    assert max_active_via_count > 0, "test sim produced no active civilizations"
    # The per-civ states must expose them too (this is what the viz reads).
    assert (
        max_active_via_states > 0
    ), "no snapshot exposes an active civilization via civilization_states"
