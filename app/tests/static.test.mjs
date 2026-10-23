// Static checks: module graph, size budget, precache list, manifest, i18n keys used in code.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const JS_BUDGET = 80 * 1024;

function walk(dir, out = []) {
  for (const f of readdirSync(dir)) {
    const p = path.join(dir, f);
    if (['tests', 'tools', 'demo', 'node_modules'].includes(f)) continue;
    if (statSync(p).isDirectory()) walk(p, out); else out.push(p);
  }
  return out;
}
const shipped = walk(APP);
const jsFiles = shipped.filter((f) => f.endsWith('.js'));

test('every imported / dynamically imported module exists', () => {
  const html = readFileSync(path.join(APP, 'index.html'), 'utf8');
  const entry = [...html.matchAll(/<script[^>]+src="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(entry.length, 'index.html loads a module');
  for (const e of entry) assert.ok(existsSync(path.join(APP, e)), e);
  for (const f of jsFiles) {
    const src = readFileSync(f, 'utf8');
    const refs = [...src.matchAll(/(?:import\s[^'"]*?from\s*|import\s*\(\s*|^import\s*)['"](\.{1,2}\/[^'"]+)['"]/gm)].map((m) => m[1]);
    for (const r of refs) assert.ok(existsSync(path.resolve(path.dirname(f), r)), `${path.relative(APP, f)} -> ${r}`);
  }
});

test(`total shipped JS stays under ${JS_BUDGET / 1024} KB uncompressed`, () => {
  const total = jsFiles.reduce((s, f) => s + statSync(f).size, 0);
  console.log(`# shipped JS: ${jsFiles.length} files, ${(total / 1024).toFixed(1)} KB`);
  assert.ok(total < JS_BUDGET, `JS is ${total} bytes`);
});

test('first screen does not statically import the chart', () => {
  const graph = new Set();
  const visit = (f) => {
    if (graph.has(f)) return; graph.add(f);
    const src = readFileSync(f, 'utf8');
    for (const m of src.matchAll(/^import\s[^'"]*?['"](\.{1,2}\/[^'"]+)['"]/gm)) visit(path.resolve(path.dirname(f), m[1]));
  };
  visit(path.join(APP, 'js', 'app.js'));
  assert.ok(![...graph].some((f) => f.endsWith('chart.js')), 'chart.js must be lazy');
  assert.ok(![...graph].some((f) => f.includes(`${path.sep}routes${path.sep}`)), 'routes must be lazy');
});

test('service worker precaches files that exist, including every shipped JS/i18n/icon', () => {
  const sw = readFileSync(path.join(APP, 'sw.js'), 'utf8');
  const block = (name) => [...sw.slice(sw.indexOf(`const ${name} = [`), sw.indexOf('];', sw.indexOf(`const ${name} = [`))).matchAll(/'([^']+)'/g)].map((m) => m[1]);
  const all = [...block('PRECACHE'), ...block('ICONS').map((n) => `icons/commodities/${n}.svg`)];
  for (const f of all) if (f !== './') assert.ok(existsSync(path.join(APP, f)), `precache missing file ${f}`);
  for (const f of shipped.map((x) => path.relative(APP, x).split(path.sep).join('/'))) {
    if (/\.(js|json|svg|png|css|html|webmanifest)$/.test(f) && f !== 'sw.js' && !f.endsWith('.md')) assert.ok(all.includes(f), `${f} not precached`);
  }
  assert.match(sw, /method !== 'GET'/, 'non-GET requests are not cached');
  assert.match(sw, /X-From-Cache/);
});

test('manifest is installable', () => {
  const m = JSON.parse(readFileSync(path.join(APP, 'manifest.webmanifest'), 'utf8'));
  for (const k of ['name', 'short_name', 'start_url', 'display', 'theme_color', 'lang']) assert.ok(m[k], k);
  assert.equal(m.start_url, './'); assert.equal(m.display, 'standalone');
  for (const s of ['192x192', '512x512']) {
    const ic = m.icons.find((i) => i.sizes === s && i.type === 'image/png');
    assert.ok(ic, s);
    const buf = readFileSync(path.join(APP, ic.src));
    assert.equal(buf.toString('hex', 0, 8), '89504e470d0a1a0a', `${s} is a PNG`);
    assert.equal(buf.readUInt32BE(16), +s.split('x')[0], `${s} width`);
  }
});

test('every literal i18n key used in code exists in en.json', () => {
  const en = JSON.parse(readFileSync(path.join(APP, 'i18n', 'en.json'), 'utf8'));
  const html = readFileSync(path.join(APP, 'index.html'), 'utf8');
  const used = new Set();
  for (const f of jsFiles) for (const m of readFileSync(f, 'utf8').matchAll(/\bt\(\s*'([a-z0-9_.]+)'/gi)) used.add(m[1]);
  for (const f of jsFiles) for (const m of readFileSync(f, 'utf8').matchAll(/(?:empty|field)\([^)]*?'([a-z]+\.[a-z0-9_.]+)'/gi)) used.add(m[1]);
  for (const m of html.matchAll(/data-i18n(?:-aria|-ph)?="([^"]+)"/g)) used.add(m[1]);
  const missing = [...used].filter((k) => !(k in en) && !k.endsWith('.'));
  assert.deepEqual(missing, []);
  assert.ok(used.size > 100, `only ${used.size} keys found — regex broken?`);
});

test('no external network origins or CDNs in shipped code', () => {
  for (const f of shipped.filter((x) => /\.(js|html|css)$/.test(x))) {
    const src = readFileSync(f, 'utf8');
    const urls = [...src.matchAll(/https?:\/\/[^\s'"`)]+/g)].map((m) => m[0]).filter((u) => !u.startsWith('http://www.w3.org/'));
    assert.deepEqual(urls, [], path.relative(APP, f));
  }
});

test('no innerHTML with data (XSS guard)', () => {
  for (const f of jsFiles) assert.ok(!/\.innerHTML\s*=/.test(readFileSync(f, 'utf8')), path.relative(APP, f));
});

test('service-worker VERSION is the current content hash of the app shell (run app/tools/stamp-sw.mjs)', async () => {
  const { shellHash, currentVersion } = await import('../tools/stamp-sw.mjs');
  assert.equal(currentVersion(), shellHash());
});
