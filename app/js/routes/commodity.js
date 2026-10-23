import { h, icon, pictogram, freshLine, backLink, pageTitle, put } from '../ui.js';
import { t, price, rupees, pct, date, dateTime, num, commodityInfo } from '../i18n.js';
import { decide, defaultWeeklyPct, isExpired, PERISHABLE, RULES } from '../decision.js';
import { coveragePer100 } from '../format.js';
import * as api from '../api.js';
import * as store from '../store.js';

const SIG_ICON = { SELL: 'sell', HOLD: 'hold', WATCH: 'watch', COMPARE: 'compare' };
const HORIZON_ORDER = ['next', 'h3', 'h7', 'h14'];

const dl = (rows) => h('dl', { class: 'facts' }, rows.filter(Boolean).map(([k, v]) => h('div', {}, h('dt', {}, k), h('dd', {}, v))));

export async function render(view, [id], ctx) {
  if (!id) throw new api.ApiError('bad_request');
  const meta = ctx.meta;
  const [series, fc] = await Promise.all([
    api.series(id, 180),
    api.forecast(id).catch((e) => (e.code === 'not_found' ? null : Promise.reject(e))),
  ]);
  const cmp = await api.compare(id, 'state').catch(() => null);
  const e = series.entity;
  const pts = series.points || [];
  const last = pts[pts.length - 1] || {};
  const { local } = commodityInfo(e.commodity);

  // --- header + latest report -----------------------------------------------------------
  view.append(backLink('#/home'),
    h('div', { class: 'c-head' }, pictogram(e.commodity, 56),
      h('div', {}, pageTitle(local ? local : e.commodity), local ? h('p', { class: 'cname-en', lang: 'en' }, e.commodity) : null,
        h('p', { class: 'muted' }, t('common.variety', { variety: [e.variety, e.grade].filter(Boolean).join(' · ') || '–' })),
        h('p', { class: 'muted' }, t('common.place', { market: e.market, district: e.district, state: e.state })))),
    h('section', { class: 'card', 'aria-labelledby': 'lr-h' },
      h('h2', { class: 'h3', id: 'lr-h' }, t('commodity.latest')),
      h('p', { class: 'big-price' }, h('span', { class: 'muted small' }, t('price.modal')), h('br'), price(last.modal)),
      dl([[t('price.min'), price(last.min)], [t('price.max'), price(last.max)]]),
      freshLine(series.freshness, meta)));

  // --- decision card (C) ----------------------------------------------------------------
  if (fc) view.append(decisionCard(fc, e, cmp, meta));

  // --- chart + summary (B) ---------------------------------------------------------------
  const hs = fc && fc.supported ? [...fc.horizons].sort((a, b) => HORIZON_ORDER.indexOf(a.horizon) - HORIZON_ORDER.indexOf(b.horizon)) : [];
  const chartBox = h('div', { class: 'chart-box' });
  import('../chart.js').then(({ priceChart }) => chartBox.append(priceChart(pts, hs.length ? { origin: fc.origin, horizons: hs } : null,
    { label: t('commodity.chart_label'), fmtPrice: rupees, fmtDate: date }))).catch(() => {});
  const first = pts.find((p) => p.modal != null);
  const lastH = hs[hs.length - 1];
  view.append(h('section', { class: 'card', 'aria-labelledby': 'ch-h' },
    h('h2', { class: 'h2', id: 'ch-h' }, t('commodity.chart_title')),
    chartBox,
    h('ul', { class: 'legend', 'aria-hidden': 'true' },
      h('li', {}, h('i', { class: 'lg lg-hist' }), t('commodity.legend_history')),
      hs.length ? [h('li', {}, h('i', { class: 'lg lg-med' }), t('commodity.legend_median')),
        h('li', {}, h('i', { class: 'lg lg-b80' }), t('commodity.legend_band80')),
        h('li', {}, h('i', { class: 'lg lg-b90' }), t('commodity.legend_band90'))] : null),
    h('h3', { class: 'h3' }, t('commodity.summary_title')),
    first ? h('p', {}, t('commodity.summary_history', { n: num(pts.length), from_date: date(first.date), to_date: date(last.date), from: price(first.modal), to: price(last.modal) })) : null,
    h('p', {}, lastH ? t('commodity.summary_forecast', { days: num(lastH.days), median: price(lastH.median), lo: price(lastH.lo80), hi: price(lastH.hi80) }) : t('commodity.summary_none'))));

  // --- horizons --------------------------------------------------------------------------
  if (fc && !fc.supported) {
    view.append(h('section', { class: 'card notice' }, h('h2', { class: 'h3' }, icon('info'), ' ', t('commodity.no_forecast')),
      h('p', {}, t('unsupported.' + (fc.unsupported_reason || 'insufficient_history')))));
  } else if (hs.length) {
    view.append(h('section', { class: 'card' }, h('h2', { class: 'h2' }, t('commodity.horizons')),
      h('ul', { class: 'plain hz' }, hs.map((x) => h('li', { class: 'hz-row' },
        h('h3', { class: 'h3' }, t('horizon.' + x.horizon)),
        x.target_window ? h('p', { class: 'muted small' }, t('commodity.target', { from: date(x.target_window[0]), to: date(x.target_window[1]) })) : null,
        dl([[t('commodity.median'), price(x.median)],
          [t('commodity.range80'), `${rupees(x.lo80)} – ${rupees(x.hi80)}`],
          x.lo90 != null ? [t('commodity.range90'), `${rupees(x.lo90)} – ${rupees(x.hi90)}`] : null,
          [t('commodity.change'), pct(x.change_pct)]]),
        h('p', { class: 'small' }, t('commodity.accuracy', { mae: pct(x.test_mae_pct_of_price, false), cov: num(coveragePer100(x.interval_coverage80_test)) })),
        x.test_rel_mae_vs_persistence != null ? h('p', { class: 'small muted' }, t('commodity.vs_naive', { ratio: num(x.test_rel_mae_vs_persistence, 2) })) : null)))));
  }

  // --- trend, volatility, explanation -----------------------------------------------------
  const s = series.summary || {};
  const ex = (fc && fc.explanation) || {};
  view.append(h('section', { class: 'card' }, h('h2', { class: 'h2' }, t('commodity.trend')),
    h('p', { class: 'note-hist' }, t('alerts.note')),
    s.trend ? h('p', { class: 'big-trend' }, icon(s.trend === 'rising' ? 'up' : s.trend === 'falling' ? 'down' : 'flat'), ' ', t('trend.' + s.trend)) : null,
    dl([s.change_30d_pct != null ? [t('commodity.change_30d'), pct(s.change_30d_pct)] : null,
      s.volatility_level ? [t('commodity.volatility'), t('commodity.volatility_value', { level: t('vol.' + s.volatility_level), pct: pct(s.volatility_30d_pct, false) })] : null,
      s.n_obs_30d != null ? [t('commodity.reports_30d'), num(s.n_obs_30d)] : null]),
    ex.seasonal_last_year_change_pct != null ? h('p', {}, t('commodity.seasonal', { pct: pct(ex.seasonal_last_year_change_pct) })) : null,
    ex.markets_moving_same_way_pct != null ? h('p', {}, t('commodity.markets_same', { pct: pct(ex.markets_moving_same_way_pct, false) })) : null));

  // --- warnings ----------------------------------------------------------------------------
  if (fc && fc.warnings && fc.warnings.length) {
    view.append(h('section', { class: 'card notice notice-warn', 'aria-labelledby': 'w-h' },
      h('h2', { class: 'h3', id: 'w-h' }, icon('warn'), ' ', t('commodity.warnings')),
      h('ul', {}, fc.warnings.map((w) => h('li', {}, t('warning.' + w))))));
  }

  // --- provenance ---------------------------------------------------------------------------
  if (fc) {
    const src = fc.source || (meta && meta.source) || {};
    view.append(h('section', { class: 'card' }, h('h2', { class: 'h3' }, t('commodity.about')),
      dl([[t('commodity.model'), [...new Set(hs.map((x) => x.model).filter(Boolean))].join(', ') || '–'],
        [t('commodity.source'), src.name || '–'], src.licence ? [t('commodity.licence'), src.licence] : null,
        [t('commodity.version'), fc.model_version || (meta && meta.model_version) || '–'],
        meta && meta.generated_at ? [t('commodity.generated'), dateTime(meta.generated_at)] : null])));
  }
  view.append(h('a', { class: 'btn btn-ghost btn-block', href: '#/compare/' + encodeURIComponent(id) }, icon('compare'), t('common.compare_markets')));
}

// ------------------------------------------------------------------------------------------
function decisionCard(fc, e, cmp, meta) {
  const d = fc.decision || {};
  const perishable = d.costs && typeof d.costs.perishable === 'boolean' ? d.costs.perishable : PERISHABLE.has(e.commodity);
  const saved = store.load('costs', {}) || {};
  const defWeekly = defaultWeeklyPct(perishable);
  let weekly = +(perishable ? saved.perishable : saved.durable) || defWeekly;
  let transport = +saved.transport || 0;
  // the rule is evaluated on the primary horizon only (conf/decision_rules.json)
  const hz = (fc.horizons || []).find((x) => x.horizon === RULES.primaryHorizon) || null;
  const expired = isExpired(hz, meta);

  const card = h('section', { class: 'card decision', 'aria-labelledby': 'dc-h' });
  const body = h('div', { 'aria-live': 'polite' });
  const wIn = h('input', { id: 'c-week', class: 'input', type: 'number', inputmode: 'decimal', min: 0, max: 50, step: 0.5, value: weekly });
  const tIn = h('input', { id: 'c-trans', class: 'input', type: 'number', inputmode: 'numeric', min: 0, max: 100000, step: 10, value: transport });

  function draw() {
    const r = decide({ today: fc.origin ? fc.origin.modal_price : null, horizon: hz, supported: fc.supported && !!hz,
      unsupportedReason: fc.unsupported_reason, stale: !!(fc.freshness && fc.freshness.stale), expired, perishable,
      weeklyPct: weekly, transportPerQ: transport, compareItems: cmp ? cmp.items : [] });
    const days = hz ? hz.days : 7;
    const custom = weekly !== defWeekly || transport !== 0;
    const ev = [];
    if (hz && fc.origin) {
      ev.push(t('decision.ev_interval', { days: num(days), lo: price(hz.lo80), hi: price(hz.hi80), today: price(fc.origin.modal_price) }));
      if (r.costPct != null) {
        ev.push(t('decision.ev_cost', { days: num(days), pct: pct(r.costPct, false), amount: rupees(fc.origin.modal_price * r.costPct / 100) }));
        ev.push(t('decision.ev_need', { need: price(r.needPrice) }));
      }
      ev.push(t('decision.ev_accuracy', { mae: pct(hz.test_mae_pct_of_price, false), cov: num(coveragePer100(hz.interval_coverage80_test)) }));
    }
    if (r.best) ev.push(t('decision.ev_compare', { market: r.best.item.entity.market, price: price(r.best.item.modal_price), diff: pct(r.best.gainPct) }));
    if (fc.freshness) ev.push(t('decision.ev_fresh', { date: date(fc.freshness.last_date) }));
    put(body, 
      h('div', { class: 'signal sig-' + r.signal },
        icon(SIG_ICON[r.signal], 'ic sig-ic'),
        h('div', {}, h('p', { class: 'sig-name' }, t('signal.' + r.signal)),
          h('p', { class: 'sig-text' }, t('signal_text.' + r.signal, { days: num(days) })))),
      custom ? h('p', { class: 'tag tag-info' }, t('decision.with_your_costs')) : null,
      d.signal && d.signal !== r.signal ? h('p', { class: 'small muted' }, t('decision.server_signal', { signal: t('signal.' + d.signal) })) : null,
      !fc.supported && fc.unsupported_reason ? h('p', {}, t('unsupported.' + fc.unsupported_reason)) : null,
      h('ul', { class: 'reasons' }, r.reasons.map((c) => h('li', {}, t('reason.' + c)))),
      r.snapshot ? h('p', { class: 'small muted snapshot' }, t('decision.at_snapshot',
        { date: date(fc.origin && fc.origin.date), signal: t('signal.' + r.snapshot.signal) })) : null,
      r.signal === 'COMPARE' ? h('a', { class: 'btn btn-primary', href: '#/compare/' + encodeURIComponent(e.entity_id) }, icon('compare'), t('common.compare_markets')) : null,
      h('details', { class: 'why' }, h('summary', {}, t('decision.why')), h('ul', {}, ev.map((x) => h('li', {}, x)))));
  }

  const apply = (ev) => {
    ev.preventDefault();
    weekly = Math.min(50, Math.max(0, +wIn.value || 0));
    transport = Math.min(100000, Math.max(0, +tIn.value || 0));
    const s = store.load('costs', {}) || {};
    s[perishable ? 'perishable' : 'durable'] = weekly; s.transport = transport;
    store.save('costs', s);
    draw();
  };
  const reset = () => { weekly = defWeekly; transport = 0; wIn.value = weekly; tIn.value = 0; const s = store.load('costs', {}) || {}; delete s[perishable ? 'perishable' : 'durable']; delete s.transport; store.save('costs', s); draw(); };

  card.append(
    h('h2', { class: 'h2', id: 'dc-h' }, t('decision.title')),
    h('p', { class: 'kind' }, icon('info'), ' ', t('decision.kind')),
    body,
    h('details', { class: 'costs' }, h('summary', {}, t('decision.costs_title')),
      h('form', { onsubmit: apply },
        h('div', { class: 'field' }, h('label', { class: 'label', for: 'c-week' }, t('decision.holding_cost')), wIn,
          h('p', { class: 'help' }, t('decision.holding_help', { pct: pct(defWeekly, false) }), ' ', t('decision.fixed_help', { pct: pct(RULES.fixedPct, false) }))),
        h('div', { class: 'field' }, h('label', { class: 'label', for: 'c-trans' }, t('decision.transport_cost')), tIn),
        h('div', { class: 'row-btns' }, h('button', { class: 'btn btn-secondary', type: 'submit' }, t('decision.apply')),
          h('button', { class: 'btn btn-ghost', type: 'button', onclick: reset }, t('decision.reset'))))),
    h('p', { class: 'small muted' }, t('decision.disclaimer')));
  draw();
  return card;
}
