# Benchmark Results - War Implementation

**Date**: 2026-02-11 22:50:09

## Configuration

- Stars: 100,000
- Duration: 10.0 Gyr
- Emergence rate: 0.1 per Myr
- Encounter scan: 50.0 Myr
- Snapshot interval: 100.0 Myr

## Performance

- **Total time**: 229.71s
  - Init: 4.91s (2.1%)
  - Run: 224.80s (97.9%)
- **Peak memory**: 785.4 MB

## Simulation Statistics

- Total civilizations: 884
- Active civilizations: 0
- Extinct civilizations: 884
- Total colonized systems: 50751
- Snapshots saved: 102

## Snapshot Statistics

- Total snapshots: 102
- Avg snapshot size: ~11451.9 KB

## Profiling - Top 30 Functions

```
         31841284 function calls (31643786 primitive calls) in 229.636 seconds

   Ordered by: cumulative time
   List reduced from 8130 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.076    0.076  224.796  224.796 engine.py:802(run)
    19056    5.503    0.000  210.441    0.011 engine.py:708(_step)
    19056   73.891    0.004   96.463    0.005 structure.py:1079(evolve_positions_adaptive)
    19056    0.248    0.000   88.680    0.005 engine.py:1328(_process_probe_events)
    49232    2.239    0.000   85.777    0.002 engine.py:1716(_handle_replication_complete)
    41511    5.986    0.000   83.532    0.002 engine.py:1840(_launch_offspring_probes)
    41621   52.165    0.001   54.690    0.001 engine.py:1890(_find_nearest_targets)
   175903   34.908    0.000   35.134    0.000 _shape_base_impl.py:628(column_stack)
   156863    0.203    0.000   32.937    0.000 structure.py:55(positions)
    53216    1.205    0.000   13.524    0.000 engine.py:1736(_calculate_intercept_position)
      102    0.803    0.008   12.798    0.125 engine.py:2562(_save_snapshot)
    38071    0.972    0.000    9.653    0.000 structure.py:1063(_compute_accel_numba)
   215959    2.514    0.000    8.978    0.000 _linalg.py:2623(norm)
    38071    8.516    0.000    8.516    0.000 numba_kernels.py:1362(compute_total_acceleration_kernel)
    18580    6.551    0.000    8.482    0.000 engine.py:3166(_update_colony_strengths)
   136025    7.072    0.000    7.072    0.000 {method 'reduce' of 'numpy.ufunc' objects}
    18580    0.098    0.000    5.082    0.000 engine.py:1139(_evolve_civilizations)
        1    0.002    0.002    4.908    4.908 engine.py:405(initialize)
    18580    0.125    0.000    3.823    0.000 engine.py:2712(_scan_for_encounters)
    30579    3.101    0.000    3.301    0.000 civ_spatial_index.py:145(find_territory_overlaps)
    18580    2.684    0.000    2.684    0.000 engine.py:1151(<listcomp>)
        1    2.426    2.426    2.653    2.653 star_formation.py:212(sample)
    49868    0.167    0.000    2.376    0.000 engine.py:1377(_handle_probe_arrival)
    41621    1.521    0.000    2.344    0.000 spatial.py:25(query_radius)
    18580    1.137    0.000    2.293    0.000 engine.py:1172(_evolve_civilizations_sequential)
    49868    2.103    0.000    2.112    0.000 civ_spatial_index.py:105(get_colonizers_at_star)
        6    0.000    0.000    1.943    0.324 dispatcher.py:344(_compile_for_args)
     82/6    0.001    0.000    1.933    0.322 dispatcher.py:862(compile)
     26/5    0.000    0.000    1.926    0.385 dispatcher.py:79(compile)
     26/5    0.000    0.000    1.926    0.385 dispatcher.py:86(_compile_cached)


```
