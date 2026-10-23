"""Builds the IEEE-format manuscript (IEEEtran, journal mode) from the single source in paper/ijf/.

    python3 paper/ieee/build_ieee.py && (cd paper/ieee && tectonic -X compile main.tex)

Only presentation changes are made here: two-column floats, IEEE abstract/index terms,
single-blind author block and a non-anonymised availability statement. Every number and claim
comes from paper/ijf/*.tex unchanged, so the two manuscripts cannot drift apart.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "ijf"
OUT = Path(__file__).resolve().parent / "sections"
WIDE = {"tab:main", "tab:retrain", "tab:features", "tab:prosp", "tab:revision"}  # too wide for one column -> table*
REPO = "https://github.com/kaushalrog/AG-DATA"
DEMO = "https://kaushalrog.github.io/AG-DATA/"


def floats(tex: str) -> str:
    def widen(m):
        body = m.group(0)
        lab = re.search(r"\\label\{([^}]+)\}", body)
        if lab and lab.group(1) in WIDE:
            body = body.replace("\\begin{table}[t]", "\\begin{table*}[!t]").replace("\\end{table}", "\\end{table*}")
        else:
            body = body.replace("\\begin{table}[t]", "\\begin{table}[!t]")
        return body.replace("0.74\\linewidth", "0.78\\textwidth")
    tex = re.sub(r"\\begin\{table\}\[t\].*?\\end\{table\}", widen, tex, flags=re.S)
    tex = tex.replace("\\begin{figure}[t]", "\\begin{figure}[!t]").replace("width=0.72\\linewidth", "width=\\columnwidth")
    return tex


def abstract(tex: str) -> str:
    body = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.S).group(1).replace("\\noindent", "").strip()
    kw = re.search(r"Keywords:\}\s*(.*)", tex).group(1).strip()
    terms = ", ".join(k.strip().capitalize() for k in kw.split(";"))
    return f"\\begin{{abstract}}\n{body}\n\\end{{abstract}}\n\n\\begin{{IEEEkeywords}}\n{terms}\n\\end{{IEEEkeywords}}\n"


def availability(tex: str) -> str:
    old = "An anonymised review package and a tagged release remain to be prepared; neither is claimed to exist."
    assert old in tex, "availability sentence changed in ijf/s10_conclusion.tex"
    new = (f"The repository is public at \\url{{{REPO}}}, and the release commit will be tagged at acceptance. "
           f"A static demonstration of the farmer application, serving a bundled snapshot of real reports, is at \\url{{{DEMO}}}.")
    return tex.replace(old, new)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for f in sorted(SRC.glob("s*.tex")):
        tex = f.read_text()
        if f.name == "s00_abstract.tex":
            tex = abstract(tex)
        else:
            tex = floats(tex)
        tex = tex.replace('\\input{tables/revision_robustness}', '\\input{../tables/revision_robustness}')
        # long identifiers must be breakable in a narrow column
        tex = tex.replace("\\texttt{khandelwalmanas/daily-commodity-prices-india}", "\\url{khandelwalmanas/daily-commodity-prices-india}")
        if f.name == "s10_conclusion.tex":
            tex = availability(tex)
        (OUT / f.name).write_text(tex)
    print(f"wrote {len(list(OUT.glob('s*.tex')))} sections to {OUT}")


if __name__ == "__main__":
    main()
