---
name: archi-view
description: Genereer een view (diagram) in het .archimate-model met deterministische layout. Gebruik bij "maak een view", "genereer een diagram", "visualiseer de gebieden/bouwblokken", of als een selectie van elementen zichtbaar moet worden in Archi.
---

# View genereren in het .archimate-model

Views worden onderdeel van het modelbestand zelf en zijn direct zichtbaar in
Archi (Models-boom → Views). Genereren:

```bash
uv run archi add-view --name "<naam>" --layout <grid|cluster> \
    [--type Capability ...] [--relation Aggregation ...] [--property key=value]
```

## Layoutkeuze

- **`grid`** — alle geselecteerde elementen in een eenvoudig raster; alle
  geselecteerde relaties als verbindingen. Goed voor kleine selecties en
  overzichten zonder hiërarchie.
- **`cluster`** — groepeert op structurele relaties (Aggregation/Composition
  binnen de selectie): het bronelement komt als kop boven zijn doelelementen,
  met ruimte voor de relatiepijlen. Goed voor gebied→bouwblok-achtige
  structuren. Elementen zonder koppeling komen los achteraan.

## Selectie

- `--type` (herhaalbaar) filtert op elementtype, `--property key=value` op een
  property, `--relation` (herhaalbaar) beperkt welke relaties getekend worden.
- Zonder filters gaat het hele model de view in — vrijwel nooit de bedoeling.

## Na het genereren

1. `just validate` (draait ook automatisch bij het opslaan door de CLI).
2. `just normalize` vóór commit.
3. `uv run archi render` — ververst de Mermaid-weergaven in `views/` zodat de
   view ook op GitHub zichtbaar is (de pre-commit hook dwingt dit af).
4. Fijnslijpen van de layout kan daarna gewoon in de Archi-GUI; het bestand
   is de bron, dus die aanpassing is een normale modelwijziging (opnieuw
   normaliseren, renderen en committen).
