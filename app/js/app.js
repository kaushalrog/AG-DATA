// App bootstrap: language, hash router with lazily imported screens, banners, SW, install prompt.
import { setLang, t, loadCommodities } from './i18n.js';
import * as api from './api.js';
import * as store from './store.js';
import { renderBanners, loading, errorBox } from './ui.js';

const routes = {
  home: () => import('./routes/home.js'),
  commodity: () => import('./routes/commodity.js'),
  compare: () => import('./routes/compare.js'),
  markets: () => import('./routes/markets.js'),
  alerts: () => import('./routes/alerts.js'),
  guide: () => import('./routes/guide.js'),
  settings: () => import('./routes/settings.js'),
  welcome: () => import('./routes/onboarding.js'),
};

const main = document.getElementById('main');
const banners = document.getElementById('banners');
let renderSeq = 0;

export const ctx = {
  meta: null,
  rerender: () => route(),
  announce(msg) { const l = document.getElementById('live'); l.textContent = ''; setTimeout(() => { l.textContent = msg; }, 50); },
};

function parse() {
  const parts = (location.hash.replace(/^#\/?/, '') || 'home').split('/');
  return { name: parts[0] || 'home', args: parts.slice(1).map(decodeURIComponent) };
}

async function route() {
  const seq = ++renderSeq;
  let { name, args } = parse();
  if (!store.load('onboarded', false) && name !== 'welcome') { location.replace('#/welcome'); return; }
  if (!routes[name]) name = 'home';
  document.querySelectorAll('.bottomnav a').forEach((a) => {
    const on = a.dataset.route === name || (a.dataset.route === 'home' && ['commodity', 'compare'].includes(name));
    if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  main.replaceChildren(loading());
  try {
    const mod = await routes[name]();
    if (seq !== renderSeq) return;
    const view = document.createElement('div');
    view.className = 'view';
    await mod.render(view, args, ctx);
    if (seq !== renderSeq) return;
    main.replaceChildren(view);
    const h1 = view.querySelector('h1');
    if (h1 && document.activeElement !== document.body) h1.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  } catch (err) {
    if (seq !== renderSeq) return;
    main.replaceChildren(errorBox(err, () => { api.resetMode(); route(); }));
  }
  renderBanners(banners);
}

async function loadMeta() {
  try { ctx.meta = await api.meta(); } catch { ctx.meta = null; }
}

function setupInstall() {
  const btn = document.getElementById('install-btn');
  let deferred = null;
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault(); deferred = e; btn.hidden = false;
  });
  btn.addEventListener('click', async () => {
    if (!deferred) return;
    btn.hidden = true;
    deferred.prompt();
    try { await deferred.userChoice; } catch { /* ignore */ }
    deferred = null;
  });
  window.addEventListener('appinstalled', () => { btn.hidden = true; });
}

async function start() {
  if (store.load('largeText', false)) document.documentElement.classList.add('large');
  const lang = store.load('lang', null) || 'en';
  try { await setLang(lang); } catch { await setLang('en').catch(() => {}); }
  await loadCommodities();
  api.onStatus(() => renderBanners(banners));
  setupInstall();
  if ('serviceWorker' in navigator) {
    // the shell is served from cache first, so a new version only runs after a reload: do it once,
    // when an updated worker takes over (not on the very first install)
    const hadController = !!navigator.serviceWorker.controller;
    let reloading = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (hadController && !reloading) { reloading = true; location.reload(); }
    });
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
  window.addEventListener('hashchange', route);
  window.addEventListener('online', () => { api.resetMode(); ctx.announce(t('common.loading')); route(); });
  await loadMeta();
  await route();
}

start();
