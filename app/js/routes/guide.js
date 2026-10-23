import { h, icon, pageTitle, backLink } from '../ui.js';
import { t } from '../i18n.js';

// topic -> pictogram (commodity icon or UI sprite icon)
export const TOPICS = {
  prices: { img: 'tomato' }, trends: { ui: 'up' }, forecasts: { img: 'onion' }, wrong: { ui: 'warn' },
  ranges: { ui: 'watch' }, compare: { ui: 'compare' }, transport: { img: 'produce' }, signals: { ui: 'hold' },
  guarantee: { ui: 'info' }, missing: { ui: 'clock' },
};

const pic = (k) => (TOPICS[k].img
  ? h('img', { src: `icons/commodities/${TOPICS[k].img}.svg`, alt: '', width: 40, height: 40, class: 'picto' })
  : h('span', { class: 'picto picto-ui' }, icon(TOPICS[k].ui)));

export async function render(view, [topic]) {
  if (topic && TOPICS[topic]) {
    view.append(backLink('#/guide'),
      h('article', { class: 'card guide' },
        h('div', { class: 'c-head' }, pic(topic), pageTitle(t(`guide.${topic}.title`))),
        ['p1', 'p2', 'p3'].map((p) => h('p', {}, t(`guide.${topic}.${p}`)))),
      h('a', { class: 'btn btn-ghost btn-block', href: '#/guide' }, t('guide.all_topics')));
    return;
  }
  view.append(pageTitle(t('guide.title')), h('p', { class: 'lead' }, t('guide.intro')),
    h('ul', { class: 'list' }, Object.keys(TOPICS).map((k) => h('li', {},
      h('a', { class: 'row', href: '#/guide/' + k }, pic(k), h('span', { class: 'row-main' }, h('strong', {}, t(`guide.${k}.title`))), icon('next'))))));
}
