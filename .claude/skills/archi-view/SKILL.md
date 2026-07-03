---
name: archi-view
description: Genereer of verwijder een view (diagram) in het .archimate-model met deterministische layout. Gebruik bij "maak een view", "genereer een diagram", "visualiseer de gebieden/bouwblokken", "verwijder view", of als een selectie van elementen zichtbaar moet worden in Archi of op GitHub.
---

# Views genereren in het .archimate-model

Views worden onderdeel van het modelbestand zelf. Ze zijn daarna op drie
plekken zichtbaar: in Archi (Models-boom, map Views), als Mermaid op GitHub
(`views/<slug>.md`) en als NLDD-HTML (`views/html/<slug>.html`, bekijken met
`just serve`). De slug volgt uit de viewnaam; beide indexbestanden worden
automatisch bijgewerkt.

## Genereren

```bash
uv run archi add-view --name "<naam>" --layout <grid|cluster> \
    [--type Capability ...] [--relation Aggregation ...] [--property key=value] \
    [--root "<element>"] [--related]
```

Voorbeeld, een brede selectieview:

```bash
uv run archi add-view --name "Ontwikkelingsgebieden en functionele bouwblokken" \
    --layout cluster --type Capability --relation Aggregation
```

Voorbeeld, een detailview van één gebied met alles eromheen:

```bash
uv run archi add-view --name "Gegevensuitwisseling in detail" \
    --layout cluster --root "Gegevensuitwisseling" --related
```

## Layoutkeuze

- **`grid`**: alle geselecteerde elementen in een raster, alle geselecteerde
  relaties als verbindingen. Geschikt voor kleine selecties zonder
  hiërarchie.
- **`cluster`**: groepeert op structurele relaties (Aggregation en
  Composition binnen de selectie). Het bronelement komt als kop boven zijn
  doelelementen, met ruimte voor de pijlen. Elementen zonder koppeling komen
  los achteraan. Dit is de keuze voor gebied-naar-bouwblok-structuren.

## Selectie

`--type` en `--relation` zijn herhaalbaar; `--property key=value` filtert op
een property-waarde. `--root "<element>"` selecteert dat element plus alles
wat het (recursief) aggregeert of composeert; `--related` voegt daar de
direct gerelateerde elementen aan toe (één stap, beide richtingen), zoals de
doelen en diensten rond een gebied. Zonder filters gaat het hele model de
view in, en dat is vrijwel nooit de bedoeling. Een lege selectie geeft een
foutmelding in plaats van een lege view.

## Na het genereren

1. `just validate` (draait ook automatisch bij het opslaan door de CLI).
2. `just normalize` vóór commit.
3. `just render`, zodat de nieuwe view ook in `views/` en `views/html/`
   staat; de pre-commit hook dwingt dit af en de renders committen mee.
4. Layout fijnslijpen kan daarna in de Archi-GUI. Het bestand is de bron,
   dus zo'n aanpassing is een gewone modelwijziging: opnieuw normaliseren,
   renderen en committen.

## Verwijderen

```bash
uv run archi remove "<viewnaam of id>"
```

Een view heeft zelden inkomende verwijzingen, dus dit kan meestal zonder
`--cascade`. Daarna `just render`: de bijbehorende bestanden in `views/`
worden opgeruimd (alleen bestanden met het generatie-markercommentaar; iets
wat een mens daar zelf heeft neergezet blijft staan).
