"""Monte Carlo framework for running multiple simulation realizations."""

import numpy as np
from typing import List, Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

from .engine import GalaxySimulation
from ..config.parameters import SimulationConfig


class MonteCarloRunner:
    """
    Run multiple independent simulation realizations for statistical analysis.
    """

    def __init__(self, config: SimulationConfig):
        """
        Initialize Monte Carlo runner.

        Args:
            config: Base simulation configuration
        """
        self.config = config
        self.results: List[Dict[str, Any]] = []

    def run_single_realization(self, realization_id: int) -> Dict[str, Any]:
        """
        Run a single simulation realization.

        Args:
            realization_id: Unique ID for this realization

        Returns:
            Dictionary with simulation results
        """
        # Create simulation with unique seed
        seed = self.config.simulation.random_seed + realization_id
        sim = GalaxySimulation(self.config, seed=seed)

        # Run simulation
        sim.run(verbose=False)

        # Extract results
        stats = sim.get_statistics()
        stats['realization_id'] = realization_id

        return stats

    def run_parallel(self, n_processes: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Run multiple realizations in parallel.

        Args:
            n_processes: Number of parallel processes (None = auto)

        Returns:
            List of result dictionaries
        """
        n_realizations = self.config.simulation.num_realizations

        print(f"Running {n_realizations} Monte Carlo realizations...")

        with ProcessPoolExecutor(max_workers=n_processes) as executor:
            futures = [
                executor.submit(self.run_single_realization, i)
                for i in range(n_realizations)
            ]

            results = []
            for future in tqdm(as_completed(futures), total=n_realizations):
                results.append(future.result())

        self.results = results
        return results

    def run_sequential(self) -> List[Dict[str, Any]]:
        """
        Run multiple realizations sequentially (for debugging).

        Returns:
            List of result dictionaries
        """
        n_realizations = self.config.simulation.num_realizations

        print(f"Running {n_realizations} Monte Carlo realizations (sequential)...")

        results = []
        for i in tqdm(range(n_realizations)):
            results.append(self.run_single_realization(i))

        self.results = results
        return results

    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyze Monte Carlo results and compute comprehensive statistics.

        Includes mean, std, median, percentiles, and 95% confidence intervals.

        Returns:
            Dictionary with statistical analysis including CI and percentiles
        """
        if not self.results:
            raise ValueError("No results to analyze. Run simulations first.")

        # Extract metrics
        total_civs = np.array([r['total_civilizations'] for r in self.results])
        active_civs = np.array([r['active_civilizations'] for r in self.results])
        extinct_civs = np.array([r['extinct_civilizations'] for r in self.results])

        def compute_statistics(data: np.ndarray, name: str) -> Dict[str, float]:
            """Compute comprehensive statistics with confidence intervals."""
            n = len(data)
            mean = np.mean(data)
            std = np.std(data, ddof=1)  # Unbiased estimator
            sem = std / np.sqrt(n)  # Standard error of mean

            # 95% confidence interval (normal approximation)
            ci_95_lower = mean - 1.96 * sem
            ci_95_upper = mean + 1.96 * sem

            return {
                'mean': float(mean),
                'std': float(std),
                'sem': float(sem),
                'median': float(np.median(data)),
                'min': float(np.min(data)),
                'max': float(np.max(data)),
                'ci_95_lower': float(ci_95_lower),
                'ci_95_upper': float(ci_95_upper),
                'percentile_5': float(np.percentile(data, 5)),
                'percentile_25': float(np.percentile(data, 25)),
                'percentile_75': float(np.percentile(data, 75)),
                'percentile_95': float(np.percentile(data, 95)),
                'coefficient_of_variation': float(std / (mean + 1e-10))
            }

        # Compute extinction rate
        extinction_rate = extinct_civs / np.maximum(total_civs, 1)

        return {
            'n_realizations': len(self.results),
            'total_civilizations': compute_statistics(total_civs, 'total'),
            'active_civilizations': compute_statistics(active_civs, 'active'),
            'extinct_civilizations': compute_statistics(extinct_civs, 'extinct'),
            'extinction_rate': compute_statistics(extinction_rate, 'extinction_rate')
        }
