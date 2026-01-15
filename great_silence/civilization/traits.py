"""
Civilization traits and characteristics system.

This module defines inherent traits that affect civilization behavior,
crisis survival, and technological advancement.

Traits are assigned at birth based on:
- Random variation (representing cultural/genetic factors)
- Parent star properties (metallicity, age, location)
- Galactic environment (stellar density, hazard exposure)
"""

from dataclasses import dataclass
import numpy as np
from typing import Optional


@dataclass
class CivilizationTraits:
    """
    Inherent characteristics that affect civilization survival and development.

    All traits are normalized to [0.0, 1.0] range where:
    - 0.0 = minimum (worst for survival)
    - 1.0 = maximum (best for survival)

    Attributes:
        political_cohesion: Unity vs fragmentation (0=fragmented, 1=unified)
            Affects crisis response coordination and resource mobilization.

        technological_wisdom: Foresight and caution in tech development (0=reckless, 1=wise)
            Affects ability to anticipate dangers before they become crises.

        risk_tolerance: Attitude toward dangerous technologies (0=cautious, 1=aggressive)
            High risk tolerance → faster advancement but higher crisis probability.
            Low risk tolerance → slower advancement but better crisis navigation.

        resource_abundance: Economic buffer for crisis investment (0=poor, 1=rich)
            Rich civilizations can afford redundancy, multiple approaches, failures.

        adaptability: Speed of learning and behavioral change (0=rigid, 1=flexible)
            Affects how quickly they learn from near-misses and previous crises.

    Example:
        >>> traits = CivilizationTraits(
        ...     political_cohesion=0.8,
        ...     technological_wisdom=0.6,
        ...     risk_tolerance=0.3,
        ...     resource_abundance=0.7,
        ...     adaptability=0.75
        ... )
        >>> modifier = traits.get_crisis_survival_modifier()
        >>> # modifier > 1.0 means better than average survival chance
    """

    political_cohesion: float
    technological_wisdom: float
    risk_tolerance: float
    resource_abundance: float
    adaptability: float

    def __post_init__(self):
        """Validate trait values are in valid range."""
        for trait_name in ['political_cohesion', 'technological_wisdom',
                          'risk_tolerance', 'resource_abundance', 'adaptability']:
            value = getattr(self, trait_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{trait_name} must be in [0.0, 1.0], got {value}")

    def get_crisis_survival_modifier(self) -> float:
        """
        Calculate overall crisis survival probability modifier.

        Returns a multiplicative modifier where:
        - 1.0 = neutral (no modification)
        - > 1.0 = better than average survival chance
        - < 1.0 = worse than average survival chance

        Formula weights:
        - Political cohesion: +30% at max (most important for crisis response)
        - Technological wisdom: +20% at max
        - Resource abundance: +15% at max
        - Adaptability: +15% at max
        - Risk tolerance: -20% at max (high risk is dangerous)

        Returns:
            Survival probability multiplier [0.2, 1.8]
        """
        modifier = 1.0

        # Positive modifiers (higher = better)
        modifier += 0.30 * self.political_cohesion
        modifier += 0.20 * self.technological_wisdom
        modifier += 0.15 * self.resource_abundance
        modifier += 0.15 * self.adaptability

        # Negative modifier (higher risk tolerance = worse survival)
        modifier -= 0.20 * self.risk_tolerance

        return modifier

    def get_advancement_rate_modifier(self) -> float:
        """
        Calculate technological advancement rate modifier.

        High risk tolerance → faster advancement
        High wisdom → slower but safer advancement

        Returns:
            Advancement rate multiplier
        """
        modifier = 1.0

        # Risk-takers advance faster
        modifier += 0.40 * self.risk_tolerance

        # Wise civilizations advance more slowly (being careful)
        modifier -= 0.20 * self.technological_wisdom

        # Resource-rich can invest more in R&D
        modifier += 0.15 * self.resource_abundance

        return max(0.5, modifier)  # Never go below 0.5x speed

    def get_crisis_detection_bonus(self) -> float:
        """
        Calculate probability of detecting/anticipating a crisis early.

        Early detection allows taking preventive measures.

        Returns:
            Detection probability bonus [0.0, 1.0]
        """
        # Wisdom is key for foresight
        detection = 0.5 * self.technological_wisdom

        # Cautious civilizations watch for dangers
        detection += 0.3 * (1.0 - self.risk_tolerance)

        # Resources help fund monitoring systems
        detection += 0.2 * self.resource_abundance

        return min(1.0, detection)

    def evolve_from_experience(self, crisis_survived: bool,
                              crisis_severity: float) -> 'CivilizationTraits':
        """
        Create new traits reflecting learning from crisis experience.

        Surviving crises improves traits (post-traumatic growth).
        Failing crises slightly worsens traits (if civilization survives at all).

        Args:
            crisis_survived: Whether the crisis was overcome
            crisis_severity: How severe the crisis was [0.0, 1.0]

        Returns:
            New CivilizationTraits with updated values
        """
        if crisis_survived:
            # Learn from success - traits improve
            growth_factor = 0.1 * crisis_severity  # Harder crises teach more

            new_cohesion = min(1.0, self.political_cohesion + growth_factor * 0.15)
            new_wisdom = min(1.0, self.technological_wisdom + growth_factor * 0.20)
            new_adaptability = min(1.0, self.adaptability + growth_factor * 0.10)

            # Success slightly increases risk tolerance (overconfidence)
            new_risk = min(1.0, self.risk_tolerance + growth_factor * 0.05)

            new_resources = self.resource_abundance  # Unchanged

        else:
            # Near-miss (survived but barely) - become more cautious
            damage_factor = 0.05 * crisis_severity

            new_cohesion = max(0.0, self.political_cohesion - damage_factor * 0.10)
            new_wisdom = max(0.0, self.technological_wisdom - damage_factor * 0.05)
            new_adaptability = max(0.0, self.adaptability - damage_factor * 0.05)

            # Failure reduces risk tolerance (learned caution)
            new_risk = max(0.0, self.risk_tolerance - damage_factor * 0.15)

            # Crises can deplete resources
            new_resources = max(0.0, self.resource_abundance - damage_factor * 0.10)

        return CivilizationTraits(
            political_cohesion=new_cohesion,
            technological_wisdom=new_wisdom,
            risk_tolerance=new_risk,
            resource_abundance=new_resources,
            adaptability=new_adaptability
        )

    def apply_breakthrough(self, breakthrough_type: str) -> 'CivilizationTraits':
        """
        Apply effects of a breakthrough event.

        Args:
            breakthrough_type: Type of breakthrough

        Returns:
            New CivilizationTraits with breakthrough effects applied
        """
        # Start with current traits
        new_cohesion = self.political_cohesion
        new_wisdom = self.technological_wisdom
        new_risk = self.risk_tolerance
        new_resources = self.resource_abundance
        new_adaptability = self.adaptability

        if breakthrough_type == "unification_movement":
            new_cohesion = min(1.0, self.political_cohesion + 0.30)

        elif breakthrough_type == "scientific_revolution":
            new_wisdom = min(1.0, self.technological_wisdom + 0.20)
            new_adaptability = min(1.0, self.adaptability + 0.10)

        elif breakthrough_type == "philosophical_awakening":
            # Balanced growth across all positive traits
            new_cohesion = min(1.0, self.political_cohesion + 0.15)
            new_wisdom = min(1.0, self.technological_wisdom + 0.15)
            new_adaptability = min(1.0, self.adaptability + 0.15)
            new_risk = max(0.0, self.risk_tolerance - 0.10)  # More cautious

        elif breakthrough_type == "resource_discovery":
            new_resources = min(1.0, self.resource_abundance + 0.50)

        elif breakthrough_type == "social_reform":
            new_cohesion = min(1.0, self.political_cohesion + 0.25)
            new_adaptability = min(1.0, self.adaptability + 0.20)

        elif breakthrough_type == "technological_leap":
            new_wisdom = min(1.0, self.technological_wisdom + 0.15)
            new_resources = min(1.0, self.resource_abundance + 0.15)

        return CivilizationTraits(
            political_cohesion=new_cohesion,
            technological_wisdom=new_wisdom,
            risk_tolerance=new_risk,
            resource_abundance=new_resources,
            adaptability=new_adaptability
        )

    def to_dict(self) -> dict:
        """Convert traits to dictionary for serialization."""
        return {
            'political_cohesion': self.political_cohesion,
            'technological_wisdom': self.technological_wisdom,
            'risk_tolerance': self.risk_tolerance,
            'resource_abundance': self.resource_abundance,
            'adaptability': self.adaptability
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CivilizationTraits':
        """Create traits from dictionary."""
        return cls(
            political_cohesion=data['political_cohesion'],
            technological_wisdom=data['technological_wisdom'],
            risk_tolerance=data['risk_tolerance'],
            resource_abundance=data['resource_abundance'],
            adaptability=data['adaptability']
        )


class TraitGenerator:
    """
    Generator for civilization traits based on environmental factors.

    Traits are influenced by:
    - Parent star metallicity (affects resource abundance)
    - Galactic location (affects risk exposure)
    - Random variation (represents cultural diversity)
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize trait generator.

        Args:
            seed: Random seed for reproducibility
        """
        self.rng = np.random.default_rng(seed)

    def generate_random_traits(self) -> CivilizationTraits:
        """
        Generate completely random traits.

        Uses normal distribution centered at 0.5 with some variance.

        Returns:
            CivilizationTraits with random values
        """
        def sample_trait() -> float:
            """Sample a single trait value from normal distribution."""
            # Normal distribution, mean=0.5, std=0.15
            value = self.rng.normal(0.5, 0.15)
            # Clamp to [0, 1]
            return np.clip(value, 0.0, 1.0)

        return CivilizationTraits(
            political_cohesion=sample_trait(),
            technological_wisdom=sample_trait(),
            risk_tolerance=sample_trait(),
            resource_abundance=sample_trait(),
            adaptability=sample_trait()
        )

    def generate_traits_from_environment(
        self,
        star_metallicity: Optional[float] = None,
        galactic_radius_kpc: Optional[float] = None,
        stellar_density: Optional[float] = None
    ) -> CivilizationTraits:
        """
        Generate traits influenced by environmental factors.

        Args:
            star_metallicity: Metallicity relative to solar (affects resource_abundance)
                Higher metallicity → more heavy elements → more resources
            galactic_radius_kpc: Distance from galactic center
                Inner galaxy → higher density, more hazards → lower risk_tolerance
            stellar_density: Local stellar density (stars per kpc³)
                High density → more interaction → higher cohesion

        Returns:
            CivilizationTraits influenced by environment
        """
        # Start with random baseline
        traits = self.generate_random_traits()

        # Modify based on star metallicity
        if star_metallicity is not None:
            # High metallicity → more resources
            # Typical range: 0.5x solar to 2x solar
            metal_factor = np.clip(star_metallicity, 0.5, 2.0) - 0.5  # [0, 1.5]
            resource_bonus = metal_factor / 1.5 * 0.3  # Up to +0.3
            traits.resource_abundance = np.clip(
                traits.resource_abundance + resource_bonus, 0.0, 1.0
            )

        # Modify based on galactic location
        if galactic_radius_kpc is not None:
            # Inner galaxy (R < 5 kpc) is dangerous
            # Outer galaxy (R > 10 kpc) is safer
            if galactic_radius_kpc < 5.0:
                # Dangerous inner galaxy → lower risk tolerance
                risk_reduction = (5.0 - galactic_radius_kpc) / 5.0 * 0.2  # Up to -0.2
                traits.risk_tolerance = np.clip(
                    traits.risk_tolerance - risk_reduction, 0.0, 1.0
                )
            elif galactic_radius_kpc > 10.0:
                # Safer outer galaxy → might increase risk tolerance
                risk_increase = min(galactic_radius_kpc - 10.0, 5.0) / 5.0 * 0.1
                traits.risk_tolerance = np.clip(
                    traits.risk_tolerance + risk_increase, 0.0, 1.0
                )

        # Modify based on stellar density
        if stellar_density is not None:
            # High density → more potential for interaction and trade
            # This could increase cohesion (shared culture)
            # Density typically ranges from 0.01 to 10 stars/kpc³ in disk
            if stellar_density > 1.0:
                cohesion_bonus = min(np.log10(stellar_density), 1.0) * 0.15
                traits.political_cohesion = np.clip(
                    traits.political_cohesion + cohesion_bonus, 0.0, 1.0
                )

        return traits

    def generate_correlated_traits(
        self,
        base_trait: str,
        base_value: float,
        correlation: float = 0.5
    ) -> CivilizationTraits:
        """
        Generate traits with correlation to a base trait.

        Useful for creating civilizations with consistent "personalities":
        - High cohesion → likely high wisdom (stable societies)
        - High risk tolerance → likely low wisdom (aggressive cultures)

        Args:
            base_trait: Name of trait to base others on
            base_value: Value of base trait [0, 1]
            correlation: Strength of correlation [0, 1]
                0 = random
                1 = perfect correlation

        Returns:
            CivilizationTraits with correlated values
        """
        traits_dict = {}

        # Define correlations between traits
        correlations = {
            'political_cohesion': {
                'technological_wisdom': 0.6,      # United → careful
                'risk_tolerance': -0.4,            # United → cautious
                'resource_abundance': 0.3,         # United → efficient
                'adaptability': 0.4                # United → coordinated change
            },
            'technological_wisdom': {
                'political_cohesion': 0.6,
                'risk_tolerance': -0.7,            # Wise → cautious
                'resource_abundance': 0.2,
                'adaptability': 0.3
            },
            'risk_tolerance': {
                'political_cohesion': -0.4,
                'technological_wisdom': -0.7,      # Aggressive → reckless
                'resource_abundance': -0.2,        # Risk-takers waste resources
                'adaptability': 0.5                # Risk-takers try new things
            },
            'resource_abundance': {
                'political_cohesion': 0.3,
                'technological_wisdom': 0.2,
                'risk_tolerance': -0.2,
                'adaptability': 0.2
            },
            'adaptability': {
                'political_cohesion': 0.4,
                'technological_wisdom': 0.3,
                'risk_tolerance': 0.5,
                'resource_abundance': 0.2
            }
        }

        # Set base trait
        traits_dict[base_trait] = base_value

        # Generate other traits with correlation
        for trait_name in ['political_cohesion', 'technological_wisdom',
                          'risk_tolerance', 'resource_abundance', 'adaptability']:
            if trait_name == base_trait:
                continue

            # Get correlation coefficient
            corr_coef = correlations[base_trait].get(trait_name, 0.0)

            # Apply correlation strength
            effective_corr = corr_coef * correlation

            # Generate correlated value
            # value = base_value * correlation + random * (1 - correlation)
            random_component = self.rng.normal(0.5, 0.15)
            if effective_corr > 0:
                # Positive correlation
                value = base_value * effective_corr + random_component * (1 - abs(effective_corr))
            else:
                # Negative correlation
                value = (1 - base_value) * abs(effective_corr) + random_component * (1 - abs(effective_corr))

            traits_dict[trait_name] = np.clip(value, 0.0, 1.0)

        return CivilizationTraits(**traits_dict)
