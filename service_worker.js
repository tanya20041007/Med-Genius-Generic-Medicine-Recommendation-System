/**
 * MedGenius — Service Worker  (Feature #17 — PWA)
 * ═════════════════════════════════════════════════
 * Implements a cache-first strategy for static assets and a
 * network-first strategy for API calls, enabling offline access
 * to the medicine database and previously visited pages.
 *
 * Registration (add to index.html <script>):
 *   if ('serviceWorker' in navigator) {
 *     navigator.serviceWorker.register('/service_worker.js')
 *       .then(reg => console.log('SW registered:', reg.scope))
 *       .catch(err => console.error('SW registration failed:', err));
 *   }
 */

const CACHE_VERSION   = 'medgenius-v2.1';
const STATIC_CACHE    = `${CACHE_VERSION}-static`;
const API_CACHE       = `${CACHE_VERSION}-api`;
const OFFLINE_PAGE    = '/offline.html';

// ── Assets to precache on install ────────────────────────────────────────────
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  // Add your CSS/JS bundle paths here:
  // '/static/css/main.css',
  // '/static/js/main.js',
];

// ── API routes to cache with network-first strategy ──────────────────────────
const NETWORK_FIRST_PATTERNS = [
  '/api/medicines',
  '/api/stats',
  '/api/health',
];

// ── Install: precache static assets ──────────────────────────────────────────
self.addEventListener('install', (event) => {
  console.log(`[SW] Installing ${CACHE_VERSION}…`);
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Precaching static assets');
        // Use { cache: 'reload' } to bypass HTTP cache during install
        return Promise.allSettled(
          PRECACHE_URLS.map((url) =>
            cache.add(new Request(url, { cache: 'reload' }))
          )
        );
      })
      .then(() => {
        console.log('[SW] Install complete. Activating immediately.');
        return self.skipWaiting();
      })
  );
});

// ── Activate: clean up old caches ────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  console.log(`[SW] Activating ${CACHE_VERSION}`);
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith('medgenius-') && name !== STATIC_CACHE && name !== API_CACHE)
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => {
      console.log('[SW] Now controlling all clients');
      return self.clients.claim();
    })
  );
});

// ── Fetch: routing logic ──────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET requests (POST, PUT, DELETE — these are API mutations)
  if (event.request.method !== 'GET') return;

  // Skip cross-origin requests (CDN, external APIs)
  if (url.origin !== self.location.origin) return;

  // ── API calls: network-first, fall back to cache ──────────────────────────
  if (url.pathname.startsWith('/api/')) {
    const shouldCache = NETWORK_FIRST_PATTERNS.some((p) => url.pathname.startsWith(p));
    if (shouldCache) {
      event.respondWith(networkFirstWithCache(event.request, API_CACHE));
    } else {
      // Non-cacheable API calls — network only
      event.respondWith(networkOnly(event.request));
    }
    return;
  }

  // ── Static assets: cache-first, fall back to network ─────────────────────
  event.respondWith(cacheFirstWithNetwork(event.request));
});

// ── Push notifications (medication reminders) ─────────────────────────────────
self.addEventListener('push', (event) => {
  let data = { title: 'MedGenius Reminder', body: 'Time to take your medicine!' };
  try {
    data = event.data?.json() || data;
  } catch (_) {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body:    data.body,
      icon:    '/icons/icon-192x192.png',
      badge:   '/icons/icon-96x96.png',
      vibrate: [200, 100, 200],
      data:    { url: data.url || '/#/reminders' },
      actions: [
        { action: 'taken',  title: '✅ Mark as taken' },
        { action: 'snooze', title: '⏰ Snooze 10 min' },
        { action: 'dismiss',title: '✖ Dismiss'        },
      ],
      requireInteraction: true,
    })
  );
});

// ── Notification click handling ───────────────────────────────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const action = event.action;
  const data   = event.notification.data || {};

  if (action === 'dismiss') return;

  if (action === 'snooze') {
    // Re-show notification after 10 minutes
    setTimeout(() => {
      self.registration.showNotification(event.notification.title, {
        body:  event.notification.body + ' (Snoozed)',
        icon:  '/icons/icon-192x192.png',
        badge: '/icons/icon-96x96.png',
        data,
      });
    }, 10 * 60 * 1000);
    return;
  }

  // action === 'taken' or click on notification body → open/focus app
  const targetUrl = action === 'taken'
    ? `/#/reminders?mark_taken=${data.reminder_id || ''}`
    : (data.url || '/#/reminders');

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clients) => {
        // If app already open, focus it
        const existing = clients.find((c) => c.url.includes(self.location.origin));
        if (existing) {
          existing.navigate(targetUrl);
          return existing.focus();
        }
        // Otherwise open new window
        return self.clients.openWindow(targetUrl);
      })
  );
});

// ── Background sync (retry failed API calls when back online) ─────────────────
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-reminders') {
    event.waitUntil(syncReminders());
  }
});

async function syncReminders() {
  console.log('[SW] Background sync: syncing reminders');
  // In a full implementation, retrieve queued POST requests from IndexedDB
  // and replay them against the API once connectivity is restored.
}


// ── Strategy helpers ──────────────────────────────────────────────────────────

/**
 * Network-first: try network, on failure return cached response.
 * Also updates cache on successful network responses.
 */
async function networkFirstWithCache(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (_) {
    const cached = await caches.match(request);
    if (cached) {
      console.log('[SW] Serving from API cache (offline):', request.url);
      return cached;
    }
    // Return a JSON "offline" error response
    return new Response(
      JSON.stringify({ error: 'You are offline. Please check your internet connection.', offline: true }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Cache-first: serve from cache, fall back to network and cache the result.
 * On failure (both cache miss + network failure), serve the offline page.
 */
async function cacheFirstWithNetwork(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (_) {
    console.log('[SW] Offline fallback for:', request.url);
    const offlinePage = await caches.match(OFFLINE_PAGE);
    return offlinePage || new Response('<h1>You are offline</h1>', {
      status: 503,
      headers: { 'Content-Type': 'text/html' },
    });
  }
}

/** Network-only: no caching */
async function networkOnly(request) {
  try {
    return await fetch(request);
  } catch (_) {
    return new Response(
      JSON.stringify({ error: 'Network request failed. You may be offline.', offline: true }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}