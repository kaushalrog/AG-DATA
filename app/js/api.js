// API client for docs/API.md. Order of preference:
//   1. network (via the service worker, which falls back to its cache and marks X-From-Cache)
//   2. demo snapshot in demo/ (only when the API is unreachable AND nothing was served from cache)
import { API_BASE, API_TIMEOUT_MS } from '../config.js';

export class ApiError extends Error {
  constructor(code) { super(code); this.code = code; }
}

const listeners = new Set();
export const status = { mode: 'live', cachedAt: null, meta: null };
export function onStatus(fn) { listeners.add(fn); }
function emit() { listeners.forEach((fn) => fn(status)); }

let demoIndex;
let forceDemo = false;

function qs(params) {
  if (!params) return '';
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') u.set(k, v);
  const s = u.toString();
  return s ? '?' + s : '';
}

async function fetchTimeout(url) {
  const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
  const timer = ctl && setTimeout(() => ctl.abort(), API_TIMEOUT_MS);
  try { return await fetch(url, { signal: ctl && ctl.signal, headers: { Accept: 'application/json' } }); }
  finally { if (timer) clearTimeout(timer); }
}

export async function get(path, params) {
  if (!forceDemo) {
    let res;
    try { res = await fetchTimeout(API_BASE + path + qs(params)); } catch { res = null; }
    const json = res && (res.headers.get('content-type') || '').includes('json');
    if (res && json) {
      const body = await res.json().catch(() => null);
      if (res.ok && body) {
        const cached = res.headers.get('X-From-Cache');
        if (cached !== null) { status.mode = 'cache'; status.cachedAt = cached || null; }
        else { status.mode = 'live'; status.cachedAt = null; } // back online: clear the offline badge
        emit();
        return body;
      }
      if (res.status !== 503) throw new ApiError((body && body.error && body.error.code) || 'unavailable');
    }
    // Unreachable (network error, timeout, 503 or a non-JSON reply such as a static server's 404).
    if (status.mode === 'cache') throw new ApiError('network');
    if (!(await loadDemoIndex())) throw new ApiError('network');
    forceDemo = true;
    status.mode = 'demo';
    emit();
  }
  return demoGet(path, params || {});
}

/** Called by "Try again": go back to the network on the next request. */
export function resetMode() { forceDemo = false; status.mode = 'live'; status.cachedAt = null; }

async function loadDemoIndex() {
  if (demoIndex !== undefined) return demoIndex;
  try {
    const r = await fetch('demo/index.json');
    demoIndex = r.ok ? await r.json() : null;
  } catch { demoIndex = null; }
  return demoIndex;
}

async function demoFile(name) {
  const r = await fetch('demo/' + name);
  if (!r.ok) throw new ApiError('not_found');
  return r.json();
}

const has = (v, q) => !q || String(v || '').toLowerCase().includes(String(q).toLowerCase());
const eq = (a, b) => !b || a === b;

/** Serve an endpoint from the demo snapshot, relying only on demo/index.json. */
async function demoGet(path, p) {
  const idx = await loadDemoIndex();
  if (!idx) throw new ApiError('network');
  const m = path.match(/^\/(series|forecast|compare)\/(.+)$/);
  if (m) {
    const [, kind, id] = m;
    const ids = (idx.entities && idx.entities[kind]) || [];
    if (!ids.includes(decodeURIComponent(id))) throw new ApiError('not_found');
    return demoFile(`${kind}_${decodeURIComponent(id)}.json`);
  }
  const key = path.replace(/^\//, '').replace('/', '_');
  const file = idx.files && idx.files[key];
  if (!file) throw new ApiError('not_found');
  const data = await demoFile(file);
  const lim = +p.limit || 50, off = +p.offset || 0;
  if (key === 'prices_latest') {
    const items = data.items.filter((it) => eq(it.entity.state, p.state) && eq(it.entity.district, p.district)
      && eq(it.entity.market, p.market) && eq(it.entity.commodity, p.commodity)
      && (has(it.entity.commodity, p.q) || has(it.entity.market, p.q)));
    return { total: items.length, limit: lim, offset: off, items: items.slice(off, off + lim) };
  }
  if (key === 'markets') {
    const items = (data.items || []).filter((it) => eq(it.state, p.state) && eq(it.district, p.district) && has(it.market, p.q));
    return { total: items.length, limit: lim, offset: off, items: items.slice(off, off + lim) };
  }
  if (key === 'trends' && p.state && data.state !== p.state) {
    const f = idx.trends_by_state && idx.trends_by_state[p.state];
    return f ? demoFile(f) : { state: p.state, as_of: data.as_of, rising: [], falling: [] };
  }
  if (key === 'alerts') {
    return { items: (data.items || []).filter((it) => eq(it.entity.state, p.state) && eq(it.entity.commodity, p.commodity)) };
  }
  return data;
}

// Convenience wrappers (names follow docs/API.md).
export const meta = async () => { const m = await get('/meta'); status.meta = m; emit(); return m; };
export const states = () => get('/states');
export const markets = (p) => get('/markets', p);
export const commodities = (p) => get('/commodities', p);
export const latest = (p) => get('/prices/latest', p);
export const series = (id, days = 180) => get('/series/' + encodeURIComponent(id), { days });
export const forecast = (id) => get('/forecast/' + encodeURIComponent(id));
export const compare = (id, scope = 'district') => get('/compare/' + encodeURIComponent(id), { scope, limit: 20 });
export const alerts = (p) => get('/alerts', p);
export const trends = (p) => get('/trends', p);
