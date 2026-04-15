/* ============================================================
 * Service Worker for EuroPCR 2026 Guide
 *
 * Strategy:
 *   - Cache-first for app shell (HTML, CSS, JS, icons, manifest)
 *   - Cache-first with network fallback for data JSON (bundled content)
 *   - Stale-while-revalidate for data when online
 *
 * To force update: bump CACHE_VERSION.
 * ============================================================ */

'use strict';

// Bump this when you want all clients to clear their cache.
const CACHE_VERSION = 'v2.1.0';
const CACHE_NAME = `europcr2026-${CACHE_VERSION}`;

const APP_SHELL = [
  './',
  './index.html',
  './style.css?v=2.1.0',
  './app.js?v=2.1.0',
  './manifest.webmanifest',
  './icons/icon.svg',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './data/meta.json',
  './data/schedule.json',
  './data/sessions.json',
  './data/speakers.json',
  './data/trials.json',
];

// ---- Install: precache everything ----
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(APP_SHELL).catch((err) => {
        console.warn('[SW] Precache partial failure:', err);
        // Don't fail install if some files are missing (e.g. icons not yet generated)
      });
    })
  );
  self.skipWaiting();
});

// ---- Activate: delete old caches ----
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k.startsWith('europcr2026-') && k !== CACHE_NAME)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ---- Fetch: cache-first with network fallback ----
self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Only handle same-origin GETs
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Network-first for data files (lets user get fresh schedule when online)
  if (url.pathname.includes('/data/')) {
    event.respondWith(networkFirst(req));
    return;
  }

  // Cache-first for everything else (app shell)
  event.respondWith(cacheFirst(req));
});

async function cacheFirst(req) {
  const cached = await caches.match(req);
  if (cached) return cached;
  try {
    const fresh = await fetch(req);
    if (fresh.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(req, fresh.clone());
    }
    return fresh;
  } catch (err) {
    // Offline and not cached -- return a simple error response
    return new Response('Offline and resource not cached', { status: 503 });
  }
}

async function networkFirst(req) {
  try {
    const fresh = await fetch(req);
    if (fresh.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(req, fresh.clone());
    }
    return fresh;
  } catch (err) {
    const cached = await caches.match(req);
    if (cached) return cached;
    return new Response('Offline and data not cached', { status: 503 });
  }
}

// Allow main thread to trigger cache refresh
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (event.data && event.data.type === 'REFRESH_DATA') {
    caches.open(CACHE_NAME).then(async (cache) => {
      const dataUrls = APP_SHELL.filter((u) => u.includes('/data/'));
      for (const u of dataUrls) {
        try {
          const resp = await fetch(u, { cache: 'no-cache' });
          if (resp.ok) await cache.put(u, resp.clone());
        } catch (err) { /* ignore */ }
      }
      event.ports[0]?.postMessage({ ok: true });
    });
  }
});
