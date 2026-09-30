# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Wat deze repo is

`archi-cli`: een deterministische CLI (`tools/archi_tool/`, commando `archi`)
voor het inspecteren, muteren, valideren en renderen van native
`.archimate`-modellen, plus de Claude Code skills die de werkwijze beschrijven.
De tool is generiek en werkt op elk `.archimate`-bestand; er zit geen model in
deze repo (het ADO-model is losgetrokken naar een eigen repo). De testsuite
draait op een klein fixture-model in `tests/fixtures/`.

De tool is gepubliceerd op PyPI als `archi-cli` en distribueert zichzelf als
Claude Code plugin (`archi-tools`) via de marketplace `archi-marketplace`.

## Commando's

```bash
just setup            # eenmalig: uv sync + pre-commit install
just test             # pytest
just lint             # alle pre-commit hooks op alle bestanden (zoals CI)
just demo             # de CLI op het fixture-model
just build            # distributies bouwen + twine check (vóór een release)

# De CLI zelf (op elk model; --model vóór het subcommando):
uv run archi stats|list|show|tree ...      # inspectie
uv run archi add-element|add-relation|set-property|remove-property|move|rename|set-documentation|remove ...
uv run archi add-view --name ... --layout grid|cluster
uv run archi slides [--deck decks/<naam>.toml]
uv run archi validate|normalize|render
uv run archi setup                         # Archi-engine ophalen naar de cache
```

Het model wordt gevonden via `--model <pad>`, via `[tool.archi] model` in een
`archi.toml`, of als het enige `.archimate`-bestand in de werkmap.

## Prerequisites: controleren en zo nodig installeren

Ga er niet vanuit dat de omgeving compleet is. Controleer bij het eerste
commando dat faalt (of proactief aan het begin van een sessie) en installeer
wat ontbreekt, zonder de gebruiker ernaartoe te sturen:

- `uv` ontbreekt (`command -v uv` / `where.exe uv`): macOS/Linux
  `curl -LsSf https://astral.sh/uv/install.sh | sh` of `brew install uv`;
  Windows `winget install --id astral-sh.uv -e` of
  `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
  uv regelt zelf een passende Python (>=3.12).
- `just` ontbreekt: macOS `brew install just`; Windows
  `winget install --id Casey.Just -e`; Linux via de packagemanager.
- Venv of dependencies ontbreken (`.venv/` bestaat niet, of `uv run archi`
  faalt op imports): `uv sync`.
- Pre-commit hooks ontbreken (`.git/hooks/pre-commit` bestaat niet of bevat
  geen pre-commit-aanroep): `uv run pre-commit install`. pre-commit zelf is
  een dev-dependency en komt mee met `uv sync`; er is geen globale
  installatie nodig.
- Archi ontbreekt (alleen nodig voor `normalize`): `archi` haalt de engine
  bij het eerste gebruik zelf op, of expliciet met `archi setup`. Valideren,
  renderen en muteren werken zonder Archi.

## Testen

- Hele suite: `just test`
- Eén test: `uv run pytest tests/test_model.py::test_remove_cascade_cleans_views_and_relations`
- Tests werken op een kopie van `tests/fixtures/klein-model.archimate` via de
  `model`- en `model_path`-fixtures in `tests/conftest.py`. Nieuwe checks in
  `validate.py` horen een test te krijgen die het fixture-model gericht
  corrumpeert en de foutmelding asserteert.

## Publiceren naar PyPI

De CLI is een pakket `archi-cli` (importnaam `archi_tool`, commando `archi`),
gepubliceerd op https://pypi.org/project/archi-cli/. De achtergrond staat in
`adr/0006-publiceren-op-pypi.md`.

**Wanneer publiceren.** Alleen bij een bewuste release, niet per merge. Een
merge naar `main` triggert niets: de release-workflow luistert uitsluitend
naar een versie-tag `v*`. Een PyPI-versie is onomkeerbaar, dus publiceer pas
als `main` groen is en de wijziging klaar is voor gebruikers.

**Hoe publiceren.**

1. Bump de versie in `pyproject.toml` (semantisch: patch voor fixes, minor
   voor features).
2. Commit dat op `main` (via de normale branch → PR → merge).
3. Tag en push: de tag moet exact de pyproject-versie zijn, met een `v`-prefix.
   ```bash
   git checkout main && git pull
   git tag v0.1.1
   git push origin v0.1.1
   ```
4. `.github/workflows/release.yml` doet de rest: het controleert dat de tag met
   de pyproject-versie matcht (anders faalt het luid), bouwt met `uv build` en
   publiceert via **PyPI Trusted Publishing** (OIDC). Er is geen API-token of
   secret in de repo.

**Vóór een release verifiëren** (goedkoop, en een PyPI-versie is onomkeerbaar):
```bash
just build   # uv build + twine check; moet PASSED geven
```

**Eenmalig al geregeld:** de Trusted Publisher is op PyPI gekoppeld
(owner `BureauArchitectuurDigitaleOverheid`, repo `ai-assisted-architecting`,
workflow `release.yml`, environment `pypi`). Dat hoeft niet opnieuw.

## Harde regels

- **Nooit handmatig XML bewerken** in een modelbestand. Alle mutaties via de
  `archi`-CLI, die valideert automatisch en weigert opslaan bij fouten. Voor
  procedures: skills `archi-model`, `archi-view` en `archi-slides`.
- Ids (`id-<uuid4>`) zijn onveranderlijk; de tooling genereert nieuwe.
- Nieuwe checks in `validate.py` krijgen een test. Structurele beslissingen
  krijgen een ADR in `adr/`.
- Wijzigingen via branch → commit → PR. Semantische Nederlandstalige
  commit-berichten. De pre-commit hooks draaien ruff, bestandscontroles,
  zizmor, `uv lock` en pytest (`just lint` op alle bestanden). CI
  (`.github/workflows/ci.yml`) draait dezelfde hooks, de suite op Ubuntu en
  Windows, en een testbuild; `release.yml` draait de tests nogmaals vóór
  publicatie.

## Architectuur van de tooling

`tools/archi_tool/` is een uv-project met entrypoint `archi` (pyproject):

- `model.py`: laden, muteren en opslaan met lxml. Het formaat: alleen het
  rootelement zit in de archimate-namespace, de rest is unqualified;
  concepten dragen `xsi:type="archimate:..."`; relatietypes eindigen op
  `Relationship` (Amerikaanse spelling); bounds van geneste view-objecten
  zijn relatief aan hun parent. `remove` ruimt bij cascade ook
  view-objecten, connections en `targetConnections`-attributen op.
- `validate.py`: integriteitschecks plus conventiecheck tegen een
  conventies-doc (sectie "Property-keys", eventueel genummerd; telt alleen
  bullets die met een backticked key beginnen).
- `discovery.py`: vindt het modelbestand (`--model` > `[tool.archi] model` in
  `archi.toml`/`pyproject.toml`, omhoog gezocht > enig `.archimate` in de map)
  en de conventielijst (config > `conventies.md` naast het model > ingebouwde
  standaardset). Maakt de CLI onafhankelijk van een vaste repo-layout.
- `normalize.py`: load+save-roundtrip door de headless Archi CLI. Binary via
  env var `ARCHI_APP`, anders het eerste bestaande pad uit `ARCHI_CANDIDATES`
  (macOS, Windows machine- en user-scope, Linux), anders de gecachte engine.
  Ontbreekt alles, dan haalt `normalize` de engine automatisch op (tenzij
  `--no-download`).
- `engine.py`: haalt de Archi-distributie (MIT, gebundelde JRE, ~165 MB) op
  naar `~/.cache/archi-cli/<versie>/` en pakt hem uit; `ARCHI_VERSION` is
  gepind en het archief wordt tegen de SHA-1 uit het `SUMSSHA1`-bestand
  gecontroleerd. archi.io houdt alleen de nieuwste release online: staat de
  pin er niet meer, dan valt `resolve_release()` met een waarschuwing terug op
  de nieuwste release (ADR 0011). Aangeroepen door `archi setup` en door de
  auto-fetch in `normalize`. Zie ADR 0005.
- `views.py`: view-generatie met grid- of cluster-layout. `--root` selecteert
  een element plus zijn aggregatie/compositie-closure, `--related` voegt direct
  gerelateerde elementen toe (detailviews per element); het kolomaantal van de
  cluster-layout groeit mee met het aantal clusters.
- `render.py`: views naar Mermaid-markdown, met `accTitle`/`accDescr` voor
  toegankelijkheid en het ArchiMate-laagkleurenpalet (`LAYER_PALETTE`).
  `view_stems()` is de enige bron voor bestandsnamen van views (slug van de
  naam; bij een botsing krijgen alle betrokken views een id-suffix,
  onafhankelijk van de volgorde in het model). Alle links naar
  een view (index, view-referenties, slides) gaan via deze functie.
- `render_html.py`: views naar NLDD-gestileerde HTML met de layout uit het
  model, inclusief de ArchiMate-notatie-iconen per elementtype
  (`ICON_GLYPHS`, geometrie geport uit de Archi-broncode), notes, groups,
  view-referenties en bendpoints. Niet gerenderd: SketchModel- en
  CanvasModel-views, DiagramModelImage en custom kleuren/fonts uit Archi.
  Let op: NLDD-primitives zijn zelf al `light-dark()`-paren, dus
  nooit dubbel wikkelen. Diagram-canvas is bewust altijd licht.
  `diagram_canvas()` en `DIAGRAM_CSS` worden gedeeld met de slide-renderer.
- `render_slides.py`: decks (`decks/*.toml`, stdlib-`tomllib`) naar
  zelfstandige HTML-presentaties: één lineair verhaal per deck, geen
  overzichts- of menumechanismen. Slidetypes: title, section, view, text,
  bullets, closing. Deterministisch: de optionele datum op de titelslide is
  deckdata (letterlijk weergegeven), geen timestamps of absolute paden in de
  output. View-slides tekenen het echte diagram op een witte kaart binnen de
  slide (markerprefix `s<n>-` tegen dubbele SVG-ids); een `focus`-veld zoomt de
  camera op één element en dimt de rest (rect server-side berekend, animatie
  client-side).
- `links.py`: doorklik-links uit een links-bestand (`[tool.archi] links`):
  per bronplaat (bestandsnaam zonder extensie) elementnaam → relatief pad.
  Gebruikt door `render_html` (klikbare element-vakjes) en `render_slides`
  (met `../`-correctie); `validate` controleert de elementnamen, `render` de
  bestanden. Zie ADR 0010.
- `cli.py`: Typer-subcommands (getypeerde functies, `--model` als globale
  optie); mutaties slaan alleen op bij schone validatie.

Gegenereerde view-bestanden dragen een markercommentaar (eerste regel); alleen
bestanden met die marker worden overschreven of opgeruimd.

Docs en commit-berichten zijn Nederlandstalig; code en comments zijn Engels.
