# Tests

Run from the repository root (Node 24, no installs):

```
node --test app/tests/
```

`index.js` makes the directory form work by loading every `*.test.mjs`; `node --test app/tests/*.test.mjs`
also works.

| File | Checks |
|---|---|
| `i18n.test.mjs` | identical key sets in en/ta/te/ml/hi/kn, `_status: provisional-ai`, no empty strings, identical `{placeholder}` tokens, native script present, every signal/reason/warning/unsupported/alert/error code has a key (also parsed from `docs/API.md`), 10 guide topics × 4 strings, 36 commodity labels × 5 languages + icon files |
| `decision.test.mjs` | the client decision rule against `docs/API.md` (HOLD / SELL / COMPARE / WATCH, thresholds, precedence, transport, stale/unsupported), defaults equal `conf/decision_rules.json`, the rule reproduces every demo decision card, compare ordering never ranks stale above fresh |
| `format.test.mjs` | ₹ with Indian grouping in all six locales, signed percents, calendar dates without timezone shift, freshness wording for old datasets |
| `demo.test.mjs` | every demo file conforms to the API contract; `index.json` lists exactly the files present |
| `static.test.mjs` | every static/dynamic import exists, shipped JS < 80 KB, chart and routes are lazy, SW precache list matches shipped files, manifest + PNG icon sizes, every literal i18n key used in code exists, no external URLs, no `innerHTML` |
| `sw.test.mjs` | service worker in a VM with mocked `caches`/`fetch`: network-first + `X-From-Cache`, no caching of errors or non-GET, JSON 404 not masked, versioned cache cleanup, offline navigation fallback |

## Manual browser checks (before a release)

Serve statically: `python3 -m http.server -d app 8080`, open http://localhost:8080/ in Chrome with
DevTools device emulation (and ideally on a real low-end Android phone).

1. **Onboarding**: first launch shows the language grid in native scripts; choose தமிழ், pick a state,
   Continue. Reload: the language persists; `<html lang="ta">`.
2. **Demo + stale banners**: with no backend, a blue "Demo snapshot" badge and an amber "These are not
   today's prices" banner (newest report date + "historical snapshot") appear on every screen.
3. **Home**: state/district/market selectors filter the list; search "tom" finds Tomato; each row shows
   price "₹2,000 / quintal", the report date and an "Older report" tag when stale; movers and the alerts teaser show.
4. **Commodity** (`#/commodity/-7212340012345`): chart with 80 %/90 % bands **and** a text summary;
   four horizon rows with accuracy sentences; trend/volatility; warnings; model/source/version.
5. **Decision card**: HOLD with icon + text; open "Your costs", set holding 10 % → the card changes to
   WATCH and says "Worked out with your costs" plus the default-cost signal; "Use default costs" restores
   it. Kolar tomato (`#/commodity/8801234500001`) shows COMPARE; transport ₹200 → WATCH.
6. **Compare** (`#/compare/-7212340012345`): Mettur (9 days old) is last and marked "Not comparable (older
   report)"; entering a transport cost shows "after transport" percentages.
7. **Alerts**: note says these are past measurements, not forecasts; type labels (sudden rise/fall,
   possible data error).
8. **Guide**: 10 topics, each with pictogram and 3 short paragraphs, in every language.
9. **Settings**: change language, default state, costs; Large text enlarges everything; Clear saved data
   returns to onboarding on next navigation.
10. **Layout**: at 320 px width no horizontal scroll in any language (Malayalam and Tamil are the longest);
    all buttons ≥ 48 px; keyboard Tab shows a visible focus ring; with reduced motion the spinner is static.
11. **PWA** (needs a real browser with SW support, on `localhost` or HTTPS, with the backend): Lighthouse
    "installable"; Install button appears (Chrome); load a commodity, go offline (DevTools → Network →
    Offline), reload → app opens and shows "Offline – showing saved data from …"; bump `VERSION` in `sw.js`
    and check old caches are deleted.
12. **Screen reader** (TalkBack / VoiceOver): page heading announced on navigation; banners and loading
    are announced; pictograms are silent; the chart has a label and the summary is read.
