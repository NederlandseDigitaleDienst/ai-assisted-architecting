from lxml import etree

from archi_tool.model import XSI_TYPE
from archi_tool.render import MARKER, render_all, render_view, slugify


def test_slugify():
    assert slugify("Capabilities (relatieweergave)") == \
        "capabilities-relatieweergave"
    assert slugify("???") == "view"


def test_render_flat_view(model):
    diagram = model.diagrams()[0]
    output = render_view(model, diagram)
    assert output.startswith(MARKER)
    assert "# Testview" in output
    assert "flowchart TD" in output
    assert "accTitle: Testview" in output
    assert 'n1["Gebied Alfa"]' in output
    assert 'n2["Bouwblok Beta"]' in output
    assert "n1 --o n2" in output           # aggregation, unlabeled
    assert "classDef strategy" in output
    assert "class n1,n2 strategy" in output


def test_render_nested_view_uses_subgraph(model):
    diagrams_folder = model.folder("diagrams")
    diagram = etree.SubElement(diagrams_folder, "element", {
        XSI_TYPE: "archimate:ArchimateDiagramModel",
        "name": "Genest", "id": "id-view-nested"})
    outer = etree.SubElement(diagram, "child", {
        XSI_TYPE: "archimate:DiagramObject", "id": "id-obj-n1",
        "archimateElement": "id-el-alfa"})
    etree.SubElement(outer, "child", {
        XSI_TYPE: "archimate:DiagramObject", "id": "id-obj-n2",
        "archimateElement": "id-el-beta"})
    etree.SubElement(outer, "sourceConnection", {
        XSI_TYPE: "archimate:Connection", "id": "id-conn-n1",
        "source": "id-obj-n1", "target": "id-obj-n2",
        "archimateRelationship": "id-rel-agg"})

    output = render_view(model, diagram)
    assert 'subgraph n1["Gebied Alfa"]' in output
    assert 'n2["Bouwblok Beta"]' in output
    assert "end" in output
    # containment arrow into own subgraph is redundant and skipped
    assert " --o " not in output


def test_render_labeled_influence_edge(model):
    diagram = model.diagrams()[0]
    obj = model.id_index()["id-obj-beta"]
    etree.SubElement(obj, "sourceConnection", {
        XSI_TYPE: "archimate:Connection", "id": "id-conn-2",
        "source": "id-obj-beta", "target": "id-obj-alfa",
        "archimateRelationship": "id-rel-inf"})
    output = render_view(model, diagram)
    assert 'n2 -.->|"draagt bij aan"| n1' in output


def test_label_escaping(model):
    model.rename("id-el-alfa", 'Gebied "Alfa" & co')
    output = render_view(model, model.diagrams()[0])
    assert 'n1["Gebied #quot;Alfa#quot; & co"]' in output


def test_render_all_writes_index_and_cleans_stale(model, tmp_path):
    out = tmp_path / "views"
    out.mkdir()
    stale_generated = out / "oude-view.md"
    stale_generated.write_text(f"{MARKER}\noud", encoding="utf-8")
    handwritten = out / "notities.md"
    handwritten.write_text("# van de architect", encoding="utf-8")

    written, removed = render_all(model, out)
    assert (out / "testview.md").exists()
    index = (out / "README.md").read_text(encoding="utf-8")
    assert "[Testview](testview.md)" in index
    assert not stale_generated.exists()
    assert handwritten.exists()
    assert stale_generated in removed

    # second run is idempotent
    written, removed = render_all(model, out)
    assert written == [] and removed == []
