import re

import pytest
from archi_tool.model import ArchiModel, ModelError, new_id, xsi_type
from archi_tool.validate import validate
from lxml import etree


def assert_valid(model):
    errors, _ = validate(model)
    assert errors == []


def test_load_and_counts(model):
    assert model.name == "Klein testmodel"
    assert len(model.elements()) == 3
    assert len(model.relationships()) == 2
    assert len(model.diagrams()) == 1


def test_resolve_by_id_and_name(model):
    assert model.resolve("id-el-alfa").get("name") == "Gebied Alfa"
    assert model.resolve("Doel Gamma").get("id") == "id-el-gamma"
    with pytest.raises(ModelError):
        model.resolve("bestaat-niet")


def test_add_element_lands_in_layer_folder(model):
    el = model.add_element(
        "Driver",
        "Nieuwe ontwikkeling",
        properties={"Omschrijving": "test"},
        documentation="toelichting",
    )
    folder = el.getparent()
    assert folder.get("type") == "motivation"
    assert model.properties(el) == {"Omschrijving": "test"}
    assert model.documentation(el) == "toelichting"
    assert el.get("id").startswith("id-")
    assert_valid(model)


def test_add_element_unknown_type(model):
    with pytest.raises(ModelError):
        model.add_element("Onzin", "x")


def test_add_relation_by_name(model):
    rel = model.add_relation("Realization", "Bouwblok Beta", "Gebied Alfa")
    assert xsi_type(rel) == "RealizationRelationship"
    assert rel.getparent().get("type") == "relations"
    assert_valid(model)


def test_add_relation_unknown_type(model):
    with pytest.raises(ModelError):
        model.add_relation("Vage-lijn", "id-el-alfa", "id-el-beta")


def test_add_relation_refuses_view_endpoint(model):
    with pytest.raises(ModelError, match="is een view"):
        model.add_relation("Association", "Testview", "id-el-gamma")


def test_add_relation_refuses_relation_endpoint(model):
    with pytest.raises(ModelError, match="is zelf een relatie"):
        model.add_relation("Influence", "id-rel-agg", "id-el-gamma")


def test_add_relation_allows_association_to_relation(model):
    rel = model.add_relation("Association", "id-rel-agg", "id-el-gamma")
    assert xsi_type(rel) == "AssociationRelationship"
    assert_valid(model)


def test_set_property_updates_and_creates(model):
    model.set_property("id-el-alfa", "Capability-niveau", "bouwblok")
    model.set_property("id-el-alfa", "Bron", "test")
    props = model.properties(model.resolve("id-el-alfa"))
    assert props == {"Capability-niveau": "bouwblok", "Bron": "test"}


def test_remove_property_removes_only_that_key(model):
    model.set_property("id-el-alfa", "Omschrijving", "tekst")
    model.remove_property("id-el-alfa", "Omschrijving")
    props = model.properties(model.resolve("id-el-alfa"))
    assert props == {"Capability-niveau": "gebied"}
    assert_valid(model)


def test_remove_property_refuses_missing_key(model):
    with pytest.raises(ModelError, match="niet gevonden"):
        model.remove_property("id-el-alfa", "Bestaat-niet")


def test_add_element_in_subfolder_refuses_missing_without_create(model):
    with pytest.raises(ModelError, match="Submap 'Gebied X' niet gevonden"):
        model.add_element("BusinessService", "Dienst", subfolder="Gebied X")


def test_add_element_and_relation_in_created_subfolder(model):
    el = model.add_element(
        "BusinessService", "Dienst", subfolder="Gebied X/Sub", create_subfolder=True
    )
    assert el.getparent().get("name") == "Sub"
    assert el.getparent().getparent().get("name") == "Gebied X"
    assert model.top_folder(el).get("type") == "business"
    # tweede keer: de submap bestaat nu, geen create nodig en geen duplicaat
    el2 = model.add_element("BusinessService", "Dienst 2", subfolder="Gebied X/Sub")
    assert el2.getparent() is el.getparent()
    rel = model.add_relation(
        "Realization",
        el.get("id"),
        "id-el-beta",
        subfolder="Gebied X",
        create_subfolder=True,
    )
    assert rel.getparent().get("name") == "Gebied X"
    assert model.top_folder(rel).get("type") == "relations"
    assert_valid(model)


def test_move_within_layer_and_back(model):
    model.move("id-el-gamma", "Gebied X", create_subfolder=True)
    el = model.resolve("id-el-gamma")
    assert el.getparent().get("name") == "Gebied X"
    assert model.top_folder(el).get("type") == "motivation"
    model.move("id-rel-agg", "Gebied X", create_subfolder=True)
    assert model.top_folder(model.resolve("id-rel-agg")).get("type") == "relations"
    model.move("id-el-gamma", "")
    assert model.resolve("id-el-gamma").getparent().get("type") == "motivation"
    assert_valid(model)


@pytest.mark.parametrize(
    "ref, message",
    [
        ("id-obj-alfa", "geen element, relatie of view (maar een 'child')"),
        ("id-conn-1", "geen element, relatie of view (maar een 'sourceConnection')"),
        ("id-model-1", "geen element, relatie of view (maar een 'model')"),
        ("id-folder-motivation", "is een map"),
    ],
)
def test_move_refuses_non_concepts(model, ref, message):
    with pytest.raises(ModelError, match=re.escape(message)):
        model.move(ref, "", create_subfolder=True)
    assert_valid(model)


def test_move_refuses_subfolder(model):
    model.move("id-el-gamma", "Gebied X", create_subfolder=True)
    folder = model.resolve("id-el-gamma").getparent()
    with pytest.raises(ModelError, match="is een map"):
        model.move(folder.get("id"), "", create_subfolder=True)


def test_move_view_to_subfolder(model):
    model.move("id-view-1", "Overzichten", create_subfolder=True)
    view = model.resolve("id-view-1")
    assert view.getparent().get("name") == "Overzichten"
    assert model.top_folder(view).get("type") == "diagrams"
    assert_valid(model)


def test_subfolder_refuses_ambiguous_name(model):
    business = model.folder("business")
    for _ in range(2):
        etree.SubElement(business, "folder", {"name": "Dubbel", "id": new_id()})
    with pytest.raises(ModelError, match="komt 2x voor"):
        model.add_element("BusinessService", "Dienst", subfolder="Dubbel")


def test_rename_and_documentation(model):
    model.rename("id-el-beta", "Bouwblok Beta 2")
    model.set_documentation("id-el-beta", "nieuw")
    el = model.resolve("id-el-beta")
    assert el.get("name") == "Bouwblok Beta 2"
    assert model.documentation(el) == "nieuw"
    assert el[0].tag == "documentation"


def test_remove_refuses_without_cascade(model):
    with pytest.raises(ModelError):
        model.remove("id-el-alfa")


def test_remove_cascade_cleans_views_and_relations(model):
    model.remove("id-el-alfa", cascade=True)
    assert model.resolve("id-el-beta") is not None
    ids = model.id_index()
    assert "id-el-alfa" not in ids
    assert "id-rel-agg" not in ids
    assert "id-obj-alfa" not in ids
    assert "id-conn-1" not in ids
    beta_obj = ids["id-obj-beta"]
    assert beta_obj.get("targetConnections") is None
    assert_valid(model)


def test_remove_relation_cascade(model):
    model.remove("id-rel-agg", cascade=True)
    ids = model.id_index()
    assert "id-rel-agg" not in ids
    assert "id-conn-1" not in ids
    assert ids["id-obj-beta"].get("targetConnections") is None
    assert_valid(model)


def test_roundtrip_save_load(model, model_path):
    model.add_element("Principle", "Testprincipe")
    model.save()
    reloaded = ArchiModel(model_path)
    assert len(reloaded.elements()) == 4
    assert reloaded.resolve("Testprincipe") is not None
    assert_valid(reloaded)
