// Finance Slip — service worker
// Caches the app shell so the app opens offline. OCR/QR libraries and Google Sheet
// sync still need internet the first time / when syncing.
const CACHE = 'finance-slip-v1';
const SHELL = [
  './',
  'index.html',
  'manifest.webmanifest',
  'icon-180.png',
  'icon-192.png',
  'icon-512.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  // Never cache Google Apps Script calls or CDN library requests — always go to network
  if (req.url.includes('script.google.com') ||
      req.url.includes('cdnjs.cloudflare.com') ||
      req.url.includes('cdn.jsdelivr.net') ||
      req.url.includes('fonts.googleapis.com') ||
      req.method !== 'GET') {
    return; // let the browser handle it normally
  }
  // App shell: cache-first, fall back to network
  e.respondWith(
    caches.match(req).then((cached) =>
      cached || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      }).catch(() => cached)
    )
  );
});
