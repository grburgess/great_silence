# Webapp Connection-Loss Fix + WebGL Viz Quick Wins — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kill the "connection lost" on viz generation (async export + dedupe + leak fix + reconnect timeout) and remove the WebGL fallback's per-tick scene churn, GPU leaks, and dead code.

**Architecture:** Python side: `ThreeJSRenderer.render()` reuses already-extracted data; the webapp offloads export to a worker thread and serves viz from one persistent static root with keep-last-3 pruning. JS side: template-only edits — frame-index gate in the playback loop, shared sprite-material cache, dispose-before-remove, dead-code deletion. WebGPU stays the default renderer (feature-detect at `index.html.j2:642`); these WebGL changes are fallback hygiene.

**Tech Stack:** Python 3 (micromamba env `galaticbot`), NiceGUI 3.14, Jinja2 templates rendering Three.js r128 (WebGL fallback), pytest.

## Global Constraints

- Run all Python via `micromamba run -n galaticbot ...`; tests via `micromamba run -n galaticbot python -m pytest <file> -x -q --override-ini="addopts="`.
- NO COMMENTS in code unless stating a non-obvious constraint (project rule).
- Match existing style; tests follow the patterns in `tests/test_webapp_smoke.py` / `tests/test_viz_export.py`.
- Ruff auto-runs after each edit and strips unused imports — add an import and its first use in the SAME edit.
- Known pre-existing test failures (do not fix, do not be blocked by): `test_progress_tracking.py` (14), `test_war_mechanics.py` (8), 2 delta-compression snapshot tests.

---

### Task 1: Dedupe export pipeline in `html_exporter.py`

**Files:**
- Modify: `great_silence/visualization/threejs/html_exporter.py:33-106` (`_load_data`), `:108-160` (`render`), `:162-215` (`export`)
- Test: `tests/test_viz_export.py`

**Interfaces:**
- Produces: `ThreeJSRenderer._loaded_animated: Optional[bool]` attr (None until `_load_data` runs); `render()` skips `_load_data` when `self.data` is populated for the same `animated` flag. Task 2 relies on `export_html(...)` being ~2x faster but signature-unchanged.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_viz_export.py`:

```python
def test_export_loads_data_once(tmp_path, monkeypatch):
    sim = _run_sim(n=300, orbit_mode="fast")

    from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer

    renderer = ThreeJSRenderer(sim)
    calls = []
    original = ThreeJSRenderer._load_data

    def counting_load(self, animated=False):
        calls.append(animated)
        return original(self, animated)

    monkeypatch.setattr(ThreeJSRenderer, "_load_data", counting_load)
    renderer.export(str(tmp_path / "viz.html"), animated=False)

    assert len(calls) == 1


def test_render_reloads_when_animated_flag_changes(tmp_path):
    sim = _run_sim(n=300, orbit_mode="fast")

    from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer

    renderer = ThreeJSRenderer(sim)
    renderer.render(animated=False)
    assert "civilizations" in renderer.data

    renderer.render(animated=True)
    assert "frames" in renderer.data
```

- [ ] **Step 2: Run tests to verify the first fails**

Run: `micromamba run -n galaticbot python -m pytest tests/test_viz_export.py -x -q --override-ini="addopts=" -k "loads_data_once or reloads_when"`
Expected: `test_export_loads_data_once` FAILS with `assert 2 == 1` (export calls `_load_data`, then `render()` calls it again). `test_render_reloads_when_animated_flag_changes` passes already (documents behavior to preserve).

- [ ] **Step 3: Implement the dedupe**

In `_load_data`, record the flag. Add to `__init__` after `self.data: dict = {}`:

```python
        self._loaded_animated: Optional[bool] = None
```

At the very end of `_load_data` (after the `else:` block's `self.data = {...}`):

```python
        self._loaded_animated = animated
```

In `render()`, replace `self._load_data(animated)` (line 128) with:

```python
        if not self.data or self._loaded_animated != animated:
            self._load_data(animated)
```

In `export()`, delete the dead first render — remove these lines (193-195):

```python
        template = self._get_template()

        html = template.render(**template_data)
```

(Keep the `template_data` dict at 183-191 — the per-JS-template loop at line 239 still uses it. Keep `self._load_data(animated)` at 181 — the sidecar size decision needs it; `render()` now reuses it.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `micromamba run -n galaticbot python -m pytest tests/test_viz_export.py -x -q --override-ini="addopts="`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_viz_export.py great_silence/visualization/threejs/html_exporter.py
git commit -m "perf: load viz data once per export instead of twice"
```

### Task 2: Async viz generation + persistent viz root in webapp

**Files:**
- Modify: `great_silence/webapp/components/results_dashboard.py` (module top, `_generate_viz`, `_export_html`), `great_silence/webapp/app.py:175-184` (`run_app`)
- Test: `tests/test_webapp_smoke.py`

**Interfaces:**
- Consumes: `export_html` (unchanged signature, faster after Task 1); `nicegui.run.io_bound(fn, *args, **kwargs)`.
- Produces: module-level `VIZ_ROOT: Path` and `_prune_viz_dirs(root: Path, keep: int = 3, exclude: Optional[Path] = None) -> None` in `results_dashboard.py`; `ResultsDashboard._generate_viz` and `._export_html` are coroutine functions; `run_app` passes `reconnect_timeout=30.0`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webapp_smoke.py`:

```python
def test_viz_handlers_are_async():
    import inspect

    from great_silence.webapp.components.results_dashboard import ResultsDashboard

    assert inspect.iscoroutinefunction(ResultsDashboard._generate_viz)
    assert inspect.iscoroutinefunction(ResultsDashboard._export_html)


def test_prune_viz_dirs_keeps_newest(tmp_path):
    from great_silence.webapp.components.results_dashboard import _prune_viz_dirs

    dirs = []
    for i in range(5):
        d = tmp_path / f"run_{i}"
        d.mkdir()
        os.utime(d, (i, i))
        dirs.append(d)

    _prune_viz_dirs(tmp_path, keep=2, exclude=dirs[0])

    remaining = sorted(p.name for p in tmp_path.iterdir())
    assert remaining == ["run_0", "run_3", "run_4"]


def test_run_app_sets_reconnect_timeout(monkeypatch):
    from nicegui import ui

    from great_silence.webapp import app as webapp_app

    captured = {}
    monkeypatch.setattr(ui, "run", lambda **kwargs: captured.update(kwargs))
    webapp_app.run_app()

    assert captured["reconnect_timeout"] == 30.0
```

Also add `import os` to the file's imports in the same edit (used by `os.utime`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `micromamba run -n galaticbot python -m pytest tests/test_webapp_smoke.py -x -q --override-ini="addopts="`
Expected: `test_viz_handlers_are_async` FAILS (plain functions); `test_prune_viz_dirs_keeps_newest` FAILS with ImportError; `test_run_app_sets_reconnect_timeout` FAILS with KeyError.

- [ ] **Step 3: Implement**

`results_dashboard.py` — replace the module imports block (lines 1-9) with:

```python
"""Results dashboard with Three.js visualization embed and statistics."""

import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

from nicegui import app, run, ui

from ..state import app_state

VIZ_ROOT = Path(tempfile.gettempdir()) / "great_silence_viz"
VIZ_ROOT.mkdir(parents=True, exist_ok=True)
app.add_static_files("/viz", str(VIZ_ROOT))


def _prune_viz_dirs(root: Path, keep: int = 3, exclude: Optional[Path] = None) -> None:
    run_dirs = [p for p in root.iterdir() if p.is_dir() and p != exclude]
    run_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for old in run_dirs[keep:]:
        shutil.rmtree(old, ignore_errors=True)
```

(`import os` disappears; `tempfile` stays. `app.add_static_files` at import time is safe — NiceGUI registers routes before `ui.run`.)

Replace `_generate_viz` (drop the inner `import time`/`import traceback` for `time` — keep `traceback` import inside or move to top; `time` is now top-level):

```python
    async def _generate_viz(self, sim) -> None:
        """Generate the Three.js visualization."""
        import traceback

        from great_silence.visualization.threejs import export_html

        self._generate_btn.disable()
        self._viz_frame_container.clear()
        with self._viz_frame_container:
            with ui.row().classes("items-center gap-3 mt-4"):
                ui.spinner(size="lg", color="cyan")
                ui.label("Generating visualization...").classes("text-gray-400")

        try:
            run_dir = VIZ_ROOT / f"run_{int(time.time() * 1000)}"
            run_dir.mkdir(parents=True, exist_ok=True)
            self._viz_html_path = str(run_dir / "visualization.html")

            await run.io_bound(
                export_html,
                sim,
                self._viz_html_path,
                animated=True,
                show_trajectories=True,
                show_spheres=True,
                show_hazards=True,
            )

            _prune_viz_dirs(VIZ_ROOT, keep=3, exclude=run_dir)

            viz_url = f"/viz/{run_dir.name}/visualization.html"

            self._viz_frame_container.clear()
            with self._viz_frame_container:
                ui.html(
                    f'<iframe src="{viz_url}" '
                    f'style="width: 100%; height: 600px; border: 1px solid #333; border-radius: 8px;">'
                    f"</iframe>",
                    sanitize=False,
                )

            self._fullscreen_frame.content = (
                f'<iframe src="{viz_url}" '
                f'style="width: 100%; height: calc(100vh - 80px); border: none;"></iframe>'
            )
            self._fullscreen_btn.visible = True

            ui.notify("Visualization generated!", type="positive")

        except Exception as e:
            traceback.print_exc()
            self._viz_frame_container.clear()
            ui.notify(f"Error generating visualization: {e}", type="negative")
        finally:
            self._generate_btn.enable()
```

In `_setup_visualization`, capture the button (assign `self._generate_btn = ui.button("Generate Visualization", ...)`).

Replace `_export_html` body's `export_html(sim, str(full_path), animated=True)` with `await run.io_bound(export_html, sim, str(full_path), animated=True)` and make the method `async def _export_html(self, sim) -> None:`.

`app.py` — in `run_app`, add `reconnect_timeout=30.0` to the `ui.run(...)` call.

- [ ] **Step 4: Run tests to verify they pass**

Run: `micromamba run -n galaticbot python -m pytest tests/test_webapp_smoke.py -x -q --override-ini="addopts="`
Expected: all pass (NiceGUI accepts async on_click handlers, so `main_page` construction still works).

- [ ] **Step 5: Commit**

```bash
git add tests/test_webapp_smoke.py great_silence/webapp/components/results_dashboard.py great_silence/webapp/app.py
git commit -m "fix: run viz export off the event loop; persistent viz root; reconnect_timeout=30"
```

### Task 3: WebGL template quick wins

**Files:**
- Modify: `great_silence/visualization/threejs/templates/ui.js.j2:675-738`, `great_silence/visualization/threejs/templates/scene.js.j2:224-225,263-391,393-434,436-461`, `great_silence/visualization/threejs/templates/particles.js.j2:21-58,104-121,162-172,222-240,303-321`
- Delete: `great_silence/visualization/threejs/templates/animation.js.j2`
- Test: `tests/test_threejs_template_hygiene.py` (create)

**Interfaces:**
- Consumes: nothing from other tasks (independent).
- Produces: `window._lastRenderedFrame` global in rendered `ui.js`; `_civSpriteMaterialCache` in rendered `particles.js`. Templates render with the same `template_data` contract as before.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_threejs_template_hygiene.py`:

```python
"""Rendered-template hygiene checks for the WebGL fallback renderer."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from great_silence.visualization.threejs.config import ThreeJSConfig

TEMPLATE_DIR = (
    Path(__file__).parent.parent / "great_silence" / "visualization" / "threejs" / "templates"
)


def _render(name):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    return env.get_template(name).render(
        config=ThreeJSConfig().to_dict(),
        show_trajectories=True,
        show_spheres=True,
        show_hazards=True,
        animated=True,
        animation_data_url=None,
        data={},
        animation_data=None,
    )


def test_playback_gates_on_frame_change():
    js = _render("ui.js.j2")
    assert "_lastRenderedFrame" in js


def test_no_per_frame_debug_logging_in_scene():
    js = _render("scene.js.j2")
    assert "[StellarMotion]" not in js
    assert "[Animation]" not in js
    assert "computeBoundingSphere" not in js


def test_scene_has_no_shadowed_playback_impl():
    js = _render("scene.js.j2")
    assert "function initAnimation" not in js
    assert "function playAnimation" not in js
    assert "function stepAnimation" not in js
    assert "function updateAnimation" not in js


def test_civ_sprite_materials_are_cached():
    js = _render("particles.js.j2")
    assert "_civSpriteMaterialCache" in js


def test_teardown_disposes_gpu_resources():
    js = _render("particles.js.j2")
    assert js.count(".dispose()") >= 6


def test_dead_trail_template_removed():
    assert not (TEMPLATE_DIR / "animation.js.j2").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `micromamba run -n galaticbot python -m pytest tests/test_threejs_template_hygiene.py -q --override-ini="addopts="`
Expected: all 6 FAIL.

- [ ] **Step 3: Edit `ui.js.j2` — frame gate**

In `updateAnimation`, replace the tail (lines 733-737):

```javascript
    const frameIndex = Math.floor(currentFrame);
    window.currentFrame = frameIndex;
    document.getElementById('timeline-slider').value = frameIndex;

    updateFrame(frameIndex);
```

with:

```javascript
    const frameIndex = Math.floor(currentFrame);
    if (frameIndex === window._lastRenderedFrame) {
        return;
    }
    window.currentFrame = frameIndex;
    document.getElementById('timeline-slider').value = frameIndex;

    updateFrame(frameIndex);
```

In `updateFrame`, after `window.currentFrame = frameIndex;` add:

```javascript
    window._lastRenderedFrame = frameIndex;
```

(Setting it inside `updateFrame` keeps direct callers — slider input, step buttons, resetPlayback — authoritative.)

- [ ] **Step 4: Edit `scene.js.j2` — dead code, logging, culling, LOD skip**

1. At `starPoints = new THREE.Points(starGeometry, starMaterial);` (line 224) add on the next line:

```javascript
    starPoints.frustumCulled = false;
```

2. Delete the whole shadowed playback block — `function initAnimation() {...}` through the end of `function updateAnimation(delta) {...}` (lines 263-391). Keep `renderStatic` above it and `updateStellarPositions` below it.

3. Replace `updateStellarPositions` (lines 393-434) with:

```javascript
function updateStellarPositions(positions) {
    if (!starGeometry || !positions || positions.length === 0) return;

    const positionAttribute = starGeometry.getAttribute('position');
    if (!positionAttribute) return;

    const count = Math.min(positions.length, positionAttribute.count);
    for (let i = 0; i < count; i++) {
        positionAttribute.setXYZ(i, positions[i][0], positions[i][1], positions[i][2]);
    }
    positionAttribute.needsUpdate = true;
}
```

4. In `animate()`, replace:

```javascript
    if (window.updateLOD) {
        window.updateLOD();
    }
```

with:

```javascript
    const cameraMoved = !window._lodCameraPos || camera.position.distanceToSquared(window._lodCameraPos) > 1e-8;
    if (window.updateLOD && (isPlaying || cameraMoved)) {
        window.updateLOD();
        window._lodCameraPos = camera.position.clone();
    }
```

- [ ] **Step 5: Edit `particles.js.j2` — material cache + dispose**

1. Above `createCivilizationSprite`, add the cache and rewrite sprite creation to use it:

```javascript
const _civSpriteMaterialCache = {};

function _getCivSpriteMaterial(baseColor, isActive) {
    const key = baseColor + '|' + (isActive ? 'a' : 'x');
    if (_civSpriteMaterialCache[key]) return _civSpriteMaterialCache[key];

    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');

    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, baseColor);
    gradient.addColorStop(0.4, baseColor);
    gradient.addColorStop(1, 'transparent');

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(32, 32, 32, 0, Math.PI * 2);
    ctx.fill();

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        opacity: isActive ? (window.config.civ_active_opacity || 0.9) : (window.config.civ_extinct_opacity || 0.5),
        blending: THREE.AdditiveBlending
    });
    _civSpriteMaterialCache[key] = material;
    return material;
}

function createCivilizationSprite(civData) {
    const baseColor = getKardashevColor(civData.kardashev);
    const sprite = new THREE.Sprite(_getCivSpriteMaterial(baseColor, civData.is_active));
    sprite.position.set(civData.position[0], civData.position[1], civData.position[2]);
    const size = civData.is_active ? (window.config.civ_active_size || 0.15) : (window.config.civ_extinct_size || 0.1);
    sprite.scale.set(size, size, 1);
    sprite.userData = civData;
    return sprite;
}
```

(Sprites share cached materials — teardown must NOT dispose them; `scene.remove` alone is correct for `updateCivilizations`.)

2. `updateProbes` teardown (lines 163-164) becomes:

```javascript
    probeLines.forEach(line => {
        line.geometry.dispose();
        line.material.dispose();
        scene.remove(line);
    });
    probeLines = [];
```

3. `updateHazards` teardown (lines 223-224) becomes:

```javascript
    hazardMeshes.forEach(mesh => {
        mesh.geometry.dispose();
        mesh.material.dispose();
        scene.remove(mesh);
    });
    hazardMeshes = [];
```

4. `updateTrajectories` teardown (lines 304-305) becomes:

```javascript
    trajectoryLines.forEach(obj => {
        obj.children.forEach(child => {
            child.geometry.dispose();
            child.material.dispose();
        });
        scene.remove(obj);
    });
    trajectoryLines = [];
```

- [ ] **Step 6: Delete the dead trail template**

```bash
git rm great_silence/visualization/threejs/templates/animation.js.j2
```

Then verify nothing references it: `grep -rn "animation.js" great_silence/visualization/threejs/templates/index.html.j2 test_threejs_templates.py` — the include list (`index.html.j2:992-1000`) does not contain it; if `test_threejs_templates.py` or webgpu assets reference it, fix those references in this step.

- [ ] **Step 7: Run tests to verify they pass**

Run: `micromamba run -n galaticbot python -m pytest tests/test_threejs_template_hygiene.py tests/test_viz_export.py tests/test_webapp_smoke.py -q --override-ini="addopts="`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add -A great_silence/visualization/threejs/templates tests/test_threejs_template_hygiene.py
git commit -m "perf: gate WebGL playback on frame change, cache civ sprite materials, dispose GPU resources, drop dead playback code"
```

### Task 4: End-to-end verification

**Files:**
- Create: scratchpad script `export_viz_steps12.py` (session scratchpad, not committed)

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Full test sweep**

Run: `micromamba run -n galaticbot python -m pytest tests/ -q --override-ini="addopts=" --ignore=tests/test_progress_tracking.py --ignore=tests/test_war_mechanics.py`
Expected: pass except the 2 known delta-compression failures.

- [ ] **Step 2: Export + browser verification (viz-verification-playbook)**

Scratchpad script: small sim (2000 stars, 1 Gyr, `save_snapshots=True`, `snapshot_interval_myr=25`), `export_html(sim, "output/viz_steps12.html", animated=True)`. Serve `output/` with `python -m http.server`, open via Playwright with a fresh `?fresh=1` query. Verify: WebGPU path initializes (no fallback error in console); force WebGL via an init script setting `Object.defineProperty(navigator, 'gpu', {get: () => undefined})`, reload, press Play, capture console — expect zero `[StellarMotion]`/`[Animation]` lines and no errors; confirm playback advances (canvas `toDataURL().length` changes across a second).

- [ ] **Step 3: Webapp end-to-end**

Launch `micromamba run -n galaticbot python -m great_silence.webapp --port 8082` in background. Playwright: set stars low (default preset fine at small count), Run Simulation, wait for completion, open 3D Visualization tab, click Generate Visualization. Verify: no "Connection lost" banner appears, spinner shows, iframe loads `/viz/run_*/visualization.html`. Click Generate again — verify a second `run_*` dir exists and pruning keeps ≤3+current in `$TMPDIR/great_silence_viz`.

- [ ] **Step 4: Update session notes + commit docs**

Append a short entry to AGENTS.md Session Notes (what was fixed, the double-pipeline gotcha, `add_static_files`-per-click leak pattern). Commit.

```bash
git add AGENTS.md docs/superpowers
git commit -m "docs: session notes for webapp viz connection-loss fix + WebGL quick wins"
```
