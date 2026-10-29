# Template (template.pptx) design

How `data.json` keys bind to shapes in the PowerPoint template.

## Two binding mechanisms

| Content | How it binds | Where |
|---|---|---|
| Text, Image, Video | `{key}` placeholder | inside the shape's text or name |
| **Table, Chart** | **alt text** | the shape's alt text == the key |

### `{key}` placeholders (text / image / video)

Put `{key}` literally in a text box, or in an image/video shape's text or name.
Keys are **case-sensitive** and must match the `data.json` key exactly.

```
{title}        ✓ matches "title"
{Title}        ✗ case mismatch
[[title]]      ✗ wrong syntax
```

### Alt text (tables & charts)

Tables and charts are **not** matched by `{key}` text. SlidePack matches them by
the shape's **alt text**. In PowerPoint: right-click the shape → *View/Edit Alt
Text* → set it to the `data.json` key.

```
Shape alt text: "sales_table"   ↔   "sales_table": { "type": "table", ... }
```

Generic alt text like "Chart 1" that doesn't match a key → the table/chart is
**silently skipped** (no error). This is the #1 cause of "my chart didn't
update".

## Repeating slides

Multiple slide objects in `data.json` may reference the **same** `template`
number. Each produces one output slide — so one template slide can generate N
data-driven slides.

```json
{ "slides": [
  { "template": 1, "name": "Widget A" },
  { "template": 1, "name": "Widget B" },
  { "template": 1, "name": "Widget C" }
]}
```

## Don't leave placeholders unfilled

Omitting a `{key}` from a slide object leaves the literal text `{key}` in the
output. To intentionally remove one, set `{ "delete": true }` — don't just drop
the key.
