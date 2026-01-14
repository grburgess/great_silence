

function initParticles() {
    updateParticles();
}

function updateParticles() {
    if (!starPoints) return;

    starGeometry.attributes.position.needsUpdate = true;
    starGeometry.attributes.color.needsUpdate = true;
    starGeometry.attributes.size.needsUpdate = true;
    starGeometry.attributes.brightness.needsUpdate = true;
}

function createCivilizationSprite(civData) {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');

    const kardashev = civData.kardashev;
    const baseColor = getKardashevColor(kardashev);

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
        opacity: civData.is_active ? (window.config.civ_active_opacity || 0.9) : (window.config.civ_extinct_opacity || 0.5),
        blending: THREE.AdditiveBlending
    });

    const sprite = new THREE.Sprite(material);
    sprite.position.set(civData.position[0], civData.position[1], civData.position[2]);
    sprite.scale.set(
        civData.is_active ? (window.config.civ_active_size || 0.15) : (window.config.civ_extinct_size || 0.1),
        civData.is_active ? (window.config.civ_active_size || 0.15) : (window.config.civ_extinct_size || 0.1),
        1
    );
    sprite.userData = civData;

    return sprite;
}

function getKardashevColor(kardashev) {
    const minK = window.config.kardashev_min || 0.7;
    const maxK = window.config.kardashev_max || 3.0;

    const normalized = Math.max(0, Math.min(1, (kardashev - minK) / (maxK - minK)));

    const colorscale = window.config.kardashev_colorscale || 'viridis';

    switch (colorscale) {
        case 'viridis':
            if (normalized < 0.2) return '#440154';
            if (normalized < 0.4) return '#3b528b';
            if (normalized < 0.6) return '#21918c';
            if (normalized < 0.8) return '#5ec962';
            return '#fde725';
        case 'plasma':
            if (normalized < 0.2) return '#0d0887';
            if (normalized < 0.4) return '#7e03a8';
            if (normalized < 0.6) return '#cc4778';
            if (normalized < 0.8) return '#f89540';
            return '#f0f921';
        case 'inferno':
            if (normalized < 0.2) return '#000004';
            if (normalized < 0.4) return '#5a1132';
            if (normalized < 0.6) return '#b5367a';
            if (normalized < 0.8) return '#ef8636';
            return '#fcffa4';
        default:
            if (normalized < 0.5) {
                const r = Math.floor(255 * (1 - normalized * 2));
                const g = Math.floor(255 * normalized * 2);
                return `rgb(${r}, ${g}, 255)`;
            } else {
                const r = Math.floor(255 * (normalized - 0.5) * 2);
                const g = Math.floor(255 * (1 - (normalized - 0.5) * 2));
                return `rgb(255, ${g}, ${255 - r})`;
            }
    }
}

let showCivSprites = true;
let showProbeSprites = true;
let showHazardSprites = true;

function updateCivilizations(civilizations) {
    civSprites.forEach(sprite => scene.remove(sprite));
    civSprites = [];

    const maxAge = Math.max(...civilizations.map(c => c.age), 0.01);
    const downsampleCutoff = maxAge * (downsamplePercent / 100);

    civilizations.forEach(civ => {
        if (downsamplePercent > 0 && civ.age > downsampleCutoff) {
            return;
        }

        const sprite = createCivilizationSprite(civ);
        sprite.visible = showCivSprites;
        civSprites.push(sprite);
        scene.add(sprite);
    });
}

function setCivVisibility(visible) {
    showCivSprites = visible;
    civSprites.forEach(sprite => {
        sprite.visible = visible;
    });
}

function createProbeTrail(probeData) {
    const positions = [];
    const colors = [];

    for (let i = 0; i < 10; i++) {
        const t = i / 9;
        const x = probeData.position[0] * (1 - t);
        const y = probeData.position[1] * (1 - t);
        const z = probeData.position[2] * (1 - t);

        positions.push(x, y, z);
        colors.push(0, 1, 1);
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.LineBasicMaterial({
        vertexColors: true,
        transparent: true,
        opacity: window.config.trajectory_opacity || 0.6,
        linewidth: window.config.trajectory_width || 2.0,
        blending: THREE.AdditiveBlending
    });

    const line = new THREE.Line(geometry, material);
    line.userData = probeData;

    return line;
}

function updateProbes(probes) {
    probeLines.forEach(line => scene.remove(line));
    probeLines = [];

    probes.forEach(probe => {
        const line = createProbeTrail(probe);
        line.visible = showProbeSprites;
        probeLines.push(line);
        scene.add(line);
    });
}

function setProbeVisibility(visible) {
    showProbeSprites = visible;
    probeLines.forEach(line => {
        line.visible = visible;
    });
}

function createHazardMarker(hazardData) {
    const geometry = new THREE.SphereGeometry(
        (window.config.hazard_marker_size || 0.3),
        16,
        16
    );

    let color;
    switch (hazardData.type.toLowerCase()) {
        case 'supernova':
        case 'sn':
            color = window.config.hazard_supernova_color || '#ff4444';
            break;
        case 'grb':
        case 'gamma':
            color = window.config.hazard_grb_color || '#ffaa00';
            break;
        case 'nsm':
        case 'merger':
            color = window.config.hazard_nsm_color || '#aa44ff';
            break;
        default:
            color = '#ff0000';
    }

    const material = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: window.config.hazard_opacity || 0.7,
        blending: THREE.AdditiveBlending
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(hazardData.position[0], hazardData.position[1], hazardData.position[2]);
    mesh.userData = hazardData;

    return mesh;
}

function updateHazards(hazards) {
    hazardMeshes.forEach(mesh => scene.remove(mesh));
    hazardMeshes = [];

    hazards.forEach(hazard => {
        const mesh = createHazardMarker(hazard);
        mesh.visible = showHazardSprites;
        hazardMeshes.push(mesh);
        scene.add(mesh);
    });
}

function setHazardVisibility(visible) {
    showHazardSprites = visible;
    hazardMeshes.forEach(mesh => {
        mesh.visible = visible;
    });
}

let trajectoryLines = [];
let showTrajectoryLines = true;

function createExpansionLine(trajectory) {
    const positions = [];
    const start = trajectory.start;
    const end = trajectory.end;
    
    const numSegments = 20;
    for (let i = 0; i <= numSegments; i++) {
        const t = i / numSegments;
        positions.push(
            start[0] + (end[0] - start[0]) * t,
            start[1] + (end[1] - start[1]) * t,
            start[2] + (end[2] - start[2]) * t
        );
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));

    const civId = trajectory.civ_id || 0;
    const hue = (civId * 0.618033988749895) % 1.0;
    const color = new THREE.Color().setHSL(hue, 1.0, 0.65);

    const material = new THREE.LineBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.9,
        linewidth: 3,
        blending: THREE.AdditiveBlending
    });

    const line = new THREE.Line(geometry, material);
    line.userData = trajectory;

    const sphereGeom = new THREE.SphereGeometry(0.03, 8, 8);
    const sphereMat = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.95,
        blending: THREE.AdditiveBlending
    });
    const endMarker = new THREE.Mesh(sphereGeom, sphereMat);
    endMarker.position.set(end[0], end[1], end[2]);
    
    const group = new THREE.Group();
    group.add(line);
    group.add(endMarker);
    group.userData = trajectory;

    return group;
}

function updateTrajectories(trajectories, currentTimeGyr) {
    trajectoryLines.forEach(obj => scene.remove(obj));
    trajectoryLines = [];

    if (!showTrajectoryLines) return;
    if (!trajectories || !Array.isArray(trajectories)) return;

    const currentTimeMyr = (currentTimeGyr || 0) * 1000;

    trajectories.forEach(traj => {
        if (traj.start && traj.end) {
            const trajTimeMyr = traj.time_myr || 0;
            if (trajTimeMyr <= currentTimeMyr) {
                const obj = createExpansionLine(traj);
                trajectoryLines.push(obj);
                scene.add(obj);
            }
        }
    });
}

function setTrajectoryVisibility(visible) {
    showTrajectoryLines = visible;
    trajectoryLines.forEach(obj => {
        obj.visible = visible;
    });
}

function updateCivilizationDisplay(percent) {
    downsamplePercent = percent;
    if (window.animationData && window.animationData.frames[currentFrame]) {
        updateCivilizations(window.animationData.frames[currentFrame].civilizations);
    }
}

window.initParticles = initParticles;
window.updateParticles = updateParticles;
window.createCivilizationSprite = createCivilizationSprite;
window.updateCivilizations = updateCivilizations;
window.setCivVisibility = setCivVisibility;
window.createProbeTrail = createProbeTrail;
window.updateProbes = updateProbes;
window.setProbeVisibility = setProbeVisibility;
window.createHazardMarker = createHazardMarker;
window.updateHazards = updateHazards;
window.setHazardVisibility = setHazardVisibility;
window.updateCivilizationDisplay = updateCivilizationDisplay;
window.createExpansionLine = createExpansionLine;
window.updateTrajectories = updateTrajectories;
window.setTrajectoryVisibility = setTrajectoryVisibility;