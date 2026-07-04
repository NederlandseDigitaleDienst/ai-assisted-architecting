"""Locate the model file and the conventions list without assuming this repo.

The CLI used to hardcode ``models/ado.archimate`` and find the conventions at
``<model>/../../docs/conventies.md``. Both assumptions are specific to this
repository. Discovery makes ``archi`` work on any model, in any layout, while
keeping the ADO defaults working through an ``archi.toml`` in the repo root.

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

# Keys that ship with the tool. A project can override this by pointing at its
# own conventions doc; without one, these keep the property-key check useful.
# Mirrors docs/conventies.md §3 so behaviour is identical for this repo when no
# doc is found (it normally is, via archi.toml).
DEFAULT_PROPERTY_KEYS = {
    "Omschrijving",
    "Toelichting",
    "Bron",
    "Capability-niveau",
    "Niveau (herkomst)",
    "Driver-categorie",
    "constraint-type",
    "Artefact-type",
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
            raise ModelError(
                f"Modelpad uit {config_path.name} bestaat niet: {path}")
        return path

    candidates = sorted(start.glob("*.archimate"))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ModelError(
            "Geen modelbestand gevonden. Geef --model <pad>, of zet "
            "`[tool.archi] model = \"...\"` in archi.toml, of draai in een map "
            "met precies één .archimate-bestand.")
    names = ", ".join(c.name for c in candidates)
    raise ModelError(
        f"Meerdere .archimate-bestanden gevonden ({names}). Kies er één met "
        "--model <pad> of leg het vast in archi.toml.")


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
                f"Conventiepad uit {config_path.name} bestaat niet: {path}")
        keys = allowed_property_keys(path)
        if not keys:
            raise ModelError(
                f"Conventiebestand {path} bevat geen Property-keys-sectie.")
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
