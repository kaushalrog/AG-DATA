// The demo snapshot must follow docs/API.md exactly, because the app reads it with the same code as the API.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const DEMO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'demo');
const rd = (f) => JSON.parse(readFileSync(path.join(DEMO, f), 'utf8'));
const idx = rd('index.json');
const ISO = /^\d{4}-\d{2}-\d{2}$/;
const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

function entity(e, where) {
  for (const k of ['entity_id', 'state', 'district', 'market', 'commodity', 'variety', 'grade']) assert.equal(typeof e[k], 'string', `${where}: entity.${k}`);
  assert.match(e.entity_id, /^-?\d+$/, `${where}: entity_id must be a numeric string`);
}
function freshness(f, where) {
  assert.match(f.last_date, ISO, `${where}: freshness.last_date`);
  assert.ok(Number.isInteger(f.days_old) && f.days_old >= 0, `${where}: days_old`);
  assert.equal(typeof f.stale, 'boolean', `${where}: stale`);
  assert.equal(f.stale, f.days_old > 3, `${where}: stale must equal days_old > 3`);
}

test('index lists existing files only and the loader needs nothing else', () => {
  for (const f of Object.values(idx.files)) assert.ok(existsSync(path.join(DEMO, f)), f);
  for (const [kind, ids] of Object.entries(idx.entities)) for (const id of ids) assert.ok(existsSync(path.join(DEMO, `${kind}_${id}.json`)), `${kind}_${id}`);
  const listed = new Set(['index.json', ...Object.values(idx.files), ...Object.entries(idx.entities).flatMap(([k, ids]) => ids.map((i) => `${k}_${i}.json`))]);
  for (const f of readdirSync(DEMO).filter((x) => x.endsWith('.json'))) assert.ok(listed.has(f), `${f} is not referenced by index.json`);
});

test('demo provenance is explicit: synthetic placeholders are flagged, real exports are labelled archive (never live)', () => {
  const real = typeof idx._doc === 'string' && idx._doc.startsWith('REAL archived');
  const meta = rd(idx.files.meta);
  if (real) {
    assert.notEqual(meta.data_origin, 'live');
    for (const f of readdirSync(DEMO).filter((x) => x.endsWith('.json'))) {
      const d = rd(f);
      if (!Array.isArray(d)) assert.notEqual(d._demo_placeholder, true, f);
    }
  } else {
    for (const f of readdirSync(DEMO).filter((x) => x.endsWith('.json'))) {
      const d = rd(f);
      if (!Array.isArray(d)) assert.equal(d._demo_placeholder, true, f);
    }
  }
});

test('/meta', () => {
  const m = rd(idx.files.meta);
  assert.match(m.data_as_of, ISO);
  assert.ok(Number.isInteger(m.days_since_data));
  assert.ok(['archive', 'replay', 'live'].includes(m.data_origin));
  for (const k of ['name', 'licence', 'url']) assert.equal(typeof m.source[k], 'string');
  assert.deepEqual(m.horizons, ['next', 'h3', 'h7', 'h14']);
  assert.equal(m.price_unit, 'INR/quintal');
  assert.deepEqual(m.languages, ['en', 'ta', 'te', 'ml', 'hi', 'kn']);
  assert.ok(!Number.isNaN(Date.parse(m.generated_at)));
});

test('/states', () => {
  const s = rd(idx.files.states);
  assert.ok(Array.isArray(s) && s.length);
  for (const x of s) { assert.equal(typeof x.state, 'string'); assert.ok(Number.isInteger(x.markets)); assert.match(x.last_date, ISO); }
});

test('/prices/latest', () => {
  const p = rd(idx.files.prices_latest);
  for (const k of ['total', 'limit', 'offset']) assert.ok(Number.isInteger(p[k]), k);
  for (const it of p.items) {
    entity(it.entity, 'latest'); freshness(it.freshness, 'latest');
    assert.match(it.date, ISO);
    for (const k of ['min_price', 'max_price', 'modal_price']) assert.ok(isNum(it[k]), k);
    assert.ok(it.min_price <= it.modal_price && it.modal_price <= it.max_price, 'min <= modal <= max');
    assert.equal(it.unit, 'INR/quintal');
    assert.equal(typeof it.forecast_supported, 'boolean');
    assert.equal(it.date, it.freshness.last_date);
  }
});

test('/series/{id}', () => {
  for (const id of idx.entities.series) {
    const s = rd(`series_${id}.json`);
    entity(s.entity, id); freshness(s.freshness, id);
    assert.equal(s.entity.entity_id, id);
    assert.equal(s.unit, 'INR/quintal');
    assert.ok(s.points.length >= 1);  // real post-migration series can be short
    for (const p of s.points) { assert.match(p.date, ISO); for (const k of ['min', 'max', 'modal']) assert.ok(isNum(p[k]), `${id} ${k}`); }
    const dates = s.points.map((p) => p.date);
    assert.deepEqual(dates, [...dates].sort(), 'points sorted by date');
    // summary values are null when the history needed to compute them is missing (real data)
    assert.ok(s.summary.trend === null || ['rising', 'falling', 'stable'].includes(s.summary.trend));
    assert.ok(s.summary.volatility_level === null || ['low', 'medium', 'high'].includes(s.summary.volatility_level));
    assert.ok(isNum(s.summary.n_obs_30d), 'n_obs_30d');
    for (const k of ['change_7d_pct', 'change_30d_pct', 'volatility_30d_pct']) assert.ok(s.summary[k] === null || isNum(s.summary[k]), k);
  }
});

test('/forecast/{id}', () => {
  const REASONS = ['lower_bound_above_cost', 'upper_bound_below_today', 'better_market_nearby', 'uncertain', 'insufficient_history', 'stale_data', 'perishable_cost_applied', 'forecast_expired'];
  const WARN = ['data_stale', 'sparse_history', 'high_volatility', 'wide_interval', 'archive_data', 'forecast_origin_differs'];
  for (const id of idx.entities.forecast) {
    const f = rd(`forecast_${id}.json`);
    entity(f.entity, id); freshness(f.freshness, id);
    assert.equal(typeof f.supported, 'boolean');
    assert.ok(['SELL', 'HOLD', 'WATCH', 'COMPARE'].includes(f.decision.signal));
    assert.equal(f.decision.kind, 'market_outlook');
    assert.ok(f.decision.reason_codes.every((r) => REASONS.includes(r)), id);
    assert.ok(f.warnings.every((w) => WARN.includes(w)), id);
    assert.equal(typeof f.decision.costs.perishable, 'boolean');
    assert.ok(isNum(f.decision.costs.holding_cost_pct));
    if (!f.supported) {
      assert.ok(['insufficient_history', 'not_in_forecast_commodities', 'stale_beyond_limit'].includes(f.unsupported_reason));
      assert.deepEqual(f.horizons, []);
      assert.equal(f.decision.signal, 'WATCH');
      continue;
    }
    assert.equal(f.unsupported_reason, null);
    assert.match(f.origin.date, ISO); assert.ok(isNum(f.origin.modal_price));
    for (const h of f.horizons) {
      assert.ok(['next', 'h3', 'h7', 'h14'].includes(h.horizon));
      assert.ok(Number.isInteger(h.days));
      assert.ok(h.lo90 <= h.lo80 && h.lo80 <= h.median && h.median <= h.hi80 && h.hi80 <= h.hi90, `${id} ${h.horizon} interval order`);
      for (const k of ['change_pct', 'test_mae_pct_of_price', 'test_rel_mae_vs_persistence', 'interval_coverage80_test']) assert.ok(isNum(h[k]), k);
      assert.ok(h.interval_coverage80_test > 0 && h.interval_coverage80_test <= 1);
      assert.equal(h.target_window.length, 2);
    }
    assert.ok(f.horizons.some((h) => h.horizon === f.decision.horizon), 'decision horizon present');
  }
});

test('/compare/{id}', () => {
  for (const id of idx.entities.compare) {
    const c = rd(`compare_${id}.json`);
    entity(c.reference.entity, id);
    assert.equal(c.reference.entity.entity_id, id);
    assert.ok(isNum(c.reference.modal_price)); assert.match(c.reference.date, ISO);
    for (const it of c.items) {
      entity(it.entity, id); freshness(it.freshness, id);
      assert.ok(isNum(it.modal_price)); assert.ok(isNum(it.diff_pct));
      assert.equal(typeof it.comparable, 'boolean');
      assert.equal(it.entity.commodity, c.reference.entity.commodity);
      assert.equal(it.entity.variety, c.reference.entity.variety);
      const gap = Math.abs(Date.parse(c.reference.date) - Date.parse(it.date)) / 864e5;
      assert.equal(it.comparable, gap <= 3, `${id}: comparable = reported within 3 days of the reference`);
    }
  }
});

test('/alerts and /trends', () => {
  const a = rd(idx.files.alerts);
  for (const it of a.items) {
    entity(it.entity, 'alert');
    assert.ok(['price_spike', 'price_drop', 'suspect_data_error'].includes(it.type));
    for (const k of ['modal_price', 'log_dev', 'robust_z', 'ref_mean_price']) assert.ok(isNum(it[k]), k);
  }
  const t = rd(idx.files.trends);
  assert.equal(typeof t.state, 'string'); assert.match(t.as_of, ISO);
  for (const r of [...t.rising, ...t.falling]) { assert.equal(typeof r.commodity, 'string'); assert.ok(isNum(r.median_change_7d_pct)); assert.ok(Number.isInteger(r.markets)); }
});
