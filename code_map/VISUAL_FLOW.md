# Great Silence - Visual Simulation Flow

ASCII diagrams and visual representations of the simulation architecture.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GREAT SILENCE SIMULATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   CONFIG     │    │    GALAXY    │    │ CIVILIZATION │                   │
│  │  parameters  │───▶│   structure  │───▶│  emergence   │                   │
│  │              │    │  star_form   │    │  expansion   │                   │
│  └──────────────┘    └──────────────┘    │  extinction  │                   │
│         │                   │            │  personality │                   │
│         │                   │            │     war      │                   │
│         ▼                   ▼            └──────────────┘                   │
│  ┌──────────────────────────────────────────────┐     │                     │
│  │           SIMULATION ENGINE                   │◀────┘                     │
│  │  ┌────────────────────────────────────────┐  │                           │
│  │  │         GalaxySimulation               │  │                           │
│  │  │  • initialize()                        │  │                           │
│  │  │  • run() ─────────────────────────────▶│──┼───▶ SNAPSHOTS            │
│  │  │  • _step()                             │  │                           │
│  │  └────────────────────────────────────────┘  │                           │
│  └──────────────────────────────────────────────┘                           │
│         │              │              │                                      │
│         ▼              ▼              ▼                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                         │
│  │ ASTROPHYSICS │ │  DISASTERS   │ │    UTILS     │                         │
│  │   hazards    │ │  scheduler   │ │   spatial    │                         │
│  │  supernovae  │ │  recovery    │ │  parallel    │                         │
│  │     grb      │ │  archiver    │ │   numba      │                         │
│  └──────────────┘ └──────────────┘ └──────────────┘                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            VISUALIZATION                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ matplotlib  │  │   plotly    │  │  three.js   │  │  timeline   │        │
│  │  2D/3D      │  │ interactive │  │   WebGL     │  │  animation  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Initialization Sequence

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         INITIALIZATION FLOW                                ║
╚═══════════════════════════════════════════════════════════════════════════╝

     ┌─────────────────┐
     │ SimulationConfig│
     │   (YAML/preset) │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │ GalaxySimulation│
     │   __init__()    │
     └────────┬────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GalaxyModel.generate_stellar_population()         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │  │
│  │   │  _generate   │    │  _generate   │    │   _apply     │   │  │
│  │   │   _bulge()   │    │   _disk()    │    │ _spiral_arms │   │  │
│  │   │  Hernquist   │    │ Exponential  │    │ Density Wave │   │  │
│  │   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   │  │
│  │          │                   │                   │           │  │
│  │          └───────────────────┼───────────────────┘           │  │
│  │                              ▼                               │  │
│  │                    ┌─────────────────┐                       │  │
│  │                    │ 3D Positions    │                       │  │
│  │                    │ (N_stars × 3)   │                       │  │
│  │                    └────────┬────────┘                       │  │
│  │                             │                                │  │
│  │   ┌─────────────────────────┼─────────────────────────┐     │  │
│  │   │                         │                         │     │  │
│  │   ▼                         ▼                         ▼     │  │
│  │ ┌──────────────┐   ┌──────────────┐   ┌──────────────┐     │  │
│  │ │  Velocities  │   │    Ages      │   │   Masses     │     │  │
│  │ │ (rotation    │   │ (gradient    │   │  (IMF:       │     │  │
│  │ │  curve)      │   │  inside-out) │   │   Kroupa)    │     │  │
│  │ └──────────────┘   └──────────────┘   └──────────────┘     │  │
│  │                             │                               │  │
│  │                             ▼                               │  │
│  │                    ┌─────────────────┐                      │  │
│  │                    │  Metallicities  │                      │  │
│  │                    │ (radial grad)   │                      │  │
│  │                    └────────┬────────┘                      │  │
│  │                             │                               │  │
│  └─────────────────────────────┼───────────────────────────────┘  │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────┐
                    │  Filter Habitable   │
                    │   0.5 < M < 1.5 M☉  │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
    │ SpatialIndex    │ │  Supernova  │ │ ExtinctionModel │
    │   (KD-tree)     │ │  Scheduler  │ │ (crisis peaks)  │
    └─────────────────┘ └─────────────┘ └─────────────────┘
              │                │                │
              └────────────────┴────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   READY TO RUN      │
                    └─────────────────────┘
```

---

## Main Simulation Loop

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         MAIN SIMULATION LOOP                               ║
╚═══════════════════════════════════════════════════════════════════════════╝

                         ┌─────────────────┐
                         │   sim.run()     │
                         └────────┬────────┘
                                  │
                                  ▼
              ┌───────────────────────────────────────┐
              │   while current_time < duration_myr   │◀─────────────────┐
              └───────────────────┬───────────────────┘                  │
                                  │                                      │
                                  ▼                                      │
                    ┌─────────────────────────┐                          │
                    │ _compute_next_timestep()│                          │
                    │                         │                          │
                    │  No probes → 10 Myr     │                          │
                    │  Probes    → 100 kyr    │                          │
                    │  Events    → 10 kyr     │                          │
                    └────────────┬────────────┘                          │
                                 │                                       │
                                 ▼                                       │
┌────────────────────────────────────────────────────────────────────┐   │
│                        _step(dt_myr)                               │   │
│  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │                                                              │  │   │
│  │  ┌─────────────┐                                             │  │   │
│  │  │1. POSITIONS │  galaxy.evolve_positions(dt_myr)            │  │   │
│  │  │  (optional) │  [Leapfrog integrator]                      │  │   │
│  │  └──────┬──────┘                                             │  │   │
│  │         │                                                    │  │   │
│  │         ▼                                                    │  │   │
│  │  ┌─────────────┐                                             │  │   │
│  │  │2. EMERGENCE │  _check_civilization_emergence()            │  │   │
│  │  │             │  [Drake equation × dt_myr]                  │  │   │
│  │  └──────┬──────┘                                             │  │   │
│  │         │                                                    │  │   │
│  │         ▼                                                    │  │   │
│  │  ┌─────────────┐                                             │  │   │
│  │  │3. EVOLUTION │  _evolve_civilizations()                    │  │   │
│  │  │             │  [Kardashev, extinction, expansion]         │  │   │
│  │  └──────┬──────┘                                             │  │   │
│  │         │                                                    │  │   │
│  │         ▼                                                    │  │   │
│  │  ┌─────────────┐                                             │  │   │
│  │  │4. PROBES    │  _process_probe_events()                    │  │   │
│  │  │             │  [Event queue: arrivals, replications]      │  │   │
│  │  └──────┬──────┘                                             │  │   │
│  │         │                                                    │  │   │
│  │         ▼                                                    │  │   │
│  │  ┌─────────────┐                                             │  │   │
│  │  │5. ENCOUNTERS│  _scan_for_encounters() [if enabled]        │  │   │
│  │  │             │  _resolve_wars()                            │  │   │
│  │  └──────┬──────┘                                             │  │   │
│  │         │                                                    │  │   │
│  │         ▼                                                    │  │   │
│  │  ┌─────────────┐                                             │  │   │
│  │  │6. HAZARDS   │  _apply_hazards()                           │  │   │
│  │  │             │  [Supernovae, GRBs]                         │  │   │
│  │  └──────┬──────┘                                             │  │   │
│  │         │                                                    │  │   │
│  │         ▼                                                    │  │   │
│  │  ┌─────────────┐                                             │  │   │
│  │  │7. SNAPSHOT  │  _save_snapshot() [periodic]                │  │   │
│  │  └─────────────┘                                             │  │   │
│  │                                                              │  │   │
│  └──────────────────────────────────────────────────────────────┘  │   │
└────────────────────────────────────────────────────────────────────┘   │
                                 │                                       │
                                 ▼                                       │
                    ┌─────────────────────────┐                          │
                    │  current_time += dt_myr │──────────────────────────┘
                    └─────────────────────────┘
                                 │
                                 ▼ (when complete)
                    ┌─────────────────────────┐
                    │   get_statistics()      │
                    └─────────────────────────┘
```

---

## Civilization Lifecycle State Machine

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                     CIVILIZATION STATE MACHINE                             ║
╚═══════════════════════════════════════════════════════════════════════════╝

                              ┌─────────────┐
                              │  HABITABLE  │
                              │    STAR     │
                              └──────┬──────┘
                                     │
                       Drake equation│× dt_myr
                        p ≈ 10⁻¹⁰/Myr│
                                     ▼
                              ┌─────────────┐
                        ┌─────│   EMERGED   │─────┐
                        │     │   K = 0.7   │     │
                        │     └──────┬──────┘     │
                        │            │            │
              ┌─────────┴────┐       │      ┌─────┴─────────┐
              │ SELF-DESTRUCT│       │      │ AGE EXTINCTION│
              │              │       │      │               │
              │ Crisis peaks:│       │      │ Exponential   │
              │ • K=0.72 ⚛   │       │      │ decay after   │
              │ • K=0.85 🌐   │       │      │ ~100 Myr      │
              │ • K=1.2  🤖   │       │      │               │
              │ • K=1.8  ⚡   │       │      └───────────────┘
              │ • K=2.5  💫   │       │               │
              └──────────────┘       │               │
                        │            │               │
                        │            ▼               │
                        │     ┌─────────────┐       │
                        │     │   GROWING   │       │
                        │     │ 0.7 < K < 3 │       │
                        │     └──────┬──────┘       │
                        │            │              │
                        │      K ≥ 0.85            │
                        │            │              │
                        │            ▼              │
                        │     ┌─────────────┐       │
                        │     │  EXPANDING  │       │
                        │     │ Probe launch│       │
                        │     └──────┬──────┘       │
                        │            │              │
                        │            ▼              │
                        │   ┌───────────────┐       │
                        │   │   COLONIES    │       │
                        │   │  (N systems)  │       │
                        │   └───────┬───────┘       │
                        │           │               │
                        │   Distributed             │
                        │   Resilience:             │
                        │   p_death = p^N           │
                        │           │               │
                        └─────┬─────┴───────────────┘
                              │
                              ▼
                       ┌─────────────┐
                       │   EXTINCT   │
                       │  (inactive) │
                       └─────────────┘


             ┌─────────────────────────────────────┐
             │        KARDASHEV PROGRESSION        │
             │                                     │
             │  0.7 ──────────────────────▶ 3.0   │
             │   │                           │     │
             │   │  Nuclear    Planetary     │     │
             │   │    Age    Unification     │     │
             │   ▼     ▼          ▼          │     │
             │  ═╪═════╪══════════╪══════════╪═    │
             │   │     │          │          │     │
             │  0.7   0.72       0.85       1.2    │
             │                                     │
             │  Hazard Rate (crisis peaks):        │
             │                                     │
             │         ∧                           │
             │        /│\     /\                   │
             │       / │ \   /  \   /\             │
             │  ────/──┼──\─/────\─/──\────────    │
             │     0.72   0.85   1.2   1.8         │
             │                                     │
             └─────────────────────────────────────┘
```

---

## Probe Expansion System

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         PROBE EXPANSION FLOW                               ║
╚═══════════════════════════════════════════════════════════════════════════╝

                    ┌─────────────────────────┐
                    │   Kardashev ≥ 0.85      │
                    │   Expansion Threshold   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   LOCK PROBE PARAMS     │
                    │   • velocity_c          │
                    │   • per_hop_range_pc    │
                    │   • offspring_count     │
                    │   • replication_delay   │
                    │   • min_metallicity     │
                    └────────────┬────────────┘
                                 │
                                 ▼
         ┌───────────────────────────────────────────────┐
         │              _launch_initial_probes()          │
         │                                               │
         │  ┌─────────┐                                  │
         │  │ HOME ★  │◀─── Civilization Home World     │
         │  └────┬────┘                                  │
         │       │                                       │
         │       │  Find targets within range:           │
         │       │  • Habitable (0.5-1.5 M☉)            │
         │       │  • Metal-rich (> threshold)          │
         │       │  • Not colonized                     │
         │       │                                       │
         │       ├──────────▶ ○ Target 1                │
         │       ├──────────▶ ○ Target 2                │
         │       └──────────▶ ○ Target 3                │
         │                                               │
         │  Schedule arrival events in event_queue       │
         └───────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         EVENT QUEUE (Min-Heap)                            │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ (time=10.5, ARRIVAL, civ_0, probe_1)                               │  │
│  │ (time=12.3, ARRIVAL, civ_0, probe_2)                               │  │
│  │ (time=15.1, REPLICATION, civ_0, probe_0)                           │  │
│  │ (time=18.7, ARRIVAL, civ_0, probe_3)                               │  │
│  │ ...                                                                │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  O(log N) pop/push operations                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
          ┌──────────────────────┴──────────────────────┐
          │                                             │
          ▼                                             ▼
┌─────────────────────────┐               ┌─────────────────────────┐
│   _handle_probe_arrival │               │ _handle_replication     │
│                         │               │   _complete             │
│  • Mark star colonized  │               │                         │
│  • Update colony_times  │               │  • Find new targets     │
│  • Schedule replication │               │  • Launch offspring     │
│  • Archive probe        │               │  • Schedule arrivals    │
└─────────────────────────┘               └─────────────────────────┘


                    EXPANSION WAVEFRONT (Top View)
                    ==============================

                    Generation 0 (initial)
                              ★
                             /│\
                            / │ \
                           /  │  \
                          ○   ○   ○   Generation 1
                         /│\  │  /│\
                        ○ ○ ○ ○ ○ ○ ○  Generation 2
                       /│\│\│\│\│\│\│\
                      ○○○○○○○○○○○○○○○○  Generation 3
                             ...

                    ★ = Home world
                    ○ = Colony
```

---

## War System Flow

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                            WAR SYSTEM FLOW                                 ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│                        _scan_for_encounters()                            │
│                                                                         │
│    ┌──────────┐                              ┌──────────┐               │
│    │   CIV A  │     Territory Overlap        │   CIV B  │               │
│    │  ○─○─○   │◀─────────────────────────────│   ○─○─○  │               │
│    │    ╲     │                              │     ╱    │               │
│    │     ○════════════════●═════════════════════○      │               │
│    │         Shared Star ─┘                             │               │
│    └──────────┘                              └──────────┘               │
│                                                                         │
│              Generate EncounterEvent                                    │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │    _handle_encounter()      │
              │                             │
              │  Check personalities:       │
              │  • CIV A: expansionist      │
              │  • CIV B: defensive         │
              └─────────────┬───────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
    ┌─────────────────┐         ┌─────────────────┐
    │  WAR DECLARED   │         │ ALLIANCE FORMED │
    │                 │         │                 │
    │ p_war based on: │         │ Compatible      │
    │ • Personalities │         │ personalities   │
    │ • Tech gap      │         │                 │
    │ • Territory     │         └─────────────────┘
    └────────┬────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          WAR STATE MACHINE                            │
│                                                                       │
│    ┌────────────┐     ┌────────────┐     ┌────────────┐              │
│    │MOBILIZATION│────▶│ OFFENSIVE  │────▶│ STALEMATE  │              │
│    └────────────┘     └─────┬──────┘     └─────┬──────┘              │
│          │                  │                  │                      │
│          │                  ▼                  │                      │
│          │          ┌──────────────┐           │                      │
│          │          │   BATTLES    │◀──────────┘                      │
│          │          └──────┬───────┘                                  │
│          │                 │                                          │
│          │    ┌────────────┴────────────┐                             │
│          │    │                         │                             │
│          │    ▼                         ▼                             │
│          │  ┌───────────┐         ┌───────────┐                       │
│          │  │ ATTACKER  │         │ DEFENDER  │                       │
│          │  │   WINS    │         │   WINS    │                       │
│          │  └─────┬─────┘         └─────┬─────┘                       │
│          │        │                     │                             │
│          │        └──────────┬──────────┘                             │
│          │                   │                                        │
│          │                   ▼                                        │
│          │    ┌──────────────────────────┐                            │
│          │    │    War Exhaustion ++     │                            │
│          │    └────────────┬─────────────┘                            │
│          │                 │                                          │
│          │                 ▼                                          │
│          │    ┌──────────────────────────┐                            │
│          └───▶│  PEACE NEGOTIATIONS      │                            │
│               └────────────┬─────────────┘                            │
│                            │                                          │
│                            ▼                                          │
│               ┌──────────────────────────┐                            │
│               │       CONCLUDED          │                            │
│               │   • Territory transfer   │                            │
│               │   • Personality evolve   │                            │
│               │   • Vassalization?       │                            │
│               └──────────────────────────┘                            │
└──────────────────────────────────────────────────────────────────────┘


              LIGHT CONE COMMUNICATION CONSTRAINT
              ====================================

              t=0: War declared at position A
                            │
                            │  Message travels at c
                            │  d_pc / 0.306 pc/yr = delay_yr
                            │
                            ▼
              t=Δt: Ally at position B learns of war

                     A ──────────────── B
                    War              Ally
                  starts            can join
                                   after Δt

              is_communication_possible():
                arrival_time = send_time + distance/c
                return arrival_time <= current_time
```

---

## Hazard Application

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                          HAZARD APPLICATION                                ║
╚═══════════════════════════════════════════════════════════════════════════╝

                         _apply_hazards()
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
    ┌─────────────────────┐         ┌─────────────────────┐
    │     SUPERNOVA       │         │        GRB          │
    │                     │         │                     │
    │  Query scheduler    │         │  Stochastic event   │
    │  for SN in window   │         │  metallicity-dep    │
    └──────────┬──────────┘         └──────────┬──────────┘
               │                               │
               ▼                               ▼
    ┌─────────────────────┐         ┌─────────────────────┐
    │    ╳ SUPERNOVA      │         │    ╳ GRB SOURCE     │
    │       ╱│╲           │         │      ╲│╱            │
    │      ╱ │ ╲          │         │    Jet│Axis        │
    │     ╱  │  ╲         │         │       │             │
    │   r=30pc           │         │   θ_beam ≈ 5°       │
    │   (lethal radius)   │         │   (narrow cone)     │
    │                     │         │                     │
    └──────────┬──────────┘         └──────────┬──────────┘
               │                               │
               └─────────────┬─────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │    Check each civilization   │
              │                              │
              │  For each colony:            │
              │    distance = ||pos - SN||   │
              │    if distance < r_lethal:   │
              │      p_destroy = f(distance) │
              │                              │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │   DISTRIBUTED RESILIENCE     │
              │                              │
              │   p_civ_survives =           │
              │     1 - ∏(p_colony_dies)     │
              │                              │
              │   Many colonies = safer      │
              │                              │
              │      Risk                    │
              │       │                      │
              │   1.0 ├──╲     ╱──           │
              │       │   ╲   ╱              │
              │       │    ╲ ╱               │
              │       │     V                │
              │   0.0 ├─────────────         │
              │       └───┬───┬───┬──        │
              │           1  10  100         │
              │         # Colonies           │
              │                              │
              │   U-shaped risk curve        │
              └──────────────────────────────┘
```

---

## Data Structures

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                          KEY DATA STRUCTURES                               ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│                           GalaxyModel                                    │
│                                                                         │
│  positions: np.ndarray (N × 3)   ─────▶  [x, y, z] in kpc              │
│  velocities: np.ndarray (N × 3)  ─────▶  [vx, vy, vz] in km/s          │
│  ages: np.ndarray (N,)           ─────▶  Gyr                           │
│  masses: np.ndarray (N,)         ─────▶  M☉                            │
│  metallicities: np.ndarray (N,)  ─────▶  [Fe/H] dex                    │
│                                                                         │
│  habitable_indices: np.ndarray   ─────▶  indices where 0.5 < M < 1.5   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         CivilizationState                                │
│                                                                         │
│  civ_id: int              ─────▶  Unique identifier                    │
│  birth_time_myr: float    ─────▶  When emerged                         │
│  parent_star_idx: int     ─────▶  Home world star index                │
│  kardashev_scale: float   ─────▶  0.7 → 3.0                            │
│  is_active: bool          ─────▶  Alive or extinct                     │
│                                                                         │
│  colonized_stars: Set[int]            ─────▶  O(1) lookups             │
│  colony_arrival_times: Dict[int,float] ────▶  When each colonized      │
│                                                                         │
│  active_probes: List[ProbeState]      ─────▶  In-flight probes         │
│  archived_probes: List[ProbeState]    ─────▶  Completed probes         │
│                                                                         │
│  personality: PersonalityState        ─────▶  Behavior traits          │
│  active_wars: Dict[int, WarState]     ─────▶  Ongoing conflicts        │
│  alliances: Set[int]                  ─────▶  Allied civ IDs           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                            ProbeState                                    │
│                                                                         │
│  probe_id: int             ─────▶  Unique identifier                   │
│  parent_probe_id: int      ─────▶  For lineage tracking                │
│  generation: int           ─────▶  0, 1, 2, ...                        │
│                                                                         │
│  launch_star_idx: int      ─────▶  Origin star                         │
│  target_star_idx: int      ─────▶  Destination star                    │
│                                                                         │
│  launch_time_myr: float    ─────▶  When departed                       │
│  arrival_time_myr: float   ─────▶  When arrives                        │
│                                                                         │
│  velocity_c: float         ─────▶  Fraction of c (locked)              │
│  per_hop_range_pc: float   ─────▶  Max distance (locked)               │
│  offspring_count: int      ─────▶  Replication count (locked)          │
│  replication_delay_yr: float ───▶  Build time (locked)                 │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     Event Queue (Min-Heap)                               │
│                                                                         │
│  event_queue: List[Tuple[float, str, int, int]]                         │
│                     │      │    │    │                                  │
│                     │      │    │    └─ probe_id                        │
│                     │      │    └────── civ_id                          │
│                     │      └─────────── event_type ('arrival'|'repl')   │
│                     └────────────────── event_time_myr                  │
│                                                                         │
│  Operations:                                                            │
│    heapq.heappush(queue, event)  ─────▶  O(log N)                      │
│    heapq.heappop(queue)          ─────▶  O(log N)                      │
│                                                                         │
│  Replaces O(N) polling with O(log N) event processing                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Spatial Indexing

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                           SPATIAL INDEXING                                 ║
╚═══════════════════════════════════════════════════════════════════════════╝

                    KD-Tree Structure (2D example)
                    ==============================

                              ●(5,4)
                             /     \
                        ●(2,3)    ●(7,2)
                        /    \       \
                   ●(1,1) ●(4,6)    ●(8,7)


                    query_radius(center=(5,4), r=3)
                    ================================

                         ┌───────────────────────┐
                         │         r=3           │
                         │     ┌───────┐         │
                         │     │   ●   │         │
                         │     │ (5,4) │         │
                         │     │  ╱│╲  │         │
                         │     │ ╱ │ ╲ │         │
                         │  ●──┼─●─┼───┼──●      │
                         │     └───────┘         │
                         │         ●             │
                         └───────────────────────┘

                    Returns: indices within radius


            SpatialIndex                      CivilizationSpatialIndex
            ============                      ========================

            • query_radius()                  • add_colony()
            • query_nearest()                 • remove_colony()
            • query_pairs()                   • find_civilizations_in_range()
                                              • find_territory_overlaps()
                                              • find_nearby_enemy_colonies()
                                              • get_frontier_colonies()
                                              • find_path_between_colonies()


            O(log N) vs O(N) comparison for 100k stars:
            ===========================================

            Operation          O(N)         O(log N)
            ─────────────────────────────────────────
            Find nearby       100,000 ops    17 ops
            Per timestep        ~1 sec       ~0.1 ms
            Full simulation     ~hours       ~seconds
```

---

## Parallel Execution

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                     CAUSALITY-PRESERVING PARALLELISM                       ║
╚═══════════════════════════════════════════════════════════════════════════╝

              Step 1: Partition by Light Cone
              ================================

              Time ↑
                   │
              t+Δt ├─────●─────────●─────────●─────
                   │    ╱│╲       ╱│╲       ╱│╲
                   │   ╱ │ ╲     ╱ │ ╲     ╱ │ ╲
                   │  ╱  │  ╲   ╱  │  ╲   ╱  │  ╲
                t  ├─●───┼───●─────┼─────●───┼───●─
                   │ A   │   B     │     C   │   D
                   │     │         │         │
                   └─────┴─────────┴─────────┴─────▶ Space

              Light cones A & B overlap → same group
              Light cones C & D overlap → same group
              Groups {A,B} and {C,D} are independent


              Step 2: Process Groups in Parallel
              ===================================

              ┌─────────────────────────────────────────────┐
              │               Main Thread                   │
              │                                             │
              │   civs = [A, B, C, D, E, F, G, H]           │
              │                     │                       │
              │   groups = find_causal_groups(civs)         │
              │                     │                       │
              │   groups = [{A,B}, {C,D}, {E}, {F,G,H}]     │
              │                     │                       │
              └─────────────────────┼───────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
              ┌──────────┐   ┌──────────┐   ┌──────────┐
              │ Thread 1 │   │ Thread 2 │   │ Thread 3 │
              │          │   │          │   │          │
              │ Process  │   │ Process  │   │ Process  │
              │ {A,B}    │   │ {C,D}    │   │ {E}      │
              │          │   │          │   │ {F,G,H}  │
              │ buffer_1 │   │ buffer_2 │   │ buffer_3 │
              └────┬─────┘   └────┬─────┘   └────┬─────┘
                   │              │              │
                   └──────────────┼──────────────┘
                                  │
                                  ▼
              ┌─────────────────────────────────────────────┐
              │               Main Thread                   │
              │                                             │
              │   _merge_probe_buffers([b1, b2, b3])        │
              │                                             │
              └─────────────────────────────────────────────┘


              ThreadLocalProbeBuffer
              ======================

              ┌─────────────────────────────────────┐
              │  probes_to_create: List[ProbeState] │
              │  events_to_schedule: List[Event]    │
              │  colonies_to_add: Set[int]          │
              └─────────────────────────────────────┘

              • No locks needed (thread-local)
              • Merged after parallel phase
              • 2-4x speedup on multicore
```

---

## Monte Carlo Ensemble

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         MONTE CARLO ENSEMBLE                               ║
╚═══════════════════════════════════════════════════════════════════════════╝

              ┌─────────────────────────────────────────────┐
              │           MonteCarloRunner(config)          │
              │                                             │
              │   n_realizations = 100                      │
              └─────────────────────┬───────────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────────┐
              │              run_parallel()                  │
              │                                             │
              │   ProcessPoolExecutor(max_workers=8)        │
              └─────────────────────┬───────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │           │         │         │          │
              ▼           ▼         ▼         ▼          ▼
        ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ...
        │Process 1│ │Process 2│ │Process 3│ │Process 4│
        │seed=42  │ │seed=43  │ │seed=44  │ │seed=45  │
        │         │ │         │ │         │ │         │
        │ GalaxySim│ │ GalaxySim│ │ GalaxySim│ │ GalaxySim│
        │ .run()  │ │ .run()  │ │ .run()  │ │ .run()  │
        │         │ │         │ │         │ │         │
        │result_1 │ │result_2 │ │result_3 │ │result_4 │
        └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
             │           │           │           │
             └───────────┴─────┬─────┴───────────┘
                               │
                               ▼
              ┌─────────────────────────────────────────────┐
              │              analyze_results()               │
              │                                             │
              │   results = [r1, r2, r3, ..., r100]         │
              │                                             │
              │   Statistics:                               │
              │   ┌─────────────────────────────────────┐   │
              │   │  total_civs:                        │   │
              │   │    mean: 47.3                       │   │
              │   │    std:  12.1                       │   │
              │   │    95% CI: [44.9, 49.7]             │   │
              │   │    percentiles: [25, 42, 54, 71]    │   │
              │   │                                     │   │
              │   │  extinction_rate:                   │   │
              │   │    mean: 0.73                       │   │
              │   │    std:  0.08                       │   │
              │   └─────────────────────────────────────┘   │
              └─────────────────────────────────────────────┘


                    Distribution of Outcomes
                    ========================

                        Total Civilizations
                    ┌─────────────────────────┐
                 30 │       ▄▄▄▄              │
                    │      ██████             │
                 20 │     ████████            │
                    │    ██████████           │
                 10 │   ████████████▄         │
                    │  ██████████████▄▄       │
                  0 └──────────────────────────
                    0   20  40  60  80  100
                        Number of Civilizations
```

---

## Visualization Pipeline

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         VISUALIZATION PIPELINE                             ║
╚═══════════════════════════════════════════════════════════════════════════╝

              Simulation Snapshots
              ════════════════════

              ┌─────────┐   ┌─────────┐   ┌─────────┐
              │ t=0 Myr │──▶│t=10 Myr │──▶│t=20 Myr │──▶ ...
              └────┬────┘   └────┬────┘   └────┬────┘
                   │             │             │
                   ▼             ▼             ▼
              ┌─────────────────────────────────────────────┐
              │            List[SimulationSnapshot]         │
              │                                             │
              │  • time_myr                                 │
              │  • civilization_states                      │
              │  • active_probes_in_flight                  │
              │  • stellar_positions                        │
              │  • colonized_systems                        │
              └─────────────────────┬───────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
     ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
     │   MATPLOTLIB    │  │     PLOTLY      │  │    THREE.JS     │
     │                 │  │                 │  │                 │
     │ GalaxyVisualizer│  │Plotly3DGalaxyViz│  │ HTMLExporter    │
     │                 │  │                 │  │                 │
     │ • 2D plots      │  │ • Interactive   │  │ • WebGL         │
     │ • 3D scatter    │  │ • Rotate/zoom   │  │ • Animation     │
     │ • Density maps  │  │ • Hover info    │  │ • LOD           │
     │ • Hazard zones  │  │ • Time slider   │  │ • Shaders       │
     └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
              │                    │                    │
              ▼                    ▼                    ▼
     ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
     │   galaxy.png    │  │  plotly.html    │  │  viz.html       │
     │   timeline.mp4  │  │                 │  │                 │
     └─────────────────┘  └─────────────────┘  └─────────────────┘


              Three.js Template Pipeline
              ==========================

              ┌─────────────┐
              │ThreeJSConfig│
              └──────┬──────┘
                     │
                     ▼
              ┌─────────────────────┐
              │   data_extractor    │
              │                     │
              │ • Galaxy positions  │
              │ • Frame data        │
              │ • Civ states        │
              │ • Probe positions   │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   Jinja2 Templates  │
              │                     │
              │ • index.html.j2     │
              │ • scene.js.j2       │
              │ • particles.js.j2   │
              │ • animation.js.j2   │
              │ • camera.js.j2      │
              │ • ui.js.j2          │
              │ • layers.js.j2      │
              │ • lod.js.j2         │
              │ • postprocess.js.j2 │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │    html_exporter    │
              │                     │
              │ Render templates    │
              │ Bundle assets       │
              │ Embed data          │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  visualization.html │
              │  (standalone)       │
              └─────────────────────┘
```

---

## Performance Summary

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         PERFORMANCE COMPARISON                             ║
╚═══════════════════════════════════════════════════════════════════════════╝

              100k stars, 10 Gyr simulation
              =============================

              ┌─────────────────────────────────────────────────────────┐
              │                                                         │
              │  Operation          Naive        Optimized    Speedup   │
              │  ─────────────────────────────────────────────────────  │
              │                                                         │
              │  Disk sampling      ~10 sec      ~0.1 sec     100x      │
              │  (Numba JIT)                                            │
              │                                                         │
              │  Probe events       O(N) poll    O(log N)     50x       │
              │  (Event queue)      ~5 sec       ~0.1 sec               │
              │                                                         │
              │  Hazard queries     O(N)         O(log N)     1000x     │
              │  (KD-tree)          ~100 ms      ~0.1 ms                │
              │                                                         │
              │  Civ evolution      Sequential   Parallel     3x        │
              │  (Causality)        ~1 sec       ~0.3 sec               │
              │                                                         │
              │  Memory (probes)    Unbounded    Archived     10x       │
              │  (Archiving)        ~10 GB       ~1 GB                  │
              │                                                         │
              │  Timestep           Fixed 1Myr   Adaptive     5x        │
              │  (10kyr-10Myr)      ~10 min      ~2 min                 │
              │                                                         │
              └─────────────────────────────────────────────────────────┘


              Typical Simulation Profile (10 Gyr, 100k stars)
              ================================================

              ┌────────────────────────────────────────────────────────┐
              │                                                        │
              │  Phase              Time          % Total               │
              │  ──────────────────────────────────────────────────    │
              │                                                        │
              │  Initialization     ~5 sec        5%                   │
              │  ├─ Galaxy gen      ~3 sec                             │
              │  ├─ Spatial index   ~1 sec                             │
              │  └─ SN scheduler    ~1 sec                             │
              │                                                        │
              │  Main loop          ~90 sec       90%                  │
              │  ├─ Emergence       ~10 sec       10%                  │
              │  ├─ Civ evolution   ~30 sec       30%                  │
              │  ├─ Probe events    ~40 sec       40%                  │
              │  └─ Hazards         ~10 sec       10%                  │
              │                                                        │
              │  Snapshots          ~5 sec        5%                   │
              │                                                        │
              │  TOTAL              ~100 sec      100%                 │
              │                                                        │
              └────────────────────────────────────────────────────────┘
```
