# ADR 0005 — De Archi-engine ophalen in plaats van vereisen

- **Status**: geaccepteerd
- **Datum**: 2026-07-04

## Context

`archi normalize` draait de headless command-line-app van Archi, de canonieke
serializer. Tot nu toe zocht de tool een lokaal geïnstalleerde Archi
op vaste paden en faalde als die er niet was; normaliseren bleef daardoor
"lokale discipline". Voor een zelfstandig, publiceerbaar pakket (ADR 0004) is
dat te zwak: een nieuwe gebruiker of een CI-runner heeft geen Archi en kan dus
niet normaliseren.

Archi is MIT-gelicentieerd en cross-platform. De volledige distributie
(~165 MB, met een gebundelde OpenJDK 21, dus self-contained) staat op GitHub
releases onder `archimatetool/archi.io`, met een voorspelbaar URL-patroon per
versie. Er is geen los, kleiner headless-artefact.

## Besluit

1. **Ophalen, niet bundelen.** Het pakket bevat geen Archi-code. `engine.py`
   downloadt de distributie bij eerste gebruik naar een per-user cache
   (`~/.cache/archi-cli/<versie>/`, override via `ARCHI_CACHE`), pakt hem uit
   en wijst `normalize` naar de binary. De wheel blijft daardoor klein en de
   distributie licht (alleen onze EUPL-code plus `lxml` en `typer`).
2. **Auto-fetch met escape.** `normalize` haalt de engine automatisch op als
   er geen lokale Archi is; `--no-download` schakelt dat uit en faalt netjes
   (voor CI en luchtdichte omgevingen). `archi setup` haalt de engine expliciet
   op, bijvoorbeeld om een CI-cache te vullen. De bestaande zoekvolgorde
   (`ARCHI_APP` → vaste paden → `PATH`) gaat vóór de cache, zodat een lokaal
   geïnstalleerde Archi altijd wint.
3. **Gepinde versie, geverifieerd.** `ARCHI_VERSION` is vastgepind (nu 5.9.0)
   zodat de download deterministisch is. Na download wordt het archief tegen
   de SHA-1 uit het `SUMSSHA1`-bestand van de release gecontroleerd; een
   mismatch breekt de installatie af. Uitpakken weigert pad-traversal-entries.
4. **Attributie.** Een `NOTICE` vermeldt Archi (MIT, © Phil Beauvoir e.a.) en
   de gebundelde OpenJDK. Dat is de enige verplichting die MIT oplegt, en die
   geldt hier strikt genomen pas bij het ophalen, niet bij distributie.

## Afwegingen

- **Ophalen boven bundelen.** 165 MB in een wheel stoppen kan niet (PyPI-limiet
  100 MiB) en is onwenselijk; ophalen is het gangbare patroon voor zware,
  niet-Python-runtimes. De prijs is een eenmalige download en een
  netwerkafhankelijkheid, beperkt tot `normalize`.
- **Gepinde versie boven "altijd de laatste".** Deterministisch en
  reproduceerbaar weegt zwaarder dan automatisch meegroeien; de versie bump je
  bewust. De `archi.io`-releases-API geeft betrouwbaar alleen de laatste
  versie terug, dus pinnen gebeurt op het vaste URL-patroon.
- **macOS `.dmg`.** Linux (`.tgz`) en Windows (`.zip`) pakken triviaal uit;
  macOS levert alleen een `.dmg`, die we mounten met `hdiutil`, de `Archi.app`
  eruit kopiëren en weer losmaken.

## Gevolgen

- Nieuwe module `engine.py`; `normalize.py` kent de cache als extra zoekpad en
  doet auto-fetch. Nieuwe subcommando's `setup` en de vlag `normalize
  --no-download`.
- Nieuwe tests `test_engine.py` met een gemockte download; geen test raakt het
  netwerk of haalt de echte distributie op.
- Nieuw bestand `NOTICE`. `normalize` werkt nu op een schone machine zonder dat
  de gebruiker Archi installeert.
- Vervolg: publiceren op PyPI als `archi-cli` (A4), dan plugin en marketplace.
