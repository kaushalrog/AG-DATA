import { h, pageTitle } from '../ui.js';
import { t, setLang, getLang } from '../i18n.js';
import { LANGS, APP_VERSION } from '../../config.js';
import { RULES } from '../decision.js';
import * as api from '../api.js';
import * as store from '../store.js';

export async function render(view, args, ctx) {
  const field = (id, key, el, help) => h('div', { class: 'field' }, h('label', { class: 'label', for: id }, t(key)), el, help ? h('p', { class: 'help' }, help) : null);
  const msg = h('p', { class: 'small', role: 'status' });

  const lang = h('select', { id: 's-lang', class: 'input', onchange: async (e) => { await setLang(e.target.value); ctx.rerender(); } },
    LANGS.map((l) => h('option', { value: l, lang: l, selected: l === getLang() }, t('lang.' + l))));

  const locn = store.load('loc', {}) || {};
  const st = h('select', { id: 's-state', class: 'input', onchange: (e) => { store.save('loc', { state: e.target.value || undefined }); msg.textContent = t('common.saved'); } },
    h('option', { value: '' }, t('common.choose_state')));
  api.states().then((ss) => ss.forEach((s) => st.append(h('option', { value: s.state, selected: s.state === locn.state }, s.state)))).catch(() => {});

  const costs = store.load('costs', {}) || {};
  const num = (id, v, max, step) => h('input', { id, class: 'input', type: 'number', inputmode: 'decimal', min: 0, max, step, value: v });
  const cp = num('s-cp', costs.perishable ?? RULES.weekly.perishable, 50, 0.5);
  const cd = num('s-cd', costs.durable ?? RULES.weekly.durable, 50, 0.5);
  const ct = num('s-ct', costs.transport ?? 0, 100000, 10);
  const saveCosts = (e) => {
    e.preventDefault();
    store.save('costs', { perishable: Math.max(0, +cp.value || 0), durable: Math.max(0, +cd.value || 0), transport: Math.max(0, +ct.value || 0) });
    msg.textContent = t('common.saved');
  };

  const large = h('input', { id: 's-large', type: 'checkbox', class: 'check', checked: document.documentElement.classList.contains('large'),
    onchange: (e) => { document.documentElement.classList.toggle('large', e.target.checked); store.save('largeText', e.target.checked); } });

  const clear = async () => {
    store.clearAll();
    try { if (self.caches) for (const k of await caches.keys()) if (k.startsWith('agri-api')) await caches.delete(k); } catch { /* ignore */ }
    msg.textContent = t('settings.cleared');
    ctx.announce(t('settings.cleared'));
  };

  const src = (ctx.meta && ctx.meta.source) || {};
  view.append(pageTitle(t('settings.title')),
    h('section', { class: 'card' }, h('h2', { class: 'h2' }, t('settings.language')), field('s-lang', 'settings.language', lang),
      h('p', { class: 'small muted' }, t('settings.translation_note'))),
    h('section', { class: 'card' }, h('h2', { class: 'h2' }, t('settings.location')), field('s-state', 'common.state', st)),
    h('section', { class: 'card' }, h('h2', { class: 'h2' }, t('settings.costs')),
      h('form', { onsubmit: saveCosts },
        field('s-cp', 'settings.holding_perishable', cp), field('s-cd', 'settings.holding_durable', cd),
        field('s-ct', 'decision.transport_cost', ct),
        h('button', { class: 'btn btn-primary', type: 'submit' }, t('common.save')))),
    h('section', { class: 'card' }, h('h2', { class: 'h2' }, t('settings.display')),
      h('label', { class: 'check-row', for: 's-large' }, large, h('span', {}, t('settings.large_text')))),
    h('section', { class: 'card' }, h('h2', { class: 'h2' }, t('settings.clear')), h('p', { class: 'help' }, t('settings.clear_help')),
      h('button', { class: 'btn btn-danger', type: 'button', onclick: clear }, t('settings.clear'))),
    msg,
    h('section', { class: 'card' }, h('h2', { class: 'h2' }, t('settings.about')),
      h('p', {}, t('settings.version', { version: APP_VERSION })),
      src.name ? h('p', {}, t('settings.data_source', { source: src.name, licence: src.licence || '–' })) : null,
      ctx.meta ? h('p', { class: 'small muted' }, t('origin.' + (ctx.meta.data_origin || 'archive'))) : null));
}
