# ADR 0007 — De repo als Claude Code plugin en marketplace

- **Status**: geaccepteerd
- **Datum**: 2026-07-04

## Context

De skills (`archi-model`, `archi-view`, `archi-slides`) stonden in
`.claude/skills/` en laadden alleen voor wie deze repo opende in Claude Code.
Nu `archi-cli` op PyPI staat (ADR 0006), kan de tooling ook buiten deze repo
gebruikt worden. Om de skills mee te distribueren, maken we de repo een
installeerbare Claude Code plugin, met een marketplace die ernaar verwijst.

## Besluit

1. **Skills blijven in `.claude/skills/`.** Claude Code laadt project-skills
   automatisch uit `.claude/skills/`, niet uit een `skills/` in de repo-root.
   Ze daar weghalen zou het lokale laden breken, dus ze blijven staan.
2. **Plugin-manifest** `.claude-plugin/plugin.json`: plugin `archi-tools`, met
   author, repository, license en keywords, plus een `skills`-veld dat naar
   `./.claude/skills/` wijst. Het `skills`-veld voegt custom map(pen) toe aan
   de plugin-scan, zodat de plugin dezelfde skills distribueert die lokaal al
   laden. Eén bron, twee doelen, geen duplicatie en geen symlinks (die op
   Windows onbetrouwbaar zijn).
3. **Marketplace-manifest** `.claude-plugin/marketplace.json`: marketplace
   `archi-marketplace` met één plugin-entry die met `source: "./"` naar de repo-root
   wijst. Eén repo is dus tegelijk de plugin én de marketplace die hem aanbiedt.
4. **Skills werken met het geïnstalleerde `archi`.** De commando's in de skills
   gebruiken `archi` (na `uv tool install archi-cli` overal beschikbaar), met
   een notitie dat binnen deze repo `uv run archi ...` en de `just`-taken de
   lokale varianten zijn. De skills beschrijven de werkwijze; de repo-
   specifieke stukken (het ADO-model, de PR-workflow) blijven als context
   staan, want ze schaden het losse gebruik niet.

## Installatie voor gebruikers

```
/plugin marketplace add BureauArchitectuurDigitaleOverheid/ai-assisted-architecting
/plugin install archi-tools@archi-marketplace
```

De plugin brengt de drie skills mee. Voor het `archi`-commando zelf: `uv tool
install archi-cli`.

## Afwegingen

- **`.claude/skills/` behouden + `skills`-manifestveld.** Skills verplaatsen
  naar `skills/` in de repo-root (wat een plugin default scant) zou het
  automatische lokale laden breken: Claude Code scant daarvoor alleen
  `.claude/skills/`. Het `skills`-veld in `plugin.json` lost dat op door
  `.claude/skills/` áán de plugin-scan toe te voegen, zodat één bron beide
  doelen dient. Symlinks (het alternatief) zijn op Windows onbetrouwbaar en de
  repo test op Windows.
- **Skills niet volledig generiek gemaakt.** Ze verwijzen nog naar dit project
  (model, conventies, workflow). Dat is bewust: het zijn werkwijze-skills, geen
  kale commando-referenties. De commando's zelf werken overal.

## Gevolgen

- Nieuwe map `.claude-plugin/` met plugin- en marketplace-manifest;
  `.claude/skills/` blijft de bron van de skills en laadt lokaal zoals eerst.
- De README beschrijft de plugin-installatie.
- De skills gebruiken het `archi`-commando; binnen de repo blijven `uv run
  archi` en de `just`-taken werken.
