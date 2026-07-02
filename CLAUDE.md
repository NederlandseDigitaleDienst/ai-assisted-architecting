# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Wat dit repo is

Experiment "AI-assisted architecting": een ArchiMate-model in **native
Archi-formaat** (`models/model.archimate`) als bron van waarheid, direct te
openen in Archi én via Claude te manipuleren met de deterministische CLI in
`tools/archi_tool`. Geen conversielaag; zie `adr/0001-archimate-als-bron.md`.

## Commando's

```bash
just setup            # eenmalig: uv sync + pre-commit install
uv run archi stats|list|show|tree          # inspectie
uv run archi add-element|add-relation|set-property|rename|remove ...
uv run archi add-view --name ... --layout grid|cluster
just validate         # integriteitschecks (ook pre-commit hook)
just normalize        # canonieke serialisatie via headless Archi (~15 s)
just test             # pytest
just open             # model openen in Archi
```

## Harde regels

- **Bron van waarheid**: `models/model.archimate`. AEF-exports, afbeeldingen
  en `.bak`-bestanden zijn afgeleid en gitignored.
- **Nooit handmatig XML bewerken** in het modelbestand — alle mutaties via de
  `archi`-CLI (valideert automatisch, weigert opslaan bij fouten). Voor
  procedures: skills `archi-model` en `archi-view`.
- Ids (`id-<uuid4>`) zijn onveranderlijk; de tooling genereert nieuwe.
- Vóór elke commit die het model raakt: `just validate` én `just normalize`
  (Archi is de canonieke serializer; dit houdt diffs klein).
- Nieuwe property-keys eerst vastleggen in `docs/conventies.md` §3 — de
  validator waarschuwt op onbekende keys. Structurele beslissingen in `adr/`.
- **Eén schrijver tegelijk** op het modelbestand: geen parallelle branches
  met modelwijzigingen (spelregels §4 — XML merget slecht).
- Wijzigingen via branch → commit → PR (`docs/spelregels.md`). Semantische
  Nederlandstalige commit-berichten.

## Architectuur van de tooling

`tools/archi_tool/` (uv-project, entrypoint `archi` in pyproject):
`model.py` (laden/muteren/opslaan met lxml; het formaat: root in de
archimate-namespace, verder unqualified elementen, concepten via
`xsi:type="archimate:..."`, relatietypes eindigen op `Relationship`),
`validate.py` (integriteitschecks + conventiecheck tegen
`docs/conventies.md`), `normalize.py` (load+save-roundtrip door de headless
Archi CLI; pad via env var `ARCHI_APP`, default `/Applications/Archi.app`),
`views.py` (grid- en cluster-layout, geport uit het ADO-exportscript),
`cli.py` (argparse-subcommands, muteert alleen bij schone validatie).

Alles in dit repo is Nederlandstalig (modelinhoud, docs, commits); code en
comments zijn Engels.
