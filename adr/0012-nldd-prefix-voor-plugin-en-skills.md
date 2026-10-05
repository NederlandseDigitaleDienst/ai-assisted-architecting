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
3. Deze repository heeft geen eigen marketplace meer. De plugin staat in de
   marketplace van de NLDD, `NederlandseDigitaleDienst/ai-plugins`, en installeren
   gaat met `/plugin install nldd-archi@nldd`. De entry daar wijst met een
   GitHub-bron naar deze repository. Daarvoor volgt de plugin de eisen van die
   marketplace: een manifest voor Claude Code en voor Cursor met dezelfde naam,
   beschrijving en versie, en de skills in `skills/` in de root.
4. Het pakket op PyPI blijft `archi-cli` en het commando blijft `archi`. Die
   namen staan in scripts, CI en documentatie van gebruikers, en het voorvoegsel
   voegt daar niets toe.

## Gevolgen

- Wie de plugin had, verwijdert de oude marketplace, voegt die van de NLDD toe
  en installeert `nldd-archi@nldd`. Dat moest door de verhuizing toch al.
- In deze repository laden de skills niet meer als projectskills uit
  `.claude/skills/`. `.claude/settings.json` zet daarom de plugin uit de
  marketplace van de NLDD aan, zodat Claude Code hem bij het openen aanbiedt;
  een skill-wijziging probeer je uit met `claude --plugin-dir .`.
- De lange vorm van een skillnaam wordt `nldd-archi:nldd-archi-model`. Een
  assistent die zelf een skill kiest, merkt er niets van.
- Projecten die de plugin in hun `.claude/settings.json` hebben aangezet,
  passen `enabledPlugins` aan naar `nldd-archi@nldd`.
