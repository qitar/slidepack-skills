# AGENTS.md

This file provides guidance to AI coding agents and human contributors working on the
`slidepack-skills` codebase.

## Project Overview

`slidepack-skills` packages a Claude Skill that builds a SlidePack `data.json` — the payload
that, together with a template PPTX, renders a PowerPoint deck through the slidepack.io API.

The format itself is documented by SlidePack's own docs. What this skill adds is help with the
chart section, where a wrong shape produces no schema error and no rendered output to point at
the cause. A `series` written as an array instead of an object, a scatter series given flat
numbers instead of `[x, y]` pairs, a `labels` array nested inside an axis: each of these is
easy to write and hard to notice. So the skill is built around mechanical checks and worked
examples rather than prose the model is trusted to remember: `schema/` + `scripts/validate.py`
catch the shape, `examples/` remove the need to author structure at all.

Treat that as the design constraint. A change that adds another paragraph of rules to `SKILL.md`
is usually worse than one that adds an example or a validator diagnostic.

## Commands

| Command | Description |
| --- | --- |
| `python skills/slidepack/scripts/run-tests.py` | Self-test: every example validates, every known-bad payload is rejected |
| `python skills/slidepack/scripts/run.py validate.py data.json` | Validate one payload |
| `python skills/slidepack/scripts/run.py probe_template.py tpl.pptx [--data data.json]` | List a template's expected keys; coverage-check a payload |

There is no repo-level install step, no build step and no CI. `run.py` supplies `jsonschema` and
`python-pptx` itself (see Dependencies below), so a plain `python` is all you need.

## Architecture

```
skills/slidepack/               the distributable skill
├── SKILL.md                    entry point — workflow, chart bracket rules, silent-failure list
├── pyproject.toml              runtime deps for uv (`package = false`); not vendored
├── schema/
│   ├── data-json.schema.json   SlidePack's official schema, vendored verbatim — do not edit
│   └── VERSION.md              source URL, fetch date, refresh steps, documented deviations
├── scripts/
│   ├── run.py                  launcher: supplies deps via uv or a private venv, never the user's Python
│   ├── validate.py             schema validation + plain-language chart diagnostics
│   ├── probe_template.py       python-pptx template prober (keys + coverage)
│   └── run-tests.py            the self-test
├── examples/                   one validated data.json per element type, + README index
└── reference/
    ├── data-types.md           condensed type reference for every element
    ├── api-workflow.md         the 4-step API sequence, expiry limits, zip layout
    └── template-design.md      {key} vs alt-text binding, repeating slides
```

`skills/slidepack/` is the unit of distribution. Installing means copying (or symlinking) that
directory into `~/.claude/skills/` or a project's `.claude/skills/` — there is no packaging step,
and nothing outside that directory ships with the skill. **Anything a user needs at runtime must
live inside it**, which is why `schema/VERSION.md` and `examples/README.md` sit under the skill
rather than in a top-level `docs/`.

### Two checks, two different questions

```
data.json ──┬─ validate.py ───────→ is the SHAPE right?   (schema + chart diagnostics)
            └─ probe_template.py ─→ do the KEYS match?    (needs the template pptx)
```

Neither subsumes the other. A payload can satisfy the schema perfectly and still leave a literal
`{chart-title}` in the rendered deck; a payload can name every template key correctly and still
render a blank chart. `SKILL.md` tells the model to run both when the template is available.

## Conventions

### The vendored schema is pristine

`schema/data-json.schema.json` is fetched verbatim from
`https://docs.slidepack.io/schemas/data-json.json` and must never be hand-edited. Where the
published schema is narrower than SlidePack's documented examples, `validate.py` relaxes an **in-memory
copy** in `apply_compat_shim()` and the deviation is written down in `schema/VERSION.md`.

Two deviations exist today (list items without `type`, series without `name`). If you add a
third, add the shim *and* the `VERSION.md` entry in the same commit — a silent shim is a rule
nobody can find later. If a schema refresh fixes one, delete the matching shim lines.

`validate.py` also *reads* the schema at runtime: `load_props()` fills `PROPS` from each chart
definition's `properties`, which is what the unknown-key check compares against. The schema leaves
`additionalProperties` open everywhere, so a key like `title` inside a chart object is accepted and
then dropped at render time — the check exists to catch that class of silent failure. Because the
key lists are derived rather than hand-copied, a refresh updates them for free; the hardcoded sets
in `PROPS` are only a fallback for when the schema cannot be read. An unknown key is a *warning*,
not an error, on purpose: the bundled schema may lag the live API, and a validator that rejects
valid payloads is worse than one that lets a typo through with a note. Title-ish keys are the
exception — those are documented as never-fields, so they fail.

Refreshing the schema means re-running `run-tests.py`: the examples are the regression suite for
that file.

### Examples are the contract

`examples/*.json` are not illustrations, they are what the model copies. Every file must be a
complete, schema-valid payload — `run-tests.py` asserts exactly that, so a half-written snippet
breaks the build. Keep one concern per file, and add the row to `examples/README.md` in the same
commit; that table is what `SKILL.md` points the model at when it goes looking.

When you add a genuinely new failure mode, add the inverse too: a known-bad payload in the
`BAD` table in `run-tests.py` that must be **rejected**. A validator that has never been shown to
say no is not tested.

### SKILL.md frontmatter

`name`, `description`, `compatibility`, `metadata`, `license` and `allowed-tools` are the fields
the skill spec permits. Adding any field outside that set makes claude.ai packaging and upload
fail outright — so version and provenance live under `metadata:`, not as top-level keys, and not
in a separate sidecar file.

`description` is the only thing an agent sees before deciding whether to load the skill. It is
written as trigger phrases rather than as a summary on purpose; keep it that way.

### Dependencies

Nothing is vendored except the schema, and nothing is ever installed into the user's own Python.
`scripts/run.py` is the one entry point: it reads the dependency list from the target script's
PEP 723 header and supplies it from the current interpreter (if already present), from uv, or
from a private venv outside the skill directory. `pyproject.toml` repeats the same list for uv
users; keep it and the script headers in step. There is deliberately no requirements.txt, and
`run.py` must stay standard-library only. There are no shell scripts on purpose: one Python
entry point behaves the same in bash and PowerShell and needs no executable bit or line-ending
pin. `validate.py` and `probe_template.py` still degrade to a clear install
message when run directly without their package. Keep that property: the skill is frequently
run in an environment the user did not prepare.

Prefer the standard library. `validate.py` hand-rolls its error formatting instead of pulling in
a reporting library, because a second required dependency doubles the chance the skill cannot run
at all.

### Console output must survive a legacy codepage

Both Python scripts call `_make_output_encoding_safe()` before printing anything, which
reconfigures stdout/stderr to UTF-8. Without it, the `✓` in a success message raises
`UnicodeEncodeError` on any Windows console running a legacy codepage — cp932 on a Japanese
system — so a *valid* payload exits non-zero with a traceback. Keep that call, and keep it ahead
of the first `print`.

### Licensing

`LICENSE` is the Apache-2.0 text verbatim, including the untouched `[yyyy] [name of copyright
owner]` template in its appendix — do not fill that in. The real attribution lives in `NOTICE`,
which is what section 4(d) requires redistributions to carry. Update `NOTICE`, not `LICENSE`.

Because a skill is installed by copying `skills/slidepack/` on its own, neither file travels with
it; the `license:` field in `SKILL.md` frontmatter is what identifies the license at the
destination.

### Language

The README is English first: `README.md` is the primary text and `README.ja.md` is the Japanese
companion. Change them together. Everything else in this repository is English, prompts included.
`SKILL.md` and `reference/*.md` are
prompts, so their language is what Claude tends to report in; right now it follows the user's
language rather than being pinned. If you want reports pinned to one language, translate those
files and nothing else — code, comments, JSON keys and validator output stay English regardless.

## Testing

`run-tests.py` is the whole suite, and it runs in about a second:

```bash
python skills/slidepack/scripts/run-tests.py
```

It compiles the Python scripts, validates every example, and feeds the validator known-bad
payloads that must be rejected. Run it before every commit — especially after refreshing the
schema, since that is the change most likely to break examples silently.

What it cannot check is the half of the system that lives on slidepack.io: whether a payload the
validator accepts actually renders. There is no fixture for that and no mock API. Verifying a
real change to `reference/api-workflow.md` or to a chart example means running the 4-step
sequence against a real template with a real API key, and reading `render_succeeded` /
`render_message` in the response — a failed render still returns HTTP 200.
