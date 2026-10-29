#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["jsonschema>=4.0"]
# ///
"""
SlidePack data.json validator.

Validates a data.json file against the bundled official SlidePack JSON Schema
(schema/data-json.schema.json) and adds friendly, targeted diagnostics for the
mistakes LLMs make most often when constructing charts — especially confusing
`{` (object) and `[` (array) for `series`, `values`, and `axis`.

Usage:
    python validate.py path/to/data.json
    python validate.py            # defaults to ./data.json

Exit codes:
    0  valid
    1  invalid (errors printed)
    2  usage / environment error (file missing, bad JSON, jsonschema not installed)

Requires: jsonschema. Start it through scripts/run.py, which supplies it without
          touching your own Python: python scripts/run.py validate.py data.json
"""

import json
import os
import sys


# ----------------------------------------------------------------------------
# Encoding safety
# ----------------------------------------------------------------------------
def _make_output_encoding_safe():
    """Stop a legacy console codepage from turning a result into a traceback.

    This script prints ✓ / ✗ / → / —. On Windows the console encoding is often a
    legacy codepage (cp932 on a Japanese system, cp1252 elsewhere) that cannot
    represent any of them, and print() raises UnicodeEncodeError instead of
    reporting the verdict — so a *valid* data.json exits non-zero with a stack
    trace. Ask for UTF-8; if the stream refuses, at least make it substitute
    rather than raise.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            try:
                stream.reconfigure(errors="replace")
            except Exception:
                pass


_make_output_encoding_safe()


# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "..", "schema", "data-json.schema.json")


# ----------------------------------------------------------------------------
# Output helpers
# ----------------------------------------------------------------------------
class C:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    OFF = "\033[0m"


def _supports_color():
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


_COLOR = _supports_color()


def paint(text, color):
    return f"{color}{text}{C.OFF}" if _COLOR else text


class Finding:
    """One problem found, with a human-readable location and a fix hint."""

    def __init__(self, path, message, hint=None, severity="error"):
        self.path = path
        self.message = message
        self.hint = hint
        self.severity = severity  # "error" (fails) or "warning" (prints only)

    def render(self):
        loc = paint(self.path or "(root)", C.CYAN)
        mark = paint("✗", C.RED) if self.severity == "error" else paint("!", C.YELLOW)
        out = [f"  {mark} {loc}\n    {self.message}"]
        if self.hint:
            for line in self.hint.splitlines():
                out.append(f"    {paint('→', C.GREEN)} {line}")
        return "\n".join(out)


# ----------------------------------------------------------------------------
# Targeted pre-checks — these produce clear messages for the known chart traps
# BEFORE the raw JSON Schema validator (whose `oneOf` errors are hard to read).
# ----------------------------------------------------------------------------
VALID_CHART_TYPES = {"chart", "scatter-chart"}
INVALID_CHART_TYPES = {
    "bar-chart", "line-chart", "area-chart", "pie-chart",
    "donut-chart", "doughnut-chart", "column-chart", "bubble-chart",
    "bar", "line", "area", "pie", "donut", "column",
}
WRAPPER_KEYS = {"data", "content", "fields", "items", "placeholders", "values_map"}
THEME_COLOR_KEYS = {
    "lt1", "dk1", "lt2", "dk2",
    "accent1", "accent2", "accent3", "accent4", "accent5", "accent6",
    "hlink", "folHlink",
}

# Which keys each chart-ish object may carry. The schema leaves
# `additionalProperties` open on all of them, so an unknown key is accepted and
# then ignored at render time — silently. These sets are only the fallback;
# main() refreshes them from the bundled schema via load_props(), so following
# the refresh procedure in schema/VERSION.md keeps this check accurate without
# anyone having to edit this file.
PROPS = {
    "chart": {
        "type", "labels", "labels_interval", "date_labels", "date_labels_format",
        "date_labels_major_unit", "date_labels_major_time_unit", "axis1", "axis2",
    },
    "scatter-chart": {"type", "axis1", "axis2"},
    "chart-axis": {"series", "bounds", "format", "major_unit"},
    "scatter-chart-axis": {
        "series", "x_bounds", "x_format", "x_major_unit",
        "y_bounds", "y_format", "y_major_unit",
    },
    "chart-series": {"name", "values", "styles", "data_point_styles"},
    "scatter-chart-series": {"name", "values", "styles", "data_point_styles"},
    "styles": {"font", "shape"},
    "styles-font": {"typeface", "size", "color", "underline", "bold", "italic", "strike"},
    "styles-shape": {"outline", "fill", "align", "vertical_align"},
    "text": {"type", "value", "styles", "hyperlink", "level"},
    "list": {"type", "values"},
    "table": {"type", "rows", "horizontal_sizing", "vertical_sizing"},
    "image": {"type", "src", "scaling", "overflow"},
    "video": {"type", "src", "thumbnail", "scaling"},
}

# Element types with a PROPS entry above, checked the same way chart-family
# objects are: unknown keys get the same "dropped silently at render" warning
# (or hard error, for a title-ish key) that chart/axis/series objects already
# get from check_unknown_keys.
NON_CHART_ELEMENT_TYPES = {"text", "list", "table", "image", "video"}


def load_props(schema):
    """Refresh PROPS from the bundled schema."""
    defs = schema.get("$defs", {}) if isinstance(schema, dict) else {}
    for name in PROPS:
        props = defs.get(name, {}).get("properties")
        if isinstance(props, dict) and props:
            PROPS[name] = set(props)

    # "styles-font"/"styles-shape" aren't their own $defs entries — they're
    # nested inside $defs.styles.properties.{font,shape}.properties.
    styles_props = defs.get("styles", {}).get("properties", {})
    for sub, key in (("font", "styles-font"), ("shape", "styles-shape")):
        props = styles_props.get(sub, {}).get("properties")
        if isinstance(props, dict) and props:
            PROPS[key] = set(props)


def _typename(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, dict):
        return "object {…}"
    if isinstance(v, list):
        return "array [...]"
    if isinstance(v, str):
        return "string"
    if isinstance(v, (int, float)):
        return "number"
    return type(v).__name__


def check_unknown_keys(obj, path, defname, what, findings, skip=()):
    """Flag keys the schema has no slot for — the renderer drops them in silence.

    A title-ish key is the documented form of this mistake: a chart has no
    `title` field, because chart and axis titles are ordinary text placeholders
    filled as SIBLINGS of the chart. That one is an error. Any other unknown key
    is a warning only, since the bundled schema may simply be older than the API.
    """
    allowed = PROPS.get(defname, set())
    for key in obj:
        if key in allowed or key in skip:
            continue
        if "title" in key.lower():
            findings.append(Finding(
                "%s.%s" % (path, key),
                "a %s object has no `%s` field. Titles are separate sibling "
                "text placeholders on the slide, not a field on this object." % (what, key),
                'WRONG: "c": { "type":"chart", "%s":"Revenue", ... }\n'
                'RIGHT: { "template":1, "chart-title":"Revenue", "c": { "type":"chart", ... } }\n'
                "The sibling key must match the template's {placeholder} exactly — "
                "run scripts/run.py probe_template.py <template.pptx> to list them." % key,
            ))
        else:
            findings.append(Finding(
                "%s.%s" % (path, key),
                "`%s` is not a %s field in the bundled schema. Unknown keys are "
                "ignored at render time without an error." % (key, what),
                "Check the spelling, or refresh the schema (schema/VERSION.md) if "
                "SlidePack has added this field.",
                severity="warning",
            ))


def check_styles_object(styles, path, findings):
    """A single Styles object ({ font: {...}, shape: {...} }) — used for both
    a series' whole-series `styles` and each element of `data_point_styles`.
    """
    if not isinstance(styles, dict):
        findings.append(Finding(
            path, f"a styles object must be an object {{}}, got {_typename(styles)}.",
            'Example: "styles": { "font": { "bold": true, "color": "2a4598" } }',
        ))
        return
    check_unknown_keys(styles, path, "styles", "styles", findings)
    for sub, defname in (("font", "styles-font"), ("shape", "styles-shape")):
        if sub not in styles:
            continue
        sub_val = styles[sub]
        sub_path = f"{path}.{sub}"
        if not isinstance(sub_val, dict):
            findings.append(Finding(
                sub_path, f"`{sub}` must be an object {{}}, got {_typename(sub_val)}.",
            ))
            continue
        check_unknown_keys(sub_val, sub_path, defname, f"styles.{sub}", findings)


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_bounds(bounds, path, findings):
    """Inverted axis bounds (minimum > maximum) render a blank/broken axis —
    the schema has no ordering constraint between the two, so nothing else
    catches this."""
    if not isinstance(bounds, dict):
        return  # not a dict at all is a type mismatch handled elsewhere
    lo, hi = bounds.get("minimum"), bounds.get("maximum")
    if _is_number(lo) and _is_number(hi) and lo > hi:
        findings.append(Finding(
            path,
            f"`minimum` ({lo}) is greater than `maximum` ({hi}) — the axis "
            "range is inverted and will render a blank or broken axis.",
            severity="warning",
        ))


def check_major_unit(value, path, findings):
    """A gridline interval of exactly 0 renders a blank or broken axis."""
    if _is_number(value) and value == 0:
        key = path.rsplit(".", 1)[-1]
        findings.append(Finding(
            path,
            f"`{key}` is 0 — an axis gridline interval of zero typically "
            "renders a blank or broken axis.",
            "Use a positive interval, or omit this key to let SlidePack "
            "choose one automatically.",
            severity="warning",
        ))


def check_axis(axis, axis_path, is_scatter, findings):
    """Validate a chart-axis / scatter-chart-axis object."""
    if not isinstance(axis, dict):
        findings.append(Finding(
            axis_path,
            f"axis must be an object {{}}, got {_typename(axis)}.",
            'Example: "axis1": { "series": { "ser1": { "name": "...", "values": [...] } } }',
        ))
        return

    if "series" not in axis:
        findings.append(Finding(
            axis_path,
            "axis is missing the required `series` key.",
            'Each axis needs: "series": { "<key>": { "name": "...", "values": [...] } }',
        ))
        return

    # `labels` inside an axis gets its own, more specific message in check_chart.
    check_unknown_keys(
        axis, axis_path,
        "scatter-chart-axis" if is_scatter else "chart-axis",
        "scatter chart axis" if is_scatter else "chart axis", findings, skip=("labels",),
    )

    if is_scatter:
        for key in ("x_bounds", "y_bounds"):
            check_bounds(axis.get(key), f"{axis_path}.{key}", findings)
        for key in ("x_major_unit", "y_major_unit"):
            check_major_unit(axis.get(key), f"{axis_path}.{key}", findings)
    else:
        check_bounds(axis.get("bounds"), f"{axis_path}.bounds", findings)
        check_major_unit(axis.get("major_unit"), f"{axis_path}.major_unit", findings)

    series = axis["series"]

    # THE most common mistake: series as an array instead of a keyed object.
    if isinstance(series, list):
        findings.append(Finding(
            f"{axis_path}.series",
            "`series` is an ARRAY [], but it MUST be a keyed OBJECT {}.",
            'WRONG: "series": [ { "name": "A", "values": [1,2,3] } ]\n'
            'RIGHT: "series": { "ser1": { "name": "A", "values": [1,2,3] } }\n'
            "Renderer error this would cause: "
            '"cannot unmarshal array into Go value of type map[string]data.Series"',
        ))
        return

    if not isinstance(series, dict):
        findings.append(Finding(
            f"{axis_path}.series",
            f"`series` must be an object {{}}, got {_typename(series)}.",
            'RIGHT: "series": { "ser1": { "name": "A", "values": [1,2,3] } }',
        ))
        return

    if not series:
        findings.append(Finding(
            f"{axis_path}.series",
            "`series` is empty. At least one series is required.",
        ))

    for key, s in series.items():
        spath = f"{axis_path}.series.{key}"

        # Mistake: series value is a bare array instead of { name, values }.
        if isinstance(s, list):
            findings.append(Finding(
                spath,
                "series value is an ARRAY, but each series must be an OBJECT "
                "with `name` and `values`.",
                'WRONG: "%s": [1, 2, 3]\n'
                'RIGHT: "%s": { "name": "...", "values": [1, 2, 3] }' % (key, key),
            ))
            continue
        if not isinstance(s, dict):
            findings.append(Finding(
                spath,
                f"series value must be an object {{}}, got {_typename(s)}.",
            ))
            continue

        check_unknown_keys(
            s, spath,
            "scatter-chart-series" if is_scatter else "chart-series",
            "series", findings,
        )

        if "values" not in s:
            findings.append(Finding(
                spath, "series is missing the required `values` key.",
            ))
        else:
            check_values(s["values"], f"{spath}.values", is_scatter, findings)

        if "name" not in s:
            # The schema marks `name` as required, but the docs allow omitting it
            # when overwriting an existing template series (the template name is
            # kept). So this is a warning, not a hard error.
            findings.append(Finding(
                spath,
                "series has no `name`. OK only when overwriting an existing "
                "template series (its name is kept); otherwise add one.",
                'Add: "name": "<series label shown in the legend>"',
                severity="warning",
            ))
        elif not isinstance(s["name"], str):
            # A wrong-typed `name` has nothing in check_unknown_keys or
            # check_values to catch it, so it otherwise falls all the way
            # through to the schema's oneOf and dumps the whole series object
            # instead of pointing at this field.
            findings.append(Finding(
                f"{spath}.name",
                f"`name` must be a string, got {_typename(s['name'])}.",
            ))

        if "styles" in s:
            check_styles_object(s["styles"], f"{spath}.styles", findings)

        if "data_point_styles" in s:
            dps = s["data_point_styles"]
            dps_path = f"{spath}.data_point_styles"
            if not isinstance(dps, list):
                findings.append(Finding(
                    dps_path,
                    f"`data_point_styles` must be an array [], got {_typename(dps)}.",
                    'Example: "data_point_styles": [ { "font": { "bold": true } }, null ]',
                ))
            else:
                for i, dp in enumerate(dps):
                    if dp is not None:
                        check_styles_object(dp, f"{dps_path}[{i}]", findings)


def check_values(values, vpath, is_scatter, findings):
    if not isinstance(values, list):
        findings.append(Finding(
            vpath, f"`values` must be an array [], got {_typename(values)}.",
        ))
        return

    if not values:
        # Nothing in the schema requires a non-empty `values`, and the loops
        # below simply don't iterate — so this passes silently by default. A
        # zero-point series renders as an empty/blank chart with no error,
        # exactly the class of failure this validator exists to catch.
        findings.append(Finding(
            vpath,
            "`values` is empty — this series will render with no data points.",
            "OK only if intentionally overwriting a template series with no "
            "data; otherwise add at least one value.",
            severity="warning",
        ))
        return

    if is_scatter:
        # scatter values MUST be [x, y] tuples.
        for i, pt in enumerate(values):
            if not (isinstance(pt, list) and len(pt) == 2
                    and all(isinstance(n, (int, float)) and not isinstance(n, bool) for n in pt)):
                findings.append(Finding(
                    f"{vpath}[{i}]",
                    "scatter-chart values must be [x, y] number pairs.",
                    'WRONG: "values": [7.1, 5.1, 3.4]\n'
                    'RIGHT: "values": [ [7.1, 5.1], [3.4, 6.9], [2.6, 2.6] ]',
                ))
                return
    else:
        # regular chart values MUST be a flat number array.
        for i, n in enumerate(values):
            if isinstance(n, list):
                findings.append(Finding(
                    f"{vpath}[{i}]",
                    "chart values must be a flat array of numbers, not nested arrays. "
                    "(Nested [x,y] pairs are only for type \"scatter-chart\".)",
                    'WRONG: "values": [ [1, 100], [2, 130] ]\n'
                    'RIGHT: "values": [ 100, 130 ]',
                ))
                return
            if not isinstance(n, (int, float)) or isinstance(n, bool):
                findings.append(Finding(
                    f"{vpath}[{i}]",
                    f"chart values must be numbers, got {_typename(n)} at index {i}.",
                ))
                return


def check_chart(obj, path, findings):
    ctype = obj.get("type")
    is_scatter = ctype == "scatter-chart"

    # `labels` is handled just below, with a message specific to each chart kind.
    check_unknown_keys(
        obj, path,
        "scatter-chart" if is_scatter else "chart",
        "chart", findings, skip=("labels",),
    )

    if "labels" in obj and is_scatter:
        findings.append(Finding(
            f"{path}.labels",
            "scatter-chart has no `labels` — x position is encoded in each [x, y] pair.",
        ))

    # `labels` must be at chart root, not inside an axis.
    for axis_key in ("axis1", "axis2"):
        axis = obj.get(axis_key)
        if isinstance(axis, dict) and "labels" in axis:
            findings.append(Finding(
                f"{path}.{axis_key}.labels",
                "`labels` belongs at the chart root, not inside an axis.",
                'RIGHT: { "type":"chart", "labels":[...], "axis1": { "series": {...} } }',
            ))

    if "axis1" not in obj:
        findings.append(Finding(path, "chart is missing the required `axis1` key."))
    else:
        check_axis(obj["axis1"], f"{path}.axis1", is_scatter, findings)
    if "axis2" in obj:
        check_axis(obj["axis2"], f"{path}.axis2", is_scatter, findings)


def check_text_like(obj, path, what, findings, skip=()):
    """A Text object — a slide placeholder, a list item, or a table cell."""
    check_unknown_keys(obj, path, "text", what, findings, skip=skip)
    if "styles" in obj:
        check_styles_object(obj["styles"], f"{path}.styles", findings)


def check_element(obj, path, t, findings):
    """Non-chart element types (text/list/table/image/video): give them the
    same unknown-key attention chart-family objects already get, instead of
    silence. Shape-level checks (row/column consistency, list nesting) are
    intentionally NOT added here — AGENTS.md scopes the silent-failure
    problem this validator targets to the chart section; this only closes
    the narrower "unknown key dropped with no warning" gap for these types.
    """
    if t == "text":
        check_text_like(obj, path, "text", findings)
        return

    check_unknown_keys(obj, path, t, t, findings)

    if t == "list":
        values = obj.get("values")
        if isinstance(values, list):
            for i, item in enumerate(values):
                if isinstance(item, dict):
                    check_text_like(item, f"{path}.values[{i}]", "list item", findings)
    elif t == "table":
        rows = obj.get("rows")
        if isinstance(rows, list):
            for ri, row in enumerate(rows):
                if isinstance(row, list):
                    for ci, cell in enumerate(row):
                        if isinstance(cell, dict):
                            # The schema defines a cell as a Text object plus `databar`.
                            check_text_like(
                                cell, f"{path}.rows[{ri}][{ci}]", "table cell", findings,
                                skip=("databar",),
                            )


def precheck_slide(slide, idx, findings):
    path = f"slides[{idx}]"
    if not isinstance(slide, dict):
        findings.append(Finding(path, f"slide must be an object, got {_typename(slide)}."))
        return
    if "template" not in slide:
        findings.append(Finding(path, "slide is missing the required `template` key."))

    for key, val in slide.items():
        if key == "template":
            continue
        kpath = f"{path}.{key}"

        # `theme` is deck-wide. Inside a slide it is accepted and then ignored.
        if key == "theme":
            findings.append(Finding(
                kpath,
                "`theme` is a ROOT-level key, not a slide key — a theme inside a "
                "slide is ignored.",
                'WRONG: { "slides": [ { "template":1, "theme": {...} } ] }\n'
                'RIGHT: { "slides": [ {...} ], "theme": { "colors": { "accent1": "f6ad5c" } } }',
            ))
            continue

        # Wrapper-key hallucination: placeholders nested under "data"/"content"/etc.
        if key in WRAPPER_KEYS and isinstance(val, dict) and "type" not in val and "delete" not in val:
            findings.append(Finding(
                kpath,
                f'"{key}" looks like a wrapper holding placeholders. SlidePack has NO '
                "wrapper — placeholders go DIRECTLY on the slide object.",
                'WRONG: { "template":1, "%s": { "title":"..." } }\n'
                'RIGHT: { "template":1, "title":"..." }' % key,
            ))
            continue

        if isinstance(val, dict):
            t = val.get("type")
            if t in INVALID_CHART_TYPES:
                findings.append(Finding(
                    kpath,
                    f'invalid chart type "{t}". Only "chart" and "scatter-chart" exist.',
                    'Use "type": "chart" for bar/line/area/pie (the visual style comes '
                    'from the template), or "type": "scatter-chart" for scatter.',
                ))
            elif t in ("chart", "scatter-chart"):
                check_chart(val, kpath, findings)
            elif "axis1" in val or "axis2" in val:
                # Not one of the two valid names, not a known wrong guess either —
                # a typo or case mismatch ("Chart", "charts"), or `type` missing
                # altogether. Nothing else has an axis1/axis2 key, so this is
                # still a chart, and without this branch it falls through to an
                # unreadable schema `oneOf` dump instead of a targeted message.
                if t is None:
                    findings.append(Finding(
                        kpath,
                        "chart object has no `type` key. Only \"chart\" and "
                        '"scatter-chart" exist.',
                        'Add: "type": "chart" for bar/line/area/pie, or "type": '
                        '"scatter-chart" for scatter.',
                    ))
                else:
                    findings.append(Finding(
                        kpath,
                        f'unrecognized chart type "{t}". Only "chart" and '
                        '"scatter-chart" exist, spelled exactly (case-sensitive).',
                        'Use "type": "chart" for bar/line/area/pie, or "type": '
                        '"scatter-chart" for scatter.',
                    ))
            elif t in NON_CHART_ELEMENT_TYPES:
                check_element(val, kpath, t, findings)
            elif t is None and "value" in val:
                # The compat shim (schema/VERSION.md) lets a Text object omit
                # `type` entirely, so this is a valid, type-less text
                # placeholder — not an unrecognized element. Still give it the
                # same unknown-key attention any other text object gets.
                check_text_like(val, kpath, "text", findings)


def precheck(data, findings):
    """Structural heuristics with friendly messages. Runs before schema validation."""
    # Legacy format: a bare array at root. The renderer still takes it, but the
    # current schema does not — say that, rather than "is not of type 'object'".
    if isinstance(data, list):
        findings.append(Finding(
            "(root)",
            "root is a bare array — the legacy format, deprecated and rejected by "
            "the current schema.",
            'Wrap it: { "slides": [ ... ] }',
        ))
        return
    if not isinstance(data, dict):
        findings.append(Finding("(root)", f"root must be an object, got {_typename(data)}."))
        return

    # Colors go under theme.colors; on `theme` directly they are silently dropped.
    # Checked even when `colors` is ALSO present — a stray key alongside a
    # correctly-nested `colors` object is just as silently dropped as one with
    # no `colors` object at all.
    theme = data.get("theme")
    if isinstance(theme, dict):
        stray = sorted(k for k in theme if k in THEME_COLOR_KEYS)
        if stray:
            findings.append(Finding(
                "theme",
                "theme colors must sit under `theme.colors`, not directly on "
                "`theme` (found: %s)." % ", ".join(stray),
                'WRONG: "theme": { "accent1": "f6ad5c" }\n'
                'RIGHT: "theme": { "colors": { "accent1": "f6ad5c" } }',
            ))

    slides = data.get("slides")
    if slides is None:
        findings.append(Finding("(root)", "root is missing the required `slides` array."))
        return
    if not isinstance(slides, list):
        findings.append(Finding("slides", f"`slides` must be an array, got {_typename(slides)}."))
        return

    for i, slide in enumerate(slides):
        precheck_slide(slide, i, findings)


# ----------------------------------------------------------------------------
# Compatibility shim
# ----------------------------------------------------------------------------
# The bundled schema (schema/data-json.schema.json) is the official one, kept
# pristine for reference. But it is stricter than SlidePack's documented,
# working examples in two places. We relax an in-memory COPY of the schema so
# the validator matches real renderer behaviour rather than rejecting valid
# payloads. See schema/VERSION.md for the rationale.
#
#  1. Text `type` is required by the schema, but the docs show list items as
#     bare `{ "value": "...", "level": 1 }` (no `type`). Relax: `value` only.
#  2. Series `name` is required by the schema, but the docs allow omitting it
#     when overwriting an existing template series. Relax: `values` only.
def apply_compat_shim(schema):
    defs = schema.get("$defs", {})
    if "text" in defs:
        defs["text"]["required"] = ["value"]
    for sd in ("chart-series", "scatter-chart-series"):
        if sd in defs:
            defs[sd]["required"] = ["values"]
    return schema


# ----------------------------------------------------------------------------
# JSON Schema validation (authoritative)
# ----------------------------------------------------------------------------
def schema_validate(data, schema):
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print(paint("ERROR: ", C.RED) + "the `jsonschema` package is not installed.",
              file=sys.stderr)
        print("Run it through the launcher, which supplies it:  "
              "python scripts/run.py validate.py <data.json>", file=sys.stderr)
        sys.exit(2)

    validator = Draft202012Validator(schema)
    findings = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = "".join(
            f"[{p}]" if isinstance(p, int) else f".{p}"
            for p in err.absolute_path
        ).lstrip(".") or "(root)"
        findings.append(Finding(path, err.message))
    return findings


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
# Schema messages that say only "this did not match" — suppressed when a
# pre-check has already explained the same subtree in plain language. The type
# name and property name vary ("is not of type 'array'", "'slides' is a
# required property"), so these are substrings, not exact messages.
GENERIC_SCHEMA_NOISE = (
    "is not valid under any of the given schemas",
    "is not of type '",
    "is a required property",
)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "data.json"

    if not os.path.isfile(target):
        print(paint("ERROR: ", C.RED) + f"file not found: {target}", file=sys.stderr)
        sys.exit(2)

    try:
        # utf-8-sig: Windows PowerShell 5.1 writes UTF-8 with a BOM.
        with open(target, encoding="utf-8-sig") as f:
            data = json.load(f)
    except UnicodeDecodeError:
        print(paint("ERROR: ", C.RED) + f"{target} is not UTF-8 encoded. "
              "Save it as UTF-8 and run again.", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(paint("ERROR: ", C.RED) + f"{target} is not valid JSON.", file=sys.stderr)
        print(f"  line {e.lineno}, column {e.colno}: {e.msg}", file=sys.stderr)
        sys.exit(2)

    try:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(paint("ERROR: ", C.RED) + f"could not load bundled schema: {e}", file=sys.stderr)
        sys.exit(2)

    apply_compat_shim(schema)
    load_props(schema)

    # 1) Friendly pre-checks for the common chart traps.
    pre = []
    precheck(data, pre)

    # 2) Authoritative JSON Schema validation.
    sch = schema_validate(data, schema)

    # The pre-checks already explain the chart traps precisely. The schema's
    # generic complaints (a failed `oneOf`, a bare type mismatch) at the same or
    # an ancestor path are just noise — drop them when a pre-check finding
    # already covers that subtree.
    pre_paths = [f.path for f in pre]

    def covered_by_precheck(schema_path):
        return any(schema_path == p or p.startswith(schema_path + ".")
                   or p.startswith(schema_path + "[")
                   for p in pre_paths)

    filtered_sch = [
        f for f in sch
        if not (any(noise in f.message for noise in GENERIC_SCHEMA_NOISE)
                and covered_by_precheck(f.path))
    ]

    # Merge, de-duplicating identical (path, message) pairs the two passes share.
    seen = set()
    findings = []
    for fnd in pre + filtered_sch:
        sig = (fnd.path, fnd.message)
        if sig in seen:
            continue
        seen.add(sig)
        findings.append(fnd)

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    if not errors:
        msg = paint("✓ valid", C.GREEN + C.BOLD) + f"  ({target} conforms to the SlidePack schema)"
        if warnings:
            msg += paint(f"  — {len(warnings)} warning(s)", C.YELLOW)
        print(msg + "\n" if warnings else msg)
        for fnd in warnings:
            print(fnd.render())
            print()
        sys.exit(0)

    print(paint(f"✗ {len(errors)} error(s) found in {target}:", C.RED + C.BOLD) + "\n")
    for fnd in errors:
        print(fnd.render())
        print()
    for fnd in warnings:
        print(fnd.render())
        print()
    print(paint("Fix the errors above, then re-run the validator before zipping.", C.YELLOW))
    sys.exit(1)


if __name__ == "__main__":
    main()
