# Presentation

`AG-DATA-presentation.tex` — Beamer slides for the Big Data Analytics project.

## Compiling

**Overleaf (easiest):** create a new project, upload the `.tex` file, set the
compiler to **pdfLaTeX**, and click Recompile.

**Locally**, with a full TeX Live / MacTeX install:

```bash
pdflatex AG-DATA-presentation.tex
pdflatex AG-DATA-presentation.tex   # run twice so slide numbers settle
```

## Packages used

Only standard ones, all present in TeX Live and on Overleaf:
`beamer`, `tikz` (arrows.meta, positioning, shapes.geometric, calc),
`booktabs`, `xcolor`, `lmodern`, `inputenc`, `fontenc`.

No custom themes (such as Metropolis) are required.

## Slides

16 frames: 15 content slides plus a closing "Thank You" slide.
16:9 aspect ratio, 12 pt base font.
