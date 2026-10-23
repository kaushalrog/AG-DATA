import { h, pageTitle } from '../ui.js';
import { t, setLang, getLang } from '../i18n.js';
import { LANGS } from '../../config.js';
import * as api from '../api.js';
import * as store from '../store.js';

export async function render(view, args, ctx) {
  const langList = h('div', { class: 'lang-grid', role: 'radiogroup', 'aria-labelledby': 'lang-h' },
    LANGS.map((l) => h('button', {
      type: 'button', role: 'radio', class: 'lang-btn', lang: l,
      'aria-checked': String(l === getLang()),
      onclick: async () => { await setLang(l); ctx.rerender(); },
    }, t('lang.' + l))));

  const sel = h('select', { id: 'ob-state', class: 'input' }, h('option', { value: '' }, t('common.choose_state')));
  const stateBox = h('div', { class: 'field' }, h('label', { for: 'ob-state', class: 'label' }, t('onboarding.choose_state')), sel);
  try {
    const states = await api.states();
    const cur = (store.load('loc', {}) || {}).state;
    for (const s of states) sel.append(h('option', { value: s.state, selected: s.state === cur }, s.state));
  } catch { stateBox.hidden = true; }

  const finish = (withState) => {
    if (withState && sel.value) store.save('loc', { state: sel.value });
    store.save('onboarded', true);
    location.hash = '#/home';
  };

  view.append(
    h('section', { class: 'card hero' },
      h('img', { src: 'icons/app-icon.svg', alt: '', width: 64, height: 64 }),
      pageTitle(t('onboarding.welcome')),
      h('p', { class: 'lead' }, t('app.tagline'))),
    h('section', { class: 'card' }, h('h2', { class: 'h2', id: 'lang-h' }, t('onboarding.choose_language')), langList),
    h('section', { class: 'card' }, stateBox,
      h('button', { type: 'button', class: 'btn btn-primary btn-block', onclick: () => finish(true) }, t('onboarding.continue')),
      h('button', { type: 'button', class: 'btn btn-ghost btn-block', onclick: () => finish(false) }, t('onboarding.skip'))),
    h('p', { class: 'muted small' }, t('settings.translation_note')));
}
