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

In two spots the bundled schema is narrower than what SlidePack's published
examples show. `validate.py` relaxes an **in-memory copy** of the schema so the
examples in the documentation validate. The file on disk stays unchanged.

1. **Text objects** — the schema requires `type:"text"` on every Text object,
   but the docs show list items as bare `{ "value": "...", "level": 1 }` (no
   `type`). The shim makes only `value` required on Text — by relaxing
   `$defs.text` itself, not just the list-item usage the docs example is
   about, since `$defs.text` is one shared definition `$ref`'d from three
   places: list items, table cells, and ordinary slide-level text
   placeholders. So a bare `{"value":"..."}` with no `type` is currently
   accepted everywhere a Text object can appear, not only inside
   `list.values`. This has only been confirmed against the docs' list-item
   example; whether the real renderer also tolerates a type-less text
   placeholder or table cell has not been separately verified. If that turns
   out not to hold, narrowing the shim to list-item context specifically
   would require restructuring the schema copy (cloning `$defs.text` per call
   site) rather than a one-line `required` change.
2. **Series `name`** — the schema marks series `name` as required, but the docs
   allow omitting it when overwriting an existing template series (the template
   series name is kept). The shim makes only `values` required; `validate.py`
   emits a non-fatal *warning* when `name` is missing.

If a future schema version fixes these, drop the matching lines in
`apply_compat_shim()`.
