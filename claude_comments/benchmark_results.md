# Benchmark Results - War Implementation

**Date**: 2026-02-11 21:56:25

## Configuration

- Stars: 100,000
- Duration: 10.0 Gyr
- Emergence rate: 0.1 per Myr
- Encounter scan: 50.0 Myr
- Snapshot interval: 100.0 Myr

## Performance

- **Total time**: 358.84s
  - Init: 64.55s (18.0%)
  - Run: 294.28s (82.0%)
- **Peak memory**: 784.2 MB

## Simulation Statistics

- Total civilizations: 1012
- Active civilizations: 0
- Extinct civilizations: 1012
- Total colonized systems: 16142
- Snapshots saved: 102

## Snapshot Statistics

- Total snapshots: 102
- Avg snapshot size: ~5143.2 KB

## Profiling - Top 30 Functions

```
         148586603 function calls (148392413 primitive calls) in 358.821 seconds

   Ordered by: cumulative time
   List reduced from 7763 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    31/30    0.065    0.002  473.926   15.798 threading.py:651(wait)
    20778   12.906    0.001  292.586    0.014 engine.py:706(_step)
    20778   97.935    0.005  230.901    0.011 structure.py:1016(evolve_positions_adaptive)
   201528   10.695    0.000  134.446    0.001 structure.py:825(_compute_gravitational_acceleration)
    30/29    0.020    0.001   90.164    3.109 threading.py:337(wait)
   201528    0.958    0.000   79.538    0.000 structure.py:665(_compute_disk_acceleration)
  1612224    1.831    0.000   71.815    0.000 necompiler.py:915(evaluate)
   777623   69.320    0.000   70.391    0.000 _shape_base_impl.py:628(column_stack)
        1    0.003    0.003   64.554   64.554 engine.py:405(initialize)
        1    0.000    0.000   60.113   60.113 structure.py:98(generate_stellar_population)
        1    0.000    0.000   59.030   59.030 structure.py:351(_generate_velocities)
        1    2.273    2.273   59.029   59.029 structure.py:482(_generate_velocities_simple)
   173036    0.281    0.000   50.901    0.000 structure.py:55(positions)
  1612224   41.889    0.000   48.799    0.000 necompiler.py:993(re_evaluate)
    20778    0.094    0.000   38.930    0.002 engine.py:1326(_process_probe_events)
    15129    1.639    0.000   33.583    0.002 engine.py:1720(_handle_replication_complete)
    14807    1.111    0.000   31.942    0.002 engine.py:1844(_launch_offspring_probes)
   160001    0.470    0.000   31.074    0.000 structure.py:310(_compute_circular_velocity)
      2/1    0.009    0.004   23.764   23.764 engine.py:800(run)
   201528   16.478    0.000   22.943    0.000 structure.py:726(_compute_bulge_acceleration)
    14925    3.620    0.000   22.251    0.001 engine.py:1894(_find_nearest_targets)
   201528   14.028    0.000   21.274    0.000 structure.py:781(_compute_halo_acceleration)
  1612224    6.716    0.000   21.186    0.000 necompiler.py:797(validate)
    14925    0.473    0.000   17.409    0.001 _arraysetops_impl.py:1060(isin)
    14925    0.799    0.000   16.925    0.001 _arraysetops_impl.py:908(_in1d)
        1    0.129    0.129   15.206   15.206 structure.py:445(_compute_asymmetric_drift)
    29266    0.313    0.000   11.235    0.000 _arraysetops_impl.py:145(unique)
    29266    0.246    0.000   10.906    0.000 _arraysetops_impl.py:348(_unique1d)
    81952    2.148    0.000    9.576    0.000 _linalg.py:2623(norm)
   122012    8.228    0.000    8.228    0.000 {method 'reduce' of 'numpy.ufunc' objects}


```
