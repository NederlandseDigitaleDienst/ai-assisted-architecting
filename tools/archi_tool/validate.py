"""Integrity checks for a native .archimate model.

Returns (errors, warnings). Errors mean the model is corrupt or will not
load correctly in Archi; warnings flag convention deviations.
"""
from __future__ import annotations

import re
from pathlib import Path

from .model import (FOLDER_BY_ELEMENT_TYPE, is_diagram, is_element,
                    is_relationship, xsi_type)

PROPERTY_KEYS_HEADING = "## Property-keys"


def allowed_property_keys(conventions_path) -> set:
    """Parse backticked property keys from the conventions doc, from the
    section under PROPERTY_KEYS_HEADING up to the next heading."""
    path = Path(conventions_path)
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    if PROPERTY_KEYS_HEADING not in text:
        return set()
    section = text.split(PROPERTY_KEYS_HEADING, 1)[1]
    section = re.split(r"\n## ", section, maxsplit=1)[0]
    return set(re.findall(r"`([^`\n]+)`", section))


def top_folder_of(model, node):
    parent = node.getparent()
    top = None
    while parent is not None:
        if parent.tag == "folder":
            top = parent
        parent = parent.getparent()
    return top


def validate(model, conventions_path=None) -> tuple[list, list]:
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

    # 2. relationship endpoints exist
    for rel in model.relationships():
        for attr in ("source", "target"):
            ref = rel.get(attr)
            if ref not in index:
                errors.append(
                    f"Relatie {rel.get('id')} ({xsi_type(rel)}): {attr} "
                    f"verwijst naar onbekend id {ref}")

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

    # 5. property keys against conventions (warning only)
    if conventions_path:
        allowed = allowed_property_keys(conventions_path)
        if allowed:
            seen_unknown = set()
            for prop in model.root.iter("property"):
                key = prop.get("key")
                if key and key not in allowed and key not in seen_unknown:
                    seen_unknown.add(key)
                    warnings.append(
                        f"Property-key '{key}' staat niet in de "
                        "conventielijst (docs/conventies.md)")

    return errors, warnings
