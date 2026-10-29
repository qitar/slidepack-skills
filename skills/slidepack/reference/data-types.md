# data.json — type reference

Condensed from the official schema (`schema/data-json.schema.json`) and
docs (https://docs.slidepack.io/llms-full.txt, "data.json Reference").

The **type column uses the schema's own `x-display-type` notation**:
- `object` → a JSON object `{ ... }`
- `number[]` → a flat array of numbers `[1, 2, 3]`
- `[number, number][]` → an array of 2-number arrays `[[1,2],[3,4]]`
- `string[][]` → a 2-D array of strings

> Don't memorise these — **copy the closest file in `examples/` and swap the
> values**, then run `python scripts/run.py validate.py data.json`.

---

## Root object

| key | type | req | notes |
|---|---|---|---|
| `slides` | `object[]` | ✓ | array of Slide objects; one output slide each |
| `theme` | `object` | | applies to the whole deck |

```json
{ "slides": [ /* Slide objects */ ], "theme": { "colors": { } } }
```

A bare top-level array (`[ {…}, {…} ]`) is the legacy format — supported but
deprecated. Always wrap in `{ "slides": [...] }`.

## Slide object

| key | type | req | notes |
|---|---|---|---|
| `template` | `integer` | ✓ | which template slide number to use |
| *(any other key)* | string \| object | | a **placeholder** — see types below |

**Placeholders sit directly on the slide object** — never under a `data`,
`content`, or `fields` wrapper. The only reserved key is `template`.
Multiple slides may reuse the same `template` number.

---

## Text  (`"type": "text"`)

A plain string is shorthand for a Text object. Use the object form for styling
or links.

| key | type | req | notes |
|---|---|---|---|
| `type` | `"text"` | ✓ | |
| `value` | `string` | ✓ | |
| `styles` | `object` | | `styles.font` + `styles.shape` (see Styles) |
| `hyperlink` | `string` | | URL |
| `level` | `integer 0–8` | | indent; only meaningful inside a List |

```json
"headline": "Q3 Results"
"subtitle": { "type": "text", "value": "Confidential", "styles": { "font": { "italic": true } } }
```

## List  (`"type": "list"`)  →  `examples/list.json`

| key | type | req | notes |
|---|---|---|---|
| `type` | `"list"` | ✓ | |
| `values` | `string[]` or `object[]` | ✓ | each item: string, or `{ "value", "level", "styles" }` |

List items use `{ "value": "...", "level": 1 }` — **not** `{ "type":"text", ... }`.
`styles.font` applies; `styles.shape` is ignored in lists.

## Table  (`"type": "table"`)  →  `examples/table.json`

| key | type | req | notes |
|---|---|---|---|
| `type` | `"table"` | ✓ | |
| `rows` | `string[][]` or `object[][]` | ✓ | **2-D array**; cell = string or Text object |
| `horizontal_sizing` | enum | | `fixed`(def) \| `anchor_left` \| `anchor_right` |
| `vertical_sizing` | enum | | `anchor_top`(def) \| `fixed` \| `anchor_bottom` |

A cell may carry a data bar: `{ "type":"text", "value":"80", "databar": { "ratio": 0.8, "color": "6b95a4" } }`.
`ratio` is 0.0–1.0. Match the **alt text** of the table shape to the key.

## Image  (`"type": "image"`)  →  `examples/image-video-theme.json`

| key | type | req | notes |
|---|---|---|---|
| `type` | `"image"` | ✓ | |
| `src` | `string` | ✓ | **relative path inside the zip**; jpg/jpeg/gif/png |
| `scaling` | enum | | `none`(def) \| `contain` \| `cover` |
| `overflow` | enum | | `visible`(def) \| `hidden` |

## Video  (`"type": "video"`)  →  `examples/image-video-theme.json`

| key | type | req | notes |
|---|---|---|---|
| `type` | `"video"` | ✓ | |
| `src` | `string` | ✓ | relative path (mp4/m4v/mov) **or** a YouTube URL |
| `thumbnail` | `string` | | **required for local files**; same aspect ratio |
| `scaling` | enum | | `contain`(def) \| `cover` |

## Delete

`{ "delete": true }` removes a placeholder so its `{key}` literal does not leak
into the output. Always delete unused placeholders rather than omitting the key.

---

## Chart  (`"type": "chart"`)  →  `examples/chart-*.json`

Bar, Line, Area and Pie are **all** `"type": "chart"`. The visual style comes
from the template PPTX, not from `data.json`. Match the chart shape's **alt
text** to the key.

| key | type | req | notes |
|---|---|---|---|
| `type` | `"chart"` | ✓ | never `bar-chart`/`line-chart`/`pie-chart`/… |
| `labels` | `string[]` | | category labels (x-axis), at the **chart root** |
| `labels_interval` | `integer` | | show 1 in every N labels |
| `date_labels` | `integer[]` | | use **instead of** `labels`; Excel serial dates |
| `date_labels_format` | `string` | | e.g. `"yyyy/mm"` |
| `date_labels_major_unit` | `integer` | | with `date_labels_major_time_unit` |
| `date_labels_major_time_unit` | enum | | `days` \| `months` \| `years` |
| `axis1` | `object` | ✓ | primary value axis (see below) |
| `axis2` | `object` | | secondary axis; identical shape |

### `axis1` / `axis2`  (chart-axis)

| key | type | req | notes |
|---|---|---|---|
| `series` | **`object`** | ✓ | **map** of key → series object (NOT an array) |
| `bounds` | `object` | | `{ "minimum": n, "maximum": n }` |
| `format` | `string` | | label number format, e.g. `"0.0%"`, `"#,#0"` |
| `major_unit` | `number` | | tick interval |

### `series.{key}`  (chart-series)

| key | type | req | notes |
|---|---|---|---|
| `name` | `string` | ✓* | legend label (*optional only when overwriting a template series) |
| `values` | **`number[]`** | ✓ | flat numbers — one per label |
| `styles` | `object` | | series-wide color (`styles.shape.fill` / `.outline`) |
| `data_point_styles` | `object[]` | | per-point styles aligned to `values`; `null` = keep default |

```json
"sales": {
  "type": "chart",
  "labels": ["Q1", "Q2", "Q3", "Q4"],
  "axis1": {
    "series": {
      "ser1": { "name": "Revenue", "values": [100, 130, 120, 145] }
    }
  }
}
```

**Dynamic series:** a series key matching a template series overwrites it; a new
key adds a series (copied from the last template series); template series absent
from your data are deleted, and an axis with no series left is deleted too.

---

## Scatter chart  (`"type": "scatter-chart"`)  →  `examples/scatter-*.json`

| key | type | req | notes |
|---|---|---|---|
| `type` | `"scatter-chart"` | ✓ | |
| `axis1` | `object` | ✓ | holds all series in the common case |
| `axis2` | `object` | | only for a second set of bounds |

**No `labels`** — x is encoded in each point.

### `axis1`  (scatter-chart-axis)

| key | type | notes |
|---|---|---|
| `series` | **`object`** | map of key → series (NOT an array) |
| `x_bounds` / `y_bounds` | `object` | `{ "minimum": n, "maximum": n }` |
| `x_format` / `y_format` | `string` | label number format |
| `x_major_unit` / `y_major_unit` | `number` | tick interval |

### `series.{key}`  (scatter-chart-series)

| key | type | req | notes |
|---|---|---|---|
| `name` | `string` | ✓* | legend label |
| `values` | **`[number, number][]`** | ✓ | array of `[x, y]` pairs |
| `styles` | `object` | | series-wide color |
| `data_point_styles` | `object[]` | | per-point; `null` = keep default |

```json
"corr": {
  "type": "scatter-chart",
  "axis1": {
    "x_bounds": { "minimum": 0, "maximum": 10 },
    "y_bounds": { "minimum": 0, "maximum": 10 },
    "series": {
      "samples": { "name": "Samples", "values": [[7.1, 5.1], [3.4, 6.9], [2.6, 2.6]] }
    }
  }
}
```

---

## Chart & axis titles (separate `{key}` placeholders — NOT chart fields)

A chart's **title** and **axis titles** are not part of the chart object. The
chart object has no `title` field. They are ordinary **text placeholders** that
live in the chart's title / axis-title text boxes in the template, and they are
filled like any `{key}` — by a **sibling key on the slide**, next to the chart.

So a single chart shape carries **two** independent bindings:

| What | Binds by | data.json |
|---|---|---|
| chart **data** (series, axes) | the shape's **alt text** | `"my-chart": { "type":"chart", ... }` |
| chart **title** text | a `{key}` in the title text box | `"chart-title": "..."` (a sibling, outside the chart) |
| **axis title** text | a `{key}` in the axis-title text box | `"x-axis-title": "...", "y-axis-title": "..."` |

```json
{
  "template": 2,
  "chart-title": "User signups: Main Product",
  "x-axis-title": "Month",
  "y-axis-title": "Signups",
  "main-chart": {
    "type": "chart",
    "labels": ["Jan", "Feb", "Mar"],
    "axis1": { "series": { "ser1": { "name": "Signups", "values": [50, 60, 71] } } }
  }
}
```

(See `examples/chart-with-titles.json`.)

### Only fill a title when its placeholder exists — don't invent keys

The key name must **exactly match** the placeholder text in the template (it is
case-sensitive). `chart-title` / `x-axis-title` are just the names used in the
docs; the real name is whatever the template author wrote.

- If the template's title box has `{chart-title}` → add a `"chart-title"` key.
- If there is **no** title placeholder (the title is hardcoded, or there is no
  title box) → **do not add a title key.** An unmatched key is silently ignored,
  and you cannot override a hardcoded title from `data.json`.
- If you can't see the template's placeholders, don't guess a title key — adding
  a wrong name does nothing, and the literal `{chart-title}` stays on screen only
  because the template *has* that placeholder and you didn't fill it.

In short: a leftover literal `{chart-title}` in the output means the template
**has** that placeholder but your `data.json` **omitted** the matching key — add
it. If the title is fine without a key, the template has no such placeholder.

> Stop guessing the names: run `python scripts/run.py probe_template.py template.pptx` — it
> lists every chart/axis-title placeholder the template actually contains (it
> reads chart and axis-title text frames, not just plain text boxes).

---

## Styles object

`styles.font` (applies to text) and `styles.shape` (applies to the shape).

**font:** `typeface` (string) · `size` (number, pt) · `color` (color) ·
`bold` · `italic` · `underline` · `strike` (booleans)

**shape:** `fill` (color) · `outline` (color) ·
`align` (`left`/`center`/`right`/`justified`/`distributed`) ·
`vertical_align` (`top`/`center`/`bottom`)

## Theme object  →  `examples/image-video-theme.json`

Colors live under `theme.colors`, **not** `theme` directly. 12 named keys:
`lt1`, `dk1`, `lt2`, `dk2`, `accent1`–`accent6`, `hlink`, `folHlink`.
An empty string `""` or `null` keeps the template's original color.

## Colors

Hex (`#f6ad5c` or `FF0000`, leading `#` optional, case-insensitive) **or** a
color name. Theme names: `lt1`, `dk1`, `lt2`, `dk2`, `accent1`–`accent6`,
`hlink`, `folHlink`. Plus HTML-like names (case-sensitive, with abbreviations):
e.g. `red`, `gold`, `dkRed`, `ltSlateGray`, `hotPink`, `dkOrange`.
