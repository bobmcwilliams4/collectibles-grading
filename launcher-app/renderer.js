const { ipcRenderer } = require('electron');

// ═══════════════════════════════════════════════════════════════════════════════
//   AUDIO ENGINE - Web Audio API Based Sound System
// ═══════════════════════════════════════════════════════════════════════════════

class AudioEngine {
    constructor() {
        this.context = null;
        this.enabled = true;
        this.masterGain = null;
        this.initialized = false;
    }

    init() {
        if (this.initialized) return;
        try {
            this.context = new (window.AudioContext || window.webkitAudioContext)();
            this.masterGain = this.context.createGain();
            this.masterGain.connect(this.context.destination);
            this.masterGain.gain.value = 0.5;
            this.initialized = true;
        } catch (e) {
            console.log('Audio not available');
        }
    }

    // Create oscillator with envelope
    createTone(frequency, duration, type = 'sine', options = {}) {
        if (!this.enabled || !this.context) return;

        const osc = this.context.createOscillator();
        const gain = this.context.createGain();
        const filter = this.context.createBiquadFilter();

        osc.type = type;
        osc.frequency.setValueAtTime(frequency, this.context.currentTime);

        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(options.filterFreq || 2000, this.context.currentTime);

        const attack = options.attack || 0.02;
        const decay = options.decay || 0.1;
        const sustain = options.sustain || 0.3;
        const release = options.release || 0.3;
        const volume = options.volume || 0.3;

        gain.gain.setValueAtTime(0, this.context.currentTime);
        gain.gain.linearRampToValueAtTime(volume, this.context.currentTime + attack);
        gain.gain.linearRampToValueAtTime(volume * sustain, this.context.currentTime + attack + decay);
        gain.gain.setValueAtTime(volume * sustain, this.context.currentTime + duration - release);
        gain.gain.linearRampToValueAtTime(0, this.context.currentTime + duration);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(this.masterGain);

        osc.start();
        osc.stop(this.context.currentTime + duration);
    }

    // Play chord (multiple frequencies)
    playChord(frequencies, duration, type = 'sine', options = {}) {
        frequencies.forEach((freq, i) => {
            setTimeout(() => {
                this.createTone(freq, duration, type, { ...options, volume: (options.volume || 0.15) });
            }, i * 50);
        });
    }

    // Startup fanfare - cinematic sound
    playStartup() {
        if (!this.enabled) return;
        this.init();

        // Deep bass sweep
        const now = this.context.currentTime;
        const bassOsc = this.context.createOscillator();
        const bassGain = this.context.createGain();
        bassOsc.type = 'sine';
        bassOsc.frequency.setValueAtTime(40, now);
        bassOsc.frequency.exponentialRampToValueAtTime(80, now + 2);
        bassGain.gain.setValueAtTime(0, now);
        bassGain.gain.linearRampToValueAtTime(0.4, now + 0.5);
        bassGain.gain.linearRampToValueAtTime(0.2, now + 1.5);
        bassGain.gain.linearRampToValueAtTime(0, now + 2.5);
        bassOsc.connect(bassGain);
        bassGain.connect(this.masterGain);
        bassOsc.start();
        bassOsc.stop(now + 2.5);

        // Cinematic rise
        setTimeout(() => {
            this.playChord([130.81, 164.81, 196.00], 0.8, 'sine', { attack: 0.1, volume: 0.2 }); // C3 chord
        }, 300);

        setTimeout(() => {
            this.playChord([196.00, 246.94, 293.66], 0.8, 'sine', { attack: 0.1, volume: 0.2 }); // G3 chord
        }, 600);

        setTimeout(() => {
            this.playChord([261.63, 329.63, 392.00, 523.25], 1.5, 'sine', { attack: 0.2, release: 0.8, volume: 0.25 }); // C major
        }, 1000);

        // Shimmer effect
        setTimeout(() => {
            for (let i = 0; i < 5; i++) {
                setTimeout(() => {
                    this.createTone(1000 + i * 200, 0.3, 'sine', { volume: 0.05, attack: 0.01 });
                }, i * 100);
            }
        }, 1500);
    }

    // Success sound - triumphant
    playSuccess() {
        if (!this.enabled) return;
        this.init();

        this.playChord([523.25, 659.25, 783.99], 0.15, 'sine', { volume: 0.2 });
        setTimeout(() => {
            this.playChord([659.25, 783.99, 987.77], 0.15, 'sine', { volume: 0.2 });
        }, 150);
        setTimeout(() => {
            this.playChord([783.99, 987.77, 1174.66], 0.4, 'sine', { volume: 0.25, release: 0.3 });
        }, 300);
    }

    // Click/UI feedback
    playClick() {
        if (!this.enabled) return;
        this.init();
        this.createTone(800, 0.05, 'sine', { volume: 0.15, attack: 0.005 });
        this.createTone(1200, 0.03, 'sine', { volume: 0.1, attack: 0.005 });
    }

    // Hover sound
    playHover() {
        if (!this.enabled) return;
        this.init();
        this.createTone(600, 0.08, 'sine', { volume: 0.08, attack: 0.01 });
    }

    // Progress tick
    playProgress(step, total) {
        if (!this.enabled) return;
        this.init();
        const freq = 300 + (step / total) * 400;
        this.createTone(freq, 0.1, 'sine', { volume: 0.1, attack: 0.01 });
    }

    // Error sound
    playError() {
        if (!this.enabled) return;
        this.init();
        this.createTone(150, 0.4, 'sawtooth', { volume: 0.15, filterFreq: 500 });
        setTimeout(() => {
            this.createTone(100, 0.5, 'sawtooth', { volume: 0.12, filterFreq: 300 });
        }, 200);
    }

    // Ambient drone (background)
    startAmbient() {
        if (!this.enabled || !this.context) return;

        const drone = this.context.createOscillator();
        const droneGain = this.context.createGain();
        const droneFilter = this.context.createBiquadFilter();

        drone.type = 'sine';
        drone.frequency.setValueAtTime(55, this.context.currentTime); // A1

        droneFilter.type = 'lowpass';
        droneFilter.frequency.setValueAtTime(200, this.context.currentTime);

        droneGain.gain.setValueAtTime(0.03, this.context.currentTime);

        drone.connect(droneFilter);
        droneFilter.connect(droneGain);
        droneGain.connect(this.masterGain);

        drone.start();

        // Subtle LFO modulation
        const lfo = this.context.createOscillator();
        const lfoGain = this.context.createGain();
        lfo.frequency.setValueAtTime(0.1, this.context.currentTime);
        lfoGain.gain.setValueAtTime(5, this.context.currentTime);
        lfo.connect(lfoGain);
        lfoGain.connect(drone.frequency);
        lfo.start();

        this.ambientDrone = drone;
        this.ambientLfo = lfo;
    }

    stopAmbient() {
        if (this.ambientDrone) {
            this.ambientDrone.stop();
            this.ambientLfo.stop();
        }
    }

    toggle() {
        this.enabled = !this.enabled;
        if (this.masterGain) {
            this.masterGain.gain.value = this.enabled ? 0.5 : 0;
        }
        return this.enabled;
    }
}

const audio = new AudioEngine();

// ═══════════════════════════════════════════════════════════════════════════════
//   PARTICLE SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════

function createParticles() {
    const container = document.getElementById('particles');
    const colors = ['#00f0ff', '#ff00ff', '#00ff88', '#ffaa00'];

    for (let i = 0; i < 80; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';

        const size = Math.random() * 4 + 2;
        const color = colors[Math.floor(Math.random() * colors.length)];

        particle.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            left: ${Math.random() * 100}%;
            background: ${color};
            box-shadow: 0 0 ${size * 2}px ${color}, 0 0 ${size * 4}px ${color};
            animation-delay: ${Math.random() * 15}s;
            animation-duration: ${10 + Math.random() * 15}s;
        `;

        container.appendChild(particle);
    }
}

// Holographic scan lines
function createHoloLines() {
    const container = document.getElementById('holoLines');

    for (let i = 0; i < 5; i++) {
        const line = document.createElement('div');
        line.className = 'holo-line';
        line.style.cssText = `
            width: 100%;
            animation-delay: ${i * 1.5}s;
        `;
        container.appendChild(line);
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//   3D BACKGROUND (Three.js style with canvas)
// ═══════════════════════════════════════════════════════════════════════════════

function initBackground() {
    const canvas = document.getElementById('bg-canvas');
    const ctx = canvas.getContext('2d');

    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    const stars = [];
    for (let i = 0; i < 200; i++) {
        stars.push({
            x: Math.random() * width,
            y: Math.random() * height,
            z: Math.random() * 1000,
            size: Math.random() * 2
        });
    }

    function animate() {
        ctx.fillStyle = 'rgba(5, 5, 10, 0.2)';
        ctx.fillRect(0, 0, width, height);

        stars.forEach(star => {
            star.z -= 2;
            if (star.z <= 0) {
                star.z = 1000;
                star.x = Math.random() * width;
                star.y = Math.random() * height;
            }

            const perspective = 500 / star.z;
            const x = (star.x - width / 2) * perspective + width / 2;
            const y = (star.y - height / 2) * perspective + height / 2;
            const size = star.size * perspective;

            const alpha = 1 - star.z / 1000;

            ctx.beginPath();
            ctx.arc(x, y, size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 240, 255, ${alpha * 0.5})`;
            ctx.fill();

            // Trail effect
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(x + (star.x - width/2) * 0.01, y + (star.y - height/2) * 0.01);
            ctx.strokeStyle = `rgba(0, 240, 255, ${alpha * 0.2})`;
            ctx.lineWidth = size * 0.5;
            ctx.stroke();
        });

        requestAnimationFrame(animate);
    }

    animate();

    window.addEventListener('resize', () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });
}

// ═══════════════════════════════════════════════════════════════════════════════
//   CONSOLE LOGGER
// ═══════════════════════════════════════════════════════════════════════════════

function log(message, type = 'info') {
    const console = document.getElementById('console');
    const line = document.createElement('div');
    line.className = `console-line ${type}`;

    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    line.innerHTML = `<span class="timestamp">[${time}]</span> ${message}`;

    console.appendChild(line);
    console.scrollTop = console.scrollHeight;

    // Sound feedback
    if (type === 'success') audio.playSuccess();
    else if (type === 'error') audio.playError();
}

// ═══════════════════════════════════════════════════════════════════════════════
//   PROGRESS HANDLER
// ═══════════════════════════════════════════════════════════════════════════════

function updateProgress(percent, text) {
    const section = document.getElementById('progressSection');
    const fill = document.getElementById('progressFill');
    const percentText = document.getElementById('progressPercent');
    const textEl = document.getElementById('progressText');

    section.classList.add('active');
    fill.style.width = percent + '%';
    percentText.textContent = percent + '%';
    textEl.textContent = text;
}

// ═══════════════════════════════════════════════════════════════════════════════
//   SYSTEM CHECK
// ═══════════════════════════════════════════════════════════════════════════════

async function runSystemCheck() {
    const components = ['backend', 'database', 'electron', 'ai_providers', 'pricing', 'webcam'];

    log('Starting system diagnostics...', 'system');

    for (let i = 0; i < components.length; i++) {
        const component = components[i];
        const indicator = document.getElementById(`status-${component}`);

        indicator.className = 'status-indicator checking';
        audio.playProgress(i, components.length);

        await new Promise(r => setTimeout(r, 300));

        try {
            const exists = await ipcRenderer.invoke('check-system', component);
            indicator.className = `status-indicator ${exists ? 'ready' : 'error'}`;

            const name = component.replace('_', ' ').toUpperCase();
            log(`${name}: ${exists ? 'READY' : 'NOT FOUND'}`, exists ? 'success' : 'warning');
        } catch (e) {
            indicator.className = 'status-indicator error';
        }

        updateProgress(Math.round((i + 1) / components.length * 40), `Checking ${component}...`);
    }

    log('System diagnostics complete', 'system');
}

// ═══════════════════════════════════════════════════════════════════════════════
//   LAUNCH SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════

async function launchSystem() {
    const launchBtn = document.getElementById('launchAll');
    const guiBtn = document.getElementById('launchGUI');
    const overlay = document.getElementById('launchingOverlay');
    const status = document.getElementById('launchStatus');

    launchBtn.disabled = true;
    audio.playClick();

    log('═══════════════════════════════════════════════', 'system');
    log('INITIATING LAUNCH SEQUENCE', 'system');
    log('═══════════════════════════════════════════════', 'system');

    // Run system check
    await runSystemCheck();

    // Start backend
    log('Starting FastAPI backend server...', 'info');
    updateProgress(50, 'Starting backend server...');
    status.textContent = 'STARTING BACKEND';

    try {
        const result = await ipcRenderer.invoke('start-backend');
        log('Backend server starting on http://localhost:8000', 'success');
        log('API Documentation: http://localhost:8000/docs', 'info');
    } catch (e) {
        log('Backend start initiated', 'warning');
    }

    updateProgress(70, 'Loading AI consensus engine...');
    status.textContent = 'LOADING AI';
    await new Promise(r => setTimeout(r, 1000));
    log('AI consensus engine loaded', 'success');

    updateProgress(85, 'Initializing pricing sources...');
    status.textContent = 'PRICING ENGINE';
    await new Promise(r => setTimeout(r, 800));
    log('Pricing sources connected', 'success');

    updateProgress(95, 'Launching GUI...');
    status.textContent = 'LAUNCHING GUI';

    try {
        await ipcRenderer.invoke('start-gui');
        log('Electron GUI launching...', 'success');
    } catch (e) {
        log('GUI launch initiated', 'warning');
    }

    updateProgress(100, 'System Ready!');
    status.textContent = 'COMPLETE';

    await new Promise(r => setTimeout(r, 500));

    overlay.classList.remove('active');
    guiBtn.disabled = false;

    log('═══════════════════════════════════════════════', 'success');
    log('SYSTEM LAUNCH COMPLETE', 'success');
    log('═══════════════════════════════════════════════', 'success');
    log('Backend API: http://localhost:8000', 'info');
    log('API Docs: http://localhost:8000/docs', 'info');

    audio.playSuccess();
}

async function launchGUI() {
    audio.playClick();
    log('Opening Electron GUI...', 'info');
    await ipcRenderer.invoke('start-gui');
    log('GUI window opened', 'success');
}

// ═══════════════════════════════════════════════════════════════════════════════
//   WINDOW CONTROLS
// ═══════════════════════════════════════════════════════════════════════════════

function minimizeWindow() {
    audio.playClick();
    ipcRenderer.invoke('minimize-window');
}

function maximizeWindow() {
    audio.playClick();
    ipcRenderer.invoke('maximize-window');
}

function closeWindow() {
    audio.playClick();
    audio.stopAmbient();
    setTimeout(() => {
        ipcRenderer.invoke('close-window');
    }, 100);
}

function toggleSound() {
    const enabled = audio.toggle();
    const btn = document.getElementById('soundToggle');
    btn.textContent = enabled ? '🔊' : '🔇';
    btn.classList.toggle('muted', !enabled);

    if (enabled) audio.playClick();
}

// ═══════════════════════════════════════════════════════════════════════════════
//   BUTTON HOVER EFFECTS
// ═══════════════════════════════════════════════════════════════════════════════

document.querySelectorAll('.launch-btn').forEach(btn => {
    btn.addEventListener('mouseenter', () => audio.playHover());
});

// ═══════════════════════════════════════════════════════════════════════════════
//   INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Initialize visual effects
    createParticles();
    createHoloLines();
    initBackground();

    // Initialize audio on first interaction
    document.body.addEventListener('click', () => {
        audio.init();
    }, { once: true });

    // Play startup sequence
    setTimeout(() => {
        audio.init();
        audio.playStartup();
        audio.startAmbient();
    }, 500);

    // Initial log
    log('Launcher initialized', 'system');
    log('Click "LAUNCH SYSTEM" to begin', 'info');

    // Get system info
    ipcRenderer.invoke('get-system-info').then(info => {
        log(`Platform: ${info.platform} | CPUs: ${info.cpus} | RAM: ${info.memory}`, 'info');
    });
});

// Handle backend logs
ipcRenderer.on('backend-log', (event, data) => {
    const lines = data.split('\n').filter(l => l.trim());
    lines.forEach(line => {
        if (line.includes('ERROR') || line.includes('error')) {
            log(line.substring(0, 100), 'error');
        } else if (line.includes('WARNING')) {
            log(line.substring(0, 100), 'warning');
        } else if (line.includes('INFO') || line.includes('Started') || line.includes('Uvicorn')) {
            log(line.substring(0, 100), 'info');
        }
    });
});
