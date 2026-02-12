# Benchmark Results - War Implementation

**Date**: 2026-02-12 08:02:00

## Configuration

- Stars: 100,000
- Duration: 10.0 Gyr
- Emergence rate: 0.1 per Myr
- Encounter scan: 50.0 Myr
- Snapshot interval: 100.0 Myr

## Performance

- **Total time**: 128.13s
  - Init: 4.70s (3.7%)
  - Run: 123.43s (96.3%)
- **Peak memory**: 783.9 MB

## Simulation Statistics

- Total civilizations: 1053
- Active civilizations: 0
- Extinct civilizations: 1053
- Total colonized systems: 29073
- Snapshots saved: 102

## Snapshot Statistics

- Total snapshots: 102
- Avg snapshot size: ~5121.4 KB

## Profiling - Top 30 Functions

```
         16067896 function calls (15870394 primitive calls) in 128.102 seconds

   Ordered by: cumulative time
   List reduced from 8116 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.056    0.056  123.433  123.433 engine.py:802(run)
    20652    3.441    0.000  121.835    0.006 engine.py:708(_step)
    20652   65.821    0.003   86.160    0.004 structure.py:1065(evolve_positions_adaptive)
    20652    0.075    0.000   22.708    0.001 engine.py:1328(_process_probe_events)
    27679    0.023    0.000   20.871    0.001 engine.py:1716(_handle_replication_complete)
    24185    1.660    0.000   20.847    0.001 engine.py:1840(_launch_offspring_probes)
    24301   18.147    0.001   18.676    0.001 engine.py:1890(_find_nearest_targets)
    41277    0.633    0.000    8.575    0.000 structure.py:1049(_compute_accel_numba)
   134714    1.551    0.000    7.883    0.000 _linalg.py:2623(norm)
    41277    7.827    0.000    7.827    0.000 numba_kernels.py:1362(compute_total_acceleration_kernel)
   108022    6.830    0.000    6.830    0.000 {method 'reduce' of 'numpy.ufunc' objects}
        1    0.001    0.001    4.697    4.697 engine.py:405(initialize)
    20230    0.072    0.000    3.975    0.000 engine.py:1139(_evolve_civilizations)
        1    2.449    2.449    2.671    2.671 star_formation.py:212(sample)
    21065    2.226    0.000    2.263    0.000 _shape_base_impl.py:628(column_stack)
    20230    2.183    0.000    2.183    0.000 engine.py:1151(<listcomp>)
    20230    1.730    0.000    2.003    0.000 engine.py:3166(_update_colony_strengths)
        6    0.000    0.000    1.724    0.287 dispatcher.py:344(_compile_for_args)
    20230    1.094    0.000    1.716    0.000 engine.py:1172(_evolve_civilizations_sequential)
     82/6    0.001    0.000    1.714    0.286 dispatcher.py:862(compile)
     26/5    0.000    0.000    1.707    0.341 dispatcher.py:79(compile)
     26/5    0.000    0.000    1.707    0.341 dispatcher.py:86(_compile_cached)
     26/5    0.001    0.000    1.707    0.341 dispatcher.py:101(_compile_core)
     26/5    0.000    0.000    1.707    0.341 compiler.py:713(compile_extra)
    28020    0.078    0.000    1.684    0.000 engine.py:1377(_handle_probe_arrival)
 1111/388    0.002    0.000    1.565    0.004 compiler_lock.py:32(_acquire_compile_lock)
    28020    1.555    0.000    1.559    0.000 civ_spatial_index.py:105(get_colonizers_at_star)
     27/5    0.000    0.000    1.558    0.312 compiler.py:433(compile_extra)
     27/5    0.000    0.000    1.553    0.311 compiler.py:500(_compile_bytecode)
     27/5    0.000    0.000    1.553    0.311 compiler.py:456(_compile_core)


```
