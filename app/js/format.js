// Pure formatting helpers (no DOM) so they can be unit-tested in Node.

export const loc = (lang) => `${lang || 'en'}-IN`;

/** Replace {name} tokens; unknown tokens are left visible so gaps are noticed. */
export function interpolate(str, vars) {
  if (!vars) return str;
  return str.replace(/\{(\w+)\}/g, (m, k) => (vars[k] === undefined || vars[k] === null ? m : String(vars[k])));
}

const nfCache = new Map();
/** Integer group sizes for 1,50,000 — Indian (lakh) grouping gives [1, 2, 3]. */
const groups = (f) => f.formatToParts(150000).filter((p) => p.type === 'integer').map((p) => p.value.length).join();
/**
 * Intl.NumberFormat('<lang>-IN'). Some ICU builds format ml-IN / kn-IN with Western grouping
 * (150,000); Indian readers expect lakh grouping (1,50,000), so we then fall back to en-IN,
 * which uses the same Latin digits.
 */
function nf(lang, opts) {
  const key = lang + JSON.stringify(opts);
  if (!nfCache.has(key)) {
    let f = new Intl.NumberFormat(loc(lang), opts);
    if (groups(f) !== '1,2,3') f = new Intl.NumberFormat('en-IN', opts);
    nfCache.set(key, f);
  }
  return nfCache.get(key);
}

export function fmtNumber(lang, n, digits = 0) {
  if (n === null || n === undefined || !Number.isFinite(+n)) return '–';
  return nf(lang, { maximumFractionDigits: digits, minimumFractionDigits: 0 }).format(+n);
}

/** Rupee amount, Indian digit grouping: ₹2,000 / ₹1,00,000 (no decimals). */
export function fmtRupees(lang, n) {
  if (n === null || n === undefined || !Number.isFinite(+n)) return '–';
  return nf(lang, { style: 'currency', currency: 'INR', maximumFractionDigits: 0, minimumFractionDigits: 0 }).format(Math.round(+n));
}

/** pct is already in percent units (4.2 means 4.2%). signed=true adds +/−. */
export function fmtPct(lang, pct, signed = true, digits = 1) {
  if (pct === null || pct === undefined || !Number.isFinite(+pct)) return '–';
  return nf(lang, { style: 'percent', maximumFractionDigits: digits, minimumFractionDigits: 0, signDisplay: signed ? 'exceptZero' : 'auto' }).format(+pct / 100);
}

/** ISO date "2026-04-17" -> "17 Apr 2026" (localised). Treated as a calendar date (UTC). */
export function fmtDate(lang, iso) {
  if (!iso) return '–';
  const d = new Date(String(iso).length <= 10 ? iso + 'T00:00:00Z' : iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return new Intl.DateTimeFormat(loc(lang), { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(d);
}

export function fmtDateTime(lang, iso) {
  if (!iso) return '–';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return new Intl.DateTimeFormat(loc(lang), { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' }).format(d);
}

/**
 * Choose the freshness phrase key. days_old is counted from meta.data_as_of (API contract),
 * so when the whole dataset is old we must NOT say "4 days old" as if relative to today.
 */
export function freshnessKey(daysOld, daysSinceData) {
  const n = Math.max(0, Math.round(+daysOld || 0));
  const datasetOld = (+daysSinceData || 0) > 3;
  if (n === 0) return { key: 'fresh.age_zero', n };
  if (datasetOld) return { key: n === 1 ? 'fresh.age_rel_one' : 'fresh.age_rel_days', n };
  return { key: n === 1 ? 'fresh.age_one' : 'fresh.age_days', n };
}

/** Accuracy phrasing inputs: MAE % -> "9.8%", coverage 0.79 -> 79 (times out of 100). */
export function coveragePer100(cov) {
  if (cov === null || cov === undefined || !Number.isFinite(+cov)) return null;
  return Math.round(+cov * 100);
}
