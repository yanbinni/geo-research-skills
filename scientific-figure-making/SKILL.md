---
name: scientific-figure-making
description: >-
  Covers publication-ready matplotlib figures for academic papers, slides, and
  reports—bars, trends, scatter, heatmaps, and multi-panel layouts—with this
  repository’s house style, print/vector export conventions, and parity with
  figures4papers demos. Use when the user is finalizing or creating such figures
  in matplotlib, including static raster and vector thematic maps. Use the
  panel purpose to choose statistical or cartographic layout. Do not use for
  interactive dashboards or web visualization, exploratory-only plots,
  dominant 3D visualization, or Illustrator/Figma-first infographics.
---

# Scientific figure making

Open `references/` only as needed; do not preload every file. Start from the table below, then follow links inside the document you opened (and into `figure_*` code via [references/demos.md](references/demos.md)) instead of loading the full reference set up front.

## Choose a layout by panel purpose

- For bars, lines, scatterplots, and matrix heatmaps, use the original statistical-figure layout.
- For static thematic maps of real locations, use the closed map frame, frame-edge coordinate labels, and light graticule in [the cartographic reference](references/cartographic-figures.md). That reference covers both raster and vector maps.
- For mixed figures, choose a layout per panel and coordinate the typography and spacing across panels. Follow an explicit user-supplied layout reference.

## When to load this skill

- Matplotlib figures for **papers, slides, or reports** that must match **this repo’s publication look** (fonts, palette, spines, legends, export).
- Requests involving **grouped bars, trend lines, heatmaps, multi-panel grids**, or **PDF/SVG/high-DPI** output in a scientific-figure context.
- References to **figures4papers** `figure_*` projects or “same style as the repo figures.”

## When not to load

- **Plotly, Altair, Bokeh**, or other interactive / web-first plotting.
- **EDA-only** plots where seaborn or pandas is enough until there is a publication target.
- Primary workflow is **3D**, **interactive GIS**, or **non-matplotlib** tooling.
- **Illustrator / Figma–first** layout or infographic (not matplotlib data plots).

## Related files

| File | Open when |
|------|-----------|
| [references/tutorials.md](references/tutorials.md) | End-to-end walkthroughs (bar, trends, heatmap) |
| [references/api.md](references/api.md) | Function signatures, `PALETTE`, validation rules |
| [references/common-patterns.md](references/common-patterns.md) | Layout patterns, legend panel, print-safe bars |
| [references/design-theory.md](references/design-theory.md) | Typography, export policy, palette rationale |
| [references/demos.md](references/demos.md) | Canonical `figure_*` demo links in figures4papers |
| [references/cartographic-figures.md](references/cartographic-figures.md) | Static raster and vector maps, closed frames, and graticules |
