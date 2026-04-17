/* OBS Portal Service Worker
 * Strateji:
 * - HTML sayfa istekleri: network-first, basarisizsa cache, o da yoksa offline sayfasi.
 * - Statik varliklar (/static/...): cache-first, sonra network.
 * - Kapsam: /portal/ ve statik varliklar.
 */

const CACHE_VERSION = 'obs-portal-v2';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const RUNTIME_CACHE = `${CACHE_VERSION}-runtime`;

const PRECACHE_URLS = [
  '/portal/',
  '/portal/offline',
  '/static/pwa/manifest.webmanifest',
  '/static/pwa/icons/icon-192.png',
  '/static/pwa/icons/icon-512.png',
  '/static/css/custom.css',
  '/static/js/app.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      // Tek tek ekliyoruz ki biri 404 donse bile SW install'u patlamasin
      return Promise.all(
        PRECACHE_URLS.map((url) =>
          cache.add(url).catch((err) => {
            console.warn('[SW] precache atlandi:', url, err);
          })
        )
      );
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => !k.startsWith(CACHE_VERSION))
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

function isHtmlRequest(request) {
  return request.mode === 'navigate' ||
    (request.method === 'GET' &&
      request.headers.get('accept') &&
      request.headers.get('accept').includes('text/html'));
}

self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Sadece GET isteklerini yonetiyoruz
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // POST/login/logout vb icin SW'i es gec
  if (url.pathname.startsWith('/auth/')) return;

  // HTML navigasyon: network-first
  if (isHtmlRequest(request)) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Basarili cevaplari runtime cache'e at
          if (response && response.status === 200 && response.type === 'basic') {
            const clone = response.clone();
            caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() =>
          caches.match(request).then(
            (cached) => cached || caches.match('/portal/offline')
          )
        )
    );
    return;
  }

  // Statik varliklar: cache-first
  if (url.pathname.startsWith('/static/') ||
      url.hostname === 'cdn.jsdelivr.net' ||
      url.hostname === 'fonts.googleapis.com' ||
      url.hostname === 'fonts.gstatic.com') {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(STATIC_CACHE).then((cache) => cache.put(request, clone));
          }
          return response;
        }).catch(() => cached);
      })
    );
    return;
  }

  // Diger GET istekleri: network, basarisizsa cache
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});

// "Yeni surum var" - window'a mesaj gonder
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// === Web Push ===============================================================
// Backend payload format: { title, body, url, icon, badge, tag }
self.addEventListener('push', (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (e) {
    payload = { title: 'OBS Bildirim', body: event.data ? event.data.text() : '' };
  }

  const title = payload.title || 'OBS Bildirim';
  const options = {
    body: payload.body || '',
    icon: payload.icon || '/static/pwa/icons/icon-192.png',
    badge: payload.badge || '/static/pwa/icons/icon-192.png',
    tag: payload.tag || 'obs-notification',
    data: { url: payload.url || '/portal/' },
    renotify: true,
    requireInteraction: false
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// Bildirime tiklaninca uygulamayi ac / odakla
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || '/portal/';

  event.waitUntil((async () => {
    const allClients = await self.clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    });
    // Acik bir pencere varsa onu kullan
    for (const client of allClients) {
      try {
        const url = new URL(client.url);
        if (url.pathname.startsWith('/portal') || url.pathname === '/') {
          await client.focus();
          if ('navigate' in client) {
            try { await client.navigate(targetUrl); } catch (_) {}
          }
          return;
        }
      } catch (_) {}
    }
    // Yoksa yeni pencere ac
    await self.clients.openWindow(targetUrl);
  })());
});
