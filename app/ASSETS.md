# Visual assets and licences

All visual assets in `app/` are **original works created for this project** and dedicated to the public
domain under **CC0 1.0** (https://creativecommons.org/publicdomain/zero/1.0/). Nothing is hotlinked or
downloaded at runtime; no third-party icon sets, fonts or images are bundled.

| Asset | How it was made | Licence |
|---|---|---|
| `icons/icon-192.png`, `icons/icon-512.png` | Rendered by `tools/make_icons.py` (Python standard library: geometric leaf + soil line, supersampled, written as PNG with `zlib`) | CC0 |
| `icons/app-icon.svg` | Written by the same script (vector version of the app icon, used as favicon) | CC0 |
| `icons/commodities/*.svg` (20 files) | Hand-written simple geometric SVG pictograms (48×48 viewBox) | CC0 |
| Inline UI icon sprite in `index.html` (`#i-home`, `#i-sell`, …) | Hand-written stroke icons (24×24) | CC0 |

Pictogram mapping (one icon may serve a group; see `i18n/commodities.json`):
tomato, onion, potato, brinjal, chilli (Green Chilli, Capsicum), leafy (Cauliflower, Cabbage, Coriander
leaves), okra (Bhindi), gourd (Bottle gourd, Bitter gourd, Cucumber), pumpkin, carrot, garlic, spice
(Ginger), banana, fruit (Apple, Lemon, Pomegranate), grain (Wheat, Paddy, Rice, Bajra, Jowar), maize,
pulse (Bengal/Green/Black gram, Arhar, Lentil), oilseed (Mustard, Soyabean, Groundnut), cotton, and
`produce` as the fallback for any other commodity.

Accessibility: pictograms are decorative (`alt=""` / `aria-hidden="true"`) because the commodity name
is always printed next to them in text.

Fonts: system fonts only, with a `font-family` stack naming Noto Sans Tamil / Telugu / Malayalam /
Devanagari / Kannada and common OS fallbacks; no font files are shipped or downloaded.

Data: demo files in `demo/` are synthetic placeholders (not real market prices). Real data comes from
AGMARKNET via data.gov.in under the Government Open Data Licence – India (GODL-India), as reported by the API.
