---
name: archi-view
description: Genereer of verwijder een view (diagram) in een .archimate-model met deterministische layout met de archi-CLI. Gebruik bij "maak een view", "genereer een diagram", "visualiseer een selectie elementen", "verwijder view", of als een selectie zichtbaar moet worden in Archi of op GitHub.
---

# Views genereren in een .archimate-model

Het commando is **`archi`** (installeerbaar met `uv tool install archi-cli`).

Views worden onderdeel van het modelbestand zelf. Na `archi render` zijn ze
ook zichtbaar buiten Archi: als Mermaid op GitHub en als HTML lokaal (de
locatie hangt af van het project). De slug volgt uit de viewnaam.

## Genereren

```bash
archi add-view --name "<naam>" --layout <grid|cluster> \
    [--type Capability ...] [--relation Aggregation ...] [--property key=value] \
    [--root "<element>"] [--related] [--element "<element>" ...]
```

Voorbeeld, een brede selectieview op een elementtype:

```bash
archi add-view --name "Alle capabilities" \
    --layout cluster --type Capability --relation Aggregation
```

Voorbeeld, een detailview van één element met alles eromheen:

```bash
archi add-view --name "<element> in detail" \
    --layout cluster --root "<element>" --related
```

## Layoutkeuze

- **`grid`**: alle geselecteerde elementen in een raster, alle geselecteerde
  relaties als verbindingen. Geschikt voor kleine selecties zonder
  hiërarchie.
- **`cluster`**: groepeert op structurele relaties (Aggregation en
  Composition binnen de selectie). Het bronelement komt als kop boven zijn
  doelelementen, met ruimte voor de pijlen. Elementen zonder koppeling komen
  los achteraan. Dit is de keuze voor hiërarchische structuren.

## Selectie

`--type` en `--relation` zijn herhaalbaar; `--property key=value` filtert op
een property-waarde. `--root "<element>"` selecteert dat element plus alles
wat het (recursief) aggregeert of composeert; `--related` voegt daar de
direct gerelateerde elementen aan toe (één stap, beide richtingen), zoals de
doelen en diensten rondom een element. `--element "<id of unieke naam>"`
(herhaalbaar) voegt een specifiek element aan de selectie toe, naast of in
plaats van de filters; handig als je een handjevol elementen bij naam wilt
tonen zonder een type- of property-filter te bedenken. Zonder filters gaat
het hele model de view in, en dat is vrijwel nooit de bedoeling. Een lege
selectie geeft een foutmelding in plaats van een lege view.

## Na het genereren

1. `archi validate` (draait ook automatisch bij het opslaan door de CLI).
2. `archi normalize` vóór commit.
3. `archi render`, zodat de nieuwe view ook als Mermaid en HTML op schijf
   staat als het project die committeert.
4. Layout fijnslijpen kan daarna in de Archi-GUI. Het bestand is de bron,
   dus zo'n aanpassing is een gewone modelwijziging: opnieuw normaliseren,
   renderen en committen.

## Verwijderen

```bash
archi remove "<viewnaam of id>"
```

Een view heeft zelden inkomende verwijzingen, dus dit kan meestal zonder
`--cascade`. Daarna `archi render`: de bijbehorende gerenderde bestanden
worden opgeruimd (alleen bestanden met het generatie-markercommentaar; iets
wat een mens daar zelf heeft neergezet blijft staan).
