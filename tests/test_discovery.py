"""Tests for model and conventions discovery, in a clean tree with no ADO
context, so nothing leaks in from the repo the tests happen to run in."""

import pytest
from archi_tool.discovery import (
    DEFAULT_PROPERTY_KEYS,
    discover_conventions,
    discover_model,
)
from archi_tool.model import ModelError


def _write_model(path):
    """A minimal well-formed shell is enough; discovery only touches paths."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('<?xml version="1.0"?><model/>', encoding="utf-8")
    return path


def test_explicit_model_wins(tmp_path):
    wanted = _write_model(tmp_path / "gekozen.archimate")
    _write_model(tmp_path / "andere.archimate")
    assert discover_model(str(wanted), start=tmp_path) == wanted


def test_explicit_missing_model_errors(tmp_path):
    with pytest.raises(ModelError, match="niet gevonden"):
        discover_model(str(tmp_path / "weg.archimate"), start=tmp_path)


def test_single_archimate_in_cwd_is_found(tmp_path):
    only = _write_model(tmp_path / "enig.archimate")
    assert discover_model(None, start=tmp_path) == only


def test_no_model_gives_helpful_error(tmp_path):
    with pytest.raises(ModelError, match="Geen modelbestand gevonden"):
        discover_model(None, start=tmp_path)


def test_multiple_models_without_config_errors(tmp_path):
    _write_model(tmp_path / "een.archimate")
    _write_model(tmp_path / "twee.archimate")
    with pytest.raises(ModelError, match="Meerdere .archimate-bestanden"):
        discover_model(None, start=tmp_path)


def test_archi_toml_selects_the_model(tmp_path):
    _write_model(tmp_path / "een.archimate")
    chosen = _write_model(tmp_path / "sub" / "hoofd.archimate")
    (tmp_path / "archi.toml").write_text(
        '[tool.archi]\nmodel = "sub/hoofd.archimate"\n', encoding="utf-8"
    )
    assert discover_model(None, start=tmp_path) == chosen


def test_archi_toml_model_relative_to_config_not_cwd(tmp_path):
    """A relative model path resolves against the config file, so running
    from a nested working directory still finds it."""
    chosen = _write_model(tmp_path / "models" / "m.archimate")
    (tmp_path / "archi.toml").write_text(
        '[tool.archi]\nmodel = "models/m.archimate"\n', encoding="utf-8"
    )
    nested = tmp_path / "deep" / "deeper"
    nested.mkdir(parents=True)
    assert discover_model(None, start=nested) == chosen


def test_pyproject_tool_archi_is_read(tmp_path):
    chosen = _write_model(tmp_path / "p.archimate")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.archi]\nmodel = "p.archimate"\n', encoding="utf-8"
    )
    # a second model means bare filesystem discovery would be ambiguous;
    # config must disambiguate
    _write_model(tmp_path / "q.archimate")
    assert discover_model(None, start=tmp_path) == chosen


def test_conventions_fall_back_to_builtin_set(tmp_path):
    model = _write_model(tmp_path / "m.archimate")
    keys, source = discover_conventions(model, start=tmp_path)
    assert keys == set(DEFAULT_PROPERTY_KEYS)
    assert source == "ingebouwde standaardset"


def test_conventions_from_docs_next_to_model(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "conventies.md").write_text(
        "## 3. Property-keys\n\n- `EigenKey` — iets\n", encoding="utf-8"
    )
    # model lives one level down; docs/ is found by walking up from it
    nested_model = _write_model(tmp_path / "models" / "m.archimate")
    keys, source = discover_conventions(nested_model, start=tmp_path)
    assert keys == {"EigenKey"}
    assert source.endswith("conventies.md")


def test_conventions_explicit_path_in_config(tmp_path):
    (tmp_path / "eigen.md").write_text(
        "## Property-keys\n\n- `ViaConfig` — x\n", encoding="utf-8"
    )
    (tmp_path / "archi.toml").write_text(
        '[tool.archi]\nconventions = "eigen.md"\n', encoding="utf-8"
    )
    model = _write_model(tmp_path / "m.archimate")
    keys, source = discover_conventions(model, start=tmp_path)
    assert keys == {"ViaConfig"}
    assert source.endswith("eigen.md")


def test_conventions_config_path_missing_fails_loudly(tmp_path):
    """A typo'd conventions path in config must not silently fall back to the
    built-in set; that would validate against the wrong list unnoticed."""
    (tmp_path / "archi.toml").write_text(
        '[tool.archi]\nconventions = "bestaat-niet.md"\n', encoding="utf-8"
    )
    model = _write_model(tmp_path / "m.archimate")
    with pytest.raises(ModelError, match="bestaat niet"):
        discover_conventions(model, start=tmp_path)


def test_conventions_config_path_without_section_fails(tmp_path):
    (tmp_path / "leeg.md").write_text("# Geen keys hier\n", encoding="utf-8")
    (tmp_path / "archi.toml").write_text(
        '[tool.archi]\nconventions = "leeg.md"\n', encoding="utf-8"
    )
    model = _write_model(tmp_path / "m.archimate")
    with pytest.raises(ModelError, match="Property-keys-sectie"):
        discover_conventions(model, start=tmp_path)
