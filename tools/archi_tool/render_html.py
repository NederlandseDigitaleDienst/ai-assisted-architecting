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

from .links import links_for
from .model import FOLDER_BY_ELEMENT_TYPE, xsi_type
from .render import (CONTAINMENT_TYPES, DOTTED_TYPES, LAYER_PALETTE, MARKER,
                     display_model_path, is_descendant, view_stems,
                     write_if_changed)

NLDD_VERSION = "0.8.64"
NLDD_CSS = (f"https://cdn.jsdelivr.net/npm/@nldd/design-system@{NLDD_VERSION}"
            "/dist/css/global.css")
NLDD_JS = f"https://cdn.jsdelivr.net/npm/@nldd/design-system@{NLDD_VERSION}/+esm"

CANVAS_MARGIN = 40

LAYER_LABELS = {
    "strategy": "Strategie",
    "business": "Bedrijf",
    "application": "Applicatie",
    "technology": "Technologie",
    "motivation": "Motivatie",
    "implementation_migration": "Implementatie & migratie",
    "other": "Overig",
}

# two stacked ArchiMate-colored blocks with a connector, as inline data URI
# so the pages stay fully self-contained ("#" must be encoded as %23)
FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect x='3' y='4' width='17' height='10' rx='2' fill='%23FAC75A' "
    "stroke='%23D4882A'/%3E"
    "%3Crect x='12' y='19' width='17' height='10' rx='2' fill='%23CECBF6' "
    "stroke='%237F77DD'/%3E"
    "%3Cpath d='M11 14v4h6v1' fill='none' stroke='%235b5b66' "
    "stroke-width='1.5'/%3E"
    "%3C/svg%3E")


# view-only child types (no archimateElement): notes, visual groups and
# references to other views all render, everything else is skipped
VIEW_ONLY_KINDS = {"Note": "note", "Group": "group",
                   "DiagramModelReference": "ref"}


def absolute_boxes(diagram, index) -> list:
    """Resolve diagram objects to absolute canvas coordinates."""
    boxes = []

    def walk(objects, offset_x, offset_y):
        for obj in objects:
            element = index.get(obj.get("archimateElement") or "")
            bounds = obj.find("bounds")
            if bounds is None:
                continue
            kind = "element" if element is not None else \
                VIEW_ONLY_KINDS.get(xsi_type(obj))
            if kind is None:
                continue
            x = offset_x + int(bounds.get("x", "0"))
            y = offset_y + int(bounds.get("y", "0"))
            children = obj.findall("child")
            boxes.append({
                "id": obj.get("id"), "element": element, "kind": kind,
                "node": obj,
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
        source_cx = source["x"] + source["w"] / 2
        source_cy = source["y"] + source["h"] / 2
        target_cx = target["x"] + target["w"] / 2
        target_cy = target["y"] + target["h"] / 2
        # bendpoint offsets are stored relative to the source center
        waypoints = [
            (source_cx + int(bp.get("startX", "0")),
             source_cy + int(bp.get("startY", "0")))
            for bp in conn.findall("bendpoint")]
        first = waypoints[0] if waypoints else (target_cx, target_cy)
        last = waypoints[-1] if waypoints else (source_cx, source_cy)
        x1, y1 = border_point(source, *first)
        x2, y2 = border_point(target, *last)
        label = (rel.get("name") if rel is not None else None) or rel_type
        edges.append({
            "points": [(x1, y1), *waypoints, (x2, y2)], "label": label,
            "source_id": conn.get("source"), "target_id": conn.get("target"),
            "dotted": rel_type in DOTTED_TYPES,
            "containment": rel_type in CONTAINMENT_TYPES,
            # a connection without relationship attaches a note: dotted, no
            # arrowhead, exactly as Archi draws it
            "note_link": rel is None,
        })
    return edges


def layer_of(element) -> str:
    return FOLDER_BY_ELEMENT_TYPE.get(xsi_type(element), "other")


# small "mini view" glyph for references to another view
VIEW_REF_ICON = (
    '<svg viewBox="0 0 16 16" width="13" height="13" fill="none" '
    'stroke="currentColor" aria-hidden="true">'
    '<rect x="1.5" y="2.5" width="13" height="11" rx="1.5"/>'
    '<rect x="4" y="5" width="3.4" height="2.6"/>'
    '<rect x="8.8" y="8.6" width="3.4" height="2.6"/>'
    '<path d="M7.4 6.3h3.1v2.3"/></svg>')


def element_icon(element) -> str:
    """ArchiMate notation icon (nested notation: top-right of the box)."""
    glyph = ICON_GLYPHS.get(ICON_BY_TYPE.get(xsi_type(element), ""))
    if not glyph:
        return ""
    _, stroke, _ = LAYER_PALETTE[layer_of(element)]
    return (f'<svg class="type-icon" viewBox="0 0 16 16" width="14" '
            f'height="14" fill="none" stroke="currentColor" '
            f'style="color:{stroke}" aria-hidden="true">{glyph}</svg>')


# behavior glyphs repeat across layers; every element type maps to a glyph
ICON_BY_TYPE = {
    # strategy
    "Resource": "Resource", "Capability": "Capability",
    "CourseOfAction": "CourseOfAction", "ValueStream": "ValueStream",
    # business
    "BusinessActor": "BusinessActor", "BusinessRole": "BusinessRole",
    "BusinessCollaboration": "Collaboration",
    "BusinessInterface": "Interface", "BusinessProcess": "Process",
    "BusinessFunction": "Function", "BusinessInteraction": "Interaction",
    "BusinessEvent": "Event", "BusinessService": "Service",
    "BusinessObject": "Object", "Contract": "Contract",
    "Representation": "Representation", "Product": "Product",
    # application
    "ApplicationComponent": "ApplicationComponent",
    "ApplicationCollaboration": "Collaboration",
    "ApplicationInterface": "Interface", "ApplicationFunction": "Function",
    "ApplicationInteraction": "Interaction",
    "ApplicationProcess": "Process", "ApplicationEvent": "Event",
    "ApplicationService": "Service", "DataObject": "Object",
    # technology & physical
    "Node": "Node", "Device": "Device", "SystemSoftware": "SystemSoftware",
    "TechnologyCollaboration": "Collaboration",
    "TechnologyInterface": "Interface", "Path": "Path",
    "CommunicationNetwork": "CommunicationNetwork",
    "TechnologyFunction": "Function", "TechnologyProcess": "Process",
    "TechnologyInteraction": "Interaction", "TechnologyEvent": "Event",
    "TechnologyService": "Service", "Artifact": "Artifact",
    "Material": "Material", "Equipment": "Equipment",
    "Facility": "Facility", "DistributionNetwork": "DistributionNetwork",
    # motivation
    "Stakeholder": "Stakeholder", "Driver": "Driver",
    "Assessment": "Assessment", "Goal": "Goal", "Outcome": "Outcome",
    "Principle": "Principle", "Requirement": "Requirement",
    "Constraint": "Constraint", "Meaning": "Meaning", "Value": "Value",
    # implementation & migration
    "WorkPackage": "WorkPackage", "Deliverable": "Deliverable",
    "ImplementationEvent": "Event", "Plateau": "Plateau", "Gap": "Gap",
    # other
    "Location": "Location", "Grouping": "Grouping", "Junction": "Junction",
}

# inner SVG per glyph for a 16x16 viewBox, ported from the drawIcon()
# methods in Archi's figure classes (stroke follows the layer line color)
ICON_GLYPHS = {
    # Resource: rounded rect body + right nub + 3 vertical lines
    "Resource": '<g fill="none" stroke="currentColor"><rect x="1" y="3.9" width="12.4" height="8.2" rx="1.2"/><rect x="13.4" y="6.4" width="1.6" height="3.3" rx="0.4"/><line x1="3.5" y1="5.5" x2="3.5" y2="10.5"/><line x1="5.9" y1="5.5" x2="5.9" y2="10.5"/><line x1="8.4" y1="5.5" x2="8.4" y2="10.5"/></g>',
    # Capability: staircase of six squares
    "Capability": '<g fill="none" stroke="currentColor"><rect x="10.3" y="1" width="4.7" height="4.7"/><rect x="5.7" y="5.7" width="4.6" height="4.6"/><rect x="10.3" y="5.7" width="4.7" height="4.6"/><rect x="1" y="10.3" width="4.7" height="4.7"/><rect x="5.7" y="10.3" width="4.6" height="4.7"/><rect x="10.3" y="10.3" width="4.7" height="4.7"/></g>',
    # CourseOfAction: target circles + arrow toward the bullseye
    "CourseOfAction": '<g fill="none" stroke="currentColor"><polygon points="2.4,8.6 6.5,9.3 4.4,12.9" fill="currentColor" stroke="none"/><path d="M4.4 10.7 A3.4 3.4 0 0 0 1 13.5"/><circle cx="10.5" cy="6.9" r="4.5"/><circle cx="10.5" cy="6.9" r="2.7"/><circle cx="10.5" cy="6.9" r="1"/><circle cx="10.5" cy="6.9" r="0.3"/></g>',
    # ValueStream: chevron
    "ValueStream": '<polygon points="1,3.3 10.3,3.3 15,8 10.3,12.7 1,12.7 5.7,8" fill="none" stroke="currentColor"/>',
    # ApplicationComponent: rectangle with two protruding nubs
    "ApplicationComponent": '<g fill="none" stroke="currentColor"><path d="M4.2 15L4.2 10.7M4.2 8.5L4.2 6.4M4.2 3.2L4.2 1L15 1L15 15L3.7 15"/><rect x="1" y="3.2" width="6.5" height="2.7"/><rect x="1" y="8.5" width="6.5" height="2.7"/></g>',
    # Node: 3D box
    "Node": '<g fill="none" stroke="currentColor"><rect x="1.2" y="4" width="10.8" height="10.8"/><path d="M1 4L4.4 1L15 1L15 11.8L12 15M12 4L15 1"/></g>',
    # Device: rounded screen on a foot
    "Device": '<g fill="none" stroke="currentColor"><rect x="2.1" y="1.5" width="11.8" height="8.6" rx="1.6"/><polygon points="1,14.5 4.2,10.2 11.8,10.2 15,14.5"/></g>',
    # SystemSoftware: two overlapping circles
    "SystemSoftware": '<g fill="none" stroke="currentColor"><circle cx="6.9" cy="9.1" r="5.9"/><path d="M12 12.1A5.9 5.9 0 1 0 3.9 4"/></g>',
    # Path: dashed line between two arrowheads
    "Path": '<g fill="none" stroke="currentColor"><path d="M3.9 8L5.5 8M7.2 8L8.8 8M10.5 8L12.1 8"/><path d="M5.1 3.9L1 8L5.1 12.1M10.9 3.9L15 8L10.9 12.1"/></g>',
    # CommunicationNetwork: four linked nodes
    "CommunicationNetwork": '<g fill="none" stroke="currentColor"><circle cx="3.3" cy="11.7" r="2.3"/><circle cx="5.2" cy="4.3" r="2.3"/><circle cx="12.7" cy="4.3" r="2.3"/><circle cx="10.8" cy="11.7" r="2.3"/><path d="M3.8 9.4L4.7 6.6M11.3 9.4L12.2 6.6M5.7 11.7L8.5 11.7M7.5 4.3L10.3 4.3"/></g>',
    # BusinessActor: stick figure
    "BusinessActor": '<ellipse cx="8" cy="3.5" rx="2.5" ry="2.5" stroke="currentColor" fill="none"/><line x1="8" y1="5.9" x2="8" y2="10.9" stroke="currentColor"/><line x1="8" y1="10.9" x2="4.7" y2="15" stroke="currentColor"/><line x1="8" y1="10.9" x2="11.3" y2="15" stroke="currentColor"/><line x1="4.7" y1="8.4" x2="11.3" y2="8.4" stroke="currentColor"/>',
    # BusinessRole: cylinder on its side
    "BusinessRole": '<path d="M3.3 4.3 A2.3 3.7 0 0 0 3.3 11.7 L12.2 11.7 M2.9 4.3 L12.2 4.3" stroke="currentColor" fill="none"/><ellipse cx="12.7" cy="8" rx="2.3" ry="3.7" stroke="currentColor" fill="none"/>',
    # Object: rectangle with title band
    "Object": '<rect x="1" y="2.6" width="14" height="10.8" stroke="currentColor" fill="none"/><line x1="1" y1="5.8" x2="15" y2="5.8" stroke="currentColor"/>',
    # Contract: object with bottom band
    "Contract": '<rect x="1" y="2.6" width="14" height="10.8" stroke="currentColor" fill="none"/><line x1="1" y1="5.8" x2="15" y2="5.8" stroke="currentColor"/><line x1="1" y1="10.2" x2="15" y2="10.2" stroke="currentColor"/>',
    # Representation: rectangle with wavy bottom
    "Representation": '<path d="M1 3.1 L1 10.6 Q4 14.6 9 11.6 Q12 9.1 15 11.6 L15 3.1 Z" stroke="currentColor" fill="none"/>',
    # Product: rectangle with corner tab
    "Product": '<rect x="1" y="2.6" width="14" height="10.8" stroke="currentColor" fill="none"/><rect x="1" y="2.6" width="6.5" height="3.2" stroke="currentColor" fill="none"/>',
    # Process: fat arrow
    "Process": '<polygon points="1,6 9,6 9,3 15,8 9,13 9,10 1,10" fill="none" stroke="currentColor"/>',
    # Function: arrow-tent
    "Function": '<polygon points="2,15 2,6 8,1 14,6 14,15 8,9" fill="none" stroke="currentColor"/>',
    # Interaction: split ellipse halves
    "Interaction": '<path d="M6.5 2 A5 6 0 0 0 6.5 14 L6.5 1.5" fill="none" stroke="currentColor"/><path d="M9.5 14 A5 6 0 0 0 9.5 2 L9.5 14.5" fill="none" stroke="currentColor"/>',
    # Event: open-ended rounded arrow
    "Event": '<path d="M1 4.1 L1 11.9 A3.5 3.9 0 0 0 1 4.1 M11.5 11.9 A3.5 3.9 0 0 0 11.5 4.1 M1 4.1 L11.5 4.1 M1 11.9 L11.5 11.9" fill="none" stroke="currentColor"/>',
    # Service: pill
    "Service": '<rect x="1" y="4.1" width="14" height="7.9" rx="3.5" ry="3.5" fill="none" stroke="currentColor"/>',
    # Collaboration: two overlapping circles
    "Collaboration": '<circle cx="6" cy="8" r="5" fill="none" stroke="currentColor"/><circle cx="10" cy="8" r="5" fill="none" stroke="currentColor"/>',
    # Interface: lollipop
    "Interface": '<circle cx="10.9" cy="8" r="4.1" fill="none" stroke="currentColor"/><line x1="6.8" y1="8" x2="1" y2="8" stroke="currentColor"/>',
    # Artifact: document with folded corner
    "Artifact": '<path d="M2.4 1 L8.9 1 L13.6 5.7 L13.6 15 L2.4 15 Z M8.9 1 L8.9 5.7 L13.6 5.7" fill="none" stroke="currentColor"/>',
    # Material: hexagon with inner marks
    "Material": '<polygon points="11.5,1.9 4.5,1.9 1,8 3.6,14.1 11.5,14.1 15,8" fill="none" stroke="currentColor"/><path d="M6.2 3.6 L3.4 8.4 M4.8 11.9 L10.6 11.9 M12.4 8.4 L9.8 3.6" fill="none" stroke="currentColor"/>',
    # Equipment: two cogs
    "Equipment": '<polygon points="10.9,11 12.1,11 12.1,9.6 10.9,9.6 10.4,8.3 11.2,7.5 10.2,6.5 9.4,7.4 8.1,6.8 8.1,5.6 6.7,5.6 6.7,6.8 5.4,7.4 4.6,6.5 3.6,7.5 4.5,8.3 3.9,9.6 2.7,9.6 2.7,11 3.9,11 4.5,12.3 3.6,13.1 4.6,14.1 5.4,13.3 6.7,13.8 6.7,15 8.1,15 8.1,13.8 9.4,13.3 10.2,14.1 11.2,13.1 10.4,12.3" fill="none" stroke="currentColor"/><circle cx="7.4" cy="10.3" r="1.8" fill="none" stroke="currentColor"/><polygon points="12.7,4.4 13.3,4.4 13.3,3.2 12.7,3.2 12,2.1 12.3,1.6 11.3,1 11,1.5 9.8,1.5 9.4,1 8.4,1.6 8.7,2.1 8.1,3.2 7.5,3.2 7.5,4.4 8.1,4.4 8.7,5.5 8.4,6 9.4,6.6 9.8,6.1 11,6.1 11.3,6.6 12.3,6 12,5.5" fill="none" stroke="currentColor"/><circle cx="10.4" cy="3.8" r="1.2" fill="none" stroke="currentColor"/>',
    # Facility: factory with sawtooth roof
    "Facility": '<polygon points="1,13.6 15,13.6 15,8 11.3,10.8 11.3,8 7.5,10.8 7.5,8 3.8,10.8 3.8,2.4 1,2.4" fill="none" stroke="currentColor"/>',
    # DistributionNetwork: double arrow
    "DistributionNetwork": '<path d="M2.6 6.4 L13.4 6.4 M2.6 9.6 L13.4 9.6 M5.1 3.9 L1 8 L5.1 12.1 M10.9 3.9 L15 8 L10.9 12.1" fill="none" stroke="currentColor"/>',
    # Stakeholder: cylinder with circle (role variant)
    "Stakeholder": '<path d="M4.7 4.7A3.7 3.3 0 0 0 4.7 11.3L11.3 11.3M4.3 4.7L11.3 4.7"/><ellipse cx="11.7" cy="8" rx="3.3" ry="3.3"/>',
    # Driver: steering wheel
    "Driver": '<ellipse cx="8" cy="8" rx="5.4" ry="5.4"/><ellipse cx="8" cy="8" rx="1.2" ry="1.2" fill="currentColor"/><line x1="1" y1="8" x2="15" y2="8"/><line x1="8" y1="1" x2="8" y2="15"/><line x1="3.1" y1="3.1" x2="12.9" y2="12.9"/><line x1="3.1" y1="12.9" x2="12.9" y2="3.1"/>',
    # Assessment: magnifying glass
    "Assessment": '<ellipse cx="9.8" cy="5.7" rx="4.7" ry="4.7"/><line x1="7.4" y1="9.2" x2="1.6" y2="15"/>',
    # Goal: target with filled bullseye
    "Goal": '<ellipse cx="8" cy="8" rx="7" ry="7"/><ellipse cx="8" cy="8" rx="4.3" ry="4.3"/><ellipse cx="8" cy="8" rx="1.6" ry="1.6" fill="currentColor"/>',
    # Outcome: target with arrow in the bullseye
    "Outcome": '<ellipse cx="6.1" cy="9.9" rx="5.1" ry="5.1"/><ellipse cx="6.1" cy="9.9" rx="3.1" ry="3.1"/><ellipse cx="6.1" cy="9.9" rx="1.2" ry="1.2" fill="currentColor"/><line x1="5.7" y1="10.3" x2="13.1" y2="2.9"/><line x1="11.1" y1="4.9" x2="11.9" y2="1"/><line x1="11.1" y1="4.9" x2="15" y2="4.1"/>',
    # Principle: rounded rectangle with exclamation mark
    "Principle": '<rect x="2" y="1" width="12" height="14" rx="2"/><line x1="7.5" y1="3" x2="7.5" y2="10"/><line x1="8.5" y1="3" x2="8.5" y2="10"/><line x1="7.5" y1="11.5" x2="7.5" y2="13.5"/><line x1="8.5" y1="11.5" x2="8.5" y2="13.5"/>',
    # Requirement: parallelogram
    "Requirement": '<polygon points="4.5,4.1 15,4.1 11.5,11.9 1,11.9"/>',
    # Constraint: parallelogram with slash
    "Constraint": '<polygon points="4.5,4.1 15,4.1 11.5,11.9 1,11.9"/><line x1="8" y1="4.1" x2="4.5" y2="11.9"/>',
    # Meaning: cloud
    "Meaning": '<path d="M8.6 3.4A5.1 3.8 0 0 0 1.6 8.6M13.9 9.1A5.1 3.8 0 0 0 7.4 3.4M7.7 12A3.8 3.2 0 0 1 1.6 8.2M13.7 8.8A3.8 3.8 0 0 1 7.5 12.2"/>',
    # Value: wide ellipse
    "Value": '<ellipse cx="8" cy="8" rx="7" ry="4.5"/>',
    # WorkPackage: circular arrow
    "WorkPackage": '<path d="M9.1 8 A4.2 4.2 0 1 0 5.6 10.8"/><line x1="5.2" y1="10.8" x2="11.3" y2="10.8"/><polygon points="11.3,8 15,10.8 11.3,13.6" fill="currentColor"/>',
    # Deliverable: rectangle with wavy bottom
    "Deliverable": '<path d="M1 3.1 L1 10.6 Q4 14.6 9 11.6 Q12 9.1 15 11.6 L15 3.1 Z"/>',
    # Plateau: three staggered lines
    "Plateau": '<line x1="4.5" y1="5.4" x2="15" y2="5.4"/><line x1="2.8" y1="8" x2="13.3" y2="8"/><line x1="1" y1="10.6" x2="11.5" y2="10.6"/>',
    # Gap: circle crossed by two lines
    "Gap": '<ellipse cx="8" cy="8" rx="5.4" ry="5.4"/><line x1="1" y1="6.8" x2="15" y2="6.8"/><line x1="1" y1="9.2" x2="15" y2="9.2"/>',
    # Location: map pin
    "Location": '<path d="M12.4 7.3 A4.7 4.7 0 1 0 3.6 7.3 L8 15 Z"/>',
    # Grouping: rectangle with corner tab
    "Grouping": '<rect x="1" y="2.6" width="6.5" height="3.2"/><rect x="1" y="5.8" width="14" height="7.5"/>',
    # Junction: connectors meeting in a filled dot
    "Junction": '<rect x="1" y="2" width="2" height="2"/><rect x="1" y="12" width="2" height="2"/><rect x="13" y="7" width="2" height="2"/><line x1="3" y1="4" x2="5" y2="6"/><line x1="9" y1="8" x2="13" y2="8"/><line x1="3" y1="12" x2="5" y2="10"/><ellipse cx="7" cy="8" rx="3" ry="3" fill="currentColor"/>',
}


def legend_html(boxes, edges) -> str:
    """Legend chips for the layers and line styles present in the view.
    Lives inside the always-light canvas, hence the fixed colors."""
    parts = []
    for layer in sorted({layer_of(b["element"]) for b in boxes
                         if b["kind"] == "element"}):
        fill, stroke, _ = LAYER_PALETTE[layer]
        parts.append(
            f'<span class="legend-item"><span class="swatch" '
            f'style="background:{fill};border-color:{stroke}"></span>'
            f'{LAYER_LABELS.get(layer, layer)}</span>')
    if any(e["containment"] for e in edges):
        parts.append(
            '<span class="legend-item"><svg width="26" height="10" '
            'viewBox="0 0 26 10" aria-hidden="true">'
            '<line x1="8" y1="5" x2="26" y2="5" class="edge"/>'
            '<path d="M1,5 L5,2 L9,5 L5,8 z" fill="#ffffff" '
            'stroke="#5b5b66"/></svg>bevat</span>')
    if any(e["dotted"] for e in edges):
        parts.append(
            '<span class="legend-item"><svg width="26" height="10" '
            'viewBox="0 0 26 10" aria-hidden="true">'
            '<line x1="0" y1="5" x2="20" y2="5" class="edge dotted"/>'
            '<path d="M19,2 L26,5 L19,8 z" fill="#5b5b66"/></svg>'
            'beïnvloedt of realiseert</span>')
    if any(not e["dotted"] and not e["containment"] and not e["note_link"]
           for e in edges):
        parts.append(
            '<span class="legend-item"><svg width="26" height="10" '
            'viewBox="0 0 26 10" aria-hidden="true">'
            '<line x1="0" y1="5" x2="20" y2="5" class="edge"/>'
            '<path d="M19,2 L26,5 L19,8 z" fill="#5b5b66"/></svg>'
            'overige relatie</span>')
    if not parts:
        return ""
    return '<div class="legend">' + "".join(parts) + "</div>"


def view_thumbnail_svg(boxes) -> str:
    """Miniature of the view layout: colored rectangles, no text."""
    if not boxes:
        return ""
    width = max(b["x"] + b["w"] for b in boxes)
    height = max(b["y"] + b["h"] for b in boxes)
    rects = []
    for box in boxes:
        if box["kind"] == "element":
            fill, stroke, _ = LAYER_PALETTE[layer_of(box["element"])]
        else:
            fill, stroke = "#ECECF1", "#9B9BA4"   # notes/groups/refs: neutral
        opacity = ' fill-opacity="0.35"' if box["container"] else ""
        rects.append(
            f'<rect x="{box["x"]}" y="{box["y"]}" width="{box["w"]}" '
            f'height="{box["h"]}" rx="6" fill="{fill}"{opacity} '
            f'stroke="{stroke}" vector-effect="non-scaling-stroke"/>')
    return (f'<svg class="thumb-svg" viewBox="-12 -12 {width + 24} '
            f'{height + 24}" preserveAspectRatio="xMidYMid meet" '
            f'aria-hidden="true">{"".join(rects)}</svg>')


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


# shared between the view pages and the slide decks (render_slides.py)
DIAGRAM_CSS = """\
    /* the diagram canvas is always light, like an image: the ArchiMate
       palette is designed for a light surface */
    .diagram-wrap { overflow-x: auto; border-radius: 12px;
      border: 1px solid var(--primitives-color-neutral-200);
      background: #ffffff; }
    .diagram { position: relative; }
    .diagram > svg { position: absolute; inset: 0; }
    .edge { stroke: #5b5b66; stroke-width: 1.3; }
    .edge.dotted { stroke-dasharray: 5 3; }
    .box { position: absolute; box-sizing: border-box;
      font-size: 13px; line-height: 1.3; }
    .leaf { display: flex; align-items: center; justify-content: center;
      text-align: center; padding: 4px 10px; border-radius: 6px;
      border: 1px solid; box-shadow: 0 1px 2px rgb(0 0 0 / 0.10);
      transition: box-shadow 0.15s ease; }
    .leaf:hover { box-shadow: 0 3px 10px rgb(0 0 0 / 0.20); }
    .box-link { color: inherit; text-decoration: none; }
    .box-link > .box { cursor: pointer; }
    .box-link > .box::after { content: "↗"; position: absolute;
      bottom: 2px; right: 5px; font-size: 11px; opacity: 0.6; }
    .box-link:hover > .box, .box-link:focus-visible > .box {
      outline: 2px solid #154273; outline-offset: 1px; }
    .container { border-radius: 10px; border: 1.5px solid;
      padding: 10px 14px; font-weight: 550; }
    .type-icon { position: absolute; top: 3px; right: 4px;
      pointer-events: none; }
    /* notes, groups and view references live on the light canvas too */
    .note { background: #FEFCF0; border: 1px solid #9B9BA4; color: #3A3A40;
      padding: 6px 9px; font-size: 12px; text-align: left;
      white-space: pre-wrap;
      clip-path: polygon(0 0, 100% 0, 100% calc(100% - 11px),
        calc(100% - 11px) 100%, 0 100%); }
    .group { border: 1px solid #9B9BA4; background: #F4F4F7; color: #3A3A40;
      padding: 4px 10px; font-weight: 550; text-align: left; }
    .ref { display: flex; align-items: center; justify-content: center;
      gap: 6px; padding: 4px 10px; border-radius: 6px;
      border: 1px solid #9B9BA4; background: #ECECF1; color: #444451; }
    .ref a { color: inherit; }
    .ref svg { flex: none; }
    /* legend sits inside the light canvas: fixed light-surface colors */
    .legend { display: flex; flex-wrap: wrap; gap: 6px 18px;
      align-items: center; padding: 10px 14px;
      border-top: 1px solid #e6e6eb; font-size: 12.5px; color: #55555e; }
    .legend-item { display: inline-flex; align-items: center; gap: 6px; }
    .legend-item svg { flex: none; }
    .swatch { width: 12px; height: 12px; border-radius: 3px;
      border: 1px solid; display: inline-block; flex: none; }
"""

PAGE_CSS = """
    /* NLDD primitives are light-dark() pairs themselves: use a single token
       and it follows the color scheme — never wrap them in light-dark(). */
    .doc { max-width: 72ch; color: var(--primitives-color-neutral-700); }
""" + DIAGRAM_CSS + """\
    .card-link { text-decoration: none; color: inherit; display: block;
      height: 100%; }
    /* thumbnails mirror the diagram canvas: always light */
    .thumb { background: #ffffff; border: 1px solid #e6e6eb;
      border-radius: 8px; height: 150px; padding: 10px;
      display: flex; align-items: center; justify-content: center; }
    .thumb-svg { width: 100%; height: 100%; }
    .meta { color: var(--primitives-color-neutral-600); font-size: 14px; }
"""


def page_shell(title: str, body: str) -> str:
    return f"""{MARKER}
<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="icon" href="{FAVICON}">
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
    <nldd-simple-section width="full">
{body}
    </nldd-simple-section>
  </nldd-page>
</nldd-app-view>
</body>
</html>
"""


def diagram_canvas(model, diagram, marker_prefix: str = "",
                   ref_base: str = "", dim_ids: set | None = None,
                   links: dict | None = None) -> dict:
    """Edge SVG and positioned box divs for one diagram, plus metadata.

    marker_prefix keeps the SVG marker ids unique when several diagrams
    share one document (the slide decks embed many); ref_base prefixes the
    links of view-reference boxes so they resolve from other directories;
    dim_ids marks diagram objects (and edges touching them) with a "dim"
    class so a slide can spotlight the rest; links maps an element name to
    the href its boxes should link to (from the links file, already
    prefixed by the caller).
    """
    index = model.id_index()
    boxes = absolute_boxes(diagram, index)
    box_by_object_id = {b["id"]: b for b in boxes}
    edges = diagram_edges(model, diagram, box_by_object_id)
    dim_ids = dim_ids or set()

    width = max((b["x"] + b["w"] for b in boxes), default=0) + CANVAS_MARGIN
    height = max((b["y"] + b["h"] for b in boxes), default=0) + CANVAS_MARGIN

    svg = [f'<svg width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}">',
           '<defs>',
           f'<marker id="{marker_prefix}arrow" markerWidth="10" '
           'markerHeight="8" refX="9" '
           'refY="4" orient="auto" markerUnits="userSpaceOnUse">'
           '<path d="M0,0 L10,4 L0,8 z" fill="#5b5b66"/></marker>',
           f'<marker id="{marker_prefix}diamond" markerWidth="14" '
           'markerHeight="8" refX="1" '
           'refY="4" orient="auto" markerUnits="userSpaceOnUse">'
           '<path d="M1,4 L7,0.5 L13,4 L7,7.5 z" fill="#ffffff" '
           'stroke="#5b5b66"/></marker>',
           '</defs>']
    for edge in edges:
        dotted = edge["dotted"] or edge["note_link"]
        classes = "edge dotted" if dotted else "edge"
        if edge["source_id"] in dim_ids or edge["target_id"] in dim_ids:
            classes += " dim"
        if edge["note_link"]:
            markers = ""
        elif edge["containment"]:
            markers = f' marker-start="url(#{marker_prefix}diamond)"'
        else:
            markers = f' marker-end="url(#{marker_prefix}arrow)"'
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in edge["points"])
        svg.append(
            f'<polyline class="{classes}" points="{points}" '
            f'fill="none"{markers}>'
            f'<title>{html.escape(edge["label"])}</title></polyline>')
    svg.append("</svg>")

    divs = []
    for box in boxes:
        style = (f'left:{box["x"]}px;top:{box["y"]}px;'
                 f'width:{box["w"]}px;height:{box["h"]}px')
        dim = " dim" if box["id"] in dim_ids else ""
        if box["kind"] == "element":
            kind = "container" if box["container"] else "leaf"
            name = html.escape(box["element"].get("name") or "")
            # Archi's own documentation field first; the "Omschrijving"
            # property only as a fallback for older models.
            description = html.escape(
                model.documentation(box["element"])
                or model.properties(box["element"]).get("Omschrijving", ""))
            title_attr = f' title="{description}"' if description else ""
            box_html = (
                f'<div class="box {kind} {layer_of(box["element"])}{dim}" '
                f'style="{style}"{title_attr}>'
                f'{element_icon(box["element"])}{name}</div>')
            href = (links or {}).get(box["element"].get("name") or "")
            if href:
                box_html = (f'<a class="box-link" href="{html.escape(href)}">'
                            f'{box_html}</a>')
            divs.append(box_html)
        elif box["kind"] == "note":
            content = box["node"].find("content")
            text = html.escape(
                (content.text if content is not None else "") or "")
            divs.append(
                f'<div class="box note{dim}" style="{style}">{text}</div>')
        elif box["kind"] == "group":
            name = html.escape(box["node"].get("name") or "")
            divs.append(
                f'<div class="box group{dim}" style="{style}">{name}</div>')
        else:  # reference to another view
            ref = index.get(box["node"].get("model") or "")
            ref_name = (ref.get("name") or "") if ref is not None else ""
            stem = (view_stems(model).get(ref.get("id"), "view")
                    if ref is not None else "view")
            href = ref_base + stem + ".html"
            divs.append(
                f'<div class="box ref{dim}" style="{style}">'
                f'{VIEW_REF_ICON}<a href="{href}">'
                f'{html.escape(ref_name or "(view)")}</a></div>')

    return {"svg": "".join(svg), "divs": "".join(divs),
            "width": width, "height": height,
            "boxes": boxes, "edges": edges}


def render_view_html(model, diagram, links: dict | None = None) -> str:
    canvas = diagram_canvas(model, diagram, links=links)
    name = diagram.get("name") or "(naamloze view)"
    documentation = model.documentation(diagram)
    doc_html = (f"      <p class=\"doc\">{html.escape(documentation)}</p>\n"
                if documentation else "")
    body = (
        f'      <nldd-link href="index.html" size="sm" '
        f'start-icon="arrow-left" text="Alle views"></nldd-link>\n'
        f'      <nldd-spacer size="8"></nldd-spacer>\n'
        f'      <nldd-title size="2"><h1>{html.escape(name)}</h1></nldd-title>\n'
        f'{doc_html}'
        f'      <nldd-spacer size="16"></nldd-spacer>\n'
        f'      <div class="diagram-wrap">\n'
        f'        <div class="diagram" '
        f'style="width:{canvas["width"]}px;height:{canvas["height"]}px">\n'
        f'          {canvas["svg"]}\n'
        f'          {canvas["divs"]}\n'
        f'        </div>\n'
        f'        {legend_html(canvas["boxes"], canvas["edges"])}\n'
        f'      </div>\n'
        f'      <nldd-spacer size="16"></nldd-spacer>\n'
        f'      <p class="meta">{len(canvas["boxes"])} elementen, '
        f'{len(canvas["edges"])} '
        f'getekende verbindingen · gegenereerd uit '
        f'<code>{html.escape(display_model_path(model))}</code></p>')
    return page_shell(name, body)


def render_index_html(model, entries) -> str:
    cards = []
    for name, filename, n_boxes, n_edges, thumbnail in entries:
        cards.append(
            f'        <a class="card-link" href="{filename}">'
            f'<nldd-card accessible-label="{html.escape(name)}">'
            f'<nldd-container padding="16">'
            f'<div class="thumb">{thumbnail}</div>'
            f'<nldd-spacer size="12"></nldd-spacer>'
            f'<nldd-title size="4"><h2>{html.escape(name)}</h2></nldd-title>'
            f'<p class="meta">{n_boxes} elementen · {n_edges} verbindingen</p>'
            f'</nldd-container>'
            f'</nldd-card></a>')
    body = (
        f'      <nldd-title size="2"><h1>{html.escape(model.name)}'
        f'</h1></nldd-title>\n'
        f'      <p class="doc">Views gegenereerd uit '
        f'<code>{html.escape(display_model_path(model))}</code>, '
        f'met de layout zoals die in het model is vastgelegd.</p>\n'
        f'      <nldd-spacer size="16"></nldd-spacer>\n'
        f'      <nldd-collection layout="grid" item-width="320px">\n'
        + "\n".join(cards) + "\n"
        '      </nldd-collection>')
    return page_shell(f"{model.name} · views", body)


def render_all_html(model, out_dir, links: dict | None = None) -> tuple[list, list]:
    """Render every view to HTML; returns (written, removed) path lists.

    links is the parsed links file ({source: {element name: target}}); a view
    picks up the section keyed by its own file stem."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written, produced, entries = [], set(), []

    index = model.id_index()
    stems = view_stems(model)
    for diagram in model.diagrams():
        name = diagram.get("name") or diagram.get("id")
        filename = stems[diagram.get("id")] + ".html"
        path = out / filename
        view_links = links_for(links or {}, stems[diagram.get("id")])
        if write_if_changed(path, render_view_html(model, diagram,
                                                   links=view_links)):
            written.append(path)
        produced.add(path.name)
        boxes = absolute_boxes(diagram, index)
        edges = diagram_edges(model, diagram, {b["id"]: b for b in boxes})
        entries.append((name, filename, len(boxes), len(edges),
                        view_thumbnail_svg(boxes)))

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
