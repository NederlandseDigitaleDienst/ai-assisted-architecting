"""Integrity checks for a native .archimate model.

Returns (errors, warnings). Errors mean the model is corrupt or will not
load correctly in Archi; warnings flag convention deviations.
"""
from __future__ import annotations

import re
from pathlib import Path

from .model import (FOLDER_BY_ELEMENT_TYPE, is_diagram, is_element,
                    is_relationship, xsi_type)
from .render import slugify, view_stems

# tolerate an optional section number ("## Property-keys", "## 3. Property-keys")
PROPERTY_KEYS_HEADING = re.compile(
    r"^##\s*(?:\d+\.\s*)?Property-keys\s*$", re.MULTILINE)


def allowed_property_keys(conventions_path) -> set:
    """Parse property keys from the conventions doc: in the section under
    the Property-keys heading, every bullet starting with a backticked key."""
    path = Path(conventions_path)
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    match = PROPERTY_KEYS_HEADING.search(text)
    if not match:
        return set()
    section = re.split(r"\n## ", text[match.end():], maxsplit=1)[0]
    return set(re.findall(r"^- `([^`\n]+)`", section, flags=re.MULTILINE))


def top_folder_of(model, node):
    parent = node.getparent()
    top = None
    while parent is not None:
        if parent.tag == "folder":
            top = parent
        parent = parent.getparent()
    return top


def validate(model, conventions_path=None, allowed_keys=None) -> tuple[list, list]:
    """Run integrity checks; return (errors, warnings).

    Property-key checking uses ``allowed_keys`` when given (a set resolved by
    discovery), otherwise parses ``conventions_path``. Passing neither skips
    the property-key check.
    """
    errors, warnings = [], []

    # 1. unique ids
    index = {}
    for node in model.root.iter():
        node_id = node.get("id")
        if not node_id:
            continue
        if node_id in index:
            errors.append(f"Dubbel id: {node_id}")
        index[node_id] = node

    # 2. relationship endpoints exist and are valid concepts
    for rel in model.relationships():
        for attr in ("source", "target"):
            ref = rel.get(attr)
            node = index.get(ref)
            if node is None:
                errors.append(
                    f"Relatie {rel.get('id')} ({xsi_type(rel)}): {attr} "
                    f"verwijst naar onbekend id {ref}")
            elif is_diagram(node):
                errors.append(
                    f"Relatie {rel.get('id')} ({xsi_type(rel)}): {attr} "
                    f"verwijst naar view {ref}; relaties kunnen geen views "
                    "verbinden")
            elif (is_relationship(node)
                    and xsi_type(rel) != "AssociationRelationship"):
                errors.append(
                    f"Relatie {rel.get('id')} ({xsi_type(rel)}): {attr} "
                    f"verwijst naar relatie {ref}; alleen een "
                    "AssociationRelationship mag een relatie als eindpunt "
                    "hebben")

    # 3. folder placement
    for node in model.root.iter("element"):
        folder = top_folder_of(model, node)
        folder_type = folder.get("type") if folder is not None else None
        if is_relationship(node) and folder_type != "relations":
            errors.append(
                f"Relatie {node.get('id')} staat in folder '{folder_type}' "
                "in plaats van 'relations'")
        elif is_diagram(node) and folder_type != "diagrams":
            errors.append(
                f"View {node.get('id')} staat in folder '{folder_type}' "
                "in plaats van 'diagrams'")
        elif is_element(node):
            expected = FOLDER_BY_ELEMENT_TYPE.get(xsi_type(node))
            if expected and folder_type != expected:
                warnings.append(
                    f"Element {node.get('id')} ({xsi_type(node)}, "
                    f"'{node.get('name')}') staat in folder '{folder_type}', "
                    f"verwacht '{expected}'")

    # 3b. diagram parts belong inside a view; a view object or connection
    # directly in a folder means it was torn out of its view (Archi still
    # loads such a file, so without this check the damage goes unnoticed)
    for node in model.root.iter("child", "sourceConnection"):
        parent = node.getparent()
        if parent is not None and parent.tag == "folder":
            errors.append(
                f"View-onderdeel {node.get('id')} ({node.tag}) staat los in "
                f"folder '{parent.get('name')}' in plaats van in een view")

    # 4. view integrity
    for diagram in model.diagrams():
        object_ids = {c.get("id") for c in diagram.iter("child")}
        for obj in diagram.iter("child"):
            element_ref = obj.get("archimateElement")
            if element_ref and element_ref not in index:
                errors.append(
                    f"View-object {obj.get('id')} verwijst naar onbekend "
                    f"element {element_ref}")
            for conn_id in (obj.get("targetConnections") or "").split():
                if conn_id not in index:
                    errors.append(
                        f"View-object {obj.get('id')}: targetConnections "
                        f"bevat onbekend id {conn_id}")
        for conn in diagram.iter("sourceConnection"):
            rel_ref = conn.get("archimateRelationship")
            if rel_ref and rel_ref not in index:
                errors.append(
                    f"Verbinding {conn.get('id')} verwijst naar onbekende "
                    f"relatie {rel_ref}")
            for attr in ("source", "target"):
                ref = conn.get(attr)
                if ref not in object_ids:
                    errors.append(
                        f"Verbinding {conn.get('id')}: {attr} verwijst niet "
                        f"naar een object in dezelfde view ({ref})")

    # 4b. view names that slugify alike would share an output file; render
    # gives each of them an id suffix, but nobody guesses that name from the
    # view name, so ask for a rename (warning only)
    stems = view_stems(model)
    by_base = {}
    for diagram in model.diagrams():
        base = slugify(diagram.get("name") or diagram.get("id"))
        by_base.setdefault(base, []).append(diagram)
    for base, diagrams in by_base.items():
        if len(diagrams) > 1:
            names = ", ".join(
                f"'{d.get('name') or '(naamloos)'}' ({d.get('id')}) → "
                f"{stems[d.get('id')]}"
                for d in diagrams)
            warnings.append(
                f"Views met dezelfde bestandsnaam '{base}': {names}. "
                "Hernoem er een voor een voorspelbare bestandsnaam")

    # 5. property keys against conventions (warning only)
    allowed = allowed_keys
    if allowed is None and conventions_path:
        allowed = allowed_property_keys(conventions_path)
    if allowed:
        seen_unknown = set()
        for prop in model.root.iter("property"):
            key = prop.get("key")
            if key and key not in allowed and key not in seen_unknown:
                seen_unknown.add(key)
                warnings.append(
                    f"Property-key '{key}' staat niet in de conventielijst")
    elif conventions_path:
        # an empty list silently disables this check; say so loudly
        warnings.append(
            f"Geen property-keys gevonden in {conventions_path}: "
            "de conventiecheck op property-keys staat hierdoor uit "
            "(ontbreekt de sectie 'Property-keys'?)")

    return errors, warnings
