"""Views whose names slugify alike must still get their own output file, and
every link to a view must point at that file."""

from archi_tool.model import XSI_TYPE
from archi_tool.render import render_all, view_stems
from archi_tool.render_html import render_all_html
from archi_tool.render_slides import load_deck, render_deck_html
from archi_tool.validate import validate
from lxml import etree


def add_colliding_view(model):
    """Add view "Testview!" (slug "testview", like the fixture's "Testview")
    and a reference to it from the fixture view."""
    views = model.folder("diagrams")
    second = etree.SubElement(
        views,
        "element",
        {
            XSI_TYPE: "archimate:ArchimateDiagramModel",
            "name": "Testview!",
            "id": "id-view-2",
        },
    )
    obj = etree.SubElement(
        second,
        "child",
        {
            XSI_TYPE: "archimate:DiagramObject",
            "id": "id-obj-gamma",
            "archimateElement": "id-el-gamma",
        },
    )
    etree.SubElement(
        obj, "bounds", {"x": "10", "y": "10", "width": "120", "height": "55"}
    )
    ref = etree.SubElement(
        model.resolve("id-view-1"),
        "child",
        {
            XSI_TYPE: "archimate:DiagramModelReference",
            "id": "id-ref-2",
            "model": "id-view-2",
        },
    )
    etree.SubElement(
        ref, "bounds", {"x": "400", "y": "60", "width": "120", "height": "55"}
    )


def test_view_stems_suffix_every_colliding_view(model):
    add_colliding_view(model)
    assert view_stems(model) == {
        "id-view-1": "testview-view-1",
        "id-view-2": "testview-view-2",
    }


def test_view_stems_do_not_depend_on_model_order(model):
    add_colliding_view(model)
    before = view_stems(model)
    # moving the first view behind the second, as `archi move` can do
    model.move("id-view-1", "Archief", create_subfolder=True)
    assert view_stems(model) == before


def test_view_stems_fall_back_to_the_full_id(model):
    # the colliding views share their short id suffix, and that suffixed
    # stem is also the plain stem of a third view: only full ids are unique
    views = model.folder("diagrams")
    for view_id, name in (
        ("id-view-a", "Testview view-bbb"),
        ("id-view-bbbbbbbb-1", "Testview!"),
        ("id-view-bbbbbbbb-2", "Testview?"),
    ):
        etree.SubElement(
            views,
            "element",
            {XSI_TYPE: "archimate:ArchimateDiagramModel", "name": name, "id": view_id},
        )
    model.resolve("id-view-1").set("name", "Andere view")
    assert view_stems(model) == {
        "id-view-1": "andere-view",
        "id-view-a": "testview-view-bbb",
        "id-view-bbbbbbbb-1": "testview-view-bbbbbbbb-1",
        "id-view-bbbbbbbb-2": "testview-view-bbbbbbbb-2",
    }


def test_render_writes_one_file_per_view(model, tmp_path):
    add_colliding_view(model)
    render_all(model, tmp_path / "md")
    render_all_html(model, tmp_path / "html")
    for folder, ext in (("md", "md"), ("html", "html")):
        assert not (tmp_path / folder / f"testview.{ext}").exists()
        first = (tmp_path / folder / f"testview-view-1.{ext}").read_text(
            encoding="utf-8"
        )
        second = (tmp_path / folder / f"testview-view-2.{ext}").read_text(
            encoding="utf-8"
        )
        assert "Gebied Alfa" in first and "Gebied Alfa" not in second
        assert "Doel Gamma" in second


def test_view_reference_and_slide_link_use_the_unique_file(model, tmp_path):
    add_colliding_view(model)
    render_all_html(model, tmp_path)
    page = (tmp_path / "testview-view-1.html").read_text(encoding="utf-8")
    assert '<a href="testview-view-2.html">Testview!</a>' in page

    deck_path = tmp_path / "d.toml"
    deck_path.write_text(
        'title = "D"\n\n[[slides]]\ntype = "view"\nview = "id-view-2"\n',
        encoding="utf-8",
    )
    output = render_deck_html(model, load_deck(deck_path, model))
    assert 'href="../testview-view-2.html"' in output


def test_validate_warns_for_colliding_view_names(model):
    add_colliding_view(model)
    errors, warnings = validate(model)
    assert errors == []
    assert any(
        "Views met dezelfde bestandsnaam 'testview'" in w
        and "testview-view-1" in w
        and "testview-view-2" in w
        for w in warnings
    )
