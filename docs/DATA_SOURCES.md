# AG-DATA — Data Sources Register

**Checked on:** 2026-10-22 (all "accessible" statements refer to this date).
**Method:** live HTTP requests (`curl`) and web research. No API key was used. Where a fact
could not be confirmed from a primary source it is marked **UNVERIFIED** with the reason.

## Purpose

This file records where AG-DATA's mandi price data comes from, how it can be refreshed, and
what each source allows. It covers the two Kaggle archives already in `data/raw/`, the
official Government of India sources behind them, and optional weather and crop-calendar
sources. Measured facts about the local files (row counts, date ranges, quality classes) are
taken from `PROJECT_STATUS.md` §3.2–3.5 and are attributed to it.

## Summary registry

| # | Source | Owner | Access | Auth | Licence | Historical? | Role in AG-DATA | Status 2026-10-22 |
|---|---|---|---|---|---|---|---|---|
| 1 | AGMARKNET 2.0 portal | DMI, Ministry of Agriculture & FW | Web UI, reports | None for public pages | Site terms not retrievable (UNVERIFIED) | Yes (via UI) | Upstream origin of all price data | Reachable (SPA) |
| 2 | data.gov.in "Current Daily Price … (Mandi)" `9ef84268-…` | MoA&FW / DA&FW via OGD (NIC) | REST API | API key | GODL-India | Not confirmed (see §2) | Incremental adapter | Reachable; 400 without key |
| 3 | data.gov.in "Variety-wise Daily Market Prices Data of Commodity" `35985678-…` | MoA&FW / DA&FW / DMI via OGD | REST API | API key | GODL-India | Likely (UNVERIFIED range) | Candidate backfill / upstream of #5a | Reachable; 400 without key |
| 4 | e-NAM | SFAC / DA&FW | Web dashboards | None found | UNVERIFIED | UNVERIFIED | Not used | Reachable |
| 5a | Kaggle "Daily Market Prices of Commodity India (2001-2026)" | Manas Khandelwal | Kaggle download | Kaggle account | GODL-India (per description) | Yes, 2001-01-10 … 2026-04-21 | **Primary historical source** | Local copy matches v134 file sizes (52 files; hashes not compared) |
| 5b | Kaggle "India Commodity Wise Mandi Dataset" | Vandeet Shah | Kaggle download | Kaggle account | Apache 2.0 (as labelled on Kaggle) | Yes, 2000-10-19 … 2024-02-02 | Secondary / arrivals enrichment | Local copy matches v1 file sizes (325 files; hashes not compared) |
| 6a | IMD gridded rainfall (0.25°) | IMD Pune | File download | None | Non-commercial reproduction only without permission | 1901–2024 | Not used | Reachable |
| 6b | Open-Meteo Historical Weather API | Open-Meteo | REST API | None (free tier) | CC BY 4.0 (data); free tier non-commercial | 1940– | Optional weather features | Tested OK |
| 6c | NASA POWER Daily API | NASA LaRC | REST API | None | No formal restriction stated; citation required | Yes | Alternative weather | Tested OK |
| 7a | DES harvesting-season appendices | DES, MoA&FW | PDF | None | UNVERIFIED | Static tables | Seasonality reference | Reachable |
| 7b | FAO GIEWS India country brief / FAO Crop Calendar | FAO | Web/PDF | None | FAO datasets CC BY 4.0 (general terms) | Narrative | Seasonality reference | Reachable |

Env var for the data.gov.in key: **`AGRI_DATA_GOV_IN_API_KEY`** (not present anywhere in the repo
today; no key is committed).

---

## 1. AGMARKNET (agmarknet.gov.in)

- **Official name:** Agricultural Marketing Information Network (AGMARKNET), now "Agmarknet 2.0".
- **Owner:** Directorate of Marketing and Inspection (DMI), Department of Agriculture and
  Farmers Welfare, Ministry of Agriculture and Farmers Welfare (owner as listed in the
  data.gov.in catalog that cites AGMARKNET as its source).
- **What we observed:** `https://agmarknet.gov.in/` returns a React single-page app titled
  "Agmarknet 2.0". The front-end bundle sets `REACT_APP_GO_LIVEDATE:"2025-11-07"` and an API
  base `https://api.agmarknet.gov.in/v1/`. That API is the portal's internal back end
  (uses access/refresh tokens for logged-in workflows); **no public documentation for it was
  found**, so it is not treated as a supported data endpoint and was not called.
- **Public report pages** (from `https://agmarknet.gov.in/sitemap.xml`):
  `/pricearrivalreportlist`, `/daily-price-and-arrival-report`, `/alltypeofreports`,
  `/termsconditions`, `/copyrightpolicy`, `/disclaimer`.
- **robots.txt:** `Allow: /` for all agents; disallows only sign-in, data-entry, admin and
  helpdesk paths. robots.txt is not a licence.
- **Terms / licence:** **UNVERIFIED** — `/termsconditions` and `/copyrightpolicy` are rendered
  client-side; their text could not be retrieved without executing JavaScript.
- **Units:** the bundle's data-entry form labels "Price unit (₹/quintal)" and quantity in
  "Quintals". This is UI text, not a published data dictionary.
- **Automated collection permitted?** **UNVERIFIED.** Use the data.gov.in API (§2/§3) instead
  of scraping the portal.
- **Historical retrievability:** via UI reports; bulk export not confirmed.

## 2. data.gov.in — "Current Daily Price of Various Commodities from Various Markets (Mandi)"

- **Resource id: `9ef84268-d588-465a-a308-a864a43d0070`** — confirmed in the resource page
  (`https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi`)
  and in the live metadata API.
- **Catalog:** uuid `6141ea17-a69d-4713-b600-0a43c8fd9a6c`,
  `/catalog/current-daily-price-various-commodities-various-markets-mandi`.
- **Owner:** Ministry of Agriculture and Farmers Welfare → Department of Agriculture and Farmers
  Welfare → Directorate of Marketing and Inspection (DMI). Sector: Agriculture / Agricultural
  Marketing. Jurisdiction: All India. Platform hosted by NIC, MeitY.
- **Description (page):** wholesale maximum, minimum and modal price on a daily basis,
  "generated through the AGMARKNET Portal".
- **Endpoint:**
  `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=$AGRI_DATA_GOV_IN_API_KEY&format=json&limit=<n>&offset=<n>&filters[<field>]=<value>`
  (`format` also accepts `csv`/`xml`; the page's own download link uses `offset=0&limit=all`).
- **Auth:** API key required. Observed responses without a valid key:

  | Request | HTTP | Body |
  |---|---|---|
  | no `api-key` | 400 | `{"error": "Authorization field missing"}` |
  | `api-key=INVALID` | 403 | `{"error": "Key not authorised"}` |

  A personal key is generated from the data.gov.in "My Account" page after registration
  (third-party guides; official page is JS-rendered). The resource page embeds a public
  **sample key** in its download URL. It was **not used** and is not recorded here; its
  limits are **UNVERIFIED** (no official statement found).
- **Schema (confirmed live, unauthenticated metadata endpoint**
  `https://api.data.gov.in/lists?format=json&filters[index_name]=9ef84268-d588-465a-a308-a864a43d0070`**):**

  | Display name | API field id | Type |
  |---|---|---|
  | State | `state` | keyword |
  | District | `district` | keyword |
  | Market | `market` | keyword |
  | Commodity | `commodity` | keyword |
  | Variety | `variety` | keyword |
  | Grade | `grade` | keyword |
  | Arrival_Date | `arrival_date` | date |
  | Min_x0020_Price | `min_price` | double |
  | Max_x0020_Price | `max_price` | double |
  | Modal_x0020_Price | `modal_price` | double |

  Filterable (`field_exposed`): `state.keyword`, `district`, `market`, `commodity`, `variety`,
  `grade`. Note the filter id for state is `state.keyword`; an adapter should try
  `filters[state.keyword]` and fall back to `filters[state]` (UNVERIFIED which works).
  No `commodity_code` and **no arrivals/quantity field**.
- **Metadata timestamps:** created 2021-08-02T21:19:28Z; `updated_date` 2026-10-22T17:00:51Z
  (i.e. refreshed on the day of checking). Page `published_date` 1369290300 (2013-05-23).
- **Response envelope:** the `/lists` endpoint (same OGD API, v2.2.0) returned
  `{message, version, status:"ok", total, count, limit, offset, records:[…], params}`.
  For `/resource/<id>` the data rows are expected under `records` with
  `total`/`count`/`limit`/`offset` (third-party guide, OGD convention). The exact `/resource`
  envelope is **UNVERIFIED** without a key.
- **Current-day only / no history?** **UNVERIFIED.** The title says "Current Daily Price" and the
  index is refreshed daily, which is consistent with a rolling current snapshot, but this
  cannot be proven without querying `arrival_date` ranges with a key. Treat as
  snapshot-only; persist every pull.
- **Rate limits:** **UNVERIFIED.** No official figure found. Third-party guides disagree
  ("1,000 requests/day" vs "no published limit"; "max 100 per page on most datasets").
  Adapter should page with modest `limit`, sleep between calls, and back off on 429/5xx.
- **Licence:** Government Open Data License – India (GODL-India), stated in the portal footer
  ("licensed under the Government Open Data License-India"). GODL permits commercial and
  non-commercial use, adaptation and redistribution with attribution to the provider
  (summary via OpenStreetMap wiki citing the gazette; gazette PDF returned 403 to our fetcher).
- **Units:** the portal metadata does **not** state a unit. Rs./Quintal is the AGMARKNET
  convention (see §8) but is **not stated in data.gov.in docs**.
- **Automated collection permitted?** Yes in the sense that the OGD API is provided for
  programmatic access under GODL; observe any key limits once a key is issued.

## 3. data.gov.in — "Variety-wise Daily Market Prices Data of Commodity" (historical candidate)

- **Resource id: `35985678-0d79-46b4-9ed6-6f13308a1d24`**, page
  `https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity`; same
  catalog `6141ea17-…`; owner MoA&FW / DA&FW / DMI. Also listed as visible on
  `aikosh.indiaai.gov.in`.
- **Metadata (live `/lists`):** created 2023-09-19T06:43:03Z, updated 2026-10-21T23:35:04Z;
  page `field_date_released` 2024-05-21; frequency shown as "Daily"; backing index
  `agmarknet_new`.
- **Fields (ids are capitalised — filter keys are case-sensitive):** `State`, `District`,
  `Market`, `Commodity`, `Variety`, `Grade`, `Arrival_Date` (date), `Min_Price`,
  `Max_Price`, `Modal_Price` (typed **keyword**, i.e. strings), `Commodity_Code`.
  Filterable: `State`, `District`, `Commodity`, `Arrival_Date`.
- **This schema is identical to the headers of our `Daily_Market_Prices_2001_2026/csv/*.csv`**,
  including `Commodity_Code`. It is the most likely upstream of the Kaggle archive (§5a);
  this is an inference, not stated by the Kaggle owner beyond "Open Data Platform".
- **Auth:** same API key; unauthenticated call → HTTP 400 `Authorization field missing`.
- **Date range / depth of history:** **UNVERIFIED** (needs a key).
- **Licence:** GODL-India. **Units:** not stated in metadata.

## 4. e-NAM (enam.gov.in)

- **Official name / owner:** National Agriculture Market (e-NAM); footer: "National Agriculture
  Market Project", Department of Agriculture & Farmers' Welfare. (SFAC as implementing agency
  is commonly reported; not confirmed on the page.)
- **Observed:** `https://enam.gov.in/web/dashboard/trade-data` returns HTTP 200; menus list
  "Trading Details", "e-NAM Live Price Information", "Agmarknet Price Dashboard",
  "eNAM vs AGMARKNET Price Dashboard". Data loads dynamically.
- **Public API:** **none found** (no documentation located). `robots.txt` → 404.
- **Licence / terms:** **UNVERIFIED** ("©Copyright 2023 National Agriculture Market Project.
  All rights reserved." in footer).
- **Decision:** not used. Coverage is limited to e-NAM-integrated mandis and trade, not the
  AGMARKNET reporting universe.

## 5. Kaggle archives used by this repo

Provenance was confirmed by comparing **every file's byte size** in the public Kaggle API
listing (`https://www.kaggle.com/api/v1/datasets/list/<owner>/<slug>`) with the local copies.

### 5a. Daily Market Prices of Commodity India (2001-2026) → `data/raw/Daily_Market_Prices_2001_2026/`

- **Page:** `https://www.kaggle.com/datasets/khandelwalmanas/daily-commodity-prices-india`
- **Owner:** Manas Khandelwal (`khandelwalmanas`). Version **134**, last updated
  **2026-04-23T04:05Z**, 7,603,454,638 bytes uncompressed, 52 files (`csv/2001…2026.csv`,
  `parquet/2001…2026.parquet`).
- **Match:** **52/52 files matching by file size** to the local copy. This also settles the
  "unknown provenance" of the local Parquet copy noted in `PROJECT_STATUS.md` §3.1: it is
  the Kaggle dataset's own `parquet/` folder (same records, not produced by our pipeline).
- **Licence:** Kaggle label "Other (specified in description)"; description states
  "Government Open Data License - India (GODL-India)" and "Data sourced from the Government of
  India's Open Data Platform".
- **Owner's description:** 2001–2025 (title says 2026), 75M+ records, 374 commodities, 1,504
  varieties, "cleaned, deduplicated, and sorted"; Min/Max/Modal "in INR per quintal".
- **Schema:** `State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_Price,Max_Price,Modal_Price,Commodity_Code`.
- **Measured locally (PROJECT_STATUS.md §3.2):** 75,984,017 rows; `Arrival_Date`
  2001-01-10 … 2026-04-21; 97.65% VALID; 339,216 surplus duplicate rows (0.45%) despite the
  "deduplicated" claim; extreme modal prices up to 918,421,086; ~6,804 markets, ~387
  commodities. Filenames do not bound dates (`2026.csv` starts 2025-12-30). Quoted fields with
  embedded commas exist.
- **Quality limitations:** no arrivals/quantity column; secondary redistribution (cleaning steps
  undocumented); duplicates and magnitude outliers need per-commodity handling.
- **Automated collection:** Kaggle download requires a Kaggle account/API token and acceptance
  of Kaggle terms; refresh by re-downloading a newer version.

### 5b. India Commodity Wise Mandi Dataset → `data/raw/india_mandi/`

- **Page:** `https://www.kaggle.com/datasets/vandeetshah/india-commodity-wise-mandi-dataset`
- **Owner:** Vandeet Shah (`vandeetshah`). Version **1**, last updated 2024-10-14T04:04Z,
  4,745,859,660 bytes, 325 CSV files (one per commodity).
- **Match:** **325/325 files matching by file size** to the local copy.
- **Licence:** labelled **Apache 2.0** on Kaggle. The description does not name the upstream
  source or its licence; the data are AGMARKNET-format (columns and units match AGMARKNET
  exports), so upstream terms (GODL/AGMARKNET) likely also apply — **UNVERIFIED**.
- **Owner's description:** 325 commodities, "Jan 1st, 2000 to Feb 1st, 2024"; columns
  `State Name, District Name, Market Name, Variety, Group, Arrivals (Tonnes),
  Min Price (Rs./Quintal), Max Price (Rs./Quintal), Modal Price (Rs./Quintal), Reported Date`.
- **Measured locally (PROJECT_STATUS.md §3.3–3.5):** 56,879,072 rows; 2000-10-19 … 2024-02-02
  (owner's "Jan 1st, 2000" start not reproduced); 96.55% VALID; 10 empty files; two header
  variants (293/22 files) and two date formats (294/21); commodity only in filename; no grade.
- **Use:** historical arrivals enrichment only; it ends 2024-02-02 so it cannot feed 2025/26
  features.

## 6. Weather

### 6a. IMD (India Meteorological Department)

- **Portals:** `https://mausam.imd.gov.in/` (forecasts/products) and
  `https://dsp.imdpune.gov.in/` (Data Supply Portal; "Climate Data Service (open for all)").
- **Gridded rainfall:** `https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html` —
  daily 0.25° × 0.25° gridded rainfall over India, **1901–2024**, mm, 135×129 grid, yearly
  binary files with sample Fortran/C readers.
- **Auth:** none for the gridded files page. **API:** none found.
- **Terms:** DSP disclaimer: reproducing material "for commercial purpose is not permitted"
  without permission. Academic use appears acceptable; formal licence **UNVERIFIED**.
- **Limitation:** annual files lag (latest year 2024 on 2026-10-22); needs grid→district mapping.

### 6b. Open-Meteo Historical Weather API (recommended optional source)

- **Endpoint:** `https://archive-api.open-meteo.com/v1/archive?latitude=..&longitude=..&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&daily=temperature_2m_max,precipitation_sum&timezone=Asia%2FKolkata`
- **Tested 2026-10-22** (Hubli area, 2025-01-01..03): HTTP 200, JSON with
  `daily_units` (`°C`, `mm`) and `daily.time[]`, `daily.temperature_2m_max[]`,
  `daily.precipitation_sum[]`.
- **Coverage:** ERA5 0.25° from 1940, ERA5-Land 0.1° from 1950, ECMWF IFS 9 km from 2017;
  ERA5 updated daily with ~5-day delay (docs page).
- **Auth:** none on the free endpoint. **Limits (pricing page):** 600/min, 5,000/hour,
  10,000/day, 300,000/month; **free API is non-commercial only**.
- **Licence:** data CC BY 4.0; attribution with link ("Weather data by Open-Meteo.com").
- **Fit:** reanalysis at point/grid level, not station observations; must map each mandi or
  district to coordinates (no geocodes in our price data — open question).

### 6c. NASA POWER

- **Endpoint:** `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR,T2M&community=AG&longitude=..&latitude=..&start=YYYYMMDD&end=YYYYMMDD&format=JSON`
- **Tested 2026-10-22:** HTTP 200, GeoJSON Feature; `properties.parameter.<NAME>.<YYYYMMDD>`;
  header shows API v2.10.1, source MERRA2, fill value -999.0; units `mm/day`, `C`.
- **Auth:** none. **Terms:** no formal restriction listed; must cite POWER reference + data
  reference (version, access date) and is asked to notify on publication/redistribution.
- **Rate limits:** **UNVERIFIED** (not checked).

## 7. Crop calendars

- **DES (desagri.gov.in):** "Harvesting Seasons of Principal Crops in Major Growing States"
  appendix to the Farm Harvest Prices publications, e.g.
  `https://desagri.gov.in/wp-content/uploads/2021/04/Appendix2.pdf` (HTTP 200, PDF). Static,
  state × crop month windows; older editions (2014-15 … 2018-19). Licence **UNVERIFIED**.
  Usable as a hand-coded seasonality lookup, not an API.
- **FAO GIEWS country brief, India:** `https://www.fao.org/giews/countrybrief/country.jsp?code=IND`
  (reference date 13-Feb-2026; PDF at `/giews/countrybrief/country/IND/pdf/IND.pdf`). Narrative
  harvest timing (e.g. Rabi wheat harvest from late March; Kharif paddy harvested by January).
  A crop-calendar graphic may be embedded as images; not machine-readable.
- **FAO Crop Calendar app:** `https://cropcalendar.apps.fao.org/` reachable (SPA); India coverage
  not inspected — **UNVERIFIED**.
- **FAO licence:** FAO database terms (`https://www.fao.org/contact-us/terms/db-terms-of-use/en/`)
  license statistical datasets CC BY 4.0 unless metadata says otherwise; attribution required.

## 8. Price units and definitions

| Evidence | Says | Strength |
|---|---|---|
| `india_mandi` file headers (§5b) | `Min/Max/Modal Price (Rs./Quintal)` | In-data label |
| Kaggle 5a description | Min/Max/Modal "in INR per quintal" | Redistributor statement |
| AGMARKNET 2.0 UI strings | "Price unit (₹/quintal)", quantity "Quintals" | Official UI, not a data dictionary |
| data.gov.in metadata (§2, §3) | Field names/types only, **no unit** | — |
| India Mandi `Arrivals (Tonnes)` | arrivals in tonnes | In-data label |

**Conclusion:** Rs./Quintal (1 quintal = 100 kg) is consistent across every source that states a
unit, but it is **not stated in the data.gov.in documentation**, so the official confirmation
requested is **UNVERIFIED**. `PROJECT_STATUS.md` §3.5 keeps the cross-source price join
blocked until checked empirically; this register supports (but does not prove) that both
sources are Rs./Quintal.

**Definitions** (data.gov.in description): min / max = lowest / highest wholesale price reported
for the market-commodity-variety-day; modal = the most frequent (modal) transaction price.
Prices are wholesale, reported per market day; non-trading days have no rows.

---

## Decisions for this project

1. **Primary historical source:** the Kaggle "Daily Market Prices of Commodity India
   (2001-2026)" archive (`data/raw/Daily_Market_Prices_2001_2026/csv/`, version 134),
   GODL-India. Attribute as: *"Source: AGMARKNET via Open Government Data Platform India
   (data.gov.in), redistributed by M. Khandelwal on Kaggle; licensed under GODL-India."*
   Use the CSVs; treat the bundled Parquet as a convenience copy only.
2. **Secondary source:** Kaggle India Commodity Wise Mandi (version 1) for historical
   arrivals only, never for 2025/26 features; no price join until units are verified
   empirically.
3. **Incremental source:** a data.gov.in OGD adapter for resource
   `9ef84268-d588-465a-a308-a864a43d0070`, key read from `AGRI_DATA_GOV_IN_API_KEY`.
   **Blocked until a key is issued** — without it the API returns 400/403. The adapter must:
   map lower-case fields (`arrival_date`, `min_price`, …) to the archive schema, set
   `commodity_code` to null, persist every daily snapshot, page with `limit`/`offset`, and
   back off politely. Resource `35985678-…` (same schema as the archive) is the preferred
   candidate for back-filling the gap after 2026-04-21 once a key exists.
4. **Weather (optional):** Open-Meteo Historical API, CC BY 4.0, non-commercial free tier,
   with visible attribution. NASA POWER is the fallback. IMD gridded data is not used
   (commercial reproduction restricted, annual lag, binary grids).
5. **Not used:** AGMARKNET 2.0 internal API (undocumented) and e-NAM (no public API, terms
   unknown). No scraping of either portal.

## Open questions

1. Does resource `9ef84268-…` keep any history, or only the current day? (Needs a key: query
   min/max `arrival_date`.)
2. Exact `/resource` JSON envelope and maximum `limit` per request with a personal key.
3. Official data.gov.in rate limits and sample-key limits — no primary statement found.
4. Which filter key works for state: `filters[state.keyword]` or `filters[state]`?
5. Date range of `35985678-…`, and whether it reproduces the Kaggle 5a archive exactly.
6. AGMARKNET 2.0 terms and copyright policy text (JS-rendered; not retrieved).
7. Upstream source and licence of the Kaggle India Mandi dataset (labelled Apache 2.0 with no
   upstream attribution).
8. Official confirmation of the Rs./Quintal unit in an AGMARKNET/DMI data dictionary.
9. Mandi/district geocodes needed to join weather; no lat/lon exists in either price source.
10. IMD gridded data licence for academic use.

## URLs visited (2026-10-22)

- https://agmarknet.gov.in/ , /robots.txt , /sitemap.xml , /static/js/main.c1f86740.js
- https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi
- https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity
- https://www.data.gov.in/apis/9ef84268-d588-465a-a308-a864a43d0070 , https://www.data.gov.in/Godl , https://www.data.gov.in/apis
- https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?format=json&limit=1 (no key → 400; invalid key → 403)
- https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24?format=json&limit=1 (no key → 400)
- https://api.data.gov.in/lists?format=json&filters[index_name]=<resource id> (metadata, no key needed)
- https://www.data.gov.in/sites/default/files/Gazette_Notification_OGDL.pdf (403 to fetcher)
- https://wiki.openstreetmap.org/wiki/Open_Geospatial_Data_from_Government_of_India (GODL summary, via search)
- https://themineworks.com/blog/india-government-data-api/ , https://indiadataatlas.deccanspatial.com/chapters/ch06-apis/data-gov-api/ , https://econabhishek.github.io/datagovindia/ (third-party API guides)
- https://enam.gov.in/web/dashboard/trade-data , https://enam.gov.in/robots.txt (404)
- https://www.kaggle.com/datasets/khandelwalmanas/daily-commodity-prices-india and Kaggle API `datasets/view` + `datasets/list` for it
- https://www.kaggle.com/datasets/vandeetshah/india-commodity-wise-mandi-dataset and Kaggle API `datasets/view` + `datasets/list` for it
- https://mausam.imd.gov.in/ , https://dsp.imdpune.gov.in/ , https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html
- https://open-meteo.com/en/licence , https://open-meteo.com/en/pricing , https://open-meteo.com/en/docs/historical-weather-api , https://archive-api.open-meteo.com/v1/archive (test call)
- https://power.larc.nasa.gov/ , https://power.larc.nasa.gov/docs/referencing/ , https://power.larc.nasa.gov/api/temporal/daily/point (test call)
- https://desagri.gov.in/ , https://desagri.gov.in/wp-content/uploads/2021/04/Appendix2.pdf
- https://www.fao.org/giews/countrybrief/country.jsp?code=IND , https://www.fao.org/giews/countrybrief/country/IND/pdf/IND.pdf , https://cropcalendar.apps.fao.org/ , https://www.fao.org/contact-us/terms/db-terms-of-use/en/

---

## Addendum (integration owner, 2026-10-22): measured effects of the AGMARKNET 2.0 migration on the archive

Measured on the silver layer of source 5a with DuckDB. The queries are in `docs/DATA_DICTIONARY.md#identifier-harmonisation`.

| Month | VALID reports | share with " APMC" market suffix | share grade FAQ | share grade Local |
|---|---:|---:|---:|---:|
| 2025-09 | 528,543 | 0.0% | 49.1% | 38.9% |
| 2025-10 | 371,917 | 0.0% | 51.0% | 36.1% |
| 2025-11 | 32,903 | 4.2% | 52.8% | 34.4% |
| 2025-12 | 171,600 | 96.9% | 29.3% | 52.9% |
| 2026-03 | 120,238 | 95.2% | 21.7% | 60.8% |

* **Timing.** The renaming and the drop in volume start in November 2025, which matches the portal go-live date (2025-11-07) recorded in §1. After the migration the archive holds about 20–35% of its earlier monthly volume.
* **Effect on forecasts.** Forecasts for Nov 2025–Apr 2026 therefore rest on sparser series, and the test-period metrics are reported for 2025-01..2025-10 and 2025-11..2026-04 separately where it matters (see `docs/EXPERIMENTS.md`).
* **Grade relabel.** A separate FAQ→Local relabel starts on 2025-01-27. On no day does a (market, commodity, variety) carry two grades, so it is treated as a relabel.
