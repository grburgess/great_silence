# Frontend pass — followups & known limitations (2026-07-01)

Built on branch perf-visual-frontend: WebGPU galaxy viz, orbit-param export,
async NiceGUI run loop, premium theme. Verified via Playwright (WebGPU ran on
this host's Metal adapter; galaxy renders with bloom/temperature-color/nebula/
shockwaves; screenshots captured). Post-build fixes applied:

- FIXED (critical): simulation_runner.py used asyncio.ensure_future + run.io_bound
  without `import asyncio` / `from nicegui import run` -> NameError crash on Run.
  The Task 10 smoke test passed only because it constructed the page but never
  executed the handler. Added imports + test_run_handler_names_resolve guard.
- FIXED (minor): np.trapz -> np.trapezoid in parameter_plots.py (numpy 2 deprecation).

Open followups (not blocking):
- WebGPU smooth-motion path: the .mjs shader drives positions from stellar_orbits
  params + a currentTimeMyr uniform (smooth), but in the export the r128
  updateFrame/updateStellarPositions snapshot path is also present and
  isStellarMotionEnabled() is false, so timeline motion is applied per-snapshot
  (stepped) rather than smoothly shader-interpolated. Stars do move; the smooth
  GPU-scrub feature needs the two paths reconciled (WebGPU should own the timeline
  and ignore the r128 snapshot updater when __USE_WEBGPU).
- Exported HTML loads three.js from CDNs (needs network) and file:// is blocked by
  the browser sandbox (must be served over http). Consider bundling for offline.
- ~~render() path (webapp embedding) does not copy templates/webgpu/*.mjs — only
  export()-to-file does. Webapp-embedded viz falls back to r128.~~ RESOLVED/stale
  (verified 2026-07-01): results_dashboard._generate_viz uses export_html (=
  export()), which copies webgpu/*.mjs into the served temp dir. Replicated the
  webapp export+serve exactly and loaded in Playwright: __USE_WEBGPU=true,
  __wgpuActive=true, all parity layers present, mjs served 200. Webapp runs full
  WebGPU, not r128.
- Static (non-animated) exports show no disaster shockwaves (populated per-frame).
- results_dashboard.py: add ARIA labels on viz/export/fullscreen controls.
