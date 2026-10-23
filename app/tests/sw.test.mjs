// Runs app/sw.js in a VM sandbox with fake `caches` and `fetch` to check the caching policy.
// (The embedded browser used during development blocks service workers, so this is the automated check.)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
import { currentVersion } from '../tools/stamp-sw.mjs';
const VERSION = currentVersion();

const SRC = readFileSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'sw.js'), 'utf8');
const ORIGIN = 'http://farm.test';

function makeEnv(fetchImpl) {
  const store = new Map(); // cacheName -> Map(url -> Response)
  const open = async (name) => {
    if (!store.has(name)) store.set(name, new Map());
    const m = store.get(name);
    return {
      put: async (req, res) => { m.set(typeof req === 'string' ? new URL(req, ORIGIN).href : req.url, res); },
      match: async (req) => { const r = m.get(typeof req === 'string' ? new URL(req, ORIGIN).href : req.url); return r ? r.clone() : undefined; },
      addAll: async (urls) => { for (const u of urls) m.set(new URL(u, ORIGIN + '/').href, new Response('x')); },
      keys: async () => [...m.keys()],
    };
  };
  const caches = {
    open, keys: async () => [...store.keys()], delete: async (k) => store.delete(k),
    match: async (req) => { for (const n of store.keys()) { const r = await (await open(n)).match(req); if (r) return r; } return undefined; },
  };
  const handlers = {};
  const self = { addEventListener: (t, fn) => { handlers[t] = fn; }, location: { origin: ORIGIN }, skipWaiting: () => {}, clients: { claim: () => {} } };
  const ctx = vm.createContext({ self, caches, fetch: fetchImpl, Response, Headers, Request, URL, setTimeout, clearTimeout, Promise, console });
  vm.runInContext(SRC, ctx);
  const fire = async (req) => {
    let p = null;
    handlers.fetch({ request: req, respondWith: (x) => { p = x; } });
    return p ? await p : null;
  };
  const lifecycle = async (type) => { let w; handlers[type]({ waitUntil: (x) => { w = x; } }); await w; };
  return { store, fire, lifecycle, caches };
}

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

test('API GET: network-first, saved to cache, then served from cache with X-From-Cache when offline', async () => {
  let online = true;
  const env = makeEnv(async () => { if (!online) throw new TypeError('offline'); return json({ data_as_of: '2026-04-21' }); });
  const r1 = await env.fire(new Request(`${ORIGIN}/api/v1/meta`));
  assert.equal(r1.status, 200);
  assert.equal(r1.headers.get('X-From-Cache'), null);
  online = false;
  const r2 = await env.fire(new Request(`${ORIGIN}/api/v1/meta`));
  assert.equal(r2.status, 200);
  assert.ok(!Number.isNaN(Date.parse(r2.headers.get('X-From-Cache'))), 'X-From-Cache carries the save time');
  assert.deepEqual(await r2.json(), { data_as_of: '2026-04-21' });
});

test('error responses are never cached; offline with nothing cached is a network error', async () => {
  let mode = 'err';
  const env = makeEnv(async () => { if (mode === 'off') throw new TypeError('offline'); return json({ error: { code: 'unavailable' } }, 503); });
  const r1 = await env.fire(new Request(`${ORIGIN}/api/v1/alerts`));
  assert.equal(r1.status, 503);
  mode = 'off';
  const r2 = await env.fire(new Request(`${ORIGIN}/api/v1/alerts`));
  assert.equal(r2.type, 'error');
});

test('a JSON 404 (unknown id) is passed through, not masked by cache', async () => {
  const env = makeEnv(async () => json({ error: { code: 'not_found', message: 'x' } }, 404));
  const r = await env.fire(new Request(`${ORIGIN}/api/v1/series/123`));
  assert.equal(r.status, 404);
  assert.equal((await env.caches.keys()).includes(`agri-api-${VERSION}`) ? (await (await env.caches.open(`agri-api-${VERSION}`)).keys()).length : 0, 0);
});

test('non-GET requests are not intercepted', async () => {
  const env = makeEnv(async () => json({}));
  assert.equal(await env.fire(new Request(`${ORIGIN}/api/v1/meta`, { method: 'POST', body: '{}' })), null);
});

test('install precaches the shell; activate removes old versioned caches only', async () => {
  const env = makeEnv(async () => new Response('net'));
  await (await env.caches.open('agri-shell-v0')).put(`${ORIGIN}/old`, new Response('old'));
  await (await env.caches.open('someone-else')).put(`${ORIGIN}/x`, new Response('x'));
  await env.lifecycle('install');
  await env.lifecycle('activate');
  const keys = await env.caches.keys();
  assert.ok(keys.includes(`agri-shell-${VERSION}`));
  assert.ok(!keys.includes('agri-shell-v0'), 'old version removed');
  assert.ok(keys.includes('someone-else'), 'foreign caches untouched');
  const shell = await (await env.caches.open(`agri-shell-${VERSION}`)).keys();
  for (const f of ['index.html', 'js/app.js', 'i18n/ta.json', 'icons/icon-512.png', 'icons/commodities/tomato.svg']) {
    assert.ok(shell.includes(`${ORIGIN}/${f}`), `${f} precached`);
  }
});

test('navigation falls back to the cached app shell when offline', async () => {
  let online = true;
  const env = makeEnv(async () => { if (!online) throw new TypeError('offline'); return new Response('net'); });
  await env.lifecycle('install');
  online = false;
  const req = { method: 'GET', url: `${ORIGIN}/`, mode: 'navigate' }; // Request() refuses mode 'navigate'
  const r = await env.fire(req);
  assert.equal(await r.text(), 'x'); // the precached index.html stub
});
