# AI-assisted architecting

[![checks](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/actions/workflows/ci.yml/badge.svg)](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/actions/workflows/ci.yml)
[![licentie: EUPL-1.2](https://img.shields.io/badge/licentie-EUPL--1.2-blue.svg)](LICENSE)

Experiment van Bureau Architectuur Digitale Overheid: een ArchiMate-model in
het native Archi-formaat als bron van waarheid, bijgehouden met AI-assistentie
en deterministische tooling. Het modelbestand opent direct in Archi, zonder
import-stap, en de views zijn op GitHub zelf te bekijken.

## Het idee

`models/ado.archimate` is de bron. Er zijn twee gelijkwaardige manieren om
eraan te werken: via de `archi`-CLI (meestal aangestuurd door een AI-sessie
zoals Claude Code) of gewoon in de Archi-GUI. Beide routes komen samen in
dezelfde controles:

- `just validate` controleert de integriteit: unieke ids, kloppende
  verwijzingen van relaties en view-objecten, juiste folder-plaatsing, en
  property-keys tegen de conventielijst.
- `just normalize` laat headless Archi het bestand opnieuw serialiseren.
  Archi is daarmee de canonieke serializer, dus diffs blijven klein en
  reviewbaar, wie of wat er ook geschreven heeft.
- `just render` genereert uit elke view in het model een Mermaid-diagram
  (rendert op GitHub, in `views/`) en een NLDD-gestileerde HTML-pagina die de
  layout uit het model pixelgetrouw volgt (`views/html/`), inclusief de
  ArchiMate-notatie-iconen per elementtype, notes, groups en bendpoints.
  Daarnaast rendert het uit elke deckdefinitie in `decks/` een presentatie
  (`views/html/slides/`): een lineair verhaal als zelfstandige HTML-slides
  in Rijkshuisstijl, met views uit het model als diagrammen, afgewisseld
  met tekst- en bulletslides.

Pre-commit hooks dwingen validatie en verse renders af bij elke commit die
het model raakt. De afweging achter deze opzet, inclusief wat we inleveren
ten opzichte van de JSON-aanpak in het zusterexperiment, staat in
`adr/0001-archimate-als-bron.md`; het besluit om gegenereerde renders wel te
committen staat in `adr/0002-views-als-mermaid-in-git.md`, dat voor de
slidedecks in `adr/0003-slidedecks-als-toml-in-git.md`.

## Structuur

```
models/ado.archimate         Het model, de bron van waarheid
decks/                       Deckdefinities voor presentaties (TOML)
views/                       Gerenderde views als Mermaid (.md, rendert op GitHub)
views/html/                  Dezelfde views als NLDD-HTML, lokaal te bekijken
views/html/slides/           Gerenderde slidedecks (één HTML per deck)
docs/conventies.md           Types, property-keys en naamgeving
docs/spelregels.md           Rollen, workflow en de een-schrijver-afspraak
adr/                         Architectuurbeslissingen
tools/archi_tool/            De archi-CLI (Python, lxml; beheerd met uv)
tests/                       pytest-suite met een klein fixture-model
.claude/skills/              Procedures voor AI-sessies (archi-model, archi-view, archi-slides)
justfile                     Vaste taken
```

## Aan de slag

Nodig: [uv](https://docs.astral.sh/uv/), [just](https://just.systems/) en
[Archi](https://www.archimatetool.com/) voor normalisatie.

macOS:

```bash
brew install uv just
brew install --cask archi
```

Windows (PowerShell):

```powershell
winget install --id astral-sh.uv -e
winget install --id Casey.Just -e
winget install --id Archi.Archi -e
```

Linux: uv via `curl -LsSf https://astral.sh/uv/install.sh | sh`, just via je
packagemanager, Archi als tgz van
[archimatetool.com/download](https://www.archimatetool.com/download/).

Archi wordt automatisch gevonden op `/Applications/Archi.app` (macOS),
`C:\Program Files\Archi\Archi.exe` (Windows) en `/opt/Archi/Archi` (Linux);
een ander pad geef je op via de env var `ARCHI_APP`. Python en pre-commit
hoef je niet zelf te installeren: uv regelt de Python-versie en pre-commit
is een dev-dependency.

```bash
just setup       # eenmalig per clone: venv, dependencies en pre-commit hooks
just stats       # wat zit erin
just open        # model openen in Archi
just serve       # gerenderde HTML-views op http://localhost:8766
```

Sla `just setup` niet over: zonder de pre-commit hooks kun je committen
zonder validatie en met verouderde renders.

Alle vaste taken:

| Commando | Wat het doet |
|---|---|
| `just setup` | venv, dependencies en pre-commit hooks installeren |
| `just validate` | integriteitschecks (draait ook als pre-commit hook) |
| `just render` | views en decks renderen naar `views/` en `views/html/` (ook hook) |
| `just normalize` | canonieke serialisatie via headless Archi, duurt zo'n 15 s |
| `just stats` | telling per elementtype, relaties en views |
| `just test` | pytest-suite |
| `just open` | model openen in Archi |
| `just serve` | HTML-views serveren op http://localhost:8766 |

Wijzigen doe je met de CLI. Die valideert het model na elke mutatie en
weigert op te slaan zolang er fouten zijn. Elementen zijn aanspreekbaar op id
of op naam, zolang die uniek is:

```bash
uv run archi list --type Capability --property "Capability-niveau=gebied"
uv run archi show "Gegevensuitwisseling"
uv run archi tree
uv run archi add-element --type Capability --name "..." \
    --property "Capability-niveau=bouwblok" --property "Omschrijving=..."
uv run archi add-relation --type Aggregation \
    --source "Gegevensuitwisseling" --target "..." --name "bevat"
uv run archi set-property "Gegevensuitwisseling" "Omschrijving=..."
uv run archi rename "Oude naam" "Nieuwe naam"
uv run archi set-documentation "Gegevensuitwisseling" "..."
uv run archi remove "Gegevensuitwisseling" --cascade
uv run archi add-view --name "..." --layout cluster \
    --type Capability --relation Aggregation
uv run archi add-view --name "... in detail" --layout cluster \
    --root "Gegevensuitwisseling" --related
uv run archi slides --deck decks/ado.toml
uv run archi set-model-name "..."
uv run archi --help
```

## Werkwijze

Branch afsplitsen, wijzigen, `just validate`, `just normalize`, committen en
een PR openen. De pre-commit hook rendert de views mee; verandert er iets in
`views/`, dan faalt de commit een keer en stage je de verse renders erbij.
CI draait dezelfde checks (validatie, actuele renders, tests) op Ubuntu en
Windows, dus een omzeilde hook strandt alsnog op de PR. De
architect-eigenaar reviewt en merget.

De belangrijkste afspraak: een schrijver tegelijk op het modelbestand. Een
enkel XML-bestand merget slecht, dus parallelle branches met modelwijzigingen
zijn er niet. Tooling- en documentatie-PR's kunnen wel naast elkaar lopen.
Details en rollen staan in `docs/spelregels.md`; de modelconventies (welke
types, welke property-keys, Nederlandse naamgeving) in `docs/conventies.md`.

Werk je met Claude Code, dan wordt `CLAUDE.md` automatisch geladen en
triggeren de skills `archi-model` (modelwijzigingen doorvoeren), `archi-view`
(views genereren) en `archi-slides` (presentaties maken) zodra je erom
vraagt.

## Herkomst

Het seedmodel is de export van het ADO-niveau-1-model uit
[`ADO-architectuurmodel-experiment`](https://github.com/BureauArchitectuurDigitaleOverheid/ADO-architectuurmodel-experiment),
waar JSON de bron is en ArchiMate een exportformaat. Dit repo draait die
verhouding om: het Archi-bestand is de bron, en al het andere wordt eruit
gegenereerd.

## Licentie

[EUPL-1.2](LICENSE).
