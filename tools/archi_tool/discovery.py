"""Locate the model file and the conventions list without assuming a layout.

An earlier version hardcoded a fixed model path and found the conventions doc
at a fixed location. Discovery makes ``archi`` work on any model, in any
layout: a project points at its model and conventions through an ``archi.toml``
(or ``pyproject.toml``), or the tool falls back to sensible defaults.

Resolution order for the model:
  1. an explicit ``--model`` path (handled by the caller)
  2. ``[tool.archi] model`` in ``archi.toml`` / ``pyproject.toml``, searched
     upward from the working directory
  3. the single ``.archimate`` file in the working directory

Resolution order for the conventions list:
  1. ``[tool.archi] conventions`` in the config file
  2. a ``conventies.md`` / ``conventions.md`` next to the model (legacy layout)
  3. the built-in default set, so the property-key check stays meaningful even
     without a project list
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from .model import ModelError

CONFIG_NAMES = ("archi.toml", "pyproject.toml")
CONVENTION_NEIGHBOURS = ("conventies.md", "conventions.md")

# Generic keys that ship with the tool as a fallback allowlist. A project
# overrides this by pointing at its own conventions doc (with a Property-keys
# section); without one, these keep the property-key check useful instead of
# silently disabling it. Descriptions belong in Archi's documentation field,
# not in a property, so "Omschrijving"/"Toelichting" are deliberately absent
# (ADR 0009).
DEFAULT_PROPERTY_KEYS = {
    "Bron",
}


def _read_archi_config(start):
    """Return ``([tool.archi]`` table, config file path) searching upward.

    Looks in the working directory and its parents for the first config file
    that carries a ``[tool.archi]`` table. Returns ``({}, None)`` when none is
    found, so callers can fall back to filesystem discovery.
    """
    for directory in (start, *start.parents):
        for name in CONFIG_NAMES:
            candidate = directory / name
            if not candidate.exists():
                continue
            try:
                data = tomllib.loads(candidate.read_text(encoding="utf-8"))
            except (tomllib.TOMLDecodeError, OSError):
                continue
            table = data.get("tool", {}).get("archi")
            if isinstance(table, dict):
                return table, candidate
    return {}, None


def discover_model(explicit=None, start=None):
    """Resolve the model path. Raise ModelError with guidance when ambiguous.

    ``explicit`` wins when given. Otherwise consult ``[tool.archi] model`` in a
    config file, then fall back to the single ``.archimate`` in ``start``.
    """
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise ModelError(f"Modelbestand niet gevonden: {path}")
        return path

    start = Path(start or Path.cwd())
    table, config_path = _read_archi_config(start)
    if "model" in table:
        # a relative path in config is relative to the config file's directory
        path = (config_path.parent / table["model"]).resolve()
        if not path.exists():
            raise ModelError(f"Modelpad uit {config_path.name} bestaat niet: {path}")
        return path

    candidates = sorted(start.glob("*.archimate"))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ModelError(
            "Geen modelbestand gevonden. Geef --model <pad>, of zet "
            '`[tool.archi] model = "..."` in archi.toml, of draai in een map '
            "met precies één .archimate-bestand."
        )
    names = ", ".join(c.name for c in candidates)
    raise ModelError(
        f"Meerdere .archimate-bestanden gevonden ({names}). Kies er één met "
        "--model <pad> of leg het vast in archi.toml."
    )


def discover_links(model_path, start=None):
    """Return the path of the links file, or None when none is configured.

    Only ``[tool.archi] links`` in a config file counts (there is no
    filesystem fallback: click-through is opt-in). A configured path that
    does not exist is a config error.
    """
    start = Path(start or Path(model_path).resolve().parent)
    table, config_path = _read_archi_config(start)
    if "links" not in table:
        return None
    path = (config_path.parent / table["links"]).resolve()
    if not path.exists():
        raise ModelError(f"Linkspad uit {config_path.name} bestaat niet: {path}")
    return path


FONT_CHOICES = ("system", "rijkssans")


def discover_fonts(model_path, start=None) -> str:
    """The font choice for rendered HTML: ``[tool.archi] fonts``, default
    "system". "rijkssans" is reserved for the Dutch central government and
    parties working on its behalf (see NOTICE)."""
    start = Path(start or Path(model_path).resolve().parent)
    table, config_path = _read_archi_config(start)
    fonts = table.get("fonts", "system")
    if fonts not in FONT_CHOICES:
        allowed = ", ".join(f'"{c}"' for c in FONT_CHOICES)
        raise ModelError(
            f"Ongeldige waarde voor fonts in {config_path.name}: {fonts!r}. "
            f"Kies uit {allowed}."
        )
    return fonts


def discover_conventions(model_path, start=None):
    """Return (allowed_property_keys, source_label).

    ``source_label`` names where the keys came from, for diagnostics. Falls
    back to the built-in default set so the check never silently disappears.
    """
    from .validate import allowed_property_keys

    start = Path(start or Path.cwd())
    table, config_path = _read_archi_config(start)
    if "conventions" in table:
        # an explicit path in config is authoritative: a missing file or one
        # without a Property-keys section is a config error, not a reason to
        # silently fall back to the built-in set
        path = (config_path.parent / table["conventions"]).resolve()
        if not path.exists():
            raise ModelError(
                f"Conventiepad uit {config_path.name} bestaat niet: {path}"
            )
        keys = allowed_property_keys(path)
        if not keys:
            raise ModelError(
                f"Conventiebestand {path} bevat geen Property-keys-sectie."
            )
        return keys, str(path)

    model_dir = Path(model_path).resolve().parent
    for directory in (model_dir, *model_dir.parents):
        for name in CONVENTION_NEIGHBOURS:
            candidate = directory / "docs" / name
            if candidate.exists():
                keys = allowed_property_keys(candidate)
                if keys:
                    return keys, str(candidate)

    return set(DEFAULT_PROPERTY_KEYS), "ingebouwde standaardset"
