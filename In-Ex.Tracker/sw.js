// Finance Slip — service worker
const CACHE = 'finance-slip-v8';
const SHELL = [
  './',
  'index.html',
  'styles.css',
  'manifest.webmanifest',
  'icon-180.png',
  'icon-192.png',
  'icon-512.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {})
  );
  // don't skipWaiting here — wait for explicit signal or app update button
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// message from app: skip waiting and take control immediately
self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.url.includes('script.google.com') ||
      req.url.includes('cdnjs.cloudflare.com') ||
      req.url.includes('cdn.jsdelivr.net') ||
      req.url.includes('fonts.googleapis.com') ||
      req.method !== 'GET') {
    return;
  }
  // network-first for HTML (ensures fresh app on reload)
  if (req.url.endsWith('.html') || req.url.endsWith('/') || req.url.includes('index.html')) {
    e.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      }).catch(() => caches.match(req))
    );
    return;
  }
  // cache-first for other assets (icons, manifest)
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
