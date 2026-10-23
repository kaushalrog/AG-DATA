// AG-DATA service worker.
//  * app shell: precached; served from cache and revalidated in the background (stale-while-revalidate).
//    VERSION is a content hash of the shell (app/tools/stamp-sw.mjs), so every change installs a new cache.
//  * GET /api/*: network-first with timeout; on failure the last good response is returned
//    with header X-From-Cache: <ISO time it was saved> so the UI can say "Offline – saved data from …"
//  * never caches non-GET requests or error responses; old caches removed on activate
const VERSION = 'v-1da619f5ac72';
const SHELL = `agri-shell-${VERSION}`;
const API = `agri-api-${VERSION}`;
const API_TIMEOUT = 5000;

const PRECACHE = [
  './', 'index.html', 'offline.html', 'manifest.webmanifest', 'config.js', 'css/app.css',
  'js/app.js', 'js/api.js', 'js/i18n.js', 'js/format.js', 'js/decision.js', 'js/store.js', 'js/ui.js', 'js/chart.js',
  'js/routes/home.js', 'js/routes/commodity.js', 'js/routes/compare.js', 'js/routes/markets.js',
  'js/routes/alerts.js', 'js/routes/guide.js', 'js/routes/settings.js', 'js/routes/onboarding.js',
  'i18n/en.json', 'i18n/ta.json', 'i18n/te.json', 'i18n/ml.json', 'i18n/hi.json', 'i18n/kn.json', 'i18n/commodities.json',
  'icons/app-icon.svg', 'icons/icon-192.png', 'icons/icon-512.png',
];
const ICONS = ['banana', 'brinjal', 'carrot', 'chilli', 'cotton', 'fruit', 'garlic', 'gourd', 'grain', 'leafy', 'maize', 'oilseed',
  'okra', 'onion', 'potato', 'produce', 'pulse', 'pumpkin', 'spice', 'tomato'];
PRECACHE.push(...ICONS.map((n) => `icons/commodities/${n}.svg`));

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k.startsWith('agri-') && k !== SHELL && k !== API).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const isJson = (res) => (res.headers.get('content-type') || '').includes('json');

async function fetchWithTimeout(req, ms) {
  let id;
  const timer = new Promise((_, rej) => { id = setTimeout(() => rej(new Error('timeout')), ms); });
  try { return await Promise.race([fetch(req), timer]); } finally { clearTimeout(id); }
}

async function apiNetworkFirst(req) {
  const cache = await caches.open(API);
  let net = null;
  try {
    net = await fetchWithTimeout(req, API_TIMEOUT);
    if (net.ok && isJson(net)) {
      const body = await net.clone().blob();
      const headers = new Headers(net.headers);
      headers.set('X-Cached-At', new Date().toISOString());
      cache.put(req, new Response(body, { status: 200, headers }));
      return net;
    }
    if (net.status < 500 && net.status !== 404 && isJson(net)) return net; // real 4xx from the API (400/429)
    if (net.status === 404 && isJson(net)) return net;                       // unknown id: do not mask with cache
  } catch { /* offline or timed out */ }
  const hit = await cache.match(req);
  if (hit) {
    const headers = new Headers(hit.headers);
    headers.set('X-From-Cache', hit.headers.get('X-Cached-At') || '');
    return new Response(await hit.blob(), { status: 200, headers });
  }
  return net || Response.error();
}

async function shellCacheFirst(req) {
  const hit = await caches.match(req, { ignoreSearch: true });
  if (hit) {
    // revalidate in the background; the next load gets the new copy
    fetch(req).then(async (res) => {
      if (res.ok && res.type === 'basic') (await caches.open(SHELL)).put(req, res.clone());
    }).catch(() => {});
    return hit;
  }
  try {
    const res = await fetch(req);
    if (res.ok && res.type === 'basic') (await caches.open(SHELL)).put(req, res.clone());
    return res;
  } catch {
    if (req.mode === 'navigate') return (await caches.match('index.html')) || caches.match('offline.html');
    return Response.error();
  }
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return; // never touch non-GET
  const url = new URL(req.url);
  if (url.pathname.includes('/api/')) { e.respondWith(apiNetworkFirst(req)); return; }
  if (url.origin !== self.location.origin) return;
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).catch(async () => (await caches.match('index.html')) || caches.match('offline.html')));
    return;
  }
  e.respondWith(shellCacheFirst(req));
});
