---
name: archi-slides
description: Genereer NLDD-gestileerde HTML-slidedecks uit het .archimate-model vanuit decks/*.toml, een lineair verhaal met views uit het model afgewisseld met tekst. Gebruik bij "maak een presentatie", "genereer slides", "maak een slidedeck", "presenteer de views", of als een deck in decks/ moet worden toegevoegd, aangepast of verwijderd.
---

# Slidedecks genereren uit het .archimate-model

Een deck is een TOML-bestand in `decks/` met één lineaire verhaallijn:
titel, secties, views uit het model, afgewisseld met tekst en bullets. De
architectuurbeelden komen bij het renderen rechtstreeks uit het model.
`archi render` (en dus `just render` en de pre-commit hook) rendert elk deck
naar één zelfstandig HTML-bestand in `views/html/slides/<slug>.html`,
bekijken met `just serve` op `http://localhost:8766/slides/<slug>.html`.
De achtergrond staat in `adr/0003-slidedecks-als-toml-in-git.md`.

## Een deck schrijven

```toml
title = "Titel van de presentatie"   # verplicht
slug = "korte-naam"                  # optioneel; default de bestandsnaam
speaker = "Naam"                     # optioneel
affiliation = "Organisatie"          # optioneel
date = "3 juli 2026"                 # optioneel; letterlijk op de titelslide
lead = "Ondertitel."                 # optioneel

[[slides]]
type = "title"

[[slides]]
type = "section"                     # hoofdstukscheider in Rijksblauw
title = "Hoofdstuk"
lead = "Optionele toelichting."

[[slides]]
type = "view"
view = "Viewnaam of view-id"         # verplicht; moet bestaan in het model
title = "Eigen titel"                # optioneel; default de viewnaam
intro = "Eigen intro"                # optioneel; default de view-documentatie
notes = "Sprekersnotitie."           # optioneel op elk slidetype

[[slides]]
type = "view"                        # zelfde view, ingezoomd: de camera
view = "Viewnaam of view-id"         # glijdt naar het element, de rest dimt
focus = "Elementnaam of -id"         # titel en intro defaulten dan naar de
                                     # naam en Omschrijving van dat element

[[slides]]
type = "text"                        # lopende tekst tussen de views
title = "Optionele kop"
body = """
Alinea's gescheiden door een witregel.

Tweede alinea.
"""

[[slides]]
type = "bullets"
title = "Kop"
bullets = ["Punt één.", "Punt twee."]
gov = "Optionele overheids-callout."

[[slides]]
type = "closing"
title = "Dank"
link = { href = "https://...", label = "linktekst" }   # optioneel
```

Toegestane sleutels per type (alles daarbuiten is een harde fout):

| type | sleutels |
|---|---|
| `title` | `title`, `lead`, `notes` |
| `section` | `title` (verplicht), `lead`, `notes` |
| `view` | `view` (verplicht), `focus`, `title`, `intro`, `notes` |
| `text` | `body` (verplicht), `title`, `lead`, `notes` |
| `bullets` | `title` en `bullets` (verplicht), `lead`, `gov`, `notes` |
| `closing` | `title` (verplicht), `lead`, `link`, `notes` |

## Renderen

```bash
just render                          # alles: views, HTML én decks
uv run archi slides                  # alleen de decks
uv run archi slides --deck decks/ado.toml   # één deck, zonder opruiming
```

Een deck dat naar een niet-bestaande view verwijst laat het renderen falen
met een foutmelding die de beschikbare views opsomt; een onbekende `focus`
noemt de containers in de view.

Een sterke verhaallijn is: overzichtsview → `focus`-slide op één gebied →
detailview van dat gebied. Detailviews genereer je met
`uv run archi add-view --layout cluster --root "<gebied>" --related`
(zie de skill archi-view).

## In de browser

Pijltjestoetsen/spatie navigeren, `f` volledig scherm, `n` sprekersnotities,
`a` autoplay, `#5` in de URL is een deeplink naar slide 5. Printen via de
browser geeft één slide per pagina (PDF-export).

## Na het genereren

1. `just render` en de gegenereerde bestanden in `views/html/slides/`
   mee-committen; de pre-commit hook dwingt dit af.
2. Gegenereerde HTML nooit handmatig bewerken (markercommentaar op regel 1);
   wijzig het deck-TOML of het model en render opnieuw.

## Verwijderen

Verwijder het TOML-bestand uit `decks/` en draai `just render`: de
bijbehorende HTML wordt opgeruimd (alleen bestanden met het marker-
commentaar; handgemaakte bestanden blijven staan).
