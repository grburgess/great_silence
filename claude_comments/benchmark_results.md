# Benchmark Results - War Implementation

**Date**: 2026-02-11 22:29:09

## Configuration

- Stars: 100,000
- Duration: 10.0 Gyr
- Emergence rate: 0.1 per Myr
- Encounter scan: 50.0 Myr
- Snapshot interval: 100.0 Myr

## Performance

- **Total time**: 290.43s
  - Init: 64.31s (22.1%)
  - Run: 226.12s (77.9%)
- **Peak memory**: 767.1 MB

## Simulation Statistics

- Total civilizations: 897
- Active civilizations: 0
- Extinct civilizations: 897
- Total colonized systems: 35929
- Snapshots saved: 102

## Snapshot Statistics

- Total snapshots: 102
- Avg snapshot size: ~10609.3 KB

## Profiling - Top 30 Functions

```
         113712621 function calls (113515123 primitive calls) in 249.875 seconds

   Ordered by: cumulative time
   List reduced from 8149 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.066    0.066  226.115  226.115 engine.py:800(run)
    17768    5.099    0.000  224.506    0.013 engine.py:706(_step)
    17768    0.235    0.000  114.948    0.006 engine.py:1326(_process_probe_events)
    17768   67.391    0.004   87.854    0.005 structure.py:1064(evolve_positions_adaptive)
    34931    2.794    0.000   67.997    0.002 engine.py:1720(_handle_replication_complete)
    31380    2.951    0.000   65.199    0.002 engine.py:1844(_launch_offspring_probes)
        1    0.002    0.002   64.310   64.310 engine.py:405(initialize)
        1    0.001    0.001   60.374   60.374 structure.py:98(generate_stellar_population)
        1    0.000    0.000   59.506   59.506 structure.py:351(_generate_velocities)
        1    2.268    2.268   59.506   59.506 structure.py:482(_generate_velocities_simple)
    35033    2.320    0.000   46.476    0.001 engine.py:1381(_handle_probe_arrival)
   646021   44.905    0.000   45.536    0.000 _shape_base_impl.py:628(column_stack)
    31480   11.891    0.000   43.941    0.001 engine.py:1894(_find_nearest_targets)
   148258    0.180    0.000   41.656    0.000 structure.py:55(positions)
   160001    0.490    0.000   32.388    0.000 structure.py:310(_compute_circular_velocity)
   160001    0.359    0.000   31.847    0.000 structure.py:825(_compute_gravitational_acceleration)
    27921    1.044    0.000   30.276    0.001 _arraysetops_impl.py:1060(isin)
    27921    1.932    0.000   29.210    0.001 _arraysetops_impl.py:908(_in1d)
   160001    0.589    0.000   27.690    0.000 structure.py:665(_compute_disk_acceleration)
  1280008    1.206    0.000   26.299    0.000 necompiler.py:915(evaluate)
    36189    2.091    0.000   22.295    0.001 {method 'remove' of 'list' objects}
  1280008    4.451    0.000   16.337    0.000 necompiler.py:797(validate)
        1    0.134    0.134   15.859   15.859 structure.py:445(_compute_asymmetric_drift)
  7278699   14.480    0.000   14.480    0.000 {built-in method numpy.asarray}
    28412    0.418    0.000   11.870    0.000 _arraysetops_impl.py:145(unique)
    28412    0.228    0.000   11.435    0.000 _arraysetops_impl.py:348(_unique1d)
    36403    0.961    0.000   10.429    0.000 engine.py:1740(_calculate_intercept_position)
  1280008    3.010    0.000    8.756    0.000 necompiler.py:993(re_evaluate)
    35515    0.835    0.000    8.528    0.000 structure.py:1048(_compute_accel_numba)
   154889    2.126    0.000    8.059    0.000 _linalg.py:2623(norm)


```
