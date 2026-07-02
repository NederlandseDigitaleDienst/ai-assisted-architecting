"""CLI for deterministic manipulation of native .archimate models.

Usage: archi <subcommand> [--model PATH] ...
Mutating subcommands validate the model in memory and refuse to save when
validation errors are found. Run `archi normalize` before committing so the
serialization stays Archi-canonical.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .model import ArchiModel, ModelError, is_element, xsi_type
from .normalize import normalize
from .render import render_all
from .validate import validate
from .views import add_view

DEFAULT_MODEL = "models/ado.archimate"
DEFAULT_CONVENTIONS = "docs/conventies.md"


def parse_properties(pairs):
    properties = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep:
            raise ModelError(f"Property moet key=value zijn, kreeg: '{pair}'")
        properties[key] = value
    return properties


def conventions_path(model_path):
    candidate = Path(model_path).resolve().parent.parent / DEFAULT_CONVENTIONS
    return candidate if candidate.exists() else None


def report_validation(model, model_path) -> bool:
    """Print validation results; return True when the model is sound."""
    errors, warnings = validate(model, conventions_path(model_path))
    for warning in warnings:
        print(f"WAARSCHUWING: {warning}")
    for error in errors:
        print(f"FOUT: {error}")
    return not errors


def save_validated(model, args) -> int:
    if not report_validation(model, args.model):
        print("Niet opgeslagen: los eerst de fouten hierboven op.")
        return 1
    model.save()
    return 0


def describe(model, node) -> str:
    kind = xsi_type(node)
    name = node.get("name") or "(naamloos)"
    return f"{node.get('id')}  [{kind}]  {name}"


# --- subcommand implementations ---------------------------------------------

def cmd_stats(model, args):
    print(f"Model: {model.name}")
    counts = Counter(xsi_type(e) for e in model.elements())
    print(f"Elementen: {sum(counts.values())}")
    for kind, count in counts.most_common():
        print(f"  {kind}: {count}")
    rel_counts = Counter(xsi_type(r) for r in model.relationships())
    print(f"Relaties: {sum(rel_counts.values())}")
    for kind, count in rel_counts.most_common():
        print(f"  {kind}: {count}")
    diagrams = model.diagrams()
    print(f"Views: {len(diagrams)}")
    for d in diagrams:
        print(f"  {d.get('name')}")
    return 0


def cmd_list(model, args):
    wanted = parse_properties(args.property)
    for el in model.elements():
        if args.type and xsi_type(el) != args.type:
            continue
        props = model.properties(el)
        if any(props.get(k) != v for k, v in wanted.items()):
            continue
        print(describe(model, el))
    return 0


def cmd_show(model, args):
    node = model.resolve(args.ref)
    print(describe(model, node))
    documentation = model.documentation(node)
    if documentation:
        print(f"  documentatie: {documentation}")
    for key, value in model.properties(node).items():
        print(f"  {key} = {value}")
    node_id = node.get("id")
    index = model.id_index()
    for rel in model.relations_of(node_id):
        other_id = (rel.get("target") if rel.get("source") == node_id
                    else rel.get("source"))
        other = index.get(other_id)
        direction = "->" if rel.get("source") == node_id else "<-"
        other_name = other.get("name") if other is not None else other_id
        print(f"  {direction} {xsi_type(rel)} {direction} {other_name}")
    return 0


def cmd_tree(model, args):
    for folder in model.root.findall("folder"):
        children = folder.findall("element")
        print(f"{folder.get('name')} ({folder.get('type')}): "
              f"{len(children)} item(s)")
        for el in children:
            if is_element(el) or el.get("name"):
                print(f"  {describe(model, el)}")
    return 0


def cmd_validate(model, args):
    if report_validation(model, args.model):
        print("OK: model is consistent.")
        return 0
    return 1


def cmd_add_element(model, args):
    el = model.add_element(args.type, args.name, folder_type=args.folder,
                           properties=parse_properties(args.property),
                           documentation=args.documentation)
    status = save_validated(model, args)
    if status == 0:
        print(f"Toegevoegd: {describe(model, el)}")
    return status


def cmd_add_relation(model, args):
    rel = model.add_relation(args.type, args.source, args.target,
                             name=args.name)
    status = save_validated(model, args)
    if status == 0:
        print(f"Toegevoegd: {rel.get('id')} [{xsi_type(rel)}] "
              f"{args.source} -> {args.target}")
    return status


def cmd_set_property(model, args):
    key, sep, value = args.pair.partition("=")
    if not sep:
        raise ModelError(f"Property moet key=value zijn, kreeg: '{args.pair}'")
    model.set_property(args.ref, key, value)
    return save_validated(model, args)


def cmd_rename(model, args):
    model.rename(args.ref, args.name)
    return save_validated(model, args)


def cmd_set_documentation(model, args):
    model.set_documentation(args.ref, args.text)
    return save_validated(model, args)


def cmd_remove(model, args):
    model.remove(args.ref, cascade=args.cascade)
    status = save_validated(model, args)
    if status == 0:
        print(f"Verwijderd: {args.ref}")
    return status


def cmd_set_model_name(model, args):
    model.set_model_name(args.name)
    return save_validated(model, args)


def cmd_add_view(model, args):
    diagram = add_view(model, args.name, layout=args.layout,
                       element_types=set(args.type) if args.type else None,
                       relation_types=(set(args.relation)
                                       if args.relation else None),
                       prop=args.property)
    status = save_validated(model, args)
    if status == 0:
        objects = len(diagram.findall("child"))
        connections = len(list(diagram.iter("sourceConnection")))
        print(f"View '{args.name}' aangemaakt: {objects} objecten, "
              f"{connections} verbindingen")
    return status


def cmd_normalize(model, args):
    normalize(args.model)
    print(f"Genormaliseerd via Archi: {args.model}")
    return 0


def cmd_render(model, args):
    written, removed = render_all(model, args.out)
    for path in written:
        print(f"Geschreven: {path}")
    for path in removed:
        print(f"Verwijderd (view bestaat niet meer): {path}")
    if not written and not removed:
        print("Views zijn al actueel.")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="archi", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"pad naar het .archimate-bestand "
                             f"(default: {DEFAULT_MODEL})")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats", help="aantallen per type, relaties en views")

    p = sub.add_parser("list", help="elementen tonen, optioneel gefilterd")
    p.add_argument("--type", help="filter op elementtype (bv. Capability)")
    p.add_argument("--property", action="append",
                   help="filter op property, key=value (herhaalbaar)")

    p = sub.add_parser("show", help="één element met properties en relaties")
    p.add_argument("ref", help="id of (unieke) naam")

    sub.add_parser("tree", help="folderstructuur met inhoud")
    sub.add_parser("validate", help="integriteitschecks draaien")
    sub.add_parser("normalize",
                   help="serialisatie canoniek maken via de Archi CLI")

    p = sub.add_parser("add-element", help="element toevoegen")
    p.add_argument("--type", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--folder", help="folder-type; default volgt uit het type")
    p.add_argument("--property", action="append", help="key=value (herhaalbaar)")
    p.add_argument("--documentation")

    p = sub.add_parser("add-relation", help="relatie toevoegen")
    p.add_argument("--type", required=True,
                   help="bv. Aggregation of AggregationRelationship")
    p.add_argument("--source", required=True, help="id of unieke naam")
    p.add_argument("--target", required=True, help="id of unieke naam")
    p.add_argument("--name", help="NL-label op de relatie")

    p = sub.add_parser("set-property", help="property zetten of bijwerken")
    p.add_argument("ref")
    p.add_argument("pair", help="key=value")

    p = sub.add_parser("rename", help="element of relatie hernoemen")
    p.add_argument("ref")
    p.add_argument("name")

    p = sub.add_parser("set-documentation", help="documentatie zetten")
    p.add_argument("ref")
    p.add_argument("text")

    p = sub.add_parser("remove", help="element of relatie verwijderen")
    p.add_argument("ref")
    p.add_argument("--cascade", action="store_true",
                   help="verwijder ook relaties en view-objecten die ernaar "
                        "verwijzen")

    p = sub.add_parser("set-model-name", help="modelnaam wijzigen")
    p.add_argument("name")

    p = sub.add_parser("render",
                       help="views renderen naar Mermaid-markdown (views/)")
    p.add_argument("--out", default="views",
                   help="doelmap voor de markdown-bestanden (default: views)")

    p = sub.add_parser("add-view", help="view genereren met berekende layout")
    p.add_argument("--name", required=True)
    p.add_argument("--layout", choices=["grid", "cluster"], default="grid")
    p.add_argument("--type", action="append",
                   help="elementtype in de selectie (herhaalbaar)")
    p.add_argument("--relation", action="append",
                   help="relatietype in de selectie (herhaalbaar)")
    p.add_argument("--property", help="selectiefilter, key=value")

    return parser


COMMANDS = {
    "stats": cmd_stats,
    "list": cmd_list,
    "show": cmd_show,
    "tree": cmd_tree,
    "validate": cmd_validate,
    "normalize": cmd_normalize,
    "add-element": cmd_add_element,
    "add-relation": cmd_add_relation,
    "set-property": cmd_set_property,
    "rename": cmd_rename,
    "set-documentation": cmd_set_documentation,
    "remove": cmd_remove,
    "set-model-name": cmd_set_model_name,
    "add-view": cmd_add_view,
    "render": cmd_render,
}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        model = ArchiModel(args.model)
        return COMMANDS[args.command](model, args)
    except ModelError as exc:
        print(f"FOUT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
