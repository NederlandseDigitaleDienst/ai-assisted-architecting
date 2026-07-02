# AI-assisted architecting

Experiment: een ArchiMate-model in **native Archi-formaat** als bron van
waarheid, bijgehouden via AI-assistentie met deterministische tooling, en
zonder import-stap te openen in Archi.

## Hoe het werkt

`models/ado.archimate` is de bron. Wijzigen kan op twee gelijkwaardige
manieren: via de CLI (`uv run archi ...`, meestal aangestuurd door een
AI-sessie) of gewoon in de Archi-GUI. In beide gevallen geldt vóór commit:
`just validate` (integriteitschecks) en `just normalize` (canonieke
serialisatie door headless Archi, zodat diffs klein en reviewbaar blijven).

## Structuur

```
models/                      Het model (bron van waarheid, 1 bestand)
views/                       Gerenderde views (Mermaid, gegenereerd — zie ADR 0002)
docs/                        Norm: conventies.md, spelregels.md
adr/                         Architectuurbeslissingen
tools/archi_tool/            Deterministische CLI (uv, Python, lxml)
tests/                       pytest-suite met klein fixture-model
.claude/skills/              AI-procedures: archi-model, archi-view
```

De views uit het model zijn op twee manieren te bekijken zonder Archi:
als Mermaid-diagram in [`views/`](views/) (rendert direct op GitHub), en
als NLDD-gestileerde HTML in [`views/html/`](views/html/) die de layout
uit het model pixelgetrouw volgt — lokaal te openen met
`open views/html/index.html`.

## Aan de slag

Vereist [uv](https://docs.astral.sh/uv/), [just](https://just.systems/) en
[Archi](https://www.archimatetool.com/) (voor normalisatie; pad instelbaar
via env var `ARCHI_APP`).

```bash
just setup       # venv + pre-commit hooks
just stats       # wat zit erin
just open        # openen in Archi
uv run archi --help
```

## Herkomst

Het seedmodel is de ADO-export uit het zusterexperiment
[`ADO-architectuurmodel-experiment`](https://github.com/BureauArchitectuurDigitaleOverheid/ADO-architectuurmodel-experiment)
(JSON-bron met AEF-export). Dit repo verkent de omgekeerde aanpak; de
afweging staat in `adr/0001-archimate-als-bron.md`.
