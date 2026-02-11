"""
float32 optimization utilities for non-critical paths.

Apple Silicon NEON processes 4×float32 vs 2×float64 per instruction.
Benefits: 2x memory bandwidth, 1.5-2x kernel speed.

SAFE for:
- Visualization positions (30 pc precision at galaxy scale)
- Distance comparisons (sterilization radius checks)
- Velocity evolution (sub-m/s precision)

NOT SAFE for:
- Orbital integration (accumulation errors over 10 Gyr)
- Drake equation probabilities (very small numbers)
- Time advancement (precision loss)
"""

import numpy as np
from typing import Optional


def to_float32_safe(array: np.ndarray, check_precision: bool = True) -> np.ndarray:
    """
    Convert array to float32 with optional precision check.

    Args:
        array: Input array (typically float64)
        check_precision: Warn if conversion loses significant precision

    Returns:
        Array as float32
    """
    if array.dtype == np.float32:
        return array

    array_f32 = array.astype(np.float32)

    if check_precision:
        # Check relative error
        rel_error = np.abs((array_f32 - array) / (array + 1e-30))
        max_rel_error = np.max(rel_error)

        if max_rel_error > 1e-5:  # >0.001% error
            import warnings
            warnings.warn(
                f"float32 conversion has max relative error {max_rel_error:.2e}. "
                f"Consider keeping float64 for this data.",
                UserWarning
            )

    return array_f32


def positions_to_float32(positions: np.ndarray) -> np.ndarray:
    """
    Convert positions to float32 for visualization.

    float32 precision: ~1e-7 relative
    At galaxy scale (10 kpc): ~1 m absolute precision
    At stellar distances (1 pc): ~0.0003 m precision
    Both are far beyond visualization requirements.

    Args:
        positions: (N, 3) positions in kpc (float64)

    Returns:
        (N, 3) positions in kpc (float32)
    """
    return positions.astype(np.float32)


def velocities_to_float32(velocities: np.ndarray) -> np.ndarray:
    """
    Convert velocities to float32 for non-critical operations.

    float32 precision sufficient for:
    - Visualization (display velocities)
    - Approximate kinematics
    - Distance checks

    NOT for:
    - Long-term orbital integration (use float64)

    Args:
        velocities: (N, 3) velocities in km/s (float64)

    Returns:
        (N, 3) velocities in km/s (float32)
    """
    return velocities.astype(np.float32)


def distances_to_float32(distances: np.ndarray) -> np.ndarray:
    """
    Convert distances to float32 for comparisons.

    Safe for:
    - Hazard radius checks (lethal range comparisons)
    - Encounter detection (proximity checks)
    - Spatial indexing

    Args:
        distances: Distance array in any unit (float64)

    Returns:
        Distance array in same unit (float32)
    """
    return distances.astype(np.float32)


class Float32Context:
    """
    Context manager for temporary float32 operations.

    Example:
        with Float32Context() as f32:
            positions_f32 = f32.convert(positions)
            distances = compute_distances(positions_f32)
    """

    def __init__(self):
        self.converted_arrays = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clear references
        self.converted_arrays.clear()
        return False

    def convert(self, array: np.ndarray) -> np.ndarray:
        """Convert array to float32 and track it."""
        array_f32 = array.astype(np.float32)
        self.converted_arrays.append(array_f32)
        return array_f32


# Precision analysis
def analyze_float32_precision(values: np.ndarray) -> dict:
    """
    Analyze precision loss from float64 → float32 conversion.

    Args:
        values: Float64 array

    Returns:
        Dictionary with precision statistics
    """
    values_f32 = values.astype(np.float32).astype(np.float64)

    abs_error = np.abs(values - values_f32)
    rel_error = abs_error / (np.abs(values) + 1e-30)

    return {
        'max_abs_error': np.max(abs_error),
        'mean_abs_error': np.mean(abs_error),
        'max_rel_error': np.max(rel_error),
        'mean_rel_error': np.mean(rel_error),
        'max_rel_error_pct': np.max(rel_error) * 100,
        'acceptable': np.max(rel_error) < 1e-5  # <0.001%
    }


# GPU-friendly dtype selection
def select_dtype_for_kernel(
    operation: str,
    precision_critical: bool = False
) -> np.dtype:
    """
    Select appropriate dtype for kernel operations.

    Args:
        operation: Operation type ('orbital', 'viz', 'distance', 'probability')
        precision_critical: Whether operation requires high precision

    Returns:
        Recommended numpy dtype
    """
    if precision_critical:
        return np.float64

    # Operation-specific recommendations
    recommendations = {
        'orbital': np.float64,  # Accumulation errors
        'probability': np.float64,  # Very small numbers
        'time': np.float64,  # Precision loss
        'viz': np.float32,  # Display only
        'distance': np.float32,  # Comparisons ok
        'velocity_display': np.float32,  # Non-integrating
        'mass': np.float32,  # Lookups ok
        'age': np.float32,  # Comparisons ok
    }

    return recommendations.get(operation, np.float64)


# Memory usage analysis
def estimate_memory_savings(
    num_arrays: int,
    array_size: int,
    elements_per_array: int = 3
) -> dict:
    """
    Estimate memory savings from float32 conversion.

    Args:
        num_arrays: Number of arrays to convert
        array_size: Number of elements per array (e.g., num_stars)
        elements_per_array: Elements per item (e.g., 3 for positions)

    Returns:
        Dictionary with memory estimates
    """
    bytes_per_element_f64 = 8
    bytes_per_element_f32 = 4

    total_elements = num_arrays * array_size * elements_per_array

    memory_f64_mb = (total_elements * bytes_per_element_f64) / (1024 ** 2)
    memory_f32_mb = (total_elements * bytes_per_element_f32) / (1024 ** 2)
    savings_mb = memory_f64_mb - memory_f32_mb

    return {
        'float64_memory_mb': memory_f64_mb,
        'float32_memory_mb': memory_f32_mb,
        'savings_mb': savings_mb,
        'savings_pct': (savings_mb / memory_f64_mb) * 100
    }
