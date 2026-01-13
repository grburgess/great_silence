"""Parallel processing utilities for civilization expansion."""

import numpy as np
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from numba import jit, prange


@dataclass
class ThreadLocalProbeBuffer:
    """Thread-local buffer for probe state."""

    probe_states: List = field(default_factory=list)
    arrivals: List = field(default_factory=list)
    replications: List = field(default_factory=list)

    def clear(self) -> None:
        """Clear all buffers."""
        self.probe_states.clear()
        self.arrivals.clear()
        self.replications.clear()


def compute_light_travel_distance(dt_myr: float) -> float:
    """Compute light travel distance for a timestep.

    Args:
        dt_myr: Timestep in million years

    Returns:
        Distance in kiloparsecs
    """
    C_PC_YR = 0.3066  # Light speed in pc/yr
    c_kpc_myr = C_PC_YR / 1e6  # Light speed in kpc/Myr
    return c_kpc_myr * dt_myr * 1e6


def find_causal_groups_simple(
    civilizations: List,
    dt_myr: float,
    positions: np.ndarray,
    check_sharing: bool = False
) -> List[List]:
    """Partition civilizations into causally independent groups.

    Two civilizations are causally connected if light can travel
    between them within the timestep.

    Args:
        civilizations: List of CivilizationState objects
        dt_myr: Timestep in million years
        positions: (N, 3) array of civilization positions
        check_sharing: Check for shared colonized systems

    Returns:
        List of causally independent groups
    """
    if len(civilizations) == 0:
        return []

    if len(civilizations) == 1:
        return [[civilizations[0]]]

    light_travel_distance = compute_light_travel_distance(dt_myr)
    max_distance = light_travel_distance

    n = len(civilizations)
    adjacency = np.zeros((n, n), dtype=bool)

    for i in range(n):
        for j in range(i + 1, n):
            dist = np.linalg.norm(positions[i] - positions[j])
            if dist <= max_distance:
                adjacency[i, j] = True
                adjacency[j, i] = True

    groups = []
    visited = np.zeros(n, dtype=bool)

    for i in range(n):
        if visited[i]:
            continue

        group = []
        stack = [i]

        while stack:
            current = stack.pop()
            if visited[current]:
                continue

            visited[current] = True
            group.append(civilizations[current])

            for neighbor in np.where(adjacency[current])[0]:
                if not visited[neighbor]:
                    stack.append(neighbor)

        groups.append(group)

    return groups


def find_causal_groups_with_colonies(
    civilizations: List,
    dt_myr: float,
    positions: np.ndarray,
    colony_map: Dict[int, Set[int]],
    check_sharing: bool = True
) -> List[List]:
    """Partition civilizations with colony overlap checking.

    Similar to find_causal_groups_simple but also considers
    shared colonized systems as causal connections.

    Args:
        civilizations: List of CivilizationState objects
        dt_myr: Timestep in million years
        positions: (N, 3) array of civilization positions
        colony_map: civ_id -> set of colonized star indices
        check_sharing: Check for shared colonized systems

    Returns:
        List of causally independent groups
    """
    if len(civilizations) == 0:
        return []

    if len(civilizations) == 1 or not check_sharing:
        return [[civilizations[0]]]

    light_travel_distance = compute_light_travel_distance(dt_myr)
    max_distance = light_travel_distance

    n = len(civilizations)
    adjacency = np.zeros((n, n), dtype=bool)

    for i in range(n):
        for j in range(i + 1, n):
            civ_i = civilizations[i]
            civ_j = civilizations[j]

            connected = False

            dist = np.linalg.norm(positions[i] - positions[j])
            if dist <= max_distance:
                connected = True

            if check_sharing:
                colonized_i = colony_map.get(civ_i.civ_id, set())
                colonized_j = colony_map.get(civ_j.civ_id, set())

                if len(colonized_i & colonized_j) > 0:
                    connected = True

            if connected:
                adjacency[i, j] = True
                adjacency[j, i] = True

    groups = []
    visited = np.zeros(n, dtype=bool)

    for i in range(n):
        if visited[i]:
            continue

        group = []
        stack = [i]

        while stack:
            current = stack.pop()
            if visited[current]:
                continue

            visited[current] = True
            group.append(civilizations[current])

            for neighbor in np.where(adjacency[current])[0]:
                if not visited[neighbor]:
                    stack.append(neighbor)

        groups.append(group)

    return groups


def should_use_parallelization(
    config,
    n_civs: int,
    n_probes: int,
    n_colonies: int
) -> bool:
    """Determine if parallelization should be used.

    Parallelization is beneficial when:
    - Multiple civilizations exist
    - Sufficient probes to parallelize
    - Not too many colonies (memory overhead)

    Args:
        config: SimulationConfig object
        n_civs: Number of active civilizations
        n_probes: Number of active probes
        n_colonies: Number of colonized stars

    Returns:
        True if parallelization should be used
    """
    if not config.simulation.parallel_processing:
        return False

    if not config.simulation.enable_within_sim_parallel:
        return False

    if n_civs < config.simulation.parallel_min_civs_threshold:
        return False

    return True


__all__ = [
    "ThreadLocalProbeBuffer",
    "compute_light_travel_distance",
    "find_causal_groups_simple",
    "find_causal_groups_with_colonies",
    "should_use_parallelization",
]
