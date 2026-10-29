#!/usr/bin/env python3
"""
Self-test for the SlidePack skill: every example must validate, and a set of known-bad payloads
must be rejected. Run from anywhere:

    python scripts/run-tests.py

The validator is started through run.py, exactly as the skill itself starts it, so a broken
launcher fails this suite too. Needs nothing beyond what run.py can provide.
"""

import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
RUN = os.path.join(HERE, "run.py")

failed = False


def say(line=""):
    print(line, flush=True)


def fail(msg):
    global failed
    failed = True
    say("  ✗ " + msg)


def ok(msg):
    say("  ✓ " + msg)


def validate(path):
    """Run validate.py through run.py; return (exit status, combined output)."""
    p = subprocess.run([sys.executable, RUN, "validate.py", path], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout


def show(out):
    for ln in out.rstrip().splitlines():
        say("      " + ln)


def chart(**extra):
    return {"slides": [{"template": 1, "c": dict(extra)}]}


SERIES = {"s": {"name": "A", "values": [1]}}

# Known-bad payloads. Each must be rejected (exit 1).
BAD = {
    "series-array": chart(type="chart", labels=["a"], axis1={"series": [{"name": "A", "values": [1]}]}),
    "scatter-flat": chart(type="scatter-chart", axis1={"series": {"s": {"name": "A", "values": [1, 2, 3]}}}),
    "bad-type": chart(type="bar-chart", axis1={"series": SERIES}),
    "wrapper": {"slides": [{"template": 1, "data": {"title": "x"}}]},
    "labels-in-axis": chart(type="chart", axis1={"labels": ["a"], "series": SERIES}),
    "chart-title-field": chart(type="chart", title="Revenue", labels=["a"], axis1={"series": SERIES}),
    "theme-in-slide": {"slides": [{"template": 1, "theme": {"colors": {"accent1": "f6ad5c"}}}]},
    "theme-colors-flat": {"slides": [{"template": 1, "t": "x"}], "theme": {"accent1": "f6ad5c"}},
    "legacy-root-array": [{"template": 1, "t": "x"}],
    "theme-colors-stray-alongside-nested": {"slides": [{"template": 1, "t": "x"}],
                                            "theme": {"colors": {"accent1": "f6ad5c"}, "accent2": "stray"}},
    "chart-type-typo": chart(type="Chart", labels=["a"], axis1={"series": SERIES}),
    "chart-type-missing": chart(labels=["a"], axis1={"series": SERIES}),
    "series-name-wrong-type": chart(type="chart", labels=["a"],
                                    axis1={"series": {"s": {"name": 123, "values": [1]}}}),
    "series-styles-wrong-type": chart(type="chart", labels=["a"], axis1={"series": {
        "s": {"name": "A", "values": [1, 2], "styles": "bold"}}}),
    "series-data-point-styles-wrong-type": chart(type="chart", labels=["a"], axis1={"series": {
        "s": {"name": "A", "values": [1, 2], "data_point_styles": {}}}}),
    "title-key-inside-text": {"slides": [{"template": 1,
                                          "title": {"value": "Revenue", "chart-title": "oops"}}]},
}

# GENERIC_SCHEMA_NOISE in validate.py suppresses a raw jsonschema message only when it matches
# one of a few substrings AND a pre-check already covers the same path. A reject/accept check
# cannot catch a regression there: both the fixed and the broken filter reject these payloads,
# exit 1 either way. The only way is to count the finding bullets ("  ✗ ") in the output: 2
# means the pre-check message and the raw schema message were both printed.
DUP = {
    "dup-root-missing-slides": {"t": "x"},
    "dup-slides-not-array": {"slides": {"template": 1}},
}

# Payloads that pass the schema yet render a blank or partly dropped result. Exit code alone
# cannot tell "warned as expected" from "said nothing at all", so each needs its warning text:
#   values: []       a zero-point series renders as a blank chart
#   inverted bounds  minimum > maximum, and major_unit of exactly 0: a blank or broken axis
#   list item typo   a typo'd key on a list item is dropped, like an unknown chart/axis key
WARN = {
    "warn-values-empty": (chart(type="chart", labels=["a"],
                                axis1={"series": {"s": {"name": "A", "values": []}}}), "is empty"),
    "warn-inverted-bounds": (chart(type="chart", labels=["a"], axis1={
        "series": SERIES, "bounds": {"minimum": 100, "maximum": 0}}), "is inverted"),
    "warn-major-unit-zero": (chart(type="chart", labels=["a"],
                                   axis1={"series": SERIES, "major_unit": 0}), "is 0"),
    "warn-list-item-unknown-key": ({"slides": [{"template": 1, "lst": {
        "type": "list", "values": [{"value": "Item", "titel": "oops"}]}}]}, "not a list item field"),
}


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    say("== scripts compile cleanly ==")
    for name in ("validate.py", "probe_template.py", "run.py", "run-tests.py"):
        path = os.path.join(HERE, name)
        try:
            with open(path, encoding="utf-8") as fh:
                compile(fh.read(), path, "exec")
            ok("scripts/" + name)
        except SyntaxError as e:
            fail("scripts/%s  (syntax error: %s)" % (name, e))

    # The model copies these files, so a warning on one teaches it to delete a working field.
    say("== examples (expect all valid, with no warnings) ==")
    for f in sorted(glob.glob(os.path.join(SKILL_DIR, "examples", "*.json"))):
        label = "examples/" + os.path.basename(f)
        st, out = validate(f)
        warned = any(ln.startswith("  ! ") for ln in out.splitlines())
        if st == 0 and not warned:
            ok(label)
        else:
            fail(label + ("  (expected no warnings)" if st == 0 else "  (expected valid)"))
            show(out)

    with tempfile.TemporaryDirectory() as tmp:
        def write(name, payload):
            path = os.path.join(tmp, name + ".json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            return path

        say("== known-bad payloads (expect all rejected) ==")
        # Demand exit 1 (invalid), not merely "non-zero". Exit 2 means the validator never ran
        # (missing package, bad interpreter); counting that as a pass would report a green suite
        # while nothing was checked.
        for name, payload in BAD.items():
            st, out = validate(write(name, payload))
            if st == 1:
                ok(name + ".json  rejected")
            elif st == 0:
                fail(name + ".json  (expected REJECT, but passed)")
            else:
                fail("%s.json  (validator could not run, exit %d)" % (name, st))
                show(out)

        say("== no duplicate messages (expect exactly 1 finding, not 2) ==")
        for name, payload in DUP.items():
            st, out = validate(write(name, payload))
            n = sum(1 for ln in out.splitlines() if ln.startswith("  ✗ "))
            if n == 1:
                ok(name + ".json  1 finding, no duplicate")
            else:
                fail("%s.json  (expected 1 finding, got %d)" % (name, n))
                show(out)

        say("== warnings on otherwise-valid payloads (expect exit 0 + specific warning text) ==")
        for name, (payload, needle) in WARN.items():
            st, out = validate(write(name, payload))
            if st == 0 and needle in out:
                ok(name + ".json  valid, with the expected warning")
            else:
                fail('%s.json  (expected exit 0 + a "%s" warning, got exit %d)' % (name, needle, st))
                show(out)

        say("== file encoding (expect BOM accepted, unreadable files exit 2) ==")
        # Windows PowerShell 5.1 writes UTF-8 with a BOM; a file that is not JSON, or not
        # UTF-8, means the validator never got to check anything, which is exit 2, not 1.
        for name, raw, want in (("utf8-bom", b'\xef\xbb\xbf{"slides": [{"template": 1}]}', 0),
                                ("not-json", b'{"slides": [', 2),
                                ("shift-jis", '{"slides": [{"template": 1, "t": "売上"}]}'.encode("shift_jis"), 2)):
            path = os.path.join(tmp, name + ".json")
            with open(path, "wb") as fh:
                fh.write(raw)
            st, out = validate(path)
            if st == want:
                ok("%s.json  exit %d" % (name, st))
            else:
                fail("%s.json  (expected exit %d, got %d)" % (name, want, st))
                show(out)

    say()
    say("TESTS FAILED" if failed else "ALL TESTS PASSED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
