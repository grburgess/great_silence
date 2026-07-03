# Smooth Expansion (Step 4, WebGPU) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Civilization and probe markers move smoothly through time in the WebGPU renderer (the default) instead of jumping at 100 Myr snapshot boundaries, and trajectory edges appear at their true continuous times.

**Architecture:** A new pure helper module `webgpu/interp-utils.mjs` (no three.js imports — Node-testable) provides binary-search keyframe bracketing with a duplicate-time alpha guard. `galaxy-webgpu.mjs` replaces the per-frame clearGroup+rebuild of civ/probe layers with per-id mesh pools synced on frame-index change, plus a per-tick interpolation pass that lerps positions between bracketing frames using the existing continuous `currentTimeMyr` clock. Trajectory visibility sweeps per-tick (continuous) instead of per-frame-change. `frameIndexForTime()` switches from round-on-uniform-spacing to binary search over actual frame times. WebGL fallback is untouched (user decision: WebGPU is the target renderer).

**Tech Stack:** three@0.180 WebGPURenderer module (TSL node materials), plain ES module helpers, pytest + node for helper tests.

## Global Constraints

- Run Python via `micromamba run -n galaticbot ...`; tests via `... -m pytest <file> -x -q --override-ini="addopts="`.
- NO COMMENTS unless stating a non-obvious constraint.
- GameBlocks skill assessed and rejected for this work (input-driven motion controllers + Rapier + three@0.161 vs our data-driven keyframe playback on r128/0.180) — do not import its modules.
- Frames carry stable `civ_id` (per civ) and `probe_id` (per probe); frame times via `time_myr` (fallback `time*1000`). Snapshot spacing is NOT uniform (adaptive dt catch-up can cluster snapshots) — alpha must guard `dt < EPS`.
- `export()` copies `webgpu/*.mjs` assets next to the HTML (html_exporter.py glob) — a new .mjs file ships automatically.
- Headless Playwright here lacks `navigator.gpu`; runtime WebGPU verification is best-effort (attempt chromium with `--enable-unsafe-webgpu`), otherwise flag for a manual look.

---

### Task 1: Pure interpolation helpers (`webgpu/interp-utils.mjs`)

**Files:**
- Create: `great_silence/visualization/threejs/templates/webgpu/interp-utils.mjs`
- Test: `tests/test_webgpu_interp_utils.py` (runs node assertions via subprocess)

**Interfaces:**
- Produces: `export function bracketForTime(times, tMyr)` → `{i, j, alpha}` with `times` ascending; clamps before-first → `{0,0,0}` and after-last → `{n-1,n-1,0}`; when `times[j]-times[i] < 1e-6` → `alpha = 1` (jump to later keyframe). `export function lerp3(a, b, alpha)` → 3-array.

- [ ] **Step 1: Write the failing test**

```python
"""Node-run tests for the WebGPU interpolation helpers."""

import shutil
import subprocess
from pathlib import Path

import pytest

MJS = (
    Path(__file__).parent.parent
    / "great_silence"
    / "visualization"
    / "threejs"
    / "templates"
    / "webgpu"
    / "interp-utils.mjs"
)

NODE_SCRIPT = """
import {{ bracketForTime, lerp3 }} from '{mjs}';

function eq(actual, expected, label) {{
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {{
        console.error(`FAIL ${{label}}: got ${{JSON.stringify(actual)}} expected ${{JSON.stringify(expected)}}`);
        process.exit(1);
    }}
}}

const times = [0, 100, 250, 250.0000001, 500];
eq(bracketForTime(times, -50), {{i: 0, j: 0, alpha: 0}}, 'before-first clamps');
eq(bracketForTime(times, 600), {{i: 4, j: 4, alpha: 0}}, 'after-last clamps');
eq(bracketForTime(times, 100), {{i: 1, j: 2, alpha: 0}}, 'exact keyframe hit');
eq(bracketForTime(times, 175), {{i: 1, j: 2, alpha: 0.5}}, 'midpoint non-uniform');
eq(bracketForTime(times, 250.00000005), {{i: 2, j: 3, alpha: 1}}, 'duplicate-time guard jumps to later frame');
eq(lerp3([0, 0, 0], [2, 4, 6], 0.5), [1, 2, 3], 'lerp3');
console.log('OK');
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_bracket_and_lerp_helpers(tmp_path):
    script = tmp_path / "run.mjs"
    script.write_text(NODE_SCRIPT.format(mjs=MJS.resolve()))
    result = subprocess.run(
        ["node", str(script)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
```

- [ ] **Step 2: Run** — `micromamba run -n galaticbot python -m pytest tests/test_webgpu_interp_utils.py -q --override-ini="addopts="` → FAIL (module missing).

- [ ] **Step 3: Implement** `interp-utils.mjs`:

```javascript
const DT_EPS = 1e-6;

export function bracketForTime(times, tMyr) {
    const n = times.length;
    if (n === 0) return { i: -1, j: -1, alpha: 0 };
    if (tMyr <= times[0]) return { i: 0, j: 0, alpha: 0 };
    if (tMyr >= times[n - 1]) return { i: n - 1, j: n - 1, alpha: 0 };
    let lo = 0;
    let hi = n - 1;
    while (hi - lo > 1) {
        const mid = (lo + hi) >> 1;
        if (times[mid] <= tMyr) lo = mid;
        else hi = mid;
    }
    const dt = times[hi] - times[lo];
    if (dt < DT_EPS) return { i: lo, j: hi, alpha: 1 };
    return { i: lo, j: hi, alpha: (tMyr - times[lo]) / dt };
}

export function lerp3(a, b, alpha) {
    return [
        a[0] + (b[0] - a[0]) * alpha,
        a[1] + (b[1] - a[1]) * alpha,
        a[2] + (b[2] - a[2]) * alpha,
    ];
}
```

- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat: keyframe bracketing helpers for WebGPU interpolation`.

### Task 2: Pooled + interpolated civ/probe layers in `galaxy-webgpu.mjs`

**Files:**
- Modify: `great_silence/visualization/threejs/templates/webgpu/galaxy-webgpu.mjs` — import helpers; `frameIndexForTime()` (:346) via binary search; `rebuildCivs`/`rebuildProbes` → pool sync keyed by id; new `updateLayerInterpolation(tMyr)` called from `tick()` after `uTime.value = currentTimeMyr` (:1264); trajectory sweep moves to the per-tick path.
- Test: `tests/test_threejs_template_hygiene.py`

**Interfaces:**
- Consumes: `bracketForTime`, `lerp3` from `./interp-utils.mjs` (relative import — sidecar dir preserved on export).
- Produces: module-level `frameTimesMyr` (built once when animationData present); `civPool: Map<civ_id, mesh>`, `probePool: Map<probe_id, mesh>`; `syncCivPool(frame)` / `syncProbePool(frame)` on frame-index change (membership + color/active state); `updateLayerInterpolation(tMyr)` per tick: bracket once, then lerp positions of pooled meshes between frames i and j by id (entity missing in j → hold at i's position); calls `updateTrajectoryVisibility(tMyr)`. Guard with `if (tMyr === lastInterpTimeMyr) return;`.

- [ ] **Step 1: Failing hygiene tests**

```python
def test_webgpu_layers_interpolate_continuously():
    mjs = (TEMPLATE_DIR / "webgpu" / "galaxy-webgpu.mjs").read_text()
    assert "interp-utils.mjs" in mjs
    assert "bracketForTime" in mjs
    assert "updateLayerInterpolation" in mjs
    assert "civPool" in mjs
    assert "probePool" in mjs


def test_webgpu_frame_index_uses_binary_search():
    mjs = (TEMPLATE_DIR / "webgpu" / "galaxy-webgpu.mjs").read_text()
    fn = mjs.split("function frameIndexForTime")[1].split("}")[0]
    assert "bracketForTime" in fn
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** Key points (adapt to actual code while editing):
  - `frameTimesMyr` computed lazily: `frames.map(f => f.time_myr !== undefined ? f.time_myr : (f.time || 0) * 1000)`.
  - `frameIndexForTime()` returns `bracketForTime(frameTimesMyr, currentTimeMyr)` `.alpha >= 0.5 ? j : i` equivalent (nearest) to preserve chart/HUD semantics.
  - Pools: mesh created via existing `emissiveSphere(...)` on first sight of an id; membership sweep hides meshes for ids absent from frame i; color/size/opacity refreshed on frame change only (Kardashev drifts slowly).
  - `updateLayerInterpolation` reads entries from frames i and j (per-frame `Map` id→entry caches, invalidated when i changes) and sets `mesh.position.set(...lerp3(pi, pj, alpha))`.
  - `tick()`: call `updateLayerInterpolation(currentTimeMyr)` every frame; `updateLayerFrame()` keeps handling frame-change work (hazards rebuild, pool sync, charts).
  - Remove the trajectory sweep from `updateDynamicLayers` (now per-tick).
- [ ] **Step 4: Run hygiene + interp tests** → PASS. `node --check` the .mjs. **Step 5: Commit** `feat: continuous-time interpolation for WebGPU civ/probe layers`.

### Task 3: Verification

- [ ] Step 1: Full affected suites (`test_threejs_template_hygiene.py`, `test_webgpu_interp_utils.py`, `test_viz_export.py`, `test_webapp_smoke.py`).
- [ ] Step 2: Attempt WebGPU runtime check: node script with playwright launching chromium `--enable-unsafe-webgpu --headless=new`; if `navigator.gpu` present, load the measure_out export via route-serving, scrub `currentTimeMyr` between two snapshot times and assert a tracked civ mesh position changes monotonically between keyframe positions (`window.__wgpuLayerState()` or a new debug hook `window.__wgpuInterpState()`). If WebGPU unavailable, record that manual verification is needed and rely on unit + hygiene tests.
- [ ] Step 3: Ultracode adversarial review of the full step-4 diff (workflow: 2-3 refuters on correctness of pooling lifecycle, alpha edge cases, id-matching, per-tick cost).
- [ ] Step 4: Docs — AGENTS.md session-notes entry + roadmap memory update; commit.
