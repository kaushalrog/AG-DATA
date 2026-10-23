// Tiny DOM helpers. All API data goes through textContent (never innerHTML).
import { t, price, pct, freshness, commodityInfo, date, num } from './i18n.js';
import { status, ApiError, resetMode } from './api.js';

export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) el.append(c.nodeType ? c : String(c));
  return el;
}

/** replaceChildren that skips null/false (DOM would otherwise insert the text "null"). */
export function put(el, ...kids) {
  el.replaceChildren(...kids.flat().filter((k) => k !== null && k !== undefined && k !== false));
}

const SVGNS = 'http://www.w3.org/2000/svg';
/** Inline UI icon from the sprite in index.html; decorative (aria-hidden). */
export function icon(name, cls = 'ic') {
  const s = document.createElementNS(SVGNS, 'svg');
  s.setAttribute('class', cls); s.setAttribute('aria-hidden', 'true'); s.setAttribute('focusable', 'false');
  const u = document.createElementNS(SVGNS, 'use');
  u.setAttribute('href', '#i-' + name);
  s.append(u);
  return s;
}

/** Commodity pictogram (decorative: the name is always printed next to it). */
export function pictogram(name, size = 40) {
  const { icon: ic } = commodityInfo(name);
  return h('img', { src: `icons/commodities/${ic}.svg`, alt: '', width: size, height: size, class: 'picto', loading: 'lazy', decoding: 'async' });
}

/** English name always, localised label (if reviewed) underneath. */
export function commodityName(name, tag = 'span') {
  const { en, local } = commodityInfo(name);
  return h(tag, { class: 'cname' }, local ? h('span', { class: 'cname-local', lang: document.documentElement.lang }, local) : null,
    h('span', { class: local ? 'cname-en' : 'cname-local', lang: 'en' }, en));
}

export function loading() {
  return h('div', { class: 'loading', role: 'status' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), t('common.loading'));
}

export function errorBox(err, retry) {
  const code = err instanceof ApiError ? err.code : 'network';
  const key = ['not_found', 'bad_request', 'rate_limited', 'unavailable', 'network'].includes(code) ? code : 'unavailable';
  return h('div', { class: 'card notice notice-error', role: 'alert' },
    h('h2', { class: 'h3' }, icon('warn'), ' ', t('error.title')),
    h('p', {}, t('error.' + key)),
    retry ? h('button', { class: 'btn btn-primary', type: 'button', onclick: retry }, icon('retry'), t('common.retry')) : null);
}

export function empty(key) {
  return h('p', { class: 'empty' }, t(key));
}

export function freshLine(f, meta) {
  return h('p', { class: 'fresh' + (f && f.stale ? ' is-stale' : '') }, f && f.stale ? icon('clock') : null, ' ', freshness(f, meta),
    f && f.stale ? h('span', { class: 'tag tag-warn' }, t('fresh.older_tag')) : null);
}

export function changeChip(p) {
  if (p === null || p === undefined) return null;
  const dir = p > 0 ? 'up' : p < 0 ? 'down' : 'flat';
  return h('span', { class: 'chip chip-' + dir }, icon(dir === 'up' ? 'up' : dir === 'down' ? 'down' : 'flat'), ' ', t('price.change_7d', { pct: pct(p) }));
}

/** One latest-price row linking to the commodity screen. */
export function priceRow(it, meta) {
  const e = it.entity;
  return h('li', {},
    h('a', { class: 'row', href: '#/commodity/' + encodeURIComponent(e.entity_id) },
      pictogram(e.commodity),
      h('div', { class: 'row-main' },
        commodityName(e.commodity, 'strong'),
        h('span', { class: 'muted small' }, [e.variety, e.market].filter(Boolean).join(' · '))),
      h('div', { class: 'row-side' },
        h('span', { class: 'price' }, price(it.modal_price)),
        changeChip(it.change_7d_pct)),
      freshLine(it.freshness, meta),
      it.forecast_supported ? h('span', { class: 'tag tag-ok row-tag' }, t('home.outlook_available')) : null));
}

/** Global data-status banners (stale / archive / offline / demo). */
export function renderBanners(el) {
  put(el);
  const m = status.meta;
  if (status.mode === 'demo') {
    el.append(h('div', { class: 'banner banner-demo' }, icon('info'),
      h('div', {}, h('strong', {}, t('banner.demo')), h('p', {}, t('banner.demo_body')))));
  } else if (status.mode === 'cache') {
    el.append(h('div', { class: 'banner banner-offline' }, icon('offline'),
      h('p', {}, t('banner.offline', { time: status.cachedAt ? new Date(status.cachedAt).toLocaleString(document.documentElement.lang + '-IN') : '–' }))));
  }
  if (m && m.days_since_data > 3) {
    const origin = m.data_origin === 'archive' ? 'banner.archive_body' : m.data_origin === 'replay' ? 'banner.replay_body' : null;
    el.append(h('div', { class: 'banner banner-stale' }, icon('clock'),
      h('div', {}, h('strong', {}, t('banner.stale_title')),
        h('p', {}, t('banner.stale_body', { date: date(m.data_as_of), n: num(m.days_since_data) })),
        origin ? h('p', {}, t(origin)) : null)));
  }
}

export function backLink(href) {
  return h('a', { class: 'back', href }, icon('back'), t('a11y.back'));
}

export function pageTitle(text) {
  return h('h1', { class: 'h1', tabindex: '-1', id: 'page-title' }, text);
}

/** Fill `box` asynchronously so the first screen paints without waiting on every request. */
export function fill(box, load, build) {
  put(box, loading());
  box.setAttribute('aria-busy', 'true');
  const run = () => load().then((d) => put(box, ...[].concat(build(d))))
    .catch((e) => put(box, errorBox(e, () => { resetMode(); fill(box, load, build); })))
    .finally(() => box.removeAttribute('aria-busy'));
  return run();
}

