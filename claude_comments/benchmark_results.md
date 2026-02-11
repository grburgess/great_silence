# Benchmark Results - War Implementation

**Date**: 2026-02-11 18:58:54

## Configuration

- Stars: 100,000
- Duration: 10.0 Gyr
- Emergence rate: 0.1 per Myr
- Encounter scan: 50.0 Myr
- Snapshot interval: 100.0 Myr

## Performance

- **Total time**: 346.08s
  - Init: 61.08s (17.6%)
  - Run: 285.01s (82.4%)
- **Peak memory**: 806.9 MB

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
         148585613 function calls (148391423 primitive calls) in 346.060 seconds

   Ordered by: cumulative time
   List reduced from 7763 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    30/29    0.069    0.002  516.213   17.800 threading.py:651(wait)
    20778   12.207    0.001  283.504    0.014 engine.py:705(_step)
    20778   94.662    0.005  224.392    0.011 structure.py:1016(evolve_positions_adaptive)
   201528   10.228    0.000  131.329    0.001 structure.py:825(_compute_gravitational_acceleration)
   201528    0.833    0.000   77.855    0.000 structure.py:665(_compute_disk_acceleration)
  1612224    1.750    0.000   70.559    0.000 necompiler.py:915(evaluate)
   777623   66.543    0.000   67.563    0.000 _shape_base_impl.py:628(column_stack)
        1    0.002    0.002   61.076   61.076 engine.py:404(initialize)
        1    0.001    0.001   56.724   56.724 structure.py:98(generate_stellar_population)
        1    0.000    0.000   55.886   55.886 structure.py:351(_generate_velocities)
        1    1.848    1.848   55.886   55.886 structure.py:482(_generate_velocities_simple)
   173036    0.259    0.000   48.861    0.000 structure.py:55(positions)
  1612224   41.767    0.000   48.577    0.000 necompiler.py:993(re_evaluate)
    29/28    0.015    0.001   40.116    1.433 threading.py:337(wait)
    20778    0.080    0.000   36.316    0.002 engine.py:1325(_process_probe_events)
    15129    1.434    0.000   32.474    0.002 engine.py:1719(_handle_replication_complete)
    14807    1.087    0.000   31.038    0.002 engine.py:1843(_launch_offspring_probes)
   160001    0.441    0.000   30.023    0.000 structure.py:310(_compute_circular_velocity)
   201528   16.142    0.000   22.438    0.000 structure.py:726(_compute_bulge_acceleration)
    14925    3.389    0.000   21.147    0.001 engine.py:1893(_find_nearest_targets)
   201528   13.950    0.000   20.812    0.000 structure.py:781(_compute_halo_acceleration)
  1612224    6.398    0.000   20.232    0.000 necompiler.py:797(validate)
    14925    0.334    0.000   16.694    0.001 _arraysetops_impl.py:1060(isin)
    14925    0.737    0.000   16.350    0.001 _arraysetops_impl.py:908(_in1d)
        1    0.122    0.122   14.891   14.891 structure.py:445(_compute_asymmetric_drift)
      2/1    0.005    0.002   14.553   14.553 engine.py:799(run)
    29266    0.330    0.000   10.813    0.000 _arraysetops_impl.py:145(unique)
    29266    0.215    0.000   10.467    0.000 _arraysetops_impl.py:348(_unique1d)
    81952    1.870    0.000    9.187    0.000 _linalg.py:2623(norm)
   122012    8.034    0.000    8.034    0.000 {method 'reduce' of 'numpy.ufunc' objects}


```
