# AG-DATA farmer app (PWA)

A mobile-first, installable, low-memory Progressive Web App that shows mandi prices, how fresh they
are, and a cautious **market outlook** (SELL / HOLD / WATCH / COMPARE) built on the AG-DATA API
(`docs/API.md`). Plain HTML + CSS + vanilla ES modules: no framework, no npm runtime dependencies,
no CDN, no build step.

## Run it

| Mode | Command | What you get |
|---|---|---|
| Static demo | `python3 -m http.server -d app 8080` then open <http://localhost:8080/> | `/api/v1/*` returns 404 HTML, so the app falls back to `demo/` and shows a **Demo snapshot** badge |
| Production | served by the FastAPI backend at `/` with the API at `/api/v1` on the same origin | live/archived data; service worker caches the shell and the last good API responses |
| Other API host | edit `<meta name="agri-api-base" content="…">` in `index.html` (no rebuild) | the backend must allow the origin via `AGRI_API_CORS_ORIGINS` |

Service workers need `https://` or `localhost`.

## Structure

```
app/
  index.html            app shell, inline SVG UI-icon sprite, bottom navigation
  config.js             API_BASE (default /api/v1, overridable by <meta name="agri-api-base">)
  manifest.webmanifest  install metadata (192/512 PNG icons, maskable)
  sw.js                 service worker (versioned caches, see "Offline")
  offline.html          fallback page if the shell itself is not cached
  css/app.css           all styles, system fonts only
  js/app.js             bootstrap + hash router; every screen is loaded with dynamic import()
  js/api.js             API client, cache marker handling, demo loader (reads demo/index.json only)
  js/i18n.js            dictionary loading, t(), localised price/date/percent helpers
  js/format.js          pure formatting (Intl.NumberFormat('<lang>-IN'), Intl.DateTimeFormat)
  js/decision.js        pure copy of the decision rule (docs/API.md, conf/decision_rules.json)
  js/store.js           localStorage wrapper (every access in try/catch)
  js/ui.js              DOM helpers (textContent only), banners, rows, error/empty states
  js/chart.js           hand-written SVG chart, lazy-loaded on the commodity screen only
  js/routes/*.js        home, commodity, compare, markets, alerts, guide, settings, onboarding
  i18n/<lang>.json      en, ta, te, ml, hi, kn — identical key sets (tested)
  i18n/commodities.json localised labels for the 36 panel commodities + pictogram mapping
  icons/                app icons + 20 original commodity pictograms (see ASSETS.md)
  demo/                 PLACEHOLDER demo snapshot (see demo/README.md)
  tools/                make_icons.py (PNG icons, stdlib only), make_demo.py (placeholder data)
  tests/                node --test suite (see tests/README.md)
```

Routes: `#/home`, `#/commodity/<entity_id>`, `#/compare/<entity_id>`, `#/markets`, `#/alerts`,
`#/guide`, `#/guide/<topic>`, `#/settings` (and `#/welcome` for first-launch onboarding).

## Budgets (measured)

* Shipped JS: **18 files, ~69 KB uncompressed** (budget 80 KB, enforced by `tests/static.test.mjs`).
  First screen (home) loads ~29 KB of JS; the chart module and all other screens are lazy.
* CSS ~16 KB. One i18n file ~30–45 KB is fetched at a time (Indian scripts are 3 bytes/char in UTF-8).
* No images on the first screen other than 3–5 small SVG pictograms (lazy `<img>`), no web fonts.
* The service worker precaches the whole shell including all six dictionaries (~200 KB) so any
  language works offline. If that is too heavy for target users, precache only `en` + the chosen
  language.

## Data honesty rules implemented

* A prominent banner whenever `meta.days_since_data > 3`, with the newest report date; for
  `data_origin: "archive"` it says it is a historical snapshot. The app never says "live"/"today".
* Every price shows its report date. `freshness.days_old` is relative to `meta.data_as_of`, so when the
  whole dataset is old the wording is "N days older than the newest report in this data", not "N days old".
* The decision card is labelled "market outlook, not a profit guarantee", uses "may be worth
  considering" wording, shows its evidence under "Why am I seeing this?", and lets the farmer edit
  holding cost (% per week) and transport (₹/quintal). The card is recomputed client-side with
  `js/decision.js` from the returned `lo80/hi80`; if the result differs from the server's card, the
  server's default-cost signal is also shown.
* Comparison: stale / `comparable:false` markets are always listed after fresh ones and visibly
  marked "Not comparable (older report)".
* Alerts and trends are labelled as past measurements, not forecasts.
* Charts are never the only carrier of information: a text summary is always shown.

## Offline

* Shell: precached and cache-first; bump `VERSION` in `sw.js` on every release (old `agri-*` caches are
  deleted on activate).
* `GET …/api/…`: network-first with a 5 s timeout; good JSON responses are saved with their save time.
  On failure the saved copy is returned with `X-From-Cache: <ISO time>` and the app shows
  "Offline – showing saved data from …". Non-GET requests and error responses are never cached.
* If the API is unreachable and nothing was served from cache, the app loads the demo snapshot.

## i18n process

1. Add/change a key in `i18n/en.json`, then add the same key to **all** of `ta te ml hi kn`.
2. Keep `{placeholder}` tokens identical (the tests compare them). Never concatenate translated
   fragments in code; use one full sentence per key.
3. API codes (signals, reason codes, warnings, unsupported reasons, alert types, errors) are mapped by key
   name (`signal.HOLD`, `reason.<code>`, `warning.<code>` …); `tests/i18n.test.mjs` parses `docs/API.md` and
   fails if a code has no key.
4. Commodity names: the English name from the data is always shown; a localised label only comes from
   `i18n/commodities.json`. Unknown commodities show English only.
5. All non-English text is AI-drafted and **provisional** (`"_status": "provisional-ai"`); see
   `i18n/TRANSLATION_STATUS.md`.

Number note: some ICU builds format `ml-IN`/`kn-IN` with Western grouping (150,000). `js/format.js`
detects this and falls back to `en-IN` grouping (1,50,000) with the same Latin digits.

## Accessibility & low-end devices

* ≥ 48 px touch targets (measured in-browser for all screens), base font 16 px, "Large text" option (125 %).
* Colour pairs chosen for WCAG AA (green `#1f6b3a` on white ≈ 6.6:1, body `#1b261d`, muted `#4a5548` ≈ 7:1);
  signals use icon + colour + text, never colour alone.
* Landmarks (`header`, `main`, `nav`), skip link, visible focus ring, `aria-live` for status/banners/
  loading, focus moves to the page heading on navigation, `lang` set on `<html>`.
* `prefers-reduced-motion` disables the only animation (spinner); `forced-colors` keeps borders.
* Works at 320 px with no horizontal scroll; long Tamil/Malayalam strings wrap (checked at 320 px for
  all screens in ta, te, ml, hi, kn).
* All API text is inserted with `textContent` (no `innerHTML`), checked by a static test.

## Known limitations / not done

* **Not tested on a physical low-end (4 GB) Android phone**, nor with TalkBack/VoiceOver. Tested only in a
  desktop Chromium-based embedded browser with mobile viewport emulation (375 px and 320 px).
* The service worker could not be exercised in that embedded browser (it blocks SW registration); its
  caching policy is covered by `tests/sw.test.mjs` with mocked `caches`/`fetch` only. Verify install +
  offline in real Chrome/Android before release.
* Translations are provisional AI drafts and need native-speaker agricultural review.
* `/markets` and `/commodities` response shapes are only described as "paged" in `docs/API.md`; the app
  accepts either an array or `{items: [...]}` with `state`, `district`, `market` fields.
* `/compare` is requested with `scope=state` for the decision card so district and state markets are both
  considered; the server's exact COMPARE scope may differ.
* Bottom-navigation labels in Malayalam/Kannada wrap onto two lines at 320 px.
* Demo files are synthetic placeholders until replaced with an export of real archived data.
