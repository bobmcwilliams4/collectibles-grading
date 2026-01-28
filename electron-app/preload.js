/**
 * EPOCGS - Preload Script v3.0.0 ENHANCED
 * Secure IPC Bridge with Security APIs
 *
 * Features:
 * - Secure credential vault access
 * - Audit logging integration
 * - Update notifications
 * - Enhanced API client with retry logic
 *
 * Authority Level 11.0 | Commander Bobby Don McWilliams II
 * ECHO OMEGA PRIME
 */

const { contextBridge, ipcRenderer } = require('electron');

// ============================================================================
// ELECTRON API - Core System Functions
// ============================================================================

contextBridge.exposeInMainWorld('electronAPI', {
    // Configuration
    getConfig: (key) => ipcRenderer.invoke('get-config', key),
    setConfig: (key, value) => ipcRenderer.invoke('set-config', key, value),
    getApiUrl: () => ipcRenderer.invoke('get-api-url'),
    getVersion: () => ipcRenderer.invoke('get-version'),

    // Dialogs
    selectDirectory: () => ipcRenderer.invoke('select-directory'),
    selectFile: (options) => ipcRenderer.invoke('select-file', options),
    saveFile: (options) => ipcRenderer.invoke('save-file', options),
    showError: (title, message) => ipcRenderer.invoke('show-error', title, message),
    showConfirm: (options) => ipcRenderer.invoke('show-confirm', options),

    // Windows
    openWebcam: () => ipcRenderer.invoke('open-webcam'),
    openExternal: (url) => ipcRenderer.invoke('open-external', url),

    // Theme
    getTheme: () => ipcRenderer.invoke('get-theme'),

    // Updates
    checkUpdates: () => ipcRenderer.invoke('check-updates'),
    onUpdateAvailable: (callback) => {
        ipcRenderer.on('update-available', (event, data) => callback(data));
    },

    // Menu actions listener
    onMenuAction: (callback) => {
        ipcRenderer.on('menu-action', (event, action) => callback(action));
    },

    // File import listener
    onImportFiles: (callback) => {
        ipcRenderer.on('import-files', (event, files) => callback(files));
    },

    // Remove listeners
    removeAllListeners: (channel) => {
        ipcRenderer.removeAllListeners(channel);
    }
});

// ============================================================================
// SECURE VAULT API - Credential Management
// ============================================================================

contextBridge.exposeInMainWorld('vault', {
    /**
     * Save a credential to the secure vault
     * @param {string} service - Service identifier (e.g., 'ebay-api', 'gpa-key')
     * @param {object} credential - Credential object with username, password, apiKey, etc.
     */
    save: (service, credential) => ipcRenderer.invoke('vault-save', service, credential),

    /**
     * Get a credential from the secure vault
     * @param {string} service - Service identifier
     * @returns {object} Credential object or null
     */
    get: (service) => ipcRenderer.invoke('vault-get', service),

    /**
     * Delete a credential from the vault
     * @param {string} service - Service identifier
     */
    delete: (service) => ipcRenderer.invoke('vault-delete', service),

    /**
     * List all services with stored credentials
     * @returns {string[]} Array of service names
     */
    list: () => ipcRenderer.invoke('vault-list')
});

// ============================================================================
// AUDIT API - Logging and Compliance
// ============================================================================

contextBridge.exposeInMainWorld('audit', {
    /**
     * Log an audit event
     * @param {string} category - Event category (UI, GRADING, SECURITY, etc.)
     * @param {string} message - Event description
     * @param {string} level - Log level (INFO, WARN, ERROR)
     */
    log: (category, message, level = 'INFO') =>
        ipcRenderer.invoke('audit-log', category, message, level),

    /**
     * Get recent audit logs
     * @param {number} count - Number of entries to retrieve
     */
    getRecent: (count = 100) => ipcRenderer.invoke('audit-get-logs', count),

    /**
     * Search audit logs
     * @param {string} query - Search term
     * @param {string} category - Optional category filter
     */
    search: (query, category = null) => ipcRenderer.invoke('audit-search', query, category),

    /**
     * Export audit logs for a date range
     * @param {string} startDate - ISO date string
     * @param {string} endDate - ISO date string
     */
    export: (startDate = null, endDate = null) =>
        ipcRenderer.invoke('audit-export', startDate, endDate)
});

// ============================================================================
// API CLIENT - Enhanced with Retry Logic
// ============================================================================

const API_CONFIG = {
    baseUrl: 'http://localhost:8000',
    timeout: 30000,
    maxRetries: 3,
    retryDelay: 1000
};

/**
 * Sleep for specified milliseconds
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Make an API request with retry logic
 */
async function apiRequest(endpoint, options = {}, retryCount = 0) {
    const url = `${API_CONFIG.baseUrl}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };

    const fetchOptions = { ...defaultOptions, ...options };

    if (fetchOptions.body && typeof fetchOptions.body === 'object') {
        fetchOptions.body = JSON.stringify(fetchOptions.body);
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeout);
    fetchOptions.signal = controller.signal;

    try {
        const response = await fetch(url, fetchOptions);
        clearTimeout(timeoutId);

        const data = await response.json();

        if (!response.ok) {
            // Handle FastAPI validation errors (422) which return detail as array
            let errorMsg = `HTTP ${response.status}`;
            if (data.detail) {
                if (Array.isArray(data.detail)) {
                    errorMsg = data.detail.map(err => {
                        const field = err.loc ? err.loc.slice(1).join('.') : 'unknown';
                        return `${field}: ${err.msg}`;
                    }).join(', ');
                } else {
                    errorMsg = data.detail;
                }
            }
            throw new Error(errorMsg);
        }

        return data;
    } catch (error) {
        clearTimeout(timeoutId);

        // Retry on network errors or 5xx responses
        const isRetryable = error.name === 'AbortError' ||
                           error.message.includes('fetch') ||
                           error.message.includes('network') ||
                           error.message.includes('HTTP 5');

        if (isRetryable && retryCount < API_CONFIG.maxRetries) {
            console.warn(`API request failed, retrying (${retryCount + 1}/${API_CONFIG.maxRetries})...`);
            await sleep(API_CONFIG.retryDelay * (retryCount + 1));
            return apiRequest(endpoint, options, retryCount + 1);
        }

        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

async function apiGet(endpoint) {
    return apiRequest(endpoint, { method: 'GET' });
}

async function apiPost(endpoint, body) {
    return apiRequest(endpoint, { method: 'POST', body });
}

async function apiPut(endpoint, body) {
    return apiRequest(endpoint, { method: 'PUT', body });
}

async function apiDelete(endpoint) {
    return apiRequest(endpoint, { method: 'DELETE' });
}

async function apiUploadFile(endpoint, file, additionalData = {}) {
    const url = `${API_CONFIG.baseUrl}${endpoint}`;

    const formData = new FormData();
    formData.append('file', file);

    for (const [key, value] of Object.entries(additionalData)) {
        formData.append(key, value);
    }

    try {
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error(`Upload Error (${endpoint}):`, error);
        throw error;
    }
}

// ============================================================================
// EXPOSE API CLIENT
// ============================================================================

contextBridge.exposeInMainWorld('api', {
    // Core methods
    request: apiRequest,
    get: apiGet,
    post: apiPost,
    put: apiPut,
    delete: apiDelete,
    uploadFile: apiUploadFile,

    // Items API (generic collectibles)
    items: {
        list: (params = {}) => {
            const query = new URLSearchParams(params).toString();
            return apiGet(`/items${query ? '?' + query : ''}`);
        },
        get: (id) => apiGet(`/items/${id}`),
        create: (data) => apiPost('/items', data),
        update: (id, data) => apiPut(`/items/${id}`, data),
        delete: (id) => apiDelete(`/items/${id}`),
        search: (query) => apiPost('/items/search', query)
    },

    // Comics API (legacy support)
    comics: {
        list: (params = {}) => {
            const query = new URLSearchParams(params).toString();
            return apiGet(`/comics${query ? '?' + query : ''}`);
        },
        get: (id) => apiGet(`/comics/${id}`),
        create: (data) => apiPost('/comics', data),
        update: (id, data) => apiPut(`/comics/${id}`, data),
        delete: (id) => apiDelete(`/comics/${id}`),
        search: (query) => apiPost('/comics/search', query)
    },

    // Grading API
    grading: {
        grade: (itemId, options = {}) => {
            const params = new URLSearchParams(options).toString();
            return apiPost(`/grade/${itemId}${params ? '?' + params : ''}`, {});
        },
        batchGrade: (itemIds) => apiPost('/grade/batch', { item_ids: itemIds }),
        getDefects: (itemId) => apiGet(`/grade/${itemId}/defects`),
        getHistory: (itemId) => apiGet(`/grade/${itemId}/history`)
    },

    // Pricing API
    pricing: {
        getPrice: (itemId) => apiPost(`/price/${itemId}`, {}),
        getPriceHistory: (itemId) => apiGet(`/price/${itemId}/history`),
        comparePrices: (itemId) => apiGet(`/price/${itemId}/compare`),
        getMarketTrends: (category) => apiGet(`/price/trends/${category}`)
    },

    // Stats API
    stats: {
        get: () => apiGet('/stats'),
        getByCollection: (collectionId) => apiGet(`/stats/collection/${collectionId}`),
        getValueHistory: () => apiGet('/stats/value-history'),
        getGradingStats: () => apiGet('/stats/grading')
    },

    // Review API
    review: {
        pending: () => apiGet('/review/pending'),
        submit: (itemId, grade, notes) => {
            const params = new URLSearchParams({ grade, notes }).toString();
            return apiPost(`/review/${itemId}?${params}`, {});
        },
        reject: (itemId, reason) => apiPost(`/review/${itemId}/reject`, { reason })
    },

    // Export API
    export: {
        generate: (options) => apiPost('/export', options),
        publish: (itemIds) => apiPost('/publish', itemIds),
        formats: () => apiGet('/export/formats'),
        history: () => apiGet('/export/history')
    },

    // Collections API
    collections: {
        list: () => apiGet('/collections'),
        types: () => apiGet('/collections/types'),
        getDefault: () => apiGet('/collections/default'),
        get: (id) => apiGet(`/collections/${id}`),
        create: (data) => apiPost('/collections', data),
        update: (id, data) => apiPut(`/collections/${id}`, data),
        delete: (id, moveItemsTo = null) => {
            const query = moveItemsTo ? `?move_items_to=${moveItemsTo}` : '';
            return apiDelete(`/collections/${id}${query}`);
        },
        setDefault: (id) => apiPost(`/collections/${id}/set-default`, {}),
        getStats: (id) => apiGet(`/collections/${id}/stats`),
        moveItems: (id, itemIds) => apiPost(`/collections/${id}/move-items`, itemIds),
        getValueHistory: (id) => apiGet(`/collections/${id}/value-history`)
    },

    // Profile API
    profile: {
        get: () => apiGet('/profile'),
        update: (data) => apiPut('/profile', data)
    },

    // Settings API
    settings: {
        get: () => apiGet('/settings'),
        update: (key, value) => apiPut(`/settings/${key}`, { value }),
        reset: () => apiPost('/settings/reset', {})
    },

    // Quick Add & Batch Operations
    quickAdd: (data) => apiPost('/items/quick-add', data),
    getPending: (limit = 50) => apiGet(`/items/pending?limit=${limit}`),
    gradePending: (limit = 10) => apiPost(`/items/grade-pending?limit=${limit}`, {}),
    batchImport: (items) => apiPost('/items/batch-import', { items }),
    batchExport: (itemIds, format) => apiPost('/items/batch-export', { item_ids: itemIds, format })
});

// ============================================================================
// WEBSOCKET CONNECTION
// ============================================================================

const websocketState = {
    ws: null,
    listeners: new Map(),
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectDelay: 5000
};

contextBridge.exposeInMainWorld('websocket', {
    async connect() {
        const wsUrl = API_CONFIG.baseUrl.replace('http', 'ws') + '/ws';

        return new Promise((resolve, reject) => {
            websocketState.ws = new WebSocket(wsUrl);

            websocketState.ws.onopen = () => {
                console.log('WebSocket connected');
                websocketState.reconnectAttempts = 0;
                resolve(true);
            };

            websocketState.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };

            websocketState.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    const eventType = data.event;

                    if (websocketState.listeners.has(eventType)) {
                        websocketState.listeners.get(eventType).forEach(cb => cb(data));
                    }

                    // Also emit to 'all' listeners
                    if (websocketState.listeners.has('all')) {
                        websocketState.listeners.get('all').forEach(cb => cb(data));
                    }
                } catch (e) {
                    console.error('WebSocket message parse error:', e);
                }
            };

            websocketState.ws.onclose = () => {
                console.log('WebSocket disconnected');

                // Auto-reconnect with exponential backoff
                if (websocketState.reconnectAttempts < websocketState.maxReconnectAttempts) {
                    websocketState.reconnectAttempts++;
                    const delay = websocketState.reconnectDelay * websocketState.reconnectAttempts;
                    console.log(`Reconnecting in ${delay}ms (attempt ${websocketState.reconnectAttempts})...`);
                    setTimeout(() => this.connect(), delay);
                }
            };
        });
    },

    disconnect() {
        if (websocketState.ws) {
            websocketState.ws.close();
            websocketState.ws = null;
        }
    },

    on(event, callback) {
        if (!websocketState.listeners.has(event)) {
            websocketState.listeners.set(event, []);
        }
        websocketState.listeners.get(event).push(callback);
    },

    off(event, callback) {
        if (websocketState.listeners.has(event)) {
            const listeners = websocketState.listeners.get(event);
            const index = listeners.indexOf(callback);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    },

    send(data) {
        if (websocketState.ws && websocketState.ws.readyState === WebSocket.OPEN) {
            websocketState.ws.send(JSON.stringify(data));
        }
    },

    isConnected() {
        return websocketState.ws && websocketState.ws.readyState === WebSocket.OPEN;
    }
});

// ============================================================================
// PERFORMANCE MONITORING
// ============================================================================

contextBridge.exposeInMainWorld('performance', {
    /**
     * Mark a performance timestamp
     */
    mark: (name) => {
        if (window.performance) {
            window.performance.mark(name);
        }
    },

    /**
     * Measure between two marks
     */
    measure: (name, startMark, endMark) => {
        if (window.performance) {
            try {
                window.performance.measure(name, startMark, endMark);
                const entries = window.performance.getEntriesByName(name);
                return entries.length > 0 ? entries[entries.length - 1].duration : null;
            } catch (e) {
                return null;
            }
        }
        return null;
    },

    /**
     * Get memory usage (if available)
     */
    getMemory: () => {
        if (window.performance && window.performance.memory) {
            return {
                usedJSHeapSize: window.performance.memory.usedJSHeapSize,
                totalJSHeapSize: window.performance.memory.totalJSHeapSize,
                jsHeapSizeLimit: window.performance.memory.jsHeapSizeLimit
            };
        }
        return null;
    }
});

console.log('EPOCGS Preload v3.0.0 initialized');
