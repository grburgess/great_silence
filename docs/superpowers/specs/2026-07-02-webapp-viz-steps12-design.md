# Webapp Connection-Loss Fix + WebGL Viz Quick Wins — Design

**Date:** 2026-07-02
**Approved by:** user (greenlit "steps 1+2, WebGPU as default" from ultracode brainstorm)

## Problem

1. Clicking "Generate Visualization" in the NiceGUI webapp shows "connection lost":
   `_generate_viz()`/`_export_html()` in `great_silence/webapp/components/results_dashboard.py`
   call `export_html()` synchronously in `on_click` handlers, blocking the asyncio event
   loop past NiceGUI's default `reconnect_timeout=3.0`. The block is ~2x longer than
   necessary because `ThreeJSRenderer.export()` runs the full extraction + serialize +
   template render pipeline twice (`html_exporter.py:181/195`, then again inside
   `render()` at `:128/:143`). Each click also leaks a `mkdtemp` dir and an
   `app.add_static_files` route.
2. The WebGL fallback renderer stutters and leaks GPU memory: `ui.js.j2:updateAnimation`
   calls `updateFrame()` every rAF tick with no frame-change gate (full civ/probe/hazard/
   trajectory teardown-rebuild ~60x/s); `particles.js.j2` rasterizes a fresh CanvasTexture
   per civilization per call and never disposes geometry/materials; `scene.js.j2` does
   per-frame `console.log` + `computeBoundingSphere()` over all stars; `scene.js.j2`
   carries a dead shadowed playback implementation and `animation.js.j2` is entirely
   unreferenced (not in the `index.html.j2` script list).

## Decision: renderer strategy

WebGPU **is already the default** (`index.html.j2:642` feature-detects `navigator.gpu`;
WebGL is the fallback, including on init failure). Keep that. Future interpolation work
(step 4, not in scope) targets `webgpu/galaxy-webgpu.mjs`. The WebGL quick wins below are
fallback hygiene + dead-code removal, not a WebGL investment.

## Scope (this spec = sequencing steps 1+2 only)

### Step 1 — connection loss (~40 lines, Python)
- `html_exporter.py`: dedupe — `render()` reuses `self.data` when already loaded for the
  same `animated` flag; `export()` drops its dead first template render. Halves export
  time for webapp and CLI alike.
- `results_dashboard.py`: `_generate_viz`/`_export_html` become `async def` and run
  `export_html` via `await run.io_bound(...)` with the button disabled and a spinner while
  exporting. Viz output goes to a persistent root (`$TMPDIR/great_silence_viz/run_<ms>/`)
  registered as a **single** static route at module import; keep-last-3 run dirs pruned on
  each new generation (never the one just created).
- `app.py`: `ui.run(..., reconnect_timeout=30.0)` as belt-and-braces.

### Step 2 — WebGL template quick wins (template edits only)
- `ui.js.j2`: gate `updateFrame()` on frame-index change (`window._lastRenderedFrame`,
  set inside `updateFrame` so slider/step direct calls stay correct). Shockwave/zone/beam
  visuals are pure functions of frame time, so the gate changes nothing visually.
- `scene.js.j2`: delete the dead shadowed `initAnimation`/`playAnimation`/`stepAnimation`/
  `updateAnimation` block (`:263-391`); strip debug logging and the per-frame
  `computeBoundingSphere()` from `updateStellarPositions`; set
  `starPoints.frustumCulled = false` at creation (single draw call, culling pointless);
  skip `updateLOD()` when paused and the camera hasn't moved.
- `particles.js.j2`: cache civ sprite materials by `(color, is_active)` — Kardashev
  colorscales yield ≤5 discrete colors, so ≤10 materials replace per-civ-per-frame canvas
  rasterization; dispose geometry/material before `scene.remove` in the probe/hazard/
  trajectory teardown loops (civ sprites share cached materials — remove only).
- Delete `animation.js.j2` (dead: never in the script include list; reads wrong key
  `p.id`).

## Out of scope (later steps, already designed)
Payload split / hrData gating / trajectory union list (step 3); continuous-clock
interpolation in WebGPU (step 4); settings-page redesign (step 5). Bonus bug noted, not
fixed here: `simulation_runner.py:135` mutates shared `app_state.config`.

## Success criteria
- `pytest tests/test_webapp_smoke.py tests/test_viz_export.py tests/test_threejs_template_hygiene.py` passes.
- Webapp end-to-end: run a small sim, click Generate Visualization — no "connection
  lost", iframe renders, second generation prunes old run dirs.
- Exported viz (WebGL fallback forced): playback shows no per-tick console spam; scene
  rebuild happens once per snapshot transition, not per rAF tick.
