import { h, icon, pageTitle, empty, fill, priceRow, put } from '../ui.js';
import { t, num } from '../i18n.js';
import * as api from '../api.js';
import * as store from '../store.js';

export async function render(view, args, ctx) {
  const locn = store.load('loc', {}) || {};
  view.append(pageTitle(t('markets.title')));
  if (!locn.state) { view.append(empty('home.no_location'), h('a', { class: 'btn btn-primary', href: '#/home' }, t('common.choose_state'))); return; }

  const q = h('input', { id: 'mq', class: 'input', type: 'search', autocomplete: 'off', placeholder: t('markets.search') });
  const box = h('div', { 'aria-live': 'polite' });
  const detail = h('div', {});
  let timer;
  const load = () => fill(box, () => api.markets({ state: locn.state, q: q.value.trim() || undefined, limit: 100 }), (r) => {
    const items = Array.isArray(r) ? r : r.items || [];
    if (!items.length) return empty('empty.markets');
    return [h('p', { class: 'muted small' }, t('markets.count', { n: num(r.total ?? items.length) })),
      h('ul', { class: 'list' }, items.map((m) => {
        const cur = m.market === locn.market;
        return h('li', { class: 'mkt' + (cur ? ' is-current' : '') },
          h('div', { class: 'row' },
            h('div', { class: 'row-main' }, h('strong', {}, m.market), h('span', { class: 'muted small' }, m.district || ''),
              cur ? h('span', { class: 'tag tag-ok' }, icon('pin'), ' ', t('markets.current')) : null),
            h('button', { class: 'btn btn-secondary btn-small', type: 'button', onclick: () => {
              store.save('loc', { state: locn.state, district: m.district, market: m.market });
              showMarket(m);
            } }, t('markets.use'))));
      }))];
  });
  const showMarket = (m) => {
    locn.district = m.district; locn.market = m.market;
    put(detail, h('h2', { class: 'h2', tabindex: '-1' }, t('markets.commodities', { market: m.market })), h('div', {}));
    fill(detail.lastChild, () => api.latest({ state: locn.state, market: m.market, limit: 50 }),
      (r) => (r.items && r.items.length ? h('ul', { class: 'list' }, r.items.map((it) => priceRow(it, ctx.meta))) : empty('empty.prices')));
    detail.firstChild.focus();
    load();
  };
  q.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(load, 350); });

  view.append(h('section', { class: 'card' }, h('label', { class: 'label', for: 'mq' }, t('markets.search')), q),
    h('section', { class: 'card' }, detail), h('section', { class: 'card' }, box));
  // a saved market that is no longer listed (e.g. a different demo snapshot) is forgotten, not shown empty
  let saved = null;
  if (locn.market) {
    const r = await api.markets({ state: locn.state, q: locn.market, limit: 100 }).catch(() => null);
    const items = r ? (Array.isArray(r) ? r : r.items || []) : [];
    saved = items.find((m) => m.market === locn.market && (!locn.district || m.district === locn.district)) || null;
    if (r && !saved) { locn.district = locn.market = undefined; store.save('loc', { state: locn.state }); }
  }
  if (saved) showMarket(saved); else load();
}
