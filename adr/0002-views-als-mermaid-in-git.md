# ADR 0002 — Gerenderde views (Mermaid) gecommit in `views/`

- **Status**: geaccepteerd
- **Datum**: 2026-07-02

## Context

De views in het model zijn alleen zichtbaar voor wie Archi opent. Voor
review, discussie en meelezen willen we de views ook op GitHub zelf zichtbaar
hebben — in PR's, in de repo-browser en in elke markdown-renderer.

ADR 0001 stelt dat afgeleide artefacten niet geversioneerd worden. Voor
GitHub-zichtbaarheid moeten de gerenderde views echter juist wél in git:
GitHub rendert alleen gecommitte markdown.

## Besluit

1. `archi render` rendert elke view in twee vormen: `views/<slug>.md` met een
   Mermaid-diagram (auto-layout, rendert op GitHub zelf) plus een index
   (`views/README.md`), en `views/html/<slug>.html` met een NLDD-gestileerde
   HTML-weergave die de layout uit het model volgt (pixelgetrouw, lokaal te
   openen in de browser; NLDD-componenten van de CDN, gepind op versie).
   Alle bestanden dragen een markercommentaar en worden nooit handmatig
   bewerkt; verdwenen views worden opgeruimd.
2. Deze bestanden worden **gecommit** — een bewuste, afgebakende uitzondering
   op ADR 0001. Synchronisatie wordt afgedwongen door een pre-commit hook die
   bij elke modelwijziging opnieuw rendert; een commit met een verouderde
   view faalt en vraagt om herstagen.
3. De rendering is deterministisch (stabiele volgorde en ids, geen
   timestamps), zodat hetzelfde model altijd byte-identieke output geeft.

## Afwegingen

- **Mermaid, niet pixelgetrouw**: Mermaid doet eigen auto-layout. We renderen
  de *inhoud* van de view (elementen, nesting als subgraphs, getekende
  relaties), niet de Archi-layout of de formele ArchiMate-notatie. Kleuren
  volgen de ArchiMate-laag; pijlstijlen benaderen het relatietype (`--o`
  containment, `-.->` gestippeld voor beïnvloedt/realiseert). Voor de echte
  notatie blijft Archi de plek.
- Door Archi gematerialiseerde nesting-verbindingen (aggregaties naar
  objecten binnen dezelfde container) worden overgeslagen: de nesting zelf
  drukt die relatie al uit.
- Grote platte views (50+ elementen) worden breed in auto-layout; dat is
  inherent en acceptabel — GitHub biedt zoom op Mermaid-diagrammen.

## Gevolgen

- Nieuwe map `views/` met gegenereerde markdown; `docs/` blijft norm-only.
- Pre-commit hook `archi-render` naast `archi-validate`.
- De skills vermelden `render` als onderdeel van de wijzigingsprocedure.
