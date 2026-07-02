from lxml import etree

from archi_tool.model import XSI_TYPE
from archi_tool.validate import allowed_property_keys, validate


def test_clean_model_validates(model):
    errors, warnings = validate(model)
    assert errors == []
    assert warnings == []


def test_duplicate_id_detected(model):
    model.resolve("id-el-beta").set("id", "id-el-alfa")
    errors, _ = validate(model)
    assert any("Dubbel id" in e for e in errors)


def test_dangling_relation_target_detected(model):
    model.resolve("id-rel-inf").set("target", "id-bestaat-niet")
    errors, _ = validate(model)
    assert any("onbekend id id-bestaat-niet" in e for e in errors)


def test_relation_in_wrong_folder_detected(model):
    rel = model.resolve("id-rel-agg")
    model.folder("strategy").append(rel)
    errors, _ = validate(model)
    assert any("in plaats van 'relations'" in e for e in errors)


def test_element_in_wrong_layer_warns(model):
    goal = model.resolve("id-el-gamma")
    model.folder("business").append(goal)
    errors, warnings = validate(model)
    assert errors == []
    assert any("verwacht 'motivation'" in w for w in warnings)


def test_dangling_connection_relationship_detected(model):
    conn = model.root.iter("sourceConnection").__next__()
    conn.set("archimateRelationship", "id-weg")
    errors, _ = validate(model)
    assert any("onbekende relatie id-weg" in e for e in errors)


def test_dangling_target_connections_detected(model):
    obj = model.id_index()["id-obj-beta"]
    obj.set("targetConnections", "id-conn-1 id-spook")
    errors, _ = validate(model)
    assert any("targetConnections bevat onbekend id id-spook" in e
               for e in errors)


def test_connection_endpoint_outside_view_detected(model):
    conn = model.root.iter("sourceConnection").__next__()
    conn.set("target", "id-el-gamma")
    errors, _ = validate(model)
    assert any("verwijst niet naar een object in dezelfde view" in e
               for e in errors)


def test_view_object_with_unknown_element_detected(model):
    obj = model.id_index()["id-obj-beta"]
    obj.set("archimateElement", "id-foetsie")
    errors, _ = validate(model)
    assert any("onbekend element id-foetsie" in e for e in errors)


def test_property_key_conventions(model, tmp_path):
    conventions = tmp_path / "conventies.md"
    conventions.write_text(
        "# Conventies\n\n## Property-keys\n\n- `Capability-niveau`\n\n"
        "## Iets anders\n\n- `Genegeerd`\n", encoding="utf-8")
    assert allowed_property_keys(conventions) == {"Capability-niveau"}

    etree.SubElement(model.resolve("id-el-gamma"), "property",
                     {"key": "Vrije-key", "value": "x"})
    _, warnings = validate(model, conventions)
    assert any("Vrije-key" in w for w in warnings)
    assert not any("Capability-niveau" in w for w in warnings)
