// Client-side copy of the decision rule (canonical spec: conf/decision_rules.json; shared fixtures:
// conf/decision_fixtures.json, also run against the API and the Spark backtest) so a farmer can re-run
// the market outlook with their own costs. Pure functions, unit-tested in Node.
// Evaluated on the primary horizon (h7). Precedence:
//   unsupported > forecast_expired > stale report > HOLD > SELL > COMPARE > WATCH
//
//   cost(h) = fixed + weekly_holding(perishable?) * days / 7          (fractions of today's price)
//   HOLD    if lo80(h) >= today * (1 + cost(h))   [== log form lo80 >= ln(1+cost) on returns]
//   SELL    if hi80(h) <= today                   [== hi80 log-return <= 0]
//   COMPARE if a market in the same district/state has a fresh (<= 3 days) price whose
//           (modal - transport) >= reference * (1 + 0.05), same commodity+variety
//   WATCH   otherwise ('uncertain'); also when unsupported ('insufficient_history') or stale ('stale_data')

export const RULES = {
  version: '2026-10-23.1',
  primaryHorizon: 'h7',
  weekly: { perishable: 5, durable: 1 }, // percent per week
  fixedPct: 1,
  compareMinGainPct: 5,
  compareMaxStaleDays: 3,
  staleAfterDays: 3,
};

export const SIGNALS = ['SELL', 'HOLD', 'WATCH', 'COMPARE'];
export const REASONS = ['lower_bound_above_cost', 'upper_bound_below_today', 'better_market_nearby',
  'uncertain', 'insufficient_history', 'stale_data', 'perishable_cost_applied', 'forecast_expired'];
const EPS = 1e-9; // boundary tolerance shared with decisions.py / ForecastEval

export const PERISHABLE = new Set([
  'Potato', 'Onion', 'Tomato', 'Brinjal', 'Green Chilli', 'Cauliflower', 'Bhindi (Ladies Finger)',
  'Cucumbar (Kheera)', 'Cabbage', 'Banana', 'Bottle gourd', 'Pumpkin', 'Bitter gourd', 'Apple',
  'Ginger (Green)', 'Carrot', 'Lemon', 'Pomegranate', 'Capsicum', 'Coriander (Leaves)',
]);

/** Total holding cost for `days`, in percent of today's price. */
export function holdingCostPct(days, weeklyPct, fixedPct = RULES.fixedPct) {
  return fixedPct + weeklyPct * (days / 7);
}

/** Best fresh, comparable alternative market after transport, or null. */
export function bestMarket(refPrice, items, transportPerQ = 0) {
  let best = null;
  for (const it of items || []) {
    if (!it || it.comparable === false) continue;
    const age = it.freshness ? it.freshness.days_old : null;
    if (age === null || age === undefined || age > RULES.compareMaxStaleDays) continue;
    const net = (+it.modal_price || 0) - (+transportPerQ || 0);
    const gainPct = refPrice > 0 ? (net / refPrice - 1) * 100 : -Infinity;
    if (!best || gainPct > best.gainPct) best = { item: it, net, gainPct };
  }
  return best;
}

/**
 * @param {object} p
 * @param {number} p.today         origin.modal_price
 * @param {object} p.horizon       {days, lo80, hi80}
 * @param {boolean} p.supported
 * @param {string|null} p.unsupportedReason
 * @param {boolean} p.stale        freshness.stale
 * @param {boolean} [p.expired]    today is past the horizon's target window, or the dataset is stale
 * @param {boolean} p.perishable
 * @param {number} p.weeklyPct     holding cost % per week
 * @param {number} [p.fixedPct]
 * @param {number} [p.transportPerQ] ₹ per quintal to reach another market
 * @param {Array}  [p.compareItems] /compare items
 */
export function decide(p) {
  const out = { signal: 'WATCH', reasons: [], costPct: null, needPrice: null, best: null };
  if (!p.supported || !p.horizon) {
    if (p.unsupportedReason === 'stale_beyond_limit') out.reasons.push('stale_data');
    else if (p.unsupportedReason === 'insufficient_history' || !p.unsupportedReason) out.reasons.push('insufficient_history');
    // not_in_forecast_commodities: no reason code; the UI shows the unsupported_reason text instead
    return out;
  }
  const { days, lo80, hi80 } = p.horizon;
  out.costPct = holdingCostPct(days, p.weeklyPct, p.fixedPct ?? RULES.fixedPct);
  out.needPrice = p.today * (1 + out.costPct / 100);
  if (p.expired) {
    // never present-tense advice for a window that has passed; keep what the rule said on the data date
    out.reasons.push('forecast_expired');
    out.snapshot = decide({ ...p, expired: false, stale: false });
    return out;
  }
  if (p.stale) { out.reasons.push('stale_data'); return out; }
  const perishableNote = p.perishable ? ['perishable_cost_applied'] : [];
  out.best = bestMarket(p.today, p.compareItems, p.transportPerQ);
  if (lo80 >= out.needPrice * (1 - EPS)) {
    out.signal = 'HOLD'; out.reasons.push('lower_bound_above_cost', ...perishableNote);
  } else if (hi80 <= p.today * (1 + EPS)) {
    out.signal = 'SELL'; out.reasons.push('upper_bound_below_today');
  } else if (out.best && out.best.gainPct >= RULES.compareMinGainPct - 1e-7) {
    out.signal = 'COMPARE'; out.reasons.push('better_market_nearby');
  } else {
    out.reasons.push('uncertain', ...perishableNote);
  }
  return out;
}

export function defaultWeeklyPct(perishable) {
  return perishable ? RULES.weekly.perishable : RULES.weekly.durable;
}

/** True when the forecast's target window has passed, or the whole dataset is older than staleAfterDays. */
export function isExpired(horizon, meta, now = new Date()) {
  if (meta && typeof meta.days_since_data === 'number' && meta.days_since_data > RULES.staleAfterDays) return true;
  const end = horizon && horizon.target_window && horizon.target_window[1];
  return !!end && now > new Date(end + 'T23:59:59');
}

/** Fresh & comparable first (by net gain), stale ones always after and visibly marked. */
export function orderCompare(items, refPrice, transport) {
  const fresh = (it) => it.comparable !== false && it.freshness && it.freshness.days_old <= RULES.compareMaxStaleDays;
  return items.map((it) => ({ it, ok: fresh(it), net: refPrice ? ((it.modal_price - transport) / refPrice - 1) * 100 : null }))
    .sort((a, b) => (a.ok === b.ok ? (b.net ?? 0) - (a.net ?? 0) : a.ok ? -1 : 1));
}
