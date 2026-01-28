const { ipcRenderer } = require('electron');

// ═══════════════════════════════════════════════════════════════════════════════
//   BREE AVATAR RENDERER - Multi-Style AI Avatar with Lip Sync & Emotions
//   Styles: A) Holographic  B) Realistic  C) Stylized/Pixar  D) Anime
// ═══════════════════════════════════════════════════════════════════════════════

// Colors
const COLORS = {
    purple: '#9d00ff',
    purpleDark: '#6a0dad',
    purpleLight: '#c77dff',
    echoOrange: '#ff6b00',
    echoOrangeLight: '#ff9248',
    magenta: '#ff00ff',
    cyan: '#00ffff',
    skinTone: '#f5d0c5',
    skinToneDark: '#d4a69a',
    hairDark: '#1a0a0a',
    hairHighlight: '#3d1f1f',
    lipColor: '#cc4466',
    eyeWhite: '#ffffff',
    eyeIris: '#4a3728',
    eyePupil: '#000000'
};

// Emotion states matching Bree's backend
const EMOTIONS = {
    ECSTATIC: { eyeScale: 1.2, browOffset: -8, mouthCurve: 0.8, blushIntensity: 0.4 },
    IMPRESSED: { eyeScale: 1.1, browOffset: -5, mouthCurve: 0.5, blushIntensity: 0.2 },
    PLEASED: { eyeScale: 1.0, browOffset: -3, mouthCurve: 0.3, blushIntensity: 0.1 },
    NEUTRAL: { eyeScale: 1.0, browOffset: 0, mouthCurve: 0, blushIntensity: 0 },
    ANNOYED: { eyeScale: 0.9, browOffset: 3, mouthCurve: -0.2, blushIntensity: 0 },
    PISSED: { eyeScale: 0.85, browOffset: 6, mouthCurve: -0.4, blushIntensity: 0.1 },
    FURIOUS: { eyeScale: 0.8, browOffset: 8, mouthCurve: -0.6, blushIntensity: 0.2 },
    NUCLEAR: { eyeScale: 0.75, browOffset: 10, mouthCurve: -0.8, blushIntensity: 0.3 }
};

// Viseme mappings for lip sync (phoneme to mouth shape)
const VISEMES = {
    'sil': { width: 0.3, height: 0.1, openness: 0 },      // Silence
    'aa': { width: 0.6, height: 0.7, openness: 0.8 },     // "father"
    'ae': { width: 0.7, height: 0.5, openness: 0.6 },     // "cat"
    'ah': { width: 0.5, height: 0.6, openness: 0.7 },     // "but"
    'ao': { width: 0.4, height: 0.7, openness: 0.75 },    // "dog"
    'aw': { width: 0.4, height: 0.6, openness: 0.65 },    // "cow"
    'ay': { width: 0.5, height: 0.5, openness: 0.5 },     // "say"
    'b': { width: 0.2, height: 0.05, openness: 0 },       // "boy"
    'ch': { width: 0.3, height: 0.2, openness: 0.15 },    // "chair"
    'd': { width: 0.35, height: 0.15, openness: 0.1 },    // "day"
    'dh': { width: 0.4, height: 0.2, openness: 0.15 },    // "the"
    'eh': { width: 0.55, height: 0.4, openness: 0.45 },   // "pet"
    'er': { width: 0.4, height: 0.35, openness: 0.35 },   // "bird"
    'ey': { width: 0.5, height: 0.35, openness: 0.35 },   // "ate"
    'f': { width: 0.35, height: 0.1, openness: 0.05 },    // "for"
    'g': { width: 0.4, height: 0.3, openness: 0.25 },     // "go"
    'hh': { width: 0.45, height: 0.4, openness: 0.4 },    // "he"
    'ih': { width: 0.45, height: 0.3, openness: 0.3 },    // "it"
    'iy': { width: 0.5, height: 0.25, openness: 0.2 },    // "eat"
    'jh': { width: 0.35, height: 0.2, openness: 0.15 },   // "joy"
    'k': { width: 0.4, height: 0.25, openness: 0.2 },     // "key"
    'l': { width: 0.4, height: 0.2, openness: 0.15 },     // "lay"
    'm': { width: 0.25, height: 0.05, openness: 0 },      // "man"
    'n': { width: 0.35, height: 0.1, openness: 0.05 },    // "no"
    'ng': { width: 0.4, height: 0.2, openness: 0.15 },    // "sing"
    'ow': { width: 0.35, height: 0.5, openness: 0.55 },   // "go"
    'oy': { width: 0.4, height: 0.5, openness: 0.5 },     // "boy"
    'p': { width: 0.2, height: 0.05, openness: 0 },       // "pay"
    'r': { width: 0.35, height: 0.25, openness: 0.2 },    // "red"
    's': { width: 0.3, height: 0.1, openness: 0.05 },     // "say"
    'sh': { width: 0.3, height: 0.15, openness: 0.1 },    // "she"
    't': { width: 0.35, height: 0.1, openness: 0.05 },    // "to"
    'th': { width: 0.4, height: 0.15, openness: 0.1 },    // "thin"
    'uh': { width: 0.4, height: 0.4, openness: 0.4 },     // "book"
    'uw': { width: 0.3, height: 0.45, openness: 0.5 },    // "too"
    'v': { width: 0.35, height: 0.1, openness: 0.05 },    // "very"
    'w': { width: 0.3, height: 0.35, openness: 0.35 },    // "way"
    'y': { width: 0.45, height: 0.25, openness: 0.2 },    // "yes"
    'z': { width: 0.3, height: 0.1, openness: 0.05 },     // "zoo"
    'zh': { width: 0.35, height: 0.15, openness: 0.1 }    // "measure"
};

class BreeAvatar {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.style = 'holographic'; // holographic, realistic, stylized, anime
        this.emotion = EMOTIONS.NEUTRAL;
        this.emotionName = 'NEUTRAL';

        // Animation state
        this.time = 0;
        this.blinkTimer = 0;
        this.blinkState = 0; // 0 = open, 1 = closing, 2 = closed, 3 = opening
        this.nextBlink = Math.random() * 3 + 2;

        // Lip sync state
        this.currentViseme = VISEMES['sil'];
        this.targetViseme = VISEMES['sil'];
        this.visemeBlend = 0;
        this.isSpeaking = false;

        // Idle animations
        this.headTilt = 0;
        this.headTiltTarget = 0;
        this.eyeLookX = 0;
        this.eyeLookY = 0;
        this.eyeLookTargetX = 0;
        this.eyeLookTargetY = 0;
        this.breathPhase = 0;

        // Micro expressions
        this.microExpressionTimer = 0;
        this.microExpression = null;

        this.resize();
        window.addEventListener('resize', () => this.resize());

        this.startIdleAnimations();
    }

    resize() {
        this.canvas.width = this.canvas.offsetWidth * 2; // 2x for retina
        this.canvas.height = this.canvas.offsetHeight * 2;
        this.ctx.scale(2, 2);
        this.width = this.canvas.offsetWidth;
        this.height = this.canvas.offsetHeight;
        this.centerX = this.width / 2;
        this.centerY = this.height / 2;
    }

    setStyle(style) {
        this.style = style;
        document.getElementById('styleIndicator').textContent = style.toUpperCase();

        // Update holo overlay visibility
        const holoOverlay = document.getElementById('holoOverlay');
        holoOverlay.style.display = style === 'holographic' ? 'block' : 'none';
    }

    setEmotion(emotionName) {
        this.emotionName = emotionName;
        this.emotion = EMOTIONS[emotionName] || EMOTIONS.NEUTRAL;
        document.getElementById('emotionIndicator').textContent = emotionName;
    }

    setViseme(visemeName) {
        this.targetViseme = VISEMES[visemeName] || VISEMES['sil'];
    }

    startSpeaking() {
        this.isSpeaking = true;
        document.getElementById('speakingWaves').classList.add('active');
    }

    stopSpeaking() {
        this.isSpeaking = false;
        this.targetViseme = VISEMES['sil'];
        document.getElementById('speakingWaves').classList.remove('active');
    }

    startIdleAnimations() {
        // Random eye movement
        setInterval(() => {
            if (!this.isSpeaking || Math.random() > 0.7) {
                this.eyeLookTargetX = (Math.random() - 0.5) * 8;
                this.eyeLookTargetY = (Math.random() - 0.5) * 4;
            }
        }, 2000 + Math.random() * 2000);

        // Random head tilt
        setInterval(() => {
            this.headTiltTarget = (Math.random() - 0.5) * 10;
        }, 3000 + Math.random() * 3000);

        // Random micro expressions
        setInterval(() => {
            if (Math.random() > 0.7) {
                this.microExpression = {
                    type: ['smirk', 'eyebrowRaise', 'noseScrunch'][Math.floor(Math.random() * 3)],
                    intensity: Math.random() * 0.5,
                    duration: 0.5 + Math.random() * 0.5
                };
                this.microExpressionTimer = 0;
            }
        }, 4000 + Math.random() * 4000);
    }

    update(deltaTime) {
        this.time += deltaTime;
        this.breathPhase += deltaTime * 1.5;

        // Blink logic
        this.blinkTimer += deltaTime;
        if (this.blinkState === 0 && this.blinkTimer >= this.nextBlink) {
            this.blinkState = 1;
            this.blinkTimer = 0;
        } else if (this.blinkState === 1 && this.blinkTimer >= 0.05) {
            this.blinkState = 2;
            this.blinkTimer = 0;
        } else if (this.blinkState === 2 && this.blinkTimer >= 0.08) {
            this.blinkState = 3;
            this.blinkTimer = 0;
        } else if (this.blinkState === 3 && this.blinkTimer >= 0.05) {
            this.blinkState = 0;
            this.blinkTimer = 0;
            this.nextBlink = Math.random() * 3 + 2;
        }

        // Smooth interpolations
        this.headTilt += (this.headTiltTarget - this.headTilt) * 0.05;
        this.eyeLookX += (this.eyeLookTargetX - this.eyeLookX) * 0.1;
        this.eyeLookY += (this.eyeLookTargetY - this.eyeLookY) * 0.1;

        // Viseme blending
        this.currentViseme = {
            width: this.currentViseme.width + (this.targetViseme.width - this.currentViseme.width) * 0.3,
            height: this.currentViseme.height + (this.targetViseme.height - this.currentViseme.height) * 0.3,
            openness: this.currentViseme.openness + (this.targetViseme.openness - this.currentViseme.openness) * 0.3
        };

        // Micro expression
        if (this.microExpression) {
            this.microExpressionTimer += deltaTime;
            if (this.microExpressionTimer >= this.microExpression.duration) {
                this.microExpression = null;
            }
        }
    }

    draw() {
        this.ctx.clearRect(0, 0, this.width, this.height);

        // Save and apply head tilt
        this.ctx.save();
        this.ctx.translate(this.centerX, this.centerY);
        this.ctx.rotate(this.headTilt * Math.PI / 180);
        this.ctx.translate(-this.centerX, -this.centerY);

        // Breathing offset
        const breathOffset = Math.sin(this.breathPhase) * 2;

        switch (this.style) {
            case 'holographic':
                this.drawHolographic(breathOffset);
                break;
            case 'realistic':
                this.drawRealistic(breathOffset);
                break;
            case 'stylized':
                this.drawStylized(breathOffset);
                break;
            case 'anime':
                this.drawAnime(breathOffset);
                break;
        }

        this.ctx.restore();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //   STYLE A: HOLOGRAPHIC (Cortana-style)
    // ═══════════════════════════════════════════════════════════════════════
    drawHolographic(breathOffset) {
        const ctx = this.ctx;
        const cx = this.centerX;
        const cy = this.centerY - 50 + breathOffset;

        // Holographic glow effect
        const glowGradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, 200);
        glowGradient.addColorStop(0, 'rgba(157, 0, 255, 0.3)');
        glowGradient.addColorStop(0.5, 'rgba(255, 107, 0, 0.15)');
        glowGradient.addColorStop(1, 'rgba(157, 0, 255, 0)');

        ctx.fillStyle = glowGradient;
        ctx.beginPath();
        ctx.arc(cx, cy, 200, 0, Math.PI * 2);
        ctx.fill();

        // Hair (flowing, ethereal)
        this.drawHolographicHair(cx, cy - 80);

        // Face outline (glowing wireframe style)
        ctx.strokeStyle = COLORS.purpleLight;
        ctx.lineWidth = 2;
        ctx.shadowColor = COLORS.purple;
        ctx.shadowBlur = 20;

        // Face shape
        ctx.beginPath();
        ctx.ellipse(cx, cy, 70, 90, 0, 0, Math.PI * 2);
        ctx.stroke();

        // Neck
        ctx.beginPath();
        ctx.moveTo(cx - 25, cy + 85);
        ctx.lineTo(cx - 30, cy + 140);
        ctx.moveTo(cx + 25, cy + 85);
        ctx.lineTo(cx + 30, cy + 140);
        ctx.stroke();

        // Shoulders hint
        ctx.beginPath();
        ctx.moveTo(cx - 30, cy + 140);
        ctx.quadraticCurveTo(cx - 80, cy + 150, cx - 100, cy + 200);
        ctx.moveTo(cx + 30, cy + 140);
        ctx.quadraticCurveTo(cx + 80, cy + 150, cx + 100, cy + 200);
        ctx.stroke();

        // Eyes
        this.drawHolographicEyes(cx, cy - 10);

        // Nose
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx - 5, cy + 25);
        ctx.lineTo(cx, cy + 30);
        ctx.stroke();

        // Mouth with lip sync
        this.drawHolographicMouth(cx, cy + 50);

        // Data particles
        this.drawHoloParticles(cx, cy);

        ctx.shadowBlur = 0;
    }

    drawHolographicHair(x, y) {
        const ctx = this.ctx;
        ctx.strokeStyle = COLORS.purpleLight;
        ctx.lineWidth = 1.5;

        // Flowing strands
        for (let i = 0; i < 30; i++) {
            const startX = x + (i - 15) * 5;
            const wave = Math.sin(this.time * 2 + i * 0.3) * 10;

            ctx.beginPath();
            ctx.moveTo(startX, y);
            ctx.quadraticCurveTo(
                startX + wave, y + 60,
                startX + wave * 0.5 + (i - 15) * 2, y + 120 + Math.abs(i - 15) * 3
            );
            ctx.stroke();
        }
    }

    drawHolographicEyes(x, y) {
        const ctx = this.ctx;
        const eyeSpacing = 35;
        const blinkScale = this.getBlinkScale();

        [-1, 1].forEach(side => {
            const ex = x + side * eyeSpacing + this.eyeLookX;
            const ey = y + this.eyeLookY;

            // Eye glow
            ctx.fillStyle = 'rgba(0, 255, 255, 0.5)';
            ctx.beginPath();
            ctx.ellipse(ex, ey, 15 * this.emotion.eyeScale, 10 * blinkScale * this.emotion.eyeScale, 0, 0, Math.PI * 2);
            ctx.fill();

            // Iris
            ctx.fillStyle = COLORS.cyan;
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.5, ey + this.eyeLookY * 0.3, 6, 0, Math.PI * 2);
            ctx.fill();

            // Pupil
            ctx.fillStyle = COLORS.purple;
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.5, ey + this.eyeLookY * 0.3, 3, 0, Math.PI * 2);
            ctx.fill();

            // Eyebrow
            ctx.strokeStyle = COLORS.purpleLight;
            ctx.beginPath();
            ctx.moveTo(ex - 15, ey - 18 + this.emotion.browOffset);
            ctx.quadraticCurveTo(ex, ey - 22 + this.emotion.browOffset * 0.5, ex + 15, ey - 16 + this.emotion.browOffset);
            ctx.stroke();
        });
    }

    drawHolographicMouth(x, y) {
        const ctx = this.ctx;
        const mouthWidth = 30 * this.currentViseme.width;
        const mouthHeight = 20 * this.currentViseme.height;
        const openness = this.currentViseme.openness;
        const curve = this.emotion.mouthCurve;

        ctx.strokeStyle = COLORS.purpleLight;
        ctx.fillStyle = 'rgba(157, 0, 255, 0.3)';

        // Upper lip
        ctx.beginPath();
        ctx.moveTo(x - mouthWidth, y);
        ctx.quadraticCurveTo(x, y - 5 + curve * 5, x + mouthWidth, y);

        // Lower lip
        ctx.quadraticCurveTo(x, y + mouthHeight + curve * 3, x - mouthWidth, y);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Teeth hint when open
        if (openness > 0.3) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
            ctx.fillRect(x - mouthWidth * 0.7, y + 2, mouthWidth * 1.4, 4);
        }
    }

    drawHoloParticles(cx, cy) {
        const ctx = this.ctx;

        for (let i = 0; i < 20; i++) {
            const angle = (this.time * 0.5 + i * 0.5) % (Math.PI * 2);
            const radius = 100 + Math.sin(this.time + i) * 30;
            const px = cx + Math.cos(angle) * radius;
            const py = cy + Math.sin(angle) * radius * 0.5;
            const size = 2 + Math.sin(this.time * 2 + i) * 1;

            ctx.fillStyle = i % 2 === 0 ? COLORS.purple : COLORS.echoOrange;
            ctx.globalAlpha = 0.5 + Math.sin(this.time + i) * 0.3;
            ctx.beginPath();
            ctx.arc(px, py, size, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    //   STYLE B: REALISTIC
    // ═══════════════════════════════════════════════════════════════════════
    drawRealistic(breathOffset) {
        const ctx = this.ctx;
        const cx = this.centerX;
        const cy = this.centerY - 30 + breathOffset;

        // Hair behind
        this.drawRealisticHairBack(cx, cy - 70);

        // Neck and shoulders
        this.drawRealisticBody(cx, cy + 100);

        // Face
        const faceGradient = ctx.createRadialGradient(cx, cy - 20, 0, cx, cy, 100);
        faceGradient.addColorStop(0, COLORS.skinTone);
        faceGradient.addColorStop(1, COLORS.skinToneDark);

        ctx.fillStyle = faceGradient;
        ctx.beginPath();
        ctx.ellipse(cx, cy, 65, 85, 0, 0, Math.PI * 2);
        ctx.fill();

        // Blush
        if (this.emotion.blushIntensity > 0) {
            ctx.fillStyle = `rgba(255, 150, 150, ${this.emotion.blushIntensity})`;
            ctx.beginPath();
            ctx.ellipse(cx - 45, cy + 10, 20, 12, 0.2, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.ellipse(cx + 45, cy + 10, 20, 12, -0.2, 0, Math.PI * 2);
            ctx.fill();
        }

        // Eyes
        this.drawRealisticEyes(cx, cy - 5);

        // Nose
        ctx.fillStyle = COLORS.skinToneDark;
        ctx.beginPath();
        ctx.moveTo(cx, cy + 5);
        ctx.lineTo(cx - 8, cy + 30);
        ctx.quadraticCurveTo(cx, cy + 35, cx + 8, cy + 30);
        ctx.closePath();
        ctx.fill();

        // Mouth
        this.drawRealisticMouth(cx, cy + 50);

        // Hair front
        this.drawRealisticHairFront(cx, cy - 70);

        // Subtle purple/orange glow
        ctx.shadowColor = COLORS.purple;
        ctx.shadowBlur = 30;
        ctx.strokeStyle = 'rgba(157, 0, 255, 0.2)';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.ellipse(cx, cy, 68, 88, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.shadowBlur = 0;
    }

    drawRealisticHairBack(x, y) {
        const ctx = this.ctx;

        // Dark flowing hair
        const hairGradient = ctx.createLinearGradient(x - 80, y, x + 80, y + 200);
        hairGradient.addColorStop(0, COLORS.hairHighlight);
        hairGradient.addColorStop(0.5, COLORS.hairDark);
        hairGradient.addColorStop(1, COLORS.hairDark);

        ctx.fillStyle = hairGradient;
        ctx.beginPath();
        ctx.moveTo(x - 70, y + 20);
        ctx.quadraticCurveTo(x - 90, y + 100, x - 75, y + 200);
        ctx.lineTo(x + 75, y + 200);
        ctx.quadraticCurveTo(x + 90, y + 100, x + 70, y + 20);
        ctx.quadraticCurveTo(x, y - 30, x - 70, y + 20);
        ctx.fill();
    }

    drawRealisticHairFront(x, y) {
        const ctx = this.ctx;

        ctx.fillStyle = COLORS.hairDark;

        // Bangs
        ctx.beginPath();
        ctx.moveTo(x - 55, y + 30);
        ctx.quadraticCurveTo(x - 30, y + 10, x - 10, y + 40);
        ctx.quadraticCurveTo(x, y + 20, x + 10, y + 45);
        ctx.quadraticCurveTo(x + 30, y + 15, x + 55, y + 35);
        ctx.quadraticCurveTo(x + 60, y, x + 40, y - 20);
        ctx.quadraticCurveTo(x, y - 40, x - 40, y - 20);
        ctx.quadraticCurveTo(x - 60, y, x - 55, y + 30);
        ctx.fill();

        // Hair strands with subtle wave
        ctx.strokeStyle = COLORS.hairHighlight;
        ctx.lineWidth = 2;
        for (let i = 0; i < 8; i++) {
            const wave = Math.sin(this.time + i) * 3;
            ctx.beginPath();
            ctx.moveTo(x - 40 + i * 10, y + 30);
            ctx.quadraticCurveTo(x - 35 + i * 10 + wave, y + 60, x - 30 + i * 10, y + 90);
            ctx.stroke();
        }
    }

    drawRealisticBody(x, y) {
        const ctx = this.ctx;

        // Neck
        const neckGradient = ctx.createLinearGradient(x, y - 20, x, y + 30);
        neckGradient.addColorStop(0, COLORS.skinTone);
        neckGradient.addColorStop(1, COLORS.skinToneDark);

        ctx.fillStyle = neckGradient;
        ctx.beginPath();
        ctx.moveTo(x - 20, y - 20);
        ctx.lineTo(x - 25, y + 30);
        ctx.lineTo(x + 25, y + 30);
        ctx.lineTo(x + 20, y - 20);
        ctx.fill();

        // Shoulders with provocative neckline hint (classy but alluring)
        ctx.fillStyle = COLORS.purpleDark;
        ctx.beginPath();
        ctx.moveTo(x - 25, y + 30);
        ctx.quadraticCurveTo(x - 60, y + 40, x - 100, y + 100);
        ctx.lineTo(x + 100, y + 100);
        ctx.quadraticCurveTo(x + 60, y + 40, x + 25, y + 30);
        ctx.fill();

        // Dress strap hints
        ctx.strokeStyle = COLORS.echoOrange;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(x - 20, y + 32);
        ctx.lineTo(x - 40, y + 50);
        ctx.moveTo(x + 20, y + 32);
        ctx.lineTo(x + 40, y + 50);
        ctx.stroke();
    }

    drawRealisticEyes(x, y) {
        const ctx = this.ctx;
        const eyeSpacing = 30;
        const blinkScale = this.getBlinkScale();

        [-1, 1].forEach(side => {
            const ex = x + side * eyeSpacing;
            const ey = y + this.eyeLookY * 0.5;

            // Eye white
            ctx.fillStyle = COLORS.eyeWhite;
            ctx.beginPath();
            ctx.ellipse(ex, ey, 14 * this.emotion.eyeScale, 9 * blinkScale * this.emotion.eyeScale, side * 0.1, 0, Math.PI * 2);
            ctx.fill();

            // Iris
            ctx.fillStyle = COLORS.eyeIris;
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.3, ey + this.eyeLookY * 0.2, 7, 0, Math.PI * 2);
            ctx.fill();

            // Pupil
            ctx.fillStyle = COLORS.eyePupil;
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.3, ey + this.eyeLookY * 0.2, 3, 0, Math.PI * 2);
            ctx.fill();

            // Eye highlight
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.3 + 2, ey + this.eyeLookY * 0.2 - 2, 2, 0, Math.PI * 2);
            ctx.fill();

            // Eyeliner
            ctx.strokeStyle = '#1a0a0a';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.ellipse(ex, ey, 15, 10 * blinkScale, side * 0.1, 0, Math.PI * 2);
            ctx.stroke();

            // Eyebrow
            ctx.strokeStyle = COLORS.hairDark;
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(ex - 12, ey - 15 + this.emotion.browOffset);
            ctx.quadraticCurveTo(ex, ey - 20 + this.emotion.browOffset * 0.7, ex + 12, ey - 14 + this.emotion.browOffset);
            ctx.stroke();

            // Eyelashes
            if (blinkScale > 0.3) {
                ctx.strokeStyle = '#1a0a0a';
                ctx.lineWidth = 1;
                for (let i = 0; i < 5; i++) {
                    const angle = (Math.PI * 0.3) + (i / 4) * (Math.PI * 0.4);
                    ctx.beginPath();
                    ctx.moveTo(ex + Math.cos(angle) * 14, ey - Math.sin(angle) * 9 * blinkScale);
                    ctx.lineTo(ex + Math.cos(angle) * 18, ey - Math.sin(angle) * 13 * blinkScale);
                    ctx.stroke();
                }
            }
        });
    }

    drawRealisticMouth(x, y) {
        const ctx = this.ctx;
        const mouthWidth = 25 * (0.5 + this.currentViseme.width * 0.5);
        const mouthHeight = 15 * this.currentViseme.height;
        const openness = this.currentViseme.openness;
        const curve = this.emotion.mouthCurve;

        // Lips
        ctx.fillStyle = COLORS.lipColor;

        // Upper lip
        ctx.beginPath();
        ctx.moveTo(x - mouthWidth, y);
        ctx.quadraticCurveTo(x - mouthWidth * 0.5, y - 4 + curve * 3, x, y - 2 + curve * 2);
        ctx.quadraticCurveTo(x + mouthWidth * 0.5, y - 4 + curve * 3, x + mouthWidth, y);
        ctx.quadraticCurveTo(x, y + 3, x - mouthWidth, y);
        ctx.fill();

        // Lower lip
        ctx.beginPath();
        ctx.moveTo(x - mouthWidth, y + 2);
        ctx.quadraticCurveTo(x, y + mouthHeight + curve * 5, x + mouthWidth, y + 2);
        ctx.quadraticCurveTo(x, y + 5, x - mouthWidth, y + 2);
        ctx.fill();

        // Mouth interior when open
        if (openness > 0.2) {
            ctx.fillStyle = '#3d1f1f';
            ctx.beginPath();
            ctx.ellipse(x, y + mouthHeight * 0.3, mouthWidth * 0.7, mouthHeight * openness * 0.5, 0, 0, Math.PI * 2);
            ctx.fill();

            // Teeth
            if (openness > 0.4) {
                ctx.fillStyle = '#f5f5f5';
                ctx.fillRect(x - mouthWidth * 0.5, y, mouthWidth, 5);
            }
        }

        // Lip gloss highlight
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.beginPath();
        ctx.ellipse(x - 5, y + mouthHeight * 0.4, 8, 3, 0.2, 0, Math.PI * 2);
        ctx.fill();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //   STYLE C: STYLIZED (Pixar-like)
    // ═══════════════════════════════════════════════════════════════════════
    drawStylized(breathOffset) {
        const ctx = this.ctx;
        const cx = this.centerX;
        const cy = this.centerY - 20 + breathOffset;

        // Soft glow background
        const bgGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, 150);
        bgGlow.addColorStop(0, 'rgba(255, 107, 0, 0.1)');
        bgGlow.addColorStop(1, 'rgba(157, 0, 255, 0.05)');
        ctx.fillStyle = bgGlow;
        ctx.beginPath();
        ctx.arc(cx, cy, 150, 0, Math.PI * 2);
        ctx.fill();

        // Hair back
        this.drawStylizedHairBack(cx, cy - 60);

        // Face (rounder, more cartoon)
        const faceGradient = ctx.createRadialGradient(cx, cy, 0, cx, cy + 30, 120);
        faceGradient.addColorStop(0, '#ffe4d6');
        faceGradient.addColorStop(1, '#e8c4b8');

        ctx.fillStyle = faceGradient;
        ctx.beginPath();
        ctx.ellipse(cx, cy + 10, 75, 85, 0, 0, Math.PI * 2);
        ctx.fill();

        // Neck and body
        this.drawStylizedBody(cx, cy + 90);

        // Blush (always a little)
        ctx.fillStyle = `rgba(255, 180, 180, ${0.3 + this.emotion.blushIntensity})`;
        ctx.beginPath();
        ctx.ellipse(cx - 50, cy + 25, 18, 10, 0.3, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(cx + 50, cy + 25, 18, 10, -0.3, 0, Math.PI * 2);
        ctx.fill();

        // Big expressive eyes
        this.drawStylizedEyes(cx, cy);

        // Small cute nose
        ctx.fillStyle = '#dba89a';
        ctx.beginPath();
        ctx.ellipse(cx, cy + 35, 8, 5, 0, 0, Math.PI);
        ctx.fill();

        // Mouth
        this.drawStylizedMouth(cx, cy + 55);

        // Hair front
        this.drawStylizedHairFront(cx, cy - 60);
    }

    drawStylizedHairBack(x, y) {
        const ctx = this.ctx;

        ctx.fillStyle = '#2a1515';
        ctx.beginPath();
        ctx.moveTo(x - 80, y + 40);
        ctx.quadraticCurveTo(x - 100, y + 120, x - 70, y + 200);
        ctx.lineTo(x + 70, y + 200);
        ctx.quadraticCurveTo(x + 100, y + 120, x + 80, y + 40);
        ctx.quadraticCurveTo(x, y - 40, x - 80, y + 40);
        ctx.fill();
    }

    drawStylizedHairFront(x, y) {
        const ctx = this.ctx;

        // Main hair shape
        ctx.fillStyle = '#2a1515';
        ctx.beginPath();
        ctx.moveTo(x - 70, y + 50);

        // Flowing bangs with wave
        const wave = Math.sin(this.time * 1.5) * 5;
        ctx.quadraticCurveTo(x - 40 + wave, y + 30, x - 20, y + 55 + wave);
        ctx.quadraticCurveTo(x, y + 35, x + 20, y + 55 - wave);
        ctx.quadraticCurveTo(x + 40 - wave, y + 30, x + 70, y + 50);
        ctx.quadraticCurveTo(x + 80, y, x + 50, y - 30);
        ctx.quadraticCurveTo(x, y - 50, x - 50, y - 30);
        ctx.quadraticCurveTo(x - 80, y, x - 70, y + 50);
        ctx.fill();

        // Highlight strands
        ctx.strokeStyle = '#4a2828';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(x - 30, y + 40);
        ctx.quadraticCurveTo(x - 25 + wave, y + 70, x - 20, y + 100);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x + 30, y + 40);
        ctx.quadraticCurveTo(x + 25 - wave, y + 70, x + 20, y + 100);
        ctx.stroke();
    }

    drawStylizedBody(x, y) {
        const ctx = this.ctx;

        // Neck
        ctx.fillStyle = '#ffe4d6';
        ctx.beginPath();
        ctx.moveTo(x - 20, y - 10);
        ctx.lineTo(x - 25, y + 25);
        ctx.lineTo(x + 25, y + 25);
        ctx.lineTo(x + 20, y - 10);
        ctx.fill();

        // Stylish top
        const topGradient = ctx.createLinearGradient(x, y, x, y + 80);
        topGradient.addColorStop(0, COLORS.purpleDark);
        topGradient.addColorStop(1, COLORS.purple);

        ctx.fillStyle = topGradient;
        ctx.beginPath();
        ctx.moveTo(x - 25, y + 25);
        ctx.quadraticCurveTo(x - 70, y + 35, x - 110, y + 120);
        ctx.lineTo(x + 110, y + 120);
        ctx.quadraticCurveTo(x + 70, y + 35, x + 25, y + 25);
        ctx.fill();

        // Orange accent
        ctx.strokeStyle = COLORS.echoOrange;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(x - 15, y + 25);
        ctx.lineTo(x, y + 50);
        ctx.lineTo(x + 15, y + 25);
        ctx.stroke();
    }

    drawStylizedEyes(x, y) {
        const ctx = this.ctx;
        const eyeSpacing = 35;
        const blinkScale = this.getBlinkScale();

        [-1, 1].forEach(side => {
            const ex = x + side * eyeSpacing;
            const ey = y + this.eyeLookY;
            const eyeWidth = 22 * this.emotion.eyeScale;
            const eyeHeight = 25 * blinkScale * this.emotion.eyeScale;

            // Eye white with slight gradient
            const eyeGrad = ctx.createRadialGradient(ex, ey, 0, ex, ey, eyeWidth);
            eyeGrad.addColorStop(0, '#ffffff');
            eyeGrad.addColorStop(1, '#f0f0f0');

            ctx.fillStyle = eyeGrad;
            ctx.beginPath();
            ctx.ellipse(ex, ey, eyeWidth, eyeHeight, 0, 0, Math.PI * 2);
            ctx.fill();

            // Large iris
            const irisGrad = ctx.createRadialGradient(ex, ey, 0, ex, ey, 14);
            irisGrad.addColorStop(0, '#6a4a3a');
            irisGrad.addColorStop(0.7, '#4a2a1a');
            irisGrad.addColorStop(1, '#2a1a0a');

            ctx.fillStyle = irisGrad;
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.3, ey + this.eyeLookY * 0.2, 14, 0, Math.PI * 2);
            ctx.fill();

            // Pupil
            ctx.fillStyle = '#000';
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.3, ey + this.eyeLookY * 0.2, 6, 0, Math.PI * 2);
            ctx.fill();

            // Big sparkle highlights (Disney style)
            ctx.fillStyle = '#fff';
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.3 + 5, ey + this.eyeLookY * 0.2 - 5, 4, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.3 - 3, ey + this.eyeLookY * 0.2 + 5, 2, 0, Math.PI * 2);
            ctx.fill();

            // Eyelid line
            ctx.strokeStyle = '#2a1515';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.ellipse(ex, ey - 2, eyeWidth + 2, eyeHeight, 0, Math.PI, Math.PI * 2);
            ctx.stroke();

            // Thick eyelashes
            ctx.lineWidth = 2;
            for (let i = 0; i < 4; i++) {
                const angle = Math.PI + (i / 3) * Math.PI;
                ctx.beginPath();
                ctx.moveTo(ex + Math.cos(angle) * (eyeWidth + 2), ey - 2 + Math.sin(angle) * eyeHeight);
                ctx.lineTo(ex + Math.cos(angle) * (eyeWidth + 8), ey - 8 + Math.sin(angle) * eyeHeight);
                ctx.stroke();
            }

            // Expressive eyebrow
            ctx.lineWidth = 5;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(ex - 18, ey - 30 + this.emotion.browOffset);
            ctx.quadraticCurveTo(ex, ey - 38 + this.emotion.browOffset * 0.7, ex + 18, ey - 28 + this.emotion.browOffset);
            ctx.stroke();
            ctx.lineCap = 'butt';
        });
    }

    drawStylizedMouth(x, y) {
        const ctx = this.ctx;
        const mouthWidth = 28 * (0.6 + this.currentViseme.width * 0.4);
        const mouthHeight = 18 * this.currentViseme.height;
        const openness = this.currentViseme.openness;
        const curve = this.emotion.mouthCurve;

        // Lip color
        ctx.fillStyle = '#e86b8a';

        if (openness > 0.2) {
            // Open mouth
            ctx.beginPath();
            ctx.ellipse(x, y, mouthWidth, mouthHeight * (0.5 + openness * 0.5), 0, 0, Math.PI * 2);
            ctx.fill();

            // Inner mouth
            ctx.fillStyle = '#4a1a2a';
            ctx.beginPath();
            ctx.ellipse(x, y, mouthWidth * 0.8, mouthHeight * openness * 0.6, 0, 0, Math.PI * 2);
            ctx.fill();

            // Tongue hint
            if (openness > 0.5) {
                ctx.fillStyle = '#e86b8a';
                ctx.beginPath();
                ctx.ellipse(x, y + mouthHeight * 0.3, mouthWidth * 0.4, mouthHeight * 0.2, 0, 0, Math.PI);
                ctx.fill();
            }

            // Teeth
            ctx.fillStyle = '#fff';
            ctx.beginPath();
            ctx.ellipse(x, y - mouthHeight * 0.2, mouthWidth * 0.6, 5, 0, 0, Math.PI);
            ctx.fill();
        } else {
            // Closed/smile
            ctx.strokeStyle = '#e86b8a';
            ctx.lineWidth = 4;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(x - mouthWidth, y);
            ctx.quadraticCurveTo(x, y + 15 * curve + 5, x + mouthWidth, y);
            ctx.stroke();
            ctx.lineCap = 'butt';
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //   STYLE D: ANIME
    // ═══════════════════════════════════════════════════════════════════════
    drawAnime(breathOffset) {
        const ctx = this.ctx;
        const cx = this.centerX;
        const cy = this.centerY - 10 + breathOffset;

        // Sparkle background
        this.drawAnimeSparkles(cx, cy);

        // Hair back
        this.drawAnimeHairBack(cx, cy - 50);

        // Face (anime proportions)
        ctx.fillStyle = '#fff5ee';
        ctx.beginPath();
        ctx.moveTo(cx - 60, cy - 30);
        ctx.quadraticCurveTo(cx - 70, cy + 40, cx - 30, cy + 80);
        ctx.quadraticCurveTo(cx, cy + 95, cx + 30, cy + 80);
        ctx.quadraticCurveTo(cx + 70, cy + 40, cx + 60, cy - 30);
        ctx.quadraticCurveTo(cx, cy - 60, cx - 60, cy - 30);
        ctx.fill();

        // Body
        this.drawAnimeBody(cx, cy + 95);

        // Blush marks (anime style)
        ctx.fillStyle = `rgba(255, 150, 180, ${0.4 + this.emotion.blushIntensity})`;
        ctx.beginPath();
        ctx.ellipse(cx - 45, cy + 35, 15, 8, 0.2, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(cx + 45, cy + 35, 15, 8, -0.2, 0, Math.PI * 2);
        ctx.fill();

        // Anime blush lines
        ctx.strokeStyle = 'rgba(255, 100, 150, 0.5)';
        ctx.lineWidth = 2;
        [-1, 1].forEach(side => {
            for (let i = 0; i < 3; i++) {
                ctx.beginPath();
                ctx.moveTo(cx + side * 35 + i * 6, cy + 32);
                ctx.lineTo(cx + side * 40 + i * 6, cy + 38);
                ctx.stroke();
            }
        });

        // HUGE anime eyes
        this.drawAnimeEyes(cx, cy + 5);

        // Small nose (anime style - just a hint)
        ctx.fillStyle = '#ffe0d6';
        ctx.beginPath();
        ctx.moveTo(cx, cy + 40);
        ctx.lineTo(cx - 3, cy + 48);
        ctx.lineTo(cx + 3, cy + 48);
        ctx.closePath();
        ctx.fill();

        // Mouth
        this.drawAnimeMouth(cx, cy + 60);

        // Hair front
        this.drawAnimeHairFront(cx, cy - 50);
    }

    drawAnimeSparkles(cx, cy) {
        const ctx = this.ctx;

        for (let i = 0; i < 8; i++) {
            const angle = (this.time * 0.3 + i * 0.8);
            const radius = 120 + Math.sin(this.time * 2 + i) * 20;
            const sx = cx + Math.cos(angle) * radius;
            const sy = cy + Math.sin(angle) * radius * 0.6;
            const size = 3 + Math.sin(this.time * 3 + i) * 2;

            ctx.fillStyle = i % 2 === 0 ? COLORS.echoOrange : COLORS.purple;
            ctx.globalAlpha = 0.6 + Math.sin(this.time * 2 + i) * 0.3;

            // Four-point star
            ctx.beginPath();
            ctx.moveTo(sx, sy - size * 2);
            ctx.lineTo(sx + size * 0.5, sy);
            ctx.lineTo(sx, sy + size * 2);
            ctx.lineTo(sx - size * 0.5, sy);
            ctx.closePath();
            ctx.fill();

            ctx.beginPath();
            ctx.moveTo(sx - size * 2, sy);
            ctx.lineTo(sx, sy + size * 0.5);
            ctx.lineTo(sx + size * 2, sy);
            ctx.lineTo(sx, sy - size * 0.5);
            ctx.closePath();
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    drawAnimeHairBack(x, y) {
        const ctx = this.ctx;

        // Dark purple-black hair
        const hairGrad = ctx.createLinearGradient(x - 100, y, x + 100, y + 200);
        hairGrad.addColorStop(0, '#1a0a15');
        hairGrad.addColorStop(0.5, '#2a1020');
        hairGrad.addColorStop(1, '#1a0a15');

        ctx.fillStyle = hairGrad;
        ctx.beginPath();
        ctx.moveTo(x - 80, y + 30);
        ctx.quadraticCurveTo(x - 110, y + 150, x - 60, y + 230);
        ctx.lineTo(x + 60, y + 230);
        ctx.quadraticCurveTo(x + 110, y + 150, x + 80, y + 30);
        ctx.quadraticCurveTo(x, y - 50, x - 80, y + 30);
        ctx.fill();
    }

    drawAnimeHairFront(x, y) {
        const ctx = this.ctx;
        const wave = Math.sin(this.time * 2) * 8;

        // Main hair mass
        ctx.fillStyle = '#1a0a15';
        ctx.beginPath();
        ctx.moveTo(x - 75, y + 60);

        // Spiky anime bangs
        ctx.lineTo(x - 60, y + 40);
        ctx.lineTo(x - 45, y + 70 + wave);
        ctx.lineTo(x - 30, y + 35);
        ctx.lineTo(x - 15, y + 65 - wave);
        ctx.lineTo(x, y + 30 + wave * 0.5);
        ctx.lineTo(x + 15, y + 65 + wave);
        ctx.lineTo(x + 30, y + 35);
        ctx.lineTo(x + 45, y + 70 - wave);
        ctx.lineTo(x + 60, y + 40);
        ctx.lineTo(x + 75, y + 60);

        ctx.quadraticCurveTo(x + 85, y - 10, x + 50, y - 40);
        ctx.quadraticCurveTo(x, y - 60, x - 50, y - 40);
        ctx.quadraticCurveTo(x - 85, y - 10, x - 75, y + 60);
        ctx.fill();

        // Purple highlight strands
        ctx.strokeStyle = COLORS.purpleDark;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(x - 30, y + 35);
        ctx.quadraticCurveTo(x - 25 + wave, y + 80, x - 20, y + 120);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x + 30, y + 35);
        ctx.quadraticCurveTo(x + 25 - wave, y + 80, x + 20, y + 120);
        ctx.stroke();

        // Ahoge (hair antenna)
        ctx.fillStyle = '#1a0a15';
        ctx.beginPath();
        ctx.moveTo(x - 5, y - 40);
        ctx.quadraticCurveTo(x + 20 + wave, y - 80, x + 10, y - 100 + wave);
        ctx.quadraticCurveTo(x + 5, y - 70, x + 5, y - 40);
        ctx.fill();
    }

    drawAnimeBody(x, y) {
        const ctx = this.ctx;

        // Neck
        ctx.fillStyle = '#fff5ee';
        ctx.beginPath();
        ctx.moveTo(x - 18, y);
        ctx.lineTo(x - 22, y + 30);
        ctx.lineTo(x + 22, y + 30);
        ctx.lineTo(x + 18, y);
        ctx.fill();

        // Outfit (alluring but classy anime style)
        const outfitGrad = ctx.createLinearGradient(x, y, x, y + 100);
        outfitGrad.addColorStop(0, COLORS.purple);
        outfitGrad.addColorStop(1, COLORS.purpleDark);

        ctx.fillStyle = outfitGrad;
        ctx.beginPath();
        ctx.moveTo(x - 22, y + 30);
        ctx.quadraticCurveTo(x - 50, y + 35, x - 100, y + 120);
        ctx.lineTo(x + 100, y + 120);
        ctx.quadraticCurveTo(x + 50, y + 35, x + 22, y + 30);
        ctx.fill();

        // Orange trim
        ctx.strokeStyle = COLORS.echoOrange;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(x - 20, y + 32);
        ctx.lineTo(x, y + 55);
        ctx.lineTo(x + 20, y + 32);
        ctx.stroke();

        // Collar detail
        ctx.strokeStyle = COLORS.echoOrangeLight;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x - 18, y + 30);
        ctx.lineTo(x - 30, y + 50);
        ctx.moveTo(x + 18, y + 30);
        ctx.lineTo(x + 30, y + 50);
        ctx.stroke();
    }

    drawAnimeEyes(x, y) {
        const ctx = this.ctx;
        const eyeSpacing = 35;
        const blinkScale = this.getBlinkScale();

        [-1, 1].forEach(side => {
            const ex = x + side * eyeSpacing;
            const ey = y + this.eyeLookY;
            const eyeWidth = 28 * this.emotion.eyeScale;
            const eyeHeight = 35 * blinkScale * this.emotion.eyeScale;

            // Eye white
            ctx.fillStyle = '#fff';
            ctx.beginPath();
            ctx.ellipse(ex, ey, eyeWidth, eyeHeight, side * 0.1, 0, Math.PI * 2);
            ctx.fill();

            // Large iris with gradient
            const irisGrad = ctx.createRadialGradient(ex, ey - 5, 0, ex, ey, 20);
            irisGrad.addColorStop(0, COLORS.echoOrange);
            irisGrad.addColorStop(0.5, '#8B4513');
            irisGrad.addColorStop(1, '#4a2510');

            ctx.fillStyle = irisGrad;
            ctx.beginPath();
            ctx.ellipse(ex + this.eyeLookX * 0.2, ey + this.eyeLookY * 0.15, 18, 20, 0, 0, Math.PI * 2);
            ctx.fill();

            // Pupil
            ctx.fillStyle = '#000';
            ctx.beginPath();
            ctx.ellipse(ex + this.eyeLookX * 0.2, ey + this.eyeLookY * 0.15, 8, 10, 0, 0, Math.PI * 2);
            ctx.fill();

            // Anime eye highlights (multiple)
            ctx.fillStyle = '#fff';
            // Main highlight
            ctx.beginPath();
            ctx.ellipse(ex + this.eyeLookX * 0.2 + 7, ey + this.eyeLookY * 0.15 - 8, 6, 8, 0.3, 0, Math.PI * 2);
            ctx.fill();
            // Secondary highlight
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.2 - 5, ey + this.eyeLookY * 0.15 + 8, 3, 0, Math.PI * 2);
            ctx.fill();
            // Small sparkle
            ctx.beginPath();
            ctx.arc(ex + this.eyeLookX * 0.2 + 3, ey + this.eyeLookY * 0.15 - 3, 2, 0, Math.PI * 2);
            ctx.fill();

            // Eye outline
            ctx.strokeStyle = '#1a0a0a';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.ellipse(ex, ey, eyeWidth + 1, eyeHeight + 1, side * 0.1, 0, Math.PI * 2);
            ctx.stroke();

            // Thick top eyelid
            ctx.lineWidth = 5;
            ctx.beginPath();
            ctx.ellipse(ex, ey, eyeWidth + 2, eyeHeight + 2, side * 0.1, Math.PI, Math.PI * 2);
            ctx.stroke();

            // Long anime eyelashes
            ctx.lineWidth = 2;
            for (let i = 0; i < 5; i++) {
                const angle = Math.PI + (i / 4) * Math.PI;
                const lashLength = i === 2 ? 15 : 10;
                ctx.beginPath();
                ctx.moveTo(ex + Math.cos(angle) * (eyeWidth + 2), ey + Math.sin(angle) * (eyeHeight + 2));
                ctx.lineTo(
                    ex + Math.cos(angle - 0.2) * (eyeWidth + lashLength),
                    ey + Math.sin(angle - 0.2) * (eyeHeight + lashLength)
                );
                ctx.stroke();
            }

            // Expressive eyebrows
            ctx.lineWidth = 4;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(ex - 20, ey - 40 + this.emotion.browOffset);
            ctx.quadraticCurveTo(ex, ey - 48 + this.emotion.browOffset * 0.7, ex + 20, ey - 38 + this.emotion.browOffset);
            ctx.stroke();
            ctx.lineCap = 'butt';
        });
    }

    drawAnimeMouth(x, y) {
        const ctx = this.ctx;
        const mouthWidth = 20 * (0.5 + this.currentViseme.width * 0.5);
        const openness = this.currentViseme.openness;
        const curve = this.emotion.mouthCurve;

        ctx.strokeStyle = '#cc4466';
        ctx.fillStyle = '#cc4466';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';

        if (openness > 0.3) {
            // Open anime mouth
            ctx.fillStyle = '#4a1020';
            ctx.beginPath();
            ctx.ellipse(x, y, mouthWidth, 12 * openness, 0, 0, Math.PI * 2);
            ctx.fill();

            // Fang (anime style!)
            if (this.emotion.mouthCurve > 0) {
                ctx.fillStyle = '#fff';
                ctx.beginPath();
                ctx.moveTo(x + 8, y - 4);
                ctx.lineTo(x + 12, y + 5);
                ctx.lineTo(x + 4, y - 2);
                ctx.fill();
            }
        } else {
            // Closed - various expressions
            if (curve > 0.3) {
                // Happy cat mouth :3
                ctx.beginPath();
                ctx.moveTo(x - mouthWidth, y);
                ctx.quadraticCurveTo(x - mouthWidth * 0.3, y + 8, x, y + 2);
                ctx.quadraticCurveTo(x + mouthWidth * 0.3, y + 8, x + mouthWidth, y);
                ctx.stroke();
            } else if (curve < -0.3) {
                // Angry/frown
                ctx.beginPath();
                ctx.moveTo(x - mouthWidth, y + 3);
                ctx.quadraticCurveTo(x, y - 5, x + mouthWidth, y + 3);
                ctx.stroke();
            } else {
                // Neutral small line
                ctx.beginPath();
                ctx.moveTo(x - mouthWidth * 0.6, y);
                ctx.lineTo(x + mouthWidth * 0.6, y);
                ctx.stroke();
            }
        }

        ctx.lineCap = 'butt';
    }

    // ═══════════════════════════════════════════════════════════════════════
    //   HELPER METHODS
    // ═══════════════════════════════════════════════════════════════════════
    getBlinkScale() {
        switch (this.blinkState) {
            case 0: return 1;
            case 1: return 0.3;
            case 2: return 0.1;
            case 3: return 0.5;
            default: return 1;
        }
    }

    animate() {
        const now = performance.now();
        const deltaTime = (now - (this.lastTime || now)) / 1000;
        this.lastTime = now;

        this.update(deltaTime);
        this.draw();
        requestAnimationFrame(() => this.animate());
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//   LIP SYNC ENGINE - Text to Viseme mapping
// ═══════════════════════════════════════════════════════════════════════════════

class LipSyncEngine {
    constructor(avatar) {
        this.avatar = avatar;
        this.visemeQueue = [];
        this.isPlaying = false;

        // Simple phoneme to viseme mapping for text
        this.phonemeMap = {
            'a': 'aa', 'e': 'eh', 'i': 'iy', 'o': 'ow', 'u': 'uw',
            'b': 'b', 'p': 'p', 'm': 'm',
            'f': 'f', 'v': 'v',
            'th': 'th', 'dh': 'dh',
            's': 's', 'z': 'z',
            'sh': 'sh', 'ch': 'ch', 'j': 'jh',
            'r': 'r', 'l': 'l',
            'w': 'w', 'y': 'y',
            'k': 'k', 'g': 'g',
            't': 't', 'd': 'd', 'n': 'n'
        };
    }

    textToVisemes(text) {
        const visemes = [];
        const words = text.toLowerCase().split(/\s+/);

        words.forEach(word => {
            const chars = word.split('');
            chars.forEach((char, i) => {
                let viseme = 'sil';
                const nextChar = chars[i + 1];

                // Check for digraphs
                if (char === 't' && nextChar === 'h') {
                    viseme = 'th';
                } else if (char === 's' && nextChar === 'h') {
                    viseme = 'sh';
                } else if (char === 'c' && nextChar === 'h') {
                    viseme = 'ch';
                } else if (this.phonemeMap[char]) {
                    viseme = this.phonemeMap[char];
                } else if (/[aeiou]/.test(char)) {
                    viseme = this.phonemeMap[char] || 'ah';
                }

                if (viseme !== 'sil') {
                    visemes.push({ viseme, duration: 80 + Math.random() * 40 });
                }
            });

            // Pause between words
            visemes.push({ viseme: 'sil', duration: 50 });
        });

        return visemes;
    }

    async speak(text, emotion = 'NEUTRAL') {
        if (this.isPlaying) {
            this.stop();
        }

        this.avatar.setEmotion(emotion);
        this.visemeQueue = this.textToVisemes(text);
        this.isPlaying = true;
        this.avatar.startSpeaking();

        await this.playVisemes();

        this.avatar.stopSpeaking();
        this.isPlaying = false;
    }

    async playVisemes() {
        for (const item of this.visemeQueue) {
            if (!this.isPlaying) break;

            this.avatar.setViseme(item.viseme);
            await this.sleep(item.duration);
        }
        this.avatar.setViseme('sil');
    }

    stop() {
        this.isPlaying = false;
        this.visemeQueue = [];
        this.avatar.stopSpeaking();
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//   INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════════

let avatar;
let lipSync;

document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('avatar-canvas');
    avatar = new BreeAvatar(canvas);
    lipSync = new LipSyncEngine(avatar);

    // Start animation
    avatar.animate();

    // IPC listeners
    ipcRenderer.on('settings-updated', (event, settings) => {
        if (settings.avatarStyle) {
            avatar.setStyle(settings.avatarStyle);
        }
    });

    ipcRenderer.on('set-style', (event, style) => {
        avatar.setStyle(style);
    });

    ipcRenderer.on('set-emotion', (event, emotion) => {
        avatar.setEmotion(emotion);
    });

    ipcRenderer.on('speak', async (event, data) => {
        const { text, emotion } = data;
        await lipSync.speak(text, emotion || 'NEUTRAL');
    });

    // Demo: cycle through styles on click
    canvas.addEventListener('click', () => {
        const styles = ['holographic', 'realistic', 'stylized', 'anime'];
        const currentIndex = styles.indexOf(avatar.style);
        const nextStyle = styles[(currentIndex + 1) % styles.length];
        avatar.setStyle(nextStyle);
    });

    console.log('Bree Avatar initialized - Click to cycle styles');
});

function closeAvatar() {
    ipcRenderer.invoke('close-avatar-window');
}
