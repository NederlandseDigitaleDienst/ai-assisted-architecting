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


def test_tooltip_prefers_documentation_over_omschrijving(model):
    model.set_documentation("id-el-alfa", "Uit documentatie")
    model.set_property("id-el-alfa", "Omschrijving", "Uit property")
    model.set_property("id-el-beta", "Omschrijving", "Alleen property")
    output = render_view_html(model, model.diagrams()[0])
    assert 'title="Uit documentatie"' in output
    assert 'title="Uit property"' not in output
    assert 'title="Alleen property"' in output  # terugval voor oudere modellen


def test_element_boxes_carry_type_icon(model):
    output = render_view_html(model, model.diagrams()[0])
    # nested notation: every element box gets its ArchiMate icon top-right
    assert output.count('class="type-icon"') == 2   # alfa en beta
    assert 'x="10.3"' in output                     # Capability staircase


def test_view_extras_notes_groups_refs_bendpoints(model):
    diagram = etree.SubElement(model.folder("diagrams"), "element", {
        XSI_TYPE: "archimate:ArchimateDiagramModel",
        "name": "Extra's", "id": "id-view-extra"})
    note = etree.SubElement(diagram, "child", {
        XSI_TYPE: "archimate:Note", "id": "id-obj-note"})
    etree.SubElement(note, "bounds", {
        "x": "300", "y": "20", "width": "150", "height": "60"})
    etree.SubElement(note, "content").text = "notitie"
    group = etree.SubElement(diagram, "child", {
        XSI_TYPE: "archimate:Group", "id": "id-obj-group", "name": "Cluster"})
    etree.SubElement(group, "bounds", {
        "x": "20", "y": "20", "width": "260", "height": "160"})
    inner = etree.SubElement(group, "child", {
        XSI_TYPE: "archimate:DiagramObject", "id": "id-obj-in",
        "archimateElement": "id-el-gamma"})
    etree.SubElement(inner, "bounds", {
        "x": "20", "y": "30", "width": "120", "height": "55"})
    ref = etree.SubElement(diagram, "child", {
        XSI_TYPE: "archimate:DiagramModelReference", "id": "id-obj-ref",
        "model": "id-view-1"})
    etree.SubElement(ref, "bounds", {
        "x": "300", "y": "120", "width": "150", "height": "50"})
    # a bare connection (no relationship) attaches the note; one bendpoint
    conn = etree.SubElement(inner, "sourceConnection", {
        "id": "id-conn-note", "source": "id-obj-in", "target": "id-obj-note"})
    etree.SubElement(conn, "bendpoint", {"startX": "50", "startY": "-40"})
    note.set("targetConnections", "id-conn-note")

    output = render_view_html(model, diagram)
    assert 'class="box note"' in output and "notitie" in output
    assert 'class="box group"' in output and "Cluster" in output
    assert 'class="box ref"' in output and 'href="testview.html"' in output
    # nested child resolves group-relative bounds: (20+20, 20+30)
    assert "left:40px;top:50px" in output
    # bendpoint = source center (100, 77.5) + offset (50, -40)
    assert "150.0,37.5" in output
    # note connections render dotted without arrowhead
    assert 'class="edge dotted"' in output
    assert 'marker' not in output.split("<polyline")[1].split(">")[0]


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
