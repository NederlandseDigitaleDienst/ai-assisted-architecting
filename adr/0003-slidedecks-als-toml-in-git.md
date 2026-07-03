# ADR 0003 — Slidedecks als TOML-bron met gecommitte HTML-render

- **Status**: geaccepteerd
- **Datum**: 2026-07-03

## Context

De views zijn zichtbaar op GitHub (Mermaid, ADR 0002) en in de browser
(NLDD-HTML), maar presenteren vraagt iets anders: een verhaallijn over
meerdere views heen, met titel-, sectie- en tekstslides eromheen. Bestaande
presentatietooling (PowerPoint, Slidev, reveal.js) breekt de lijn van dit
repo: geen determinisme, extra dependencies, en de architectuurbeelden zouden
als losse plaatjes uit de pas gaan lopen met het model.

## Besluit

1. **Decks zijn data.** Een presentatie is een TOML-bestand in `decks/`
   (stdlib-`tomllib`, geen nieuwe dependency) met één lineaire verhaallijn:
   titel, spreker, en een geordende lijst slides (`title`, `section`,
   `view`, `text`, `bullets`, `closing`). View-slides verwijzen naar een
   view in het model op naam of id; het diagram wordt bij het renderen
   getekend met dezelfde code als de HTML-views (layout, iconen en legenda
   uit het model). Bewust géén overzichts- of menumechanismen: een deck is
   een verhaal dat je van voor naar achter vertelt, geen viewer op het
   model.
2. **`archi render` rendert per deck één zelfstandig HTML-bestand** in
   `views/html/slides/` (inline CSS en vanilla JS; de gepinde NLDD-CSS van
   de CDN is de enige externe referentie). Deze bestanden worden gecommit —
   dezelfde afgebakende uitzondering op ADR 0001 als in ADR 0002, afgedwongen
   door dezelfde pre-commit hook en de CI-diff-check. Een deck dat naar een
   verwijderde view verwijst laat de render falen; dat is de bedoelde
   synchronisatiegarantie.
3. **Rendering is deterministisch**: geen timestamps (de optionele datum op
   de titelslide is deckdata en wordt letterlijk weergegeven), stabiele
   volgorde, markercommentaar op de eerste regel en veilige opruiming van
   verdwenen decks.

## Afwegingen

- **Hergebruik van het HTML-tekenpad** in plaats van een tweede renderer:
  view-slides zijn layoutgetrouw en blijven automatisch consistent met de
  losse viewpagina's.
- **TOML boven YAML/JSON**: stdlib-parser, leesbare diffs, comments mogelijk.
- **PDF via de print-CSS van de browser** (één slide per pagina) in plaats
  van een eigen exportpad.
- **Vanilla JS, geen framework**: de navigatie werkt ook zonder netwerk; de
  NLDD-CSS levert alleen tokens en fonts.

## Gevolgen

- Nieuwe map `decks/` (bron) en `views/html/slides/` (gegenereerd, gecommit).
- De pre-commit hook `archi-render` dekt ook `decks/`.
- Nieuwe skill `archi-slides` beschrijft de procedure; `archi slides` is het
  losse subcommando voor gericht renderen.
