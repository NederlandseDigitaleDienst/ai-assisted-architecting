"""Deterministic view generation for native .archimate models.

Two layout strategies, ported from the ADO exportscript
(build_archimate_export.py):

- "grid": all selected elements in a simple grid.
- "cluster": group by a structural relation (default Aggregation/Composition):
  a source element becomes a cluster head placed above its targets, with
  vertical space so connection arrows stay readable. Elements without a
  cluster become standalone nodes at the end.

All selected relations between selected elements are drawn as connections.
"""
from __future__ import annotations

from lxml import etree

from .model import XSI_TYPE, ModelError, new_id, xsi_type

NODE_W = 220
NODE_H = 70
NODE_GAP = 12
CLUSTER_COLS = 3        # clusters per canvas row
CHILD_COLS = 2          # children per row inside a cluster
CLUSTER_VGAP = 60       # space between cluster head and its child grid
MARGIN = 60
GRID_COLS = 5           # columns for the plain grid layout

CLUSTER_RELATION_TYPES = {"Aggregation", "Composition"}


def select(model, element_types=None, relation_types=None, prop=None):
    elements = model.elements()
    if element_types:
        elements = [e for e in elements if xsi_type(e) in element_types]
    if prop:
        key, _, value = prop.partition("=")
        elements = [e for e in elements
                    if model.properties(e).get(key) == value]
    ids = {e.get("id") for e in elements}
    relations = [r for r in model.relationships()
                 if r.get("source") in ids and r.get("target") in ids]
    if relation_types:
        relations = [r for r in relations
                     if xsi_type(r).removesuffix("Relationship")
                     in relation_types]
    return elements, relations


def grid_positions(elements):
    positions = {}
    for i, el in enumerate(elements):
        col, row = i % GRID_COLS, i // GRID_COLS
        positions[el.get("id")] = (
            MARGIN + col * (NODE_W + 2 * NODE_GAP),
            MARGIN + row * (NODE_H + 2 * NODE_GAP))
    return positions


def cluster_positions(elements, relations):
    ids = {e.get("id") for e in elements}
    children = {}
    childless = set()
    for r in relations:
        if xsi_type(r).removesuffix("Relationship") in CLUSTER_RELATION_TYPES:
            src, tgt = r.get("source"), r.get("target")
            if src in ids and tgt in ids:
                children.setdefault(src, []).append(tgt)
                childless.add(tgt)

    heads = [e for e in elements
             if e.get("id") in children and e.get("id") not in childless]
    placed = {h.get("id") for h in heads} | {
        c for kids in (children[h.get("id")] for h in heads) for c in kids}
    loose = [e for e in elements if e.get("id") not in placed]
    clusters = ([(h.get("id"), children[h.get("id")]) for h in heads]
                + [(e.get("id"), []) for e in loose])

    sizes = []
    for _, kids in clusters:
        n = len(kids)
        cols = min(CHILD_COLS, n) if n else 0
        rows = (n + cols - 1) // cols if n else 0
        grid_w = cols * NODE_W + max(0, cols - 1) * NODE_GAP
        width = max(NODE_W, grid_w)
        height = NODE_H + (CLUSTER_VGAP + rows * NODE_H +
                           (rows - 1) * NODE_GAP if n else 0)
        sizes.append((width, height, cols, grid_w))

    n_rows = (len(clusters) + CLUSTER_COLS - 1) // CLUSTER_COLS
    col_w = [0] * CLUSTER_COLS
    row_h = [0] * max(1, n_rows)
    for i, (width, height, _, _) in enumerate(sizes):
        col_w[i % CLUSTER_COLS] = max(col_w[i % CLUSTER_COLS], width)
        row_h[i // CLUSTER_COLS] = max(row_h[i // CLUSTER_COLS], height)
    col_x = [MARGIN]
    for c in range(CLUSTER_COLS - 1):
        col_x.append(col_x[-1] + col_w[c] + MARGIN)
    row_y = [MARGIN]
    for r in range(n_rows - 1):
        row_y.append(row_y[-1] + row_h[r] + MARGIN)

    positions = {}
    for i, (head_id, kids) in enumerate(clusters):
        width, height, cols, grid_w = sizes[i]
        x0 = col_x[i % CLUSTER_COLS]
        y0 = row_y[i // CLUSTER_COLS]
        positions[head_id] = (x0 + (width - NODE_W) // 2, y0)
        kid_x0 = x0 + (width - grid_w) // 2
        for j, kid_id in enumerate(kids):
            positions[kid_id] = (
                kid_x0 + (j % cols) * (NODE_W + NODE_GAP),
                y0 + NODE_H + CLUSTER_VGAP + (j // cols) * (NODE_H + NODE_GAP))
    return positions


def add_view(model, name, layout="grid", element_types=None,
             relation_types=None, prop=None):
    elements, relations = select(model, element_types, relation_types, prop)
    if not elements:
        raise ModelError("Selectie is leeg; geen view aangemaakt")

    if layout == "grid":
        positions = grid_positions(elements)
    elif layout == "cluster":
        positions = cluster_positions(elements, relations)
    else:
        raise ModelError(f"Onbekende layout '{layout}' (grid of cluster)")

    diagram = etree.SubElement(model.folder("diagrams"), "element", {
        XSI_TYPE: "archimate:ArchimateDiagramModel",
        "name": name, "id": new_id()})

    objects = {}
    for el in elements:
        el_id = el.get("id")
        obj = etree.SubElement(diagram, "child", {
            XSI_TYPE: "archimate:DiagramObject",
            "id": new_id(), "archimateElement": el_id})
        x, y = positions[el_id]
        etree.SubElement(obj, "bounds", {
            "x": str(x), "y": str(y),
            "width": str(NODE_W), "height": str(NODE_H)})
        objects[el_id] = obj

    for rel in relations:
        source_obj = objects[rel.get("source")]
        target_obj = objects[rel.get("target")]
        conn_id = new_id()
        etree.SubElement(source_obj, "sourceConnection", {
            XSI_TYPE: "archimate:Connection", "id": conn_id,
            "source": source_obj.get("id"), "target": target_obj.get("id"),
            "archimateRelationship": rel.get("id")})
        existing = target_obj.get("targetConnections")
        target_obj.set("targetConnections",
                       f"{existing} {conn_id}" if existing else conn_id)

    return diagram
