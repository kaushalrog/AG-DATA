// Parity: the app's snapshot mode (app/js/api.js reading build/snapshot) must answer like the real API.
//
//   node tests/snapshot_parity.mjs <snapshot_dir> <api_base> [--sample 300]
//   node tests/snapshot_parity.mjs build/snapshot http://127.0.0.1:7860/api/v1
//
// api.js runs in Node with fetch shimmed: /api/v1/* is unreachable (as on a static host) and
// snapshot/* is read from <snapshot_dir>. Every state's markets, first price page, alerts and trends,
// plus a random sample of series, forecasts and comparisons, are compared field by field with the API
// (numbers within 0.011; comparison order checked by (comparable, price), since equal prices may tie).
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';

const [dir, apiBase] = process.argv.slice(2);
const N = process.argv.includes('--sample') ? +process.argv[process.argv.indexOf('--sample') + 1] : 300;
if (!dir || !apiBase) { console.error('usage: snapshot_parity.mjs <snapshot_dir> <api_base>'); process.exit(2); }
const realFetch = globalThis.fetch;
globalThis.fetch = async (url) => {
  const u = String(url);
  if (u.startsWith('/api/') || u.includes('/api/v1/')) throw new TypeError('unreachable (static host)');
  const f = path.join(dir, u.replace(/^snapshot\//, ''));
  if (!existsSync(f)) return new Response('not found', { status: 404, headers: { 'content-type': 'text/plain' } });
  return new Response(readFileSync(f), { headers: { 'content-type': 'application/json' } });
};
const api = await import('../app/js/api.js');
const real = async (p) => (await realFetch(apiBase + p)).json();

let checks = 0; const fails = [];
function same(a, b, where) {
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) <= 0.011 || fails.push(`${where}: ${a} != ${b}`);
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return a === b || fails.push(`${where}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`);
  if (Array.isArray(a) !== Array.isArray(b)) return fails.push(`${where}: array mismatch`);
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  for (const k of keys) same(a[k], b[k], `${where}.${k}`);
  return true;
}
const check = (a, b, where) => { checks++; same(a, b, where); };
const q = (o) => '?' + new URLSearchParams(o).toString();

// meta (days_since_data is computed by both from today's date)
const m = await api.meta(), mr = await real('/meta');
delete mr.refresh; const m2 = { ...m }; delete m2.refresh;
// the server counts days in its own time zone (a container runs on UTC), the browser in the viewer's
if (Math.abs(m2.days_since_data - mr.days_since_data) <= 1) m2.days_since_data = mr.days_since_data;
check(m2, mr, 'meta');
if (api.status.mode !== 'snapshot') fails.push(`mode is ${api.status.mode}, expected snapshot`);
check(await api.states(), await real('/states'), 'states');

// The API orders prices by (date desc, commodity, market); rows tied on that key (several varieties or
// grades of one market) have no defined order even on the server, so tie groups are compared as sets
// and the last, possibly cut, group of a page is ignored.
function latestCheck(a, b, where) {
  check(a.total, b.total, `${where} total`);
  const k = (it) => `${it.date}|${it.entity.commodity}|${it.entity.market}`;
  const groups = (items) => { const g = new Map(); for (const it of items) { if (!g.has(k(it))) g.set(k(it), []); g.get(k(it)).push(it); } return g; };
  const ga = groups(a.items), gb = groups(b.items);
  check([...ga.keys()].slice(0, -1), [...gb.keys()].slice(0, -1), `${where} order`);
  for (const key of [...gb.keys()].slice(0, -1)) {
    const byId = (xs) => [...(xs || [])].sort((x, y) => (x.entity.entity_id < y.entity.entity_id ? -1 : 1));
    check(byId(ga.get(key)), byId(gb.get(key)), `${where} ${key}`);
  }
}
// Lists the API sorts with possible ties (alerts by date and |deviation|, trends by median change,
// comparisons by price): compare the sort keys, and items as sets within each tie group. When the API cut
// the list (limit), the last tie group may legitimately contain different members, so it is skipped.
function tiedCheck(a, b, keyOf, where, cut) {
  const sk = (xs) => xs.map((x) => JSON.stringify(keyOf(x)));
  let ka = sk(a), kb = sk(b);
  if (cut && kb.length) { const last = kb[kb.length - 1]; ka = ka.filter((k) => k !== last); kb = kb.filter((k) => k !== last); }
  check(ka, kb, `${where} order`);
  const id = (x) => x.entity ? x.entity.entity_id : x.commodity;
  const byKey = (xs) => { const g = new Map(); for (const x of xs) { const k = JSON.stringify(keyOf(x)); if (!g.has(k)) g.set(k, []); g.get(k).push(x); } return g; };
  const ga = byKey(a), gb = byKey(b);
  for (const k of new Set(kb)) check([...ga.get(k) || []].sort((x, y) => (id(x) < id(y) ? -1 : 1)), [...gb.get(k)].sort((x, y) => (id(x) < id(y) ? -1 : 1)), `${where} ${k}`);
}
const states = (await real('/states')).map((s) => s.state);
for (const st of states) {
  check(await api.markets({ state: st, limit: 500 }), await real('/markets' + q({ state: st, limit: 500 })), `markets ${st}`);
  latestCheck(await api.latest({ state: st, limit: 200 }), await real('/prices/latest' + q({ state: st, limit: 200 })), `latest ${st}`);
  const mk = (await real('/markets' + q({ state: st, limit: 1 }))).items[0];
  if (mk) latestCheck(await api.latest({ state: st, district: mk.district, market: mk.market, limit: 200 }),
    await real('/prices/latest' + q({ state: st, district: mk.district, market: mk.market, limit: 200 })), `latest ${st}/${mk.market}`);
  const al = (await real('/alerts' + q({ state: st, days: 14, limit: 200 }))).items;
  tiedCheck((await api.alerts({ state: st, days: 14 })).items, al, (x) => [x.date, Math.abs(x.log_dev)], `alerts ${st}`, al.length === 200);
  const ta = await api.trends({ state: st, limit: 10 }), tb = await real('/trends' + q({ state: st, limit: 10 }));
  for (const side of ['rising', 'falling']) tiedCheck(ta[side], tb[side], (x) => [x.median_change_7d_pct], `trends ${st} ${side}`, tb[side].length === 10);
}
const ptr = JSON.parse(readFileSync(path.join(dir, 'current.json'), 'utf8'));
const all = [];
for (const k of Object.values(ptr.states)) for (const r of JSON.parse(readFileSync(path.join(dir, ptr.version, 'state', `${k}.json`), 'utf8')).rows) all.push(r[0]);
let seed = 20261024; const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31);
const sample = Array.from({ length: N }, () => all[Math.floor(rnd() * all.length)]);
for (const id of sample) {
  check(await api.series(id, 180), await real(`/series/${id}?days=180`), `series ${id}`);
  // the stored decision depends on the server's clock (expiry); the app recomputes it in the browser and
  // only reads decision.costs, so the clock-dependent fields are not compared
  const fa = await api.forecast(id), fb = await real(`/forecast/${id}`);
  for (const f of [fa, fb]) { f.decision = { costs: f.decision.costs, kind: f.decision.kind }; }
  check(fa, fb, `forecast ${id}`);
  for (const scope of ['state', 'district']) {
    const a = await api.compare(id, scope), b = await real(`/compare/${id}?scope=${scope}&limit=20`);
    check(a.reference, b.reference, `compare ${id} reference`);
    // the API takes the 20 highest prices, then puts comparable reports first; a price tie at the
    // 20th place may keep a different member, so the cut-off price group is excluded on both sides
    const cut = b.items.length === 20 ? Math.min(...b.items.map((x) => x.modal_price)) : null;
    const keep = (xs) => xs.filter((x) => x.modal_price !== cut);
    tiedCheck(keep(a.items), keep(b.items), (x) => [x.comparable ? 0 : 1, -x.modal_price], `compare ${id} ${scope}`, false);
  }
}
console.log(`${checks} comparisons, ${fails.length} differences (sample ${N} series, ${states.length} states)`);
for (const f of fails.slice(0, +(process.env.SHOW || 15))) console.log('  ' + f);
process.exit(fails.length ? 1 : 0);
