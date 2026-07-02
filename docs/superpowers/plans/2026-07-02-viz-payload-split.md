# Viz Payload Split (Step 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the generated viz payload (measured 74 MB HTML for a 10k-star run) by (a) replacing per-frame cumulative trajectory lists (17.9 MB) with one union edge list, and (b) externalizing the four data blobs (animation frames 49.5 MB, hrData 21.7 MB, galaxyData 2.9 MB, civStats 0.02 MB) into sidecar `.js` files.

**Architecture:** Trajectory entries gain stable `start_idx`/`end_idx`/`source` fields; a pure union builder keeps the earliest occurrence per `(civ_id, start_idx, end_idx)` (probe-sourced entries preferred over colony-fallback). The animated payload becomes one JSON object `{frames, trajectories, time_range}` with `trajectories` stripped from frames. `export()` always writes four `window.X = ...;` sidecar `.js` files next to the HTML (exports are already multi-file — scene.js etc.); bare `render()` stays self-contained via inline fallback. Both renderers build trajectory objects once and sweep `.visible` by time.

**Tech Stack:** Python (micromamba env `galaticbot`), Jinja2 templates, Three.js r128 (WebGL) + WebGPURenderer module, pytest.

## Global Constraints

- Run Python via `micromamba run -n galaticbot ...`; tests via `... -m pytest <file> -x -q --override-ini="addopts="`.
- NO COMMENTS unless stating a non-obvious constraint. Match existing style.
- Ruff PostToolUse hook strips imports unused at edit time — add import + first use in the SAME edit.
- Recon-verified facts: per-frame trajectory lists are NOT time-prefixes — snapshots shallow-copy civs so every frame carries the civ's FINAL `archived_probes`/`colonized_stars`; probe entries carry a true immutable `arrival_time_myr`; colony-fallback entries stamp `time_myr = snap.time_myr` (wrong, per-frame). Coordinate-based dedup cannot work (endpoints drift with stellar motion; measured 97.7% "unique" by coords).
- Classic `<script src>` sidecars work under `file://` and are guaranteed to execute before `window.onload` and before the `type="module"` WebGPU block.
- `galaxy-webgpu.mjs` falls back to `hrData.per_frame.length` for chart frame count — hrData must still be a global (sidecar is fine, it loads first).

---

### Task 1: Trajectory indices + union builder in `data_extractor.py`

**Files:**
- Modify: `great_silence/visualization/threejs/data_extractor.py:107-178` (`_extract_expansion_trajectories`), add module-level `build_union_trajectories(snapshots)` below it
- Test: `tests/test_viz_export.py`

**Interfaces:**
- Produces: trajectory entries gain `"start_idx": int, "end_idx": int, "source": "probe"|"colony"`; `build_union_trajectories(snapshots: list[dict]) -> list[dict]` — snapshots are the extractor's `self.snapshots` dicts (each with a `"trajectories"` list), returns deduped entries keyed `(civ_id, start_idx, end_idx)` (fallback: rounded coords for legacy entries lacking indices), keeping min `time_myr`, with `source=="probe"` beating `"colony"` on the same key.

- [ ] **Step 1: Write failing tests** (fake snapshot objects — deterministic, no sim needed for the extraction test; plain dicts for the union test)

```python
class _FakeProbe:
    def __init__(self, launch, target, arrival, generation=1):
        self.launch_star_idx = launch
        self.target_star_idx = target
        self.arrival_time_myr = arrival
        self.generation = generation


class _FakeCiv:
    def __init__(self, civ_id, home, probes=(), colonies=()):
        self.civ_id = civ_id
        self.parent_star_idx = home
        self.archived_probes = list(probes)
        self.colonized_stars = set(colonies)


class _FakeSnap:
    def __init__(self, time_myr, civs, positions):
        self.time_myr = time_myr
        self.civilization_states = civs
        self.stellar_positions = positions


def test_trajectory_entries_carry_indices_and_source():
    import numpy as np

    from great_silence.visualization.threejs.data_extractor import (
        _extract_expansion_trajectories,
    )

    pos = np.arange(30, dtype=float).reshape(10, 3)
    civ = _FakeCiv(7, home=0, probes=[_FakeProbe(0, 3, arrival=120.0)], colonies=[3, 5])
    snap = _FakeSnap(500.0, [civ], pos)

    entries = _extract_expansion_trajectories(snap)

    probe_entries = [e for e in entries if e["source"] == "probe"]
    colony_entries = [e for e in entries if e["source"] == "colony"]
    assert probe_entries[0]["start_idx"] == 0
    assert probe_entries[0]["end_idx"] == 3
    assert probe_entries[0]["time_myr"] == 120.0
    assert colony_entries[0]["end_idx"] == 5


def test_union_trajectories_dedups_and_keeps_earliest():
    from great_silence.visualization.threejs.data_extractor import build_union_trajectories

    def entry(civ, s, e, t, source="probe", coords=None):
        return {
            "start": coords or [float(s)] * 3,
            "end": [float(e)] * 3,
            "civ_id": civ,
            "generation": 1,
            "time_myr": t,
            "start_idx": s,
            "end_idx": e,
            "source": source,
        }

    snapshots = [
        {"trajectories": [entry(1, 0, 3, 120.0), entry(1, 0, 5, 300.0, source="colony")]},
        {"trajectories": [entry(1, 0, 3, 120.0, coords=[9.9] * 3), entry(1, 0, 5, 200.0, source="colony"), entry(2, 4, 6, 400.0)]},
    ]

    union = build_union_trajectories(snapshots)

    assert len(union) == 3
    by_key = {(e["civ_id"], e["start_idx"], e["end_idx"]): e for e in union}
    assert by_key[(1, 0, 3)]["start"] == [0.0] * 3
    assert by_key[(1, 0, 5)]["time_myr"] == 200.0


def test_union_prefers_probe_over_colony_on_same_key():
    from great_silence.visualization.threejs.data_extractor import build_union_trajectories

    colony = {"start": [0.0] * 3, "end": [1.0] * 3, "civ_id": 1, "generation": 0,
              "time_myr": 50.0, "start_idx": 0, "end_idx": 1, "source": "colony"}
    probe = {"start": [0.0] * 3, "end": [1.0] * 3, "civ_id": 1, "generation": 1,
             "time_myr": 90.0, "start_idx": 0, "end_idx": 1, "source": "probe"}
    union = build_union_trajectories([{"trajectories": [colony]}, {"trajectories": [probe]}])

    assert len(union) == 1
    assert union[0]["source"] == "probe"
```

- [ ] **Step 2: Run to verify failure** — `micromamba run -n galaticbot python -m pytest tests/test_viz_export.py -q --override-ini="addopts=" -k "trajectory or union"` → KeyError 'source' / ImportError build_union_trajectories.

- [ ] **Step 3: Implement.** In `_extract_expansion_trajectories`, add to the probe entry dict: `"start_idx": launch_idx, "end_idx": target_idx, "source": "probe"`; to the colony entry: `"start_idx": home_idx, "end_idx": colony_idx, "source": "colony"`. Add below the function:

```python
def build_union_trajectories(snapshots):
    """Collapse per-snapshot cumulative trajectory lists to unique edges (earliest occurrence)."""
    best = {}
    for snap in snapshots:
        for entry in snap.get("trajectories", []):
            if "start_idx" in entry and "end_idx" in entry:
                key = (entry["civ_id"], entry["start_idx"], entry["end_idx"])
            else:
                key = (
                    entry["civ_id"],
                    tuple(round(c, 3) for c in entry["start"]),
                    tuple(round(c, 3) for c in entry["end"]),
                )
            current = best.get(key)
            if current is None:
                best[key] = entry
                continue
            entry_is_probe = entry.get("source") == "probe"
            current_is_probe = current.get("source") == "probe"
            if entry_is_probe and not current_is_probe:
                best[key] = entry
            elif entry_is_probe == current_is_probe and entry["time_myr"] < current["time_myr"]:
                best[key] = entry
    return list(best.values())
```

- [ ] **Step 4: Run tests** → pass. **Step 5: Commit** `perf: add stable indices to trajectory entries and union edge builder`.

### Task 2: Animated payload reshape in `html_exporter.py`

**Files:**
- Modify: `great_silence/visualization/threejs/html_exporter.py:44-109` (`_load_data`)
- Test: `tests/test_viz_export.py`

**Interfaces:**
- Consumes: `build_union_trajectories` from Task 1.
- Produces: `self.data["animation_data"]` is `json.dumps({"frames": [...], "trajectories": [...], "time_range": [...]})`; frames no longer carry `"trajectories"`. `self.data["frames"]`/`["time_range"]` unchanged for compat.

- [ ] **Step 1: Failing test**

```python
def test_animation_payload_has_union_and_lean_frames():
    import json as _json

    sim = _run_sim_with_snapshots()

    from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer

    renderer = ThreeJSRenderer(sim)
    renderer._load_data(animated=True)
    payload = _json.loads(renderer.data["animation_data"])

    assert set(payload.keys()) == {"frames", "trajectories", "time_range"}
    assert all("trajectories" not in f for f in payload["frames"])
```

- [ ] **Step 2: Run** → fails (payload is a bare list). **Step 3: Implement** in `_load_data`: build `frame_data` without the `"trajectories"` key (drop line 61's entry from the dict); after the frames loop:

```python
            union_trajectories = build_union_trajectories(self.extractor.snapshots)
            payload = {
                "frames": frames,
                "trajectories": union_trajectories,
                "time_range": time_range,
            }
            frames_json = json.dumps(payload)
```

(import `build_union_trajectories` at top alongside `SimulationDataExtractor` — same edit). Keep `animation_data_size_mb` computed from the new blob.

- [ ] **Step 4: Run all of tests/test_viz_export.py** → pass. **Step 5: Commit** `perf: ship union trajectory list once instead of per-frame cumulative copies`.

### Task 3: Always-externalize data sidecars + template conditional embeds

**Files:**
- Modify: `great_silence/visualization/threejs/html_exporter.py` (`render()` 111-164: new url params, delete dead 149-163 block; `export()` 166-215: write 4 sidecars, drop `_data.json` logic), `great_silence/visualization/threejs/templates/index.html.j2:1002-1028` (conditional src/inline per blob; animationData inline becomes `window.animationData = {{ animation_data | safe }};`)
- Test: `tests/test_viz_export.py`

**Interfaces:**
- Produces: `render(..., animation_data_url=None, galaxy_data_url=None, hr_data_url=None, civ_stats_data_url=None)`; `export()` writes `{stem}_animation.js`, `{stem}_galaxy.js`, `{stem}_hrdata.js`, `{stem}_civstats.js` (each `window.X = <json>;`) and passes the filenames to `render()`. Bare `render()` (no urls) stays byte-equivalent self-contained inline.

- [ ] **Step 1: Failing tests**

```python
def test_export_writes_data_sidecars_and_slim_html(tmp_path):
    sim = _run_sim_with_snapshots()

    from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer

    renderer = ThreeJSRenderer(sim)
    renderer.export(str(tmp_path / "viz.html"), animated=True)

    for name in ["viz_animation.js", "viz_galaxy.js", "viz_hrdata.js", "viz_civstats.js"]:
        assert (tmp_path / name).exists(), name

    html = (tmp_path / "viz.html").read_text()
    assert 'src="viz_animation.js' in html
    assert "window.animationData = {" not in html
    assert "window.galaxyData = {" not in html
    assert not (tmp_path / "viz_data.json").exists()
    assert (tmp_path / "viz_animation.js").read_text().startswith("window.animationData = ")


def test_bare_render_stays_self_contained():
    sim = _run_sim_with_snapshots()

    from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer

    html = ThreeJSRenderer(sim).render(animated=True)

    assert "window.animationData = {" in html
    assert "<!-- ANIMATION_DATA -->" not in html
```

- [ ] **Step 2: Run** → sidecar test fails. **Step 3: Implement** exporter + template. Template pattern per blob (galaxy shown; same for hrData/civStats; animationData branch keeps the `animated` guard):

```jinja
{% if galaxy_data_url %}
<script src="{{ galaxy_data_url }}?v={{ range(1000000) | random }}"></script>
{% else %}
<script>
{% if data.galaxy %}
window.galaxyData = {{ data.galaxy | tojson | safe }};
{% endif %}
</script>
{% endif %}
```

export() sidecar writes (before calling render):

```python
        stem = Path(filepath).stem
        sidecars = {}
        blobs = [
            ("animation_data_url", f"{stem}_animation.js", "animationData",
             self.data.get("animation_data") if animated else None),
            ("galaxy_data_url", f"{stem}_galaxy.js", "galaxyData",
             json.dumps(self.data.get("galaxy")) if self.data.get("galaxy") else None),
            ("hr_data_url", f"{stem}_hrdata.js", "hrData",
             json.dumps(self.data.get("hr_data")) if self.data.get("hr_data") else None),
            ("civ_stats_data_url", f"{stem}_civstats.js", "civStatsData",
             json.dumps(self.data.get("civ_stats")) if self.data.get("civ_stats") else None),
        ]
        for param, filename, global_name, blob in blobs:
            if blob is None:
                continue
            with open(Path(filepath).parent / filename, "w") as f:
                f.write(f"window.{global_name} = {blob};")
            sidecars[param] = filename
        html = self.render(..., **sidecars)
```

(Note: `filepath.parent.mkdir` must move BEFORE sidecar writes.) Delete the dead placeholder block in `render()`; add the three new params defaulting None and pass into `template_data`. When a blob is externalized, drop it from the inline path via the template conditionals; also skip embedding `animation_data` string in `template_data` when `animation_data_url` is set (avoids a pointless multi-MB Jinja variable).

- [ ] **Step 4: Run tests + hygiene suite** → pass. **Step 5: Commit** `perf: externalize viz data blobs to sidecar js files; fix dead externalization branch`.

### Task 4: WebGL persistent trajectories (`particles.js.j2`, `ui.js.j2`)

**Files:**
- Modify: `great_silence/visualization/threejs/templates/particles.js.j2:260-358`, `great_silence/visualization/threejs/templates/ui.js.j2` (`updateFrame` trajectory call ~:779)
- Test: `tests/test_threejs_template_hygiene.py`

**Interfaces:**
- Produces: `updateTrajectories(currentTimeGyr)` (single arg) — lazily builds persistent objects from `window.animationData.trajectories`, then sweeps `.visible = showTrajectoryLines && time_myr <= tMyr`; `setTrajectoryVisibility` re-sweeps with the last time.

- [ ] **Step 1: Failing hygiene tests**

```python
def test_webgl_trajectories_built_once_from_union():
    js = _render("particles.js.j2")
    assert "animationData.trajectories" in js
    assert "_trajectoriesBuilt" in js


def test_updateframe_passes_time_only_to_trajectories():
    js = _render("ui.js.j2")
    assert "updateTrajectories(frame.trajectories" not in js
    assert "updateTrajectories(frame.time)" in js
```

- [ ] **Step 2: Run** → fail. **Step 3: Implement** — replace `updateTrajectories` body:

```javascript
let _trajectoriesBuilt = false;
let _lastTrajTimeMyr = 0;

function _buildTrajectoryObjects() {
    const unionList = (window.animationData && window.animationData.trajectories) || window.trajectoryData || [];
    unionList.forEach(traj => {
        if (!traj.start || !traj.end) return;
        const obj = createExpansionLine(traj);
        obj.visible = false;
        trajectoryLines.push(obj);
        scene.add(obj);
    });
    _trajectoriesBuilt = true;
}

function updateTrajectories(currentTimeGyr) {
    if (!_trajectoriesBuilt) _buildTrajectoryObjects();

    const currentTimeMyr = (currentTimeGyr || 0) * 1000;
    _lastTrajTimeMyr = currentTimeMyr;

    trajectoryLines.forEach(obj => {
        obj.visible = showTrajectoryLines && (obj.userData.time_myr || 0) <= currentTimeMyr;
    });

    if (window.updateStellarTime && typeof window.updateStellarTime === 'function') {
        window.updateStellarTime(currentTimeMyr);
    }
}

function setTrajectoryVisibility(visible) {
    showTrajectoryLines = visible;
    trajectoryLines.forEach(obj => {
        obj.visible = visible && (obj.userData.time_myr || 0) <= _lastTrajTimeMyr;
    });
}
```

`ui.js.j2` call becomes `window.updateTrajectories(frame.time);`. Grep for other `updateTrajectories(` call sites (scene.js static path, layers.js) and update them the same way in this step.

- [ ] **Step 4: Run hygiene tests** → pass. **Step 5: Commit** `perf: WebGL trajectories built once from union list, visibility-swept per frame`.

### Task 5: WebGPU build-once trajectories (`galaxy-webgpu.mjs`)

**Files:**
- Modify: `great_silence/visualization/threejs/templates/webgpu/galaxy-webgpu.mjs` (`buildDynamicLayers`, `rebuildTrajectories` → `updateTrajectoryVisibility`, `updateDynamicLayers`)
- Test: `tests/test_threejs_template_hygiene.py`

**Interfaces:**
- Produces: trajGroup children built once in `buildDynamicLayers()` from `window.animationData.trajectories` (line + end marker per edge, both with `userData.timeMyr`); `updateTrajectoryVisibility(tMyr)` sweeps `.visible`; `updateDynamicLayers` calls it with the frame's time.

- [ ] **Step 1: Failing test** (plain file read — .mjs is not a Jinja template)

```python
def test_webgpu_trajectories_built_once_from_union():
    mjs = (TEMPLATE_DIR / "webgpu" / "galaxy-webgpu.mjs").read_text()
    assert "animationData.trajectories" in mjs
    assert "updateTrajectoryVisibility" in mjs
    assert "rebuildTrajectories" not in mjs
```

- [ ] **Step 2: Run** → fail. **Step 3: Implement**: in `buildDynamicLayers()` after `scene.add(...)`, build children from the union list (reuse the existing line/marker construction from `rebuildTrajectories`, storing `child.userData.timeMyr = traj.time_myr || 0`, initial `visible = false`); replace `rebuildTrajectories(frame)` with:

```javascript
function updateTrajectoryVisibility(tMyr) {
    for (const child of trajGroup.children) {
        child.visible = child.userData.timeMyr <= tMyr;
    }
    trajGroup.visible = showTrajectories;
}
```

and in `updateDynamicLayers(frameIdx)` call `updateTrajectoryVisibility(frame.time_myr !== undefined ? frame.time_myr : (frame.time || 0) * 1000)`.

- [ ] **Step 4: Run** → pass. **Step 5: Commit** `perf: WebGPU trajectories built once, visibility-swept on frame change`.

### Task 6: Compat + verification

**Files:**
- Modify: `test_threejs_templates.py` (root script — wrap mock frames as `{"frames": ..., "trajectories": [], "time_range": ...}`)
- Verify: full suite, before/after size measurement, Playwright (both renderers: trajectories appear progressively over time), webapp e2e.

- [ ] Step 1: Update root script's `template_data["animation_data"]` to the new dict shape.
- [ ] Step 2: `pytest tests/ -q --override-ini="addopts=" --ignore=tests/test_progress_tracking.py --ignore=tests/test_war_mechanics.py` → only known pre-existing failures.
- [ ] Step 3: Re-run the recon measurement config (10k stars/5 Gyr/emergence-boosted) → record new HTML + sidecar sizes vs 74 MB baseline; trajectory blob vs 17.9 MB.
- [ ] Step 4: Playwright: serve export, WebGPU path — scrub timeline, assert trajGroup children count constant while visible count grows with time; forced-WebGL copy — same for trajectoryLines; webapp generate-viz still clean.
- [ ] Step 5: Update AGENTS.md session notes + memory roadmap; commit docs.
