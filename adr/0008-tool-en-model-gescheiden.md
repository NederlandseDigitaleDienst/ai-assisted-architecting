# ADR 0008 — Tool en model uit elkaar getrokken

- **Status**: geaccepteerd
- **Datum**: 2026-07-04

## Context

Deze repo begon als één geheel: het ADO-model (`models/ado.archimate`, decks,
views) én de tooling eromheen. Sinds ADR 0004–0007 is de tooling een
zelfstandig, gepubliceerd pakket (`archi-cli` op PyPI) dat op elk
`.archimate`-bestand werkt, met een Claude Code plugin eromheen. Het ADO-model
in dezelfde repo houden botst daarmee: de plugin heette naar ADO, de CI
valideerde één specifiek model, en de tool leek gebonden aan dat project
terwijl hij dat allang niet meer is.

## Besluit

1. **Deze repo is de tool.** `archi-cli`, de skills en de plugin. Geen model,
   decks of gerenderde views meer; de testsuite draait op een fixture-model in
   `tests/fixtures/`.
2. **Het ADO-model verhuist naar een eigen repo**, met behoud van git-history
   (geëxtraheerd met `git filter-repo`). Die repo bevat `models/`, `decks/`,
   `views/`, `docs/conventies.md`, `docs/spelregels.md` en een `archi.toml` die
   `archi` naar het model wijst. Hij gebruikt `archi-cli` als tool, via
   `uv tool install archi-cli`.
3. **De marketplace heet `archi-marketplace`** (was `ado-plugins`); de plugin
   blijft `archi-tools`. Beide namen zijn projectonafhankelijk.
4. **CI en pre-commit zijn gesnoeid.** Zonder model in de repo is er niets te
   valideren of te renderen; CI draait `uv sync`, een `archi --help`-rooktest
   en de testsuite. Pre-commit draait alleen pytest. De model-afhankelijke
   checks (validate, render, view-sync-diff) horen in de model-repo.
5. **De skills zijn generiek.** ADO-elementnamen en repo-specifieke paden zijn
   vervangen door placeholders; de commando's gebruiken `archi`. De werkwijze
   blijft, de voorbeelden zijn niet langer aan één project gebonden.

## Afwegingen

- **Splitsen boven één repo houden.** Zolang het bureau de enige gebruiker was,
  was één repo prima (ADR 0006 hield het pakket bewust hier). De reden om nu
  wel te splitsen is concreet: de plugin en de tool zijn niet ADO-specifiek, en
  een tweede model (elke `.archimate`) is expliciet het doel. Een tool-repo die
  naar één project heet en één model test, klopt dan niet meer.
- **History behouden.** Het model is levend werk; `git filter-repo` houdt de
  commit-history intact in de nieuwe repo. In deze repo blijft de history van
  het model in de oude commits staan; alleen de bestanden zijn weg.
- **Ingebouwde default-property-keys generiek gemaakt.** `DEFAULT_PROPERTY_KEYS`
  bevatte ADO-keys (`Capability-niveau`, `Driver-categorie`, …); nu alleen
  generieke (`Omschrijving`, `Toelichting`, `Bron`; sinds ADR 0009 alleen nog
  `Bron`). Een project levert zijn
  eigen keys via een `conventies.md`.

## Gevolgen

- Verwijderd uit deze repo: `models/`, `decks/`, `views/`, `archi.toml`,
  `docs/conventies.md`, `docs/spelregels.md`. Hun history blijft in de oude
  commits; de bestanden leven verder in de model-repo.
- README en CLAUDE.md herschreven naar een tool-repo. De justfile is gesnoeid
  tot `setup`, `test`, `demo`, `build`.
- De drift-guard op de conventiedoc (voorheen tegen `docs/conventies.md`) test
  nu tegen een inline-fixture en tegen `DEFAULT_PROPERTY_KEYS`.
- De repo-naam (`ai-assisted-architecting`) blijft voorlopig; de PyPI-naam
  (`archi-cli`), plugin (`archi-tools`) en marketplace (`archi-marketplace`)
  zijn de namen die naar buiten tellen.
