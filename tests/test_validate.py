from archi_tool.discovery import DEFAULT_PROPERTY_KEYS
from archi_tool.validate import allowed_property_keys, validate
from lxml import etree


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


def test_relation_to_view_detected(model):
    model.resolve("id-rel-inf").set("target", "id-view-1")
    errors, _ = validate(model)
    assert any("verwijst naar view id-view-1" in e for e in errors)


def test_non_association_relation_endpoint_detected(model):
    model.resolve("id-rel-inf").set("target", "id-rel-agg")
    errors, _ = validate(model)
    assert any("alleen een AssociationRelationship" in e for e in errors)


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


def test_view_parts_loose_in_folder_detected(model):
    views = model.folder("diagrams")
    for part_id in ("id-obj-alfa", "id-conn-1"):
        part = model.id_index()[part_id]
        part.getparent().remove(part)
        views.append(part)
    errors, _ = validate(model)
    assert any("View-onderdeel id-obj-alfa (child) staat los" in e for e in errors)
    assert any(
        "View-onderdeel id-conn-1 (sourceConnection) staat los" in e for e in errors
    )


def test_dangling_connection_relationship_detected(model):
    conn = model.root.iter("sourceConnection").__next__()
    conn.set("archimateRelationship", "id-weg")
    errors, _ = validate(model)
    assert any("onbekende relatie id-weg" in e for e in errors)


def test_dangling_target_connections_detected(model):
    obj = model.id_index()["id-obj-beta"]
    obj.set("targetConnections", "id-conn-1 id-spook")
    errors, _ = validate(model)
    assert any("targetConnections bevat onbekend id id-spook" in e for e in errors)


def test_connection_endpoint_outside_view_detected(model):
    conn = model.root.iter("sourceConnection").__next__()
    conn.set("target", "id-el-gamma")
    errors, _ = validate(model)
    assert any("verwijst niet naar een object in dezelfde view" in e for e in errors)


def test_view_object_with_unknown_element_detected(model):
    obj = model.id_index()["id-obj-beta"]
    obj.set("archimateElement", "id-foetsie")
    errors, _ = validate(model)
    assert any("onbekend element id-foetsie" in e for e in errors)


def test_property_key_conventions(model, tmp_path):
    conventions = tmp_path / "conventies.md"
    conventions.write_text(
        "# Conventies\n\n## Property-keys\n\n- `Capability-niveau`\n\n"
        "## Iets anders\n\n- `Genegeerd`\n",
        encoding="utf-8",
    )
    assert allowed_property_keys(conventions) == {"Capability-niveau"}

    etree.SubElement(
        model.resolve("id-el-gamma"), "property", {"key": "Vrije-key", "value": "x"}
    )
    _, warnings = validate(model, conventions)
    assert any("Vrije-key" in w for w in warnings)
    assert not any("Capability-niveau" in w for w in warnings)


def test_property_key_heading_may_be_numbered(tmp_path):
    conventions = tmp_path / "conventies.md"
    conventions.write_text(
        "# Conventies\n\n## 3. Property-keys\n\n"
        "- `Omschrijving` — toelichting met `inline` backticks\n"
        "- `Bron` — bronverwijzing\n\n## 4. Ids\n\n- `Genegeerd`\n",
        encoding="utf-8",
    )
    # only the leading key of each bullet counts, not inline backticks
    assert allowed_property_keys(conventions) == {"Omschrijving", "Bron"}


def test_conventions_parser_matches_a_real_doc(tmp_path):
    """Guard against the parser drifting from the conventions-doc format
    (a heading rename once silently disabled this check). Uses a doc in the
    shape the tool documents, not a project-specific one."""
    doc = tmp_path / "conventies.md"
    doc.write_text(
        "## 3. Property-keys\n\n"
        "- `Omschrijving` — toelichting (mag `backticks` in de tekst hebben)\n"
        "- `Bron` — bronverwijzing\n",
        encoding="utf-8",
    )
    keys = allowed_property_keys(doc)
    assert "Omschrijving" in keys
    assert "Bron" in keys
    # inline backticks in descriptions must not count as keys
    assert "backticks" not in keys


def test_builtin_default_keys_nonempty():
    """The built-in fallback set must stay usable so the property-key check
    still runs when a project ships no conventions doc. Descriptions belong
    in the documentation field, so "Omschrijving" is not a default (ADR 0009)."""
    assert "Bron" in DEFAULT_PROPERTY_KEYS
    assert "Omschrijving" not in DEFAULT_PROPERTY_KEYS


def test_missing_property_key_section_warns(model, tmp_path):
    conventions = tmp_path / "conventies.md"
    conventions.write_text("# Conventies\n\nGeen keys hier.\n", encoding="utf-8")
    _, warnings = validate(model, conventions)
    assert any(
        "conventiecheck op property-keys staat hierdoor uit" in w for w in warnings
    )
