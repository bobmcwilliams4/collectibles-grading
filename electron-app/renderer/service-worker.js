/**
 * Service Worker for Offline Support
 * Enables offline functionality for the Collectibles Grading app
 */

const CACHE_NAME = 'collectibles-grading-v1';
const STATIC_CACHE = 'collectibles-static-v1';
const DYNAMIC_CACHE = 'collectibles-dynamic-v1';
const IMAGE_CACHE = 'collectibles-images-v1';

// Assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/app.js',
  '/styles/main.css',
  '/offline.html'
];

// API endpoints to cache
const API_CACHE_PATTERNS = [
  /\/comics\?/,
  /\/comics\/\d+$/,
  /\/stats$/
];

// Image patterns to cache
const IMAGE_PATTERNS = [
  /\.jpg$/i,
  /\.jpeg$/i,
  /\.png$/i,
  /\.webp$/i,
  /\.gif$/i
];

// =============================================================================
// INSTALL EVENT
// =============================================================================

self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker');

  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// =============================================================================
// ACTIVATE EVENT
// =============================================================================

self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              // Delete old caches
              return name.startsWith('collectibles-') &&
                     ![STATIC_CACHE, DYNAMIC_CACHE, IMAGE_CACHE].includes(name);
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// =============================================================================
// FETCH EVENT
// =============================================================================

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Handle different types of requests
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
  } else if (isImageRequest(url)) {
    event.respondWith(cacheFirst(request, IMAGE_CACHE));
  } else if (isAPIRequest(url)) {
    event.respondWith(networkFirst(request, DYNAMIC_CACHE));
  } else {
    event.respondWith(networkFirst(request, DYNAMIC_CACHE));
  }
});

// =============================================================================
// CACHING STRATEGIES
// =============================================================================

/**
 * Cache First Strategy
 * Try cache, fall back to network
 */
async function cacheFirst(request, cacheName) {
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    // Update cache in background
    fetchAndCache(request, cacheName);
    return cachedResponse;
  }

  return fetchAndCache(request, cacheName);
}

/**
 * Network First Strategy
 * Try network, fall back to cache
 */
async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      // Cache the response
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);

    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }

    throw error;
  }
}

/**
 * Stale While Revalidate
 * Return cache immediately, update cache in background
 */
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  const fetchPromise = fetch(request).then((networkResponse) => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  });

  return cachedResponse || fetchPromise;
}

/**
 * Fetch and cache helper
 */
async function fetchAndCache(request, cacheName) {
  try {
    const response = await fetch(request);

    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.error('[SW] Fetch failed:', error);
    throw error;
  }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function isStaticAsset(url) {
  return STATIC_ASSETS.some(asset => url.pathname.endsWith(asset)) ||
         url.pathname.match(/\.(js|css|woff2?|ttf|eot)$/i);
}

function isImageRequest(url) {
  return IMAGE_PATTERNS.some(pattern => pattern.test(url.pathname));
}

function isAPIRequest(url) {
  return url.pathname.startsWith('/api/') ||
         url.pathname.startsWith('/comics') ||
         url.pathname.startsWith('/grade') ||
         url.pathname.startsWith('/price');
}

// =============================================================================
// BACKGROUND SYNC
// =============================================================================

self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);

  if (event.tag === 'sync-grades') {
    event.waitUntil(syncPendingGrades());
  } else if (event.tag === 'sync-comics') {
    event.waitUntil(syncPendingComics());
  }
});

async function syncPendingGrades() {
  // Get pending grade requests from IndexedDB
  const pendingGrades = await getPendingFromIndexedDB('pending-grades');

  for (const gradeRequest of pendingGrades) {
    try {
      const response = await fetch('/grade/' + gradeRequest.comicId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(gradeRequest.data)
      });

      if (response.ok) {
        await removePendingFromIndexedDB('pending-grades', gradeRequest.id);
        console.log('[SW] Synced grade for comic:', gradeRequest.comicId);
      }
    } catch (error) {
      console.error('[SW] Failed to sync grade:', error);
    }
  }
}

async function syncPendingComics() {
  const pendingComics = await getPendingFromIndexedDB('pending-comics');

  for (const comic of pendingComics) {
    try {
      const response = await fetch('/comics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(comic.data)
      });

      if (response.ok) {
        await removePendingFromIndexedDB('pending-comics', comic.id);
        console.log('[SW] Synced comic:', comic.data.title);
      }
    } catch (error) {
      console.error('[SW] Failed to sync comic:', error);
    }
  }
}

// =============================================================================
// INDEXEDDB HELPERS
// =============================================================================

function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('collectibles-offline', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      if (!db.objectStoreNames.contains('pending-grades')) {
        db.createObjectStore('pending-grades', { keyPath: 'id', autoIncrement: true });
      }

      if (!db.objectStoreNames.contains('pending-comics')) {
        db.createObjectStore('pending-comics', { keyPath: 'id', autoIncrement: true });
      }

      if (!db.objectStoreNames.contains('offline-comics')) {
        db.createObjectStore('offline-comics', { keyPath: 'id' });
      }
    };
  });
}

async function getPendingFromIndexedDB(storeName) {
  const db = await openIndexedDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, 'readonly');
    const store = transaction.objectStore(storeName);
    const request = store.getAll();

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

async function removePendingFromIndexedDB(storeName, id) {
  const db = await openIndexedDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, 'readwrite');
    const store = transaction.objectStore(storeName);
    const request = store.delete(id);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

// =============================================================================
// PUSH NOTIFICATIONS
// =============================================================================

self.addEventListener('push', (event) => {
  console.log('[SW] Push received');

  const options = {
    body: event.data ? event.data.text() : 'New update available',
    icon: '/icons/icon-192.png',
    badge: '/icons/badge-72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      { action: 'view', title: 'View' },
      { action: 'close', title: 'Close' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Collectibles Grading', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification click:', event.action);

  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// =============================================================================
// MESSAGE HANDLING
// =============================================================================

self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data.type === 'CACHE_COMIC') {
    cacheComic(event.data.comic);
  }

  if (event.data.type === 'CLEAR_CACHE') {
    clearCache(event.data.cacheName);
  }
});

async function cacheComic(comic) {
  const cache = await caches.open(DYNAMIC_CACHE);

  // Cache comic data
  const response = new Response(JSON.stringify(comic));
  await cache.put(`/comics/${comic.id}`, response);

  // Cache images
  if (comic.front_image_path) {
    try {
      const imgResponse = await fetch(comic.front_image_path);
      const imgCache = await caches.open(IMAGE_CACHE);
      await imgCache.put(comic.front_image_path, imgResponse);
    } catch (e) {
      console.log('[SW] Could not cache image:', e);
    }
  }

  console.log('[SW] Cached comic:', comic.id);
}

async function clearCache(cacheName) {
  if (cacheName) {
    await caches.delete(cacheName);
    console.log('[SW] Cleared cache:', cacheName);
  } else {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map(name => caches.delete(name)));
    console.log('[SW] Cleared all caches');
  }
}
