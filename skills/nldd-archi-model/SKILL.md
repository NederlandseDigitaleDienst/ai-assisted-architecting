---
name: nldd-archi-model
description: Werkwijze voor het bewerken van een native .archimate-model met de archi-CLI - elementen, relaties en properties toevoegen of wijzigen, valideren en normaliseren. Gebruik bij "voeg element/relatie/doel toe", "wijzig het model", "verwijder element", "hernoem", of vragen over de archi-CLI.
---

# Werken aan een .archimate-model

Het commando is **`archi`** (installeerbaar met `uv tool install archi-cli`).
De CLI werkt op elk native `.archimate`-bestand. Het model wordt gevonden via
`--model <pad>` (vóór het subcommando), via `[tool.archi] model` in een
`archi.toml`, of als het enige `.archimate`-bestand in de werkmap.

## Harde regels

- **Nooit handmatig XML bewerken** in het modelbestand; alle mutaties via
  `archi ...`. De CLI valideert automatisch en weigert op te slaan bij
  integriteitsfouten.
- Bestaande ids nooit wijzigen; nieuwe ids genereert de tooling.
- Property-keys worden getoetst aan de conventielijst van het project (een
  `conventies.md` met een `Property-keys`-sectie, gevonden via `archi.toml`
  of naast het model) of aan een ingebouwde standaardset. Een onbekende key
  geeft een waarschuwing, geen fout.

## Modelwijziging doorvoeren

1. Kijk eerst wat er staat:
   ```bash
   archi stats
   archi list --type Capability --property "<key>=<waarde>"
   archi show "<elementnaam of id>"
   archi tree
   ```
2. Wijzig via de CLI. Elementen en relaties zijn aanspreekbaar op id of op
   naam zolang die uniek is; bij een dubbele naam somt de CLI de kandidaten
   op en gebruik je het id.
   ```bash
   archi add-element --type Capability --name "<naam>" \
       --property "<key>=<waarde>" --documentation "..."
   archi add-relation --type Aggregation \
       --source "<bron>" --target "<doel>" --name "bevat"
   archi set-property <ref> "<key>=<waarde>"
   archi remove-property <ref> "<key>"
   archi rename <ref> "Nieuwe naam"
   archi set-documentation <ref> "..."
   archi remove <ref>              # --cascade indien nodig, zie onder
   ```
   Een omschrijving van een element of relatie hoort in Archi's eigen
   documentatieveld (`--documentation` / `set-documentation`, in Archi het
   veld onder *Main*), niet in een zelfbedachte property zoals
   `Omschrijving`. Properties zijn voor gestructureerde kenmerken.
   `add-element` plaatst het element in de folder die uit het type volgt;
   `--folder <type>` overschrijft dat alleen als je een bewuste reden hebt.
   Gebruikt het model submappen binnen een laag (bv. per gebied), geef die
   dan direct mee met `--subfolder "<map>"` (bij `add-element` én
   `add-relation`; geneste mappen met `/`). Een bestaand element, relatie of
   view verplaats je met `archi move <ref> --subfolder "<map>"` (leeg = terug
   naar de laagfolder). Een ontbrekende submap is een fout met de lijst van
   bestaande submappen; alleen met `--create-subfolder` wordt hij bewust
   aangemaakt, zodat een tikfout geen nieuwe map oplevert.
3. `archi validate`. Moet schoon zijn; waarschuwingen over property-keys los
   je op in de conventielijst of door de key aan te passen.
4. `archi normalize`. Aanbevolen vóór commit: Archi serialiseert canoniek en
   houdt de diff klein. Vereist een Archi-installatie; `archi` haalt de engine
   bij het eerste gebruik zelf op (of expliciet met `archi setup`).
5. `archi render`. Ververst de gerenderde views (Mermaid en HTML) als het
   project die committeert.

## Verwijderen en de cascade

`remove` zonder `--cascade` weigert als er relaties of view-objecten naar het
element verwijzen. Dat is een signaal om eerst `show <ref>` te doen en te
zien wat eraan hangt. Met `--cascade` verdwijnen ook de verwijzende relaties,
de view-objecten en hun connections, inclusief het opschonen van
`targetConnections`-attributen. Gebruik het bewust, niet als reflex.

## Als iemand in de Archi-GUI heeft gewerkt

Dat is toegestaan; het bestand is de bron. Draai daarna wel de volledige rij:
`archi validate`, `archi normalize`, `archi render`, en commit het geheel.
Validate wijst eventuele hangende verwijzingen aan die de GUI-bewerking heeft
achtergelaten.
