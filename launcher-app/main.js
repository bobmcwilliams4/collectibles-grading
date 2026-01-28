const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const http = require('http');

let mainWindow;
let backendProcess = null;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 1000,
        minHeight: 700,
        frame: false,
        transparent: true,
        resizable: true,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            enableRemoteModule: true
        },
        icon: path.join(__dirname, 'assets/images/icon.png'),
        show: false,
        backgroundColor: '#00000000'
    });

    mainWindow.loadFile('index.html');

    // Show window when ready with fade-in effect
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

// IPC Handlers
ipcMain.handle('minimize-window', () => {
    mainWindow.minimize();
});

ipcMain.handle('maximize-window', () => {
    if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
    } else {
        mainWindow.maximize();
    }
});

ipcMain.handle('close-window', () => {
    mainWindow.close();
});

ipcMain.handle('start-backend', async () => {
    return new Promise((resolve, reject) => {
        const projectRoot = path.join(__dirname, '..');
        const backendDir = path.join(projectRoot, 'backend');

        const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

        backendProcess = spawn(pythonCmd, [
            '-m', 'uvicorn', 'main:app',
            '--host', '0.0.0.0',
            '--port', '8000',
            '--reload'
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

        // Wait for backend to be ready
        let attempts = 0;
        const checkBackend = setInterval(() => {
            attempts++;
            http.get('http://localhost:8000/docs', (res) => {
                if (res.statusCode === 200) {
                    clearInterval(checkBackend);
                    resolve({ success: true, message: 'Backend started successfully' });
                }
            }).on('error', () => {
                if (attempts > 30) {
                    clearInterval(checkBackend);
                    resolve({ success: true, message: 'Backend starting (may take a moment)' });
                }
            });
        }, 1000);
    });
});

ipcMain.handle('start-gui', async () => {
    return new Promise((resolve) => {
        const projectRoot = path.join(__dirname, '..');
        const electronDir = path.join(projectRoot, 'electron-app');

        const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';

        const guiProcess = spawn(npmCmd, ['start'], {
            cwd: electronDir,
            shell: true,
            detached: true,
            stdio: 'ignore'
        });

        guiProcess.unref();

        setTimeout(() => {
            resolve({ success: true, message: 'GUI launched' });
        }, 2000);
    });
});

ipcMain.handle('check-system', async (event, component) => {
    const projectRoot = path.join(__dirname, '..');
    const fs = require('fs');

    const paths = {
        backend: path.join(projectRoot, 'backend', 'main.py'),
        database: path.join(projectRoot, 'collectibles.db'),
        electron: path.join(projectRoot, 'electron-app', 'main.js'),
        ai_providers: path.join(projectRoot, 'backend', 'ai_providers'),
        pricing: path.join(projectRoot, 'backend', 'pricing_sources'),
        webcam: path.join(projectRoot, 'webcam_module')
    };

    return fs.existsSync(paths[component]);
});

ipcMain.handle('open-browser', (event, url) => {
    shell.openExternal(url);
});

ipcMain.handle('get-system-info', () => {
    const os = require('os');
    return {
        platform: process.platform,
        arch: process.arch,
        cpus: os.cpus().length,
        memory: Math.round(os.totalmem() / 1024 / 1024 / 1024) + ' GB',
        hostname: os.hostname()
    };
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (backendProcess) {
        backendProcess.kill();
    }
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});
