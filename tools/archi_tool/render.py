"""Render views from a .archimate model to Mermaid markdown.

Mermaid does its own auto-layout, so this renders the *content* of a view
(elements, nesting, drawn relations), not the pixel-exact Archi layout.
Nested diagram objects become subgraphs; connection line styles follow the
relation type. Output files carry a marker comment so stale files can be
cleaned up safely.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .model import FOLDER_BY_ELEMENT_TYPE, xsi_type

MARKER = "<!-- Gegenereerd door `archi render` — niet handmatig bewerken -->"


def display_model_path(model) -> str:
    """The model path as it should appear in generated output: relative to the
    working directory so renders stay byte-identical across machines, even
    when discovery resolved an absolute path via archi.toml."""
    path = Path(model.path)
    if not path.is_absolute():
        # already relative (the common case): keep it as written
        return path.as_posix()
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        # outside the working directory: the bare name keeps it deterministic
        return path.name

# (fill, stroke, text) per ArchiMate layer, matching Archi's own layer
# diagram conventions (Strategy amber, Motivation purple, Business lemon)
LAYER_PALETTE = {
    "strategy": ("#FAC75A", "#D4882A", "#633806"),
    "business": ("#FFF580", "#D4B830", "#5C4A00"),
    "application": ("#B4E2FA", "#4A9CC9", "#0D3D57"),
    "technology": ("#C9E7B7", "#7BAF5E", "#2E4A1E"),
    "motivation": ("#CECBF6", "#7F77DD", "#26215C"),
    "implementation_migration": ("#FBD5B5", "#D18A47", "#5C3305"),
    "other": ("#D3D1C7", "#888780", "#444441"),
}
LAYER_STYLES = {
    layer: f"fill:{fill},stroke:{stroke},color:{text}"
    for layer, (fill, stroke, text) in LAYER_PALETTE.items()
}

# ArchiMate-ish approximations: circle for containment (no diamond in
# Mermaid), dotted for the dashed ArchiMate lines (influence, realization).
CONTAINMENT_TYPES = {"AggregationRelationship", "CompositionRelationship"}
DOTTED_TYPES = {"InfluenceRelationship", "RealizationRelationship"}

EDGE_LEGEND = ("pijlstijlen: `--o` bevat (aggregatie/compositie), "
               "`-.->` gestippeld (beïnvloedt/realiseert), `-->` overig")


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "view"


def view_stems(model) -> dict:
    """Output file stem per view id, unique across the model.

    The stem is the slug of the view name. Names that slugify alike
    ("Overzicht" and "Overzicht!") would otherwise write to the same file, so
    every view in such a group gets a suffix from its id. The result never
    depends on model order: moving a view to another folder must not hand
    its file name to a different view, and an old link to the plain name
    should break loudly rather than silently open another view. A counter
    suffix ("-2") is avoided on purpose: it could collide with a view that
    is really called "Overzicht 2".
    """
    bases = {d.get("id"): slugify(d.get("name") or d.get("id"))
             for d in model.diagrams()}
    base_counts = Counter(bases.values())
    unique = {b for b, n in base_counts.items() if n == 1}
    id_slugs = {v: slugify(v.removeprefix("id-")) for v in bases}
    short = {v: f"{b}-{id_slugs[v][:8]}"
             for v, b in bases.items() if base_counts[b] > 1}
    short_counts = Counter(short.values())
    stems = {}
    for view_id, base in bases.items():
        if base in unique:
            stems[view_id] = base
        elif short_counts[short[view_id]] == 1 and short[view_id] not in unique:
            stems[view_id] = short[view_id]
        else:
            # ids are unique, so the full id settles any remaining clash
            stems[view_id] = f"{base}-{id_slugs[view_id]}"
    return stems


def is_descendant(node, ancestor) -> bool:
    """True when ancestor contains node (via the lxml parent chain)."""
    parent = node.getparent()
    while parent is not None:
        if parent is ancestor:
            return True
        parent = parent.getparent()
    return False


def escape_label(name: str) -> str:
    return (name or "(naamloos)").replace('"', "#quot;")


def edge_syntax(rel) -> str:
    rel_type = xsi_type(rel) if rel is not None else ""
    label = rel.get("name") if rel is not None else None
    if rel_type in CONTAINMENT_TYPES:
        return "--o"  # containment label (bevat) would only add noise
    if rel_type in DOTTED_TYPES:
        return f'-.->|"{escape_label(label)}"|' if label else "-.->"
    return f'-->|"{escape_label(label)}"|' if label else "-->"


def clean_acc_text(text: str) -> str:
    """Single-line text for accTitle/accDescr (no newlines or braces)."""
    return " ".join(text.replace("{", "(").replace("}", ")").split())


def render_view(model, diagram) -> str:
    index = model.id_index()
    lines = ["flowchart TD"]
    # accessible name and description, like regelrecht does for its docs
    lines.append(f"  accTitle: {clean_acc_text(diagram.get('name') or 'View')}")
    documentation = model.documentation(diagram)
    if documentation:
        lines.append(f"  accDescr: {clean_acc_text(documentation)}")
    mermaid_id_by_object = {}
    layer_members = {}
    counter = 0

    def register(obj, element):
        nonlocal counter
        counter += 1
        mermaid_id = f"n{counter}"
        mermaid_id_by_object[obj.get("id")] = mermaid_id
        layer = FOLDER_BY_ELEMENT_TYPE.get(xsi_type(element))
        if layer:
            layer_members.setdefault(layer, []).append(mermaid_id)
        return mermaid_id

    def walk(objects, depth):
        indent = "  " * depth
        for obj in objects:
            element = index.get(obj.get("archimateElement") or "")
            if element is None:
                continue  # notes/groups without a model element
            mermaid_id = register(obj, element)
            label = escape_label(element.get("name"))
            children = obj.findall("child")
            if children:
                lines.append(f'{indent}subgraph {mermaid_id}["{label}"]')
                walk(children, depth + 1)
                lines.append(f"{indent}end")
            else:
                lines.append(f'{indent}{mermaid_id}["{label}"]')

    walk(diagram.findall("child"), 1)

    for conn in diagram.iter("sourceConnection"):
        source_id = mermaid_id_by_object.get(conn.get("source"))
        target_id = mermaid_id_by_object.get(conn.get("target"))
        if not source_id or not target_id:
            continue
        source_obj = index.get(conn.get("source"))
        target_obj = index.get(conn.get("target"))
        rel = index.get(conn.get("archimateRelationship") or "")
        # nesting already expresses containment; skip the redundant arrow
        if (rel is not None and xsi_type(rel) in CONTAINMENT_TYPES
                and is_descendant(target_obj, source_obj)):
            continue
        lines.append(f"  {source_id} {edge_syntax(rel)} {target_id}")

    for layer, members in sorted(layer_members.items()):
        lines.append(f"  classDef {layer} {LAYER_STYLES[layer]}")
        lines.append(f"  class {','.join(members)} {layer}")

    parts = [MARKER, "", f"# {diagram.get('name') or '(naamloze view)'}", ""]
    documentation = model.documentation(diagram)
    if documentation:
        parts += [documentation, ""]
    parts += ["```mermaid", *lines, "```", "",
              f"*Gegenereerd uit `{display_model_path(model)}` — "
              f"{EDGE_LEGEND}.*", ""]
    return "\n".join(parts)


def render_index(model, entries) -> str:
    rows = [MARKER, "", "# Views", "",
            f"Gerenderde views uit `{display_model_path(model)}`. "
            "Deze bestanden worden gegenereerd door `archi render`; "
            "bewerk ze niet handmatig.", ""]
    for name, filename in entries:
        rows.append(f"- [{name}]({filename})")
    rows.append("")
    return "\n".join(rows)


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    # newline="\n" keeps LF on every platform (no CRLF churn on Windows)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def render_all(model, out_dir) -> tuple[list, list]:
    """Render every view; returns (written, removed) path lists."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written, produced, entries = [], set(), []

    stems = view_stems(model)
    for diagram in model.diagrams():
        name = diagram.get("name") or diagram.get("id")
        filename = stems[diagram.get("id")] + ".md"
        path = out / filename
        if write_if_changed(path, render_view(model, diagram)):
            written.append(path)
        produced.add(path.name)
        entries.append((name, filename))

    index_path = out / "README.md"
    if write_if_changed(index_path, render_index(model, entries)):
        written.append(index_path)
    produced.add(index_path.name)

    removed = []
    for stale in out.glob("*.md"):
        if stale.name in produced:
            continue
        first_line = stale.read_text(encoding="utf-8").split("\n", 1)[0]
        if first_line.strip() == MARKER:
            stale.unlink()
            removed.append(stale)
    return written, removed
