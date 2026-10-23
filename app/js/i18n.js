import { LANGS } from '../config.js';
import { interpolate, fmtRupees, fmtPct, fmtDate, fmtNumber, freshnessKey, fmtDateTime } from './format.js';
import * as store from './store.js';

let lang = 'en';
let dict = {};
let comm = null;

export const getLang = () => lang;

export function t(key, vars) {
  const s = dict[key];
  return interpolate(typeof s === 'string' && s ? s : key, vars);
}

export async function setLang(l) {
  if (!LANGS.includes(l)) l = 'en';
  const res = await fetch(`i18n/${l}.json`);
  if (!res.ok) throw new Error('i18n');
  dict = await res.json();
  lang = l;
  store.save('lang', l);
  document.documentElement.lang = l;
  applyStatic(document);
}

/** Fill elements carrying data-i18n / data-i18n-aria / data-i18n-ph attributes. */
export function applyStatic(root) {
  root.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
  root.querySelectorAll('[data-i18n-aria]').forEach((el) => el.setAttribute('aria-label', t(el.dataset.i18nAria)));
  root.querySelectorAll('[data-i18n-ph]').forEach((el) => el.setAttribute('placeholder', t(el.dataset.i18nPh)));
  document.title = t('app.name');
}

export const price = (n) => t('price.per_quintal', { price: fmtRupees(lang, n) });
export const rupees = (n) => fmtRupees(lang, n);
export const pct = (p, signed = true) => fmtPct(lang, p, signed);
export const date = (d) => fmtDate(lang, d);
export const dateTime = (d) => fmtDateTime(lang, d);
export const num = (n, d = 0) => fmtNumber(lang, n, d);

/** "Last report: 17 Apr 2026, 4 days old" — relative wording when the dataset itself is old. */
export function freshness(f, meta) {
  if (!f) return '';
  const { key, n } = freshnessKey(f.days_old, meta && meta.days_since_data);
  return t('fresh.last_report', { date: date(f.last_date), age: t(key, { n: num(n) }) });
}

export async function loadCommodities() {
  if (comm) return comm;
  try { comm = (await (await fetch('i18n/commodities.json')).json()).items || {}; } catch { comm = {}; }
  return comm;
}

/** English name always; localised label only from the reviewed dictionary. */
export function commodityInfo(name) {
  const e = (comm && comm[name]) || null;
  const local = e && lang !== 'en' ? e[lang] : null;
  return { en: name, local: local && local !== name ? local : null, icon: e ? e.icon : 'produce' };
}
