import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const LANGS = ['en', 'ta', 'te', 'ml', 'hi', 'kn'];
const load = (l) => JSON.parse(readFileSync(path.join(APP, 'i18n', `${l}.json`), 'utf8'));
const dicts = Object.fromEntries(LANGS.map((l) => [l, load(l)]));
const keysOf = (d) => Object.keys(d).filter((k) => !k.startsWith('_')).sort();
const tokens = (s) => (s.match(/\{\w+\}/g) || []).sort();

// Codes from docs/API.md (kept here so the test works even without the docs folder).
const CODES = {
  signal: ['SELL', 'HOLD', 'WATCH', 'COMPARE'],
  reason: ['lower_bound_above_cost', 'upper_bound_below_today', 'better_market_nearby', 'uncertain',
    'insufficient_history', 'stale_data', 'perishable_cost_applied'],
  warning: ['data_stale', 'sparse_history', 'high_volatility', 'wide_interval', 'archive_data'],
  unsupported: ['insufficient_history', 'not_in_forecast_commodities', 'stale_beyond_limit'],
  alert: ['price_spike', 'price_drop', 'suspect_data_error'],
  trend: ['rising', 'falling', 'stable'],
  vol: ['low', 'medium', 'high'],
  origin: ['archive', 'replay', 'live'],
  error: ['not_found', 'bad_request', 'rate_limited', 'unavailable', 'network'],
  horizon: ['next', 'h3', 'h7', 'h14'],
};

test('all six languages have identical key sets', () => {
  const en = keysOf(dicts.en);
  assert.ok(en.length > 200, 'en.json unexpectedly small');
  for (const l of LANGS) assert.deepEqual(keysOf(dicts[l]), en, `key mismatch in ${l}.json`);
});

test('non-English files are marked provisional-ai', () => {
  for (const l of LANGS.filter((x) => x !== 'en')) assert.equal(dicts[l]._status, 'provisional-ai', l);
});

test('no empty or whitespace-only strings', () => {
  for (const l of LANGS) for (const k of keysOf(dicts[l])) {
    assert.equal(typeof dicts[l][k], 'string', `${l}:${k} not a string`);
    assert.ok(dicts[l][k].trim().length > 0, `${l}:${k} is empty`);
  }
});

test('placeholder tokens are identical across languages', () => {
  for (const k of keysOf(dicts.en)) for (const l of LANGS) {
    assert.deepEqual(tokens(dicts[l][k]), tokens(dicts.en[k]), `${l}:${k} placeholders differ`);
  }
});

test('translations are actually in the native script (not copied English)', () => {
  const script = { ta: /[஀-௿]/, te: /[ఀ-౿]/, ml: /[ഀ-ൿ]/, hi: /[ऀ-ॿ]/, kn: /[ಀ-೿]/ };
  for (const [l, re] of Object.entries(script)) {
    const ks = keysOf(dicts[l]).filter((k) => !k.startsWith('lang.') && k !== 'common.place' && k !== 'commodity.volatility_value');
    const latin = ks.filter((k) => !re.test(dicts[l][k]));
    assert.deepEqual(latin, [], `${l}: strings without native script`);
  }
});

test('every API code (signal, reason, warning, unsupported, alert, trend, volatility, origin, error, horizon) has a key', () => {
  for (const [prefix, codes] of Object.entries(CODES)) for (const c of codes) {
    assert.ok(dicts.en[`${prefix}.${c}`], `missing ${prefix}.${c}`);
    if (prefix === 'signal') assert.ok(dicts.en[`signal_text.${c}`], `missing signal_text.${c}`);
  }
});

test('codes listed in docs/API.md are covered (when the doc is present)', (t) => {
  const doc = path.join(APP, '..', 'docs', 'API.md');
  if (!existsSync(doc)) { t.skip('docs/API.md not found'); return; }
  const md = readFileSync(doc, 'utf8');
  const table = md.slice(md.indexOf('| order | signal | rule | reason codes |'), md.indexOf('### `GET /compare'));
  const reasons = [...table.matchAll(/^\|[^|\n]*\|[^|\n]*\|[^|\n]*\|([^|\n]*)\|$/gm)].flatMap((m) => [...m[1].matchAll(/`(\w+)`/g)].map((x) => x[1]));
  assert.ok(reasons.length >= 6, 'could not parse reason codes');
  for (const r of reasons) assert.ok(dicts.en[`reason.${r}`], `reason.${r} missing`);
  const w = md.match(/"warnings":\s*\[([^\]]+)\]/);
  for (const c of [...w[1].matchAll(/"(\w+)"/g)].map((x) => x[1])) assert.ok(dicts.en[`warning.${c}`], `warning.${c} missing`);
  const ex = md.match(/"reason_codes":\s*\[([^\]]+)\]/);
  for (const c of [...ex[1].matchAll(/"(\w+)"/g)].map((x) => x[1])) assert.ok(dicts.en[`reason.${c}`], `reason.${c} missing`);
  const u = md.match(/`unsupported_reason` in ([^.]+)\./);
  for (const c of [...u[1].matchAll(/`(\w+)`/g)].map((x) => x[1])) assert.ok(dicts.en[`unsupported.${c}`], `unsupported.${c} missing`);
  const a = md.match(/"type":\s*"([^"]+)"/);
  for (const c of a[1].split('|')) assert.ok(dicts.en[`alert.${c}`], `alert.${c} missing`);
  for (const c of md.match(/"signal":\s*"([^"]+)"/)[1].split('|')) assert.ok(dicts.en[`signal.${c}`], `signal.${c} missing`);
});

test('guide topics exist with title + 3 paragraphs in every language', () => {
  const topics = ['prices', 'trends', 'forecasts', 'wrong', 'ranges', 'compare', 'transport', 'signals', 'guarantee', 'missing'];
  for (const l of LANGS) for (const tp of topics) for (const p of ['title', 'p1', 'p2', 'p3']) {
    assert.ok(dicts[l][`guide.${tp}.${p}`], `${l}: guide.${tp}.${p}`);
  }
});

test('commodity dictionary covers the 36 panel commodities in all five Indian languages', () => {
  const c = JSON.parse(readFileSync(path.join(APP, 'i18n', 'commodities.json'), 'utf8')).items;
  const names = ['Potato', 'Onion', 'Tomato', 'Brinjal', 'Wheat', 'Green Chilli', 'Cauliflower', 'Paddy (Dhan)(Common)',
    'Bhindi (Ladies Finger)', 'Cucumbar (Kheera)', 'Cabbage', 'Banana', 'Bottle gourd', 'Bengal Gram (Gram)(Whole)', 'Pumpkin',
    'Bitter gourd', 'Mustard', 'Apple', 'Rice', 'Ginger (Green)', 'Carrot', 'Maize', 'Garlic', 'Soyabean', 'Lemon', 'Pomegranate',
    'Arhar (Tur/Red Gram)(Whole)', 'Capsicum', 'Bajra (Pearl Millet/Cumbu)', 'Green Gram (Moong)(Whole)', 'Black Gram (Urd Beans)(Whole)',
    'Cotton', 'Lentil (Masur)(Whole)', 'Coriander (Leaves)', 'Jowar (Sorghum)', 'Groundnut'];
  assert.equal(names.length, 36);
  assert.deepEqual(Object.keys(c).sort(), [...names].sort());
  for (const n of names) {
    for (const l of ['ta', 'te', 'ml', 'hi', 'kn']) assert.ok(c[n][l] && c[n][l].trim(), `${n} missing ${l}`);
    assert.ok(existsSync(path.join(APP, 'icons', 'commodities', `${c[n].icon}.svg`)), `icon ${c[n].icon} missing`);
  }
});
