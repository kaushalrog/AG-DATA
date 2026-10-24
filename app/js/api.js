// API client for docs/API.md. Order of preference:
//   1. network (via the service worker, which falls back to its cache and marks X-From-Cache)
//   2. when the API is unreachable AND nothing was served from cache (e.g. a static host such as GitHub Pages):
//      a. the full published snapshot in snapshot/ (py/agri/analysis/export_snapshot.py), if deployed;
//      b. otherwise the small demo snapshot in demo/.
import { API_BASE, API_TIMEOUT_MS } from '../config.js';
import { RULES } from './decision.js';

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
    if (await loadSnapshot()) status.mode = 'snapshot';
    else if (await loadDemoIndex()) status.mode = 'demo';
    else throw new ApiError('network');
    forceDemo = true;
    emit();
  }
  return snap ? snapGet(path, params || {}) : demoGet(path, params || {});
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

// ---- full published snapshot (static files; same responses as the API, re-packed) --------------------
let snap; // undefined = not checked yet, null = not deployed
const snapCache = new Map();

async function loadSnapshot() {
  if (snap !== undefined) return snap;
  try {
    const r = await fetch('snapshot/current.json', { cache: 'no-store' });
    snap = r.ok && (r.headers.get('content-type') || '').includes('json') ? await r.json() : null;
  } catch { snap = null; }
  return snap;
}

function snapFile(name) {
  const url = `snapshot/${snap.version}/${name}`;
  if (!snapCache.has(url)) {
    snapCache.set(url, fetch(url).then((r) => { if (!r.ok) throw new ApiError('not_found'); return r.json(); })
      .catch((e) => { snapCache.delete(url); throw e instanceof ApiError ? e : new ApiError('network'); }));
  }
  return snapCache.get(url);
}

const cmpStr = (a, b) => (a < b ? -1 : a > b ? 1 : 0); // byte order, as the API's ORDER BY
const r2 = (v) => (v === null || v === undefined ? v : Math.round(v * 100) / 100);
const dayNo = (iso) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) / 864e5;
function localDay(d = new Date()) { return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 864e5; }
/** Same as the API's freshness(): age relative to the dataset's own end date. */
function snapFreshness(iso) {
  if (!iso) return { last_date: null, days_old: null, stale: true };
  const days = dayNo(snap.data_as_of) - dayNo(iso);
  return { last_date: iso, days_old: days, stale: days > RULES.staleAfterDays };
}
const shard = (id) => Number(((BigInt(id) % BigInt(snap.shards)) + BigInt(snap.shards)) % BigInt(snap.shards));
const stateKey = (st) => snap.states[st];

async function stateRows(st) {
  const k = stateKey(st);
  if (!k) return [];
  const f = await snapFile(`state/${k}.json`);
  if (!f._rows) {
    const i = Object.fromEntries(f.fields.map((n, j) => [n, j]));
    f._rows = f.rows.map((r) => ({ r, i, state: f.state }));
  }
  return f._rows;
}
function latestItem({ r, i, state }) {
  return {
    entity: { entity_id: r[i.entity_id], state, district: r[i.district], market: r[i.market], commodity: r[i.commodity],
      variety: r[i.variety], grade: r[i.grade] },
    date: r[i.date], min_price: r[i.min_price], max_price: r[i.max_price], modal_price: r[i.modal_price], unit: 'INR/quintal',
    freshness: snapFreshness(r[i.date]), change_7d_pct: r[i.change_7d_pct], forecast_supported: !!r[i.forecast_supported],
  };
}
async function findRow(id) {
  // the series file names the entity's state, so only that state's file is read
  const s = (await snapFile(`series/${shard(id)}.json`))[id];
  if (!s) throw new ApiError('not_found');
  return { s, row: (await stateRows(s.entity.state)).find((x) => x.r[x.i.entity_id] === id) };
}

async function snapGet(path, p) {
  const lim = +p.limit || 50, off = +p.offset || 0;
  const page = (items) => ({ total: items.length, limit: lim, offset: off, items: items.slice(off, off + lim) });
  const like = (v, q) => String(v || '').toLowerCase().includes(String(q).toLowerCase());
  if (path === '/meta') {
    const m = { ...(await snapFile('meta.json')) };
    m.days_since_data = localDay() - dayNo(m.data_as_of); // the API computes this per request
    return m;
  }
  if (path === '/states') return snapFile('states.json');
  if (path === '/commodities') return snapFile('commodities.json');
  if (path === '/markets') {
    const states = p.state ? [p.state] : Object.keys(snap.states);
    let items = [];
    for (const st of states) if (stateKey(st)) items = items.concat((await snapFile(`markets/${stateKey(st)}.json`)).items);
    items = items.filter((m) => (!p.district || m.district === p.district) && (!p.q || like(m.market, p.q)));
    return page(items);
  }
  if (path === '/prices/latest') {
    const states = p.state ? [p.state] : Object.keys(snap.states);
    let rows = [];
    for (const st of states) rows = rows.concat(await stateRows(st));
    rows = rows.filter(({ r, i }) => (!p.district || r[i.district] === p.district) && (!p.market || r[i.market] === p.market)
      && (!p.commodity || r[i.commodity] === p.commodity) && (!p.q || like(r[i.commodity], p.q) || like(r[i.market], p.q)));
    if (!p.state) rows.sort((a, b) => (a.r[a.i.date] < b.r[b.i.date] ? 1 : a.r[a.i.date] > b.r[b.i.date] ? -1
      : cmpStr(a.r[a.i.commodity], b.r[b.i.commodity]) || cmpStr(a.r[a.i.market], b.r[b.i.market]) || cmpStr(a.r[a.i.entity_id], b.r[b.i.entity_id])));
    const out = page(rows);
    out.items = out.items.map(latestItem);
    return out;
  }
  let m = path.match(/^\/series\/(.+)$/);
  if (m) {
    const id = decodeURIComponent(m[1]);
    const s = (await snapFile(`series/${shard(id)}.json`))[id];
    if (!s) throw new ApiError('not_found');
    return { ...s, points: s.points.map(([date, min, max, modal]) => ({ date, min, max, modal })) };
  }
  m = path.match(/^\/forecast\/(.+)$/);
  if (m) {
    const id = decodeURIComponent(m[1]);
    const f = (await snapFile(`forecast/${shard(id)}.json`))[id];
    if (!f) throw new ApiError('not_found');
    const meta = await snapFile('meta.json');
    return { ...f, model_version: meta.model_version, source: meta.source };
  }
  m = path.match(/^\/compare\/(.+)$/);
  if (m) {
    // same as the API's compare_items(): same commodity and variety in the state (or district),
    // highest modal price first, then reports within compareMaxStaleDays of the reference first
    const id = decodeURIComponent(m[1]);
    const { row } = await findRow(id);
    if (!row) throw new ApiError('not_found');
    const ref = latestItem(row), { i } = row, scope = p.scope === 'district' ? 'district' : 'state';
    const f7 = (x) => x.r[x.i.f7];
    const cand = (await stateRows(ref.entity.state)).filter((x) => x.r[i.commodity] === ref.entity.commodity
      && x.r[i.variety] === ref.entity.variety && (scope === 'state' || x.r[i.district] === ref.entity.district)
      && x.r[i.entity_id] !== id);
    cand.sort((a, b) => b.r[i.modal_price] - a.r[i.modal_price] || (a.r[i.entity_id] < b.r[i.entity_id] ? -1 : 1));
    const items = cand.slice(0, +p.limit || 20).map((x) => {
      const it = latestItem(x);
      return { entity: it.entity, modal_price: it.modal_price, date: it.date,
        diff_pct: r2((it.modal_price / ref.modal_price - 1) * 100), freshness: it.freshness, forecast_h7_median: f7(x) ?? null,
        comparable: Math.abs(dayNo(it.date) - dayNo(ref.date)) <= RULES.compareMaxStaleDays };
    });
    items.sort((a, b) => (a.comparable === b.comparable ? (b.modal_price || 0) - (a.modal_price || 0) : a.comparable ? -1 : 1));
    return { reference: { entity: ref.entity, modal_price: ref.modal_price, date: ref.date }, items };
  }
  if (path === '/alerts') {
    const states = p.state ? [p.state] : Object.keys(snap.states);
    let items = [];
    for (const st of states) if (stateKey(st)) items = items.concat((await snapFile(`alerts/${stateKey(st)}.json`)).items);
    return { items: items.filter((it) => !p.commodity || it.entity.commodity === p.commodity) };
  }
  if (path === '/trends') {
    if (!stateKey(p.state)) return { state: p.state, as_of: snap.data_as_of, rising: [], falling: [] };
    const t = await snapFile(`trends/${stateKey(p.state)}.json`), n = +p.limit || 10;
    return { ...t, rising: t.rising.slice(0, n), falling: t.falling.slice(0, n) };
  }
  throw new ApiError('not_found');
}
