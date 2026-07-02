from lxml import etree

from archi_tool.model import XSI_TYPE
from archi_tool.render import MARKER
from archi_tool.render_html import (absolute_boxes, border_point,
                                    render_all_html, render_view_html)


def test_border_point_horizontal_and_vertical():
    box = {"x": 0, "y": 0, "w": 100, "h": 50}
    assert border_point(box, 200, 25) == (100, 25)   # right border
    assert border_point(box, 50, 200) == (50, 50)    # bottom border


def test_absolute_boxes_resolve_nested_offsets(model):
    diagrams_folder = model.folder("diagrams")
    diagram = etree.SubElement(diagrams_folder, "element", {
        XSI_TYPE: "archimate:ArchimateDiagramModel",
        "name": "Genest", "id": "id-view-abs"})
    outer = etree.SubElement(diagram, "child", {
        XSI_TYPE: "archimate:DiagramObject", "id": "id-obj-o",
        "archimateElement": "id-el-alfa"})
    etree.SubElement(outer, "bounds", {
        "x": "40", "y": "40", "width": "400", "height": "300"})
    inner = etree.SubElement(outer, "child", {
        XSI_TYPE: "archimate:DiagramObject", "id": "id-obj-i",
        "archimateElement": "id-el-beta"})
    etree.SubElement(inner, "bounds", {
        "x": "16", "y": "60", "width": "220", "height": "70"})

    boxes = {b["id"]: b for b in absolute_boxes(diagram, model.id_index())}
    assert boxes["id-obj-o"]["container"] is True
    assert (boxes["id-obj-i"]["x"], boxes["id-obj-i"]["y"]) == (56, 100)


def test_render_view_html_structure(model):
    output = render_view_html(model, model.diagrams()[0])
    assert output.startswith(MARKER)
    assert "<nldd-app-view>" in output
    assert "Gebied Alfa" in output and "Bouwblok Beta" in output
    assert 'class="box leaf strategy"' in output
    assert 'marker-start="url(#diamond)"' in output   # aggregation edge
    # lines must live OUTSIDE <defs>, otherwise they are not painted
    assert "</defs>" in output
    assert output.index("</defs>") < output.index("<line")
    assert "@nldd/design-system@" in output
    # navigation back to the index and a legend inside the canvas
    assert 'href="index.html"' in output
    assert 'class="legend"' in output
    assert "Strategie" in output      # layer chip for the fixture's boxes
    assert "bevat" in output          # containment edge hint (aggregation)


def test_render_all_html_index_and_cleanup(model, tmp_path):
    out = tmp_path / "html"
    out.mkdir()
    stale = out / "weg.html"
    stale.write_text(f"{MARKER}\noud", encoding="utf-8")

    render_all_html(model, out)
    assert (out / "testview.html").exists()
    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="testview.html"' in index
    assert "<nldd-card" in index
    assert 'class="thumb-svg"' in index   # miniature per view card
    assert not stale.exists()

    written, removed = render_all_html(model, out)
    assert written == [] and removed == []
