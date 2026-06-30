# Performance + Visual Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tiered stellar-orbit engine (fast analytic epicyclic default + exact MLX-GPU toggle), make probe intercepts analytic, rebuild the Three.js galaxy viz on WebGPU, and polish the NiceGUI app — without breaking existing physics or tests.

**Architecture:** The potential is fixed, time-constant, and axisymmetric, so each orbit is independent and characterizable once via epicyclic theory. A new `EpicyclicOrbitModel` produces closed-form `positions_at_time(t)`. That single primitive feeds analytic intercepts, GPU-shader star positions, and faster snapshots. The exact leapfrog path stays as a high-fidelity toggle, optionally MLX-accelerated.

**Tech Stack:** Python 3.12, NumPy, Numba (`@njit cache=True`), SciPy cKDTree, MLX (optional, Apple GPU), pytest; Three.js WebGPURenderer + TSL (frontend), NiceGUI (webapp), Playwright MCP (smoke tests).

## Global Constraints

- Run all Python via `micromamba run -n galaticbot`.
- Run tests with `micromamba run -n galaticbot python -m pytest <path> -v --override-ini="addopts="`.
- Units: positions kpc; velocities stored km/s, convert to kpc/Myr with factor `0.001022`; time Myr in-engine.
- Numba kernels: `@njit(cache=True)`; add `parallel=True, fastmath=True` only when benchmarked (see project rule: spatial hash was 33× slower than KD-tree despite better O — benchmark every perf claim individually).
- NO COMMENTS in `src/` unless asked; documentation goes in `claude_comments/`.
- Match existing SoA position pattern (`_pos_x/_pos_y/_pos_z` + lazy `_positions_aos`); invalidate the AoS cache on SoA writes.
- Seed all RNG via `np.random.default_rng(seed)`.
- MLX is optional: every GPU path must fall back to the existing Numba path when `mlx` import fails or `orbit_use_gpu` is False.
- Existing tests must stay green. Known pre-existing failures (delta-compression snapshot tests) are out of scope.
- Reproducibility: fast vs exact tier are different models; do not assert bitwise equality between them.

---

## Phase 1 — Fast-tier epicyclic orbit engine

### Task 1: Vectorized epicyclic + vertical frequencies

**Files:**
- Modify: `great_silence/galaxy/structure.py` (add batch frequency helpers near `_compute_epicyclic_frequency:377`)
- Test: `tests/test_orbits.py` (new)

**Interfaces:**
- Consumes: `self._compute_circular_velocities_batch(positions) -> np.ndarray (km/s)` (exists, `structure.py:347`); `self._compute_accel_numba(positions) -> (N,3) kpc/Myr²` (exists, `structure.py:1049`).
- Produces:
  - `GalaxyModel.epicyclic_frequencies_batch(R_kpc: np.ndarray) -> np.ndarray` (κ in 1/Myr)
  - `GalaxyModel.vertical_frequencies_batch(R_kpc: np.ndarray) -> np.ndarray` (ν in 1/Myr)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_orbits.py
import numpy as np
from great_silence.config import SimulationConfig
from great_silence.galaxy.structure import GalaxyModel

def _make_galaxy(n=2000, seed=1):
    cfg = SimulationConfig()
    cfg.galaxy.total_stars = n
    g = GalaxyModel(cfg.galaxy, seed=seed)
    g.generate_stellar_population()
    return g

def test_epicyclic_frequency_batch_matches_scalar():
    g = _make_galaxy()
    R = np.array([2.0, 4.0, 8.0, 12.0])
    kappa_batch = g.epicyclic_frequencies_batch(R)
    kappa_scalar = np.array([g._compute_epicyclic_frequency(r) for r in R])
    assert np.allclose(kappa_batch, kappa_scalar, rtol=0.05)

def test_vertical_frequency_positive_and_decreasing():
    g = _make_galaxy()
    R = np.array([1.0, 4.0, 8.0, 14.0])
    nu = g.vertical_frequencies_batch(R)
    assert np.all(nu > 0)
    assert nu[0] > nu[-1]  # stiffer vertical restoring force near center
```

- [ ] **Step 2: Run, expect FAIL** — `micromamba run -n galaticbot python -m pytest tests/test_orbits.py -v --override-ini="addopts="` → AttributeError: `epicyclic_frequencies_batch`.

- [ ] **Step 3: Implement batch helpers**

```python
# in GalaxyModel, after _compute_epicyclic_frequency
def epicyclic_frequencies_batch(self, R_kpc):
    R = np.maximum(R_kpc, 0.1)
    dr = 0.1
    vc = self._compute_circular_velocities_batch(np.column_stack([R, np.zeros_like(R), np.zeros_like(R)])) * 0.001022
    vc_p = self._compute_circular_velocities_batch(np.column_stack([R + dr, np.zeros_like(R), np.zeros_like(R)])) * 0.001022
    vc_m = self._compute_circular_velocities_batch(np.column_stack([np.maximum(R - dr, 0.1), np.zeros_like(R), np.zeros_like(R)])) * 0.001022
    Omega = vc / R
    dvc_dR = (vc_p - vc_m) / (2 * dr)
    dOmega_dR = (dvc_dR - vc / R) / R
    kappa_sq = R * 2 * Omega * dOmega_dR + 4 * Omega**2
    return np.sqrt(np.maximum(kappa_sq, 0.0))

def vertical_frequencies_batch(self, R_kpc):
    R = np.maximum(R_kpc, 0.1)
    dz = 0.05
    zer = np.zeros_like(R)
    a_plus = self._compute_accel_numba(np.column_stack([R, zer, zer + dz]))[:, 2]
    a_minus = self._compute_accel_numba(np.column_stack([R, zer, zer - dz]))[:, 2]
    d2Phi_dz2 = -(a_plus - a_minus) / (2 * dz)
    return np.sqrt(np.maximum(d2Phi_dz2, 1e-12))
```

- [ ] **Step 4: Run, expect PASS.**

- [ ] **Step 5: Commit** — `git add tests/test_orbits.py great_silence/galaxy/structure.py && git commit -m "feat: batch epicyclic and vertical frequencies"`

---

### Task 2: `EpicyclicOrbitModel` — characterize orbits at init

**Files:**
- Create: `great_silence/galaxy/orbits.py`
- Test: `tests/test_orbits.py` (extend)

**Interfaces:**
- Consumes: `GalaxyModel` (positions kpc, velocities km/s, `epicyclic_frequencies_batch`, `vertical_frequencies_batch`, `_compute_circular_velocities_batch`).
- Produces:
  - `EpicyclicOrbitModel(galaxy: GalaxyModel)` — `.from_galaxy()` computes per-star params: `R_g, Omega_g, kappa, nu, X (radial amp), alpha (radial phase), phi_g0 (guiding azimuth at t=0), Z (vertical amp), beta (vertical phase)` — all shape (N,).
  - `.positions_at_time(t_myr: float) -> np.ndarray (N,3) kpc`
  - `.params_dict() -> dict[str, np.ndarray]` (for GPU/viz export)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_orbits.py (append)
from great_silence.galaxy.orbits import EpicyclicOrbitModel

def test_positions_at_zero_match_initial():
    g = _make_galaxy(n=1500)
    orb = EpicyclicOrbitModel.from_galaxy(g)
    pos0 = orb.positions_at_time(0.0)
    assert np.allclose(pos0, g.positions, atol=0.05)  # < 50 pc reconstruction error

def test_circular_orbit_conserves_radius():
    # A star started on a circular orbit (v_R=0, v_z=0, z=0) keeps |R| ~ constant.
    g = _make_galaxy(n=800)
    g._pos_z[:] = 0.0
    R = np.sqrt(g._pos_x**2 + g._pos_y**2)
    vc = g._compute_circular_velocities_batch(g.positions)
    phi = np.arctan2(g._pos_y, g._pos_x)
    vx = -vc * np.sin(phi); vy = vc * np.cos(phi)
    g.velocities = np.column_stack([vx, vy, np.zeros_like(vx)])
    orb = EpicyclicOrbitModel.from_galaxy(g)
    pos = orb.positions_at_time(200.0)
    R_new = np.sqrt(pos[:, 0]**2 + pos[:, 1]**2)
    assert np.median(np.abs(R_new - R) / R) < 0.05

def test_params_dict_shapes():
    g = _make_galaxy(n=500)
    orb = EpicyclicOrbitModel.from_galaxy(g)
    d = orb.params_dict()
    for k in ["R_g", "Omega_g", "kappa", "nu", "X", "alpha", "phi_g0", "Z", "beta"]:
        assert d[k].shape == (500,)
```

- [ ] **Step 2: Run, expect FAIL** (module missing).

- [ ] **Step 3: Implement `orbits.py`**

```python
import numpy as np

KMS_TO_KPC_MYR = 0.001022

class EpicyclicOrbitModel:
    def __init__(self, R_g, Omega_g, kappa, nu, X, alpha, phi_g0, Z, beta):
        self.R_g, self.Omega_g, self.kappa, self.nu = R_g, Omega_g, kappa, nu
        self.X, self.alpha, self.phi_g0, self.Z, self.beta = X, alpha, phi_g0, Z, beta

    @classmethod
    def from_galaxy(cls, galaxy):
        pos = galaxy.positions
        vel = galaxy.velocities * KMS_TO_KPC_MYR
        x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
        R = np.sqrt(x**2 + y**2)
        R = np.maximum(R, 1e-6)
        phi = np.arctan2(y, x)
        v_R = (vel[:, 0] * x + vel[:, 1] * y) / R
        v_phi = (-vel[:, 0] * y + vel[:, 1] * x) / R
        v_z = vel[:, 2]
        L_z = R * v_phi

        R_g = cls._guiding_radius(galaxy, R, L_z)
        vc_g = galaxy._compute_circular_velocities_batch(
            np.column_stack([R_g, np.zeros_like(R_g), np.zeros_like(R_g)])) * KMS_TO_KPC_MYR
        Omega_g = vc_g / R_g
        kappa = np.maximum(galaxy.epicyclic_frequencies_batch(R_g), 1e-9)
        nu = np.maximum(galaxy.vertical_frequencies_batch(R_g), 1e-9)

        dR = R - R_g
        X = np.sqrt(dR**2 + (v_R / kappa)**2)
        alpha = np.arctan2(-v_R / kappa, dR)
        gamma = 2.0 * Omega_g / (kappa * R_g)   # epicyclic azimuth coupling
        phi_g0 = phi + gamma * X * np.sin(alpha) / R_g
        Z = np.sqrt(z**2 + (v_z / nu)**2)
        beta = np.arctan2(-v_z / nu, z)
        return cls(R_g, Omega_g, kappa, nu, X, alpha, phi_g0, Z, beta)

    @staticmethod
    def _guiding_radius(galaxy, R0, L_z, iters=12):
        Rg = np.maximum(R0.copy(), 0.1)
        for _ in range(iters):
            vc = galaxy._compute_circular_velocities_batch(
                np.column_stack([Rg, np.zeros_like(Rg), np.zeros_like(Rg)])) * KMS_TO_KPC_MYR
            f = Rg * vc - L_z
            dR = 0.05
            vc2 = galaxy._compute_circular_velocities_batch(
                np.column_stack([Rg + dR, np.zeros_like(Rg), np.zeros_like(Rg)])) * KMS_TO_KPC_MYR
            df = ((Rg + dR) * vc2 - L_z - f) / dR
            Rg = np.clip(Rg - f / np.where(np.abs(df) < 1e-9, 1e-9, df), 0.1, 50.0)
        return Rg

    def positions_at_time(self, t_myr):
        ph_R = self.kappa * t_myr + self.alpha
        R = self.R_g + self.X * np.cos(ph_R)
        gamma = 2.0 * self.Omega_g / (self.kappa * self.R_g)
        phi = self.phi_g0 + self.Omega_g * t_myr - gamma * self.X * np.sin(ph_R) / self.R_g
        z = self.Z * np.cos(self.nu * t_myr + self.beta)
        return np.column_stack([R * np.cos(phi), R * np.sin(phi), z])

    def params_dict(self):
        return {"R_g": self.R_g, "Omega_g": self.Omega_g, "kappa": self.kappa,
                "nu": self.nu, "X": self.X, "alpha": self.alpha,
                "phi_g0": self.phi_g0, "Z": self.Z, "beta": self.beta}
```

- [ ] **Step 4: Run, expect PASS.** If `test_positions_at_zero_match_initial` exceeds 50 pc, tighten `_guiding_radius` iters or report the median error — the gate is Task 9, not bitwise.

- [ ] **Step 5: Commit** — `git commit -am "feat: EpicyclicOrbitModel with closed-form positions_at_time"`

---

### Task 3: Numba kernel for `positions_at_time` + config wiring

**Files:**
- Modify: `great_silence/utils/numba_kernels.py` (add `epicyclic_positions_kernel`)
- Modify: `great_silence/galaxy/orbits.py` (use kernel in `positions_at_time`)
- Modify: `great_silence/config/parameters.py` (add `orbit_mode`, `orbit_use_gpu` to `SimulationParameters` near line 272)
- Test: `tests/test_orbits.py` (extend)

**Interfaces:**
- Produces: `epicyclic_positions_kernel(t, R_g, Omega_g, kappa, nu, X, alpha, phi_g0, Z, beta, out)` writes (N,3); config fields `orbit_mode: str = "fast"`, `orbit_use_gpu: bool = False`.

- [ ] **Step 1: Failing test**

```python
def test_kernel_matches_numpy_positions():
    g = _make_galaxy(n=1000)
    orb = EpicyclicOrbitModel.from_galaxy(g)
    ref = orb._positions_numpy(150.0)   # keep numpy version as reference
    fast = orb.positions_at_time(150.0)  # kernel-backed
    assert np.allclose(ref, fast, atol=1e-6)

def test_config_has_orbit_fields():
    from great_silence.config import SimulationConfig
    c = SimulationConfig()
    assert c.simulation.orbit_mode == "fast"
    assert c.simulation.orbit_use_gpu is False
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3:** Rename current numpy body to `_positions_numpy`; add `@njit(cache=True)` `epicyclic_positions_kernel`; make `positions_at_time` call the kernel into a preallocated `self._out` buffer. Add the two config fields with defaults shown above.

- [ ] **Step 4: Run, expect PASS.**

- [ ] **Step 5: Commit** — `git commit -am "feat: numba epicyclic kernel + orbit_mode/orbit_use_gpu config"`

---

### Task 4: Wire fast tier into the simulation engine

**Files:**
- Modify: `great_silence/simulation/engine.py` (initialization + position evolution dispatch)
- Test: `tests/test_orbits.py` (integration)

**Interfaces:**
- Consumes: `config.simulation.orbit_mode`; `EpicyclicOrbitModel`.
- Produces: `engine` builds `self.orbit_model = EpicyclicOrbitModel.from_galaxy(self.galaxy)` at init when `orbit_mode == "fast"`; positions advanced by setting `self.galaxy.positions = self.orbit_model.positions_at_time(self.current_time_myr)` instead of leapfrog stepping.

- [ ] **Step 1: Failing integration test**

```python
def test_fast_mode_runs_and_moves_stars():
    from great_silence import GalaxySimulation, SimulationConfig
    c = SimulationConfig()
    c.galaxy.total_stars = 5000
    c.simulation.simulation_duration_gyr = 1.0
    c.simulation.orbit_mode = "fast"
    sim = GalaxySimulation(c); sim.initialize()
    p0 = sim.galaxy.positions.copy()
    sim.run()
    assert not np.allclose(p0, sim.galaxy.positions)  # stars moved
    assert np.isfinite(sim.galaxy.positions).all()
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3:** In engine init, branch on `orbit_mode`. In the position-advance path (where `evolve_positions_adaptive`/`evolve_positions` is called), when `orbit_mode == "fast"`, set positions directly from `self.orbit_model.positions_at_time(t)`; skip the leapfrog. Keep `orbit_mode == "exact"` on the existing path.

- [ ] **Step 4: Run, expect PASS** plus existing motion tests: `pytest tests/test_stellar_motion.py -v --override-ini="addopts="`.

- [ ] **Step 5: Commit** — `git commit -am "feat: fast epicyclic orbit tier wired into engine"`

---

## Phase 2 — Exact tier MLX-GPU backend

### Task 5: MLX acceleration kernel with Numba fallback

**Files:**
- Create: `great_silence/utils/mlx_backend.py`
- Modify: `great_silence/galaxy/structure.py` (`_compute_accel_numba` dispatch when `orbit_use_gpu`)
- Test: `tests/test_mlx_backend.py` (new, `pytest.importorskip("mlx")`)

**Interfaces:**
- Produces: `mlx_available() -> bool`; `compute_total_acceleration_mlx(positions, params) -> np.ndarray (N,3)` mirroring `compute_total_acceleration_kernel` math (disk Miyamoto-Nagai + bulge Hernquist + isothermal halo).

- [ ] **Step 1: Failing test**

```python
# tests/test_mlx_backend.py
import numpy as np, pytest
mlx = pytest.importorskip("mlx.core")
from great_silence.utils.mlx_backend import compute_total_acceleration_mlx
from great_silence.utils.numba_kernels import compute_total_acceleration_kernel

def test_mlx_matches_numba(galaxy_params):
    pos = np.random.default_rng(0).uniform(-10, 10, (4000, 3))
    out = np.zeros_like(pos)
    compute_total_acceleration_kernel(pos, *galaxy_params, out)
    mlx_out = compute_total_acceleration_mlx(pos, galaxy_params)
    assert np.allclose(out, mlx_out, rtol=1e-4, atol=1e-8)
```

(Define a `galaxy_params` fixture pulling the same potential params the Numba kernel takes — copy them from the existing `_compute_accel_numba` call site at `structure.py:1049`.)

- [ ] **Step 2: Run, expect FAIL/skip** (skips if MLX absent; that is acceptable on CI but the implementer runs it locally where MLX is installed).

- [ ] **Step 3:** Implement `mlx_backend.py` translating the three-potential math to `mlx.core` array ops; `mlx_available()` guards import. In `structure.py`, when `self._orbit_use_gpu and mlx_available()`, route `_compute_accel_numba` through MLX; else existing Numba.

- [ ] **Step 4: Run, expect PASS** locally (MLX installed).

- [ ] **Step 5: Commit** — `git commit -am "feat: MLX Apple-GPU acceleration backend with Numba fallback"`

---

### Task 6: Benchmark fast vs exact-CPU vs exact-GPU

**Files:**
- Modify: `scripts/benchmark_quick.py` (add `--orbit-mode {fast,exact}` and `--gpu` flags; print integrator time)
- Doc: `claude_comments/orbit_engine_benchmark.md` (new)

- [ ] **Step 1:** Add CLI flags; run the same 30k-star / 5 Gyr scenario across `fast`, `exact` (Numba), `exact --gpu` (MLX). Record integrator time + total time.
- [ ] **Step 2:** Write results to `claude_comments/orbit_engine_benchmark.md` with the measured numbers (no placeholders — paste real output).
- [ ] **Step 3: Commit** — `git commit -am "docs: orbit engine benchmark (fast vs exact vs gpu)"`

---

## Phase 3 — Analytic probe intercepts

### Task 7: Closed-form intercept solver against the orbit model

**Files:**
- Modify: `great_silence/simulation/engine.py` (`_calculate_intercept_position:1729`, `_calculate_intercept_positions_batch:1783`)
- Test: `tests/test_intercepts.py` (new)

**Interfaces:**
- Consumes: `self.orbit_model.positions_at_time(t)` (Task 2); `C_PC_YR`.
- Produces: same signatures/returns as today — `(intercept_pos (3,), travel_time_myr)` and batch `((n,3), (n,))`. Behavior change only: when `orbit_mode == "fast"`, solve `|orbit.positions_at_time(t_launch + τ)[idx] − source| = v_probe·τ` by bracketing τ in `[0, τ_max]` and bisection (20 iters). Fall back to the existing linear-extrapolation code when `orbit_model is None` (exact mode) or motion disabled.

- [ ] **Step 1: Failing test**

```python
# tests/test_intercepts.py
import numpy as np
from great_silence import GalaxySimulation, SimulationConfig

def test_intercept_arrives_where_target_is():
    c = SimulationConfig()
    c.galaxy.total_stars = 3000
    c.simulation.orbit_mode = "fast"
    sim = GalaxySimulation(c); sim.initialize()
    src = sim.galaxy.positions[0]
    pos, tt = sim._calculate_intercept_position(src, target_idx=100, velocity_c=0.01)
    actual = sim.orbit_model.positions_at_time(sim.current_time_myr + tt)[100]
    assert np.linalg.norm(pos - actual) < 1e-3   # intercept lands on the true future position
    assert tt > 0
```

- [ ] **Step 2: Run, expect FAIL** (current linear code won't match the curved orbit).
- [ ] **Step 3:** Implement the bracket+bisection solver for the fast path; keep the legacy branch. Vectorize the batch variant over target indices.
- [ ] **Step 4: Run, expect PASS** plus `pytest tests/test_stellar_motion.py -v --override-ini="addopts="`.
- [ ] **Step 5: Commit** — `git commit -am "feat: analytic probe intercepts on epicyclic orbits"`

---

## Phase 4 — WebGPU compute visualization

> Frontend tasks: apply the `frontend-design` skill for visual decisions. Tests are schema + Playwright-MCP smoke, not pixel assertions. Keep the existing r128 export as the fallback path — do not delete it.

### Task 8: Export orbit params instead of per-frame positions

**Files:**
- Modify: `great_silence/visualization/threejs/data_extractor.py`
- Test: `tests/test_viz_export.py` (new or extend existing viz test)

**Interfaces:**
- Produces: exported JSON gains a `stellar_orbits` block with arrays `R_g, Omega_g, kappa, nu, X, alpha, phi_g0, Z, beta` (from `orbit_model.params_dict()`), plus `reference_time_myr`. When `orbit_model is None`, fall back to existing per-frame `stellar_positions`.

- [ ] **Step 1: Failing schema test**

```python
def test_export_includes_orbit_params():
    from great_silence import GalaxySimulation, SimulationConfig
    from great_silence.visualization.threejs.data_extractor import extract_data  # match real name
    c = SimulationConfig(); c.galaxy.total_stars = 500; c.simulation.orbit_mode = "fast"
    sim = GalaxySimulation(c); sim.initialize(); sim.run()
    data = extract_data(sim)
    assert "stellar_orbits" in data
    assert len(data["stellar_orbits"]["R_g"]) == 500
```

(Confirm the real extractor entry-point name first; adjust import.)

- [ ] **Step 2–4:** Implement, run FAIL→PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat: export epicyclic orbit params for GPU viz"`

### Task 9: WebGPURenderer galaxy with shader-computed positions + cinematic look

**Files:**
- Create: `great_silence/visualization/threejs/templates/webgpu/` (scene, star material with TSL position-from-orbit-params, selective bloom, nebula, disaster shaders)
- Modify: `index.html.j2` to load the WebGPU build when `navigator.gpu` exists, else current r128.

**Interface contract (the part that must be exact):**
- Per-star instanced attributes: `R_g, Omega_g, kappa, nu, X, alpha, phi_g0, Z, beta` (float), plus `starColorTemp` (float, from mass/type).
- Uniform: `currentTimeMyr` (float). Vertex/compute stage computes position exactly as `EpicyclicOrbitModel.positions_at_time` (same formula — radial `R_g + X cos(κt+α)`, azimuth with `gamma = 2Ω/(κ R_g)` coupling, vertical `Z cos(νt+β)`), so playback and slider scrub need only update `currentTimeMyr`.
- Look: ACESFilmic tone mapping; selective bloom on stars + disaster meshes only; additive HDR sprites; temperature→color; volumetric nebula backdrop; disaster shockwave/glow.

- [ ] **Step 1:** Build the WebGPU scene + star material; map the orbit-param attributes; implement the position formula in TSL.
- [ ] **Step 2:** Add tone mapping, selective bloom, nebula, disaster effects, cinematic intro camera (apply `frontend-design`).
- [ ] **Step 3:** Wire feature-detection fallback to r128 in `index.html.j2`.
- [ ] **Step 4: Playwright-MCP smoke test** — export an HTML, open it, assert: canvas present, `navigator.gpu` path active (or fallback), zero console errors, stars visibly move when `currentTimeMyr` advances. Record steps in `tests/test_viz_smoke.md`.
- [ ] **Step 5: Commit** — `git commit -am "feat: WebGPU galaxy viz with shader-computed epicyclic positions"`

---

## Phase 5 — NiceGUI polish

### Task 10: Smoother run loop + progress

**Files:**
- Modify: `great_silence/webapp/components/simulation_runner.py`

- [ ] **Step 1:** Make the run loop async / non-blocking; drive the progress bar by sim-time fraction (`current_time_myr / total`); throttle the event feed (batch updates, cap list length).
- [ ] **Step 2:** Manual check + existing webapp import test: `pytest tests/ -k webapp --override-ini="addopts="` (add a build-smoke test if none exists).
- [ ] **Step 3: Commit** — `git commit -am "feat: smooth async run loop and sim-time progress"`

### Task 11: Premium theme + dashboard

**Files:**
- Modify: `great_silence/webapp/themes.py`, `great_silence/webapp/components/results_dashboard.py`, `great_silence/webapp/components/parameter_plots.py`

- [ ] **Step 1:** Apply `frontend-design` skill — glassmorphism cards, typographic scale, motion/transitions, responsive layout; refresh dashboard plots.
- [ ] **Step 2:** Build-smoke test passes (app imports, pages construct without error).
- [ ] **Step 3: Commit** — `git commit -am "feat: premium NiceGUI theme and dashboard polish"`

---

## Phase 6 — Validation gate

### Task 12: Fast-vs-exact drift validation (the default-on gate)

**Files:**
- Create: `tests/test_orbit_drift.py`
- Doc: `claude_comments/orbit_engine_benchmark.md` (append drift section)

**Success gate (from spec):** median per-star radial error < 5% of `R_g` over 2 Gyr between fast tier and exact leapfrog; `L_z` conserved by construction.

- [ ] **Step 1: Write the gate test**

```python
def test_fast_vs_exact_radial_drift_under_5pct():
    import numpy as np
    from great_silence import GalaxySimulation, SimulationConfig
    from great_silence.galaxy.orbits import EpicyclicOrbitModel

    c = SimulationConfig(); c.galaxy.total_stars = 4000
    sim = GalaxySimulation(c); sim.initialize()
    orb = EpicyclicOrbitModel.from_galaxy(sim.galaxy)

    # exact reference: integrate the same stars 2 Gyr with leapfrog
    t = 2000.0
    fast = orb.positions_at_time(t)
    exact = sim.galaxy.integrate_reference(t)   # thin helper: loop evolve_positions_adaptive to t
    R_fast = np.sqrt(fast[:, 0]**2 + fast[:, 1]**2)
    R_exact = np.sqrt(exact[:, 0]**2 + exact[:, 1]**2)
    assert np.median(np.abs(R_fast - R_exact) / orb.R_g) < 0.05
```

- [ ] **Step 2:** Add a minimal `GalaxyModel.integrate_reference(t_myr)` helper (loops the existing exact integrator to time `t`, returns positions). Run the gate.
- [ ] **Step 3:** If it fails, record the measured median in the benchmark doc and revisit the 5% number per spec (the number is revisitable; document the real value). If it passes, confirm `orbit_mode="fast"` default stands.
- [ ] **Step 4:** Full suite green: `micromamba run -n galaticbot python -m pytest tests/ -q --override-ini="addopts="`.
- [ ] **Step 5: Commit** — `git commit -am "test: fast-vs-exact orbit drift validation gate"`

---

## Self-review notes

- Spec coverage: A→Tasks 1-6, B→Task 7, C→Tasks 8-9, D→Tasks 10-11, success criteria→Tasks 6 & 12. Covered.
- Frontend tasks (9, 11) intentionally specify interface contracts + deliverables rather than full shader/CSS source — those are iterative visual work driven by `frontend-design`; the exact part (orbit-param attribute names, the position formula, the data schema) is pinned.
- Type consistency: orbit param names `R_g, Omega_g, kappa, nu, X, alpha, phi_g0, Z, beta` are identical across Tasks 2, 3, 8, 9, 12.
- Verify real entry-point names before importing in tests (`extract_data`, exact intercept method signatures) — noted inline.
