---
name: slidepack
description: >
  Use when doing ANY task involving SlidePack.
  Triggers: generating PowerPoint presentations programmatically; constructing data.json
  payloads; designing PPTX templates with placeholders; calling the slidepack.io API
  (sessions, render, download); automating slide creation from structured data;
  building SlidePack integrations or wrappers.
license: Apache-2.0
metadata:
  version: "0.3.0"
  organization: Qitar LLC and manamu Inc.
  schema-source: https://docs.slidepack.io/schemas/data-json.json
  schema-fetched: "2026-06-10"
---

# SlidePack

SlidePack is an HTTP API that renders a PowerPoint (`.pptx`) from a **template
PPTX** + a **`data.json`** that fills its placeholders. This skill makes you
produce a **correct `data.json`** — verified mechanically, not by hope.

## The one rule that matters: validate, don't guess

After you write `data.json`, **always run the bundled validator** and fix every
error before zipping. This catches the `{` vs `[` chart mistakes that silently
break renders.

```bash
python scripts/run.py validate.py data.json     # ✓ valid  OR  a list of errors with fixes
```

`run.py` supplies the dependencies (`jsonschema`) through uv or a private venv kept
outside this directory. **Never `pip install` into the user's own Python.** If it reports
that it cannot set up the environment, tell the user. It checks against the official
SlidePack schema bundled in `schema/data-json.schema.json` and adds plain-language
hints for the common chart traps.

It also rejects the traps the schema itself lets through — a `title` written
*inside* a chart object, a `theme` inside a slide, colors not under
`theme.colors` — and warns about any key the schema has no slot for, since the
renderer ignores those without a word.

## How to build a data.json (the reliable path)

0. **If you have the template PPTX, inspect it first** to learn exactly which
   keys it expects (placeholders *and* chart/axis-title placeholders *and*
   table/chart alt text):
   ```bash
   python scripts/run.py probe_template.py template.pptx --slide 15      # one slide's keys
   python scripts/run.py probe_template.py template.pptx --data data.json # + coverage check
   ```
   This is the surest way to fill every placeholder (and avoid leftover
   `{chart-title}`). `--slide N` is the same number as `"template": N` in data.json
   (counted from 1 in the template PPTX); without it every slide is listed. Tables show
   their size (`13 rows x 16 cols`) and the coverage check flags data whose table size
   differs. `run.py` supplies `python-pptx` the same way.
   (Paths in this file are relative to this skill's directory.)
1. **Don't author chart/table structure from scratch.** Open the closest file in
   `examples/`, copy it, and swap in your values. (`examples/README.md` lists them.)
2. For exact field meanings, read `reference/data-types.md`.
3. **Validate** → `python scripts/run.py validate.py data.json` → fix → repeat until `✓ valid`.
4. Assemble the zip and call the API (`reference/api-workflow.md`).

```
[inspect template]  →  construct  →  validate  →  fix  →  zip  →  render  →  download
```

> `validate.py` checks the **shape** of data.json (the schema). `probe_template.py`
> checks it against the **template's actual keys** (coverage). Use both when you
> have the template.

## Chart bracket rules (memorise these six)

Charts are where structure goes wrong. The types are fixed:

```
type      → "chart" (bar/line/area/pie)  or  "scatter-chart".  Nothing else.
series    → an OBJECT (map):  { "ser1": { "name": "...", "values": [...] } }
            NEVER an array:   [ { "name": "...", "values": [...] } ]   ✗
chart   values → number[]            [100, 130, 120]
scatter values → [number,number][]   [[7.1, 5.1], [3.4, 6.9]]
axis1 / axis2 / bounds / x_bounds → OBJECTS  { ... }
labels    → at the chart ROOT, never inside an axis
```

Minimal correct chart:

```json
"my_chart_alt_text": {
  "type": "chart",
  "labels": ["Q1", "Q2", "Q3", "Q4"],
  "axis1": {
    "series": {
      "ser1": { "name": "Revenue", "values": [100, 130, 120, 145] }
    }
  }
}
```

The visual style (bar / line / area / pie) comes from the **template PPTX**, not
from `data.json` — so it is always `"type": "chart"`. There is no `bar-chart`,
`line-chart`, `pie-chart`, etc.

**Chart and axis titles are NOT chart fields.** The chart object has no `title`.
A chart title / axis title is a separate `{key}` text placeholder that sits as a
**sibling of the chart**, filled like any text key. Add it only when the
template actually has that placeholder — see `reference/data-types.md`
("Chart & axis titles") and `examples/chart-with-titles.json`.

```json
{
  "template": 2,
  "chart-title": "User signups",          // sibling text placeholder, outside the chart
  "main-chart": { "type": "chart", "labels": [...], "axis1": { "series": {...} } }
}
```

## Six mistakes that fail silently (no error, blank output)

1. **Placeholders under a wrapper.** They go directly on the slide object — never
   under `"data"`, `"content"`, or `"fields"`. Only `"template"` is reserved.
2. **Chart/table without matching alt text.** Tables and charts bind by the
   shape's **alt text**, not `{key}`. Mismatch → silently skipped.
3. **Omitting a placeholder key.** Leaves the literal `{key}` in the output.
   Use `{ "delete": true }` to remove one.
4. **`theme` inside a slide, or colors not under `theme.colors`.** `theme` is a
   root-level key; colors live under `theme.colors`.
5. **Not checking `render_succeeded`.** A failed render still returns HTTP 200;
   the reason is in `render_message`.
6. **Forgetting the chart-title placeholder.** A leftover literal `{chart-title}`
   in the output means the template has that placeholder but `data.json` omitted
   the matching sibling key. Add it. (And don't invent a title key when no such
   placeholder exists — it is silently ignored.) `probe_template.py` lists the
   exact title placeholder names so you don't have to guess.

## Map of this skill

| Path | What it is |
|---|---|
| `scripts/run.py` | Launcher: runs a script below with its dependencies, outside the user's Python |
| `scripts/validate.py` | **Run this** (via `run.py`). Validates data.json + friendly chart diagnostics |
| `scripts/probe_template.py` | Lists the keys a template expects; coverage-checks a data.json (run via `run.py`) |
| `scripts/run-tests.py` | Self-test: all examples valid, known-bad payloads rejected |
| `schema/data-json.schema.json` | Official SlidePack data.json JSON Schema (vendored) |
| `schema/VERSION.md` | Source, refresh steps, documented schema-vs-docs deviations |
| `examples/*.json` | Copy-paste-ready, validated decks — your starting point |
| `reference/data-types.md` | Condensed type reference for every element |
| `reference/api-workflow.md` | The 4-step API sequence + expiry limits + zip layout |
| `reference/template-design.md` | `{key}` vs alt-text binding, repeating slides |
| `pyproject.toml` | Dependencies — `jsonschema`, plus optional `python-pptx` (uv fetches them on `uv run`) |

## Verify against live docs when in doubt

The schema and docs can change. Authoritative sources:
- Full reference (LLM): https://docs.slidepack.io/llms-full.txt
- data.json JSON Schema: https://docs.slidepack.io/schemas/data-json.json
  (refresh with the steps in `schema/VERSION.md`)

> `https://docs.slidepack.io/schemas/api.json` is **only** the HTTP session/upload
> response schema — it does **not** describe `data.json`. Don't validate slide
> data against it.
