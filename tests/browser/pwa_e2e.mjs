// Real-browser PWA checks with headless Google Chrome over the DevTools Protocol.
// No npm packages: Node >= 22 (global WebSocket/fetch) and a local Chrome binary.
//
//   node tests/browser/pwa_e2e.mjs http://localhost:8000/   [--chrome "/path/to/chrome"]
//
// Checks (results -> results/browser/pwa_report.json; exit 1 if any FAIL):
//   1. service worker registers and activates; app shell precached
//   2. Chrome's own installability check (Page.getInstallabilityErrors) passes; manifest parses
//   3. offline reload serves the cached shell and the app renders with an offline/cached status
//   4. low-end profile: 4x CPU throttle + slow 3G (400 ms RTT, 400 kbit/s) at 360x740 -
//      time to first rendered list, JS heap after load, bytes transferred
//   5. accessibility basics on home + commodity + guide: html lang, accessible names for
//      controls, alt text, WCAG AA contrast for text, touch targets >= 44 px
//   6. six languages at 320 px: no horizontal overflow, no raw i18n keys, lang attribute set
// It uses a throwaway profile directory and never touches the user's Chrome profile.
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

// skip onboarding: preferences the app stores locally
const seed = (lang) => `try{localStorage.setItem('agri.lang',${JSON.stringify(JSON.stringify(lang))});localStorage.setItem('agri.onboarded','true');localStorage.setItem('agri.loc',JSON.stringify({state:'Tamil Nadu'}))}catch(e){}`;

try {
  // ---------- 1-2: service worker + installability --------------------------------------
  await go(BASE);
  await evaljs(seed('en'));
  await go(BASE);
  const swOk = await waitFor(`navigator.serviceWorker && navigator.serviceWorker.controller !== null || (async()=>{const r=await navigator.serviceWorker.getRegistration();return !!(r&&r.active)})()`, 20000);
  const sw = await evaljs(`(async()=>{const r=await navigator.serviceWorker.getRegistration();return r?{scope:r.scope,active:r.active&&r.active.state,script:r.active&&r.active.scriptURL}:null})()`);
  check('service worker registered and active', swOk && sw && sw.active === 'activated', sw);
  const keys = await evaljs(`caches.keys()`);
  const shellCount = await evaljs(`(async()=>{const k=(await caches.keys()).find(x=>x.startsWith('agri-shell-'));if(!k)return 0;return (await (await caches.open(k)).keys()).length})()`);
  check('app shell precached', shellCount >= 20, { caches: keys, shell_entries: shellCount });
  const inst = await cdp('Page.getInstallabilityErrors');
  check('Chrome installability check passes', (inst.installabilityErrors || []).length === 0, inst.installabilityErrors);
  const man = await cdp('Page.getAppManifest');
  check('manifest parses without errors', man.url && (man.errors || []).length === 0, { url: man.url, errors: man.errors });

  // ---------- 3: offline ----------------------------------------------------------------
  await go(BASE + '#/home'); await sleep(1500); // warm the API cache through the service worker
  await cdp('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  await cdp('Page.reload', { ignoreCache: false });
  await sleep(500); await waitFor('document.readyState === "complete"');
  const offlineRendered = await waitFor(`document.querySelector('main') && document.querySelector('main').innerText.length > 50`, 15000);
  const offlineText = await evaljs(`document.body.innerText.slice(0, 400)`);
  check('offline reload renders the cached app', offlineRendered, offlineText.replace(/\s+/g, ' ').slice(0, 160));
  await cdp('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });

  // ---------- 4: low-end device profile ---------------------------------------------------
  await cdp('Emulation.setDeviceMetricsOverride', { width: 360, height: 740, deviceScaleFactor: 2, mobile: true });
  await cdp('Emulation.setCPUThrottlingRate', { rate: 4 });
  await cdp('Network.emulateNetworkConditions', { offline: false, latency: 400, downloadThroughput: 400 * 1024 / 8, uploadThroughput: 400 * 1024 / 8 });
  await cdp('Network.clearBrowserCache');
  await evaljs(`(async()=>{for(const k of await caches.keys())await caches.delete(k);const r=await navigator.serviceWorker.getRegistration();if(r)await r.unregister();})()`);
  await go(BASE + '#/home');
  bytes = 0;
  const t0 = Date.now();
  await reload(true);
  const rendered = await waitFor(`document.querySelectorAll('main a, main li, main .card').length > 3`, 60000);
  const tFirst = Date.now() - t0;
  await cdp('Performance.enable');
  const perf = Object.fromEntries((await cdp('Performance.getMetrics')).metrics.map((m) => [m.name, m.value]));
  const heapMB = perf.JSHeapUsedSize / 1048576;
  check('cold load on slow 3G + 4x CPU renders the home list', rendered && tFirst < 20000, { ms_to_first_list: tFirst, transferred_kb: Math.round(bytes / 1024) });
  check('JS heap after load is small (< 30 MB)', heapMB < 30, { js_heap_used_mb: +heapMB.toFixed(2), dom_nodes: perf.Nodes });
  await cdp('Emulation.setCPUThrottlingRate', { rate: 1 });
  await cdp('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });

  // ---------- 5: accessibility basics -------------------------------------------------------
  const a11yProbe = `(()=>{
    const lum=(c)=>{const m=c.match(/[\\d.]+/g);if(!m)return null;const [r,g,b]=m.slice(0,3).map(Number).map(v=>{v/=255;return v<=0.03928?v/12.92:((v+0.055)/1.055)**2.4});return 0.2126*r+0.7152*g+0.0722*b};
    const bg=(el)=>{while(el){const c=getComputedStyle(el).backgroundColor;const a=(c.match(/[\\d.]+/g)||[])[3];if(c&&c!=='transparent'&&!(a!==undefined&&+a===0))return c;el=el.parentElement}return 'rgb(255,255,255)'};
    const issues={unnamed:[],noalt:[],contrast:[],small:[]};
    document.querySelectorAll('button,a[href],input,select,textarea,[role=button]').forEach(el=>{
      const r=el.getBoundingClientRect(); if(!r.width||getComputedStyle(el).visibility==='hidden')return;
      // textContent, not innerText: controls inside a collapsed <details> have no rendered text
      if(el.closest('details:not([open])'))return;
      const name=(el.getAttribute('aria-label')||el.textContent||el.title||el.value||(el.labels&&el.labels[0]&&el.labels[0].textContent)||'').trim();
      if(!name)issues.unnamed.push(el.outerHTML.slice(0,80));
      const inLabel=el.closest('label'); const box=inLabel?inLabel.getBoundingClientRect():r;
      if(Math.min(box.width,box.height)<44 && !el.closest('p,li')) issues.small.push((name||el.tagName).slice(0,30)+' '+Math.round(box.width)+'x'+Math.round(box.height));
    });
    document.querySelectorAll('img').forEach(i=>{if(!i.hasAttribute('alt'))issues.noalt.push(i.src.slice(-40))});
    document.querySelectorAll('main *').forEach(el=>{
      if(!el.childNodes.length||![...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()))return;
      const cs=getComputedStyle(el); if(cs.visibility==='hidden'||cs.display==='none')return;
      const L1=lum(cs.color),L2=lum(bg(el)); if(L1==null||L2==null)return;
      const ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05); const big=parseFloat(cs.fontSize)>=24||(parseFloat(cs.fontSize)>=18.66&&+cs.fontWeight>=700);
      if(ratio<(big?3:4.5))issues.contrast.push(el.textContent.trim().slice(0,30)+' '+ratio.toFixed(2));
    });
    return {lang:document.documentElement.lang,issues};
  })()`;
  const ids = await (await fetch(new URL('demo/index.json', BASE))).json().then((j) => j.entities.forecast).catch(() => []);
  const screens = ['#/home', ids.length ? `#/commodity/${encodeURIComponent(ids[0])}` : '#/markets', '#/guide', '#/settings'];
  const a11y = {};
  for (const scr of screens) {
    await go(BASE + scr); await reload(); await sleep(2500);
    a11y[scr] = await evaljs(a11yProbe);
  }
  const all = (k) => Object.values(a11y).flatMap((x) => x.issues[k]);
  check('every interactive control has an accessible name', all('unnamed').length === 0, all('unnamed').slice(0, 5));
  check('every image has alt text', all('noalt').length === 0, all('noalt').slice(0, 5));
  check('text contrast meets WCAG AA', all('contrast').length === 0, all('contrast').slice(0, 8));
  check('touch targets >= 44 px (outside running text)', all('small').length === 0, all('small').slice(0, 8));
  check('html lang attribute set', Object.values(a11y).every((x) => x.lang), Object.fromEntries(Object.entries(a11y).map(([k, v]) => [k, v.lang])));

  // ---------- 6: six languages at 320 px ------------------------------------------------------
  await cdp('Emulation.setDeviceMetricsOverride', { width: 320, height: 640, deviceScaleFactor: 2, mobile: true });
  const langRes = {};
  for (const lang of ['en', 'ta', 'te', 'ml', 'hi', 'kn']) {
    await evaljs(seed(lang));
    langRes[lang] = {};
    for (const scr of screens) {
      await go(BASE + scr); await reload(); await sleep(1800);
      langRes[lang][scr] = await evaljs(`({lang:document.documentElement.lang,
        overflow:document.documentElement.scrollWidth - window.innerWidth,
        rawKeys:(document.body.innerText.match(/\\b[a-z_]+\\.[a-z_]+(\\.[a-z_]+)?\\b/g)||[]).filter(s=>/^(signal|reason|warning|decision|common|home|guide|nav|banner|origin|unsupported|commodity|alert|settings)\\./.test(s)).slice(0,5),
        bad:/\\b(undefined|NaN|null)\\b/.test(document.body.innerText)})`);
    }
  }
  const flat = Object.entries(langRes).flatMap(([l, o]) => Object.entries(o).map(([s, v]) => ({ l, s, ...v })));
  check('no horizontal overflow at 320 px in 6 languages', flat.every((x) => x.overflow <= 1), flat.filter((x) => x.overflow > 1).map((x) => `${x.l} ${x.s} +${x.overflow}px`));
  check('no raw i18n keys or undefined/NaN/null in 6 languages', flat.every((x) => !x.rawKeys.length && !x.bad), flat.filter((x) => x.rawKeys.length || x.bad).map((x) => `${x.l} ${x.s} ${x.rawKeys}`));
  check('document lang matches the chosen language', flat.every((x) => x.lang === x.l), flat.filter((x) => x.lang !== x.l).map((x) => `${x.l}->${x.lang}`));
} catch (e) {
  check('harness ran to completion', false, String(e));
} finally {
  const ver = await send('Browser.getVersion').catch(() => ({}));
  mkdirSync('results/browser', { recursive: true });
  writeFileSync('results/browser/pwa_report.json', JSON.stringify({ base: BASE, browser: ver.product, ran_at: new Date().toISOString(),
    profile: 'temporary, deleted after run', results }, null, 1));
  ws.close(); chrome.kill('SIGTERM'); await sleep(500);
  rmSync(profile, { recursive: true, force: true });
  const failed = results.filter((r) => r.status === 'FAIL').length;
  console.log(`\n${results.length - failed}/${results.length} checks passed (${ver.product || 'Chrome'})`);
  process.exit(failed ? 1 : 0);
}
