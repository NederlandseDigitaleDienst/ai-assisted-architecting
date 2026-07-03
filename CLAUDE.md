# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Wat dit repo is

Experiment "AI-assisted architecting": een ArchiMate-model in native
Archi-formaat (`models/ado.archimate`) als bron van waarheid, direct te
openen in Archi en via de deterministische CLI in `tools/archi_tool` te
manipuleren. Er is geen conversielaag; de afweging staat in
`adr/0001-archimate-als-bron.md`, het besluit om gegenereerde renders te
committen in `adr/0002-views-als-mermaid-in-git.md`.

## Commando's

```bash
just setup            # eenmalig: uv sync + pre-commit install
just validate         # integriteitschecks (ook pre-commit hook)
just render           # views naar Mermaid (views/) en NLDD-HTML (views/html/), decks naar slides (views/html/slides/), ook pre-commit hook
just normalize        # canonieke serialisatie via headless Archi (~15 s)
just stats            # aantallen per type, relaties en views
just test             # pytest
just open             # model openen in Archi
just serve            # gerenderde HTML-views op http://localhost:8766

# Commando's met argumenten lopen via de CLI zelf:
uv run archi list|show|tree ...            # inspectie
uv run archi add-element|add-relation|set-property|rename|set-documentation|remove ...
uv run archi add-view --name ... --layout grid|cluster
uv run archi slides [--deck decks/<naam>.toml]
uv run archi set-model-name ...
```

Vuistregel: vaste taken via `just`, geparametriseerde commando's via
`uv run archi`. Elk commando accepteert `--model <pad>` voor een ander
bestand dan `models/ado.archimate`.

## Prerequisites: controleren en zo nodig installeren

Ga er niet vanuit dat de omgeving compleet is. Controleer bij het eerste
commando dat faalt (of proactief aan het begin van een sessie) en installeer
wat ontbreekt, zonder de gebruiker ernaartoe te sturen:

- `uv` ontbreekt (`command -v uv` / `where.exe uv`): macOS/Linux
  `curl -LsSf https://astral.sh/uv/install.sh | sh` of `brew install uv`;
  Windows `winget install --id astral-sh.uv -e` of
  `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
  uv regelt zelf een passende Python (>=3.11).
- `just` ontbreekt: macOS `brew install just`; Windows
  `winget install --id Casey.Just -e`; Linux via de packagemanager.
- Venv of dependencies ontbreken (`.venv/` bestaat niet, of `uv run archi`
  faalt op imports): `uv sync`.
- Pre-commit hooks ontbreken (`.git/hooks/pre-commit` bestaat niet of bevat
  geen pre-commit-aanroep): `uv run pre-commit install`. pre-commit zelf is
  een dev-dependency en komt mee met `uv sync`; er is geen globale
  installatie nodig.
- Archi ontbreekt (geen match in `ARCHI_CANDIDATES` uit
  `tools/archi_tool/normalize.py` en `ARCHI_APP` is niet gezet): macOS
  `brew install --cask archi`; Windows `winget install --id Archi.Archi -e`;
  Linux tgz van archimatetool.com. Of meld dat alleen `normalize` hierdoor
  niet kan; valideren, renderen en muteren werken zonder Archi.

`just setup` dekt de venv en de hooks in één keer, maar vereist dat uv en
just er al zijn. Alle installatiebronnen (URL's en winget-id's) zijn
geverifieerd op 2026-07-02.

## Testen

- Hele suite: `just test`
- Eén test: `uv run pytest tests/test_model.py::test_remove_cascade_cleans_views_and_relations`
- Tests werken op een kopie van `tests/fixtures/klein-model.archimate` via de
  `model`- en `model_path`-fixtures in `tests/conftest.py`. Nieuwe checks in
  `validate.py` horen een test te krijgen die het fixture-model gericht
  corrumpeert en de foutmelding asserteert.

## Harde regels

- **Bron van waarheid**: `models/ado.archimate`. AEF-exports, afbeeldingen en
  `.bak`-bestanden zijn afgeleid en gitignored. Uitzondering: `views/` bevat
  gegenereerde weergaven die wel gecommit worden (ADR 0002, voor slides
  ADR 0003); nooit handmatig bewerken, `just render` houdt ze synchroon.
  Deckdefinities in `decks/*.toml` zijn bron (met de hand te bewerken); de
  gerenderde slides in `views/html/slides/` zijn afgeleid en gecommit.
- **Nooit handmatig XML bewerken** in het modelbestand. Alle mutaties via de
  `archi`-CLI, die valideert automatisch en weigert opslaan bij fouten. Voor
  procedures: skills `archi-model`, `archi-view` en `archi-slides`.
- Ids (`id-<uuid4>`) zijn onveranderlijk; de tooling genereert nieuwe.
- Vóór elke commit die het model raakt: `just validate`, `just normalize` en
  `just render`. De pre-commit hooks dwingen validate, render en pytest af
  (ook bij tooling-wijzigingen); normalize niet (te traag voor een hook), dus
  die stap is discipline. CI (`.github/workflows/ci.yml`) draait dezelfde
  checks op Ubuntu en Windows en faalt als de gecommitte views niet synchroon
  zijn met het model.
- Nieuwe property-keys eerst vastleggen in `docs/conventies.md` §3; de
  validator waarschuwt op onbekende keys. Structurele beslissingen krijgen
  een ADR in `adr/`.
- **Eén schrijver tegelijk** op het modelbestand: geen parallelle branches
  met modelwijzigingen (spelregels §4; XML merget slecht).
- Wijzigingen via branch → commit → PR (`docs/spelregels.md`). Semantische
  Nederlandstalige commit-berichten.

## Architectuur van de tooling

`tools/archi_tool/` is een uv-project met entrypoint `archi` (pyproject):

- `model.py`: laden, muteren en opslaan met lxml. Het formaat: alleen het
  rootelement zit in de archimate-namespace, de rest is unqualified;
  concepten dragen `xsi:type="archimate:..."`; relatietypes eindigen op
  `Relationship` (Amerikaanse spelling); bounds van geneste view-objecten
  zijn relatief aan hun parent. `remove` ruimt bij cascade ook
  view-objecten, connections en `targetConnections`-attributen op.
- `validate.py`: integriteitschecks plus conventiecheck tegen
  `docs/conventies.md` (sectie "Property-keys", eventueel genummerd; telt
  alleen bullets die met een backticked key beginnen).
- `normalize.py`: load+save-roundtrip door de headless Archi CLI. Binary via
  env var `ARCHI_APP`, anders het eerste bestaande pad uit `ARCHI_CANDIDATES`
  (macOS, Windows machine- en user-scope, Linux).
- `views.py`: view-generatie met grid- of cluster-layout (geport uit het
  ADO-exportscript).
- `render.py`: views naar Mermaid-markdown, met `accTitle`/`accDescr` voor
  toegankelijkheid en het ArchiMate-laagkleurenpalet (`LAYER_PALETTE`).
- `render_html.py`: views naar NLDD-gestileerde HTML met de layout uit het
  model, inclusief de ArchiMate-notatie-iconen per elementtype
  (`ICON_GLYPHS`, geometrie geport uit de Archi-broncode), notes, groups,
  view-referenties en bendpoints. Niet gerenderd: SketchModel- en
  CanvasModel-views, DiagramModelImage en custom kleuren/fonts uit Archi.
  Let op: NLDD-primitives zijn zelf al `light-dark()`-paren, dus
  nooit dubbel wikkelen. Diagram-canvas is bewust altijd licht.
  `diagram_canvas()` en `DIAGRAM_CSS` worden gedeeld met de slide-renderer.
- `render_slides.py`: decks (`decks/*.toml`, stdlib-`tomllib`) naar
  zelfstandige HTML-presentaties in `views/html/slides/`: één lineair
  verhaal per deck, geen overzichts- of menumechanismen. Slidetypes:
  title, section, view, text, bullets, closing. Deterministisch: de datum
  op de titelslide wordt client-side ingevuld (`data-today`), geen
  timestamps of absolute paden in de output. View-slides tekenen het echte
  diagram (markerprefix `s<n>-` tegen dubbele SVG-ids, `ref_base="../"`
  voor view-referenties).
- `cli.py`: argparse-subcommands; mutaties slaan alleen op bij schone
  validatie.

Gegenereerde bestanden in `views/` dragen een markercommentaar (eerste
regel); alleen bestanden met die marker worden overschreven of opgeruimd.

Alles in dit repo is Nederlandstalig (modelinhoud, docs, commits); code en
comments zijn Engels.
