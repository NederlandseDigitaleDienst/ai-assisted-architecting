---
name: archi-model
description: Werkwijze voor het .archimate-model - elementen, relaties en properties wijzigen via de archi-CLI, valideren en normaliseren. Gebruik bij elke wijziging aan models/ado.archimate, bij "voeg element/bouwblok/doel/relatie toe", "wijzig het model", "verwijder element", of vragen over de modelconventies.
---

# Werken aan het .archimate-model

## Leesvolgorde

1. `docs/conventies.md` — types in gebruik, property-keys, naamgeving
2. `docs/spelregels.md` — workflow en de één-schrijver-afspraak

## Harde regels

- **Nooit handmatig XML bewerken** in `models/ado.archimate`; alle mutaties
  via `uv run archi ...`. De CLI valideert automatisch en weigert op te slaan
  bij integriteitsfouten.
- Bestaande ids nooit wijzigen; nieuwe ids genereert de tooling.
- Nieuwe property-keys eerst toevoegen aan `docs/conventies.md` §3.

## Modelwijziging doorvoeren

1. Branch afsplitsen (nooit direct op `main`); check dat er geen andere
   model-PR openstaat (één schrijver tegelijk).
2. Verkennen: `uv run archi stats` / `list --type ...` / `show <id|naam>`.
3. Wijzigen, bijvoorbeeld:
   ```bash
   uv run archi add-element --type Capability --name "..." \
       --property "Capability-niveau=bouwblok" --property "Omschrijving=..."
   uv run archi add-relation --type Aggregation --source "<gebied>" --target "<bouwblok>" --name "bevat"
   uv run archi set-property <id> "Omschrijving=..."
   uv run archi remove <id>            # --cascade voor relaties/view-objecten
   ```
   Elementen en relaties zijn aanspreekbaar op id of (unieke) naam.
4. `just validate` — moet schoon zijn.
5. `just normalize` — Archi serialiseert canoniek; verplicht vóór commit
   zodat de diff klein blijft (duurt ~15 s, headless Archi).
6. `just render` — ververst de gerenderde weergaven in `views/` en
   `views/html/` (de pre-commit hook dwingt dit af; renders committen mee).
7. Commit (semantisch, Nederlands) → push → PR.

## Valkuilen

- `remove` zonder `--cascade` weigert bewust als er relaties of
  view-objecten naar het element verwijzen; dat is een signaal om eerst te
  kijken wat er aan hangt (`show <id>`), niet om blind `--cascade` te doen.
- Als iemand het bestand in de Archi-GUI heeft bewerkt: gewoon doorwerken,
  maar altijd eerst `just validate` en vóór commit `just normalize`.
