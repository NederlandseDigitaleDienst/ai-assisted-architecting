# Bijdragen

Bijdragen zijn welkom. Deze repo bevat twee dingen: de `archi-cli`-tool (Python)
en de Claude Code skills. Het model waarop de tool ontstond woont in een eigen
repo; daar draag je op een andere manier aan bij (zie de README daar).

## Opzetten

Je hebt [uv](https://docs.astral.sh/uv/) en [just](https://just.systems/) nodig.
De rest regelt `uv`.

```bash
git clone git@github.com:BureauArchitectuurDigitaleOverheid/ai-assisted-architecting.git
cd ai-assisted-architecting
just setup     # venv, dependencies en de pre-commit hook
just test      # de testsuite
```

De testsuite draait op een klein fixture-model in `tests/fixtures/`, niet op een
echt model. Je hebt dus geen `.archimate`-bestand nodig om de tool te
ontwikkelen.

## Werkwijze

- Werk op een branch, open een pull request. Push niet naar `main`.
- De pre-commit hooks draaien ruff, een paar bestandscontroles, zizmor (op de
  workflows), `uv lock` en `pytest`. `just lint` draait ze allemaal op alle
  bestanden. CI draait dezelfde hooks, plus de tests op Ubuntu (Python 3.12 en
  3.14) en Windows, en een testbuild van het pakket.
- Commit-berichten en documentatie zijn Nederlandstalig; code en comments zijn
  Engels. Een Dutch domeinterm zonder goede Engelse tegenhanger
  (`OrganisatieEenheid`, `bewindspersoon`) mag blijven staan.
- Een nieuwe check in `validate.py` hoort een test te krijgen die het
  fixture-model gericht corrumpeert en de foutmelding controleert.
- Structurele beslissingen leg je vast in een ADR in `adr/`.

## De code

`tools/archi_tool/` is een uv-project met entrypoint `archi`. De opbouw en de
formaatdetails van het `.archimate`-formaat staan in `CLAUDE.md` onder
"Architectuur van de tooling". Kort:

- `model.py` laadt, muteert en bewaart met lxml.
- `validate.py` doet de integriteitschecks.
- `discovery.py` vindt het model en de conventielijst.
- `render.py`, `render_html.py`, `render_slides.py` doen de views en slides.
- `normalize.py` en `engine.py` draaien en beheren de headless Archi-engine.
- `cli.py` is de Typer-laag.

## De skills

De skills staan in `.claude/skills/`. Ze beschrijven de werkwijze en roepen het
`archi`-commando aan. Houd ze generiek: gebruik placeholders in plaats van
namen uit een specifiek model. Verandert een CLI-flag, werk dan de skill in
dezelfde PR bij, zodat de tekst en de tool synchroon blijven.

## Een release maken

Alleen bij een bewuste release, en alleen door een maintainer. Bump de versie in
`pyproject.toml`, merge dat naar `main`, en tag:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

De workflow bouwt en publiceert naar PyPI via Trusted Publishing. De volledige
procedure staat in `CLAUDE.md` onder "Publiceren naar PyPI".

## Licentie

Door bij te dragen ga je akkoord dat je bijdrage onder de
[EUPL-1.2](LICENSE) valt, net als de rest van de repo.
