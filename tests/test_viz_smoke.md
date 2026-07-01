# WebGPU galaxy viz — Playwright-MCP smoke test

Manual smoke test for the WebGPU renderer path
(`great_silence/visualization/threejs/templates/webgpu/galaxy-webgpu.mjs`).
Rendering is GPU-driven and cannot be pixel-asserted in CI, so this is run by
hand with the Playwright MCP browser.

## Export a test scene

```python
from great_silence import GalaxySimulation, SimulationConfig
from great_silence.visualization.threejs import export_html

c = SimulationConfig()
c.galaxy.total_stars = 3000
c.simulation.simulation_duration_gyr = 2.0
c.simulation.orbit_mode = "fast"          # produces sim.orbit_model -> stellar_orbits export
c.simulation.save_snapshots = True
sim = GalaxySimulation(c); sim.initialize(); sim.run()
export_html(sim, "galaxy.html", animated=True)
```

`export_html` copies `templates/webgpu/*.mjs` next to the HTML (into `./webgpu/`).

## Serve and open

`file://` is blocked for ES-module + importmap loading, so serve over HTTP:

```bash
python -m http.server 8791 --bind 127.0.0.1   # in the export directory
```

Navigate the MCP browser to `http://127.0.0.1:8791/galaxy.html`.

## Assertions (all verified 2026-07-01, headless Chromium / macOS Metal)

1. **WebGPU path active** — `window.__USE_WEBGPU === true` and
   `window.__wgpuActive === true` (feature detection picked WebGPU; the r128
   WebGL `init()` did not run).
2. **Zero console errors** — only one benign warning
   ("Multiple instances of Three.js being imported", from the coexisting r128
   global + the module three build).
3. **Canvas present** — the WebGPU canvas is appended to `#canvas-container`.
4. **Stars visibly move when `currentTimeMyr` advances** — scrub the timeline
   slider to `0` then `100`; `#time-display` goes `0.00 Gyr` -> `2.00 Gyr` and
   the outer-disk star pattern rotates/redistributes (positions recomputed on
   the GPU from the epicyclic formula; only the `currentTimeMyr` uniform is
   uploaded).
5. **Aesthetic** — bloomed HDR galactic core, temperature-colored stars,
   deep-space nebula backdrop, ACESFilmic tone mapping, cinematic slow-orbit
   intro camera; disaster shockwave rings (SN/GRB/NSM) glow via selective
   (threshold) bloom.

## Fallback

When `navigator.gpu` is absent, or the WebGPU module throws during init, the
page logs `WebGPU init failed, falling back to WebGL` and runs the existing
r128 `init()`. Verified by forcing an import failure: `__USE_WEBGPU` flips to
`false` and the WebGL scene renders.

**Note:** Headless environments without a working WebGPU adapter fall back to
r128 WebGL — that is acceptable. In this run headless Chromium exposed a real
WebGPU adapter (Metal), so the WebGPU path itself was exercised end-to-end.
