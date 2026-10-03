# AGENTS.md

Instructies voor AI-codeassistenten (en mensen) die aan deze repository
werken. Gebruikersdocumentatie staat in [README.md](README.md), de werkwijze
voor bijdragers in [CONTRIBUTING.md](CONTRIBUTING.md).

## Wat deze repo is

`archi-cli`: een deterministische command line tool (`tools/archi_tool/`,
commando `archi`) voor het inspecteren, muteren, valideren en renderen van
native Archi-modellen (`.archimate`), plus de skills (`.claude/skills/`) die
beschrijven hoe een AI-assistent via de tool aan een model werkt.

- De tool is generiek. Er zit geen echt model in deze repo; de tests draaien
  op `tests/fixtures/klein-model.archimate` en er is een voorbeeld in
  `examples/vergunningverlening/`.
- Gepubliceerd op PyPI als `archi-cli` (importnaam `archi_tool`). De repo is
  tegelijk een Claude Code plugin (`archi-tools`) en marketplace
  (`archi-marketplace`), via `.claude-plugin/`.
- Uitgebracht door de Nederlandse Digitale Dienst onder de EUPL-1.2.

## Omgeving opzetten

```bash
just setup        # uv sync + pre-commit install
```

Ga er niet van uit dat de omgeving compleet is. Ontbreekt iets, installeer het
dan zelf in plaats van de gebruiker ernaartoe te sturen:

- **uv** (`command -v uv`, op Windows `where.exe uv`): macOS/Linux
  `curl -LsSf https://astral.sh/uv/install.sh | sh` of `brew install uv`;
  Windows `winget install --id astral-sh.uv -e`. uv regelt zelf Python 3.12+.
- **just**: macOS `brew install just`, Windows `winget install --id Casey.Just -e`,
  Linux via de packagemanager.
- **Venv of dependencies** (`.venv/` ontbreekt of imports falen): `uv sync`.
- **Pre-commit hooks** (`.git/hooks/pre-commit` ontbreekt): `uv run pre-commit install`.
- **Archi** is alleen nodig voor `normalize`; de tool haalt de engine zelf op
  (`archi setup`). Alle andere commando's werken zonder Archi.

Gebruik altijd `uv run ...` voor Python; installeer niets met een globale pip.

## Commando's

```bash
just test         # pytest, de hele suite
just lint         # alle pre-commit hooks op alle bestanden, zoals CI
just demo         # de CLI op het fixture-model
just build        # uv build + twine check, vóór een release

uv run pytest tests/test_model.py::test_remove_cascade_cleans_views_and_relations
uv run archi --model tests/fixtures/klein-model.archimate stats
```

De CLI vindt het model via `--model <pad>` (vóór het subcommando), via
`[tool.archi] model` in een `archi.toml` of `pyproject.toml` (omhoog gezocht),
of als het enige `.archimate`-bestand in de werkmap.

## Codestijl en conventies

- **Taal.** Code, identifiers en comments in het Engels. Gebruikersmeldingen,
  documentatie, commit-berichten en PR-beschrijvingen in het Nederlands.
  Nederlandse domeintermen zonder goede Engelse tegenhanger mogen blijven.
- **Opmaak.** ruff format (regellengte 88) en ruff lint met regels E, F, W, B
  en I. De hooks controleren dat; draai `just lint` vóór je commit.
- **Afhankelijkheden.** Alleen `lxml` en `typer` als runtime-dependency. Een
  nieuwe dependency vraagt om een goede reden en een vermelding in de PR.
- **Determinisme.** Gegenereerde uitvoer bevat geen timestamps, absolute paden
  of willekeurige volgordes. Dezelfde invoer geeft byte voor byte dezelfde
  uitvoer.
- **Veilig XML parsen.** Modelbestanden zijn onbetrouwbare invoer; laad ze
  alleen via `ArchiModel`, dat een parser zonder DTD's, entities of netwerk
  gebruikt (`model.safe_parser()`).

## Testen

- Tests werken op een kopie van het fixture-model via de fixtures `model` en
  `model_path` in `tests/conftest.py`.
- Een nieuwe check in `validate.py` krijgt een test die het fixture-model
  gericht beschadigt en de foutmelding controleert.
- Geen test raakt het netwerk. Downloads en HTTP worden gemonkeypatcht (zie
  `tests/test_engine.py`).
- Het voorbeeld in `examples/vergunningverlening/` moet valideren en de
  gecommitte Mermaid-views moeten actueel zijn (`tests/test_example.py`). Pas
  je de renderer aan, draai dan `archi render` in die map en commit de views.
- CI draait de suite op Ubuntu (Python 3.12 en 3.14) en Windows. Houd paden en
  regeleinden platformonafhankelijk.

## Architectuur

- `model.py`: laden, muteren en opslaan met lxml. Alleen het rootelement zit in
  de archimate-namespace, de rest is unqualified; concepten dragen
  `xsi:type="archimate:..."`; relatietypes eindigen op `Relationship`; bounds
  van geneste view-objecten zijn relatief aan hun parent. `remove --cascade`
  ruimt ook view-objecten, connections en `targetConnections` op.
- `validate.py`: integriteitschecks (ids, relatie-eindpunten, mapplaatsing,
  view-integriteit, botsende viewbestandsnamen) plus de conventiecheck op
  property-keys en de controle van het links-bestand.
- `discovery.py`: vindt model, conventielijst, links-bestand en fontkeuze uit
  `[tool.archi]`. Maakt de CLI onafhankelijk van een vaste repo-layout.
- `normalize.py`: load-save-roundtrip door de headless Archi-CLI. Binary via
  `ARCHI_APP`, anders een bekende installatielocatie, anders de gecachte engine;
  ontbreekt alles, dan wordt de engine opgehaald (tenzij `--no-download`).
- `engine.py`: haalt Archi op naar `~/.cache/archi-cli/<versie>/`. De versie is
  gepind (`ARCHI_VERSION`); verdwijnt die van archi.io, dan valt de tool met een
  waarschuwing terug op de nieuwste release. Elke download wordt geverifieerd
  tegen het checksumbestand van de release (`SHA256.txt` of het oudere
  `SUMSSHA1`) of anders tegen de upload-digest van GitHub. Zie ADR 0005 en 0011.
- `views.py`: view-generatie met grid- of clusterlayout; `--root` en
  `--related` voor detailviews per element.
- `render.py`: views naar Mermaid-markdown, met `accTitle`/`accDescr`.
  `view_stems()` is de enige bron voor bestandsnamen van views; alle links naar
  een view lopen daarlangs.
- `render_html.py`: views naar HTML met het NLDD Design System
  (`NLDD_VERSION`), met de layout en ArchiMate-notatie uit het model. Standaard
  het systeemfont; RijksSans alleen met `fonts = "rijkssans"`. NLDD-kleuren zijn
  al `light-dark()`-paren: nooit opnieuw inpakken. Het diagramcanvas is bewust
  altijd licht.
- `render_slides.py`: decks (`decks/*.toml`) naar zelfstandige
  HTML-presentaties; slidetypes title, section, view, text, bullets, closing.
- `links.py`: doorkliks uit een links-bestand (ADR 0010).
- `cli.py`: Typer-subcommando's; mutaties slaan alleen op bij een schone
  validatie.

Gegenereerde bestanden beginnen met een markercommentaar; alleen bestanden met
die marker worden overschreven of opgeruimd. Structurele beslissingen staan in
`adr/`.

## Werkwijze voor wijzigingen

- Werk op een branch vanaf een verse `origin/main`; open een pull request.
  Push nooit direct naar `main`.
- Commit-berichten: Nederlands, gebiedende wijs in de titel ("Voeg ... toe"),
  met in de body waarom de wijziging nodig is.
- Werk `CHANGELOG.md` bij onder **Unreleased** voor elke wijziging die een
  gebruiker merkt.
- Verandert een CLI-optie, werk dan in dezelfde PR de skills, de README en dit
  bestand bij.
- Een structurele beslissing krijgt een ADR in `adr/`.

## Releasen

Alleen op verzoek van een maintainer; een PyPI-versie is onomkeerbaar.

1. Verhoog de versie volgens [SemVer](https://semver.org/lang/nl/) in
   `pyproject.toml`, `.claude-plugin/plugin.json`, de `archi-cli`-regel in
   `uv.lock` en `softwareVersion` in `publiccode.yml` (zet daar ook
   `releaseDate`). `scripts/check_release.py` bewaakt in CI dat ze gelijk zijn.
2. Zet in `CHANGELOG.md` de inhoud van **Unreleased** onder een nieuwe kop
   `## [X.Y.Z] - JJJJ-MM-DD`.
3. Merge via een PR, wacht tot CI op `main` groen is, en tag:
   `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. `release.yml` controleert tag, versie en changelog, draait de tests, bouwt,
   publiceert via PyPI Trusted Publishing (geen tokens in de repo) en maakt een
   GitHub Release met de changelogsectie als tekst.

## Grenzen

**Altijd:** valideren na een modelwijziging, tests draaien vóór een commit,
`uv` gebruiken voor Python.

**Eerst vragen:** een nieuwe runtime-dependency, een wijziging aan de
release-workflow, het taggen of publiceren van een versie, en alles wat de
uitvoer van bestaande gebruikers zichtbaar verandert.

**Nooit:**

- XML in een modelbestand met de hand bewerken. Alle mutaties gaan via de
  `archi`-CLI, die valideert en weigert op te slaan bij fouten. Gebruik daarvoor
  de skills `archi-model`, `archi-view` en `archi-slides`.
- Ids (`id-<uuid4>`) wijzigen; de tooling maakt nieuwe aan.
- Hooks overslaan (`--no-verify`) of secrets, tokens en persoonsgegevens
  committen.
- Een test aanpassen zodat hij slaagt zonder het onderliggende probleem op te
  lossen.
