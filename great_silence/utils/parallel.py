"""Parallel processing utilities for civilization expansion."""

import numpy as np
from scipy.spatial import cKDTree
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class ThreadLocalProbeBuffer:
    """Thread-local buffer for probe state."""

    probe_states: List = field(default_factory=list)
    arrivals: List = field(default_factory=list)
    replications: List = field(default_factory=list)
    new_probes: List = field(default_factory=list)
    new_events: List = field(default_factory=list)
    extinction_updates: List = field(default_factory=list)

    def clear(self) -> None:
        """Clear all buffers."""
        self.probe_states.clear()
        self.arrivals.clear()
        self.replications.clear()
        self.new_probes.clear()
        self.new_events.clear()
        self.extinction_updates.clear()


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
    positions: np.ndarray,
    civ_ids: List[int],
    max_distance_kpc: float
) -> List[List[int]]:
    """Partition civilizations into causally independent groups.

    Uses scipy KD-tree for O(N log N) pair finding instead of O(N²).

    Two civilizations are causally connected if light can travel
    between them within the timestep.

    Args:
        positions: (N, 3) array of civilization positions in kpc
        civ_ids: List of civilization IDs (used to map back)
        max_distance_kpc: Maximum causal connection distance in kpc

    Returns:
        List of groups, where each group is a list of indices into positions
    """
    n = len(positions)
    
    if n == 0:
        return []
    
    if n == 1:
        return [[0]]
    
    tree = cKDTree(positions)
    pairs = tree.query_pairs(max_distance_kpc)
    
    adjacency = {i: set() for i in range(n)}
    for i, j in pairs:
        adjacency[i].add(j)
        adjacency[j].add(i)
    
    groups = []
    visited = set()
    
    for start in range(n):
        if start in visited:
            continue
        
        group = []
        stack = [start]
        
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            
            visited.add(current)
            group.append(current)
            
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    stack.append(neighbor)
        
        groups.append(group)
    
    return groups


def find_causal_groups_with_colonies(
    positions: np.ndarray,
    civ_ids: List[int],
    colonized_systems: List[Set[int]],
    max_distance_kpc: float
) -> List[List[int]]:
    """Partition civilizations with colony overlap checking.

    Uses scipy KD-tree for O(N log N) distance-based pair finding.
    Also considers shared colonized systems as causal connections.

    Args:
        positions: (N, 3) array of civilization positions in kpc
        civ_ids: List of civilization IDs
        colonized_systems: List of colonized star sets (one per civ)
        max_distance_kpc: Maximum causal connection distance in kpc

    Returns:
        List of groups, where each group is a list of indices into positions
    """
    n = len(positions)
    
    if n == 0:
        return []
    
    if n == 1:
        return [[0]]
    
    tree = cKDTree(positions)
    distance_pairs = tree.query_pairs(max_distance_kpc)
    
    adjacency = {i: set() for i in range(n)}
    
    for i, j in distance_pairs:
        adjacency[i].add(j)
        adjacency[j].add(i)
    
    for i in range(n):
        for j in range(i + 1, n):
            if j in adjacency[i]:
                continue
            if len(colonized_systems[i] & colonized_systems[j]) > 0:
                adjacency[i].add(j)
                adjacency[j].add(i)
    
    groups = []
    visited = set()
    
    for start in range(n):
        if start in visited:
            continue
        
        group = []
        stack = [start]
        
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            
            visited.add(current)
            group.append(current)
            
            for neighbor in adjacency[current]:
                if neighbor not in visited:
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
