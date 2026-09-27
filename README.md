# AI-assisted architecting

[![checks](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/actions/workflows/ci.yml/badge.svg)](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/actions/workflows/ci.yml)
[![licentie: EUPL-1.2](https://img.shields.io/badge/licentie-EUPL--1.2-blue.svg)](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/archi-cli.svg)](https://pypi.org/project/archi-cli/)

Een manier van architecteren waarbij een ArchiMate-model in het native
Archi-formaat de bron van waarheid is, en je het met AI-assistentie bijhoudt in
plaats van met de hand door de GUI te klikken. Deze repo levert de twee dingen
die daarvoor nodig zijn:

- **`archi-cli`**: een deterministische command line tool die een
  `.archimate`-model inspecteert, muteert, valideert en rendert, en weigert een
  kapot model op te slaan. Op PyPI, werkt op elk model.
- **De skills** (`archi-model`, `archi-view`, `archi-slides`): de werkwijze
  die een AI-sessie zoals Claude Code volgt om via de CLI aan het model te
  werken. Te installeren als Claude Code plugin.

Het model zelf hoort niet hier: dat woont in een eigen repo en gebruikt
`archi-cli` als tool. Het ADO-model waarvoor dit ontstond is daar het
voorbeeld.

## De CLI

```bash
uv tool install archi-cli
archi --help
```

Dat zet het commando `archi` op je `$PATH`. Het model wordt gevonden via
`--model <pad>` (vóór het subcommando), via een `archi.toml` in de map
(`[tool.archi] model = "..."`), of als het enige `.archimate`-bestand in de
werkmap.

```bash
archi stats                                    # tellingen per type
archi list --type Capability                   # elementen, gefilterd
archi show "<elementnaam of id>"               # één element met relaties
archi tree                                     # folderstructuur

archi add-element --type Capability --name "..." --documentation "..."
archi add-relation --type Aggregation --source "..." --target "..." --name "bevat"
archi set-property <ref> "<key>=<waarde>"      # property zetten of bijwerken
archi remove-property <ref> "<key>"            # property verwijderen
archi set-documentation <ref> "..."            # Archi's documentatieveld
archi add-element ... --subfolder "Gebied X"    # in een submap van de laag
archi move <ref> --subfolder "Gebied X"        # naar een submap verplaatsen
archi rename <ref> "Nieuwe naam"
archi remove <ref> --cascade

archi add-view --name "..." --layout cluster --type Capability --relation Aggregation
archi slides --deck decks/<naam>.toml

archi validate                                 # integriteitschecks
archi normalize                                # canonieke serialisatie via Archi
archi render                                   # views naar Mermaid en HTML
```

Voor `normalize` is de Archi-engine nodig; die haalt `archi` bij het eerste
gebruik zelf op (of expliciet met `archi setup`), dus je hoeft Archi niet apart
te installeren. `archi <commando> --help` toont de volledige set vlaggen;
shell-completion zet je aan met `archi --install-completion`.

Wat de tool bijzonder maakt:

- **Muteren met een vangnet.** Elke wijziging valideert het model in het
  geheugen; bij een fout weigert de CLI op te slaan. Ids zijn onveranderlijk.
- **Canonieke serialisatie.** `normalize` laat de headless Archi-engine het
  bestand herschrijven, zodat git-diffs klein blijven, of de wijziging nu van
  de tool of van de Archi-GUI kwam.
- **Renderen.** Elke view wordt een Mermaid-diagram (rendert op GitHub) en een
  HTML-pagina die de layout uit het model volgt, plus een presentatie per
  deckdefinitie.
- **Doorklikken tussen views.** Met een links-bestand
  (`[tool.archi] links = "…"` in `archi.toml`) worden elementen in de
  HTML-views en slides klikbaar naar een andere view of een ander bestand,
  bijvoorbeeld een SVG die een project met eigen scripts maakt. Zie
  hieronder.

### Doorklikken met een links-bestand

Welk element waarheen doorklikt is een redactionele keuze, geen modelfeit;
het staat daarom in een apart TOML-bestand (zie ADR 0010):

```toml
# archi.toml
[tool.archi]
links = "tools/links.toml"

# tools/links.toml
["overzicht-van-de-gebieden"]            # bestandsnaam van de bronplaat, zonder extensie
"Gebied A" = "gebied-a-in-detail.html"   # elementnaam = pad, relatief aan de bronplaat
"Gebied B" = "../eigen-svg/gebied-b.svg"
```

Een sectie hoort bij de HTML-view met die bestandsnaam (de slug van de
viewnaam; bij views met botsende namen de naam mét id-suffix die `archi
render` kiest), of bij een bestand dat een project zelf genereert: dezelfde
sectievorm is dan bruikbaar voor eigen scripts, zodat één bestand over alle
doorkliks gaat. In slides worden relatieve paden automatisch gecorrigeerd
voor de submap. `archi validate` waarschuwt voor elementnamen die niet in de
view (of het model) staan, `archi render` voor doelen die niet bestaan en
voor secties die bij geen view of bestand horen.

## De skills als Claude Code plugin

Deze repo is tegelijk de plugin (`archi-tools`) en de marketplace die hem
aanbiedt (`archi-marketplace`). Zo installeer je de skills bij je eigen model:

```
/plugin marketplace add BureauArchitectuurDigitaleOverheid/ai-assisted-architecting
/plugin install archi-tools@archi-marketplace
```

De plugin brengt de drie skills mee; het `archi`-commando zelf komt van
`uv tool install archi-cli`. Zie `adr/0007-claude-code-plugin.md`.

## Ontwikkelen aan de tool

```bash
just setup       # venv, dependencies en de pre-commit hook
just test        # de testsuite (draait op een fixture-model)
just demo        # de CLI op het fixture-model
just build       # distributies bouwen en de metadata controleren
```

De testsuite draait op `tests/fixtures/klein-model.archimate`, niet op een echt
model. Wijzigingen lopen via een branch en een PR; CI draait de suite op Ubuntu
en Windows. Publiceren naar PyPI gebeurt op een versie-tag, zie `CLAUDE.md` en
`adr/0006-publiceren-op-pypi.md`.

## Structuur

```
tools/archi_tool/       De archi-CLI (Python, lxml, Typer; beheerd met uv)
tests/                  pytest-suite met een klein fixture-model
.claude/skills/         De skills (archi-model, archi-view, archi-slides)
.claude-plugin/         Plugin- en marketplace-manifest
adr/                    Architectuurbeslissingen over de tool
justfile                Vaste taken
```

## Licentie

[EUPL-1.2](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/LICENSE).
