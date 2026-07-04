# ADR 0006 — De archi-CLI publiceren op PyPI als `archi-cli`

- **Status**: geaccepteerd
- **Datum**: 2026-07-04

## Context

Na ADR 0004 (CLI zelfstandig) en 0005 (engine ophalen) is `archi` een tool die
op elk model werkt en de Archi-engine zelf regelt. Om het buiten deze repo
bruikbaar te maken, moet het installeerbaar zijn met één commando. Dit ADR legt
de publicatie vast.

## Besluit

1. **Distributienaam `archi-cli`** op de publieke PyPI. De importnaam blijft
   `archi_tool` en het commando blijft `archi`; alleen de naam waaronder je
   installeert verandert. Op PyPI gecheckt en vrij; `archi` zelf was bezet
   (een archive-library). Installatie: `uv tool install archi-cli`, waarna het
   commando `archi` op `$PATH` staat.
2. **Publiek, niet privé.** Past bij een open (EUPL-1.2) overheidsexperiment en
   is het makkelijkst installeerbaar. Geen bureau-index of GitHub-Releases-only.
3. **Trusted Publishing (OIDC), geen API-token.** De release-workflow
   (`.github/workflows/release.yml`) draait op een versie-tag (`v*`), bouwt
   sdist en wheel met `uv build`, en publiceert met
   `pypa/gh-action-pypi-publish`. PyPI vertrouwt de workflow op basis van repo +
   workflow-naam; er staat geen secret in de repo. De workflow controleert dat
   de tag met de versie in `pyproject.toml` overeenkomt voordat hij bouwt.
4. **Het pakket blijft in deze repo.** Skills, tool, voorbeeldmodel en tests
   leven en testen samen; één changelog, geen versie-sync. Afsplitsen naar een
   eigen repo is pas zinvol als er een tweede model of beheerder is die de tool
   zonder deze repo wil onderhouden (de beslisregel uit het plan). De code is er
   klaar voor (modules importeren alleen elkaar), dus afsplitsen kan later
   goedkoop.

## Handmatige stap (eenmalig, door de beheerder)

Trusted Publishing vereist dat het PyPI-project de GitHub-workflow eenmalig
vertrouwt. Op https://pypi.org, na inloggen:

1. Publiceer eerst handmatig een eerste release, óf maak het project aan via de
   "pending publisher"-route (Account → Publishing) zonder dat het project al
   bestaat.
2. Koppel als Trusted Publisher: owner `BureauArchitectuurDigitaleOverheid`,
   repository `ai-assisted-architecting`, workflow `release.yml`, environment
   `pypi`.
3. Daarna publiceert elke tag `vX.Y.Z` (die met de pyproject-versie matcht)
   automatisch.

Dit is de enige stap die niet in het repo geautomatiseerd is; er komt bewust
geen token in een secret store.

## Gevolgen

- `pyproject.toml` draagt volledige PyPI-metadata (naam, description met de
  *ar·cli·mate*-tagline, keywords, classifiers, urls, readme); sdist bundelt
  `README.md`, `LICENSE` en `NOTICE`.
- Nieuwe workflow `release.yml`. De README beschrijft de losse installatie
  bovenaan.
- Releasen: versie bumpen in `pyproject.toml`, taggen `vX.Y.Z`, pushen; de
  workflow doet de rest.
- Vervolg: de Claude Code plugin (B) en marketplace (C) bouwen op dit pakket
  voort.
