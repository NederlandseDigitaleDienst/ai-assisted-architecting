# ADR 0001 — Native .archimate als bron van waarheid

- **Status**: geaccepteerd
- **Datum**: 2026-07-02

## Context

In het zusterexperiment (`ADO-architectuurmodel-experiment`) is het model
vastgelegd als JSON met een eigen metamodel, met een exportscript naar het
ArchiMate Exchange Format (AEF) en vandaar naar Archi's native formaat. Dat
werkt, maar heeft twee kosten: een conversielaag die onderhouden moet worden,
en een import-stap voor iedereen die in Archi wil kijken of werken.

Dit experiment draait de aanpak om: het native `.archimate`-bestand is zelf de
bron. AI-manipulatie gebeurt met deterministische tooling direct op dat
bestand; architecten openen hetzelfde bestand in Archi zonder import.

## Besluit

1. `models/ado.archimate` is de bron van waarheid. Alle andere vormen
   (AEF-export, afbeeldingen) zijn afgeleid en ongeversioneerd.
2. Wijzigingen lopen via de CLI in `tools/archi_tool` (surgical edits op de
   XML, gevolgd door automatische validatie) óf via de Archi-GUI.
3. Elke wijziging wordt vóór commit **genormaliseerd** door een load+save-
   roundtrip door de headless Archi CLI. Archi is daarmee de canonieke
   serializer: diffs blijven klein, ongeacht of de wijziging van de tooling
   of van de GUI kwam.
4. Samenwerking volgt de PR-workflow met één-schrijver-tegelijk op het
   modelbestand (zie `docs/spelregels.md`).

## Afwegingen

**Gewonnen** ten opzichte van de JSON-aanpak:

- Geen conversielaag en geen import-stap: Archi opent de bron direct.
- GUI-bewerkingen en AI-bewerkingen zijn gelijkwaardig; er is geen
  "eenrichtingsverkeer" meer tussen bron en tool.
- Views inclusief layout zijn onderdeel van de bron.

**Ingeleverd**:

- Het formaat is een tool-serialisatie (Eclipse EMF XML van Archi), geen open
  standaard. Mitigatie: AEF-export blijft op elk moment mogelijk via de
  Archi CLI (`--xmlexchange.export`-route) als distributievorm.
- Eén XML-bestand merget slecht. coArchi lost dit op met een eigen
  opslagformaat en een verbod op git-merges; wij mitigeren met kleine PR's,
  normalisatie vóór elke commit en de één-schrijver-afspraak.
- Het bestand is minder prettig handmatig te lezen dan de JSON. Mitigatie:
  de CLI biedt `stats`, `list`, `show` en `tree` voor inspectie.

## Gevolgen

- Het seedmodel is de ADO-export van 2026-07-02 (123 elementen, 222 relaties,
  2 views bij het seedmoment), hernoemd naar "ADO Architectuurmodel". Het
  model groeit daarna door; de actuele telling toont `just stats`.
- Validatie draait automatisch bij elke CLI-mutatie en als pre-commit hook.
- Schemabeslissingen (nieuwe elementtypes, nieuwe property-keys) worden
  vastgelegd in `docs/conventies.md`; structurele beslissingen in nieuwe ADR's.
