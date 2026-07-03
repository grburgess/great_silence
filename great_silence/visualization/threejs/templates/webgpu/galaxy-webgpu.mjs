// WebGPU galaxy renderer.
//
// Every star position is computed on the GPU from its epicyclic orbit
// parameters (R_g, Omega_g, kappa, nu, X, alpha, phi_g0, Z, beta) and a single
// `currentTimeMyr` uniform, mirroring EpicyclicOrbitModel.positions_at_time.
// Scrubbing / playback therefore only ever updates one float uniform -- zero
// per-frame CPU position upload.
//
// Analytic position (kpc, t in Myr):
//   ph_R  = kappa*t + alpha
//   R     = R_g + X*cos(ph_R)
//   gamma = 2*Omega_g / (kappa*R_g)
//   phi   = phi_g0 + Omega_g*t - gamma*X*sin(ph_R)
//   z     = Z*cos(nu*t + beta)
//   x = R*cos(phi);  y = R*sin(phi)

import * as THREE from 'three';
import {
    Fn, attribute, uniform, float, vec3, color,
    cos, sin, normalize, mix, positionLocal, pass,
} from 'three/tsl';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { bracketForTime, lerp3 } from './interp-utils.mjs';

const KPC = 1.0; // galaxy data is already in kpc scene units

const DISASTER_COLORS = {
    supernova: 0xff4400,
    grb: 0x00ffff,
    ns_merger: 0xff00ff,
};

const DISASTER_LIFESPAN_MYR = 320.0;
const DISASTER_MAX_RADIUS_KPC = 2.8;
const DISASTER_POOL_SIZE = 96;

function classifyDisaster(type) {
    const t = String(type || '').toLowerCase();
    if (t.includes('grb') || t.includes('gamma')) return 'grb';
    if (t.includes('ns') || t.includes('neutron') || t.includes('merger') || t.includes('kilonova')) return 'ns_merger';
    return 'supernova';
}

// --- module-level state (single renderer per page) ---
let renderer, scene, camera, controls, postProcessing;
let uTime, uStarIntensity;
let starPoints = null;
let disasterPool = [];
let disasterEvents = [];
let clock;

let minTimeMyr = 0.0;
let maxTimeMyr = 5000.0;
let currentTimeMyr = 0.0;
let playing = true;
let playbackMyrPerSec = 260.0;
let lastChartFrame = -1;

let introDone = false;
const introDuration = 5.5;
const camStart = new THREE.Vector3(2.0, 62.0, 4.0);
const camEnd = new THREE.Vector3(19.0, 15.0, 27.0);

function easeInOutCubic(x) {
    return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}

// ---------------------------------------------------------------------------
// Star field: GPU-computed epicyclic positions
// ---------------------------------------------------------------------------
function buildStarField(galaxyData) {
    const positions = galaxyData.positions || [];
    const n = positions.length;
    if (n === 0) return null;

    const orbits = galaxyData.stellar_orbits || null;
    const colors = galaxyData.colors || [];
    const sizes = galaxyData.sizes || [];

    const geometry = new THREE.BufferGeometry();

    // WebGPU caps a geometry at 8 vertex buffers, so orbit params are packed
    // into vec4 attributes rather than one buffer each.
    //   oA = (R_g, Omega_g, kappa, nu)
    //   oB = (X, alpha, phi_g0, Z)
    //   oC = (beta, starSize, unused, unused)
    const pos = new Float32Array(n * 3);
    const starColor = new Float32Array(n * 3);
    const oA = new Float32Array(n * 4);
    const oB = new Float32Array(n * 4);
    const oC = new Float32Array(n * 4);

    const g = orbits || {};
    for (let i = 0; i < n; i++) {
        const p = positions[i];
        pos[i * 3 + 0] = p[0];
        pos[i * 3 + 1] = p[1];
        pos[i * 3 + 2] = p[2];

        const c = colors[i] || [0.9, 0.9, 1.0];
        starColor[i * 3 + 0] = c[0];
        starColor[i * 3 + 1] = c[1];
        starColor[i * 3 + 2] = c[2];

        const s = sizes[i] !== undefined ? sizes[i] : 0.03;
        const sizePx = Math.min(6.0, 1.6 + s * 55.0);

        if (orbits) {
            oA[i * 4 + 0] = g.R_g[i];
            oA[i * 4 + 1] = g.Omega_g[i];
            oA[i * 4 + 2] = g.kappa[i];
            oA[i * 4 + 3] = g.nu[i];
            oB[i * 4 + 0] = g.X[i];
            oB[i * 4 + 1] = g.alpha[i];
            oB[i * 4 + 2] = g.phi_g0[i];
            oB[i * 4 + 3] = g.Z[i];
            oC[i * 4 + 0] = g.beta[i];
        }
        oC[i * 4 + 1] = sizePx;
    }
    geometry.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geometry.setAttribute('starColor', new THREE.BufferAttribute(starColor, 3));
    geometry.setAttribute('oC', new THREE.BufferAttribute(oC, 4));

    const material = new THREE.PointsNodeMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        sizeAttenuation: false,
    });

    material.colorNode = attribute('starColor', 'vec3').mul(uStarIntensity);
    material.sizeNode = attribute('oC', 'vec4').y;

    if (orbits) {
        geometry.setAttribute('oA', new THREE.BufferAttribute(oA, 4));
        geometry.setAttribute('oB', new THREE.BufferAttribute(oB, 4));

        const epicyclicPosition = Fn(() => {
            const t = uTime;
            const a = attribute('oA', 'vec4');
            const b = attribute('oB', 'vec4');
            const c = attribute('oC', 'vec4');
            const R_g = a.x;
            const Omega_g = a.y;
            const kappa = a.z;
            const nu = a.w;
            const X = b.x;
            const alpha = b.y;
            const phi_g0 = b.z;
            const Z = b.w;
            const beta = c.x;

            const phR = kappa.mul(t).add(alpha);
            const R = R_g.add(X.mul(cos(phR)));
            const gamma = Omega_g.mul(2.0).div(kappa.mul(R_g));
            const phi = phi_g0.add(Omega_g.mul(t)).sub(gamma.mul(X).mul(sin(phR)));
            const z = Z.mul(cos(nu.mul(t).add(beta)));
            return vec3(R.mul(cos(phi)), R.mul(sin(phi)), z);
        });

        material.positionNode = epicyclicPosition();
    }

    const points = new THREE.Points(geometry, material);
    points.frustumCulled = false;
    return points;
}

// ---------------------------------------------------------------------------
// Deep-space backdrop: nebula gradient + faint static starfield
// ---------------------------------------------------------------------------
function buildNebula() {
    const geo = new THREE.SphereGeometry(700, 48, 32);
    const mat = new THREE.MeshBasicNodeMaterial({
        side: THREE.BackSide,
        depthWrite: false,
        depthTest: false,
    });

    const dir = normalize(positionLocal);
    const band = float(1.0).sub(dir.y.abs());               // brighter toward disk plane
    const swirl = sin(dir.x.mul(7.0)).mul(sin(dir.z.mul(5.0))).mul(0.5).add(0.5);

    const deep = color(0x04050d);
    const mid = color(0x0a0a1e);
    const warm = color(0x160a1c);
    let neb = mix(deep, mid, band);
    neb = mix(neb, warm, swirl.mul(band).mul(0.6));
    mat.colorNode = neb;
    mat.toneMapped = false;

    return new THREE.Mesh(geo, mat);
}

function buildBackgroundStars(seed = 7) {
    const count = 2200;
    const pos = new Float32Array(count * 3);
    let s = seed;
    const rand = () => {
        s = (s * 1103515245 + 12345) & 0x7fffffff;
        return s / 0x7fffffff;
    };
    for (let i = 0; i < count; i++) {
        const u = rand() * 2 - 1;
        const theta = rand() * Math.PI * 2;
        const r = 520 + rand() * 120;
        const sq = Math.sqrt(1 - u * u);
        pos[i * 3 + 0] = r * sq * Math.cos(theta);
        pos[i * 3 + 1] = r * u;
        pos[i * 3 + 2] = r * sq * Math.sin(theta);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsNodeMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        sizeAttenuation: false,
    });
    mat.colorNode = color(0x334066).mul(0.9);
    mat.sizeNode = float(1.2);
    const pts = new THREE.Points(geo, mat);
    pts.frustumCulled = false;
    return pts;
}

// ---------------------------------------------------------------------------
// Disasters: expanding shockwave rings with per-type glow
// ---------------------------------------------------------------------------
function buildDisasterPool() {
    const pool = [];
    const ringGeo = new THREE.RingGeometry(0.82, 1.0, 64);
    for (let i = 0; i < DISASTER_POOL_SIZE; i++) {
        const uColor = uniform(new THREE.Color(0xffffff));
        const uOpacity = uniform(0.0);
        const mat = new THREE.MeshBasicNodeMaterial({
            transparent: true,
            depthWrite: false,
            side: THREE.DoubleSide,
            blending: THREE.AdditiveBlending,
        });
        mat.colorNode = uColor.mul(2.4);
        mat.opacityNode = uOpacity;
        mat.toneMapped = false;
        const ring = new THREE.Mesh(ringGeo, mat);
        ring.visible = false;
        ring.userData = { uColor, uOpacity };
        pool.push(ring);
    }
    return pool;
}

function collectDisasterEvents(animationData) {
    const events = [];
    if (!animationData || !animationData.frames) return events;
    for (const frame of animationData.frames) {
        const t = frame.time_myr !== undefined ? frame.time_myr : (frame.time || 0) * 1000;
        const hazards = frame.hazards || [];
        for (const h of hazards) {
            const p = h.position || [0, 0, 0];
            events.push({ t, pos: p, kind: classifyDisaster(h.type) });
        }
    }
    return events;
}

function updateDisasters() {
    let slot = 0;
    const maxR = disasterState.exaggeratedScale
        ? DISASTER_MAX_RADIUS_KPC * (disasterState.scaleMultiplier / 20.0)
        : DISASTER_MAX_RADIUS_KPC;
    for (const ev of disasterEvents) {
        const age = currentTimeMyr - ev.t;
        if (age < 0 || age > DISASTER_LIFESPAN_MYR) continue;
        if (!kindShown(ev.kind)) continue;
        if (slot >= disasterPool.length) break;

        const ring = disasterPool[slot++];
        const frac = age / DISASTER_LIFESPAN_MYR;
        const radius = 0.15 + easeInOutCubic(frac) * maxR;
        const opacity = Math.pow(1.0 - frac, 1.8);

        ring.visible = true;
        ring.position.set(ev.pos[0] * KPC, ev.pos[1] * KPC, ev.pos[2] * KPC);
        ring.scale.setScalar(radius);
        ring.userData.uColor.value.setHex(DISASTER_COLORS[ev.kind]);
        ring.userData.uOpacity.value = opacity;
    }
    for (let i = slot; i < disasterPool.length; i++) {
        disasterPool[i].visible = false;
    }
}

// ---------------------------------------------------------------------------
// Playback + UI hooks
// ---------------------------------------------------------------------------
function timeToFrac(t) {
    return maxTimeMyr > minTimeMyr ? (t - minTimeMyr) / (maxTimeMyr - minTimeMyr) : 0.0;
}

// Bridge the continuous WebGPU time to the frame-indexed chart system so the
// HR diagram (and other panels) animate as currentTimeMyr advances.
function updateChartFrame() {
    if (!window.updateCharts) return;
    const nFrames = (window.animationData && window.animationData.frames && window.animationData.frames.length)
        || (window.hrData && window.hrData.per_frame && window.hrData.per_frame.length) || 0;
    if (nFrames <= 0) return;
    const idx = Math.max(0, Math.min(nFrames - 1, Math.round(timeToFrac(currentTimeMyr) * (nFrames - 1))));
    if (idx !== lastChartFrame) {
        lastChartFrame = idx;
        window.updateCharts(idx);
    }
}

// ---------------------------------------------------------------------------
// Camera modes (orbit / follow / fly / tour) — ported to the WebGPU camera.
// The WebGL camera.js drives a hidden camera; these operate on the module's
// own `camera`/`controls`. Positions are in kpc scene units (KPC = 1.0), the
// same frame as animationData civilization positions.
// ---------------------------------------------------------------------------
let cameraMode = 'orbit';
let autoRotate = true;
let glide = null; // { fromPos, toPos, fromTgt, toTgt, t, dur } — TWEEN-free preset glide

let followCivId = null;
let followTarget = null;
const followOffset = new THREE.Vector3(5.0, 5.0, 5.0);
const followLerp = 0.05;
let autoFollow = true;

const flyKeys = { forward: false, backward: false, left: false, right: false, up: false, down: false, boost: false };
const flyEuler = new THREE.Euler(0, 0, 0, 'YXZ');
const flyMoveSpeed = 0.5;
const flyBoost = 3.0;
let flyMouseAttached = false;
let flyHintTimeout = null;

let tourCurve = null;
let tourTargetCurve = null;
let tourProgress = 0.0;
let tourPlaying = false;
let tourDuration = 20.0;
let tourName = '';

let frameTimesMyr = null;

function getFrameTimes() {
    if (frameTimesMyr) return frameTimesMyr;
    const frames = (window.animationData && window.animationData.frames) || [];
    if (!frames.length) return null;
    frameTimesMyr = frames.map((f) => (f.time_myr !== undefined ? f.time_myr : (f.time || 0) * 1000));
    return frameTimesMyr;
}

function frameIndexForTime() {
    const times = getFrameTimes();
    if (!times) return -1;
    const { i, j, alpha } = bracketForTime(times, currentTimeMyr);
    return alpha >= 0.5 ? j : i;
}

function currentFrameCivs() {
    const idx = frameIndexForTime();
    if (idx < 0) return [];
    const f = window.animationData.frames[idx];
    return (f && f.civilizations) ? f.civilizations : [];
}

function applyCameraMode(mode) {
    cameraMode = mode;
    const sel = document.getElementById('camera-mode-select');
    if (sel && sel.value !== mode) sel.value = mode;
    const followC = document.getElementById('follow-controls');
    const tourC = document.getElementById('tour-controls');
    if (followC) followC.style.display = mode === 'follow' ? 'flex' : 'none';
    if (tourC) tourC.style.display = mode === 'tour' ? 'flex' : 'none';

    if (mode === 'fly') {
        controls.enabled = false;
        controls.autoRotate = false;
        flyEuler.setFromQuaternion(camera.quaternion);
        attachFlyMouse();
        showFlyHint();
    } else if (mode === 'tour') {
        controls.enabled = false;
        controls.autoRotate = false;
        detachFlyMouse();
        hideFlyHint();
    } else if (mode === 'follow') {
        controls.enabled = true;
        controls.autoRotate = false;
        detachFlyMouse();
        hideFlyHint();
        updateFollowTargetList();
    } else {
        controls.enabled = true;
        controls.autoRotate = autoRotate;
        detachFlyMouse();
        hideFlyHint();
        glide = null;
    }
}

function transitionTo(pos, target, dur) {
    applyCameraMode('orbit');
    autoRotate = false;
    controls.autoRotate = false;
    const arBtn = document.getElementById('btn-cam-autorotate');
    if (arBtn) arBtn.classList.remove('active');
    glide = {
        fromPos: camera.position.clone(),
        toPos: new THREE.Vector3(pos[0], pos[1], pos[2]),
        fromTgt: controls.target.clone(),
        toTgt: new THREE.Vector3(target[0], target[1], target[2]),
        t: 0.0,
        dur: Math.max(0.2, dur || 2.0),
    };
}

function updateFollowTargetList() {
    const sel = document.getElementById('follow-target-select');
    if (!sel) return;
    const active = currentFrameCivs().filter((c) => c.is_active);
    sel.innerHTML = '';
    if (!active.length) {
        const o = document.createElement('option');
        o.value = '';
        o.textContent = autoFollow ? '⏳ Auto-follow: waiting...' : 'No civilizations yet';
        o.disabled = true;
        o.selected = true;
        sel.appendChild(o);
        return;
    }
    const def = document.createElement('option');
    def.value = '';
    def.textContent = 'Select civilization...';
    sel.appendChild(def);
    active.slice().sort((a, b) => b.kardashev - a.kardashev).forEach((c) => {
        const o = document.createElement('option');
        o.value = c.civ_id;
        o.textContent = `Civ ${c.civ_id} (K${c.kardashev.toFixed(2)})`;
        if (c.civ_id === followCivId) o.selected = true;
        sel.appendChild(o);
    });
}

function updateFollow() {
    const civs = currentFrameCivs();
    const active = civs.filter((c) => c.is_active);
    if (followCivId != null) {
        const civ = civs.find((c) => c.civ_id === followCivId);
        if (!civ || !civ.is_active) {
            if (autoFollow && active.length) {
                followCivId = active.slice().sort((a, b) => b.kardashev - a.kardashev)[0].civ_id;
                followTarget = null;
                updateFollowTargetList();
            } else {
                followCivId = null;
                followTarget = null;
            }
            return;
        }
        const tp = new THREE.Vector3(civ.position[0], civ.position[1], civ.position[2]);
        if (!followTarget) followTarget = tp.clone();
        else followTarget.lerp(tp, followLerp);
        controls.target.lerp(followTarget, followLerp);
        const desired = followTarget.clone().add(followOffset);
        camera.position.lerp(desired, followLerp * 0.5);
    } else if (autoFollow && active.length) {
        followCivId = active.slice().sort((a, b) => b.kardashev - a.kardashev)[0].civ_id;
        followTarget = null;
        updateFollowTargetList();
    }
}

function attachFlyMouse() {
    if (flyMouseAttached) return;
    document.addEventListener('mousemove', onFlyMouseMove);
    document.body.style.cursor = 'crosshair';
    flyMouseAttached = true;
}

function detachFlyMouse() {
    if (!flyMouseAttached) return;
    document.removeEventListener('mousemove', onFlyMouseMove);
    document.body.style.cursor = 'default';
    flyMouseAttached = false;
}

function onFlyMouseMove(e) {
    if (cameraMode !== 'fly') return;
    flyEuler.y -= (e.movementX || 0) * 0.002;
    flyEuler.x -= (e.movementY || 0) * 0.002;
    flyEuler.x = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, flyEuler.x));
    camera.quaternion.setFromEuler(flyEuler);
}

function updateFly(dt) {
    const speed = flyMoveSpeed * (flyKeys.boost ? flyBoost : 1.0) * dt * 60;
    const dir = new THREE.Vector3();
    camera.getWorldDirection(dir);
    const right = new THREE.Vector3().crossVectors(dir, camera.up).normalize();
    if (flyKeys.forward) camera.position.addScaledVector(dir, speed);
    if (flyKeys.backward) camera.position.addScaledVector(dir, -speed);
    if (flyKeys.left) camera.position.addScaledVector(right, -speed);
    if (flyKeys.right) camera.position.addScaledVector(right, speed);
    if (flyKeys.up) camera.position.y += speed;
    if (flyKeys.down) camera.position.y -= speed;
    controls.target.copy(camera.position).addScaledVector(dir, 10);
}

function showFlyHint() {
    const h = document.getElementById('fly-mode-hint');
    if (!h) return;
    if (flyHintTimeout) clearTimeout(flyHintTimeout);
    h.classList.remove('fading');
    h.style.display = 'block';
    flyHintTimeout = setTimeout(() => {
        h.classList.add('fading');
        setTimeout(() => {
            if (h.classList.contains('fading')) h.style.display = 'none';
        }, 500);
    }, 3000);
}

function hideFlyHint() {
    const h = document.getElementById('fly-mode-hint');
    if (!h) return;
    if (flyHintTimeout) {
        clearTimeout(flyHintTimeout);
        flyHintTimeout = null;
    }
    h.classList.remove('fading');
    h.style.display = 'none';
}

function startTour(key) {
    const tours = window.cameraTours || {};
    const tour = tours[key];
    if (!tour) return;
    applyCameraMode('tour');
    tourName = tour.name;
    tourDuration = tour.duration || 20.0;
    tourProgress = 0.0;
    tourPlaying = true;
    const P = tour.keyframes.map((k) => new THREE.Vector3(k.position[0], k.position[1], k.position[2]));
    const T = tour.keyframes.map((k) => new THREE.Vector3(k.target[0], k.target[1], k.target[2]));
    tourCurve = new THREE.CatmullRomCurve3(P, false, 'centripetal', 0.5);
    tourTargetCurve = new THREE.CatmullRomCurve3(T, false, 'centripetal', 0.5);
    updateTourUI();
}

function stopTour() {
    tourPlaying = false;
    tourCurve = null;
    tourTargetCurve = null;
    tourProgress = 0.0;
    const ts = document.getElementById('tour-select');
    if (ts) ts.value = '';
    updateTourUI();
}

function updateTour(dt) {
    if (!tourPlaying || !tourCurve) return;
    tourProgress += dt / tourDuration;
    if (tourProgress >= 1.0) tourProgress = 0.0;
    camera.position.copy(tourCurve.getPointAt(tourProgress));
    const t = tourTargetCurve.getPointAt(tourProgress);
    camera.lookAt(t);
    controls.target.copy(t);
    updateTourUI();
}

function updateTourUI() {
    const pb = document.getElementById('btn-tour-play');
    if (pb) pb.textContent = tourPlaying ? '⏸' : '▶';
    const prog = document.getElementById('tour-progress');
    if (prog) prog.style.width = (tourProgress * 100) + '%';
    const nm = document.getElementById('tour-name');
    if (nm) nm.textContent = tourName || '';
}

function onCamKeyDown(e) {
    if (cameraMode === 'fly') {
        switch (e.key.toLowerCase()) {
            case 'w': flyKeys.forward = true; break;
            case 's': flyKeys.backward = true; break;
            case 'a': flyKeys.left = true; break;
            case 'd': flyKeys.right = true; break;
            case 'q': flyKeys.down = true; break;
            case 'e': flyKeys.up = true; break;
            case 'shift': flyKeys.boost = true; break;
            case 'h': showFlyHint(); break;
            case 'escape':
            case 'f': applyCameraMode('orbit'); break;
        }
        if (['w', 's', 'a', 'd', 'q', 'e'].includes(e.key.toLowerCase())) e.preventDefault();
        return;
    }
    if (e.key === 'f' || e.key === 'F') {
        applyCameraMode('fly');
    } else if (e.key === 'Escape') {
        if (cameraMode === 'tour') stopTour();
        if (cameraMode !== 'orbit') applyCameraMode('orbit');
    }
}

function onCamKeyUp(e) {
    if (cameraMode !== 'fly') return;
    switch (e.key.toLowerCase()) {
        case 'w': flyKeys.forward = false; break;
        case 's': flyKeys.backward = false; break;
        case 'a': flyKeys.left = false; break;
        case 'd': flyKeys.right = false; break;
        case 'q': flyKeys.down = false; break;
        case 'e': flyKeys.up = false; break;
        case 'shift': flyKeys.boost = false; break;
    }
}

function updateCameraSystem(dt) {
    if (glide) {
        glide.t += dt;
        const k = Math.min(glide.t / glide.dur, 1.0);
        const e = easeInOutCubic(k);
        camera.position.lerpVectors(glide.fromPos, glide.toPos, e);
        controls.target.lerpVectors(glide.fromTgt, glide.toTgt, e);
        if (k >= 1.0) glide = null;
    }
    if (cameraMode === 'fly') updateFly(dt);
    else if (cameraMode === 'tour') updateTour(dt);
    else if (cameraMode === 'follow') updateFollow();

    if (cameraMode === 'orbit' || cameraMode === 'follow') controls.update();
}

function wireCameraUI() {
    const modeSel = document.getElementById('camera-mode-select');
    if (modeSel) modeSel.addEventListener('change', (e) => applyCameraMode(e.target.value));

    const followSel = document.getElementById('follow-target-select');
    if (followSel) {
        followSel.addEventListener('change', (e) => {
            if (e.target.value !== '') {
                followCivId = parseInt(e.target.value, 10);
                followTarget = null;
            }
        });
    }

    const tourSel = document.getElementById('tour-select');
    if (tourSel) {
        const tours = window.cameraTours || {};
        Object.keys(tours).forEach((key) => {
            const o = document.createElement('option');
            o.value = key;
            o.textContent = tours[key].name;
            tourSel.appendChild(o);
        });
        tourSel.addEventListener('change', (e) => {
            if (e.target.value) startTour(e.target.value);
        });
    }
    const tourPlay = document.getElementById('btn-tour-play');
    if (tourPlay) {
        tourPlay.addEventListener('click', () => {
            if (tourCurve) {
                tourPlaying = !tourPlaying;
                updateTourUI();
            }
        });
    }
    const tourStopBtn = document.getElementById('btn-tour-stop');
    if (tourStopBtn) {
        tourStopBtn.addEventListener('click', () => {
            stopTour();
            applyCameraMode('orbit');
        });
    }

    const presets = window.cameraPresets || [
        { position: [0, 0, 40], target: [0, 0, 0], duration: 2.0 },
        { position: [30, 0, 0], target: [0, 0, 0], duration: 2.0 },
        { position: [25, 25, 15], target: [0, 0, 0], duration: 2.5 },
    ];
    const wirePreset = (id, i) => {
        const b = document.getElementById(id);
        if (b && presets[i]) {
            b.addEventListener('click', () => transitionTo(presets[i].position, presets[i].target, presets[i].duration));
        }
    };
    wirePreset('btn-cam-top', 0);
    wirePreset('btn-cam-edge', 1);
    wirePreset('btn-cam-angle', 2);

    const arBtn = document.getElementById('btn-cam-autorotate');
    if (arBtn) {
        arBtn.classList.toggle('active', autoRotate);
        arBtn.addEventListener('click', () => {
            autoRotate = !autoRotate;
            if (cameraMode === 'orbit') controls.autoRotate = autoRotate;
            arBtn.classList.toggle('active', autoRotate);
        });
    }

    window.addEventListener('keydown', onCamKeyDown);
    window.addEventListener('keyup', onCamKeyUp);
}

// ---------------------------------------------------------------------------
// Dynamic per-frame layers (civilizations, probes, hazard markers,
// trajectories) — ported from the WebGL particles.js so the WebGPU scene has
// parity. Rebuilt only when the frame index changes; toggled via the layer
// buttons. Rendered as additive emissive spheres/lines (MeshBasicNodeMaterial /
// LineBasicNodeMaterial) so they participate in the bloom pass like the stars.
// ---------------------------------------------------------------------------
let civGroup = null;
let probeGroup = null;
let hazardGroup = null;
let trajGroup = null;
let showStars = true;
let showCivs = true;
let showProbes = true;
let showHazards = true;
let showTrajectories = true;
let usePostProcessing = true;
let lastLayerFrame = -1;

const VIRIDIS = [0x440154, 0x3b528b, 0x21918c, 0x5ec962, 0xfde725];
const HAZARD_MARKER_COLORS = { supernova: 0xff4444, grb: 0xffaa00, ns_merger: 0xaa44ff };

function kardashevColorHex(k) {
    const cfg = window.config || {};
    const minK = cfg.kardashev_min || 0.7;
    const maxK = cfg.kardashev_max || 3.0;
    const n = Math.max(0, Math.min(1, (k - minK) / (maxK - minK)));
    return VIRIDIS[Math.min(VIRIDIS.length - 1, Math.floor(n * (VIRIDIS.length - 1e-6)))];
}

function emissiveSphere(radius, hex, opacity) {
    const geo = new THREE.SphereGeometry(radius, 12, 12);
    const mat = new THREE.MeshBasicNodeMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
    });
    mat.colorNode = color(hex).mul(1.8);
    mat.opacityNode = float(opacity);
    mat.toneMapped = false;
    return new THREE.Mesh(geo, mat);
}

function clearGroup(g) {
    if (!g) return;
    for (let i = g.children.length - 1; i >= 0; i--) {
        const c = g.children[i];
        g.remove(c);
        if (c.geometry) c.geometry.dispose();
        if (c.material) c.material.dispose();
    }
}

function buildDynamicLayers() {
    civGroup = new THREE.Group();
    probeGroup = new THREE.Group();
    hazardGroup = new THREE.Group();
    trajGroup = new THREE.Group();
    scene.add(civGroup, probeGroup, hazardGroup, trajGroup);
    buildTrajectoryObjects();
}

function buildTrajectoryObjects() {
    const unionList = (window.animationData && window.animationData.trajectories) || [];
    for (const traj of unionList) {
        if (!traj.start || !traj.end) continue;
        const timeMyr = traj.time_myr || 0;
        const civId = traj.civ_id || 0;
        const hex = new THREE.Color().setHSL((civId * 0.618033988749895) % 1.0, 1.0, 0.65).getHex();
        const geo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(traj.start[0], traj.start[1], traj.start[2]),
            new THREE.Vector3(traj.end[0], traj.end[1], traj.end[2]),
        ]);
        const mat = new THREE.LineBasicNodeMaterial({
            transparent: true,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
        });
        mat.colorNode = color(hex).mul(1.5);
        mat.opacityNode = float(0.9);
        mat.toneMapped = false;
        const line = new THREE.Line(geo, mat);
        line.visible = false;
        line.userData.timeMyr = timeMyr;
        trajGroup.add(line);
        const end = emissiveSphere(0.03, hex, 0.95);
        end.position.set(traj.end[0], traj.end[1], traj.end[2]);
        end.visible = false;
        end.userData.timeMyr = timeMyr;
        trajGroup.add(end);
    }
}

const civPool = new Map();
const probePool = new Map();

function _disposePooled(group, pool, id) {
    const m = pool.get(id);
    if (!m) return;
    group.remove(m);
    if (m.geometry) m.geometry.dispose();
    if (m.material) m.material.dispose();
    pool.delete(id);
}

function syncCivPool(frame) {
    const cfg = window.config || {};
    const present = new Set();
    for (const civ of frame.civilizations || []) {
        const id = civ.civ_id;
        present.add(id);
        const active = civ.is_active;
        const hex = kardashevColorHex(civ.kardashev);
        const stateKey = hex + '|' + (active ? 'a' : 'x');
        let m = civPool.get(id);
        if (m && m.userData.stateKey !== stateKey) {
            _disposePooled(civGroup, civPool, id);
            m = null;
        }
        if (!m) {
            const r = active ? cfg.civ_active_size || 0.15 : cfg.civ_extinct_size || 0.1;
            const op = active ? cfg.civ_active_opacity || 0.9 : cfg.civ_extinct_opacity || 0.5;
            m = emissiveSphere(r, hex, op);
            m.userData.stateKey = stateKey;
            m.position.set(civ.position[0], civ.position[1], civ.position[2]);
            civPool.set(id, m);
            civGroup.add(m);
        }
    }
    for (const [id, m] of civPool) m.visible = present.has(id);
    civGroup.visible = showCivs;
}

function syncProbePool(frame) {
    const present = new Set();
    for (const p of frame.probes || []) {
        present.add(p.probe_id);
        if (!probePool.has(p.probe_id)) {
            const m = emissiveSphere(0.05, 0x00ffff, 0.9);
            m.position.set(p.position[0], p.position[1], p.position[2]);
            probePool.set(p.probe_id, m);
            probeGroup.add(m);
        }
    }
    for (const id of [...probePool.keys()]) {
        if (!present.has(id)) _disposePooled(probeGroup, probePool, id);
    }
    probeGroup.visible = showProbes;
}

function rebuildHazards(frame) {
    clearGroup(hazardGroup);
    const cfg = window.config || {};
    for (const h of frame.hazards || []) {
        const kind = classifyDisaster(h.type);
        if (!kindShown(kind)) continue;
        const m = emissiveSphere(
            cfg.hazard_marker_size || 0.3,
            HAZARD_MARKER_COLORS[kind] || 0xff0000,
            cfg.hazard_opacity || 0.7,
        );
        const pos = h.position || [0, 0, 0];
        m.position.set(pos[0], pos[1], pos[2]);
        hazardGroup.add(m);
    }
    hazardGroup.visible = showHazards;
}

function updateTrajectoryVisibility(tMyr) {
    for (const child of trajGroup.children) {
        child.visible = child.userData.timeMyr <= tMyr;
    }
    trajGroup.visible = showTrajectories;
}

function updateDynamicLayers(frameIdx) {
    if (!window.animationData || !window.animationData.frames) return;
    const frame = window.animationData.frames[frameIdx];
    if (!frame) return;
    syncCivPool(frame);
    syncProbePool(frame);
    rebuildHazards(frame);
}

function updateLayerFrame() {
    const fi = frameIndexForTime();
    if (fi >= 0 && fi !== lastLayerFrame) {
        lastLayerFrame = fi;
        updateDynamicLayers(fi);
    }
}

let lastInterpTimeMyr = null;
let interpCache = { i: -1, j: -1, civsJ: null, probesJ: null };

function updateLayerInterpolation(tMyr) {
    if (tMyr === lastInterpTimeMyr) return;
    const times = getFrameTimes();
    if (!times) return;
    lastInterpTimeMyr = tMyr;
    const { i, j, alpha } = bracketForTime(times, tMyr);
    if (i < 0) return;
    const frames = window.animationData.frames;
    if (interpCache.i !== i || interpCache.j !== j) {
        const civsJ = new Map();
        for (const c of frames[j].civilizations || []) civsJ.set(c.civ_id, c);
        const probesJ = new Map();
        for (const p of frames[j].probes || []) probesJ.set(p.probe_id, p);
        interpCache = { i, j, civsJ, probesJ };
    }
    for (const civ of frames[i].civilizations || []) {
        const m = civPool.get(civ.civ_id);
        if (!m) continue;
        const next = interpCache.civsJ.get(civ.civ_id);
        const p = next ? lerp3(civ.position, next.position, alpha) : civ.position;
        m.position.set(p[0], p[1], p[2]);
    }
    for (const probe of frames[i].probes || []) {
        const m = probePool.get(probe.probe_id);
        if (!m) continue;
        const next = interpCache.probesJ.get(probe.probe_id);
        const p = next ? lerp3(probe.position, next.position, alpha) : probe.position;
        m.position.set(p[0], p[1], p[2]);
    }
    updateTrajectoryVisibility(tMyr);
}

function wireLayerUI() {
    const toggle = (id, get, set, apply) => {
        const b = document.getElementById(id);
        if (!b) return;
        b.classList.toggle('active', get());
        b.addEventListener('click', (e) => {
            set(!get());
            e.target.classList.toggle('active', get());
            apply();
        });
    };
    toggle('btn-stars', () => showStars, (v) => (showStars = v), () => {
        if (starPoints) starPoints.visible = showStars;
    });
    toggle('btn-civs', () => showCivs, (v) => (showCivs = v), () => {
        if (civGroup) civGroup.visible = showCivs;
    });
    toggle('btn-probes', () => showProbes, (v) => (showProbes = v), () => {
        if (probeGroup) probeGroup.visible = showProbes;
    });
    toggle('btn-hazards', () => showHazards, (v) => (showHazards = v), () => {
        if (hazardGroup) hazardGroup.visible = showHazards;
    });
    toggle('btn-trajectories', () => showTrajectories, (v) => (showTrajectories = v), () => {
        if (trajGroup) trajGroup.visible = showTrajectories;
    });
    toggle('btn-postprocess', () => usePostProcessing, (v) => (usePostProcessing = v), () => {});
}

// ---------------------------------------------------------------------------
// Disaster sub-layers (sterilization zones / GRB beam cones / death markers)
// + panel controls (type filters, history, scale) + timeline — ported from the
// WebGL layers.js. Driven by an aggregated disaster list (window.allDisasters),
// times in Gyr to match the WebGL data. Pools of node-material meshes with
// per-mesh uColor/uOpacity uniforms, mirroring the shockwave ring pool.
// ---------------------------------------------------------------------------
const ZONE_POOL_SIZE = 64;
const BEAM_POOL_SIZE = 64;
const DEATH_POOL_SIZE = 64;

const disasterState = {
    showHistory: false,
    exaggeratedScale: false,
    showSupernovae: true,
    showGRBs: true,
    showNSMergers: true,
    showZones: true,
    showBeams: true,
    showDeathMarkers: true,
    scaleMultiplier: 50.0,
};

let allDisasters = [];
let zonePool = [];
let beamPool = [];
let deathPool = [];

function hexForKind(kind) {
    return DISASTER_COLORS[kind] !== undefined ? DISASTER_COLORS[kind] : 0xff0000;
}

function kindShown(kind) {
    if (kind === 'supernova') return disasterState.showSupernovae;
    if (kind === 'grb') return disasterState.showGRBs;
    if (kind === 'ns_merger') return disasterState.showNSMergers;
    return true;
}

function scaledRadius(radiusKpc, energy) {
    if (disasterState.exaggeratedScale) {
        const ef = Math.log10(energy || 1e51) / 51;
        return radiusKpc * disasterState.scaleMultiplier * ef;
    }
    return radiusKpc;
}

function buildAllDisasters() {
    const list = [];
    const frames = (window.animationData && window.animationData.frames) || [];
    for (const f of frames) {
        const t = f.time_myr !== undefined ? f.time_myr / 1000.0 : f.time || 0;
        for (const h of f.hazards || []) {
            list.push({
                time: h.time !== undefined ? h.time : t,
                type: h.type,
                kind: classifyDisaster(h.type),
                position: h.position || [0, 0, 0],
                lethal_radius: h.lethal_radius || 0.01,
                sterilization_radius: h.sterilization_radius || h.lethal_radius || 0.03,
                energy: h.energy || 1e51,
                jet_theta: h.jet_theta,
                jet_phi: h.jet_phi,
                affected_civs: h.affected_civs || [],
            });
        }
    }
    const seen = new Set();
    allDisasters = list
        .filter((d) => {
            const k = `${(d.time || 0).toFixed(3)}_${d.type}`;
            if (seen.has(k)) return false;
            seen.add(k);
            return true;
        })
        .sort((a, b) => a.time - b.time);
    window.allDisasters = allDisasters;
    updateDisasterCount();
}

function updateDisasterCount() {
    const el = document.getElementById('disaster-count');
    if (!el) return;
    const sn = allDisasters.filter((d) => d.kind === 'supernova').length;
    const grb = allDisasters.filter((d) => d.kind === 'grb').length;
    const nsm = allDisasters.filter((d) => d.kind === 'ns_merger').length;
    el.innerHTML =
        `<span style="color:#ff4400;">SN: ${sn}</span> | ` +
        `<span style="color:#00ffff;">GRB: ${grb}</span> | ` +
        `<span style="color:#ff00ff;">NSM: ${nsm}</span>`;
}

function makePooledMesh(geo, side, additive) {
    const uColor = uniform(new THREE.Color(0xffffff));
    const uOpacity = uniform(0.0);
    const mat = new THREE.MeshBasicNodeMaterial({
        transparent: true,
        depthWrite: false,
        side,
        blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    });
    mat.colorNode = additive ? uColor.mul(2.0) : uColor;
    mat.opacityNode = uOpacity;
    mat.toneMapped = false;
    const mesh = new THREE.Mesh(geo, mat);
    mesh.visible = false;
    mesh.userData = { uColor, uOpacity };
    return mesh;
}

function buildDeathMarkerGeo() {
    const s = 0.15;
    const shape = new THREE.Shape();
    shape.moveTo(-s, -s * 0.2);
    shape.lineTo(-s * 0.2, -s);
    shape.lineTo(0, -s * 0.4);
    shape.lineTo(s * 0.2, -s);
    shape.lineTo(s, -s * 0.2);
    shape.lineTo(s * 0.4, 0);
    shape.lineTo(s, s * 0.2);
    shape.lineTo(s * 0.2, s);
    shape.lineTo(0, s * 0.4);
    shape.lineTo(-s * 0.2, s);
    shape.lineTo(-s, s * 0.2);
    shape.lineTo(-s * 0.4, 0);
    shape.closePath();
    return new THREE.ShapeGeometry(shape);
}

function buildDisasterSublayers() {
    const zoneGeo = new THREE.SphereGeometry(1, 16, 12);
    for (let i = 0; i < ZONE_POOL_SIZE; i++) {
        const m = makePooledMesh(zoneGeo, THREE.BackSide, false);
        scene.add(m);
        zonePool.push(m);
    }
    const beamGeo = new THREE.ConeGeometry(0.5, 2, 16, 1, true);
    for (let i = 0; i < BEAM_POOL_SIZE; i++) {
        const m = makePooledMesh(beamGeo, THREE.DoubleSide, false);
        scene.add(m);
        beamPool.push(m);
    }
    const deathGeo = buildDeathMarkerGeo();
    for (let i = 0; i < DEATH_POOL_SIZE; i++) {
        const m = makePooledMesh(deathGeo, THREE.DoubleSide, false);
        scene.add(m);
        deathPool.push(m);
    }
}

function updateZones(vis, currentTime) {
    const cfg = window.config || {};
    const fadeTime = (cfg.disaster_fade_time_myr || 200) / 1000.0;
    let slot = 0;
    if (disasterState.showZones) {
        for (const d of vis) {
            if (slot >= zonePool.length) break;
            const el = currentTime - d.time;
            let opacity;
            if (el <= fadeTime) opacity = (1 - (el / fadeTime) * 0.7) * (cfg.sterilization_zone_opacity || 0.25);
            else if (disasterState.showHistory) opacity = 0.1;
            else continue;
            const r = scaledRadius(d.sterilization_radius || d.lethal_radius || 0.03, d.energy);
            const m = zonePool[slot++];
            m.position.set(d.position[0], d.position[1], d.position[2]);
            m.scale.setScalar(r);
            m.userData.uColor.value.setHex(hexForKind(d.kind));
            m.userData.uOpacity.value = Math.max(0.05, opacity);
            m.visible = true;
        }
    }
    for (let i = slot; i < zonePool.length; i++) zonePool[i].visible = false;
}

function updateBeams(vis, currentTime) {
    const cfg = window.config || {};
    const fadeTime = (cfg.beam_fade_time_myr || 100) / 1000.0;
    let slot = 0;
    if (disasterState.showBeams) {
        const jets = vis.filter(
            (d) => (d.kind === 'grb' || d.kind === 'ns_merger') && d.jet_theta !== undefined,
        );
        for (const d of jets) {
            if (slot + 1 >= beamPool.length) break;
            const el = currentTime - d.time;
            let opacity;
            if (el <= fadeTime) opacity = (1 - el / fadeTime) * 0.5;
            else if (disasterState.showHistory) opacity = 0.15;
            else continue;
            const theta = d.jet_theta || 0;
            const phi = d.jet_phi || 0;
            const beamLen =
                d.kind === 'grb' ? scaledRadius(d.lethal_radius || 5.0, d.energy) : scaledRadius(3.0, d.energy);
            const coneR = Math.tan((25 * Math.PI) / 180) * beamLen;
            const dirX = Math.sin(theta) * Math.cos(phi);
            const dirY = Math.sin(theta) * Math.sin(phi);
            const dirZ = Math.cos(theta);
            const [px, py, pz] = d.position;
            const hex = hexForKind(d.kind);
            for (const sgn of [1, -1]) {
                const m = beamPool[slot++];
                m.position.set(px, py, pz);
                m.scale.set(coneR, beamLen, coneR);
                m.userData.uColor.value.setHex(hex);
                m.userData.uOpacity.value = opacity;
                m.lookAt(px + sgn * dirX, py + sgn * dirY, pz + sgn * dirZ);
                m.rotateX(Math.PI / 2);
                m.visible = true;
            }
        }
    }
    for (let i = slot; i < beamPool.length; i++) beamPool[i].visible = false;
}

function updateDeaths(vis, currentTime) {
    const cfg = window.config || {};
    const fadeTime = (cfg.death_marker_fade_myr || 500) / 1000.0;
    let slot = 0;
    if (disasterState.showDeathMarkers) {
        const deadly = vis.filter((d) => d.affected_civs && d.affected_civs.length > 0);
        for (const d of deadly) {
            if (slot >= deathPool.length) break;
            const el = currentTime - d.time;
            if (el < 0 || el > fadeTime) continue;
            const progress = el / fadeTime;
            const m = deathPool[slot++];
            m.position.set(d.position[0], d.position[1], d.position[2] + 0.1);
            m.scale.setScalar(0.3 + progress * 0.2);
            m.userData.uColor.value.setHex(0xff0000);
            m.userData.uOpacity.value = (1 - progress * 0.5) * 0.9;
            if (camera) m.quaternion.copy(camera.quaternion);
            m.visible = true;
        }
    }
    for (let i = slot; i < deathPool.length; i++) deathPool[i].visible = false;
}

function drawDisasterTimeline(currentTime) {
    const canvas = document.getElementById('disaster-timeline-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, W, H);
    const tmin = minTimeMyr / 1000.0;
    const tmax = maxTimeMyr / 1000.0;
    const span = Math.max(1e-6, tmax - tmin);
    for (const d of allDisasters) {
        if (!kindShown(d.kind)) continue;
        const x = ((d.time - tmin) / span) * W;
        ctx.fillStyle = '#' + hexForKind(d.kind).toString(16).padStart(6, '0');
        ctx.fillRect(x - 1, 2, 2, H - 4);
    }
    const px = ((currentTime - tmin) / span) * W;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(px - 1, 0, 2, H);
}

function updateDisasterSublayers() {
    if (!zonePool.length) return;
    const currentTime = currentTimeMyr / 1000.0;
    const vis = allDisasters.filter((d) => {
        if (!kindShown(d.kind)) return false;
        const el = currentTime - d.time;
        if (el < 0) return false;
        if (disasterState.showHistory) return true;
        return el <= 0.1;
    });
    updateZones(vis, currentTime);
    updateBeams(vis, currentTime);
    updateDeaths(vis, currentTime);
    drawDisasterTimeline(currentTime);
}

function wireDisasterUI() {
    const chk = (id, fn) => {
        const e = document.getElementById(id);
        if (e) e.addEventListener('change', () => fn(e.checked));
    };
    chk('disaster-history-toggle', (v) => {
        disasterState.showHistory = v;
        const l = document.getElementById('history-mode-label');
        if (l) l.textContent = v ? 'Show History' : 'Current Only';
    });
    chk('disaster-scale-toggle', (v) => {
        disasterState.exaggeratedScale = v;
        const l = document.getElementById('scale-mode-label');
        if (l) l.textContent = v ? 'Exaggerated (50x)' : 'Physical Scale';
    });
    const refilter = () => {
        if (lastLayerFrame >= 0 && window.animationData) {
            rebuildHazards(window.animationData.frames[lastLayerFrame]);
        }
    };
    chk('filter-supernova', (v) => {
        disasterState.showSupernovae = v;
        refilter();
    });
    chk('filter-grb', (v) => {
        disasterState.showGRBs = v;
        refilter();
    });
    chk('filter-nsm', (v) => {
        disasterState.showNSMergers = v;
        refilter();
    });
    chk('show-zones', (v) => (disasterState.showZones = v));
    chk('show-beams', (v) => (disasterState.showBeams = v));
    chk('show-death-markers', (v) => (disasterState.showDeathMarkers = v));
}

function wireUI() {
    const slider = document.getElementById('timeline-slider');
    const timeDisplay = document.getElementById('time-display');
    const playBtn = document.getElementById('btn-playpause');

    if (slider) {
        slider.addEventListener('input', () => {
            const frac = parseFloat(slider.value) / 100.0;
            currentTimeMyr = minTimeMyr + frac * (maxTimeMyr - minTimeMyr);
            playing = false;
            if (playBtn) playBtn.textContent = '▶ Play';
        });
    }
    if (playBtn) {
        playBtn.addEventListener('click', () => {
            playing = !playing;
            playBtn.textContent = playing ? '⏸ Pause' : '▶ Play';
        });
    }

    window.__wgpuUpdateUI = () => {
        if (slider && document.activeElement !== slider) {
            slider.value = String(timeToFrac(currentTimeMyr) * 100.0);
        }
        if (timeDisplay) {
            timeDisplay.textContent = (currentTimeMyr / 1000.0).toFixed(2) + ' Gyr';
        }
    };

    wireCameraUI();
    wireLayerUI();
    wireDisasterUI();
}

// ---------------------------------------------------------------------------
// Main render loop
// ---------------------------------------------------------------------------
function tick() {
    const dt = clock.getDelta();
    const elapsed = clock.getElapsedTime();

    if (!introDone) {
        const k = Math.min(elapsed / introDuration, 1.0);
        const e = easeInOutCubic(k);
        camera.position.lerpVectors(camStart, camEnd, e);
        camera.lookAt(0, 0, 0);
        if (k >= 1.0) {
            introDone = true;
            controls.enabled = true;
            applyCameraMode(cameraMode);
        }
    } else {
        updateCameraSystem(dt);
    }

    if (playing) {
        currentTimeMyr += dt * playbackMyrPerSec;
        if (currentTimeMyr > maxTimeMyr) currentTimeMyr = minTimeMyr;
    }

    uTime.value = currentTimeMyr;
    updateDisasters();
    updateDisasterSublayers();
    if (window.__wgpuUpdateUI) window.__wgpuUpdateUI();
    updateChartFrame();
    updateLayerFrame();
    updateLayerInterpolation(currentTimeMyr);

    if (usePostProcessing) postProcessing.render();
    else renderer.render(scene, camera);
}

function onResize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------
export async function initWebGPUGalaxy() {
    const galaxyData = window.galaxyData;
    if (!galaxyData) throw new Error('window.galaxyData missing');

    const cfg = window.config || {};
    const container = document.getElementById('canvas-container') || document.body;

    scene = new THREE.Scene();

    const fov = cfg.camera_fov || 70;
    const far = Math.max(cfg.camera_far || 2000, 2000);
    camera = new THREE.PerspectiveCamera(fov, window.innerWidth / window.innerHeight, 0.05, far);
    camera.position.copy(camStart);

    renderer = new THREE.WebGPURenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    container.appendChild(renderer.domElement);

    await renderer.init();

    uTime = uniform(0.0);
    uStarIntensity = uniform(2.6);

    clock = new THREE.Clock();

    // Backdrop
    scene.add(buildNebula());
    scene.add(buildBackgroundStars());

    // Stars (GPU-positioned)
    starPoints = buildStarField(galaxyData);
    if (starPoints) scene.add(starPoints);

    // Disasters
    disasterPool = buildDisasterPool();
    disasterPool.forEach((r) => scene.add(r));
    disasterEvents = collectDisasterEvents(window.animationData);

    // Dynamic per-frame layers (civs, probes, hazard markers, trajectories)
    buildDynamicLayers();

    // Disaster sub-layers (zones / beams / death markers) + aggregated list
    buildDisasterSublayers();
    buildAllDisasters();

    // Time range
    if (window.animationData && window.animationData.frames && window.animationData.frames.length > 0) {
        const frames = window.animationData.frames;
        minTimeMyr = frames[0].time_myr !== undefined ? frames[0].time_myr : (frames[0].time || 0) * 1000;
        maxTimeMyr = frames[frames.length - 1].time_myr !== undefined
            ? frames[frames.length - 1].time_myr
            : (frames[frames.length - 1].time || 0) * 1000;
        if (maxTimeMyr <= minTimeMyr) maxTimeMyr = minTimeMyr + 5000.0;
    } else {
        minTimeMyr = 0.0;
        maxTimeMyr = 5000.0;
    }
    currentTimeMyr = minTimeMyr;

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.autoRotateSpeed = 0.16;
    controls.minDistance = 1.0;
    controls.maxDistance = 400.0;
    controls.enabled = false;
    controls.target.set(0, 0, 0);

    // Selective bloom: threshold keeps the dim nebula/backdrop out; only bright
    // HDR stars and disaster rings glow.
    postProcessing = new THREE.PostProcessing(renderer);
    const scenePass = pass(scene, camera);
    const sceneColor = scenePass.getTextureNode();
    const bloomPass = bloom(sceneColor, 0.85, 0.55, 0.55);
    postProcessing.outputNode = sceneColor.add(bloomPass);

    wireUI();
    window.addEventListener('resize', onResize);

    const loading = document.getElementById('loading-screen');
    if (loading) loading.style.display = 'none';
    const overlay = document.getElementById('ui-overlay');
    if (overlay) overlay.style.display = 'block';

    window.__wgpuActive = true;
    window.__wgpuCameraState = () => ({
        mode: cameraMode,
        introDone,
        autoRotate,
        followCivId,
        pos: camera.position.toArray(),
        target: controls.target.toArray(),
    });
    window.__wgpuInterpState = () => ({
        timeMyr: currentTimeMyr,
        bracket: getFrameTimes() ? bracketForTime(getFrameTimes(), currentTimeMyr) : null,
        civPositions: Object.fromEntries(
            [...civPool].map(([id, m]) => [id, m.position.toArray()]),
        ),
    });
    window.__wgpuLayerState = () => ({
        frame: lastLayerFrame,
        stars: { visible: starPoints ? starPoints.visible : null },
        civs: { visible: civGroup ? civGroup.visible : null, count: civGroup ? civGroup.children.length : 0 },
        probes: { visible: probeGroup ? probeGroup.visible : null, count: probeGroup ? probeGroup.children.length : 0 },
        hazards: { visible: hazardGroup ? hazardGroup.visible : null, count: hazardGroup ? hazardGroup.children.length : 0 },
        traj: { visible: trajGroup ? trajGroup.visible : null, count: trajGroup ? trajGroup.children.length : 0 },
        postProcessing: usePostProcessing,
        disasters: {
            total: allDisasters.length,
            zonesVisible: zonePool.filter((m) => m.visible).length,
            beamsVisible: beamPool.filter((m) => m.visible).length,
            deathsVisible: deathPool.filter((m) => m.visible).length,
            state: { ...disasterState },
        },
    });
    renderer.setAnimationLoop(tick);
}
