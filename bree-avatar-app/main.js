const { app, BrowserWindow, ipcMain, screen, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const os = require('os');

let mainWindow;
let avatarWindow = null;
let pythonProcess = null;

// Settings
let settings = {
    avatarStyle: 'holographic',
    displayMode: 'windowed',
    voiceEnabled: true,
    soundEnabled: true,
    avatarSize: 'medium',
    avatarPosition: 'bottom-right',
    alwaysOnTop: true
};

function createMainWindow() {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    mainWindow = new BrowserWindow({
        width: 1600,
        height: 1000,
        minWidth: 1400,
        minHeight: 900,
        frame: false,
        transparent: true,
        resizable: true,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        },
        icon: path.join(__dirname, 'assets/bree-icon.png'),
        show: false,
        backgroundColor: '#00000000'
    });

    mainWindow.loadFile('index.html');

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        mainWindow.focus();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
        if (avatarWindow) avatarWindow.close();
        if (pythonProcess) pythonProcess.kill();
    });
}

function createAvatarWindow() {
    if (avatarWindow) {
        avatarWindow.focus();
        return;
    }

    const { width, height } = screen.getPrimaryDisplay().workAreaSize;
    const sizes = {
        small: { w: 350, h: 500 },
        medium: { w: 500, h: 700 },
        large: { w: 700, h: 950 }
    };
    const size = sizes[settings.avatarSize] || sizes.medium;

    const positions = {
        'bottom-right': { x: width - size.w - 30, y: height - size.h - 30 },
        'bottom-left': { x: 30, y: height - size.h - 30 },
        'top-right': { x: width - size.w - 30, y: 30 },
        'top-left': { x: 30, y: 30 },
        'center': { x: (width - size.w) / 2, y: (height - size.h) / 2 }
    };
    const pos = positions[settings.avatarPosition] || positions['bottom-right'];

    avatarWindow = new BrowserWindow({
        width: size.w,
        height: size.h,
        x: pos.x,
        y: pos.y,
        frame: false,
        transparent: true,
        resizable: true,
        alwaysOnTop: settings.alwaysOnTop,
        skipTaskbar: settings.displayMode === 'overlay',
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        },
        backgroundColor: '#00000000'
    });

    avatarWindow.loadFile('avatar-3d.html');
    avatarWindow.on('closed', () => { avatarWindow = null; });
}

// ═══════════════════════════════════════════════════════════════════════════════
//   PYTHON INTEGRATION - Calls bree_voice_feedback.py with pygame audio
// ═══════════════════════════════════════════════════════════════════════════════

async function speakWithBree(text, emotion = 'NEUTRAL') {
    const projectRoot = path.join(__dirname, '..');
    const pythonScript = path.join(projectRoot, 'backend', 'bree_voice_feedback.py');

    return new Promise((resolve, reject) => {
        // Create a temporary Python script that imports and uses Bree
        const pythonCode = `
import sys
import asyncio
sys.path.insert(0, r"${projectRoot.replace(/\\/g, '/')}")
sys.path.insert(0, r"${projectRoot.replace(/\\/g, '/')}/backend")

from bree_voice_feedback import get_bree, EmotionType

async def main():
    bree = get_bree()
    emotion = EmotionType.${emotion}
    await bree.speak(r"""${text.replace(/"/g, '\\"')}""", emotion)
    print("DONE")

asyncio.run(main())
`;

        const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
        pythonProcess = spawn(pythonCmd, ['-c', pythonCode], {
            cwd: path.join(projectRoot, 'backend'),
            env: { ...process.env },
            shell: true
        });

        let output = '';
        pythonProcess.stdout.on('data', (data) => {
            output += data.toString();
            if (output.includes('DONE')) {
                resolve({ success: true });
            }
        });

        pythonProcess.stderr.on('data', (data) => {
            console.log('Bree stderr:', data.toString());
        });

        pythonProcess.on('close', (code) => {
            if (code === 0) {
                resolve({ success: true });
            } else {
                reject(new Error(`Python exited with code ${code}`));
            }
        });

        pythonProcess.on('error', (err) => {
            reject(err);
        });

        // Timeout after 30 seconds
        setTimeout(() => {
            if (pythonProcess) {
                pythonProcess.kill();
                reject(new Error('Speech timeout'));
            }
        }, 30000);
    });
}

// IPC Handlers
ipcMain.handle('minimize-window', () => mainWindow?.minimize());
ipcMain.handle('maximize-window', () => {
    if (mainWindow?.isMaximized()) mainWindow.unmaximize();
    else mainWindow?.maximize();
});
ipcMain.handle('close-window', () => mainWindow?.close());

ipcMain.handle('get-settings', () => settings);
ipcMain.handle('save-settings', (event, newSettings) => {
    settings = { ...settings, ...newSettings };
    if (avatarWindow && !avatarWindow.isDestroyed()) {
        avatarWindow.webContents.send('settings-updated', settings);
    }
    return settings;
});

ipcMain.handle('open-avatar-window', () => createAvatarWindow());
ipcMain.handle('close-avatar-window', () => {
    if (avatarWindow) {
        avatarWindow.close();
        avatarWindow = null;
    }
});

ipcMain.handle('toggle-avatar', () => {
    if (avatarWindow && !avatarWindow.isDestroyed()) {
        avatarWindow.close();
        avatarWindow = null;
    } else {
        createAvatarWindow();
    }
});

// Speech with Python/Pygame integration
ipcMain.handle('speak-text', async (event, data) => {
    const { text, emotion } = data;

    console.log(`Speaking [${emotion}]: ${text}`);

    // Notify avatar to start lip sync
    if (avatarWindow && !avatarWindow.isDestroyed()) {
        avatarWindow.webContents.send('start-speaking', { text, emotion });
    }
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('start-speaking', { text, emotion });
    }

    try {
        await speakWithBree(text, emotion);
    } catch (err) {
        console.error('Speech failed:', err);
    }

    // Notify avatar to stop lip sync
    if (avatarWindow && !avatarWindow.isDestroyed()) {
        avatarWindow.webContents.send('stop-speaking');
    }
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('stop-speaking');
    }

    return { success: true };
});

ipcMain.handle('set-emotion', (event, emotion) => {
    if (avatarWindow && !avatarWindow.isDestroyed()) {
        avatarWindow.webContents.send('set-emotion', emotion);
    }
});

ipcMain.handle('set-avatar-style', (event, style) => {
    settings.avatarStyle = style;
    if (avatarWindow && !avatarWindow.isDestroyed()) {
        avatarWindow.webContents.send('set-style', style);
    }
});

ipcMain.handle('open-url', (event, url) => shell.openExternal(url));

// System stats
function getSystemStats() {
    const cpus = os.cpus();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const usedMem = totalMem - freeMem;

    let totalIdle = 0, totalTick = 0;
    cpus.forEach(cpu => {
        for (let type in cpu.times) totalTick += cpu.times[type];
        totalIdle += cpu.times.idle;
    });

    return {
        cpu: { usage: Math.round((1 - totalIdle / totalTick) * 100), cores: cpus.length },
        memory: {
            total: Math.round(totalMem / 1024 / 1024 / 1024 * 10) / 10,
            used: Math.round(usedMem / 1024 / 1024 / 1024 * 10) / 10,
            percent: Math.round((usedMem / totalMem) * 100)
        }
    };
}

ipcMain.handle('get-system-stats', () => getSystemStats());

app.whenReady().then(createMainWindow);

app.on('window-all-closed', () => {
    if (pythonProcess) pythonProcess.kill();
    if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
});

setInterval(() => {
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('system-stats', getSystemStats());
    }
}, 2000);
