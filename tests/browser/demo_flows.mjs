// Demo-mode flow checks in headless Chrome (what a visitor of the static GitHub Pages site can reach).
//
//   node tests/browser/demo_flows.mjs http://localhost:8091/   [--chrome "/path/to/chrome"]
//
// Through the app's own API client (app/js/api.js, demo mode), for every state in the snapshot:
//   every market listed returns prices; every price row's forecast, series and comparison load.
// Through the UI at 360x740: a sample of commodity pages and every state's market list render
// without the "Could not load this" error card or an empty "No prices found" market.
// Exit 1 on any FAIL.
import { spawn } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

const BASE = process.argv[2] || 'http://localhost:8000/';
const CHROME = (process.argv.includes('--chrome') && process.argv[process.argv.indexOf('--chrome') + 1])
  || process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
const check = (name, ok, detail) => { results.push({ name, status: ok ? 'PASS' : 'FAIL', detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`, detail ?? ''); };

const profile = mkdtempSync(path.join(tmpdir(), 'agri-pwa-'));
const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--disable-extensions', 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
const wsUrl = await new Promise((resolve, reject) => {
  let buf = '';
  chrome.stderr.on('data', (d) => { buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/); if (m) resolve(m[1]); });
  setTimeout(() => reject(new Error('chrome did not start')), 20000);
});

// --- minimal CDP client -------------------------------------------------------------
const ws = new WebSocket(wsUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map(); const listeners = [];
ws.addEventListener('message', (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) { const { res, rej } = pending.get(msg.id); pending.delete(msg.id); msg.error ? rej(new Error(msg.error.message)) : res(msg.result); }
  else listeners.forEach((l) => l(msg));
});
const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
  const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId }));
});
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId: S } = await send('Target.attachToTarget', { targetId, flatten: true });
const cdp = (m, p) => send(m, p, S);
const evaljs = async (expr) => {
  const r = await cdp('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'eval error');
  return r.result.value;
};
const waitFor = async (expr, ms = 20000) => { const t = Date.now(); while (Date.now() - t < ms) { if (await evaljs(expr).catch(() => false)) return true; await sleep(200); } return false; };
const go = async (url) => { await cdp('Page.navigate', { url }); await sleep(300); await waitFor('document.readyState === "complete"'); };
// a hash change does not reload a single-page app; use this whenever a fresh load matters
const reload = async (ignoreCache = false) => { await cdp('Page.reload', { ignoreCache }); await sleep(300); await waitFor('document.readyState === "complete"'); };
let bytes = 0;
listeners.push((m) => { if (m.method === 'Network.loadingFinished' && m.sessionId === S) bytes += m.params.encodedDataLength || 0; });
await cdp('Page.enable'); await cdp('Runtime.enable'); await cdp('Network.enable');


const ERR = 'Could not load this';
await cdp('Emulation.setDeviceMetricsOverride', { width: 360, height: 740, deviceScaleFactor: 2, mobile: true });
const seedLoc = (loc) => `localStorage.setItem('agri.lang','"en"');localStorage.setItem('agri.onboarded','true');localStorage.setItem('agri.loc',${JSON.stringify(JSON.stringify(loc))})`;
await go(BASE); await evaljs(seedLoc({ state: 'Tamil Nadu' })); await reload();
await waitFor(`document.querySelector('main, #app') && document.body.innerText.length > 50`);

// 1. API client in demo mode, exhaustively
const api = await evaljs(`(async () => {
  const api = await import(new URL('js/api.js', location.href).href);
  const out = { states: 0, markets: 0, empty: [], entities: 0, failed: [] };
  const states = await api.states();
  for (const s of states) {
    out.states++;
    const ms = (await api.markets({ state: s.state, limit: 500 })).items;
    for (const m of ms) {
      out.markets++;
      const p = await api.latest({ state: s.state, market: m.market, limit: 200 });
      if (!p.items.length) { out.empty.push(m.market); continue; }
      for (const it of p.items) {
        out.entities++;
        const id = it.entity.entity_id;
        for (const [k, f] of [['forecast', api.forecast], ['series', api.series], ['compare', api.compare]]) {
          try { await f(id); } catch (e) { out.failed.push(k + ':' + id + ':' + (e.code || e.message)); }
        }
      }
    }
  }
  out.mode = api.status.mode;
  return out;
})()`);
check('demo mode is active', api.mode === 'demo', api.mode);
check('every listed market has prices', api.markets > 0 && api.empty.length === 0, { states: api.states, markets: api.markets, empty: api.empty.slice(0, 5) });
check('every price row opens forecast, series and comparison', api.entities > 0 && api.failed.length === 0, { entities: api.entities, failed: api.failed.slice(0, 5) });

// 2. UI: market lists per state, and a sample of commodity pages
const states = await evaljs(`fetch('demo/states.json').then(r => r.json()).then(s => s.map(x => x.state))`);
const bad = [];
for (const st of states) {
  await evaljs(seedLoc({ state: st })); await go(BASE + '#/markets'); await reload();
  await waitFor(`document.body.innerText.includes('markets found') || document.body.innerText.includes('${ERR}')`, 15000);
  await sleep(800);
  const txt = await evaljs('document.body.innerText');
  if (txt.includes(ERR) || txt.includes('No prices found')) bad.push(st);
}
check('markets screen shows prices for the chosen market in every state', bad.length === 0, bad);
// a location saved from an older snapshot (the faculty phone had Paderu saved) must not empty the home list
await evaljs(seedLoc({ state: 'Andhra Pradesh', district: 'No Such District', market: 'No Such Market' })); await go(BASE + '#/home'); await reload();
await waitFor(`document.querySelectorAll('ul.list li').length > 0 || document.body.innerText.includes('No prices')`, 15000);
const homeRows = await evaljs(`document.querySelectorAll('ul.list li').length`);
const savedLoc = await evaljs(`localStorage.getItem('agri.loc')`);
check('a saved market missing from the snapshot is forgotten and home still lists prices', homeRows > 0 && !savedLoc.includes('No Such'), { homeRows, savedLoc });
const sample = await evaljs(`fetch('demo/index.json').then(r => r.json()).then(i => i.entities.forecast.filter((_, k) => k % 97 === 0))`);
const badC = [];
for (const id of sample) {
  await go(BASE + '#/commodity/' + encodeURIComponent(id)); await reload();
  const ok = await waitFor(`document.body.innerText.includes('${ERR}') || !!document.querySelector('svg, canvas, table')`, 15000);
  await sleep(500);
  if (!ok || (await evaljs(`document.body.innerText.includes('${ERR}')`))) badC.push(id);
}
check('sampled commodity pages render without an error card', badC.length === 0, { sampled: sample.length, failed: badC });

ws.close(); chrome.kill(); await sleep(500); try { rmSync(profile, { recursive: true, force: true }); } catch {}
const failed = results.filter((r) => r.status === 'FAIL').length;
console.log(`\n${results.length - failed}/${results.length} demo-flow checks passed`);
process.exit(failed ? 1 : 0);
