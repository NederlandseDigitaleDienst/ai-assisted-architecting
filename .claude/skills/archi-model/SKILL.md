---
name: archi-model
description: Werkwijze voor het .archimate-model - elementen, relaties en properties wijzigen via de archi-CLI, valideren en normaliseren. Gebruik bij elke wijziging aan models/ado.archimate, bij "voeg element/bouwblok/doel/relatie toe", "wijzig het model", "verwijder element", "hernoem", of vragen over de modelconventies.
---

# Werken aan het .archimate-model

## Leesvolgorde

1. `docs/conventies.md`: types in gebruik, property-keys, naamgeving
2. `docs/spelregels.md`: workflow en de een-schrijver-afspraak

## Harde regels

- **Nooit handmatig XML bewerken** in `models/ado.archimate`; alle mutaties
  via `uv run archi ...`. De CLI valideert automatisch en weigert op te slaan
  bij integriteitsfouten.
- Bestaande ids nooit wijzigen; nieuwe ids genereert de tooling.
- Nieuwe property-keys eerst toevoegen aan `docs/conventies.md` §3, anders
  waarschuwt de validator. Nieuwe elementtypes of structurele keuzes krijgen
  een ADR in `adr/`.
- Elk commando accepteert `--model <pad>` (vóór het subcommando) voor een
  ander modelbestand; zonder vlag vindt de CLI het model via `archi.toml`
  (`[tool.archi] model`), in deze repo `models/ado.archimate`.

## Modelwijziging doorvoeren

1. Branch afsplitsen (nooit direct op `main`). Check dat er geen andere
   model-PR openstaat: een schrijver tegelijk.
2. Kijk eerst wat er staat:
   ```bash
   just stats
   uv run archi list --type Capability --property "Capability-niveau=gebied"
   uv run archi show "Gegevensuitwisseling"    # id of unieke naam
   uv run archi tree
   ```
3. Wijzig via de CLI. Elementen en relaties zijn aanspreekbaar op id of op
   naam zolang die uniek is; bij een dubbele naam somt de CLI de kandidaten
   op en gebruik je het id.
   ```bash
   uv run archi add-element --type Capability --name "..." \
       --property "Capability-niveau=bouwblok" --property "Omschrijving=..."
   uv run archi add-relation --type Aggregation \
       --source "<gebied>" --target "<bouwblok>" --name "bevat"
   uv run archi set-property <ref> "Omschrijving=..."
   uv run archi rename <ref> "Nieuwe naam"
   uv run archi set-documentation <ref> "..."
   uv run archi remove <ref>              # --cascade indien nodig, zie onder
   ```
   `add-element` plaatst het element in de folder die uit het type volgt;
   `--folder <type>` overschrijft dat alleen als je een bewuste reden hebt.
4. `just validate`. Moet schoon zijn; waarschuwingen over property-keys los
   je op in de conventielijst of door de key aan te passen.
5. `just normalize`. Verplicht vóór commit: Archi serialiseert canoniek en
   houdt de diff klein. Duurt ongeveer 15 seconden (headless Archi).
6. `just render`. Ververst `views/` en `views/html/`; de gerenderde
   bestanden committen mee.
7. Commit (semantisch, Nederlands), push, PR openen. De architect-eigenaar
   reviewt en merget.

De pre-commit hooks draaien validate en render nogmaals. Faalt de commit
omdat render bestanden bijwerkte, stage die dan en commit opnieuw; dat is het
normale pad, geen fout.

## Verwijderen en de cascade

`remove` zonder `--cascade` weigert als er relaties of view-objecten naar het
element verwijzen. Dat is een signaal om eerst `show <ref>` te doen en te
zien wat eraan hangt. Met `--cascade` verdwijnen ook de verwijzende relaties,
de view-objecten en hun connections, inclusief het opschonen van
`targetConnections`-attributen. Gebruik het bewust, niet als reflex.

## Als iemand in de Archi-GUI heeft gewerkt

Dat is toegestaan; het bestand is de bron. Draai daarna wel de volledige rij:
`just validate`, `just normalize`, `just render`, en commit het geheel.
Validate wijst eventuele hangende verwijzingen aan die de GUI-bewerking
heeft achtergelaten.
