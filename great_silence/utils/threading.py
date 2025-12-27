"""
Threading configuration utilities for optimal performance on M1 Max.

Handles the complex interaction between NumPy BLAS, Numba OpenMP, and
system threads to avoid oversubscription and maximize performance.
"""

import os
import warnings


def configure_m1_max_threading(
    numba_threads: int = 8,
    numpy_threads: int = 1,
    suppress_omp_warnings: bool = True
) -> None:
    """
    Configure threading for optimal M1 Max performance.

    The M1 Max has 8 performance cores + 2 efficiency cores. For scientific
    computing, we want to:
    1. Use Numba's parallelism (8 threads on P-cores)
    2. Disable NumPy's BLAS parallelism (avoid nested parallelism)
    3. Suppress deprecated OpenMP warnings

    Args:
        numba_threads: Number of threads for Numba (default: 8 for M1 Max P-cores)
        numpy_threads: Number of threads for NumPy BLAS (default: 1 to avoid nesting)
        suppress_omp_warnings: Whether to suppress OpenMP warnings (default: True)

    Example:
        >>> from great_silence.utils.threading import configure_m1_max_threading
        >>> configure_m1_max_threading()  # Optimal M1 Max settings
        >>> # Now run your simulation

    Technical Details:
        The M1 Max has:
        - 8 P-cores (performance) @ 3.2 GHz
        - 2 E-cores (efficiency) @ 2.0 GHz

        For compute-heavy workloads like GalaticBot:
        - Use P-cores only (8 threads)
        - Avoid E-cores (slower, cause context switching)
        - Disable nested parallelism (NumPy BLAS threads)

        Why NumPy threads = 1?
        - GalaticBot uses Numba for hot loops
        - Numba already parallelizes these loops
        - NumPy BLAS parallelism underneath Numba = oversubscription
        - Oversubscription: 8 Numba threads × 8 BLAS threads = 64 OS threads
        - Result: Thrashing, cache contention, slow!

        Why Numba threads = 8?
        - Matches P-core count
        - Parallelizes position evolution, distance calcs
        - 10-100x speedup on these operations
    """
    # Set Numba threading
    os.environ['NUMBA_NUM_THREADS'] = str(numba_threads)
    os.environ['OMP_NUM_THREADS'] = str(numba_threads)
    os.environ['NUMBA_THREADING_LAYER'] = 'omp'

    # Set NumPy/BLAS threading to 1 (avoid nested parallelism)
    os.environ['OPENBLAS_NUM_THREADS'] = str(numpy_threads)
    os.environ['MKL_NUM_THREADS'] = str(numpy_threads)
    os.environ['VECLIB_MAXIMUM_THREADS'] = str(numpy_threads)  # Apple Accelerate
    os.environ['BLIS_NUM_THREADS'] = str(numpy_threads)

    # Suppress OpenMP warnings about deprecated routines
    if suppress_omp_warnings:
        os.environ['OMP_DISPLAY_ENV'] = 'FALSE'
        # This suppresses the "omp_set_nested deprecated" warning
        # The warning is harmless - NumPy/Numba use old OpenMP API
        # Modern equivalent: omp_set_max_active_levels
        warnings.filterwarnings('ignore', category=UserWarning, module='numba')

    print(f"Threading configured for M1 Max:")
    print(f"  Numba threads: {numba_threads} (parallel Numba loops)")
    print(f"  NumPy/BLAS threads: {numpy_threads} (avoid nested parallelism)")
    print(f"  OpenMP warnings: {'suppressed' if suppress_omp_warnings else 'shown'}")


def configure_custom_threading(
    n_threads: int,
    allow_nested: bool = False,
    suppress_omp_warnings: bool = True
) -> None:
    """
    Configure threading for custom hardware.

    Args:
        n_threads: Total number of threads to use
        allow_nested: Allow nested parallelism (NumPy + Numba)
        suppress_omp_warnings: Suppress OpenMP warnings

    Example:
        >>> # For 16-core AMD workstation
        >>> configure_custom_threading(n_threads=16)

        >>> # For dual-socket server with hyperthreading
        >>> configure_custom_threading(n_threads=64, allow_nested=True)
    """
    if allow_nested:
        # Use nested parallelism (advanced users only)
        # Numba and NumPy both parallel
        os.environ['NUMBA_NUM_THREADS'] = str(n_threads // 2)
        os.environ['OMP_NUM_THREADS'] = str(n_threads // 2)
        os.environ['OPENBLAS_NUM_THREADS'] = str(2)
        os.environ['MKL_NUM_THREADS'] = str(2)
        print(f"Threading configured (nested parallelism):")
        print(f"  Numba threads: {n_threads // 2}")
        print(f"  BLAS threads: 2")
        print(f"  Total potential threads: {n_threads}")
    else:
        # Standard config: Numba parallel, NumPy serial
        configure_m1_max_threading(
            numba_threads=n_threads,
            numpy_threads=1,
            suppress_omp_warnings=suppress_omp_warnings
        )


def get_optimal_thread_count() -> int:
    """
    Detect optimal thread count for current hardware.

    Returns:
        Recommended number of threads

    Example:
        >>> n_threads = get_optimal_thread_count()
        >>> configure_custom_threading(n_threads)
    """
    import multiprocessing

    # Get total CPU count
    cpu_count = multiprocessing.cpu_count()

    # Try to detect M1/M2/M3 Mac
    try:
        import platform
        if platform.system() == 'Darwin' and platform.machine() == 'arm64':
            # Apple Silicon - use P-cores only
            # M1/M2/M3 variants:
            # M1: 8 cores (4P + 4E) or 8 (8P)
            # M1 Pro: 8 (6P + 2E) or 10 (8P + 2E)
            # M1 Max: 10 (8P + 2E)
            # M1 Ultra: 20 (16P + 4E)
            # M2: Similar pattern
            # M3: Similar pattern

            if cpu_count == 8:
                return 4  # M1 base - 4 P-cores
            elif cpu_count == 10:
                return 8  # M1 Pro/Max - 8 P-cores
            elif cpu_count == 12:
                return 8  # M2 Pro - 8 P-cores
            elif cpu_count >= 16:
                return cpu_count - 4  # Ultra/Max - assume 4 E-cores
            else:
                return cpu_count // 2  # Conservative
    except:
        pass

    # Intel/AMD: use all cores (hyperthreading OK for compute)
    return cpu_count


def benchmark_threading(n_trials: int = 5) -> None:
    """
    Benchmark different threading configurations.

    Tests performance with different thread counts to find optimal.

    Args:
        n_trials: Number of trials per configuration

    Example:
        >>> benchmark_threading()
        Testing 1 threads: 2.34s
        Testing 2 threads: 1.18s
        Testing 4 threads: 0.61s
        Testing 8 threads: 0.31s  ← FASTEST
        Optimal: 8 threads
    """
    import time
    import numpy as np

    print("Benchmarking threading configurations...")
    print("(Running NumPy + Numba workload)")
    print()

    # Import numba here so we can reconfigure
    from numba import jit, prange

    @jit(nopython=True, parallel=True)
    def compute_workload(n):
        """Representative Numba parallel workload."""
        result = np.zeros(n)
        for i in prange(n):
            x = 0.0
            for j in range(1000):
                x += np.sin(i * j) * np.cos(i + j)
            result[i] = x
        return result

    results = {}
    thread_counts = [1, 2, 4, 8]

    for n_threads in thread_counts:
        # Reconfigure
        os.environ['NUMBA_NUM_THREADS'] = str(n_threads)
        os.environ['OMP_NUM_THREADS'] = str(n_threads)

        # Clear numba cache
        compute_workload.parallel_diagnostics(level=0)

        # Warmup
        _ = compute_workload(1000)

        # Benchmark
        times = []
        for _ in range(n_trials):
            start = time.time()
            _ = compute_workload(100000)
            times.append(time.time() - start)

        avg_time = np.mean(times)
        results[n_threads] = avg_time
        print(f"  {n_threads} threads: {avg_time:.3f}s")

    # Find optimal
    optimal = min(results, key=results.get)
    print()
    print(f"Optimal: {optimal} threads (fastest)")
    print(f"Speedup vs 1 thread: {results[1] / results[optimal]:.1f}x")
