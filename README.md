# slidepack-skills

[日本語](README.ja.md)

A Claude Skill for [SlidePack](https://slidepack.io), the service from Qitar LLC that builds
PowerPoint decks from a template and a JSON file.

With this skill installed, Claude can write the `data.json` that SlidePack needs, check it
against SlidePack's official JSON Schema, and walk through the API calls that turn it into a
`.pptx` file.

## What is included

- **Examples.** One `data.json` for each element type, each checked against the schema (text,
  list, table, image, chart and so on). Claude starts from these instead of writing the
  structure from scratch. If you write a `data.json` by hand, you can copy them as templates.
- **A validator.** `validate.py` checks a `data.json` against the official schema and explains
  each problem it finds in plain language, with a suggested fix. Chart definitions get extra
  attention, since that is where mistakes are easiest to make.
- **A template inspector.** `probe_template.py` lists the keys a template PPTX expects, and
  with a `data.json` it reports which keys are missing or unused.
- **Reference notes.** A summary of each data type, the API sequence, and how to design a
  template.

## Requirements

- Claude Code. This is the only environment the skill has been tested in.
- Python 3.8 or later, for the scripts.
- [jsonschema](https://pypi.org/project/jsonschema/) for the validator (set up automatically).
- [python-pptx](https://pypi.org/project/python-pptx/) for the template inspector (set up automatically).
- A SlidePack account and API token, if you want to render a deck. See
  [Setting up an API token](#setting-up-an-api-token).

You do not need the PowerPoint application to generate a deck. To open the generated `.pptx`,
use any application that reads PPTX files, such as PowerPoint, Keynote or Google Slides.

## What needs a network connection

| Task | Network |
| --- | --- |
| Validate a `data.json` (`validate.py`) | Not needed. The schema is bundled. |
| Inspect a template (`probe_template.py`) | Not needed. |
| First run only: fetching the Python packages (`jsonschema`, `python-pptx`) | Needed, from PyPI. Later runs reuse the cached packages. |
| Render a deck through the SlidePack API | Needed. Requests go to `https://slidepack.io` and to the upload URL that the API returns, and are authenticated with your API token. |

If Claude Code runs in an environment that restricts outbound traffic (a corporate proxy, a
sandbox, an allow-list), the render step will fail until `slidepack.io` is reachable. Validation
and inspection are not affected. You can also use the skill for validation and render the deck
by other means.

Environments other than Claude Code, such as claude.ai or Cowork, have not been tested.

## Install

Clone the repository:

```bash
git clone https://github.com/qitar/slidepack-skills.git
cd slidepack-skills
```

Install the skill by copying the `skills/slidepack` directory. To make it available in every
project:

```bash
cp -r skills/slidepack ~/.claude/skills/
```

To use it in one project:

```bash
cp -r skills/slidepack /path/to/your/project/.claude/skills/
```

If you would rather follow this repository as it changes, link it instead:

```bash
ln -s "$(pwd)/skills/slidepack" ~/.claude/skills/slidepack
```

You do not need to install any Python packages yourself. Claude starts the scripts through
`scripts/run.py`, which provides the packages they need without changing your PC's Python
environment (see [Using the scripts on their own](#using-the-scripts-on-their-own)).

After installing, ask Claude for a deck, for example: "Using template.pptx, make slides from
this sales data."

## Setting up an API token

Rendering a deck requires a SlidePack API token. Sign in to the
[SlidePack dashboard](https://slidepack.io/app) and create one.

The skill has no configuration file or environment variable for the token. Give the token to
Claude when you ask it to render a deck.

## Using the scripts on their own

The scripts can be run without Claude. Run them through `run.py`, which works in both bash and
PowerShell:

```bash
python skills/slidepack/scripts/run.py validate.py data.json
python skills/slidepack/scripts/run.py probe_template.py template.pptx --data data.json
```

`run.py` reads the packages a script needs and provides them in this order, without changing
your PC's Python environment:

1. If your Python already has them, it uses that.
2. Otherwise, if [uv](https://docs.astral.sh/uv/) is installed, it runs the script in a
   temporary environment.
3. Otherwise it creates a private virtual environment outside the skill directory
   (`~/.cache/slidepack-skill/venv`, or under `XDG_CACHE_HOME` when that is set; the
   equivalent under `LOCALAPPDATA` on Windows; set `SLIDEPACK_SKILL_VENV` to move it) and
   installs the packages there.

If none of that is possible it stops with a message and installs nothing.

`validate.py` exits with `0` when the payload is valid and `1` when it is not. It exits with `2`
when it could not run at all, for instance because the file is missing or is not valid JSON.
`run.py` exits with `2` when it cannot set up the packages.

The self-test is:

```bash
python skills/slidepack/scripts/run-tests.py
```

It checks that every example validates and that a set of known-bad payloads are rejected.

## Contents

```
skills/slidepack/
  SKILL.md            entry point of the skill
  pyproject.toml      Python dependencies (for uv)
  schema/             SlidePack's data.json schema, with notes on where it came from
  scripts/            validator, template inspector, self-test
  examples/           one data.json per element type
  reference/          data types, API workflow, template design
```

Only `skills/slidepack/` needs to be installed. Everything the skill uses at runtime is inside it.

## SlidePack documentation

- [SlidePack Docs](https://docs.slidepack.io/en)
- [API endpoint reference](https://docs.slidepack.io/en/reference/endpoints)
- [Full reference (text)](https://docs.slidepack.io/llms-full.txt). If anything in this skill
  differs from the live documentation, the documentation is correct.
- [data.json JSON Schema](https://docs.slidepack.io/schemas/data-json.json). The bundled copy
  came from here. `skills/slidepack/schema/VERSION.md` describes how to refresh it.

## License

Apache License 2.0. The full text is in [LICENSE](LICENSE), and the copyright notice is in
[NOTICE](NOTICE).

Copyright 2026 Qitar LLC and manamu Inc.
