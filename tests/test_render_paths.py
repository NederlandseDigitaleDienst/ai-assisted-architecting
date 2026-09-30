"""Renders must be byte-identical across machines. Discovery can hand the
model an absolute path (resolved via archi.toml); the generated output must
still show a stable, relative path, never a machine-specific absolute one."""

from archi_tool.render import display_model_path


class _FakeModel:
    def __init__(self, path):
        self.path = str(path)


def test_absolute_path_inside_cwd_becomes_relative(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    absolute = tmp_path / "models" / "model.archimate"
    assert display_model_path(_FakeModel(absolute)) == "models/model.archimate"


def test_path_outside_cwd_falls_back_to_name(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    elsewhere = tmp_path / "elders" / "model.archimate"
    # not a machine-specific absolute path leaking into committed output
    assert display_model_path(_FakeModel(elsewhere)) == "model.archimate"


def test_relative_path_stays_relative(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert (
        display_model_path(_FakeModel("models/model.archimate"))
        == "models/model.archimate"
    )
