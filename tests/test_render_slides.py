import pytest

from archi_tool.model import ModelError
from archi_tool.render import MARKER
from archi_tool.render_html import diagram_canvas
from archi_tool.render_slides import (load_deck, render_all_slides,
                                      render_deck_html)

DECK_TOML = """\
title = "Testdeck"
speaker = "Tester"
affiliation = "Testbureau"
date = "3 juli 2026"

[[slides]]
type = "title"
notes = "Welkom."

[[slides]]
type = "section"
title = "Hoofdstuk"

[[slides]]
type = "view"
view = "Testview"

[[slides]]
type = "view"
view = "id-view-1"
title = "Nogmaals, via het id"

[[slides]]
type = "text"
title = "Tussenstuk"
body = \"\"\"
Eerste alinea van het verhaal.

Tweede alinea, na een witregel.
\"\"\"

[[slides]]
type = "bullets"
title = "Punten"
bullets = ["Eerste punt", "Tekst met <b>markup</b>"]
gov = "Voor de overheid."

[[slides]]
type = "closing"
title = "Dank"
link = { href = "https://example.org", label = "het repo" }
"""


def write_deck(tmp_path, content=DECK_TOML, name="testdeck.toml"):
    decks = tmp_path / "decks"
    decks.mkdir(exist_ok=True)
    path = decks / name
    path.write_text(content, encoding="utf-8")
    return path


def test_load_deck_structure(model, tmp_path):
    deck = load_deck(write_deck(tmp_path), model)
    assert deck["slug"] == "testdeck"               # from the file stem
    assert [s["type"] for s in deck["slides"]] == [
        "title", "section", "view", "view", "text", "bullets", "closing"]
    assert deck["slides"][2]["diagram"].get("id") == "id-view-1"
    assert deck["slides"][3]["diagram"].get("id") == "id-view-1"


def test_render_deck_marker_chrome_and_determinism(model, tmp_path):
    path = write_deck(tmp_path)
    output = render_deck_html(model, load_deck(path, model))
    assert output.startswith(MARKER)
    assert '<html lang="nl">' in output
    assert "@nldd/design-system@" in output
    assert 'class="slide slide-title dark"' in output
    assert ">01/07<" in output                      # zero-padded counter
    assert 'class="progress"' in output
    # the date is deck data, rendered verbatim — never "today"
    assert "3 juli 2026" in output
    assert "Intl.DateTimeFormat" not in output
    assert output == render_deck_html(model, load_deck(path, model))


def test_view_slide_reuses_model_layout(model, tmp_path):
    output = render_deck_html(model, load_deck(write_deck(tmp_path), model))
    assert "Gebied Alfa" in output
    assert 'class="box leaf strategy"' in output
    assert "left:60px;top:60px" in output           # layout from the model
    assert 'class="type-icon"' in output
    assert 'class="legend"' in output
    # marker ids are prefixed per slide (first view slide is slide 3)
    assert 'id="s3-diamond"' in output
    assert 'marker-start="url(#s3-diamond)"' in output
    # the escape hatch to the standalone view page, one directory up
    assert 'href="../testview.html"' in output


def test_text_and_bullets_slides(model, tmp_path):
    output = render_deck_html(model, load_deck(write_deck(tmp_path), model))
    assert 'class="slide slide-text dark"' in output
    assert "<p>Eerste alinea van het verhaal.</p>" in output
    assert "<p>Tweede alinea, na een witregel.</p>" in output
    assert "Welkom." in output                      # notes rendered hidden
    assert 'class="notes" hidden' in output
    assert "Specifiek voor de overheid" in output
    assert "&lt;b&gt;markup&lt;/b&gt;" in output    # user text is escaped
    assert 'href="https://example.org"' in output


def test_load_deck_unknown_view(model, tmp_path):
    path = write_deck(tmp_path, """\
title = "Kapot"

[[slides]]
type = "view"
view = "Bestaat Niet"
""")
    with pytest.raises(ModelError, match="bestaat niet in het model"):
        load_deck(path, model)
    with pytest.raises(ModelError, match="Beschikbare views: Testview"):
        load_deck(path, model)


def test_load_deck_unknown_type_and_key(model, tmp_path):
    path = write_deck(tmp_path, """\
title = "Kapot"

[[slides]]
type = "grafiek"
""")
    with pytest.raises(ModelError, match="onbekend type 'grafiek'"):
        load_deck(path, model)
    path = write_deck(tmp_path, """\
title = "Kapot"

[[slides]]
type = "section"
title = "Ok"
bullits = ["typo"]
""")
    with pytest.raises(ModelError, match="onbekende sleutel 'bullits'"):
        load_deck(path, model)


def test_load_deck_missing_title_and_body(model, tmp_path):
    path = write_deck(tmp_path, """\
[[slides]]
type = "title"
""")
    with pytest.raises(ModelError, match="'title' ontbreekt"):
        load_deck(path, model)
    path = write_deck(tmp_path, """\
title = "Kapot"

[[slides]]
type = "text"
title = "Zonder body"
""")
    with pytest.raises(ModelError, match="'body' ontbreekt"):
        load_deck(path, model)


def test_render_all_slides_cleanup_and_idempotence(model, tmp_path):
    write_deck(tmp_path)
    out = tmp_path / "slides"
    out.mkdir()
    stale = out / "weg.html"
    stale.write_text(f"{MARKER}\noud", encoding="utf-8")
    handmade = out / "handmatig.html"
    handmade.write_text("<p>zelf gemaakt</p>", encoding="utf-8")

    written, removed = render_all_slides(model, tmp_path / "decks", out)
    assert (out / "testdeck.html").exists()
    assert not stale.exists()                       # marker: cleaned up
    assert handmade.exists()                        # no marker: untouched
    assert removed == [stale]

    written, removed = render_all_slides(model, tmp_path / "decks", out)
    assert written == [] and removed == []


def test_render_all_slides_without_decks_dir(model, tmp_path):
    out = tmp_path / "slides"
    written, removed = render_all_slides(model, tmp_path / "geen-decks", out)
    assert written == [] and removed == []


def test_diagram_canvas_default_marker_ids(model):
    # regression for the render_view_html refactor: without a prefix the
    # marker ids must stay exactly "arrow"/"diamond" (byte-identical pages)
    canvas = diagram_canvas(model, model.diagrams()[0])
    assert 'id="arrow"' in canvas["svg"]
    assert 'marker-start="url(#diamond)"' in canvas["svg"]
