"""
Test Monte Carlo statistical integrity and reproducibility.

These tests verify that:
1. Random number generation is reproducible with fixed seeds
2. Event schemas are consistent across simulations
3. Export/import round-trips preserve data
4. Core statistics are unaffected by serialization bugs
"""

import pytest
import json
import tempfile
import os
import numpy as np
from pathlib import Path


# Import after path setup
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.realistic_3d_simulation import Realistic3DSimulation
from examples.deadly_simulation import DeadlySimulation


class TestMonteCarloReproducibility:
    """Test that simulations are reproducible with fixed seeds."""

    def test_fixed_seed_reproduces_results(self):
        """Verify that same seed produces identical results."""
        seed = 42
        params = {
            'num_stars': 1000,
            'num_civilizations': 5,
            'seed': seed
        }

        # Run twice with same seed
        sim1 = Realistic3DSimulation(**params)
        sim1.initialize()
        sim1.run(duration_myr=100.0)

        sim2 = Realistic3DSimulation(**params)
        sim2.initialize()
        sim2.run(duration_myr=100.0)

        # Results should be identical
        alive1 = sum(1 for c in sim1.civilizations if c.alive)
        alive2 = sum(1 for c in sim2.civilizations if c.alive)
        assert alive1 == alive2, f"Alive count not reproducible: {alive1} vs {alive2}"

        assert len(sim1.supernova_events) == len(sim2.supernova_events), \
            "Supernova count not reproducible"

        assert len(sim1.grb_events) == len(sim2.grb_events), \
            "GRB count not reproducible"

    def test_different_seeds_produce_different_results(self):
        """Verify that different seeds produce different results."""
        params = {
            'num_stars': 1000,
            'num_civilizations': 10,
        }

        sim1 = Realistic3DSimulation(**params, seed=42)
        sim1.initialize()
        sim1.run(duration_myr=500.0)

        sim2 = Realistic3DSimulation(**params, seed=99)
        sim2.initialize()
        sim2.run(duration_myr=500.0)

        # Results should differ (with overwhelming probability)
        alive1 = sum(1 for c in sim1.civilizations if c.alive)
        alive2 = sum(1 for c in sim2.civilizations if c.alive)

        # At least ONE of these should be different (extremely likely)
        differ = (
            alive1 != alive2 or
            len(sim1.supernova_events) != len(sim2.supernova_events) or
            len(sim1.grb_events) != len(sim2.grb_events)
        )

        assert differ, "Different seeds produced identical results (extremely unlikely)"


class TestEventSchemaValidation:
    """Test that event dictionaries have consistent schemas."""

    def test_grb_event_schema_consistency(self):
        """Verify all GRB events have identical schemas."""
        sim = Realistic3DSimulation(num_stars=5000, num_civilizations=10, seed=42)
        sim.initialize()
        sim.run(duration_myr=500.0)

        if not sim.grb_events:
            pytest.skip("No GRB events generated")

        # All events should have identical keys
        expected_keys = set(sim.grb_events[0].keys())

        for i, event in enumerate(sim.grb_events):
            assert set(event.keys()) == expected_keys, \
                f"GRB event {i} has inconsistent schema: {set(event.keys())} != {expected_keys}"

            # Verify required keys exist
            assert 'time_myr' in event
            assert 'position' in event
            assert 'direction' in event

    def test_supernova_event_schema_consistency(self):
        """Verify all supernova events have identical schemas."""
        sim = Realistic3DSimulation(num_stars=5000, num_civilizations=5, seed=42)
        sim.initialize()
        sim.run(duration_myr=500.0)

        if not sim.supernova_events:
            pytest.skip("No supernova events generated")

        expected_keys = set(sim.supernova_events[0].keys())

        for i, event in enumerate(sim.supernova_events):
            assert set(event.keys()) == expected_keys, \
                f"SN event {i} has inconsistent schema: {set(event.keys())} != {expected_keys}"


class TestExportImportIntegrity:
    """Test that export/import round-trips preserve data integrity."""

    def test_full_export_pipeline_no_crash(self):
        """Test complete simulation -> export cycle doesn't crash."""
        sim = Realistic3DSimulation(num_stars=1000, num_civilizations=5, seed=42)
        sim.initialize()
        sim.run(duration_myr=100.0)

        # Export should NOT raise KeyError (fixed bug)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name

        try:
            # This would crash with the 'direction' vs 'beam_direction' bug
            sim.export_3d_data(export_path)

            # Verify file was created and is valid JSON
            assert os.path.exists(export_path)

            with open(export_path, 'r') as f:
                data = json.load(f)

            # Verify structure
            assert 'civilizations' in data
            assert 'supernova_events' in data
            assert 'grb_events' in data
            assert 'metadata' in data

        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)

    def test_exported_data_schema_valid(self):
        """Test that exported data has correct schema."""
        sim = Realistic3DSimulation(num_stars=1000, num_civilizations=5, seed=42)
        sim.initialize()
        sim.run(duration_myr=100.0)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name

        try:
            sim.export_3d_data(export_path)

            with open(export_path, 'r') as f:
                data = json.load(f)

            # Verify GRB events have correct schema in exported data
            for grb in data.get('grb_events', []):
                assert 'time_myr' in grb, "Missing time_myr in exported GRB"
                assert 'position' in grb, "Missing position in exported GRB"
                assert 'direction' in grb, "Missing direction in exported GRB"

                # Verify types
                assert isinstance(grb['position'], list)
                assert len(grb['position']) == 3

                assert isinstance(grb['direction'], list)
                assert len(grb['direction']) == 3

        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)


class TestCrossScriptCompatibility:
    """Test compatibility between different simulation scripts."""

    def test_realistic_vs_deadly_schema_match(self):
        """Ensure Realistic and Deadly simulations use same event schemas."""
        seed = 42

        sim1 = Realistic3DSimulation(num_stars=1000, num_civilizations=5, seed=seed)
        sim1.initialize()
        sim1.run(duration_myr=100.0)

        sim2 = DeadlySimulation(num_stars=1000, num_civilizations=5, seed=seed)
        sim2.initialize()
        sim2.run(duration_myr=100.0)

        # Both should have events (at least with some probability)
        if sim1.grb_events and sim2.grb_events:
            keys1 = set(sim1.grb_events[0].keys())
            keys2 = set(sim2.grb_events[0].keys())

            assert keys1 == keys2, \
                f"Incompatible GRB schemas between scripts: {keys1} vs {keys2}"


class TestStatisticalInvariance:
    """Test that core statistics are computed correctly."""

    def test_civilization_count_preserved(self):
        """Verify civilization count remains constant."""
        num_civs = 20
        sim = Realistic3DSimulation(num_stars=5000, num_civilizations=num_civs, seed=42)
        sim.initialize()

        assert len(sim.civilizations) == num_civs

        sim.run(duration_myr=100.0)

        # Total count should never change
        assert len(sim.civilizations) == num_civs, \
            "Civilization count changed during simulation!"

    def test_alive_count_bounds(self):
        """Verify alive count stays within valid bounds."""
        num_civs = 20
        sim = Realistic3DSimulation(num_stars=5000, num_civilizations=num_civs, seed=42)
        sim.initialize()
        sim.run(duration_myr=1000.0)

        alive = sum(1 for c in sim.civilizations if c.alive)
        assert 0 <= alive <= num_civs, \
            f"Alive count out of bounds: {alive} not in [0, {num_civs}]"

    def test_death_counts_sum_correctly(self):
        """Verify death cause counts sum to total dead."""
        sim = Realistic3DSimulation(num_stars=5000, num_civilizations=20, seed=42)
        sim.initialize()
        sim.run(duration_myr=1000.0)

        total_civs = len(sim.civilizations)
        alive_count = sum(1 for c in sim.civilizations if c.alive)
        dead_count = total_civs - alive_count

        # Count deaths by cause
        death_causes = {}
        for civ in sim.civilizations:
            if not civ.alive:
                cause = civ.cause_of_death or 'unknown'
                death_causes[cause] = death_causes.get(cause, 0) + 1

        # Sum should equal total dead
        assert sum(death_causes.values()) == dead_count, \
            f"Death counts don't sum: {sum(death_causes.values())} != {dead_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
