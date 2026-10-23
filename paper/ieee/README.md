# IEEE-format manuscript

* `main.tex`: IEEEtran in `journal` mode, two columns. `main.pdf` is the compiled version (8 pages).
* `sections/` is **generated** from `../ijf/` by `build_ieee.py`. Edit `../ijf/*.tex`, then rebuild:
  ```bash
  python3 paper/ieee/build_ieee.py && (cd paper/ieee && tectonic -X compile main.tex)
  ```
  The build changes only presentation:
  * wide tables become `table*`;
  * the abstract and keywords become IEEE Abstract / Index Terms;
  * the author block is single-blind;
  * the availability statement links the public repository and the live demo.

  The numbers are identical to the IJF version and are traceable in `docs/VERIFIED_METRICS.md`.

## Suggested IEEE venue
**IEEE Access** is the realistic first choice. It is a broad-scope, single-blind, open-access journal with no page limit, and it accepts applied evaluation work. Note that it charges an article processing charge.

Fallbacks:
* *IEEE Transactions on AgriFood Electronics*;
* *IEEE Transactions on Computational Social Systems*, for the farmer-facing framing.

## Checklist before submission
- [ ] Corresponding author and e-mails in the `\thanks` block (currently "[to be completed]").
- [ ] Confirm the department name and affiliation of every author.
- [ ] Abstract within 250 words, one paragraph, no citations. It is currently 148 words.
- [ ] Author biographies and photos (`IEEEbiography`), which IEEE Access asks for at the final stage.
- [ ] Tag the release commit and replace "will be tagged at acceptance" with the tag.
- [ ] Upload `../supplement.pdf` as supplementary material.
- [ ] Optional: a graphical abstract.
- [ ] Run the journal's own template check. IEEE Access provides its own LaTeX template, `ieeeaccess.cls`. If it is required at submission, swap the class and keep the sections.
