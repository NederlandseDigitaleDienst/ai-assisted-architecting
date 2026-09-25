"""Click-through links from a links file: loading, discovery, rendering in
HTML views and slide decks, and the checks in validate and render."""
import pytest

from archi_tool.cli import main
from archi_tool.discovery import discover_links
from archi_tool.links import check_link_files, links_for, load_links, with_base
from archi_tool.model import ModelError
from archi_tool.render_html import render_view_html
from archi_tool.render_slides import load_deck, render_deck_html
from archi_tool.validate import validate

LINKS_TOML = """\
["testview"]
"Gebied Alfa" = "../script-generated-svg/alfa.svg"
"""


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- loading and paths -------------------------------------------------------

def test_load_links_and_links_for(tmp_path):
    links = load_links(write(tmp_path / "links.toml", LINKS_TOML))
    assert links == {"testview": {"Gebied Alfa": "../script-generated-svg/alfa.svg"}}
    assert links_for(links, "testview", base="../") == {
        "Gebied Alfa": "../../script-generated-svg/alfa.svg"}
    assert links_for(links, "andere-view") == {}
    assert load_links(None) == {}


def test_load_links_rejects_malformed_section(tmp_path):
    path = write(tmp_path / "links.toml", '["testview"]\n"Gebied Alfa" = 3\n')
    with pytest.raises(ModelError, match="sectie 'testview'"):
        load_links(path)


def test_with_base_leaves_urls_absolute_paths_and_anchors_alone():
    assert with_base("x.html", "../") == "../x.html"
    for target in ("https://example.org/x", "/abs/x.html", "#anker",
                   "mailto:a@b.nl"):
        assert with_base(target, "../") == target


# --- discovery ---------------------------------------------------------------

def test_discover_links_is_opt_in(tmp_path):
    model = write(tmp_path / "m.archimate", "<model/>")
    assert discover_links(model) is None


def test_discover_links_from_config_and_missing_path(tmp_path):
    model = write(tmp_path / "m.archimate", "<model/>")
    write(tmp_path / "tools" / "links.toml", LINKS_TOML)
    write(tmp_path / "archi.toml", '[tool.archi]\nlinks = "tools/links.toml"\n')
    assert discover_links(model) == (tmp_path / "tools" / "links.toml").resolve()
    write(tmp_path / "archi.toml", '[tool.archi]\nlinks = "weg.toml"\n')
    with pytest.raises(ModelError, match="Linkspad uit archi.toml bestaat niet"):
        discover_links(model)


# --- rendering ---------------------------------------------------------------

def test_view_html_wraps_linked_elements_only(model):
    output = render_view_html(model, model.diagrams()[0],
                              links={"Gebied Alfa": "../svg/alfa.svg"})
    assert '<a class="box-link" href="../svg/alfa.svg"><div class="box' in output
    assert output.count('class="box-link"') == 1      # Bouwblok Beta: no link
    assert ".box-link" in output                       # styling present


def test_slides_prefix_links_for_the_deck_directory(model, tmp_path):
    deck = write(tmp_path / "decks" / "d.toml",
                 'title = "D"\n\n[[slides]]\ntype = "view"\nview = "Testview"\n')
    links = load_links(write(tmp_path / "links.toml", LINKS_TOML))
    output = render_deck_html(model, load_deck(deck, model), links=links)
    assert 'href="../../script-generated-svg/alfa.svg"' in output


# --- checks ------------------------------------------------------------------

def test_validate_warns_for_unknown_link_elements(model):
    links = {"testview": {"Gebied Alfa": "a.svg", "Doel Gamma": "g.svg"},
             "eigen-svg": {"Bouwblok Beta": "b.svg", "Bestaat Niet": "x.svg"}}
    errors, warnings = validate(model, links=links)
    assert errors == []
    # Doel Gamma exists in the model but is not drawn in Testview
    assert "Link in 'testview': element 'Doel Gamma' staat niet in die view" in warnings
    assert ("Link in 'eigen-svg': geen element met de naam 'Bestaat Niet' "
            "in het model") in warnings
    assert len(warnings) == 2


def test_check_link_files(tmp_path):
    views = tmp_path / "views"
    write(views / "script-generated-svg" / "eigen.svg", "<svg/>")
    write(views / "script-generated-svg" / "doel.svg", "<svg/>")
    links = {
        "testview": {"A": "../script-generated-svg/doel.svg",
                     "B": "../script-generated-svg/weg.svg",
                     "C": "https://example.org"},
        "eigen": {"D": "doel.svg"},
        "hernoemde-view": {"E": "doel.svg"},
    }
    warnings = check_link_files(links, views, views / "html", {"testview"})
    assert len(warnings) == 2
    assert any("'testview' → 'B'" in w and "weg.svg" in w for w in warnings)
    assert any("sectie 'hernoemde-view' hoort bij geen view" in w
               for w in warnings)


def test_render_command_uses_configured_links(model_path, tmp_path, capsys,
                                              monkeypatch):
    write(tmp_path / "links.toml",
          LINKS_TOML + '\n["weg-view"]\n"Gebied Alfa" = "x.html"\n')
    write(tmp_path / "archi.toml", '[tool.archi]\nlinks = "links.toml"\n')
    monkeypatch.chdir(tmp_path)
    status = main(["--model", str(model_path), "render",
                   "--out", str(tmp_path / "views"),
                   "--decks", str(tmp_path / "decks")])
    output = capsys.readouterr().out
    assert status == 0
    html = (tmp_path / "views" / "html" / "testview.html").read_text(encoding="utf-8")
    assert 'href="../script-generated-svg/alfa.svg"' in html
    # the target was never generated, and 'weg-view' matches nothing
    assert "WAARSCHUWING: Links: 'testview' → 'Gebied Alfa'" in output
    assert "sectie 'weg-view' hoort bij geen view" in output
