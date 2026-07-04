# archi-cli

[![checks](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/actions/workflows/ci.yml/badge.svg)](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/actions/workflows/ci.yml)
[![licentie: EUPL-1.2](https://img.shields.io/badge/licentie-EUPL--1.2-blue.svg)](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/archi-cli.svg)](https://pypi.org/project/archi-cli/)

*ar·cli·mate*: de CLI in je ArchiMate. Een deterministische command line tool
voor native `.archimate`-modellen, plus de Claude Code skills die de werkwijze
beschrijven. Je inspecteert, muteert, valideert en rendert een model zonder de
Archi-GUI te openen, en de tool weigert een kapot model op te slaan.

De tool is generiek: hij werkt op elk `.archimate`-bestand. Het ADO-model
waarvoor hij ontstond woont in een eigen repo en gebruikt `archi-cli` als
dependency.

## Installeren

```bash
uv tool install archi-cli
archi --help
```

Dat zet het commando `archi` op je `$PATH`. Voor `normalize` is de Archi-engine
nodig; die haalt `archi` bij het eerste gebruik zelf op (of expliciet met
`archi setup`), dus je hoeft Archi niet apart te installeren.

## Gebruiken

Het model wordt gevonden via `--model <pad>` (vóór het subcommando), via een
`archi.toml` in de map (`[tool.archi] model = "..."`), of als het enige
`.archimate`-bestand in de werkmap.

```bash
archi stats                                    # tellingen per type
archi list --type Capability                   # elementen, gefilterd
archi show "<elementnaam of id>"               # één element met relaties
archi tree                                     # folderstructuur

archi add-element --type Capability --name "..." --property "Omschrijving=..."
archi add-relation --type Aggregation --source "..." --target "..." --name "bevat"
archi set-property <ref> "Omschrijving=..."
archi rename <ref> "Nieuwe naam"
archi remove <ref> --cascade

archi add-view --name "..." --layout cluster --type Capability --relation Aggregation
archi slides --deck decks/<naam>.toml

archi validate                                 # integriteitschecks
archi normalize                                # canonieke serialisatie via Archi
archi render                                   # views naar Mermaid en HTML
```

`archi <commando> --help` toont de volledige set vlaggen. Shell-completion
installeer je met `archi --install-completion`.

## Wat het doet

- **Muteren met een vangnet.** Elke wijziging valideert het model in het
  geheugen; bij een integriteitsfout weigert de CLI op te slaan. Ids zijn
  onveranderlijk en worden door de tooling gegenereerd.
- **Canonieke serialisatie.** `normalize` laat de headless Archi-engine het
  bestand herschrijven, zodat git-diffs klein blijven, ongeacht of de laatste
  wijziging van deze tool of van de Archi-GUI kwam.
- **Renderen.** `render` maakt van elke view een Mermaid-diagram (rendert op
  GitHub) en een HTML-pagina die de layout uit het model volgt, plus een
  presentatie per deckdefinitie in `decks/`.

## Als Claude Code plugin

De skills zijn los te installeren, zodat je ze in een ander project met je
eigen `.archimate`-model gebruikt. Deze repo is tegelijk de plugin
(`archi-tools`) en de marketplace die hem aanbiedt (`archi-marketplace`):

```
/plugin marketplace add BureauArchitectuurDigitaleOverheid/ai-assisted-architecting
/plugin install archi-tools@archi-marketplace
```

De plugin brengt de skills `archi-model`, `archi-view` en `archi-slides` mee;
het `archi`-commando zelf komt van `uv tool install archi-cli`. Zie
`adr/0007-claude-code-plugin.md`.

## Ontwikkelen

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
.claude/skills/         Claude Code skills (archi-model, archi-view, archi-slides)
.claude-plugin/         Plugin- en marketplace-manifest
adr/                    Architectuurbeslissingen
justfile                Vaste taken
```

## Licentie

[EUPL-1.2](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/LICENSE).
