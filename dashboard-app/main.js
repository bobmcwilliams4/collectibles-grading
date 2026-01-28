const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const os = require('os');

let mainWindow;
let backendProcess = null;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1200,
        minHeight: 800,
        frame: false,
        transparent: true,
        resizable: true,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        },
        icon: path.join(__dirname, 'assets/icon.png'),
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
        if (backendProcess) {
            backendProcess.kill();
        }
    });
}

// System monitoring
function getSystemStats() {
    const cpus = os.cpus();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const usedMem = totalMem - freeMem;

    // Calculate CPU usage
    let totalIdle = 0, totalTick = 0;
    cpus.forEach(cpu => {
        for (let type in cpu.times) {
            totalTick += cpu.times[type];
        }
        totalIdle += cpu.times.idle;
    });
    const cpuUsage = Math.round((1 - totalIdle / totalTick) * 100);

    return {
        cpu: {
            usage: cpuUsage,
            cores: cpus.length,
            model: cpus[0].model
        },
        memory: {
            total: Math.round(totalMem / 1024 / 1024 / 1024 * 10) / 10,
            used: Math.round(usedMem / 1024 / 1024 / 1024 * 10) / 10,
            free: Math.round(freeMem / 1024 / 1024 / 1024 * 10) / 10,
            percent: Math.round((usedMem / totalMem) * 100)
        },
        uptime: os.uptime(),
        platform: os.platform(),
        hostname: os.hostname(),
        arch: os.arch()
    };
}

// IPC Handlers
ipcMain.handle('get-system-stats', () => getSystemStats());

ipcMain.handle('minimize-window', () => mainWindow.minimize());
ipcMain.handle('maximize-window', () => {
    if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
    } else {
        mainWindow.maximize();
    }
});
ipcMain.handle('close-window', () => mainWindow.close());

ipcMain.handle('check-backend', async () => {
    return new Promise((resolve) => {
        http.get('http://localhost:8000/docs', (res) => {
            resolve(res.statusCode === 200);
        }).on('error', () => {
            resolve(false);
        });
    });
});

ipcMain.handle('start-backend', async () => {
    const projectRoot = path.join(__dirname, '..');
    const backendDir = path.join(projectRoot, 'backend');
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

    backendProcess = spawn(pythonCmd, [
        '-m', 'uvicorn', 'main:app',
        '--host', '0.0.0.0', '--port', '8000', '--reload'
    ], {
        cwd: backendDir,
        env: { ...process.env, PYTHONPATH: projectRoot },
        shell: true
    });

    backendProcess.stdout.on('data', (data) => {
        mainWindow.webContents.send('backend-log', data.toString());
    });

    backendProcess.stderr.on('data', (data) => {
        mainWindow.webContents.send('backend-log', data.toString());
    });

    return { success: true };
});

ipcMain.handle('open-url', (event, url) => shell.openExternal(url));

ipcMain.handle('get-grading-stats', async () => {
    // Simulated stats - in production, fetch from backend API
    return {
        totalGraded: Math.floor(Math.random() * 500) + 100,
        todayGraded: Math.floor(Math.random() * 20),
        avgGrade: (Math.random() * 3 + 6).toFixed(1),
        topProviders: ['Claude', 'Gemini', 'GPT-4'],
        recentActivity: [
            { time: '2 min ago', action: 'Graded Amazing Spider-Man #129', grade: 8.5 },
            { time: '15 min ago', action: 'Graded X-Men #1', grade: 7.0 },
            { time: '1 hour ago', action: 'Graded Batman #404', grade: 9.2 }
        ]
    };
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (backendProcess) backendProcess.kill();
    if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

// Update stats every 2 seconds
setInterval(() => {
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('system-stats', getSystemStats());
    }
}, 2000);
