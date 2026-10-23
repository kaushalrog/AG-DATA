import { h, icon, pictogram, commodityName, pageTitle, empty, fill } from '../ui.js';
import { t, price, pct, date, num } from '../i18n.js';
import * as api from '../api.js';
import * as store from '../store.js';

const TYPE_ICON = { price_spike: 'up', price_drop: 'down', suspect_data_error: 'warn' };

export async function render(view, args, ctx) {
  const state = (store.load('loc', {}) || {}).state;
  const trendsBox = h('div', {});
  const alertsBox = h('div', {});
  view.append(pageTitle(t('alerts.title')),
    h('p', { class: 'notice note-hist card' }, icon('info'), ' ', t('alerts.note')));
  if (!state) { view.append(empty('home.no_location'), h('a', { class: 'btn btn-primary', href: '#/home' }, t('common.choose_state'))); return; }

  const col = (key, arr, dir) => h('section', { class: 'card' }, h('h2', { class: 'h2' }, icon(dir), ' ', t(key)),
    arr && arr.length ? h('ul', { class: 'plain' }, arr.map((m) => h('li', { class: 'mover' }, pictogram(m.commodity, 28), commodityName(m.commodity),
      h('span', { class: 'chip chip-' + dir }, pct(m.median_change_7d_pct)), h('span', { class: 'small muted' }, t('alerts.markets_n', { n: num(m.markets) }))))) : empty('empty.alerts'));

  view.append(trendsBox, h('section', { class: 'card' }, h('h2', { class: 'h2' }, t('alerts.unusual')), alertsBox));
  fill(trendsBox, () => api.trends({ state, limit: 10 }), (tr) => [col('alerts.rising', tr.rising, 'up'), col('alerts.falling', tr.falling, 'down')]);
  fill(alertsBox, () => api.alerts({ state, days: 14 }), (a) => (a.items && a.items.length
    ? h('ul', { class: 'list' }, a.items.map((it) => h('li', {}, h('a', { class: 'row', href: '#/commodity/' + encodeURIComponent(it.entity.entity_id) },
      pictogram(it.entity.commodity),
      h('div', { class: 'row-main' }, commodityName(it.entity.commodity, 'strong'),
        h('span', { class: 'muted small' }, `${it.entity.market} · ${date(it.date)}`),
        h('span', { class: 'tag tag-' + (it.type === 'suspect_data_error' ? 'warn' : 'info') }, icon(TYPE_ICON[it.type] || 'info'), ' ', t('alert.' + it.type))),
      h('div', { class: 'row-side' }, h('span', { class: 'small' }, t('alerts.vs_usual', { price: price(it.modal_price), ref: price(it.ref_mean_price) })))))))
    : empty('empty.alerts')));
}
