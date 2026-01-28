const { ipcRenderer } = require('electron');

// ═══════════════════════════════════════════════════════════════════════════════
//   BREE AVATAR DASHBOARD - Renderer
//   Uses Python backend (bree_voice_feedback.py) for actual TTS with pygame
// ═══════════════════════════════════════════════════════════════════════════════

// Matrix Rain
class MatrixRain {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.columns = [];
        this.fontSize = 16;
        this.chars = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンBREE0123456789';

        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        this.canvas.width = this.canvas.offsetWidth;
        this.canvas.height = this.canvas.offsetHeight;

        const columnCount = Math.floor(this.canvas.width / this.fontSize);
        this.columns = [];

        for (let i = 0; i < columnCount; i++) {
            this.columns.push({
                y: Math.random() * this.canvas.height,
                speed: 0.5 + Math.random() * 2,
                length: 5 + Math.floor(Math.random() * 20)
            });
        }
    }

    draw() {
        this.ctx.fillStyle = 'rgba(10, 0, 16, 0.05)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.font = `${this.fontSize}px "Share Tech Mono", monospace`;

        this.columns.forEach((col, i) => {
            const x = i * this.fontSize;

            for (let j = 0; j < col.length; j++) {
                const y = col.y - j * this.fontSize;
                if (y < 0) continue;

                const alpha = 1 - (j / col.length);
                const char = this.chars[Math.floor(Math.random() * this.chars.length)];

                if (j === 0) {
                    this.ctx.fillStyle = `rgba(255, 200, 255, ${alpha})`;
                } else if (j < 3) {
                    const orangeMix = (i % 10 === 0) ? 255 : 100;
                    this.ctx.fillStyle = `rgba(${orangeMix}, ${100 - orangeMix/3}, 255, ${alpha * 0.9})`;
                } else {
                    this.ctx.fillStyle = `rgba(157, 0, 255, ${alpha * 0.6})`;
                }

                this.ctx.fillText(char, x, y);
            }

            col.y += col.speed * this.fontSize * 0.3;

            if (col.y - col.length * this.fontSize > this.canvas.height) {
                col.y = 0;
                col.speed = 0.5 + Math.random() * 2;
                col.length = 5 + Math.floor(Math.random() * 20);
            }
        });
    }

    animate() {
        this.draw();
        requestAnimationFrame(() => this.animate());
    }
}

// Sound Effects Engine
class SoundEffectsEngine {
    constructor() {
        this.context = null;
        this.masterGain = null;
        this.enabled = true;
    }

    init() {
        if (this.context) return;
        this.context = new (window.AudioContext || window.webkitAudioContext)();
        this.masterGain = this.context.createGain();
        this.masterGain.connect(this.context.destination);
        this.masterGain.gain.value = 0.4;
    }

    createTone(freq, duration, type = 'sine', opts = {}) {
        if (!this.enabled || !this.context) return;

        const osc = this.context.createOscillator();
        const gain = this.context.createGain();
        const filter = this.context.createBiquadFilter();

        osc.type = type;
        osc.frequency.setValueAtTime(freq, this.context.currentTime);

        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(opts.filter || 3000, this.context.currentTime);

        const vol = opts.volume || 0.2;
        gain.gain.setValueAtTime(0, this.context.currentTime);
        gain.gain.linearRampToValueAtTime(vol, this.context.currentTime + 0.01);
        gain.gain.linearRampToValueAtTime(0, this.context.currentTime + duration);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(this.masterGain);

        osc.start();
        osc.stop(this.context.currentTime + duration);
    }

    playStartup() {
        if (!this.enabled) return;
        this.init();

        const osc = this.context.createOscillator();
        const gain = this.context.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(40, this.context.currentTime);
        gain.gain.setValueAtTime(0, this.context.currentTime);
        gain.gain.linearRampToValueAtTime(0.15, this.context.currentTime + 1);
        gain.gain.linearRampToValueAtTime(0, this.context.currentTime + 3);
        osc.connect(gain);
        gain.connect(this.masterGain);
        osc.start();
        osc.stop(this.context.currentTime + 3);

        setTimeout(() => {
            [220, 277, 330, 440, 554].forEach((freq, i) => {
                setTimeout(() => this.createTone(freq, 0.25, 'sine', { volume: 0.1 }), i * 80);
            });
        }, 400);

        setTimeout(() => {
            [261.63, 329.63, 392, 523.25].forEach(freq => {
                this.createTone(freq, 1.2, 'sine', { volume: 0.08 });
            });
        }, 1000);
    }

    playClick() {
        if (!this.enabled) return;
        this.init();
        this.createTone(800, 0.04, 'square', { volume: 0.08 });
    }

    playHover() {
        if (!this.enabled) return;
        this.init();
        this.createTone(400, 0.06, 'sine', { volume: 0.04 });
    }

    playSuccess() {
        if (!this.enabled) return;
        this.init();
        [523, 659, 784].forEach((f, i) => {
            setTimeout(() => this.createTone(f, 0.18, 'sine', { volume: 0.12 }), i * 80);
        });
    }

    playNotification() {
        if (!this.enabled) return;
        this.init();
        this.createTone(880, 0.08, 'sine', { volume: 0.12 });
        setTimeout(() => this.createTone(1100, 0.12, 'sine', { volume: 0.1 }), 80);
    }

    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }
}

// Console Logger
function log(message, type = 'info') {
    const consoleEl = document.getElementById('console');
    if (!consoleEl) return;

    const line = document.createElement('div');
    line.className = `console-line ${type}`;
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    line.innerHTML = `<span class="time">[${time}]</span> ${message}`;
    consoleEl.appendChild(line);
    consoleEl.scrollTop = consoleEl.scrollHeight;

    while (consoleEl.children.length > 50) {
        consoleEl.removeChild(consoleEl.firstChild);
    }
}

// Global state
let matrixRain;
let soundEffects;
let currentEmotion = 'NEUTRAL';
let currentStyle = 'holographic';
let isSpeaking = false;
let settings = {};

// UI Functions
function minimizeWindow() {
    soundEffects?.playClick();
    ipcRenderer.invoke('minimize-window');
}

function maximizeWindow() {
    soundEffects?.playClick();
    ipcRenderer.invoke('maximize-window');
}

function closeWindow() {
    soundEffects?.playClick();
    ipcRenderer.invoke('close-window');
}

function toggleSound() {
    const enabled = soundEffects?.toggle();
    const btn = document.getElementById('soundToggle');
    if (btn) {
        btn.textContent = enabled ? '🔊' : '🔇';
        btn.classList.toggle('muted', !enabled);
    }
    if (enabled) soundEffects?.playClick();
}

function selectNav(element, section) {
    soundEffects?.playClick();
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    log(`Navigated to ${section}`, 'info');
}

function selectStyle(style) {
    soundEffects?.playClick();
    currentStyle = style;

    document.querySelectorAll('.style-card').forEach(el => el.classList.remove('active'));
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }

    ipcRenderer.invoke('set-avatar-style', style);
    log(`Avatar style: ${style.toUpperCase()}`, 'system');
}

function cycleStyle() {
    soundEffects?.playClick();
    const styles = ['holographic', 'realistic', 'stylized', 'anime'];
    const currentIndex = styles.indexOf(currentStyle);
    const nextStyle = styles[(currentIndex + 1) % styles.length];
    currentStyle = nextStyle;

    document.querySelectorAll('.style-card').forEach((card, i) => {
        card.classList.toggle('active', styles[i] === nextStyle);
    });

    ipcRenderer.invoke('set-avatar-style', nextStyle);
    log(`Style cycled to: ${nextStyle.toUpperCase()}`, 'info');
}

function setEmotion(emotion) {
    soundEffects?.playClick();
    currentEmotion = emotion;

    document.querySelectorAll('.emotion-btn').forEach(el => el.classList.remove('active'));
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }

    ipcRenderer.invoke('set-emotion', emotion);
    log(`Emotion: ${emotion}`, 'info');
}

function launchAvatar() {
    soundEffects?.playSuccess();
    ipcRenderer.invoke('open-avatar-window');
    log('Launching Bree 3D Avatar window...', 'success');
}

function testSpeak() {
    soundEffects?.playNotification();
    const testPhrases = {
        ECSTATIC: "[gasps] Holy SHIT! A 9.8?! That's fucking GORGEOUS! I could kiss this comic!",
        IMPRESSED: "Not bad at all. I'm actually impressed with this one. Good shit.",
        PLEASED: "Yeah, this is pretty decent. Solid condition. I can work with this.",
        NEUTRAL: "Alright, let me take a look at what we've got here.",
        ANNOYED: "[sighs] Really? This is what you're bringing me? Mediocre at best.",
        PISSED: "Are you fucking kidding me with this garbage? Who stored this, a raccoon?",
        FURIOUS: "What the actual FUCK happened to this comic?! This is an abomination!",
        NUCLEAR: "[screaming] THIS IS THE WORST PIECE OF SHIT I HAVE EVER LAID EYES ON! BURN IT!"
    };

    const phrase = testPhrases[currentEmotion] || testPhrases.NEUTRAL;
    speakText(phrase, currentEmotion);
}

function speakCustom() {
    const input = document.getElementById('speechInput');
    if (input && input.value.trim()) {
        speakText(input.value.trim(), currentEmotion);
    }
}

async function speakText(text, emotion) {
    if (isSpeaking) {
        log('Already speaking, please wait...', 'warning');
        return;
    }

    isSpeaking = true;
    log(`Speaking [${emotion}]: ${text.substring(0, 50)}...`, 'system');

    try {
        // This calls Python bree_voice_feedback.py with pygame playback
        await ipcRenderer.invoke('speak-text', { text, emotion });
        log('Speech completed', 'success');
    } catch (err) {
        log(`Speech error: ${err.message}`, 'error');
    }

    isSpeaking = false;
}

function updateSetting(key, value) {
    soundEffects?.playClick();
    settings[key] = value;
    ipcRenderer.invoke('save-settings', { [key]: value });
    log(`Setting: ${key} = ${value}`, 'info');
}

function toggleSetting(key) {
    soundEffects?.playClick();
    const toggle = document.getElementById(key);
    if (toggle) {
        const isActive = toggle.classList.toggle('active');
        settings[key] = isActive;
        ipcRenderer.invoke('save-settings', { [key]: isActive });
        log(`Setting: ${key} = ${isActive}`, 'info');
    }
}

// Quick Actions
function startGrading() {
    soundEffects?.playNotification();
    log('Starting grading session...', 'system');
    speakText("[excited] Alright, let's grade some comics! Bring 'em on, I'm ready to judge!", 'PLEASED');
}

function openCamera() {
    soundEffects?.playClick();
    log('Opening camera module...', 'system');
}

function openAPI() {
    soundEffects?.playClick();
    ipcRenderer.invoke('open-url', 'http://localhost:8000/docs');
    log('Opening API documentation...', 'info');
}

function exportData() {
    soundEffects?.playClick();
    log('Exporting collection data...', 'system');
    setTimeout(() => {
        log('Export complete: collection_export.json', 'success');
        soundEffects?.playSuccess();
    }, 1500);
}

function updateSystemStats(stats) {
    const cpuValue = document.getElementById('cpu-value');
    const cpuBar = document.getElementById('cpu-bar');
    const memValue = document.getElementById('mem-value');
    const memBar = document.getElementById('mem-bar');

    if (cpuValue) cpuValue.textContent = `${stats.cpu.usage}%`;
    if (cpuBar) cpuBar.style.width = `${stats.cpu.usage}%`;
    if (memValue) memValue.textContent = `${stats.memory.used} / ${stats.memory.total} GB`;
    if (memBar) memBar.style.width = `${stats.memory.percent}%`;
}

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    // Matrix Rain
    const matrixCanvas = document.getElementById('matrix-canvas');
    if (matrixCanvas) {
        matrixRain = new MatrixRain(matrixCanvas);
        matrixRain.animate();
    }

    // Sound Effects
    soundEffects = new SoundEffectsEngine();

    document.body.addEventListener('click', () => {
        soundEffects.init();
    }, { once: true });

    setTimeout(() => {
        soundEffects.init();
        soundEffects.playStartup();
    }, 300);

    // Load settings
    settings = await ipcRenderer.invoke('get-settings');

    // Logs
    log('Bree Avatar System v2.0 initialized', 'system');
    log('Three.js 3D renderer active', 'success');
    log('Python backend: bree_voice_feedback.py', 'info');
    log('Audio: ElevenLabs TTS + pygame playback', 'info');
    log('Voice ID: pzKXffibtCDxnrVO8d1U', 'info');

    // Hover sounds
    document.querySelectorAll('.nav-item, .action-btn, .style-card, .preview-btn, .emotion-btn, .provider-badge').forEach(el => {
        el.addEventListener('mouseenter', () => soundEffects?.playHover());
    });

    // IPC listeners
    ipcRenderer.on('system-stats', (event, stats) => {
        updateSystemStats(stats);
    });

    ipcRenderer.on('start-speaking', () => {
        isSpeaking = true;
    });

    ipcRenderer.on('stop-speaking', () => {
        isSpeaking = false;
    });

    // Get initial stats
    const initialStats = await ipcRenderer.invoke('get-system-stats');
    updateSystemStats(initialStats);

    setTimeout(() => {
        log('System ready - Click LAUNCH AVATAR', 'success');
        soundEffects?.playSuccess();
    }, 2000);
});
