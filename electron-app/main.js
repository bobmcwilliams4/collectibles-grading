/**
 * EPOCGS - Electron Main Process v3.0.0 ENHANCED
 * Echo Prime Omega Collectibles Grading System
 *
 * Features:
 * - Encrypted database storage
 * - Secure credential management
 * - Certificate pinning
 * - Comprehensive audit logging
 * - Auto-update system
 *
 * Authority Level 11.0 | Commander Bobby Don McWilliams II
 * ECHO OMEGA PRIME
 */

const { app, BrowserWindow, ipcMain, dialog, Menu, shell, nativeTheme, safeStorage, net } = require('electron');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const Store = require('electron-store');

// ============================================================================
// SECURITY MODULE - Encryption & Credential Management
// ============================================================================

class SecureVault {
    constructor(vaultPath) {
        this.vaultPath = vaultPath;
        this.vaultFile = path.join(vaultPath, 'secure_credentials.vault');
        this.keyFile = path.join(vaultPath, '.vault_key');
        this.encryptionKey = null;
        this.initialized = false;
    }

    async initialize() {
        // Ensure vault directory exists
        if (!fs.existsSync(this.vaultPath)) {
            fs.mkdirSync(this.vaultPath, { recursive: true });
        }

        // Check if system supports secure storage
        if (safeStorage.isEncryptionAvailable()) {
            this.encryptionKey = await this.getOrCreateKey();
            this.initialized = true;
            auditLogger.log('SECURITY', 'SecureVault initialized with OS encryption');
        } else {
            // Fallback to derived key (less secure but functional)
            this.encryptionKey = this.deriveFallbackKey();
            this.initialized = true;
            auditLogger.log('SECURITY', 'SecureVault initialized with fallback encryption', 'WARN');
        }
    }

    async getOrCreateKey() {
        try {
            if (fs.existsSync(this.keyFile)) {
                const encryptedKey = fs.readFileSync(this.keyFile);
                return safeStorage.decryptString(encryptedKey);
            } else {
                // Generate new 256-bit key
                const newKey = crypto.randomBytes(32).toString('hex');
                const encryptedKey = safeStorage.encryptString(newKey);
                fs.writeFileSync(this.keyFile, encryptedKey, { mode: 0o600 });
                return newKey;
            }
        } catch (error) {
            auditLogger.log('SECURITY', `Key retrieval error: ${error.message}`, 'ERROR');
            return this.deriveFallbackKey();
        }
    }

    deriveFallbackKey() {
        // Derive key from machine-specific info (fallback only)
        const machineId = `${process.env.COMPUTERNAME || 'unknown'}-${process.env.USERNAME || 'user'}`;
        return crypto.createHash('sha256').update(machineId).digest('hex');
    }

    encrypt(data) {
        if (!this.initialized) throw new Error('Vault not initialized');

        const iv = crypto.randomBytes(16);
        const key = Buffer.from(this.encryptionKey.slice(0, 32), 'hex');
        const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);

        let encrypted = cipher.update(JSON.stringify(data), 'utf8', 'hex');
        encrypted += cipher.final('hex');
        const authTag = cipher.getAuthTag();

        return {
            iv: iv.toString('hex'),
            data: encrypted,
            tag: authTag.toString('hex')
        };
    }

    decrypt(encryptedData) {
        if (!this.initialized) throw new Error('Vault not initialized');

        try {
            const key = Buffer.from(this.encryptionKey.slice(0, 32), 'hex');
            const decipher = crypto.createDecipheriv(
                'aes-256-gcm',
                key,
                Buffer.from(encryptedData.iv, 'hex')
            );
            decipher.setAuthTag(Buffer.from(encryptedData.tag, 'hex'));

            let decrypted = decipher.update(encryptedData.data, 'hex', 'utf8');
            decrypted += decipher.final('utf8');

            return JSON.parse(decrypted);
        } catch (error) {
            auditLogger.log('SECURITY', `Decryption failed: ${error.message}`, 'ERROR');
            return null;
        }
    }

    saveCredential(service, credential) {
        const credentials = this.loadAllCredentials();
        credentials[service] = {
            ...credential,
            updatedAt: new Date().toISOString()
        };

        const encrypted = this.encrypt(credentials);
        fs.writeFileSync(this.vaultFile, JSON.stringify(encrypted, null, 2), { mode: 0o600 });
        auditLogger.log('SECURITY', `Credential saved for: ${service}`);
        return true;
    }

    getCredential(service) {
        const credentials = this.loadAllCredentials();
        if (credentials[service]) {
            auditLogger.log('SECURITY', `Credential accessed for: ${service}`);
            return credentials[service];
        }
        return null;
    }

    deleteCredential(service) {
        const credentials = this.loadAllCredentials();
        if (credentials[service]) {
            delete credentials[service];
            const encrypted = this.encrypt(credentials);
            fs.writeFileSync(this.vaultFile, JSON.stringify(encrypted, null, 2), { mode: 0o600 });
            auditLogger.log('SECURITY', `Credential deleted for: ${service}`);
            return true;
        }
        return false;
    }

    loadAllCredentials() {
        try {
            if (fs.existsSync(this.vaultFile)) {
                const data = JSON.parse(fs.readFileSync(this.vaultFile, 'utf8'));
                return this.decrypt(data) || {};
            }
        } catch (error) {
            auditLogger.log('SECURITY', `Failed to load credentials: ${error.message}`, 'ERROR');
        }
        return {};
    }

    listServices() {
        const credentials = this.loadAllCredentials();
        return Object.keys(credentials);
    }
}

// ============================================================================
// AUDIT LOGGING MODULE
// ============================================================================

class AuditLogger {
    constructor(logPath) {
        this.logPath = logPath;
        this.logFile = path.join(logPath, 'audit.log');
        this.sessionId = crypto.randomBytes(8).toString('hex');
        this.initialized = false;
    }

    initialize() {
        if (!fs.existsSync(this.logPath)) {
            fs.mkdirSync(this.logPath, { recursive: true });
        }
        this.initialized = true;
        this.log('SYSTEM', 'Audit logging initialized', 'INFO');
        this.log('SESSION', `New session started: ${this.sessionId}`);
    }

    log(category, message, level = 'INFO') {
        if (!this.initialized) return;

        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            sessionId: this.sessionId,
            level,
            category,
            message
        };

        const logLine = `[${timestamp}] [${this.sessionId}] [${level}] [${category}] ${message}\n`;

        try {
            fs.appendFileSync(this.logFile, logLine);
        } catch (error) {
            console.error('Audit log write failed:', error.message);
        }

        // Also log to console in development
        if (process.argv.includes('--dev')) {
            const colors = { INFO: '\x1b[36m', WARN: '\x1b[33m', ERROR: '\x1b[31m', SECURITY: '\x1b[35m' };
            const color = colors[level] || colors[category] || '\x1b[0m';
            console.log(`${color}[AUDIT] [${category}] ${message}\x1b[0m`);
        }
    }

    getRecentLogs(count = 100) {
        try {
            if (!fs.existsSync(this.logFile)) return [];
            const content = fs.readFileSync(this.logFile, 'utf8');
            const lines = content.trim().split('\n');
            return lines.slice(-count);
        } catch (error) {
            return [];
        }
    }

    searchLogs(query, category = null) {
        try {
            if (!fs.existsSync(this.logFile)) return [];
            const content = fs.readFileSync(this.logFile, 'utf8');
            const lines = content.trim().split('\n');

            return lines.filter(line => {
                const matchesQuery = line.toLowerCase().includes(query.toLowerCase());
                const matchesCategory = !category || line.includes(`[${category}]`);
                return matchesQuery && matchesCategory;
            });
        } catch (error) {
            return [];
        }
    }

    exportLogs(startDate = null, endDate = null) {
        try {
            if (!fs.existsSync(this.logFile)) return [];
            const content = fs.readFileSync(this.logFile, 'utf8');
            const lines = content.trim().split('\n');

            if (!startDate && !endDate) return lines;

            return lines.filter(line => {
                const match = line.match(/\[([\d-T:.Z]+)\]/);
                if (!match) return false;
                const logDate = new Date(match[1]);
                const afterStart = !startDate || logDate >= new Date(startDate);
                const beforeEnd = !endDate || logDate <= new Date(endDate);
                return afterStart && beforeEnd;
            });
        } catch (error) {
            return [];
        }
    }
}

// ============================================================================
// CERTIFICATE PINNING MODULE
// ============================================================================

class CertificatePinner {
    constructor() {
        // Trusted certificate fingerprints (SHA-256)
        this.pinnedCertificates = new Map();
        this.trustedDomains = new Set(['localhost', '127.0.0.1']);
    }

    addPin(domain, fingerprint) {
        if (!this.pinnedCertificates.has(domain)) {
            this.pinnedCertificates.set(domain, new Set());
        }
        this.pinnedCertificates.get(domain).add(fingerprint.toLowerCase());
        auditLogger.log('SECURITY', `Certificate pin added for: ${domain}`);
    }

    addTrustedDomain(domain) {
        this.trustedDomains.add(domain);
    }

    verify(hostname, certificate) {
        // Always trust localhost in development
        if (this.trustedDomains.has(hostname)) {
            return true;
        }

        // Check if we have pins for this domain
        if (!this.pinnedCertificates.has(hostname)) {
            // No pins configured - allow (but log)
            auditLogger.log('SECURITY', `No certificate pin for: ${hostname}`, 'WARN');
            return true;
        }

        // Calculate certificate fingerprint
        const fingerprint = crypto
            .createHash('sha256')
            .update(certificate.data)
            .digest('hex');

        const pins = this.pinnedCertificates.get(hostname);
        const isValid = pins.has(fingerprint);

        if (!isValid) {
            auditLogger.log('SECURITY', `Certificate pin mismatch for: ${hostname}`, 'ERROR');
        }

        return isValid;
    }
}

// ============================================================================
// AUTO-UPDATE MODULE
// ============================================================================

class AutoUpdater {
    constructor(updateUrl) {
        this.updateUrl = updateUrl;
        this.currentVersion = require('./package.json').version;
        this.updateAvailable = false;
        this.latestVersion = null;
    }

    async checkForUpdates() {
        try {
            const response = await net.fetch(`${this.updateUrl}/latest.json`);
            if (!response.ok) {
                auditLogger.log('UPDATE', 'Failed to check for updates', 'WARN');
                return null;
            }

            const data = await response.json();
            this.latestVersion = data.version;

            if (this.compareVersions(data.version, this.currentVersion) > 0) {
                this.updateAvailable = true;
                auditLogger.log('UPDATE', `Update available: ${data.version}`);
                return {
                    available: true,
                    currentVersion: this.currentVersion,
                    latestVersion: data.version,
                    releaseNotes: data.releaseNotes || '',
                    downloadUrl: data.downloadUrl
                };
            }

            auditLogger.log('UPDATE', 'Application is up to date');
            return { available: false, currentVersion: this.currentVersion };
        } catch (error) {
            auditLogger.log('UPDATE', `Update check failed: ${error.message}`, 'ERROR');
            return null;
        }
    }

    compareVersions(v1, v2) {
        const parts1 = v1.split('.').map(Number);
        const parts2 = v2.split('.').map(Number);

        for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
            const p1 = parts1[i] || 0;
            const p2 = parts2[i] || 0;
            if (p1 > p2) return 1;
            if (p1 < p2) return -1;
        }
        return 0;
    }
}

// ============================================================================
// ENCRYPTED DATABASE STORE
// ============================================================================

class EncryptedStore {
    constructor(options) {
        this.storePath = options.cwd;
        this.storeFile = path.join(this.storePath, 'encrypted_data.store');
        this.encryptionKey = null;
        this.data = {};
        this.defaults = options.defaults || {};
    }

    async initialize(vault) {
        // Use vault's encryption key
        this.encryptionKey = vault.encryptionKey;

        // Load existing data or initialize with defaults
        if (fs.existsSync(this.storeFile)) {
            try {
                const encrypted = JSON.parse(fs.readFileSync(this.storeFile, 'utf8'));
                this.data = vault.decrypt(encrypted) || { ...this.defaults };
            } catch (error) {
                auditLogger.log('DATABASE', `Failed to load encrypted store: ${error.message}`, 'ERROR');
                this.data = { ...this.defaults };
            }
        } else {
            this.data = { ...this.defaults };
            this.save();
        }

        auditLogger.log('DATABASE', 'Encrypted store initialized');
    }

    save() {
        const vault = secureVault;
        const encrypted = vault.encrypt(this.data);
        fs.writeFileSync(this.storeFile, JSON.stringify(encrypted, null, 2), { mode: 0o600 });
    }

    get(key) {
        if (key) {
            const keys = key.split('.');
            let value = this.data;
            for (const k of keys) {
                if (value === undefined || value === null) return undefined;
                value = value[k];
            }
            return value !== undefined ? value : this.defaults[key];
        }
        return { ...this.data };
    }

    set(key, value) {
        const keys = key.split('.');
        let obj = this.data;

        for (let i = 0; i < keys.length - 1; i++) {
            if (!(keys[i] in obj)) obj[keys[i]] = {};
            obj = obj[keys[i]];
        }

        obj[keys[keys.length - 1]] = value;
        this.save();
        auditLogger.log('DATABASE', `Config updated: ${key}`);
        return true;
    }

    delete(key) {
        const keys = key.split('.');
        let obj = this.data;

        for (let i = 0; i < keys.length - 1; i++) {
            if (!(keys[i] in obj)) return false;
            obj = obj[keys[i]];
        }

        if (keys[keys.length - 1] in obj) {
            delete obj[keys[keys.length - 1]];
            this.save();
            return true;
        }
        return false;
    }

    get store() {
        return { ...this.data };
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Enable audio autoplay without user gesture (for BREE voice)
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

// Set app user data path
const userDataPath = path.join(process.env.APPDATA || process.env.HOME, 'EPOCGS');
app.setPath('userData', userDataPath);

// Initialize security modules
const auditLogger = new AuditLogger(path.join(userDataPath, 'logs'));
const secureVault = new SecureVault(path.join(userDataPath, 'vault'));
const certificatePinner = new CertificatePinner();
const autoUpdater = new AutoUpdater('https://api.echo-op.com/updates/epocgs');

// Encrypted configuration store
const encryptedStore = new EncryptedStore({
    cwd: userDataPath,
    defaults: {
        windowBounds: { width: 1400, height: 900 },
        apiEndpoint: 'http://localhost:8000',
        theme: 'system',
        voiceEnabled: true,
        autoCapture: true,
        qualityThreshold: 0.85,
        lastDirectory: '',
        autoUpdateCheck: true,
        telemetryEnabled: false
    }
});

// Legacy unencrypted store (for migration)
const legacyStore = new Store({
    cwd: userDataPath,
    name: 'config_legacy',
    clearInvalidConfig: true
});

// Main window reference
let mainWindow = null;
let webcamWindow = null;

// ============================================================================
// WINDOW MANAGEMENT
// ============================================================================

async function createMainWindow() {
    // Initialize security modules
    auditLogger.initialize();
    await secureVault.initialize();
    await encryptedStore.initialize(secureVault);

    // Migrate legacy config if needed
    migrateFromLegacyStore();

    const { width, height } = encryptedStore.get('windowBounds');

    mainWindow = new BrowserWindow({
        width,
        height,
        minWidth: 1024,
        minHeight: 768,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true,
            preload: path.join(__dirname, 'preload.js'),
            webSecurity: true
        },
        icon: path.join(__dirname, 'assets', 'icon.png'),
        show: false,
        backgroundColor: '#0f0f1a',
        autoHideMenuBar: false,
        frame: true,
        title: 'EPOCGS - Collectibles Grading System'
    });

    // Load main page
    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

    // Show when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        auditLogger.log('UI', 'Main window displayed');

        // Check for updates on startup
        if (encryptedStore.get('autoUpdateCheck')) {
            autoUpdater.checkForUpdates().then(result => {
                if (result && result.available) {
                    mainWindow.webContents.send('update-available', result);
                }
            });
        }
    });

    // Save window bounds on resize
    mainWindow.on('resize', () => {
        const bounds = mainWindow.getBounds();
        encryptedStore.set('windowBounds', { width: bounds.width, height: bounds.height });
    });

    // Handle window close
    mainWindow.on('closed', () => {
        auditLogger.log('SESSION', 'Main window closed');
        mainWindow = null;
        if (webcamWindow) {
            webcamWindow.close();
        }
    });

    // Open dev tools in development
    if (process.argv.includes('--dev')) {
        mainWindow.webContents.openDevTools();
    }

    // Create application menu
    createMenu();

    auditLogger.log('SESSION', 'Application started successfully');
}

function migrateFromLegacyStore() {
    try {
        const legacyData = legacyStore.store;
        if (Object.keys(legacyData).length > 0) {
            // Migrate each key
            for (const [key, value] of Object.entries(legacyData)) {
                if (encryptedStore.get(key) === undefined) {
                    encryptedStore.set(key, value);
                }
            }
            // Clear legacy store after migration
            legacyStore.clear();
            auditLogger.log('DATABASE', 'Migrated from legacy unencrypted store');
        }
    } catch (error) {
        auditLogger.log('DATABASE', `Migration failed: ${error.message}`, 'WARN');
    }
}

function createWebcamWindow() {
    if (webcamWindow) {
        webcamWindow.focus();
        return;
    }

    webcamWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        parent: mainWindow,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true,
            preload: path.join(__dirname, 'preload.js')
        },
        icon: path.join(__dirname, 'assets', 'icon.png'),
        title: 'Webcam Grading'
    });

    webcamWindow.loadFile(path.join(__dirname, 'renderer', 'webcam-grading.html'));

    webcamWindow.on('closed', () => {
        auditLogger.log('UI', 'Webcam window closed');
        webcamWindow = null;
    });

    auditLogger.log('UI', 'Webcam window opened');
}

// ============================================================================
// MENU
// ============================================================================

function createMenu() {
    const template = [
        {
            label: 'File',
            submenu: [
                {
                    label: 'New Item',
                    accelerator: 'CmdOrCtrl+N',
                    click: () => {
                        mainWindow.webContents.send('menu-action', 'new-item');
                        auditLogger.log('UI', 'Menu: New Item');
                    }
                },
                {
                    label: 'Open Webcam Grading',
                    accelerator: 'CmdOrCtrl+W',
                    click: createWebcamWindow
                },
                { type: 'separator' },
                {
                    label: 'Import Items',
                    accelerator: 'CmdOrCtrl+I',
                    click: () => importItems()
                },
                {
                    label: 'Export Catalog',
                    accelerator: 'CmdOrCtrl+E',
                    click: () => {
                        mainWindow.webContents.send('menu-action', 'export');
                        auditLogger.log('UI', 'Menu: Export');
                    }
                },
                { type: 'separator' },
                { role: 'quit' }
            ]
        },
        {
            label: 'Edit',
            submenu: [
                { role: 'undo' },
                { role: 'redo' },
                { type: 'separator' },
                { role: 'cut' },
                { role: 'copy' },
                { role: 'paste' },
                { role: 'selectAll' }
            ]
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },
        {
            label: 'Grading',
            submenu: [
                {
                    label: 'Grade Selected',
                    accelerator: 'CmdOrCtrl+G',
                    click: () => {
                        mainWindow.webContents.send('menu-action', 'grade');
                        auditLogger.log('GRADING', 'Menu: Grade Selected');
                    }
                },
                {
                    label: 'Batch Grade',
                    accelerator: 'CmdOrCtrl+Shift+G',
                    click: () => {
                        mainWindow.webContents.send('menu-action', 'batch-grade');
                        auditLogger.log('GRADING', 'Menu: Batch Grade');
                    }
                },
                { type: 'separator' },
                {
                    label: 'Get Pricing',
                    accelerator: 'CmdOrCtrl+P',
                    click: () => {
                        mainWindow.webContents.send('menu-action', 'pricing');
                        auditLogger.log('PRICING', 'Menu: Get Pricing');
                    }
                },
                { type: 'separator' },
                {
                    label: 'Manual Review Queue',
                    click: () => {
                        mainWindow.webContents.send('menu-action', 'review-queue');
                        auditLogger.log('UI', 'Menu: Review Queue');
                    }
                }
            ]
        },
        {
            label: 'Tools',
            submenu: [
                {
                    label: 'Settings',
                    accelerator: 'CmdOrCtrl+,',
                    click: () => mainWindow.webContents.send('menu-action', 'settings')
                },
                {
                    label: 'Statistics',
                    click: () => mainWindow.webContents.send('menu-action', 'statistics')
                },
                { type: 'separator' },
                {
                    label: 'Check for Updates',
                    click: async () => {
                        const result = await autoUpdater.checkForUpdates();
                        if (result) {
                            if (result.available) {
                                mainWindow.webContents.send('update-available', result);
                            } else {
                                dialog.showMessageBox(mainWindow, {
                                    type: 'info',
                                    title: 'No Updates',
                                    message: 'You are running the latest version.',
                                    detail: `Current version: ${result.currentVersion}`
                                });
                            }
                        }
                    }
                },
                { type: 'separator' },
                {
                    label: 'View Audit Log',
                    click: () => mainWindow.webContents.send('menu-action', 'audit-log')
                },
                {
                    label: 'Security Settings',
                    click: () => mainWindow.webContents.send('menu-action', 'security-settings')
                },
                { type: 'separator' },
                {
                    label: 'Generate Investor Portal',
                    click: () => mainWindow.webContents.send('menu-action', 'generate-portal')
                }
            ]
        },
        {
            label: 'Help',
            submenu: [
                {
                    label: 'Documentation',
                    click: () => shell.openExternal('https://echo-op.com/docs/epocgs')
                },
                {
                    label: 'Grading Guide',
                    click: () => shell.openExternal('https://echo-op.com/docs/grading-standards')
                },
                { type: 'separator' },
                {
                    label: 'Report Issue',
                    click: () => shell.openExternal('https://github.com/echoprime/epocgs/issues')
                },
                { type: 'separator' },
                {
                    label: 'About EPOCGS',
                    click: showAboutDialog
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

// ============================================================================
// DIALOGS
// ============================================================================

async function importItems() {
    const result = await dialog.showOpenDialog(mainWindow, {
        title: 'Import Collectible Images',
        properties: ['openFile', 'multiSelections'],
        filters: [
            { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'webp', 'gif'] },
            { name: 'Data Files', extensions: ['csv', 'xlsx', 'json'] },
            { name: 'All Files', extensions: ['*'] }
        ],
        defaultPath: encryptedStore.get('lastDirectory')
    });

    if (!result.canceled && result.filePaths.length > 0) {
        encryptedStore.set('lastDirectory', path.dirname(result.filePaths[0]));
        mainWindow.webContents.send('import-files', result.filePaths);
        auditLogger.log('IMPORT', `Imported ${result.filePaths.length} files`);
    }
}

function showAboutDialog() {
    const pkg = require('./package.json');
    dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'About EPOCGS',
        message: `EPOCGS v${pkg.version}`,
        detail: 'Echo Prime Omega Collectibles Grading System\n\n' +
                'AI-Powered Multi-Model Consensus Grading\n\n' +
                'Authority Level 11.0\n' +
                'Commander Bobby Don McWilliams II\n' +
                'System: ECHO OMEGA PRIME\n\n' +
                'Features:\n' +
                '  - Multi-AI consensus grading\n' +
                '  - Real-time webcam capture\n' +
                '  - Multi-source price comparison\n' +
                '  - Encrypted secure storage\n' +
                '  - Comprehensive audit logging\n' +
                '  - Value tracking over time'
    });
    auditLogger.log('UI', 'About dialog displayed');
}

// ============================================================================
// IPC HANDLERS - Configuration
// ============================================================================

ipcMain.handle('get-config', (event, key) => {
    const value = key ? encryptedStore.get(key) : encryptedStore.store;
    return value;
});

ipcMain.handle('set-config', (event, key, value) => {
    encryptedStore.set(key, value);
    return true;
});

ipcMain.handle('get-api-url', () => {
    return encryptedStore.get('apiEndpoint') || 'http://localhost:8000';
});

// ============================================================================
// IPC HANDLERS - Secure Credential Management
// ============================================================================

ipcMain.handle('vault-save', async (event, service, credential) => {
    try {
        secureVault.saveCredential(service, credential);
        return { success: true };
    } catch (error) {
        auditLogger.log('SECURITY', `Vault save failed: ${error.message}`, 'ERROR');
        return { success: false, error: error.message };
    }
});

ipcMain.handle('vault-get', async (event, service) => {
    try {
        const credential = secureVault.getCredential(service);
        return { success: true, credential };
    } catch (error) {
        auditLogger.log('SECURITY', `Vault get failed: ${error.message}`, 'ERROR');
        return { success: false, error: error.message };
    }
});

ipcMain.handle('vault-delete', async (event, service) => {
    try {
        const result = secureVault.deleteCredential(service);
        return { success: result };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

ipcMain.handle('vault-list', async () => {
    try {
        const services = secureVault.listServices();
        return { success: true, services };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

// ============================================================================
// IPC HANDLERS - Audit Logging
// ============================================================================

ipcMain.handle('audit-log', (event, category, message, level = 'INFO') => {
    auditLogger.log(category, message, level);
    return true;
});

ipcMain.handle('audit-get-logs', (event, count = 100) => {
    return auditLogger.getRecentLogs(count);
});

ipcMain.handle('audit-search', (event, query, category = null) => {
    return auditLogger.searchLogs(query, category);
});

ipcMain.handle('audit-export', (event, startDate = null, endDate = null) => {
    return auditLogger.exportLogs(startDate, endDate);
});

// ============================================================================
// IPC HANDLERS - Dialogs
// ============================================================================

ipcMain.handle('select-directory', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory']
    });
    return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('select-file', async (event, options = {}) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        title: options.title || 'Select File',
        properties: ['openFile'],
        filters: options.filters || [
            { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'webp'] }
        ]
    });
    return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('save-file', async (event, options = {}) => {
    const result = await dialog.showSaveDialog(mainWindow, {
        title: options.title || 'Save File',
        defaultPath: options.defaultPath,
        filters: options.filters || [
            { name: 'All Files', extensions: ['*'] }
        ]
    });
    return result.canceled ? null : result.filePath;
});

ipcMain.handle('show-error', async (event, title, message) => {
    await dialog.showErrorBox(title, message);
    auditLogger.log('UI', `Error shown: ${title} - ${message}`, 'ERROR');
});

ipcMain.handle('show-confirm', async (event, options) => {
    const result = await dialog.showMessageBox(mainWindow, {
        type: 'question',
        buttons: ['Yes', 'No'],
        title: options.title || 'Confirm',
        message: options.message
    });
    return result.response === 0;
});

// ============================================================================
// IPC HANDLERS - Windows & External
// ============================================================================

ipcMain.handle('open-webcam', () => {
    createWebcamWindow();
});

ipcMain.handle('open-external', (event, url) => {
    // Validate URL before opening
    try {
        const parsed = new URL(url);
        if (['http:', 'https:'].includes(parsed.protocol)) {
            shell.openExternal(url);
            auditLogger.log('UI', `External URL opened: ${parsed.hostname}`);
        }
    } catch (error) {
        auditLogger.log('SECURITY', `Invalid external URL blocked: ${url}`, 'WARN');
    }
});

ipcMain.handle('get-theme', () => {
    return nativeTheme.shouldUseDarkColors ? 'dark' : 'light';
});

// ============================================================================
// IPC HANDLERS - Updates
// ============================================================================

ipcMain.handle('check-updates', async () => {
    return await autoUpdater.checkForUpdates();
});

ipcMain.handle('get-version', () => {
    return require('./package.json').version;
});

// ============================================================================
// APP LIFECYCLE
// ============================================================================

app.whenReady().then(createMainWindow);

app.on('window-all-closed', () => {
    auditLogger.log('SESSION', 'All windows closed');
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
    }
});

app.on('before-quit', () => {
    auditLogger.log('SESSION', 'Application shutting down');
});

// ============================================================================
// SECURITY - Certificate Handling
// ============================================================================

app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
    const urlObj = new URL(url);

    // Allow localhost in development
    if (urlObj.hostname === 'localhost' || urlObj.hostname === '127.0.0.1') {
        event.preventDefault();
        callback(true);
        return;
    }

    // Check certificate pins
    if (certificatePinner.verify(urlObj.hostname, certificate)) {
        event.preventDefault();
        callback(true);
    } else {
        auditLogger.log('SECURITY', `Certificate rejected for: ${urlObj.hostname}`, 'ERROR');
        callback(false);
    }
});

// Prevent navigation to untrusted URLs
app.on('web-contents-created', (event, contents) => {
    contents.on('will-navigate', (navEvent, url) => {
        const trustedDomains = ['localhost', '127.0.0.1', 'echo-op.com'];
        try {
            const urlObj = new URL(url);
            if (!trustedDomains.some(d => urlObj.hostname === d || urlObj.hostname.endsWith(`.${d}`))) {
                auditLogger.log('SECURITY', `Blocked navigation to: ${urlObj.hostname}`, 'WARN');
                navEvent.preventDefault();
            }
        } catch {
            navEvent.preventDefault();
        }
    });

    // Prevent new window creation from links
    contents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });
});

// ============================================================================
// EXPORTS (for testing)
// ============================================================================

module.exports = {
    SecureVault,
    AuditLogger,
    CertificatePinner,
    AutoUpdater,
    EncryptedStore
};
