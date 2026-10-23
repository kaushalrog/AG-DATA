// Hand-written SVG chart: past modal prices + forecast median with 90% and 80% bands.
// Lazy-loaded only on the commodity screen. The chart is decorative-plus: a text summary
// with the same information is always rendered next to it.
const NS = 'http://www.w3.org/2000/svg';
const el = (tag, attrs) => {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
};
const day = (iso) => Date.parse(iso + 'T00:00:00Z') / 864e5;

/**
 * @param {Array} points  [{date, modal}]
 * @param {object|null} fc  {origin:{date, modal_price}, horizons:[{days, median, lo80, hi80, lo90, hi90}]}
 * @param {object} o  {label, fmtPrice(n), fmtDate(iso)}
 */
export function priceChart(points, fc, o) {
  const W = 340, H = 190, L = 6, R = 6, T = 22, B = 24;
  const hist = points.filter((p) => p.modal != null);
  const hs = fc && fc.horizons && fc.horizons.length ? fc.horizons : [];
  const o0 = fc && fc.origin ? fc.origin : hist.length ? { date: hist[hist.length - 1].date, modal_price: hist[hist.length - 1].modal } : null;
  const xs = hist.map((p) => day(p.date));
  const ys = hist.map((p) => p.modal);
  if (o0) { xs.push(day(o0.date)); ys.push(o0.modal_price); }
  hs.forEach((h) => { xs.push(day(o0.date) + h.days); ys.push(h.lo90 ?? h.lo80 ?? h.median, h.hi90 ?? h.hi80 ?? h.median); });
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, class: 'chart', role: 'img', 'aria-label': o.label });
  if (xs.length < 2) return svg;
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  let y0 = Math.min(...ys), y1 = Math.max(...ys);
  const pad = (y1 - y0) * 0.08 || y1 * 0.05 || 1; y0 -= pad; y1 += pad;
  const X = (d) => L + ((d - x0) / (x1 - x0 || 1)) * (W - L - R);
  const Y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  const f = (n) => n.toFixed(1);

  // grid: 3 horizontal lines with price labels
  for (let i = 0; i <= 2; i++) {
    const v = y0 + ((y1 - y0) * (2 - i)) / 2;
    svg.append(el('line', { x1: L, x2: W - R, y1: f(Y(v)), y2: f(Y(v)), class: 'c-grid' }));
    const tx = el('text', { x: L + 2, y: f(Y(v) - 4), class: 'c-lbl' }); tx.textContent = o.fmtPrice(v); svg.append(tx);
  }
  if (hs.length && o0) {
    const ox = day(o0.date);
    const band = (lo, hi, cls) => {
      const pts = [[ox, o0.modal_price], ...hs.map((h) => [ox + h.days, h[hi]])];
      const back = [...hs].reverse().map((h) => [ox + h.days, h[lo]]);
      svg.append(el('polygon', { class: cls, points: [...pts, ...back, [ox, o0.modal_price]].map(([a, b]) => `${f(X(a))},${f(Y(b))}`).join(' ') }));
    };
    if (hs.every((h) => h.lo90 != null && h.hi90 != null)) band('lo90', 'hi90', 'c-b90');
    band('lo80', 'hi80', 'c-b80');
    svg.append(el('line', { x1: f(X(ox)), x2: f(X(ox)), y1: T, y2: H - B, class: 'c-now' }));
    svg.append(el('polyline', { class: 'c-med', points: [[ox, o0.modal_price], ...hs.map((h) => [ox + h.days, h.median])].map(([a, b]) => `${f(X(a))},${f(Y(b))}`).join(' ') }));
    hs.forEach((h) => svg.append(el('circle', { cx: f(X(ox + h.days)), cy: f(Y(h.median)), r: 3, class: 'c-dot' })));
  }
  if (hist.length > 1) svg.append(el('polyline', { class: 'c-hist', points: hist.map((p) => `${f(X(day(p.date)))},${f(Y(p.modal))}`).join(' ') }));
  const d0 = el('text', { x: L, y: H - 6, class: 'c-lbl' }); d0.textContent = o.fmtDate(new Date(x0 * 864e5).toISOString().slice(0, 10));
  const d1 = el('text', { x: W - R, y: H - 6, class: 'c-lbl', 'text-anchor': 'end' }); d1.textContent = o.fmtDate(new Date(x1 * 864e5).toISOString().slice(0, 10));
  svg.append(d0, d1);
  return svg;
}
