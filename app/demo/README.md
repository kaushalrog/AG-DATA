# Demo snapshot (real archived data)

The app loads these files **only** when the API is unreachable **and** nothing was served from the service-worker cache in this session. The UI then shows a "Demo snapshot" badge on every screen.

* **What it is.** These files are **real AGMARKNET reports** (official data.gov.in records up to 2026-10-22), exported from the gold layer of experiment `fc_main_v3` by `py/agri/analysis/export_demo.py`. Every file is exactly the response the real API returned.
* **Coverage.** Data as of 2026-10-22; forecast series across 10 states, plus latest prices, markets, alerts and Tamil Nadu trends.
* **Labelling.** `meta.json` says `data_origin: "official"` with the data date. Once the snapshot is more than 3 days old, the app shows the stale-data banner, and decision cards switch to `WATCH / forecast_expired`, with the outlook on the data date shown as history only.
* **Licence.** GODL-India, with AGMARKNET attribution in `meta.json`.

Regenerate after a new publish:

```bash
PYTHONPATH=py .venv/bin/python -m agri.analysis.export_demo --per-state 8
node --test app/tests/
```

## Contract
* Each file is the exact JSON body of the API endpoint (`docs/API.md`). The loader reads only `index.json` to discover files.
* Per-entity files are named `series_<id>.json`, `forecast_<id>.json` and `compare_<id>.json`.
* `prices_latest`, `markets` and `alerts` are filtered and paged on the client. `trends.json` holds one state.
* `app/tools/make_demo.py` can still generate **synthetic** placeholders for offline development. Those carry `"_demo_placeholder": true`, and `demo.test.mjs` enforces that flag whenever the index does not declare a real export.
