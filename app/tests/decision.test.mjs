import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { decide, holdingCostPct, bestMarket, defaultWeeklyPct, orderCompare, isExpired, RULES, PERISHABLE } from '../js/decision.js';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = { today: 2000, supported: true, stale: false, perishable: true, weeklyPct: 5, transportPerQ: 0, compareItems: [] };
const hz = (lo80, hi80, days = 7) => ({ days, lo80, hi80 });
const fresh = (d) => ({ last_date: '2026-04-20', days_old: d, stale: d > 3 });

test('holding cost = fixed + weekly * days/7 (h7 perishable = 6%, matches API example)', () => {
  assert.equal(holdingCostPct(7, 5), 6);
  assert.equal(holdingCostPct(14, 1), 3);
  assert.ok(Math.abs(holdingCostPct(3, 5) - (1 + 15 / 7)) < 1e-9);
});

test('HOLD when lo80 >= today * (1 + cost)', () => {
  const r = decide({ ...base, horizon: hz(2120, 2500) }); // need 2000*1.06 = 2120
  assert.equal(r.signal, 'HOLD');
  assert.deepEqual(r.reasons, ['lower_bound_above_cost', 'perishable_cost_applied']);
  assert.equal(r.needPrice, 2120);
});

test('just below the cost threshold is not HOLD', () => {
  assert.equal(decide({ ...base, horizon: hz(2119, 2500) }).signal, 'WATCH');
});

test('farmer-supplied lower holding cost can turn WATCH into HOLD', () => {
  const h = hz(2060, 2400);
  assert.equal(decide({ ...base, horizon: h }).signal, 'WATCH');
  assert.equal(decide({ ...base, horizon: h, weeklyPct: 1 }).signal, 'HOLD'); // need 2040
});

test('SELL when hi80 <= today (even the optimistic outcome is below today)', () => {
  const r = decide({ ...base, horizon: hz(1500, 2000) });
  assert.equal(r.signal, 'SELL');
  assert.deepEqual(r.reasons, ['upper_bound_below_today']);
  assert.equal(decide({ ...base, horizon: hz(1500, 2001) }).signal, 'WATCH');
});

test('COMPARE needs a fresh (<=3 days), comparable market >= 5% higher after transport', () => {
  const h = hz(1800, 2300);
  const item = (price, d, comparable = true) => ({ entity: { market: 'X' }, modal_price: price, freshness: fresh(d), comparable });
  assert.equal(decide({ ...base, horizon: h, compareItems: [item(2100, 1)] }).signal, 'COMPARE');
  assert.deepEqual(decide({ ...base, horizon: h, compareItems: [item(2100, 1)] }).reasons, ['better_market_nearby']);
  assert.equal(decide({ ...base, horizon: h, compareItems: [item(2099, 1)] }).signal, 'WATCH');
  assert.equal(decide({ ...base, horizon: h, compareItems: [item(2500, 4)] }).signal, 'WATCH', 'stale market ignored');
  assert.equal(decide({ ...base, horizon: h, compareItems: [item(2500, 1, false)] }).signal, 'WATCH', 'non-comparable ignored');
  assert.equal(decide({ ...base, horizon: h, compareItems: [item(2200, 1)], transportPerQ: 150 }).signal, 'WATCH', 'transport removes gain');
});

test('HOLD and SELL take precedence over COMPARE (table order in docs/API.md)', () => {
  const items = [{ entity: { market: 'X' }, modal_price: 3000, freshness: fresh(0), comparable: true }];
  assert.equal(decide({ ...base, horizon: hz(2200, 2600), compareItems: items }).signal, 'HOLD');
  assert.equal(decide({ ...base, horizon: hz(1500, 1900), compareItems: items }).signal, 'SELL');
});

test('WATCH with uncertain when the interval straddles today', () => {
  const r = decide({ ...base, perishable: false, weeklyPct: 1, horizon: hz(1900, 2100) });
  assert.equal(r.signal, 'WATCH');
  assert.deepEqual(r.reasons, ['uncertain']);
});

test('unsupported and stale forecasts are always WATCH', () => {
  assert.deepEqual(decide({ ...base, supported: false, unsupportedReason: 'insufficient_history', horizon: null }).reasons, ['insufficient_history']);
  assert.deepEqual(decide({ ...base, supported: false, unsupportedReason: 'stale_beyond_limit', horizon: null }).reasons, ['stale_data']);
  assert.deepEqual(decide({ ...base, supported: false, unsupportedReason: 'not_in_forecast_commodities', horizon: null }).reasons, []);
  const s = decide({ ...base, stale: true, horizon: hz(3000, 3500) });
  assert.equal(s.signal, 'WATCH');
  assert.deepEqual(s.reasons, ['stale_data']);
});

test('bestMarket picks the highest net gain among fresh comparable markets', () => {
  const items = [
    { entity: { market: 'A' }, modal_price: 2100, freshness: fresh(1), comparable: true },
    { entity: { market: 'B' }, modal_price: 2300, freshness: fresh(2), comparable: true },
    { entity: { market: 'C' }, modal_price: 2900, freshness: fresh(8), comparable: false },
  ];
  const b = bestMarket(2000, items, 100);
  assert.equal(b.item.entity.market, 'B');
  assert.ok(Math.abs(b.gainPct - 10) < 1e-9);
});

test('defaults mirror conf/decision_rules.json', () => {
  const conf = JSON.parse(readFileSync(path.join(APP, '..', 'conf', 'decision_rules.json'), 'utf8'));
  assert.equal(RULES.weekly.perishable, conf.weekly_holding_cost.perishable * 100);
  assert.equal(RULES.weekly.durable, conf.weekly_holding_cost.durable * 100);
  assert.equal(RULES.fixedPct, conf.fixed_transaction_cost * 100);
  assert.equal(RULES.compareMinGainPct, conf.compare_min_gain * 100);
  assert.equal(RULES.compareMaxStaleDays, conf.compare_max_staleness_days);
  assert.equal(RULES.version, conf.version);
  assert.deepEqual([...PERISHABLE].sort(), [...conf.perishable_commodities].sort());
  assert.equal(defaultWeeklyPct(true), 5);
  assert.equal(defaultWeeklyPct(false), 1);
});

// evaluated as of the export time: the stored server decision is a snapshot, while expiry depends on the clock
test('demo forecasts: client rule reproduces the server decision with default costs', () => {
  const idx = JSON.parse(readFileSync(path.join(APP, 'demo', 'index.json'), 'utf8'));
  const meta = JSON.parse(readFileSync(path.join(APP, 'demo', idx.files.meta), 'utf8'));
  for (const id of idx.entities.forecast) {
    const fc = JSON.parse(readFileSync(path.join(APP, 'demo', `forecast_${id}.json`), 'utf8'));
    const cmp = idx.entities.compare.includes(id) ? JSON.parse(readFileSync(path.join(APP, 'demo', `compare_${id}.json`), 'utf8')) : { items: [] };
    const h = fc.horizons.find((x) => x.horizon === RULES.primaryHorizon) || null;
    const perishable = fc.decision.costs.perishable;
    const r = decide({ today: fc.origin.modal_price, horizon: h, supported: fc.supported, unsupportedReason: fc.unsupported_reason,
      stale: fc.freshness.stale, expired: isExpired(h, meta, new Date(meta.generated_at)), perishable, weeklyPct: defaultWeeklyPct(perishable), compareItems: cmp.items });
    assert.equal(r.signal, fc.decision.signal, `entity ${id}`);
    assert.deepEqual(r.reasons, fc.decision.reason_codes, `entity ${id} reasons`);
    if (fc.decision.at_snapshot) assert.equal(r.snapshot.signal, fc.decision.at_snapshot.signal, `entity ${id} snapshot`);
  }
});

test('compare ordering never ranks a stale market above a fresh one', () => {
  const items = [
    { modal_price: 3000, freshness: fresh(9), comparable: false },
    { modal_price: 2100, freshness: fresh(1), comparable: true },
    { modal_price: 2300, freshness: fresh(2), comparable: true },
  ];
  const out = orderCompare(items, 2000, 0);
  assert.deepEqual(out.map((x) => x.it.modal_price), [2300, 2100, 3000]);
  assert.equal(out[2].ok, false);
});

test('client rule agrees with the shared fixtures (conf/decision_fixtures.json)', () => {
  const fx = JSON.parse(readFileSync(path.join(APP, '..', 'conf', 'decision_fixtures.json'), 'utf8'));
  assert.equal(fx.rules_version, RULES.version);
  for (const c of fx.cases) {
    const i = c.input;
    const per = PERISHABLE.has(i.commodity);
    const r = decide({ today: i.today, horizon: { days: i.days, lo80: i.lo80, hi80: i.hi80 }, supported: i.supported,
      unsupportedReason: i.unsupported_reason, stale: i.stale, expired: i.expired, perishable: per,
      weeklyPct: defaultWeeklyPct(per), transportPerQ: i.transport,
      compareItems: i.compare.map((m) => ({ modal_price: m.modal_price, comparable: m.comparable, freshness: { days_old: m.days_old } })) });
    assert.deepEqual([r.signal, r.reasons], [c.expected.signal, c.expected.reasons], c.name);
  }
});

test('expired forecasts never give present-tense advice but keep the historical outlook', () => {
  const r = decide({ ...base, horizon: hz(2200, 2500), expired: true });
  assert.equal(r.signal, 'WATCH');
  assert.deepEqual(r.reasons, ['forecast_expired']);
  assert.equal(r.snapshot.signal, 'HOLD');
});
