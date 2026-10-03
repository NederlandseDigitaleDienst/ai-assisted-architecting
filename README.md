# archi-cli

[![checks](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/actions/workflows/ci.yml/badge.svg)](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/archi-cli.svg)](https://pypi.org/project/archi-cli/)
[![Python](https://img.shields.io/pypi/pyversions/archi-cli.svg)](https://pypi.org/project/archi-cli/)
[![licentie: EUPL-1.2](https://img.shields.io/badge/licentie-EUPL--1.2-blue.svg)](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/LICENSE)

Houd je ArchiMate-model bij zoals code. `archi-cli` is een command line tool
voor native [Archi](https://www.archimatetool.com/)-modellen: je bekijkt,
wijzigt en controleert een `.archimate`-bestand vanuit de terminal, en
genereert er views, webpagina's en presentaties uit. Elke wijziging wordt
gevalideerd voordat hij wordt opgeslagen, zodat het model nooit kapot raakt.
Dat maakt de tool geschikt om samen met een AI-assistent aan een model te
werken, met git als geheugen.

![Een gegenereerde presentatie die inzoomt op één capability](https://raw.githubusercontent.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/main/docs/img/slide-focus.png)

*Een slide uit het meegeleverde voorbeeld: de camera zoomt in op één
element en dimt de rest. Gegenereerd uit het model, zonder handwerk.*

## Wat het is, en wat niet

**Wel:**

- Een **command line tool** die het native Archi-formaat leest en schrijft. Het
  bestand blijft gewoon te openen en te bewerken in Archi.
- Een **vangnet**. Elke mutatie wordt eerst in het geheugen gevalideerd; bij een
  fout weigert de tool op te slaan. Ids blijven onveranderd.
- **Deterministisch.** Dezelfde invoer geeft dezelfde uitvoer, zodat diffs klein
  blijven en je de uitvoer in CI kunt controleren.
- Een set **skills voor Claude Code** die beschrijven hoe een AI-assistent via
  deze tool aan een model werkt.

**Niet:**

- **Geen vervanging van Archi.** Vrij modelleren op het canvas en de layout van
  een view fijnslijpen doe je in Archi. De tool en Archi werken op hetzelfde
  bestand en vullen elkaar aan.
- **Geen ArchiMate-validator.** `archi validate` controleert de integriteit van
  het bestand en je eigen conventies, niet of een relatie volgens de
  ArchiMate-specificatie is toegestaan.
- **Geen AI.** De tool zelf bevat geen AI en stuurt je model nergens heen. Alleen
  het eenmalig ophalen van de Archi-engine gebruikt het netwerk.
- **Geen officieel product of standaard.** Het is open source software in de
  bètafase, zonder garanties of ondersteuningsafspraken.

## Snel aan de slag

Je hebt [uv](https://docs.astral.sh/uv/) nodig; uv regelt zelf een passende
Python (3.12 of nieuwer).

```bash
uv tool install archi-cli
archi --version
```

Probeer het op het meegeleverde voorbeeld, een fictief model van een gemeente
die vergunningen verleent:

```bash
git clone https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting.git
cd ai-assisted-architecting/examples/vergunningverlening
archi stats                          # wat zit er in het model
archi show "Toetsen aan regels"      # één element met zijn relaties
archi render                         # views en slides naar views/
```

Open daarna `views/html/index.html` in je browser. De Mermaid-versies van de
views staan [hier op GitHub](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/examples/vergunningverlening/views/README.md) al
gerenderd.

Voor je eigen model: draai `archi` in de map met je `.archimate`-bestand, of
leg het vast in een `archi.toml` (zie [Configuratie](#configuratie)).

## Wat je ermee kunt

| Taak | Commando's |
| --- | --- |
| Inspecteren | `stats`, `list`, `show`, `tree` |
| Wijzigen | `add-element`, `add-relation`, `set-property`, `remove-property`, `set-documentation`, `rename`, `move`, `remove`, `set-model-name` |
| Views genereren | `add-view` met grid- of clusterlayout, geselecteerd op type, property, relatie of vanuit één element |
| Controleren | `validate` |
| Normaliseren | `normalize` |
| Publiceren | `render` (views) en `slides` (presentaties) |

`archi <commando> --help` toont alle opties. Een paar voorbeelden:

```bash
archi add-element --type Capability --name "Toezicht" --documentation "Naleving controleren."
archi add-relation --type Aggregation --source "Vergunningverlening" --target "Toezicht"
archi move "Toezicht" --subfolder "Gebied handhaving" --create-subfolder
archi add-view --name "Capabilities" --layout cluster --type Capability
archi remove "Toezicht" --cascade      # ook relaties en view-objecten
```

**Controleren.** `archi validate` vindt onder meer dubbele ids, relaties naar
elementen die niet bestaan, elementen in de verkeerde laagmap, kapotte views en
property-keys die niet in je conventielijst staan. Mutaties draaien dezelfde
controles automatisch.

**Normaliseren.** `archi normalize` laat Archi zelf het bestand opnieuw wegschrijven,
in zijn eigen canonieke vorm. Zo blijven git-diffs klein, of een wijziging nu
uit de tool of uit Archi komt. De Archi-engine haalt de tool bij het eerste
gebruik zelf op en controleert de download.

**Publiceren.** `archi render` zet elke view om naar Mermaid (dat GitHub direct
toont) en naar een webpagina met de layout en de ArchiMate-notatie uit het
model, gestileerd met het [NLDD Design System](https://github.com/NederlandseDigitaleDienst/design-system).
Een indexpagina toont alle views met een miniatuur.

![Een gegenereerde view met de layout uit het model](https://raw.githubusercontent.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/main/docs/img/view-dienst-platform.png)

**Presenteren.** Een deck in `decks/*.toml` beschrijft een lineair verhaal met
views uit het model, afgewisseld met tekst. `archi slides` maakt er een
zelfstandige HTML-presentatie van, met zoom-op-een-element, sprekersnotities en
volledig scherm. Zie [het voorbeelddeck](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/examples/vergunningverlening/decks/rondleiding.toml).

**Doorklikken.** Met een links-bestand worden elementen in de webpagina's
klikbaar naar een andere view of een ander bestand, bijvoorbeeld een diagram
dat je met eigen scripts maakt. Zie [ADR 0010](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/adr/0010-doorklikken-via-links-bestand.md).

![De indexpagina met alle views](https://raw.githubusercontent.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/main/docs/img/views-index.png)

## Configuratie

De tool zoekt het model in deze volgorde: de optie `--model <pad>` (vóór het
subcommando), de sleutel `model` in een `archi.toml` (in de werkmap of een map
erboven), of het enige `.archimate`-bestand in de werkmap.

```toml
# archi.toml
[tool.archi]
model = "model/architectuur.archimate"
conventions = "docs/conventies.md"   # toegestane property-keys
links = "links.toml"                 # doorkliks in de webpagina's
fonts = "system"                     # of "rijkssans", zie hieronder
```

Alle sleutels zijn optioneel. Dezelfde tabel mag ook in een `pyproject.toml`.

**Lettertype.** De webpagina's gebruiken standaard het systeemlettertype.
RijksSans is uitsluitend bedoeld voor publicaties van de Rijksoverheid en
partijen die in haar opdracht werken; valt jouw publicatie daaronder, zet dan
`fonts = "rijkssans"`.

## Werken met een AI-assistent

De skills `archi-model`, `archi-view` en `archi-slides` leren een AI-assistent
hoe hij via deze tool aan een model werkt: welke commando's, in welke
volgorde, en wanneer hij moet valideren en normaliseren. Installeer ze in
Claude Code als plugin:

```
/plugin marketplace add BureauArchitectuurDigitaleOverheid/ai-assisted-architecting
/plugin install archi-tools@archi-marketplace
```

De plugin brengt alleen de skills mee; het commando `archi` installeer je met
uv, zoals hierboven. De tool garandeert dat het model technisch klopt, niet dat
de architectuur klopt. Lees wijzigingen van een assistent na zoals je een pull
request van een collega naleest.

## Grenzen en bekende beperkingen

- **Alleen het native Archi-formaat** (`.archimate`). Het Open Group
  Exchange-formaat wordt niet gelezen of geschreven.
- **`normalize` heeft de Archi-engine nodig** (ongeveer 165 MB, eenmalig).
  Archi levert die voor macOS (Intel en Apple Silicon) en voor 64-bit x86 op
  Linux en Windows. Op andere platforms installeer je Archi zelf en wijs je hem
  aan met de omgevingsvariabele `ARCHI_APP`. Alle andere commando's werken
  zonder Archi.
- **Automatische layout is een startpunt.** `add-view` plaatst elementen in een
  raster of in clusters; bij grotere views schuif je in Archi nog wat bij.
- **Niet alles wordt gerenderd.** Sketch- en canvasviews, afbeeldingen en eigen
  kleuren en lettertypes uit Archi komen niet in de webpagina's.
- **De webpagina's laden het design system van een CDN** en hebben dus internet
  nodig om goed te tonen.
- **Uitvoer en meldingen zijn Nederlandstalig.**

## Disclaimer

Deze software wordt geleverd zoals hij is, zonder enige garantie; zie de
artikelen 7 en 8 van de [EUPL-1.2](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/LICENSE). De tool is in bètafase: tot versie
1.0 kunnen commando's en uitvoer nog veranderen. Elke wijziging die je moet
weten staat in de [changelog](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/CHANGELOG.md).

ArchiMate is een geregistreerd handelsmerk van The Open Group. Dit project is
onafhankelijk en niet verbonden aan The Open Group of het Archi-project.

## Meedoen

Bijdragen zijn welkom: lees [CONTRIBUTING.md](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/CONTRIBUTING.md) voor de
werkwijze en de [gedragscode](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/CODE_OF_CONDUCT.md). Een beveiligingsprobleem meld
je volgens [SECURITY.md](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/SECURITY.md), niet in een openbaar issue.
Beslissingen over de opzet van de tool staan als ADR's in [`adr/`](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/tree/main/adr/).

## Licentie

[EUPL-1.2](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/LICENSE). Ontwikkeld door de Nederlandse Digitale Dienst. Archi
zelf valt onder de MIT-licentie; zie [NOTICE](https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/blob/main/NOTICE).
