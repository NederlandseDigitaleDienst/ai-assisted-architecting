"""Check that every file carrying the release version agrees, and at release
time that the tag and the changelog match it.

    uv run python scripts/check_release.py                  # versions agree
    uv run python scripts/check_release.py --tag v1.2.3 --notes notes.md

With --tag, the changelog must have a "## [1.2.3]" section; --notes writes
that section's body to a file for the GitHub Release.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def versions(root: Path = ROOT) -> dict[str, str]:
    """The version as each file states it."""
    found = {
        "pyproject.toml": tomllib.loads((root / "pyproject.toml").read_text("utf-8"))[
            "project"
        ]["version"],
        ".claude-plugin/plugin.json": json.loads(
            (root / ".claude-plugin" / "plugin.json").read_text("utf-8")
        )["version"],
        ".cursor-plugin/plugin.json": json.loads(
            (root / ".cursor-plugin" / "plugin.json").read_text("utf-8")
        )["version"],
    }
    lock = tomllib.loads((root / "uv.lock").read_text("utf-8"))
    found["uv.lock"] = next(
        p["version"] for p in lock["package"] if p["name"] == "archi-cli"
    )
    match = re.search(
        r'^softwareVersion:\s*"?([^"\s]+)"?\s*$',
        (root / "publiccode.yml").read_text("utf-8"),
        re.MULTILINE,
    )
    found["publiccode.yml"] = match.group(1) if match else "(ontbreekt)"
    return found


def changelog_section(version: str, root: Path = ROOT) -> str | None:
    """The body of the "## [version]" section of CHANGELOG.md, or None."""
    text = (root / "CHANGELOG.md").read_text("utf-8")
    match = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## |^\[[^\]]+\]: |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else None


def check(tag: str | None = None, root: Path = ROOT) -> tuple[list[str], str | None]:
    """(errors, release notes). Notes are only looked up with a tag."""
    errors = []
    found = versions(root)
    if len(set(found.values())) != 1:
        listed = ", ".join(f"{f}: {v}" for f, v in found.items())
        errors.append(f"Versies lopen uiteen ({listed})")
    version = found["pyproject.toml"]
    notes = None
    if tag is not None:
        if tag != f"v{version}":
            errors.append(
                f"Tag {tag} hoort bij versie {tag.removeprefix('v')}, niet {version}"
            )
        notes = changelog_section(version, root)
        if not notes:
            errors.append(f"CHANGELOG.md heeft geen gevulde sectie '## [{version}]'")
    return errors, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", help="release tag, e.g. v1.2.3")
    parser.add_argument("--notes", type=Path, help="write the changelog section here")
    args = parser.parse_args(argv)
    errors, notes = check(args.tag)
    for error in errors:
        print(f"FOUT: {error}", file=sys.stderr)
    if errors:
        return 1
    if args.notes and notes:
        args.notes.write_text(notes + "\n", encoding="utf-8")
    print(f"Versie {versions()['pyproject.toml']} klopt overal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
