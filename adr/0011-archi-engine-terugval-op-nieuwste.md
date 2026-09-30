# ADR 0011: Terugvallen op de nieuwste Archi-release als de pin verdwijnt

- **Status**: geaccepteerd
- **Datum**: 2026-09-30
- **Wijzigt**: ADR 0005 (gepinde versie)

## Context

ADR 0005 pinde de Archi-engine op een vaste versie en haalde die op via een
vast URL-patroon op `archimatetool/archi.io`. Die repo houdt echter alleen de
nieuwste release online. Toen Archi 5.10.0 uitkwam (3 september 2026),
verdween 5.9.0, en gaf `archi setup` een 404. Daarmee faalde ook de
auto-fetch in `normalize` voor iedereen zonder lokale Archi-installatie, en
dat gold ook voor de net gepubliceerde 0.2.0.

Het tagformaat veranderde tegelijk: `5.9.0` werd `5.10_0`, terwijl de
bestandsnamen `5.10.0` bleven gebruiken.

De wekelijkse `engine-e2e` faalde sinds 7 september, maar niemand zag het:
een mislukte geplande run gaf alleen een e-mail aan wie de cron het laatst
wijzigde.

## Besluit

1. **De pin blijft de voorkeur.** `ARCHI_VERSION` staat nu op 5.10.0 en wordt
   als eerste geprobeerd, onder beide tagformaten (`5.10.0` en `5.10_0`).
2. **Terugval op de nieuwste release.** Staat de gepinde versie niet meer
   online, dan bepaalt `engine.py` de nieuwste release via de redirect van
   `/releases/latest` (geen API-aanroep, dus geen rate limit) en haalt die op,
   met een waarschuwing. `normalize` blijft zo werken tot iemand de pin
   ophoogt.
3. **Checksum verplicht.** Het `SUMSSHA1`-bestand wordt vóór de download
   opgehaald en dient tegelijk als bestaanscontrole. Daarmee wordt elke
   download geverifieerd; voorheen werd verificatie stil overgeslagen als het
   checksumbestand niet op te halen was.

   Dat bestand kan zelf fout zijn: voor 5.10.0 noemt het een verouderde hash
   voor de Windows-zip (de lijst is aangemaakt vóór de zip werd geüpload). Bij
   een mismatch vergelijkt `engine.py` de download daarom eerst met de
   SHA-256 die GitHub bij de upload vastlegde (via de releases-API) voordat
   hij faalt. Een bestand dat daarmee klopt is byte-identiek aan het
   gepubliceerde asset; is de API onbereikbaar, dan faalt de download zoals
   voorheen.
4. **Cache per versie, elke versie bruikbaar.** Een eerder teruggevallen
   versie in de cache wordt hergebruikt, zodat niet bij elke `normalize`
   opnieuw wordt opgezocht. De gepinde versie gaat voor als die er ook staat.
5. **Signalering.** `engine-e2e` draait zonder cache, zodat de download elke
   week echt wordt getest. De job faalt ook als de terugval nodig was (de pin
   moet omhoog), en een mislukte geplande run opent een issue of reageert op
   het openstaande.

## Afwegingen

- **Terugvallen boven hard falen.** Hard falen is zuiverder voor
  reproduceerbaarheid, maar laat gebruikers zonder werkende `normalize` zitten
  op een moment dat niemand van ons iets heeft veranderd. Een nieuwere Archi
  serialiseert in de praktijk vrijwel gelijk; de waarschuwing en het issue
  zorgen dat de pin snel volgt.
- **Redirect boven de GitHub-API.** De API vraagt zonder token een rate limit
  van 60 verzoeken per uur per IP, wat op gedeelde CI-runners snel op is. De
  redirect van `/releases/latest` heeft die grens niet. De API wordt alleen
  geraadpleegd bij een checksum-mismatch, met een token uit `GITHUB_TOKEN` of
  `GH_TOKEN` als dat er is.
- **Twee tagformaten proberen boven er één afleiden.** archi.io heeft het
  formaat al eens gewijzigd; een tweede poging kost één HTTP-verzoek.

## Gevolgen

- `engine.py`: `resolve_release()` kiest versie en tag; `cached_binary()`
  kijkt ook naar andere versies in de cache.
- Tests in `test_engine.py` voor beide tagformaten, de terugval (inclusief
  hergebruik zonder netwerk), een ontbrekend checksumbestand en een
  netwerkfout. Geen test raakt het netwerk.
- `engine-e2e.yml`: geen cache meer, faalt op een terugval, opent een issue.
