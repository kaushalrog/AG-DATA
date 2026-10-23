import { h, icon, errorBox, empty, priceRow, pageTitle, commodityName, pictogram, fill, put } from '../ui.js';
import { t, pct, num } from '../i18n.js';
import * as api from '../api.js';
import * as store from '../store.js';

export async function render(view, args, ctx) {
  const locn = store.load('loc', {}) || {};
  const meta = ctx.meta;

  // --- location selectors -------------------------------------------------------------
  const sState = h('select', { id: 'f-state', class: 'input' }, h('option', { value: '' }, t('common.choose_state')));
  const sDist = h('select', { id: 'f-dist', class: 'input' }, h('option', { value: '' }, t('common.all_districts')));
  const sMkt = h('select', { id: 'f-mkt', class: 'input' }, h('option', { value: '' }, t('common.all_markets')));
  const field = (id, key, el) => h('div', { class: 'field' }, h('label', { class: 'label', for: id }, t(key)), el);

  const states = await api.states().catch(() => []);
  for (const s of states) sState.append(h('option', { value: s.state, selected: s.state === locn.state }, s.state));

  let marketsInState = [];
  async function loadMarkets() {
    sDist.length = 1; sMkt.length = 1;
    if (!sState.value) return;
    try {
      const r = await api.markets({ state: sState.value, limit: 500 });
      marketsInState = Array.isArray(r) ? r : r.items || [];
    } catch { marketsInState = []; }
    const dists = [...new Set(marketsInState.map((m) => m.district).filter(Boolean))].sort();
    for (const d of dists) sDist.append(h('option', { value: d, selected: d === locn.district }, d));
    // a saved district/market that is no longer listed (e.g. a different demo snapshot) would filter
    // the price list to nothing while the selects look blank: forget it
    if (locn.district && !dists.includes(locn.district)) { locn.district = locn.market = undefined; store.save('loc', locn); }
    fillMarkets();
  }
  function fillMarkets() {
    sMkt.length = 1;
    const ms = marketsInState.filter((m) => !sDist.value || m.district === sDist.value).map((m) => m.market);
    for (const m of [...new Set(ms)].sort()) sMkt.append(h('option', { value: m, selected: m === locn.market }, m));
    if (locn.market && !ms.includes(locn.market)) { locn.market = undefined; store.save('loc', locn); }
  }
  const persist = () => {
    locn.state = sState.value || undefined; locn.district = sDist.value || undefined; locn.market = sMkt.value || undefined;
    store.save('loc', locn);
    refresh();
  };
  sState.addEventListener('change', async () => { locn.district = locn.market = undefined; await loadMarkets(); persist(); });
  sDist.addEventListener('change', () => { locn.market = undefined; fillMarkets(); persist(); });
  sMkt.addEventListener('change', persist);
  await loadMarkets();

  // --- search -------------------------------------------------------------------------
  const q = h('input', { id: 'q', class: 'input', type: 'search', autocomplete: 'off', enterkeyhint: 'search', placeholder: t('common.search_placeholder') });
  const searchForm = h('form', { class: 'search', role: 'search', onsubmit: (e) => { e.preventDefault(); refresh(); } },
    h('label', { class: 'sr-only', for: 'q' }, t('common.search')), q,
    h('button', { class: 'btn btn-primary btn-icon', type: 'submit', 'aria-label': t('common.search') }, icon('search')));

  // --- sections -----------------------------------------------------------------------
  const listTitle = h('h2', { class: 'h2' }, t('home.latest'));
  const list = h('div', {});
  const movers = h('section', { class: 'card', hidden: true });
  const teaser = h('div', {});

  let offset = 0;
  function refresh() {
    offset = 0;
    const query = q.value.trim();
    listTitle.textContent = query ? t('home.results_for', { q: query }) : t('home.latest');
    if (!locn.state && !query) { put(list, empty('home.no_location')); movers.hidden = true; put(teaser); return; }
    const params = { state: locn.state, district: locn.district, market: locn.market, q: query || undefined, limit: 20 };
    fill(list, () => api.latest(params), (r) => buildList(r, params));
    loadSide();
  }
  function buildList(r, params) {
    if (!r.items || !r.items.length) return empty('empty.prices');
    const ul = h('ul', { class: 'list' }, r.items.map((it) => priceRow(it, meta)));
    const out = [ul];
    if (r.total > (r.offset || 0) + r.items.length) {
      const more = h('button', { class: 'btn btn-ghost btn-block', type: 'button' }, t('common.load_more'));
      more.addEventListener('click', async () => {
        more.disabled = true;
        offset += r.items.length;
        try {
          const nx = await api.latest({ ...params, offset });
          nx.items.forEach((it) => ul.append(priceRow(it, meta)));
          if (nx.total > offset + nx.items.length) { more.disabled = false; r = { ...nx, offset }; } else more.remove();
        } catch (e) { more.replaceWith(errorBox(e)); }
      });
      out.push(more);
    }
    return out;
  }
  function loadSide() {
    if (!locn.state) return;
    api.trends({ state: locn.state, limit: 5 }).then((tr) => {
      const col = (key, arr, dir) => h('div', { class: 'mover-col' },
        h('h3', { class: 'h3' }, icon(dir), ' ', t(key)),
        h('ul', { class: 'plain' }, (arr || []).slice(0, 5).map((m) => h('li', { class: 'mover' },
          pictogram(m.commodity, 28), commodityName(m.commodity),
          h('span', { class: 'chip chip-' + dir }, t('home.median_change', { pct: pct(m.median_change_7d_pct), n: num(m.markets) }))))));
      put(movers, h('h2', { class: 'h2' }, t('home.movers', { state: tr.state || locn.state })),
        h('p', { class: 'muted small' }, t('alerts.note')),
        h('div', { class: 'movers' }, col('home.rising', tr.rising, 'up'), col('home.falling', tr.falling, 'down')));
      movers.hidden = !((tr.rising || []).length || (tr.falling || []).length);
    }).catch(() => { movers.hidden = true; });
    api.alerts({ state: locn.state, days: 14 }).then((a) => {
      const n = (a.items || []).length;
      put(teaser, n ? h('a', { class: 'card link-card', href: '#/alerts' }, icon('bell'),
        h('span', {}, t('home.alerts_teaser', { n: num(n) })), icon('next')) : '');
    }).catch(() => put(teaser));
  }

  view.append(
    pageTitle(t('home.title')),
    h('section', { class: 'card', 'aria-labelledby': 'loc-h' },
      h('h2', { class: 'h3', id: 'loc-h' }, icon('pin'), ' ', t('home.location')),
      h('div', { class: 'fields' }, field('f-state', 'common.state', sState), field('f-dist', 'common.district', sDist), field('f-mkt', 'common.market', sMkt))),
    searchForm,
    teaser,
    h('section', { class: 'card' }, listTitle, list),
    movers,
    h('section', { class: 'card' }, h('h2', { class: 'h2' }, t('home.quick')),
      h('div', { class: 'quick' },
        h('a', { class: 'btn btn-ghost', href: '#/alerts' }, icon('bell'), t('home.see_alerts')),
        h('a', { class: 'btn btn-ghost', href: '#/guide/prices' }, icon('book'), t('home.read_guide')),
        h('a', { class: 'btn btn-ghost', href: '#/guide/forecasts' }, icon('watch'), t('guide.forecasts.title')))));
  refresh();
}
