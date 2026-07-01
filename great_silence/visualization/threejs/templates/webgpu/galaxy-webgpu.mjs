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
    for (const ev of disasterEvents) {
        const age = currentTimeMyr - ev.t;
        if (age < 0 || age > DISASTER_LIFESPAN_MYR) continue;
        if (slot >= disasterPool.length) break;

        const ring = disasterPool[slot++];
        const frac = age / DISASTER_LIFESPAN_MYR;
        const radius = 0.15 + easeInOutCubic(frac) * DISASTER_MAX_RADIUS_KPC;
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
            controls.autoRotate = true;
        }
    } else {
        controls.update();
    }

    if (playing) {
        currentTimeMyr += dt * playbackMyrPerSec;
        if (currentTimeMyr > maxTimeMyr) currentTimeMyr = minTimeMyr;
    }

    uTime.value = currentTimeMyr;
    updateDisasters();
    if (window.__wgpuUpdateUI) window.__wgpuUpdateUI();
    updateChartFrame();

    postProcessing.render();
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
    renderer.setAnimationLoop(tick);
}
