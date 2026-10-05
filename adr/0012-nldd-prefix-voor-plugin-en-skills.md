# ADR 0012: Plugin en skills krijgen het voorvoegsel nldd-

- **Status**: geaccepteerd
- **Datum**: 2026-10-05
- **Wijzigt**: ADR 0007 en ADR 0008 (namen van plugin en marketplace)

## Context

De repository is verhuisd naar de GitHub-organisatie van de Nederlandse
Digitale Dienst en wordt openbaar. Op termijn hoort de plugin in de
marketplace van de NLDD (`NederlandseDigitaleDienst/ai-plugins`), naast
`nldd-design-system`. Daar dragen plugins en skills het voorvoegsel `nldd-`,
zodat een gebruiker in een lijst met skills ziet waar ze vandaan komen. De
oude namen (`archi-tools`, `archi-marketplace`, `archi-model`) zeiden dat niet,
en `archi-` alleen botst makkelijk met andere ArchiMate-gereedschappen.

## Besluit

1. De plugin heet `nldd-archi`, met als weergavenaam *NLDD Archi*.
2. De skills heten `nldd-archi-model`, `nldd-archi-view` en `nldd-archi-slides`.
3. De marketplace in deze repository heet ook `nldd-archi`. Installeren gaat met
   `/plugin install nldd-archi@nldd-archi`. Komt de plugin in de marketplace van
   de NLDD, dan wordt dat `nldd-archi@nldd`; de entry daar wijst met een
   GitHub-bron naar deze repository.
4. Het pakket op PyPI blijft `archi-cli` en het commando blijft `archi`. Die
   namen staan in scripts, CI en documentatie van gebruikers, en het voorvoegsel
   voegt daar niets toe.

## Gevolgen

- Wie de plugin had, voegt de marketplace opnieuw toe en installeert
  `nldd-archi`. Dat moest door de verhuizing toch al.
- De lange vorm van een skillnaam wordt `nldd-archi:nldd-archi-model`. Een
  assistent die zelf een skill kiest, merkt er niets van.
- Projecten die de plugin in hun `.claude/settings.json` hebben aangezet,
  passen `enabledPlugins` aan naar `nldd-archi@nldd-archi`.
