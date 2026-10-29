# Golden examples

Every file here is a **complete, schema-valid `data.json`**. The workflow is:
**copy the closest one, swap in your values, then validate** —
`python ../scripts/run.py validate.py your-data.json`. Don't author chart structure
from scratch.

All files are checked in CI-style by `scripts/run-tests.py`.

| File | Shows |
|---|---|
| `chart-bar.json` | bar chart — two series, `bounds`/`format`/`major_unit` |
| `chart-line-dual-axis.json` | line chart — `axis1` + `axis2` (dual axis), percent format |
| `chart-area.json` | area chart — series-level fill colors |
| `chart-pie.json` | pie chart — single series, per-slice colors via `data_point_styles` |
| `chart-date-axis.json` | date axis — `date_labels` (Excel serial) instead of `labels` |
| `chart-with-titles.json` | chart **title** + **axis titles** as sibling `{key}` placeholders |
| `scatter-single.json` | scatter — one series of `[x, y]` pairs, x/y bounds |
| `scatter-multi-axis.json` | scatter — two series, series styles + per-point highlight |
| `table.json` | table — header + rows, styled cell, data bar |
| `list.json` | list — indent `level`, per-item styles |
| `text-styles.json` | text — font/shape styles, hyperlink, `{ "delete": true }` |
| `image-video-theme.json` | image, local video (+thumbnail), YouTube video, `theme.colors` |
| `full-deck.json` | a complete multi-slide deck mixing several types |

## The chart bracket rule (the one that breaks charts)

```
series   → OBJECT  { "ser1": { ... } }      (a map; NEVER an array [ ])
chart    values → number[]            [100, 130, 120]
scatter  values → [number,number][]   [[7.1, 5.1], [3.4, 6.9]]
axis1/axis2, bounds, x_bounds → OBJECT { }
labels   → string[]  at the chart ROOT (never inside an axis)
```
