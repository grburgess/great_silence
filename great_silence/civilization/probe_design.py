"""
Self-replicating probe design parameters based on Kardashev scale.

These functions determine probe capabilities based on the civilization's
technological level when the expansion program is initiated.
"""


def probe_velocity_from_kardashev(kardashev_level: float) -> float:
    """
    Calculate probe velocity as fraction of c based on tech level.

    Probe velocity is locked at launch based on initial Kardashev level.
    Represents the propulsion technology available when expansion begins.

    Args:
        kardashev_level: Civilization's Kardashev scale when expansion starts

    Returns:
        Velocity as fraction of light speed (0.0 to ~0.1)

    Physical basis:
        K<0.85: No interstellar capability
        K=0.85-0.95: Early fusion drives (~0.15% c, 450 km/s)
        K=0.95-1.05: Mature fusion/light sails (0.5% c)
        K=1.05-1.50: Early antimatter rockets (1.5% c)
        K>1.50: Dyson-powered beamed propulsion (5% c)

    Realistic upper limit ~0.1c due to:
        - Interstellar medium damage at high velocity
        - Energy requirements scale as γmv²
        - Structural integrity of probe
    """
    if kardashev_level < 0.85:
        return 0.0  # No expansion capability
    elif kardashev_level < 0.95:
        return 0.0015  # 0.15% c (~450 km/s) - early fusion
    elif kardashev_level < 1.05:
        return 0.005   # 0.5% c - mature fusion
    elif kardashev_level < 1.50:
        return 0.015   # 1.5% c - early antimatter
    else:
        return 0.05    # 5% c - Dyson-powered (near maximum realistic)


def per_hop_range_from_kardashev(kardashev_level: float) -> float:
    """
    Calculate per-hop colonization range in parsecs.

    NOT the total expansion range, but how far each probe can target
    new systems from its current location. Determines branching density.

    Args:
        kardashev_level: Civilization's Kardashev scale

    Returns:
        Maximum range per hop in parsecs

    Physical basis:
        - Probes target nearest uncolonized stars, not distant ones
        - Range limited by:
          * Mission duration tolerance (even at 0.01c, 100pc = 32,600 years)
          * Communication/coordination capability
          * Risk accumulation over distance
          * Target density (more tech → can afford sparser colonization)

    Typical stellar density: ~0.1 stars/pc³ in solar neighborhood
    Within 50 pc sphere: ~50,000 stars, ~500-2000 habitable
    """
    if kardashev_level < 0.85:
        return 0.0
    elif kardashev_level < 0.95:
        return 30.0  # Conservative, nearby stars only
    elif kardashev_level < 1.20:
        return 50.0  # Moderate range
    else:
        return 100.0  # Extended range for high-K civilizations


def offspring_count(kardashev_level: float) -> int:
    """
    Calculate number of offspring probes created at each colony.

    Critical parameter for expansion rate: N^generations exponential growth.

    Args:
        kardashev_level: Civilization's Kardashev scale

    Returns:
        Number of offspring probes per replication event

    Physical basis:
        - Must extract resources from local system (asteroid mining, gas giants)
        - Manufacturing time scales with complexity
        - Energy requirements: each offspring needs propulsion system
        - Conservative: N=5-8 (slow exponential)
        - Aggressive: N=15-20 (fast exponential, high-K civs)

    Exponential growth examples:
        N=5, 10 generations: 9.7 million descendants
        N=8, 10 generations: 1.07 billion descendants
        N=15, 10 generations: 5.76×10^11 descendants
    """
    if kardashev_level < 0.85:
        return 0  # No expansion
    elif kardashev_level < 0.95:
        return 5  # Limited replication capability
    elif kardashev_level < 1.20:
        return 8  # Moderate
    else:
        return 12  # Mature Type I+ civilization


def replication_delay_years(kardashev_level: float) -> float:
    """
    Calculate time (in years) from probe arrival to offspring launch.

    Represents: arrival → survey → resource extraction → manufacturing → launch

    Args:
        kardashev_level: Civilization's Kardashev scale

    Returns:
        Replication delay in years

    Physical basis:
        K<0.95: Limited automation, slow ISRU
            - Survey phase: 10-20 years
            - Resource extraction setup: 50-100 years
            - Manufacturing per offspring: 50-100 years (parallel production)
            - Total: ~200-300 years

        K=0.95-1.20: Moderate automation
            - Faster resource processing
            - Better manufacturing templates
            - Total: ~100-150 years

        K>1.20: Advanced automation, Dyson-scale energy beaming
            - Highly parallel production
            - Pre-optimized manufacturing
            - Total: ~50 years

    This delay prevents instantaneous exponential explosion.
    """
    if kardashev_level < 0.85:
        return float('inf')  # Cannot replicate
    elif kardashev_level < 0.95:
        return 300.0  # Slow, limited automation
    elif kardashev_level < 1.20:
        return 150.0  # Moderate
    else:
        return 50.0   # Fast, Type I coordination


def min_metallicity_for_replication(
    kardashev_level: float,
    threshold_k085: float = -0.3,
    threshold_k095: float = -0.5,
    threshold_k120: float = -1.0
) -> float:
    """
    Minimum stellar metallicity [Fe/H] required for probe replication.

    Self-replicating probes need sufficient heavy elements (metals) in the
    target system for resource extraction and manufacturing. Lower-tech
    civilizations need richer systems; advanced civs can use metal-poor stars.

    Args:
        kardashev_level: Civilization's Kardashev scale
        threshold_k085: Metallicity threshold for K=0.85-0.95 (default: -0.3)
        threshold_k095: Metallicity threshold for K=0.95-1.20 (default: -0.5)
        threshold_k120: Metallicity threshold for K>1.20 (default: -1.0)

    Returns:
        Minimum [Fe/H] metallicity (solar = 0.0, metal-poor < -1.0)

    Physical basis:
        - Need metals for: structures, electronics, propulsion, energy systems
        - Found in: asteroids, planetary cores, gas giant atmospheres
        - Metal-poor stars ([Fe/H] < -1.0) have few rocky bodies
        - Solar metallicity ([Fe/H] = 0.0) has abundant resources

        K=0.85-0.95: Need metal-rich systems (default: [Fe/H] > -0.3)
            - Limited refining/processing capability
            - Require abundant, easily accessible metals

        K=0.95-1.20: Can use solar-metallicity systems (default: [Fe/H] > -0.5)
            - Better resource extraction technology
            - More efficient manufacturing

        K>1.20: Can utilize metal-poor systems (default: [Fe/H] > -1.0)
            - Advanced transmutation or matter replication
            - Can extract trace metals efficiently
    """
    if kardashev_level < 0.85:
        return float('inf')  # Cannot replicate
    elif kardashev_level < 0.95:
        return threshold_k085  # Need metal-rich systems
    elif kardashev_level < 1.20:
        return threshold_k095  # Solar-metallicity acceptable
    else:
        return threshold_k120  # Can use metal-poor systems


# Constants
# Speed of light constant (for travel time calculations)
C_PC_YR = 0.306601  # Speed of light in parsecs/year
