# ADR 0010 — Doorklikken tussen views via een links-bestand

- **Status**: geaccepteerd
- **Datum**: 2026-09-25

## Context

Gerenderde views zijn losse pagina's. Om een verhaal door een model te kunnen
volgen (van een overzicht naar het detail van één onderdeel) moeten
elementen kunnen doorklikken naar een andere view. Archi kent zelf alleen de
*View Reference*: een apart vakje in een view dat naar een andere view wijst
(de HTML-render maakt daar al een link van). Een element zelf klikbaar maken
kan Archi niet, en projecten maken daarnaast vaak eigen diagrammen met
scripts (bijvoorbeeld SVG's) waar de doorklik ook naartoe of vandaan moet.

Het ADO-model deed dit al voor zijn script-SVG's met een apart bestand
`tools/links.toml`, bewust buiten het model: of iets doorklikt is een
redactionele keuze voor de presentatie, geen eigenschap van de architectuur.

## Besluit

1. **Een links-bestand, opt-in via `archi.toml`** (`[tool.archi] links`).
   Zonder die regel verandert er niets.
2. **Vorm:** per bronplaat een sectie met als naam de bestandsnaam zonder
   extensie; daarin `"elementnaam" = "pad"`, met het pad relatief aan de map
   van de bronplaat. Voor een HTML-view is de sectienaam de slug van de
   viewnaam. Dezelfde vorm is bruikbaar voor een project dat eigen diagrammen
   genereert, zodat één bestand over alle doorkliks beslist en views en
   eigen diagrammen naar elkaar kunnen linken.
3. **archi-cli maakt element-vakjes klikbaar** in de HTML-views en in de
   views binnen slides (relatieve paden daar met `../`, omdat decks een map
   dieper staan). URL's, absolute paden en ankers blijven ongemoeid.
4. **Controles zijn waarschuwingen, geen fouten:** `validate` controleert of
   een elementnaam in de betreffende view staat (of, voor een eigen diagram,
   in het model); `render` controleert of doelbestanden bestaan en of elke
   sectie bij een view of een bestaand bestand hoort. Zo valt een hernoemde
   view of een tikfout op zonder dat een ontbrekende link het werk blokkeert.
5. **Niet voor Mermaid:** GitHub blokkeert klikbare links in Mermaid.

## Gevolgen

- Een hernoemde view verandert zijn bestandsnaam en dus zijn sectienaam;
  `render` waarschuwt dan, en de sectie moet mee worden hernoemd.
- Een element dat in een view meerdere keren voorkomt, linkt overal.
