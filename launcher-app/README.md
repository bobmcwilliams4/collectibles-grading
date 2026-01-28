# Collectibles Grading System - High-End Launcher

A production-grade graphical launcher for the Collectibles Grading System featuring:

## Features

### Visual Effects
- **3D Starfield Background** - Animated parallax star field with trails
- **Particle System** - 80+ floating particles with glow effects
- **Holographic Scan Lines** - Cyberpunk-style horizontal scanners
- **Animated Grid Floor** - Perspective 3D grid with movement
- **Glassmorphism UI** - Modern frosted glass effect panels
- **Animated Logo** - Triple rotating rings with pulsing core
- **Progress Animations** - Smooth progress bars with glow effects

### Audio System (Web Audio API)
- **Cinematic Startup Sequence** - Deep bass sweep with rising chord progression
- **Ambient Drone** - Low-frequency background atmosphere with LFO modulation
- **Success Fanfare** - Triumphant chord progression
- **UI Feedback** - Click, hover, and progress sounds
- **Error Sounds** - Distinct audio for failures
- **Master Volume Control** - Toggle sound on/off

### Functionality
- **System Diagnostics** - Checks all system components with visual indicators
- **Backend Launch** - Starts FastAPI server with real-time log streaming
- **GUI Launch** - Opens the Electron desktop application
- **Progress Tracking** - Real-time progress bar with status updates
- **Console Output** - Color-coded log messages with timestamps
- **Frameless Window** - Custom title bar with window controls

## Quick Start

1. **Install Dependencies** (first time only):
   ```
   cd launcher-app
   npm install
   ```

2. **Run the Launcher**:
   - Double-click `RUN_LAUNCHER.bat` in the project root
   - OR run `npm start` in the launcher-app directory

## File Structure

```
launcher-app/
├── main.js          # Electron main process
├── index.html       # UI layout and styles
├── renderer.js      # Frontend logic, audio engine, animations
├── package.json     # Dependencies
├── install.bat      # Installation script
└── assets/
    ├── sounds/      # Audio files (optional)
    └── images/      # Icon files
```

## Audio Notes

The audio system uses the Web Audio API to generate sounds programmatically:
- No external audio files required
- Sounds are synthesized in real-time
- Includes ambient drone, startup fanfare, UI feedback
- Sound can be toggled with the button in the bottom-right corner

## System Requirements

- Node.js 18+
- npm 9+
- Windows 10/11
- 4GB RAM recommended

## Keyboard Shortcuts

- Click anywhere to initialize audio (required by browsers)
- Sound toggle button in bottom-right corner
- Window controls in top-right (minimize, maximize, close)
