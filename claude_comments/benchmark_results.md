# Benchmark Results - War Implementation

**Date**: 2026-02-11 22:41:36

## Configuration

- Stars: 100,000
- Duration: 10.0 Gyr
- Emergence rate: 0.1 per Myr
- Encounter scan: 50.0 Myr
- Snapshot interval: 100.0 Myr

## Performance

- **Total time**: 239.00s
  - Init: 64.02s (26.8%)
  - Run: 174.97s (73.2%)
- **Peak memory**: 761.2 MB

## Simulation Statistics

- Total civilizations: 897
- Active civilizations: 0
- Extinct civilizations: 897
- Total colonized systems: 35929
- Snapshots saved: 102

## Snapshot Statistics

- Total snapshots: 102
- Avg snapshot size: ~10614.9 KB

## Profiling - Top 30 Functions

```
         112226945 function calls (112029443 primitive calls) in 238.949 seconds

   Ordered by: cumulative time
   List reduced from 8129 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.064    0.064  174.973  174.973 engine.py:802(run)
    17768    4.404    0.000  173.391    0.010 engine.py:708(_step)
    17768   65.990    0.004   86.284    0.005 structure.py:1064(evolve_positions_adaptive)
    17768    0.166    0.000   66.565    0.004 engine.py:1328(_process_probe_events)
    34931    1.772    0.000   64.854    0.002 engine.py:1716(_handle_replication_complete)
        1    0.002    0.002   64.024   64.024 engine.py:405(initialize)
    31380    4.514    0.000   63.077    0.002 engine.py:1840(_launch_offspring_probes)
        1    0.001    0.001   60.146   60.146 structure.py:98(generate_stellar_population)
        1    0.001    0.001   59.290   59.290 structure.py:351(_generate_velocities)
        1    2.216    2.216   59.289   59.289 structure.py:482(_generate_velocities_simple)
   646021   43.973    0.000   44.604    0.000 _shape_base_impl.py:628(column_stack)
    31480   39.320    0.001   41.054    0.001 engine.py:1890(_find_nearest_targets)
   148258    0.215    0.000   40.917    0.000 structure.py:55(positions)
   160001    0.491    0.000   32.220    0.000 structure.py:310(_compute_circular_velocity)
   160001    0.356    0.000   31.679    0.000 structure.py:825(_compute_gravitational_acceleration)
   160001    0.580    0.000   27.553    0.000 structure.py:665(_compute_disk_acceleration)
  1280008    1.210    0.000   26.156    0.000 necompiler.py:915(evaluate)
  1280008    4.354    0.000   16.253    0.000 necompiler.py:797(validate)
        1    0.133    0.133   15.703   15.703 structure.py:445(_compute_asymmetric_drift)
    36403    0.910    0.000   10.045    0.000 engine.py:1736(_calculate_intercept_position)
    35515    0.807    0.000    8.725    0.000 structure.py:1048(_compute_accel_numba)
  1280008    2.913    0.000    8.692    0.000 necompiler.py:993(re_evaluate)
   154889    1.943    0.000    7.829    0.000 _linalg.py:2623(norm)
    35515    7.775    0.000    7.775    0.000 numba_kernels.py:1362(compute_total_acceleration_kernel)
  2560016    5.091    0.000    6.772    0.000 necompiler.py:754(getArguments)
   112696    6.430    0.000    6.430    0.000 {method 'reduce' of 'numpy.ufunc' objects}
    17294    4.872    0.000    6.318    0.000 engine.py:3166(_update_colony_strengths)
    17294    0.089    0.000    4.516    0.000 engine.py:1139(_evolve_civilizations)
    17294    0.104    0.000    3.003    0.000 engine.py:2712(_scan_for_encounters)
        1    2.375    2.375    2.598    2.598 star_formation.py:212(sample)


```
