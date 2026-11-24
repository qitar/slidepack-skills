# Bundled SlidePack data.json schema

`data-json.schema.json` is the **official** SlidePack JSON Schema for `data.json`,
vendored verbatim (kept pristine — do not edit it by hand).

| | |
|---|---|
| Source | https://docs.slidepack.io/schemas/data-json.json |
| Fetched | 2026-11-24 |
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
