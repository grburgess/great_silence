# Three.js Visualization Troubleshooting Guide

## Issues Encountered

### 1. JavaScript Files Not Found (404 Errors)

**Problem:** Browser shows "Failed to load resource: the server responded with a status of 404 (File not found)" for .js files

**Root Cause:** JavaScript template files had `.j2` extension but were being exported as `filename.js.j2` instead of `filename.js`

**Solution:**
- Fixed filename generation in `html_exporter.py`:
  ```python
  js_filename = template_file.stem.replace('.js', '') + '.js'
  ```
- Template files must be named correctly: `scene.js.j2`, `camera.js.j2`, etc.

**Check:** List examples/*.js to verify correct filenames

---

### 2. THREE is Not Defined

**Problem:** Console shows "Uncaught ReferenceError: THREE is not defined"

**Root Cause:** Script loading order - custom JS files loaded before Three.js CDN

**Solution:** 
- Ensure Three.js CDN scripts are loaded BEFORE custom JS files in HTML template
- Order in `index.html.j2`:
  ```html
  <!-- Three.js CDNs FIRST -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r150/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.150.0/examples/js/controls/OrbitControls.js"></script>
  <!-- etc -->
  
  <!-- Custom JS files AFTER -->
  <script src="scene.js"></script>
  <script src="camera.js"></script>
  ```

**Check:** View page source and verify Three.js scripts come before scene.js

---

### 3. Jinja2 Template Syntax in Shader Code

**Problem:** "jinja2.exceptions.UndefinedError: 'window' is undefined"

**Root Cause:** Using Jinja2 template syntax inside JavaScript template strings

**Wrong:**
```javascript
const starFragmentShader = `
    float opacity = {{ window.config.star_opacity or 0.8 }};
`;
```

**Correct:**
```javascript
const starFragmentShader = `
    float opacity = window.config.star_opacity || 0.8;
`;
```

**Rule:** Don't use Jinja2 `{{ }}` or `{% %}` syntax inside JavaScript template strings (backtick strings)

---

### 4. onWindowResize Function Not Found

**Problem:** "Uncaught ReferenceError: onWindowResize is not defined"

**Root Cause:** Function defined AFTER it's called by event listener

**Solution:** Define functions BEFORE they're referenced

**Wrong:**
```javascript
window.addEventListener('resize', onWindowResize);

function onWindowResize() {
    // ...
}
```

**Correct:**
```javascript
function onWindowResize() {
    // ...
}

window.addEventListener('resize', onWindowResize);
```

---

### 5. Local Server Required

**Problem:** Opening HTML file directly (`file://`) causes CORS errors

**Solution:** Always use local HTTP server:

```bash
cd examples
python -m http.server 8080
# Or use:
python examples/launch_viz_server.py
```

Then open: http://localhost:8080/galaxy_visualization.html

---

### 6. Duplicate Function Definitions

**Problem:** Multiple `function initScene()` or `function onWindowResize()` in same file

**Root Cause:** Template includes partial file multiple times, or copy-paste error

**Check:** 
```bash
grep -n "function initScene" scene.js
# Should show: 1 definition only
```

---

## Debugging Steps

### Step 1: Verify Files Exist
```bash
ls examples/*.js
ls examples/*.html
```

### Step 2: Check Script Order in HTML
```bash
grep "script src" examples/galaxy_visualization.html
# Verify Three.js CDNs come first, then custom JS files
```

### Step 3: Check Browser Console
- Open DevTools (F12)
- Look for 404 errors for JS files
- Look for "THREE is not defined" errors
- Look for function not defined errors

### Step 4: Verify Template Rendering
```bash
head -20 examples/scene.js
# Check that window.config appears correctly
# Check that THREE references exist
```

### Step 5: Check for Template Syntax Errors
```bash
python examples/quick_viz_example.py
# Watch for Jinja2 errors during export
```

---

## File Structure

### Template Files (j2)
```
great_silence/visualization/threejs/templates/
├── __init__.py
├── index.html.j2          # Main HTML template
├── scene.js.j2             # Scene initialization
├── camera.js.j2            # Camera controls
├── particles.js.j2          # Star particles
├── lod.js.j2                # Level of detail
├── ui.js.j2                 # User interface
└── postprocess.js.j2       # Post-processing effects
```

### Exported Files
```
examples/
├── galaxy_visualization.html  # Complete HTML
├── scene.js                 # Rendered from scene.js.j2
├── camera.js                # Rendered from camera.js.j2
├── particles.js              # Rendered from particles.js.j2
├── lod.js                   # Rendered from lod.js.j2
├── ui.js                    # Rendered from ui.js.j2
└── postprocess.js            # Rendered from postprocess.js.j2
```

---

## Key Code Patterns

### Correct Template Usage

**Inside JavaScript files (templates/*.js.j2):**
- Use `window.config.variable` for config values
- Use JavaScript defaults: `|| 0.8` instead of Jinja2 `or 0.8`
- Don't use `{{ }}` or `{% %}` inside JavaScript

**Inside HTML template (index.html.j2):**
- Use Jinja2 `{{ }}` for data injection
- Use Jinja2 `{% if %}` for conditional logic
- Order scripts: Three.js CDNs → Custom JS → Init code

---

## Quick Fixes

### Fix 404 for JS files
```bash
rm examples/*.js
python examples/quick_viz_example.py
```

### Fix THREE undefined
Check `index.html.j2` script order - Three.js must load before scene.js

### Fix template syntax
Search for `{{` inside JavaScript template strings in .j2 files
Replace with JavaScript defaults: `|| defaultValue`

---

## Testing Checklist

- [ ] All .js files exist in examples/
- [ ] Three.js CDN scripts load first in HTML
- [ ] Custom JS files load after Three.js
- [ ] No duplicate function definitions
- [ ] No Jinja2 syntax in JavaScript template strings
- [ ] Functions defined before they're called
- [ ] Use local HTTP server, not file://
- [ ] Check browser console for errors
- [ ] Verify window.config is defined before use

---

## Current Status

**Last Issues:**
- JavaScript files export correctly
- Script loading order looks correct
- Still getting "THREE is not defined" error

**Root Cause Identified:**
CDN scripts failing to load despite correct order and HTTP server usage.

## Fixes Applied (Jan 14, 2026)

### 1. Added CDN Fallbacks
All Three.js scripts now fallback from cdnjs/cdnjs to unpkg:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r150/three.min.js"
        onerror="this.src='https://unpkg.com/three@0.150.0/build/three.min.js'">
```

### 2. Added Global Error Detection
Script listener detects loading failures:
```javascript
window.addEventListener('error', function(e) {
    if (e.target.tagName === 'SCRIPT') {
        console.error('Script failed to load:', e.target.src);
    }
}, true);
```

### 3. Added THREE Availability Check
Graceful error message if Three.js fails to load:
```javascript
if (typeof THREE === 'undefined') {
    document.getElementById('loading-text').textContent = 'Error: Three.js failed to load...';
    return;
}
```

## Testing After Fixes

1. Re-export visualization:
   ```bash
   python examples/quick_viz_example.py
   ```

2. Start server:
   ```bash
   cd examples && python -m http.server 8080
   ```

3. Check console:
   - No "THREE is not defined" errors
   - No CDN 404 errors
   - Fallback messages if primary CDN fails

## Future Improvements

- Consider bundling Three.js locally for offline use
- Add script loading progress indicator
- Implement local Three.js download in html_exporter.py
