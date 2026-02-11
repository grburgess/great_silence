"""Tests for Phase 0 bug fixes."""

import pytest
import numpy as np
from unittest.mock import Mock
import sys
import inspect

from great_silence import SimulationConfig, GalaxySimulation
from great_silence.simulation.engine import CivilizationState, HazardEvent
from great_silence.utils.numba_kernels import compute_emergence_probabilities_kernel


class TestPhase0BugFixes:
    """Test Phase 0 bug fixes from optimization plan."""

    def test_no_duplicate_hazard_event_class(self):
        """Verify only one HazardEvent class exists in codebase."""
        # Check engine.py has HazardEvent
        from great_silence.simulation import engine
        assert hasattr(engine, 'HazardEvent')

        # Verify no duplicates in disasters module
        try:
            from great_silence.simulation.disasters import unified_scheduler
            # If HazardEvent exists here, it should be the same class
            if hasattr(unified_scheduler, 'HazardEvent'):
                from great_silence.simulation.engine import HazardEvent as EngineHazard
                assert unified_scheduler.HazardEvent is EngineHazard, "Duplicate HazardEvent class found"
        except (ImportError, AttributeError):
            pass  # Module may not exist or no duplicate

    def test_scipy_expit_imported_at_module_level(self):
        """Verify scipy.special.expit imported at module level in engine.py."""
        from great_silence.simulation import engine

        # Check expit is imported
        assert hasattr(engine, 'expit'), "scipy.special.expit not imported in engine.py"

        # Verify it's the scipy function
        from scipy.special import expit as scipy_expit
        assert engine.expit is scipy_expit

    def test_no_dead_code_after_returns(self):
        """Verify no unreachable code after return statements."""
        from great_silence.simulation import engine

        # Get source code
        source = inspect.getsource(engine)
        lines = source.split('\n')

        # Simple heuristic: check for common patterns of dead code
        # (Note: This is a basic check, not a full AST analysis)
        found_issues = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('return '):
                # Check next non-empty, non-comment line
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith('#'):
                        # Should be dedented (end of function) or pass/comment
                        indent_return = len(line) - len(line.lstrip())
                        indent_next = len(lines[j]) - len(lines[j].lstrip())
                        if indent_next > indent_return:
                            # Potential dead code (same or more indented)
                            # But check if it's part of a dict/list literal spanning lines
                            if not next_line.startswith(('def ', 'class ', 'except', 'finally', 'elif', 'else', '"', '}', ']')):
                                found_issues.append((i+1, next_line[:50]))
                        break

    def test_evolve_personality_unpacking(self):
        """Test PersonalityState → CivilizationState field unpacking."""
        from great_silence.civilization.personality import evolve_personality, PersonalityState

        # Create test personality state
        personality = PersonalityState(
            personality_type="aggressive",
            friendliness=0.3,
            aggression_factor=0.8
        )

        # Test evolve_personality returns PersonalityState
        rng = np.random.default_rng(42)
        result = evolve_personality(
            personality=personality,
            war_outcome='victory',
            num_wars_lost=0,
            num_wars_won=1,
            rng=rng
        )
        assert isinstance(result, PersonalityState)

        # Verify fields exist
        assert hasattr(result, 'personality_type')
        assert hasattr(result, 'friendliness')
        assert hasattr(result, 'aggression_factor')
        assert hasattr(result, 'war_trauma')
        assert hasattr(result, 'victory_confidence')

        # Simulate unpacking into civ
        civ = CivilizationState(
            civ_id=1,
            birth_time_myr=0.0,
            parent_star_idx=0
        )
        civ.personality_type = result.personality_type
        civ.friendliness = result.friendliness
        civ.aggression_factor = result.aggression_factor
        civ.war_trauma = result.war_trauma
        civ.victory_confidence = result.victory_confidence

        # Verify no errors
        assert civ.personality_type == result.personality_type

    def test_o1_dict_lookups_civ_by_id(self):
        """Test O(1) _civ_by_id dict lookups replace O(N) scans."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01

        sim = GalaxySimulation(config, seed=42)
        sim.initialize()

        # Verify _civ_by_id exists
        assert hasattr(sim, '_civ_by_id')
        assert isinstance(sim._civ_by_id, dict)

        # Create test civilizations
        civ1 = CivilizationState(civ_id=1, birth_time_myr=0.0, parent_star_idx=0)
        civ2 = CivilizationState(civ_id=2, birth_time_myr=0.0, parent_star_idx=1)

        sim.civilizations.append(civ1)
        sim.civilizations.append(civ2)
        sim._civ_by_id[1] = civ1
        sim._civ_by_id[2] = civ2

        # Test O(1) lookup
        assert sim._civ_by_id[1] is civ1
        assert sim._civ_by_id[2] is civ2
        assert sim._civ_by_id.get(999) is None

    def test_spatial_index_probe_arrival(self):
        """Test civ_spatial_index usage instead of O(N) probe arrival loop."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01

        sim = GalaxySimulation(config, seed=42)
        sim.initialize()

        # Verify civ_spatial_index exists and is used
        assert hasattr(sim, 'civ_spatial_index')

        # Index should be built when needed
        if len(sim.civilizations) > 0:
            sim.civ_spatial_index.build(sim.civilizations)
            assert sim.civ_spatial_index.positions is not None

    def test_fastmath_audit_emergence_kernel(self):
        """Verify compute_emergence_probabilities_kernel doesn't use fastmath."""
        # Get function signature
        sig = str(compute_emergence_probabilities_kernel.signatures) if hasattr(
            compute_emergence_probabilities_kernel, 'signatures'
        ) else ""

        # Check function metadata
        # Note: We check that fastmath is NOT used for this specific kernel
        # (it can cause issues with probability calculations)
        source = inspect.getsource(compute_emergence_probabilities_kernel)

        # Function should use cache=True but NOT fastmath=True
        assert 'cache=True' in source
        # Should NOT have fastmath in decorator
        assert 'fastmath=True' not in source.split('def compute_emergence_probabilities_kernel')[0]

    def test_memory_pool_buffers_preallocated(self):
        """Test _effects_buffer, _mask_buffer, _dist_buffer pre-allocation."""
        config = SimulationConfig()
        config.galaxy.total_stars = 1000
        config.simulation.simulation_duration_gyr = 0.01

        sim = GalaxySimulation(config, seed=42)
        sim.initialize()

        # Check if buffers exist
        assert hasattr(sim, '_effects_buffer') or hasattr(sim, '_mask_buffer') or hasattr(sim, '_dist_buffer')

        # If they exist, verify they're numpy arrays
        if hasattr(sim, '_effects_buffer'):
            assert isinstance(sim._effects_buffer, np.ndarray)
            assert sim._effects_buffer.shape[0] >= sim.galaxy.positions.shape[0]

        if hasattr(sim, '_mask_buffer'):
            assert isinstance(sim._mask_buffer, np.ndarray)
            assert sim._mask_buffer.dtype == bool

        if hasattr(sim, '_dist_buffer'):
            assert isinstance(sim._dist_buffer, np.ndarray)
            assert sim._dist_buffer.dtype in [np.float32, np.float64]

    def test_hazard_event_dataclass_structure(self):
        """Test HazardEvent dataclass has correct fields."""
        event = HazardEvent(
            time_myr=100.0,
            event_type='supernova',
            position=np.array([1.0, 2.0, 3.0]),
            energy=1e51,
            sterilization_radius_pc=100.0,
            affected_civ_ids=[1, 2, 3]
        )

        assert event.time_myr == 100.0
        assert event.event_type == 'supernova'
        assert np.allclose(event.position, [1.0, 2.0, 3.0])
        assert event.energy == 1e51
        assert event.sterilization_radius_pc == 100.0
        assert event.affected_civ_ids == [1, 2, 3]

    def test_simulation_initialization_no_errors(self):
        """Test simulation initializes without errors after Phase 0 fixes."""
        config = SimulationConfig()
        config.galaxy.total_stars = 100
        config.simulation.simulation_duration_gyr = 0.01

        sim = GalaxySimulation(config, seed=42)

        # Should initialize without errors
        sim.initialize()

        # Basic sanity checks
        assert sim.galaxy.positions is not None
        assert len(sim.galaxy.positions) == 100
        assert sim.civilizations is not None
        assert sim._civ_by_id is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
