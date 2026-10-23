# Reviews still required (cannot be done by automated tests)

## What automated testing has established (2026-10-23)

| Check | Environment | Result | Evidence |
|---|---|---|---|
| Service worker activates, app shell precached | Headless Chrome 155 (macOS) and Chrome on GitHub `ubuntu-latest` | PASS | `results/browser/pwa_report*.json`, CI run 39899466902 job `browser` |
| Chrome installability criteria (`Page.getInstallabilityErrors` = none) | same | PASS | same |
| Offline reload serves the cached app | same | PASS | same |
| Cold load with 4× CPU throttle + slow 3G (400 ms RTT, 400 kbit/s) at 360×740 | headless Chrome | PASS: first list in 4.1 s, 69–71 KB transferred | same |
| JS heap after load | headless Chrome | 2.5 MB (API mode), 7.1 MB (demo mode) | same |
| Accessible names, alt text, WCAG AA contrast (computed), touch targets ≥ 44 px, `lang` attribute | 4 screens | PASS | same |
| Six languages at 320 px: no overflow, no raw keys/`undefined`/`NaN`, correct `lang` | 4 screens × 6 languages | PASS | same |
| i18n key parity, placeholders, native script | Node unit tests | PASS (56 tests) | `app/tests/` |

**Observation (not a failure).** The home screen renders about 20,000 DOM nodes, mostly the state selector and the price list. That is heavy for low-end phones. Capping the visible list (e.g. 50 rows with "show more") is the first optimisation to try after a real-device test.

**What these tests do NOT establish.**
* The install prompt and home-screen behaviour on Android.
* Performance on real low-end hardware (CPU throttling is an emulation).
* Screen-reader usability.
* Whether the translations are correct and understandable for farmers.

## 1. Real-device test (4 GB RAM Android): NOT RUN
**Devices.** At least two: one Android Go or entry device with about 3–4 GB RAM (e.g. a Redmi A-series or Samsung Galaxy A0x class), plus one mid-range device. Use Chrome stable.

**Protocol.**
1. Serve the app over HTTPS (any static host) or via `adb reverse tcp:8000 tcp:8000` to `http://localhost:8000`, because service workers need a secure origin.
2. **Cold start.** Clear site data, enable mobile data, and record time to the first price list with Chrome DevTools remote debugging (Performance panel). Repeat 3 times.
3. **Install.** Tap "Install app" or use the browser menu ("Add to Home screen"). Open it from the home screen and confirm standalone mode, icon and name.
4. **Offline.** Turn on airplane mode and reopen. Expect the shell and saved prices with the "offline – saved data from …" notice. Then go back online and confirm the badge clears.
5. **Memory.** Read `chrome://inspect` → Memory, or `adb shell dumpsys meminfo com.android.chrome`, after 5 minutes of use. Record the PSS of the renderer.
6. **Low-end flags.** Repeat steps 2–5 with Data Saver on and the screen at the largest font size.

**Record:** device, Android and Chrome versions, timings, memory, and screenshots. Store them in `results/device/<device>/`.

**Pass criteria (proposed):**
* first list in under 5 s on 3G;
* no crash or reload under memory pressure;
* the install works;
* offline reopen works.

## 2. Screen reader (TalkBack): NOT RUN
Navigate Home → commodity → decision card → "Why am I seeing this?" → guide using TalkBack swipe navigation only. Check that:
* every control is announced with a meaningful name in the chosen language;
* the decision signal and its cautionary text are read out;
* chart information is available as text (the chart summary).

## 3. Native-speaker translation review: NOT DONE
The Tamil, Telugu, Malayalam, Hindi and Kannada strings are AI-drafted (`app/i18n/TRANSLATION_STATUS.md`).

**Reviewers.** One reviewer per language, ideally an agricultural extension worker or someone who works with farmers, not only a fluent speaker.

**Scope.** All keys in `app/i18n/<lang>.json` (264+ keys) and the 36 commodity labels in `app/i18n/commodities.json`.

**Priority order:**
1. `signal.*`, `signal_text.*`, `reason.*`, `decision.*` (risk of misleading advice);
2. `warning.*`, `banner.*`, `unsupported.*`;
3. `guide.*`;
4. everything else.

**Checklist for each string:**
1. The meaning is identical to the English source, especially hedging ("may be worth considering", "not a guarantee"). No string may sound more certain than the English.
2. It uses words farmers actually use for mandi, modal price, quintal, arrival and grade.
3. It reads naturally at a primary-school reading level.
4. Placeholders `{…}` are kept and positioned grammatically.
5. Commodity names follow local usage, and English names remain visible.

**Process.** Reviewers comment in a copy of the JSON. A maintainer applies the changes, removes `"_status": "provisional-ai"` once a language is fully reviewed, and records the reviewer and date in `TRANSLATION_STATUS.md`. Then run `node --test app/tests/` and the browser suite.

## 4. Farmer usability study: NOT DONE
* **Method.** 8–12 farmers per language region, task-based sessions:
  * find today's price for their crop and market;
  * explain what the range means;
  * explain what WATCH and HOLD mean;
  * compare two markets.
* **Measures.** Task success, misinterpretation of the cards (especially reading HOLD as a guarantee), and time taken.
* **Ethics.** Informed consent and no personal data. The study needs institutional ethics approval before it starts.
