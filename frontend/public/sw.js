/**
 * Service Worker for Raster to SVG PWA — Phase 8
 *
 * Implements:
 * - Cache-first for static assets (app shell)
 * - Network-first for API calls
 * - Stale-while-revalidate for WASM modules
 * - Offline conversion using WASM engine
 * - Background sync for queued server conversions
 */

const CACHE_VERSION = 'raster-svg-v1';
const STATIC_CACHE = `static-${CACHE_VERSION}`;
const WASM_CACHE = `wasm-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `dynamic-${CACHE_VERSION}`;

// App shell files to precache
const PRECACHE_URLS = [
    '/',
    '/convert',
    '/convert-new',
    '/history',
    '/offline',
    '/manifest.json',
];

// WASM module URLs
const WASM_URLS = [
    '/wasm/vtracer_wasm_bg.wasm',
    '/wasm/vtracer_wasm.js',
];

// =============================================================================
// Install: Precache static assets
// =============================================================================
self.addEventListener('install', (event) => {
    event.waitUntil(
        Promise.all([
            // Cache app shell
            caches.open(STATIC_CACHE).then((cache) => {
                return cache.addAll(PRECACHE_URLS).catch((err) => {
                    console.warn('Precache partial failure:', err);
                });
            }),
            // Cache WASM modules
            caches.open(WASM_CACHE).then((cache) => {
                return cache.addAll(WASM_URLS).catch((err) => {
                    console.warn('WASM precache not available yet:', err);
                });
            }),
        ]).then(() => self.skipWaiting())
    );
});

// =============================================================================
// Activate: Clean old caches
// =============================================================================
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => {
                        return name !== STATIC_CACHE &&
                            name !== WASM_CACHE &&
                            name !== DYNAMIC_CACHE;
                    })
                    .map((name) => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

// =============================================================================
// Fetch: Route requests to appropriate strategy
// =============================================================================
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests (upload, conversion POSTs)
    if (request.method !== 'GET') return;

    // API calls: Network-first
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(request));
        return;
    }

    // WASM modules: Stale-while-revalidate (large files, rarely change)
    if (url.pathname.startsWith('/wasm/')) {
        event.respondWith(staleWhileRevalidate(request, WASM_CACHE));
        return;
    }

    // Static assets: Cache-first
    if (
        url.pathname.match(/\.(js|css|png|jpg|svg|ico|woff2?)$/) ||
        PRECACHE_URLS.includes(url.pathname)
    ) {
        event.respondWith(cacheFirst(request));
        return;
    }

    // Pages: Network-first with offline fallback
    event.respondWith(networkFirstWithFallback(request));
});

// =============================================================================
// Caching Strategies
// =============================================================================

async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;

    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        return new Response('Offline', { status: 503 });
    }
}

async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        const cached = await caches.match(request);
        if (cached) return cached;
        return new Response(
            JSON.stringify({ error: 'Offline', offline: true }),
            { status: 503, headers: { 'Content-Type': 'application/json' } }
        );
    }
}

async function networkFirstWithFallback(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        const cached = await caches.match(request);
        if (cached) return cached;

        // Offline fallback page
        const offlinePage = await caches.match('/offline');
        if (offlinePage) return offlinePage;

        return new Response(
            '<html><body><h1>Offline</h1><p>Please check your connection. Client-side WASM conversion is available offline.</p></body></html>',
            { status: 503, headers: { 'Content-Type': 'text/html' } }
        );
    }
}

async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);

    const fetchPromise = fetch(request)
        .then((response) => {
            if (response.ok) {
                cache.put(request, response.clone());
            }
            return response;
        })
        .catch(() => null);

    return cached || (await fetchPromise) || new Response('Offline', { status: 503 });
}

// =============================================================================
// Background Sync for queued conversions
// =============================================================================
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-conversions') {
        event.waitUntil(syncQueuedConversions());
    }
});

async function syncQueuedConversions() {
    // Retrieve queued conversion requests from IndexedDB
    // and submit them to the server when back online
    try {
        const db = await openDB();
        const tx = db.transaction('pending-conversions', 'readonly');
        const store = tx.objectStore('pending-conversions');
        const requests = await getAllFromStore(store);

        for (const req of requests) {
            try {
                const response = await fetch('/api/v1/convert', {
                    method: 'POST',
                    body: req.formData,
                });

                if (response.ok) {
                    // Remove from queue
                    const deleteTx = db.transaction('pending-conversions', 'readwrite');
                    deleteTx.objectStore('pending-conversions').delete(req.id);

                    // Notify the client
                    self.clients.matchAll().then((clients) => {
                        clients.forEach((client) => {
                            client.postMessage({
                                type: 'sync-complete',
                                id: req.id,
                                result: 'success',
                            });
                        });
                    });
                }
            } catch {
                // Will retry on next sync
            }
        }
    } catch (err) {
        console.error('Sync failed:', err);
    }
}

function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('raster-svg-sw', 1);
        request.onupgradeneeded = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains('pending-conversions')) {
                db.createObjectStore('pending-conversions', { keyPath: 'id' });
            }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

function getAllFromStore(store) {
    return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

// =============================================================================
// Push Notifications (conversion complete)
// =============================================================================
self.addEventListener('push', (event) => {
    if (!event.data) return;

    const data = event.data.json();

    event.waitUntil(
        self.registration.showNotification(data.title || 'Conversion Complete', {
            body: data.body || 'Your SVG is ready to download',
            icon: '/icons/icon-192x192.png',
            badge: '/icons/icon-72x72.png',
            tag: data.tag || 'conversion',
            data: data.url || '/',
            actions: [
                { action: 'download', title: 'Download SVG' },
                { action: 'view', title: 'View Result' },
            ],
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = event.notification.data || '/';

    event.waitUntil(
        self.clients.matchAll({ type: 'window' }).then((clients) => {
            for (const client of clients) {
                if (client.url === url && 'focus' in client) {
                    return client.focus();
                }
            }
            return self.clients.openWindow(url);
        })
    );
});
