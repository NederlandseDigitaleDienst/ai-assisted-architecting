# ADR 0009 — Omschrijvingen horen in Archi's documentatieveld

- **Status**: geaccepteerd
- **Datum**: 2026-09-25
- **Wijzigt**: ADR 0008 (default-property-keys)

## Context

Archi heeft voor elk element, elke relatie en elke view een standaard
documentatieveld (`<documentation>`, in de GUI onder *Main*). De skills en de
README van deze tool adviseerden toch een omschrijving als property
`Omschrijving=...` vast te leggen, en ADR 0008 nam `Omschrijving` en
`Toelichting` op in de ingebouwde lijst van generieke property-keys. Modellen
die die werkwijze volgden (zoals het ADO-model) hebben hun omschrijvingen
daardoor in een zelfbedachte property staan: onzichtbaar op de plek waar
Archi-gebruikers ze verwachten, en niet meegenomen door tooling die het
documentatieveld leest.

## Besluit

1. **Een omschrijving hoort in het documentatieveld** (`--documentation` bij
   `add-element`, of `set-documentation`). Properties zijn voor
   gestructureerde kenmerken. De skills en de README zeggen dat nu zo.
2. **`Omschrijving` en `Toelichting` zijn geen default-property-keys meer.**
   `DEFAULT_PROPERTY_KEYS` bevat alleen nog `Bron`. Een model zonder eigen
   conventielijst dat die keys gebruikt, krijgt dus een waarschuwing van
   `validate`; dat is bedoeld als duwtje richting het documentatieveld. Een
   project dat de keys bewust wil houden, zet ze in zijn eigen
   `conventies.md`.
3. **Leesvolgorde in de renderers:** eerst het documentatieveld, dan de
   property `Omschrijving` als terugval voor modellen die nog niet gemigreerd
   zijn (tooltip in `render_html`, intro in `render_slides`).
4. **Migreren kan volledig via de CLI:** `set-documentation` gevolgd door het
   nieuwe `remove-property`, zodat er geen lege properties achterblijven.

## Gevolgen

- Slides: als een element zowel documentatie als een `Omschrijving` heeft,
  wint nu de documentatie. Bestaande decks kunnen daardoor een andere intro
  tonen; noemen in de release notes.
- Een model zonder conventielijst dat `Omschrijving`/`Toelichting` gebruikt,
  ziet na de upgrade nieuwe waarschuwingen (geen fouten).
