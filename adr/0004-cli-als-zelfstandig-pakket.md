# ADR 0004 — De archi-CLI als zelfstandig, herbruikbaar pakket

- **Status**: geaccepteerd
- **Datum**: 2026-07-04

## Context

De `archi`-CLI in `tools/archi_tool` was geschreven voor dit ene repo. Twee
aannames zaten hardcoded in `cli.py`: het modelpad (`models/ado.archimate`) en
de vindplaats van de conventielijst (`<model>/../../docs/conventies.md`). De
CLI draaide daardoor alleen binnen een clone van deze repo, met de project-venv
en het model op een vast pad. Dat blokkeert hergebruik: een ander team met een
eigen `.archimate`-model, of een CI-pipeline in een ander repo, kon de tool
niet zonder aanpassing gebruiken.

De ambitie is de tool te publiceren als zelfstandig pakket (`archi-cli` op
PyPI, commando `archi`), en er later een Claude Code plugin en marketplace
omheen te leggen. Deze ADR legt de eerste stap vast: de CLI context-onaf-
hankelijk maken en de commandolaag herbouwen.

## Besluit

1. **Model- en conventie-discovery** vervangen de hardcoded paden
   (`discovery.py`). Het model wordt gevonden via, in volgorde: een expliciete
   `--model`, `[tool.archi] model` in `archi.toml`/`pyproject.toml` (omhoog
   gezocht vanaf de werkmap), of het enige `.archimate`-bestand in de werkmap.
   Geen of meerdere kandidaten geven een duidelijke fout in plaats van een
   stille ADO-aanname. De conventielijst komt uit config, anders uit
   `docs/conventies.md` naast het model, anders uit een **ingebouwde
   standaardset** zodat de property-key-check ook zonder projectlijst zinvol
   blijft. Deze repo legt zijn keuzes vast in `archi.toml`, dus commando's
   zonder `--model` blijven op `models/ado.archimate` werken.
2. **De CLI is herschreven van argparse naar Typer.** De commandologica
   (`model.py`, `validate.py`, `views.py`, de renderers) blijft ongewijzigd;
   alleen `cli.py` verandert. Typer levert shell-completion (bash, zsh, fish,
   PowerShell), Rich-help en -foutopmaak, en getypeerde commando's. Typer
   vendort Click sinds 0.26, dus de enige toegevoegde runtime-dependency is
   `typer` (met Rich/shellingham); `lxml` blijft de andere.
3. **Renders blijven deterministisch.** Discovery kan een absoluut modelpad
   opleveren (via `archi.toml`); `display_model_path` in `render.py` toont het
   pad relatief aan de werkmap, zodat de gegenereerde views byte-identiek
   blijven ongeacht de machine. Dit is met een regressietest geborgd.

## Afwegingen

- **Typer boven argparse.** Voor een intern projectscript woog argparse-met-
  één-dependency het zwaarst. Voor een publiek pakket telt de developer-
  experience wél: completion en nette help maken het verschil tussen "correct"
  en "af". De extra dependency is bewust en verdedigbaar.
- **Discovery boven een verplichte `--model`.** Een verplichte vlag was
  simpeler, maar breekt de ergonomie voor het veelvoorkomende geval (één model
  in de repo). Config-discovery houdt dat geval kort en maakt de tool toch
  generiek.
- **`--model` blijft een globale optie** (vóór het subcommando), zoals git dat
  met veel vlaggen doet. Consistent en clean; de skills en README vermelden de
  plaatsing.

## Gevolgen

- Nieuwe modules `discovery.py`; nieuwe tests `test_discovery.py`,
  `test_cli_typer.py`, `test_render_paths.py`. `test_cli.py` blijft de CLI
  end-to-end dekken en draait ongewijzigd op de Typer-CLI.
- Nieuw bestand `archi.toml` in de repo-root legt model en conventielijst vast.
- `typer` toegevoegd aan de dependencies; `docs/conventies.md` blijft de bron
  voor deze repo, met de ingebouwde set als vangnet elders.
- Vervolgstappen (engine ophalen zodat `normalize` overal werkt, publiceren op
  PyPI, plugin, marketplace) staan los van deze ADR en volgen later.
