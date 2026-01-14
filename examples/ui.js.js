

let isPlaying = false;
let currentFrame = 0;
let playbackSpeed = 1.0;
let showStars = true;
let showCivs = true;
let showProbes = true;
let showHazards = true;
let usePostProcessing = false;
let downsamplePercent = 0;

function initUI() {
    initPlaybackControls();
    initLayerControls();
    initSpeedControl();
    initDownsampleControl();
    initExportButton();
    initRaycaster();
    initMiniMap();
}

function initPlaybackControls() {
    const btnPlayPause = document.getElementById('btn-playpause');
    const btnStep = document.getElementById('btn-step');
    const btnReset = document.getElementById('btn-reset');
    const timelineSlider = document.getElementById('timeline-slider');

    btnPlayPause.addEventListener('click', togglePlayPause);
    btnStep.addEventListener('click', stepForward);
    btnReset.addEventListener('click', resetPlayback);

    timelineSlider.addEventListener('input', (e) => {
        currentFrame = parseInt(e.target.value);
        if (window.animationData) {
            updateFrame(currentFrame);
        }
    });
}

function initLayerControls() {
    document.getElementById('btn-stars').addEventListener('click', (e) => {
        showStars = !showStars;
        e.target.classList.toggle('active', showStars);
        updateStarsVisible(showStars);
    });

    document.getElementById('btn-civs').addEventListener('click', (e) => {
        showCivs = !showCivs;
        e.target.classList.toggle('active', showCivs);
        updateCivizationsVisible(showCivs);
    });

    document.getElementById('btn-probes').addEventListener('click', (e) => {
        showProbes = !showProbes;
        e.target.classList.toggle('active', showProbes);
        updateProbesVisible(showProbes);
    });

    document.getElementById('btn-hazards').addEventListener('click', (e) => {
        showHazards = !showHazards;
        e.target.classList.toggle('active', showHazards);
        updateHazardsVisible(showHazards);
    });

    document.getElementById('btn-postprocess').addEventListener('click', (e) => {
        usePostProcessing = !usePostProcessing;
        e.target.classList.toggle('active', usePostProcessing);
        window.usePostProcessing = usePostProcessing;
    });
}

function initSpeedControl() {
    const speedSlider = document.getElementById('speed-slider');
    const speedDisplay = document.getElementById('speed-display');

    speedSlider.addEventListener('input', (e) => {
        playbackSpeed = parseFloat(e.target.value);
        speedDisplay.textContent = playbackSpeed.toFixed(1) + 'x';
    });
}

function initDownsampleControl() {
    const downsampleSlider = document.getElementById('downsample-slider');
    const downsampleDisplay = document.getElementById('downsample-display');
    const downsampleContainer = document.getElementById('downsample-container');

    if (window.animationData) {
        const maxCivs = Math.max(...window.animationData.frames.map(f => f.civilizations.length));
        
        if (maxCivs > 20) {
            downsampleContainer.style.display = 'flex';
            
            downsampleSlider.addEventListener('input', (e) => {
                downsamplePercent = parseInt(e.target.value);
                if (downsamplePercent === 0) {
                    downsampleDisplay.textContent = 'All';
                } else {
                    downsampleDisplay.textContent = 'Youngest ' + (100 - downsamplePercent) + '%';
                }
                if (window.updateCivilizationDisplay) {
                    window.updateCivilizationDisplay(downsamplePercent);
                }
            });
        }
    }
}

function initExportButton() {
    document.getElementById('btn-export').addEventListener('click', exportFrame);
}

function initRaycaster() {
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const tooltip = document.getElementById('tooltip');

    renderer.domElement.addEventListener('mousemove', (event) => {
        mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);

        if (civSprites.length > 0) {
            const intersects = raycaster.intersectObjects(civSprites);

            if (intersects.length > 0) {
                const sprite = intersects[0].object;
                const civData = sprite.userData;

                tooltip.style.display = 'block';
                tooltip.style.left = event.clientX + 10 + 'px';
                tooltip.style.top = event.clientY + 10 + 'px';

                document.getElementById('tooltip-title').textContent = 'Civilization';
                document.getElementById('tooltip-content').innerHTML = `
                    <strong>ID:</strong> ${civData.civ_id}<br>
                    <strong>Kardashev:</strong> ${civData.kardashev.toFixed(2)}<br>
                    <strong>Age:</strong> ${civData.age.toFixed(2)} Gyr<br>
                    <strong>Status:</strong> ${civData.is_active ? 'Active' : 'Extinct'}
                `;

                document.getElementById('info-civ-id').textContent = civData.civ_id;
                document.getElementById('info-kardashev').textContent = civData.kardashev.toFixed(2);
                document.getElementById('info-age').textContent = civData.age.toFixed(2) + ' Gyr';
                document.getElementById('info-status').textContent = civData.is_active ? 'Active' : 'Extinct';
                document.getElementById('info-position').textContent = 
                    `[${civData.position[0].toFixed(2)}, ${civData.position[1].toFixed(2)}, ${civData.position[2].toFixed(2)}]`;
                document.getElementById('info-panel').style.display = 'block';
            } else {
                tooltip.style.display = 'none';
                document.getElementById('info-panel').style.display = 'none';
            }
        }
    });

    renderer.domElement.addEventListener('click', (event) => {
        mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);

        if (civSprites.length > 0) {
            const intersects = raycaster.intersectObjects(civSprites);

            if (intersects.length > 0) {
                const civData = intersects[0].object.userData;
                followCivilization(civData.civ_id);
            }
        }
    });
}

function initMiniMap() {
    const canvas = document.getElementById('mini-map-canvas');
    const ctx = canvas.getContext('2d');

    canvas.width = 150;
    canvas.height = 150;

    function updateMiniMap() {
        if (!window.animationData) return;

        const frame = window.animationData.frames[currentFrame];
        if (!frame) return;

        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = '#333333';
        ctx.beginPath();
        ctx.arc(canvas.width / 2, canvas.height / 2, 5, 0, Math.PI * 2);
        ctx.fill();

        frame.civilizations.forEach(civ => {
            if (!civ.is_active) return;

            const x = canvas.width / 2 + civ.position[0] * 5;
            const y = canvas.height / 2 + civ.position[1] * 5;

            ctx.fillStyle = civ.kardashev > 2.0 ? '#ff6600' : '#00ffff';
            ctx.beginPath();
            ctx.arc(x, y, 2, 0, Math.PI * 2);
            ctx.fill();
        });

        requestAnimationFrame(updateMiniMap);
    }

    if (window.animationData) {
        updateMiniMap();
    }
}

function togglePlayPause() {
    isPlaying = !isPlaying;
    window.isPlaying = isPlaying;
    
    const btn = document.getElementById('btn-playpause');
    if (isPlaying) {
        btn.textContent = '⏸ Pause';
    } else {
        btn.textContent = '▶ Play';
    }
}

function stepForward() {
    isPlaying = false;
    window.isPlaying = false;
    document.getElementById('btn-playpause').textContent = '▶ Play';

    if (window.animationData) {
        currentFrame = Math.min(currentFrame + 1, window.animationData.frames.length - 1);
        updateFrame(currentFrame);
    }
}

function resetPlayback() {
    isPlaying = false;
    window.isPlaying = false;
    currentFrame = 0;
    document.getElementById('btn-playpause').textContent = '▶ Play';
    document.getElementById('timeline-slider').value = 0;

    if (window.animationData) {
        updateFrame(0);
    }
}

function exportFrame() {
    renderer.render(scene, camera);
    const link = document.createElement('a');
    link.download = 'galaxy_frame_' + currentFrame + '.png';
    link.href = renderer.domElement.toDataURL('image/png');
    link.click();
}

function initAnimation() {
    if (!window.animationData) return;

    const frames = window.animationData.frames;
    const timelineSlider = document.getElementById('timeline-slider');

    timelineSlider.max = frames.length - 1;
    timelineSlider.value = 0;

    window.currentFrame = 0;
    updateFrame(0);
}

function updateAnimation(delta) {
    if (!window.animationData) return;

    const frames = window.animationData.frames;
    const frameDuration = (window.config.frame_duration_ms || 50) / 1000;
    const speedMultiplier = playbackSpeed;

    if (currentFrame < frames.length - 1) {
        currentFrame += (speedMultiplier * delta) / frameDuration;
        currentFrame = Math.min(currentFrame, frames.length - 1);
        
        const frameIndex = Math.floor(currentFrame);
        document.getElementById('timeline-slider').value = frameIndex;
        
        updateFrame(frameIndex);
    }
}

function updateFrame(frameIndex) {
    if (!window.animationData) return;

    const frame = window.animationData.frames[frameIndex];
    if (!frame) return;

    const timeDisplay = document.getElementById('time-display');
    const timeStats = document.getElementById('time-stats');
    const civStats = document.getElementById('civ-stats');

    timeDisplay.textContent = frame.time.toFixed(2) + ' Gyr';
    timeStats.textContent = 'Time: ' + frame.time.toFixed(2) + ' Gyr';
    civStats.textContent = 'Active: ' + frame.civilizations.filter(c => c.is_active).length + ' | Total: ' + frame.civilizations.length;

    if (window.updateCivilizations) {
        window.updateCivilizations(frame.civilizations);
    }

    if (window.updateProbes) {
        window.updateProbes(frame.probes);
    }

    if (window.updateHazards) {
        window.updateHazards(frame.hazards);
    }
}

window.initUI = initUI;
window.togglePlayPause = togglePlayPause;
window.stepForward = stepForward;
window.resetPlayback = resetPlayback;