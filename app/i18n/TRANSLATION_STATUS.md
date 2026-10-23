# Translation status

| File | Language | Status |
|---|---|---|
| `en.json` | English | source text |
| `ta.json` | Tamil (primary usability target) | **provisional – AI drafted, not reviewed** |
| `te.json` | Telugu | **provisional – AI drafted, not reviewed** |
| `ml.json` | Malayalam | **provisional – AI drafted, not reviewed** |
| `hi.json` | Hindi | **provisional – AI drafted, not reviewed** |
| `kn.json` | Kannada | **provisional – AI drafted, not reviewed** |
| `commodities.json` | commodity labels in ta/te/ml/hi/kn | **provisional – AI drafted, not reviewed** |

All non-English strings were written by an AI model. Each non-English file carries
`"_status": "provisional-ai"` (ignored by the key-parity tests). They **must be reviewed by native
speakers with agricultural/mandi vocabulary** before the app is shown to farmers as finished.

What reviewers should check first:

1. **Decision card wording** (`signal.*`, `signal_text.*`, `reason.*`, `decision.kind`,
   `decision.disclaimer`): must stay cautious ("may be worth considering"), never sound like a promise or
   an instruction, and the SELL/HOLD/WATCH/COMPARE labels must be short and unambiguous.
2. **Price terms**: modal / minimum / maximum price, "quintal", and the local mandi words farmers use
   (e.g. Tamil "மோடல் விலை" vs "அதிகம் கிடைத்த விலை"; Hindi "भाव"; APMC / regulated market names).
3. **Freshness and stale-data banners** (`fresh.*`, `banner.*`): must make clear that old data is not today's price.
4. **Commodity names** in `commodities.json`: regional names differ (e.g. Jowar, Bajra, Maize in Tamil;
   Lentil in Malayalam). Prefer the names used on local mandi boards.
5. **Guide** (`guide.*`): simple sentences, correct place names (Kolar, Chintamani, Lasalgaon) in each script.
6. Long strings at 320 px width (the app wraps text, but shorter is better on the bottom navigation).

Process: edit the JSON, keep every `{placeholder}` exactly as in English, run `node --test app/tests/`
(parity, empty strings, placeholder parity, native-script check), then change the status above to
"reviewed by <name>, <date>".
