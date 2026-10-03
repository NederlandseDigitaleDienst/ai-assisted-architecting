"""The shipped example must stay valid, and its committed Mermaid views must
match what `archi render` produces, so the README never shows stale output."""

from pathlib import Path

from archi_tool.model import ArchiModel
from archi_tool.render import render_all
from archi_tool.validate import validate

EXAMPLE = Path(__file__).parent.parent / "examples" / "vergunningverlening"


def test_example_model_validates():
    errors, _ = validate(ArchiModel(EXAMPLE / "vergunningverlening.archimate"))
    assert errors == []


def test_example_views_are_up_to_date(tmp_path, monkeypatch):
    # render shows the model path relative to the working directory, so run
    # from the example folder, as `archi render` there does
    monkeypatch.chdir(EXAMPLE)
    model = ArchiModel(EXAMPLE / "vergunningverlening.archimate")
    render_all(model, tmp_path)
    committed = {
        p.name: p.read_text(encoding="utf-8") for p in (EXAMPLE / "views").glob("*.md")
    }
    fresh = {p.name: p.read_text(encoding="utf-8") for p in tmp_path.glob("*.md")}
    assert committed.keys() == fresh.keys(), "run `archi render` in the example"
    for name, text in fresh.items():
        assert committed[name] == text, (
            f"{name} is stale: run `archi render` in the example"
        )
