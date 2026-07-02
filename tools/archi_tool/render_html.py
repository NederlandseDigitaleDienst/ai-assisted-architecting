"""Render views to standalone HTML pages styled with the NLDD design system.

Unlike the Mermaid renderer this is faithful to the Archi view: it uses the
layout stored in the model. Bounds of nested diagram objects are relative to
their parent; this module resolves them to absolute canvas coordinates.
Boxes are positioned divs, connections an SVG layer clipped to box borders.
NLDD components and tokens load from the CDN, pinned to a fixed version so
output stays deterministic.
"""
from __future__ import annotations

import html
from pathlib import Path

from .model import FOLDER_BY_ELEMENT_TYPE, xsi_type
from .render import (CONTAINMENT_TYPES, DOTTED_TYPES, LAYER_PALETTE, MARKER,
                     slugify, write_if_changed)

NLDD_VERSION = "0.8.64"
NLDD_CSS = (f"https://cdn.jsdelivr.net/npm/@nldd/design-system@{NLDD_VERSION}"
            "/dist/css/global.css")
NLDD_JS = f"https://cdn.jsdelivr.net/npm/@nldd/design-system@{NLDD_VERSION}/+esm"

CANVAS_MARGIN = 40


def absolute_boxes(diagram, index) -> list:
    """Resolve diagram objects to absolute canvas coordinates."""
    boxes = []

    def walk(objects, offset_x, offset_y):
        for obj in objects:
            element = index.get(obj.get("archimateElement") or "")
            bounds = obj.find("bounds")
            if element is None or bounds is None:
                continue
            x = offset_x + int(bounds.get("x", "0"))
            y = offset_y + int(bounds.get("y", "0"))
            children = obj.findall("child")
            boxes.append({
                "id": obj.get("id"), "element": element,
                "x": x, "y": y,
                "w": int(bounds.get("width", "120")),
                "h": int(bounds.get("height", "55")),
                "container": bool(children),
            })
            walk(children, x, y)

    walk(diagram.findall("child"), 0, 0)
    return boxes


def border_point(box, toward_x, toward_y):
    """Point on the border of an axis-aligned box, from its center toward
    the given target point."""
    center_x = box["x"] + box["w"] / 2
    center_y = box["y"] + box["h"] / 2
    dx, dy = toward_x - center_x, toward_y - center_y
    if dx == 0 and dy == 0:
        return center_x, center_y
    scale_x = (box["w"] / 2) / abs(dx) if dx else float("inf")
    scale_y = (box["h"] / 2) / abs(dy) if dy else float("inf")
    scale = min(scale_x, scale_y)
    return center_x + dx * scale, center_y + dy * scale


def diagram_edges(model, diagram, box_by_object_id) -> list:
    index = model.id_index()

    def is_descendant(node, ancestor):
        parent = node.getparent()
        while parent is not None:
            if parent is ancestor:
                return True
            parent = parent.getparent()
        return False

    edges = []
    for conn in diagram.iter("sourceConnection"):
        source = box_by_object_id.get(conn.get("source"))
        target = box_by_object_id.get(conn.get("target"))
        if not source or not target:
            continue
        rel = index.get(conn.get("archimateRelationship") or "")
        rel_type = xsi_type(rel) if rel is not None else ""
        source_obj = index.get(conn.get("source"))
        target_obj = index.get(conn.get("target"))
        if (rel_type in CONTAINMENT_TYPES
                and is_descendant(target_obj, source_obj)):
            continue
        target_cx = target["x"] + target["w"] / 2
        target_cy = target["y"] + target["h"] / 2
        source_cx = source["x"] + source["w"] / 2
        source_cy = source["y"] + source["h"] / 2
        x1, y1 = border_point(source, target_cx, target_cy)
        x2, y2 = border_point(target, source_cx, source_cy)
        label = (rel.get("name") if rel is not None else None) or rel_type
        edges.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": label,
            "dotted": rel_type in DOTTED_TYPES,
            "containment": rel_type in CONTAINMENT_TYPES,
        })
    return edges


def layer_of(element) -> str:
    return FOLDER_BY_ELEMENT_TYPE.get(xsi_type(element), "other")


def layer_css() -> str:
    rules = []
    for layer, (fill, stroke, text) in LAYER_PALETTE.items():
        rules.append(
            f"    .leaf.{layer} {{ background: {fill}; "
            f"border-color: {stroke}; color: {text}; }}")
        rules.append(
            f"    .container.{layer} {{ background: "
            f"color-mix(in srgb, {fill} 22%, transparent); "
            f"border-color: {stroke}; color: {text}; }}")
    return "\n".join(rules)


PAGE_CSS = """
    .doc { max-width: 72ch; color: light-dark(#414149, #c5c5cd); }
    /* the diagram canvas is always light, like an image: the ArchiMate
       palette is designed for a light surface */
    .diagram-wrap { overflow-x: auto; border-radius: 12px;
      border: 1px solid light-dark(#e0e0e5, #45454d);
      background: #ffffff; }
    .diagram { position: relative; }
    .diagram > svg { position: absolute; inset: 0; }
    .edge { stroke: #5b5b66; stroke-width: 1.3; }
    .edge.dotted { stroke-dasharray: 5 3; }
    .box { position: absolute; box-sizing: border-box;
      font-size: 13px; line-height: 1.3; }
    .leaf { display: flex; align-items: center; justify-content: center;
      text-align: center; padding: 4px 10px; border-radius: 6px;
      border: 1px solid; box-shadow: 0 1px 2px rgb(0 0 0 / 0.10); }
    .container { border-radius: 10px; border: 1.5px solid;
      padding: 10px 14px; font-weight: 550; }
    .card-link { text-decoration: none; color: inherit; display: block; }
    .meta { color: light-dark(#5b5b66, #a0a0ab); font-size: 14px; }
"""


def page_shell(title: str, body: str) -> str:
    return f"""{MARKER}
<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{NLDD_CSS}">
<script type="module">import "{NLDD_JS}";</script>
<style>
{layer_css()}
{PAGE_CSS}
</style>
</head>
<body>
<nldd-app-view>
  <nldd-page>
    <nldd-container padding="24" sm-padding="8">
{body}
    </nldd-container>
  </nldd-page>
</nldd-app-view>
</body>
</html>
"""


def render_view_html(model, diagram) -> str:
    index = model.id_index()
    boxes = absolute_boxes(diagram, index)
    box_by_object_id = {b["id"]: b for b in boxes}
    edges = diagram_edges(model, diagram, box_by_object_id)

    width = max((b["x"] + b["w"] for b in boxes), default=0) + CANVAS_MARGIN
    height = max((b["y"] + b["h"] for b in boxes), default=0) + CANVAS_MARGIN

    svg = [f'<svg width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}">',
           '<defs>',
           '<marker id="arrow" markerWidth="10" markerHeight="8" refX="9" '
           'refY="4" orient="auto" markerUnits="userSpaceOnUse">'
           '<path d="M0,0 L10,4 L0,8 z" fill="#5b5b66"/></marker>',
           '<marker id="diamond" markerWidth="14" markerHeight="8" refX="1" '
           'refY="4" orient="auto" markerUnits="userSpaceOnUse">'
           '<path d="M1,4 L7,0.5 L13,4 L7,7.5 z" fill="#ffffff" '
           'stroke="#5b5b66"/></marker>',
           '</defs>']
    for edge in edges:
        classes = "edge dotted" if edge["dotted"] else "edge"
        markers = ('marker-start="url(#diamond)"' if edge["containment"]
                   else 'marker-end="url(#arrow)"')
        svg.append(
            f'<line class="{classes}" x1="{edge["x1"]:.1f}" '
            f'y1="{edge["y1"]:.1f}" x2="{edge["x2"]:.1f}" '
            f'y2="{edge["y2"]:.1f}" {markers}>'
            f'<title>{html.escape(edge["label"])}</title></line>')
    svg.append("</svg>")

    divs = []
    for box in boxes:
        kind = "container" if box["container"] else "leaf"
        name = html.escape(box["element"].get("name") or "")
        description = html.escape(
            model.properties(box["element"]).get("Omschrijving", ""))
        title_attr = f' title="{description}"' if description else ""
        divs.append(
            f'<div class="box {kind} {layer_of(box["element"])}" '
            f'style="left:{box["x"]}px;top:{box["y"]}px;'
            f'width:{box["w"]}px;height:{box["h"]}px"{title_attr}>'
            f'{name}</div>')

    name = diagram.get("name") or "(naamloze view)"
    documentation = model.documentation(diagram)
    doc_html = (f"      <p class=\"doc\">{html.escape(documentation)}</p>\n"
                if documentation else "")
    body = (
        f'      <nldd-title size="2"><h1>{html.escape(name)}</h1></nldd-title>\n'
        f'{doc_html}'
        f'      <nldd-spacer size="16"></nldd-spacer>\n'
        f'      <div class="diagram-wrap">\n'
        f'        <div class="diagram" '
        f'style="width:{width}px;height:{height}px">\n'
        f'          {"".join(svg)}\n'
        f'          {"".join(divs)}\n'
        f'        </div>\n'
        f'      </div>\n'
        f'      <nldd-spacer size="16"></nldd-spacer>\n'
        f'      <p class="meta">{len(boxes)} elementen, {len(edges)} '
        f'getekende verbindingen — gegenereerd uit '
        f'<code>{html.escape(Path(model.path).as_posix())}</code> · '
        f'<a href="index.html">alle views</a></p>')
    return page_shell(name, body)


def render_index_html(model, entries) -> str:
    cards = []
    for name, filename, n_boxes, n_edges in entries:
        cards.append(
            f'        <a class="card-link" href="{filename}">'
            f'<nldd-card accessible-label="{html.escape(name)}">'
            f'<nldd-container padding="16">'
            f'<nldd-title size="4"><h2>{html.escape(name)}</h2></nldd-title>'
            f'<p class="meta">{n_boxes} elementen, {n_edges} verbindingen</p>'
            f'</nldd-container>'
            f'</nldd-card></a>')
    body = (
        f'      <nldd-title size="2"><h1>{html.escape(model.name)} — views'
        f'</h1></nldd-title>\n'
        f'      <p class="doc">Weergaven gegenereerd uit '
        f'<code>{html.escape(Path(model.path).as_posix())}</code>, '
        f'met de layout zoals die in het model is vastgelegd.</p>\n'
        f'      <nldd-spacer size="16"></nldd-spacer>\n'
        f'      <nldd-collection layout="grid" item-width="320px">\n'
        + "\n".join(cards) + "\n"
        f'      </nldd-collection>')
    return page_shell(f"{model.name} — views", body)


def render_all_html(model, out_dir) -> tuple[list, list]:
    """Render every view to HTML; returns (written, removed) path lists."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written, produced, entries = [], set(), []

    index = model.id_index()
    for diagram in model.diagrams():
        name = diagram.get("name") or diagram.get("id")
        filename = slugify(name) + ".html"
        path = out / filename
        if write_if_changed(path, render_view_html(model, diagram)):
            written.append(path)
        produced.add(path.name)
        boxes = absolute_boxes(diagram, index)
        edges = diagram_edges(model, diagram, {b["id"]: b for b in boxes})
        entries.append((name, filename, len(boxes), len(edges)))

    index_path = out / "index.html"
    if write_if_changed(index_path, render_index_html(model, entries)):
        written.append(index_path)
    produced.add(index_path.name)

    removed = []
    for stale in out.glob("*.html"):
        if stale.name in produced:
            continue
        first_line = stale.read_text(encoding="utf-8").split("\n", 1)[0]
        if first_line.strip() == MARKER:
            stale.unlink()
            removed.append(stale)
    return written, removed
