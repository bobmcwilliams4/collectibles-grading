const { ipcRenderer } = require('electron');

// ═══════════════════════════════════════════════════════════════════════════════
//   PURPLE MATRIX RAIN - Canvas Animation
// ═══════════════════════════════════════════════════════════════════════════════

class MatrixRain {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.columns = [];
        this.fontSize = 16;
        this.chars = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%^&*()';

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
                chars: [],
                length: 5 + Math.floor(Math.random() * 20)
            });
        }
    }

    draw() {
        // Fade effect
        this.ctx.fillStyle = 'rgba(10, 0, 16, 0.05)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        this.ctx.font = `${this.fontSize}px "Share Tech Mono", monospace`;

        this.columns.forEach((col, i) => {
            const x = i * this.fontSize;

            // Draw trail
            for (let j = 0; j < col.length; j++) {
                const y = col.y - j * this.fontSize;
                if (y < 0) continue;

                const alpha = 1 - (j / col.length);
                const char = this.chars[Math.floor(Math.random() * this.chars.length)];

                if (j === 0) {
                    // Head - bright white/pink
                    this.ctx.fillStyle = `rgba(255, 200, 255, ${alpha})`;
                    this.ctx.shadowColor = '#ff00ff';
                    this.ctx.shadowBlur = 10;
                } else if (j < 3) {
                    // Near head - bright purple
                    this.ctx.fillStyle = `rgba(200, 100, 255, ${alpha * 0.9})`;
                    this.ctx.shadowBlur = 5;
                } else {
                    // Trail - darker purple
                    this.ctx.fillStyle = `rgba(157, 0, 255, ${alpha * 0.6})`;
                    this.ctx.shadowBlur = 0;
                }

                this.ctx.fillText(char, x, y);
            }

            this.ctx.shadowBlur = 0;

            // Move column
            col.y += col.speed * this.fontSize * 0.3;

            // Reset when off screen
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

// ═══════════════════════════════════════════════════════════════════════════════
//   AUDIO VISUALIZATION WAVE
// ═══════════════════════════════════════════════════════════════════════════════

class WaveVisualizer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.points = [];
        this.numPoints = 100;
        this.time = 0;

        this.resize();
        window.addEventListener('resize', () => this.resize());

        for (let i = 0; i < this.numPoints; i++) {
            this.points.push({
                x: 0,
                y: 0,
                baseY: 0
            });
        }
    }

    resize() {
        this.canvas.width = this.canvas.offsetWidth;
        this.canvas.height = this.canvas.offsetHeight;
    }

    draw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.time += 0.02;

        const centerY = this.canvas.height / 2;
        const amplitude = this.canvas.height * 0.3;

        // Update points
        for (let i = 0; i < this.numPoints; i++) {
            const x = (i / this.numPoints) * this.canvas.width;
            const wave1 = Math.sin(this.time * 2 + i * 0.1) * amplitude * 0.5;
            const wave2 = Math.sin(this.time * 3 + i * 0.15) * amplitude * 0.3;
            const wave3 = Math.sin(this.time + i * 0.05) * amplitude * 0.2;

            this.points[i].x = x;
            this.points[i].y = centerY + wave1 + wave2 + wave3;
        }

        // Draw gradient fill
        const gradient = this.ctx.createLinearGradient(0, 0, this.canvas.width, 0);
        gradient.addColorStop(0, 'rgba(157, 0, 255, 0.3)');
        gradient.addColorStop(0.5, 'rgba(255, 0, 255, 0.4)');
        gradient.addColorStop(1, 'rgba(157, 0, 255, 0.3)');

        this.ctx.beginPath();
        this.ctx.moveTo(0, this.canvas.height);
        this.ctx.lineTo(0, this.points[0].y);

        for (let i = 1; i < this.numPoints; i++) {
            const xc = (this.points[i].x + this.points[i - 1].x) / 2;
            const yc = (this.points[i].y + this.points[i - 1].y) / 2;
            this.ctx.quadraticCurveTo(this.points[i - 1].x, this.points[i - 1].y, xc, yc);
        }

        this.ctx.lineTo(this.canvas.width, this.canvas.height);
        this.ctx.closePath();
        this.ctx.fillStyle = gradient;
        this.ctx.fill();

        // Draw line
        this.ctx.beginPath();
        this.ctx.moveTo(0, this.points[0].y);

        for (let i = 1; i < this.numPoints; i++) {
            const xc = (this.points[i].x + this.points[i - 1].x) / 2;
            const yc = (this.points[i].y + this.points[i - 1].y) / 2;
            this.ctx.quadraticCurveTo(this.points[i - 1].x, this.points[i - 1].y, xc, yc);
        }

        this.ctx.strokeStyle = '#ff00ff';
        this.ctx.lineWidth = 2;
        this.ctx.shadowColor = '#ff00ff';
        this.ctx.shadowBlur = 15;
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;

        // Draw second wave (offset)
        this.ctx.beginPath();
        this.ctx.moveTo(0, this.points[0].y + 20);

        for (let i = 1; i < this.numPoints; i++) {
            const offset = Math.sin(this.time + i * 0.1) * 10;
            const xc = (this.points[i].x + this.points[i - 1].x) / 2;
            const yc = (this.points[i].y + this.points[i - 1].y) / 2 + offset;
            this.ctx.quadraticCurveTo(this.points[i - 1].x, this.points[i - 1].y + offset, xc, yc);
        }

        this.ctx.strokeStyle = 'rgba(0, 255, 255, 0.5)';
        this.ctx.lineWidth = 1;
        this.ctx.stroke();
    }

    animate() {
        this.draw();
        requestAnimationFrame(() => this.animate());
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//   AUDIO ENGINE
// ═══════════════════════════════════════════════════════════════════════════════

class AudioEngine {
    constructor() {
        this.context = null;
        this.enabled = true;
        this.masterGain = null;
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
        const attack = opts.attack || 0.01;
        const release = opts.release || 0.2;

        gain.gain.setValueAtTime(0, this.context.currentTime);
        gain.gain.linearRampToValueAtTime(vol, this.context.currentTime + attack);
        gain.gain.linearRampToValueAtTime(0, this.context.currentTime + duration);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(this.masterGain);

        osc.start();
        osc.stop(this.context.currentTime + duration);
    }

    // Deep bass ambient
    playAmbientPulse() {
        if (!this.enabled) return;
        this.init();

        const now = this.context.currentTime;
        const osc = this.context.createOscillator();
        const gain = this.context.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(40, now);

        gain.gain.setValueAtTime(0, now);
        gain.gain.linearRampToValueAtTime(0.15, now + 1);
        gain.gain.linearRampToValueAtTime(0.08, now + 2);
        gain.gain.linearRampToValueAtTime(0, now + 3);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start();
        osc.stop(now + 3);
    }

    playStartup() {
        if (!this.enabled) return;
        this.init();

        // Bass drop
        this.playAmbientPulse();

        // Rising synth
        setTimeout(() => {
            [220, 330, 440, 550, 660].forEach((freq, i) => {
                setTimeout(() => {
                    this.createTone(freq, 0.3, 'sine', { volume: 0.1 });
                }, i * 100);
            });
        }, 500);

        // Final chord
        setTimeout(() => {
            [261.63, 329.63, 392, 523.25].forEach(freq => {
                this.createTone(freq, 1, 'sine', { volume: 0.08, release: 0.5 });
            });
        }, 1200);
    }

    playClick() {
        if (!this.enabled) return;
        this.init();
        this.createTone(800, 0.05, 'square', { volume: 0.1 });
    }

    playHover() {
        if (!this.enabled) return;
        this.init();
        this.createTone(400, 0.08, 'sine', { volume: 0.05 });
    }

    playSuccess() {
        if (!this.enabled) return;
        this.init();
        [523, 659, 784].forEach((f, i) => {
            setTimeout(() => this.createTone(f, 0.2, 'sine', { volume: 0.15 }), i * 100);
        });
    }

    playNotification() {
        if (!this.enabled) return;
        this.init();
        this.createTone(880, 0.1, 'sine', { volume: 0.15 });
        setTimeout(() => this.createTone(1100, 0.15, 'sine', { volume: 0.12 }), 100);
    }

    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }
}

const audio = new AudioEngine();

// ═══════════════════════════════════════════════════════════════════════════════
//   CONSOLE LOGGER
// ═══════════════════════════════════════════════════════════════════════════════

function log(message, type = 'info') {
    const console = document.getElementById('console');
    const line = document.createElement('div');
    line.className = `console-line ${type}`;

    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    line.innerHTML = `<span class="time">[${time}]</span> ${message}`;

    console.appendChild(line);
    console.scrollTop = console.scrollHeight;

    // Keep only last 50 lines
    while (console.children.length > 50) {
        console.removeChild(console.firstChild);
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//   UI FUNCTIONS
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
    ipcRenderer.invoke('close-window');
}

function toggleSound() {
    const enabled = audio.toggle();
    const btn = document.getElementById('soundToggle');
    btn.textContent = enabled ? '🔊' : '🔇';
    btn.classList.toggle('muted', !enabled);
    if (enabled) audio.playClick();
}

function selectNav(element) {
    audio.playClick();
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    log(`Navigated to ${element.querySelector('.nav-label').textContent}`, 'info');
}

// Quick Actions
function startGrading() {
    audio.playClick();
    log('Starting grading session...', 'system');
    audio.playNotification();
}

function openCamera() {
    audio.playClick();
    log('Opening webcam module...', 'system');
}

function openAPI() {
    audio.playClick();
    ipcRenderer.invoke('open-url', 'http://localhost:8000/docs');
    log('Opening API documentation...', 'info');
}

function exportData() {
    audio.playClick();
    log('Exporting collection data...', 'system');
    setTimeout(() => {
        log('Export complete: collection_export.json', 'success');
        audio.playSuccess();
    }, 1500);
}

// ═══════════════════════════════════════════════════════════════════════════════
//   DATA UPDATES
// ═══════════════════════════════════════════════════════════════════════════════

function updateSystemStats(stats) {
    document.getElementById('cpu-value').textContent = `${stats.cpu.usage}%`;
    document.getElementById('cpu-bar').style.width = `${stats.cpu.usage}%`;

    document.getElementById('mem-value').textContent = `${stats.memory.used} / ${stats.memory.total} GB`;
    document.getElementById('mem-bar').style.width = `${stats.memory.percent}%`;
}

async function checkBackend() {
    const status = document.getElementById('backend-status');
    const online = await ipcRenderer.invoke('check-backend');
    status.textContent = online ? '● Online' : '○ Offline';
    status.style.color = online ? '#00ff41' : '#ff4444';
}

function populateActivity() {
    const activities = [
        { time: '2 min ago', title: 'Graded Amazing Spider-Man #129', grade: '8.5' },
        { time: '15 min ago', title: 'Graded X-Men #1', grade: '7.0' },
        { time: '32 min ago', title: 'Graded Batman #404', grade: '9.2' },
        { time: '1 hour ago', title: 'Graded Hulk #181', grade: '6.5' },
        { time: '2 hours ago', title: 'Graded Action Comics #1', grade: '4.0' },
    ];

    const list = document.getElementById('activity-list');
    list.innerHTML = '';

    activities.forEach(act => {
        const item = document.createElement('div');
        item.className = 'activity-item';
        item.innerHTML = `
            <div class="activity-icon">📚</div>
            <div class="activity-info">
                <div class="activity-title">${act.title}</div>
                <div class="activity-time">${act.time}</div>
            </div>
            <div class="activity-grade">${act.grade}</div>
        `;
        list.appendChild(item);
    });
}

function animateStats() {
    // Animate stat values
    const targets = {
        'stat-total': 247,
        'stat-today': 12,
        'stat-grade': 7.8,
        'stat-queue': 5
    };

    Object.entries(targets).forEach(([id, target]) => {
        const el = document.getElementById(id);
        const isFloat = id === 'stat-grade';
        let current = 0;
        const increment = target / 30;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            el.textContent = isFloat ? current.toFixed(1) : Math.floor(current);
        }, 30);
    });
}

// ═══════════════════════════════════════════════════════════════════════════════
//   INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Matrix Rain
    const matrixCanvas = document.getElementById('matrix-canvas');
    const matrix = new MatrixRain(matrixCanvas);
    matrix.animate();

    // Initialize Wave Visualizer
    const waveCanvas = document.getElementById('wave-canvas');
    const wave = new WaveVisualizer(waveCanvas);
    wave.animate();

    // Initialize audio on first click
    document.body.addEventListener('click', () => {
        audio.init();
    }, { once: true });

    // Startup sequence
    setTimeout(() => {
        audio.init();
        audio.playStartup();
    }, 300);

    // Initial logs
    log('Matrix Dashboard initialized', 'system');
    log('Connecting to backend...', 'info');

    // Check backend
    checkBackend();
    setInterval(checkBackend, 5000);

    // Populate activity
    populateActivity();

    // Animate stats
    setTimeout(animateStats, 500);

    // Add hover sounds
    document.querySelectorAll('.nav-item, .action-btn, .stat-card, .provider-badge').forEach(el => {
        el.addEventListener('mouseenter', () => audio.playHover());
    });

    // Listen for system stats updates
    ipcRenderer.on('system-stats', (event, stats) => {
        updateSystemStats(stats);
    });

    // Listen for backend logs
    ipcRenderer.on('backend-log', (event, data) => {
        const lines = data.split('\n').filter(l => l.trim());
        lines.forEach(line => {
            if (line.length > 80) line = line.substring(0, 80) + '...';
            if (line.includes('ERROR')) log(line, 'error');
            else if (line.includes('WARNING')) log(line, 'warning');
            else log(line, 'info');
        });
    });

    setTimeout(() => {
        log('Backend connection established', 'success');
        log('System ready', 'success');
        audio.playSuccess();
    }, 2000);
});
