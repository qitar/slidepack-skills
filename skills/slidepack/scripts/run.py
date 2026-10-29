#!/usr/bin/env python3
"""
Run one of this skill's scripts without installing anything into the user's own Python.

Usage:
    python run.py validate.py data.json
    python run.py probe_template.py template.pptx --data data.json

The dependencies are read from the target script's PEP 723 header, so that header stays the
single source of truth. They are supplied, in order of preference, by:

  1. the current interpreter, if it already has them;
  2. uv, in a throwaway environment (`uv run --no-project --with ...`);
  3. a private virtual environment kept OUTSIDE the skill directory (see below).

If none of these is possible, it says so and exits with 2; it never runs `pip install` against
the interpreter it was started with.

Environment:
    SLIDEPACK_SKILL_VENV   where the fallback venv lives. Default: the user cache directory
                           (under LOCALAPPDATA on Windows, ~/.cache elsewhere; in a slidepack-skill/venv folder).

Exit codes: whatever the target script returns, or 2 when the environment could not be prepared.
"""

import ast
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _make_output_encoding_safe():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def read_dependencies(script):
    """Return the `dependencies` list from the script's PEP 723 header (empty if none)."""
    with open(script, encoding="utf-8") as fh:
        text = fh.read()
    block = re.search(r"^# /// script\s*$(.*?)^# ///\s*$", text, re.M | re.S)
    if not block:
        return []
    body = "\n".join(re.sub(r"^# ?", "", ln) for ln in block.group(1).splitlines())
    m = re.search(r"dependencies\s*=\s*(\[.*?\])", body, re.S)
    return ast.literal_eval(m.group(1)) if m else []


def dist_name(requirement):
    return re.split(r"[<>=!~;\[ ]", requirement, maxsplit=1)[0]


def already_installed(requirements):
    try:
        from importlib import metadata
    except ImportError:
        return False
    for req in requirements:
        try:
            metadata.version(dist_name(req))
        except metadata.PackageNotFoundError:
            return False
    return True


def venv_dir():
    override = os.environ.get("SLIDEPACK_SKILL_VENV")
    if override:
        return override
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "slidepack-skill", "venv")


def venv_python(path):
    sub = ("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")
    return os.path.join(path, *sub)


def prepare_venv(requirements):
    """Create (or reuse) the private venv and make sure `requirements` are installed in it."""
    path = venv_dir()
    py = venv_python(path)
    if not os.path.exists(py):
        print("slidepack-skill: creating a private virtual environment at " + path, file=sys.stderr)
        import venv
        existed = os.path.exists(path)
        try:
            venv.create(path, with_pip=True)
        except Exception as e:  # e.g. Debian/Ubuntu without python3-venv: ensurepip is missing
            print("slidepack-skill: could not create it: %s" % e, file=sys.stderr)
            if not existed:  # never delete a directory this run did not create
                shutil.rmtree(path, ignore_errors=True)
            return None
    if not already_installed_in(py, requirements):
        print("slidepack-skill: installing " + ", ".join(requirements) + " into that environment",
              file=sys.stderr)
        rc = subprocess.call([py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", *requirements])
        if rc != 0:
            return None
    return py


def already_installed_in(py, requirements):
    code = (
        "import sys\nfrom importlib import metadata\n"
        "for r in sys.argv[1:]:\n"
        "    try: metadata.version(r)\n"
        "    except metadata.PackageNotFoundError: sys.exit(1)\n"
    )
    return subprocess.call([py, "-c", code, *map(dist_name, requirements)]) == 0


def main(argv):
    _make_output_encoding_safe()
    if len(argv) < 2:
        print("usage: python run.py <script.py> [args...]", file=sys.stderr)
        return 2
    name, args = argv[1], argv[2:]
    script = name if os.path.isabs(name) else os.path.join(HERE, name)
    if not os.path.isfile(script):
        print("run.py: no such script: " + name, file=sys.stderr)
        return 2

    requirements = read_dependencies(script)
    if not requirements or already_installed(requirements):
        return subprocess.call([sys.executable, script, *args])

    uv = shutil.which("uv")
    if uv:
        cmd = [uv, "run", "--no-project", "--quiet"]
        for req in requirements:
            cmd += ["--with", req]
        return subprocess.call(cmd + ["python", script, *args])

    py = prepare_venv(requirements)
    if py:
        return subprocess.call([py, script, *args])

    print("run.py: could not set up " + ", ".join(requirements) + ".\n"
          "  Install uv (https://docs.astral.sh/uv/) or allow a private venv; this script does not\n"
          "  install packages into your own Python.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
