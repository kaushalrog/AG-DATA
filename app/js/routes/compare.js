import { h, icon, pictogram, commodityName, freshLine, backLink, pageTitle, empty, put } from '../ui.js';
import { t, price, pct, date } from '../i18n.js';
import { orderCompare } from '../decision.js';
import * as api from '../api.js';
import * as store from '../store.js';

export async function render(view, [id], ctx) {
  let scope = 'district';
  const costs = store.load('costs', {}) || {};
  const tIn = h('input', { id: 'cmp-trans', class: 'input', type: 'number', inputmode: 'numeric', min: 0, step: 10, value: +costs.transport || 0 });
  const list = h('div', { 'aria-live': 'polite' });
  const head = h('div', {});
  let data = null;

  function draw() {
    const transport = Math.max(0, +tIn.value || 0);
    const ref = data.reference;
    put(head, h('div', { class: 'c-head' }, pictogram(ref.entity.commodity, 48),
      h('div', {}, commodityName(ref.entity.commodity, 'strong'),
        h('p', { class: 'muted small' }, ref.entity.variety || ''),
        h('p', {}, t('compare.reference', { market: ref.entity.market, price: price(ref.modal_price), date: date(ref.date) })))));
    const rows = orderCompare(data.items || [], ref.modal_price, transport);
    if (!rows.length) { put(list, empty('compare.empty')); return; }
    put(list, h('ul', { class: 'list' }, rows.map(({ it, ok, net }) => h('li', { class: 'cmp' + (ok ? '' : ' is-stale') },
      h('div', { class: 'row' },
        h('div', { class: 'row-main' },
          h('strong', {}, it.entity.market), h('span', { class: 'muted small' }, it.entity.district),
          ok ? null : h('p', { class: 'tag tag-warn' }, icon('clock'), ' ', t('compare.not_comparable'))),
        h('div', { class: 'row-side' },
          h('span', { class: 'price' }, price(it.modal_price)),
          h('span', { class: 'chip chip-' + (it.diff_pct > 0 ? 'up' : it.diff_pct < 0 ? 'down' : 'flat') }, t('compare.diff', { pct: pct(it.diff_pct) })),
          transport > 0 && net != null ? h('span', { class: 'small' }, t('compare.after_transport', { pct: pct(net) })) : null,
          it.forecast_h7_median != null ? h('span', { class: 'small muted' }, t('compare.forecast_h7', { price: price(it.forecast_h7_median) })) : null),
        freshLine(it.freshness, ctx.meta))))));
  }

  async function load() {
    put(list, h('p', { class: 'loading', role: 'status' }, t('common.loading')));
    data = await api.compare(id, scope);
    draw();
  }

  const scopeSel = h('select', { id: 'cmp-scope', class: 'input', onchange: async (e) => { scope = e.target.value; await load().catch(() => {}); } },
    h('option', { value: 'district' }, t('compare.scope_district')), h('option', { value: 'state' }, t('compare.scope_state')));
  tIn.addEventListener('input', () => { if (data) draw(); });
  tIn.addEventListener('change', () => { const c = store.load('costs', {}) || {}; c.transport = Math.max(0, +tIn.value || 0); store.save('costs', c); });

  view.append(backLink('#/commodity/' + encodeURIComponent(id)), pageTitle(t('compare.title')), head,
    h('section', { class: 'card' },
      h('div', { class: 'fields' },
        h('div', { class: 'field' }, h('label', { class: 'label', for: 'cmp-scope' }, t('compare.scope_label')), scopeSel),
        h('div', { class: 'field' }, h('label', { class: 'label', for: 'cmp-trans' }, t('decision.transport_cost')), tIn)),
      h('p', { class: 'small muted' }, t('compare.note'))),
    h('section', { class: 'card' }, list));
  await load();
}
