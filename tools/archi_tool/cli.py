"""CLI for deterministic manipulation of native .archimate models.

Usage: archi <subcommand> [--model PATH] ...
Mutating subcommands validate the model in memory and refuse to save when
validation errors are found. Run `archi normalize` before committing so the
serialization stays Archi-canonical.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import typer
from lxml import etree

from .discovery import discover_conventions, discover_links, discover_model
from .links import check_link_files, load_links
from .model import ArchiModel, ModelError, is_element, xsi_type
from .normalize import normalize
from .render import render_all, slugify, write_if_changed
from .render_html import render_all_html
from .render_slides import load_deck, render_all_slides, render_deck_html
from .validate import validate
from .views import add_view


def parse_properties(pairs):
    properties = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep:
            raise ModelError(f"Property moet key=value zijn, kreeg: '{pair}'")
        properties[key] = value
    return properties


def report_validation(model, model_path) -> bool:
    """Print validation results; return True when the model is sound."""
    # anchor conventions discovery at the model, not the working directory, so
    # validating a model from another project uses that project's conventions
    allowed_keys, _ = discover_conventions(
        model_path, start=Path(model_path).resolve().parent)
    # validation runs after every mutation: a broken links file must not
    # block modelling (ADR 0010), so here it degrades to a warning; render
    # and slides, which actually use the links, still fail on it
    try:
        links = load_links(discover_links(model_path))
    except ModelError as exc:
        print(f"WAARSCHUWING: links-bestand genegeerd: {exc}")
        links = {}
    errors, warnings = validate(model, allowed_keys=allowed_keys, links=links)
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
    def walk(folder, depth):
        children = folder.findall("element")
        indent = "  " * depth
        folder_type = folder.get("type")
        label = (f"{folder.get('name')} ({folder_type})" if folder_type
                 else folder.get("name"))
        print(f"{indent}{label}: {len(children)} item(s)")
        for el in children:
            if is_element(el) or el.get("name"):
                print(f"{indent}  {describe(model, el)}")
        for sub in folder.findall("folder"):
            walk(sub, depth + 1)

    for folder in model.root.findall("folder"):
        walk(folder, 0)
    return 0


def cmd_validate(model, args):
    if report_validation(model, args.model):
        print("OK: het model is consistent.")
        return 0
    return 1


def cmd_add_element(model, args):
    el = model.add_element(args.type, args.name, folder_type=args.folder,
                           properties=parse_properties(args.property),
                           documentation=args.documentation,
                           subfolder=args.subfolder,
                           create_subfolder=args.create_subfolder)
    status = save_validated(model, args)
    if status == 0:
        print(f"Toegevoegd: {describe(model, el)}")
    return status


def cmd_add_relation(model, args):
    rel = model.add_relation(args.type, args.source, args.target,
                             name=args.name, subfolder=args.subfolder,
                             create_subfolder=args.create_subfolder)
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
    status = save_validated(model, args)
    if status == 0:
        print(f"Property gezet op '{args.ref}': {key} = {value}")
    return status


def cmd_move(model, args):
    target = model.move(args.ref, args.subfolder,
                        create_subfolder=args.create_subfolder)
    status = save_validated(model, args)
    if status == 0:
        print(f"Verplaatst: '{args.ref}' naar folder '{target.get('name')}'")
    return status


def cmd_remove_property(model, args):
    model.remove_property(args.ref, args.key)
    status = save_validated(model, args)
    if status == 0:
        print(f"Property verwijderd van '{args.ref}': {args.key}")
    return status


def cmd_rename(model, args):
    model.rename(args.ref, args.name)
    status = save_validated(model, args)
    if status == 0:
        print(f"Hernoemd: '{args.ref}' heet nu '{args.name}'")
    return status


def cmd_set_documentation(model, args):
    model.set_documentation(args.ref, args.text)
    status = save_validated(model, args)
    if status == 0:
        print(f"Documentatie gezet op '{args.ref}'")
    return status


def cmd_remove(model, args):
    model.remove(args.ref, cascade=args.cascade)
    status = save_validated(model, args)
    if status == 0:
        print(f"Verwijderd: {args.ref}")
    return status


def cmd_set_model_name(model, args):
    model.set_model_name(args.name)
    status = save_validated(model, args)
    if status == 0:
        print(f"Modelnaam gewijzigd naar '{args.name}'")
    return status


def cmd_add_view(model, args):
    extra = [model.resolve(ref) for ref in (args.element or [])]
    for node in extra:
        if not is_element(node):
            raise ModelError(
                f"'{node.get('name') or node.get('id')}' is geen element")
    diagram = add_view(model, args.name, layout=args.layout,
                       element_types=set(args.type) if args.type else None,
                       relation_types=(set(args.relation)
                                       if args.relation else None),
                       prop=args.property, root=args.root,
                       related=args.related,
                       extra_elements=extra or None)
    status = save_validated(model, args)
    if status == 0:
        objects = len(diagram.findall("child"))
        connections = len(list(diagram.iter("sourceConnection")))
        print(f"View '{args.name}' aangemaakt: {objects} objecten, "
              f"{connections} verbindingen")
    return status


def cmd_normalize(model, args):
    normalize(args.model, download=not args.no_download)
    print(f"Genormaliseerd via Archi: {args.model}")
    return 0


def cmd_setup(model, args):
    from .engine import download_engine, find_or_none
    existing = find_or_none()
    if existing:
        print(f"Archi al beschikbaar: {existing}")
        return 0
    binary = download_engine()
    print(f"Archi-engine klaar: {binary}")
    return 0


def cmd_render(model, args):
    links = load_links(discover_links(args.model))
    written, removed = render_all(model, args.out)
    html_dir = Path(args.out) / "html"
    html_written, html_removed = render_all_html(model, html_dir, links=links)
    deck_written, deck_removed = render_all_slides(
        model, Path(args.decks), html_dir / "slides", links=links)
    for path in written + html_written + deck_written:
        print(f"Geschreven: {path}")
    for path in removed + html_removed:
        print(f"Verwijderd (view bestaat niet meer): {path}")
    for path in deck_removed:
        print(f"Verwijderd (deck bestaat niet meer): {path}")
    if not (written or removed or html_written or html_removed
            or deck_written or deck_removed):
        print("Views zijn al actueel.")
    view_slugs = {slugify(d.get("name") or d.get("id"))
                  for d in model.diagrams()}
    for warning in check_link_files(links, args.out, html_dir, view_slugs):
        print(f"WAARSCHUWING: {warning}")
    return 0


def cmd_slides(model, args):
    links = load_links(discover_links(args.model))
    if args.deck:
        written = []
        for deck_path in args.deck:
            deck = load_deck(Path(deck_path), model)
            path = Path(args.out) / f"{deck['slug']}.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            if write_if_changed(path, render_deck_html(model, deck,
                                                       links=links)):
                written.append(path)
        removed = []
    else:
        written, removed = render_all_slides(
            model, Path(args.decks), Path(args.out), links=links)
    for path in written:
        print(f"Geschreven: {path}")
    for path in removed:
        print(f"Verwijderd (deck bestaat niet meer): {path}")
    if not (written or removed):
        print("Slides zijn al actueel.")
    return 0


# --- Typer app --------------------------------------------------------------
#
# Typer owns argument parsing and help; the cmd_* functions above own the
# behaviour. Each command is a thin typed wrapper that packs its parameters
# into a namespace (so the cmd_* signatures stay untouched) and hands them to
# _run, which centralises model discovery, loading and Dutch error handling.

HELP = """CLI voor deterministische bewerking van native .archimate-modellen.

Muterende subcommando's valideren het model in het geheugen en weigeren op te
slaan zolang er fouten zijn. Draai `archi normalize` vóór het committen, zodat
de serialisatie Archi-canoniek blijft.
"""

app = typer.Typer(
    help=HELP, no_args_is_help=True, add_completion=True,
    context_settings={"help_option_names": ["-h", "--help"]})

# the global --model, shared by every command through the app callback
_state = SimpleNamespace(model=None)

ModelOption = typer.Option(
    None, "--model",
    help="pad naar het .archimate-bestand; standaard gevonden via archi.toml "
         "of het enige .archimate-bestand in de huidige map")


@app.callback()
def _main(model: Optional[str] = ModelOption):
    _state.model = model


def _run(command_fn, *, load_model=True, need_model=True, **fields) -> None:
    """Discover the model, run a cmd_* function, translate errors, set exit.

    ``load_model=False`` is for normalize, which must not let lxml parse the
    file first (Archi is the canonical serializer and may load what lxml
    refuses). ``need_model=False`` is for commands that touch no model at all,
    such as setup. Raises typer.Exit with the command's status code.
    """
    args = SimpleNamespace(model=None, **fields)
    try:
        if need_model:
            args.model = discover_model(_state.model)
        model = ArchiModel(args.model) if (need_model and load_model) else None
        status = command_fn(model, args)
    except ModelError as exc:
        typer.echo(f"FOUT: {exc}", err=True)
        raise typer.Exit(1) from None
    except (etree.XMLSyntaxError, OSError) as exc:
        typer.echo(f"FOUT: kan {args.model} niet lezen: {exc}", err=True)
        raise typer.Exit(1) from None
    raise typer.Exit(status)


# Repeated options declared once; Typer reads the default value + help here.
PropertyFilter = typer.Option(
    None, "--property", help="filter op property, key=value (herhaalbaar)")


@app.command(help="aantallen per type, relaties en views")
def stats():
    _run(cmd_stats)


@app.command("list", help="elementen tonen, optioneel gefilterd")
def list_elements(
    type: Optional[str] = typer.Option(
        None, help="filter op elementtype (bv. Capability)"),
    property: Optional[list[str]] = PropertyFilter,
):
    _run(cmd_list, type=type, property=property)


@app.command(help="één element met properties en relaties")
def show(ref: str = typer.Argument(help="id of (unieke) naam")):
    _run(cmd_show, ref=ref)


@app.command(help="folderstructuur met inhoud")
def tree():
    _run(cmd_tree)


@app.command("validate", help="integriteitschecks draaien")
def validate_command():
    _run(cmd_validate)


@app.command("normalize", help="serialisatie canoniek maken via de Archi CLI")
def normalize_command(
    no_download: bool = typer.Option(
        False, "--no-download",
        help="haal de Archi-engine niet automatisch op; faal als hij "
             "ontbreekt (voor CI en luchtdichte omgevingen)"),
):
    _run(cmd_normalize, load_model=False, no_download=no_download)


@app.command("setup", help="de Archi-engine ophalen naar de lokale cache")
def setup_command():
    _run(cmd_setup, need_model=False)


@app.command("add-element", help="element toevoegen")
def add_element(
    type: str = typer.Option(..., help="elementtype (bv. Capability)"),
    name: str = typer.Option(..., help="naam van het element"),
    folder: Optional[str] = typer.Option(
        None, help="folder-type; default volgt uit het type"),
    property: Optional[list[str]] = typer.Option(
        None, "--property", help="key=value (herhaalbaar)"),
    documentation: Optional[str] = typer.Option(None),
    subfolder: Optional[str] = typer.Option(
        None, help="submap binnen de laagfolder, geneste mappen met '/'"),
    create_subfolder: bool = typer.Option(
        False, "--create-subfolder",
        help="ontbrekende submap aanmaken (anders: fout)"),
):
    _run(cmd_add_element, type=type, name=name, folder=folder,
         property=property, documentation=documentation,
         subfolder=subfolder, create_subfolder=create_subfolder)


@app.command("add-relation", help="relatie toevoegen")
def add_relation(
    type: str = typer.Option(
        ..., help="bv. Aggregation of AggregationRelationship"),
    source: str = typer.Option(..., help="id of unieke naam"),
    target: str = typer.Option(..., help="id of unieke naam"),
    name: Optional[str] = typer.Option(None, help="NL-label op de relatie"),
    subfolder: Optional[str] = typer.Option(
        None, help="submap binnen Relations, geneste mappen met '/'"),
    create_subfolder: bool = typer.Option(
        False, "--create-subfolder",
        help="ontbrekende submap aanmaken (anders: fout)"),
):
    _run(cmd_add_relation, type=type, source=source,
         target=target, name=name, subfolder=subfolder,
         create_subfolder=create_subfolder)


@app.command(help="element, relatie of view naar een submap verplaatsen")
def move(
    ref: str = typer.Argument(help="id of (unieke) naam"),
    subfolder: str = typer.Option(
        ..., help="submap binnen de huidige laagfolder, geneste mappen met "
                  "'/'; leeg ('') = terug naar de laagfolder zelf"),
    create_subfolder: bool = typer.Option(
        False, "--create-subfolder",
        help="ontbrekende submap aanmaken (anders: fout)"),
):
    _run(cmd_move, ref=ref, subfolder=subfolder,
         create_subfolder=create_subfolder)


@app.command("set-property", help="property zetten of bijwerken")
def set_property(
    ref: str = typer.Argument(help="id of (unieke) naam"),
    pair: str = typer.Argument(help="key=value"),
):
    _run(cmd_set_property, ref=ref, pair=pair)


@app.command("remove-property", help="property verwijderen")
def remove_property(
    ref: str = typer.Argument(help="id of (unieke) naam"),
    key: str = typer.Argument(help="property-key"),
):
    _run(cmd_remove_property, ref=ref, key=key)


@app.command(help="element of relatie hernoemen")
def rename(
    ref: str = typer.Argument(help="id of (unieke) naam"),
    name: str = typer.Argument(help="nieuwe naam"),
):
    _run(cmd_rename, ref=ref, name=name)


@app.command("set-documentation", help="documentatie zetten")
def set_documentation(
    ref: str = typer.Argument(help="id of (unieke) naam"),
    text: str = typer.Argument(help="documentatietekst"),
):
    _run(cmd_set_documentation, ref=ref, text=text)


@app.command(help="element of relatie verwijderen")
def remove(
    ref: str = typer.Argument(help="id of (unieke) naam"),
    cascade: bool = typer.Option(
        False, help="verwijder ook relaties en view-objecten die ernaar "
                    "verwijzen"),
):
    _run(cmd_remove, ref=ref, cascade=cascade)


@app.command("set-model-name", help="modelnaam wijzigen")
def set_model_name(name: str = typer.Argument(help="nieuwe modelnaam")):
    _run(cmd_set_model_name, name=name)


@app.command(help="views renderen naar Mermaid, NLDD-HTML en slidedecks")
def render(
    out: str = typer.Option(
        "views", help="doelmap voor de markdown-bestanden (default: views)"),
    decks: str = typer.Option(
        "decks", help="map met deckdefinities in TOML (default: decks)"),
):
    _run(cmd_render, out=out, decks=decks)


@app.command(help="slidedecks renderen naar zelfstandige HTML")
def slides(
    deck: Optional[list[str]] = typer.Option(
        None, "--deck", help="specifiek deckbestand (.toml); herhaalbaar; "
                             "default: alle decks in de decks-map"),
    decks: str = typer.Option(
        "decks", help="map met deckdefinities in TOML (default: decks)"),
    out: str = typer.Option(
        "views/html/slides", help="doelmap voor de HTML-bestanden"),
):
    _run(cmd_slides, deck=deck, decks=decks, out=out)


@app.command("add-view", help="view genereren met berekende layout")
def add_view_command(
    name: str = typer.Option(..., help="naam van de nieuwe view"),
    layout: str = typer.Option("grid", help="grid of cluster"),
    type: Optional[list[str]] = typer.Option(
        None, help="elementtype in de selectie (herhaalbaar)"),
    relation: Optional[list[str]] = typer.Option(
        None, help="relatietype in de selectie (herhaalbaar)"),
    property: Optional[str] = typer.Option(
        None, "--property", help="selectiefilter, key=value"),
    root: Optional[str] = typer.Option(
        None, help="element (id of naam): dit element plus alles wat het "
                   "aggregeert of composeert"),
    related: bool = typer.Option(
        False, help="voeg ook direct gerelateerde elementen toe (één stap, "
                    "alleen samen met --root zinvol)"),
    element: Optional[list[str]] = typer.Option(
        None, "--element", help="element (id of unieke naam) toevoegen aan de "
                                "selectie (herhaalbaar)"),
):
    if layout not in ("grid", "cluster"):
        typer.echo("FOUT: --layout moet grid of cluster zijn", err=True)
        raise typer.Exit(1)
    _run(cmd_add_view, name=name, layout=layout, type=type,
         relation=relation, property=property, root=root, related=related,
         element=element)


def main(argv=None) -> int:
    """Entry point. Returns an exit code so tests can call it directly.

    With standalone_mode=False, Typer returns the command's exit code (from
    typer.Exit) instead of calling sys.exit, and lets usage errors surface as
    Click exceptions. We translate both into an int so `sys.exit(main())` and
    direct test calls behave identically.
    """
    # Typer vendors Click; there is no top-level `click` module to import.
    from typer._click.exceptions import ClickException

    try:
        result = app(args=argv, standalone_mode=False)
    except ClickException as exc:  # e.g. missing/unknown option
        exc.show()
        return exc.exit_code
    except typer.Abort:
        typer.echo("Afgebroken.", err=True)
        return 1
    return int(result or 0)


if __name__ == "__main__":
    sys.exit(main())
