# Bundled SlidePack data.json schema

`data-json.schema.json` is the **official** SlidePack JSON Schema for `data.json`,
vendored verbatim (kept pristine — do not edit it by hand).

| | |
|---|---|
| Source | https://docs.slidepack.io/schemas/data-json.json |
| Fetched | 2026-06-10 |
| Draft | JSON Schema 2020-12 |

The authoritative reference page that links to this schema is
https://docs.slidepack.io/llms-full.txt (section "data.json Reference").

> Note: `https://docs.slidepack.io/schemas/api.json` is a **different** schema —
> it covers the HTTP API session/upload responses, **not** `data.json`. Do not
> use it to validate slide data.

## How to refresh

```bash
curl -s https://docs.slidepack.io/schemas/data-json.json -o data-json.schema.json
# then re-run the self-test: every example must still validate, every known-bad payload must still be rejected
python ../scripts/run-tests.py
```

## Documented deviations (compat shim in scripts/validate.py)

In one spot the bundled schema is narrower than what SlidePack's published
examples show. `validate.py` relaxes an **in-memory copy** of the schema so the
examples in the documentation validate. The file on disk stays unchanged.

- **Series `name`** — the schema marks series `name` as required, but the
  renderer accepts a series without it and uses the series key as its name
  (confirmed 2026-11-23 for chart and scatter-chart, new and existing series;
  the docs' dynamic-series recipe omits `name` too). The shim makes only
  `values` required; `validate.py` emits a non-fatal *warning* when `name` is
  missing.

If a future schema version fixes this, drop the matching lines in
`apply_compat_shim()`.

### Not relaxed: Text `type`

The docs show list items without `type` (`{ "value": "...", "level": 1 }`), and
the renderer accepts a type-less Text object anywhere (confirmed 2026-11-23).
This skill still requires `"type": "text"` on every Text object, as the schema
does: being allowed to leave it out helps nobody, and one form is easier to
copy. Do not add a shim for it.
