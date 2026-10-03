# Changelog

Alle wijzigingen die een gebruiker van `archi-cli` merkt, per versie. De opzet
volgt [Keep a Changelog](https://keepachangelog.com/nl/1.1.0/) en de versies
volgen [Semantic Versioning](https://semver.org/lang/nl/). Zolang de versie
onder 1.0 ligt, kan een minor-versie gedrag veranderen; dat staat dan onder
**Gewijzigd** met wat je moet aanpassen.

## [Unreleased]

### Toegevoegd

- `archi --version` toont de geïnstalleerde versie.
- `[tool.archi] fonts` kiest het lettertype van de webpagina's en slides:
  `"system"` (standaard) of `"rijkssans"`.
- Een voorbeeldmodel met views en een deck in `examples/vergunningverlening/`.
- `AGENTS.md` met instructies voor AI-codeassistenten; `CLAUDE.md` verwijst
  ernaar.
- Een gedragscode, een beveiligingsbeleid, issue- en PR-sjablonen en een
  `publiccode.yml`.
- De release-workflow maakt een GitHub Release met de tekst uit deze changelog,
  en CI controleert dat de versies in `pyproject.toml`, `plugin.json` en
  `uv.lock` gelijk zijn.

### Gewijzigd

- **De webpagina's en slides gebruiken standaard het systeemlettertype.**
  RijksSans is alleen bedoeld voor de Rijksoverheid en partijen in haar
  opdracht. Val je daaronder en wil je de oude weergave terug, zet dan
  `fonts = "rijkssans"` in je `archi.toml`.
- Het NLDD Design System is bijgewerkt van 0.8.64 naar 0.8.93.
- De Nederlandse Digitale Dienst is de uitgever en copyrighthouder.
- De README is herschreven, met wat de tool wel en niet is, de grenzen en een
  disclaimer.

## [0.2.2] - 2026-10-03

### Opgelost

- De Archi-engine wordt weer opgehaald. archi.io verving het checksumbestand
  `SUMSSHA1` door `Archi-<versie>-SHA256.txt`, waardoor 0.2.1 geen engine meer
  kon downloaden. De tool kent nu beide bestanden en verifieert tegen de
  upload-digest van GitHub als een release geen bekend checksumbestand heeft.

## [0.2.1] - 2026-09-30

### Opgelost

- De Archi-engine wordt weer opgehaald. archi.io houdt alleen de nieuwste
  release online, waardoor de gepinde 5.9.0 een 404 gaf. De pin staat op 5.10.0;
  verdwijnt een gepinde versie, dan valt `archi setup` met een waarschuwing
  terug op de nieuwste release (ADR 0011).
- Elke engine-download wordt geverifieerd. Klopt het checksumbestand van Archi
  zelf niet, dan geldt de SHA-256 die GitHub bij de upload vastlegde.

## [0.2.0] - 2026-09-30

### Toegevoegd

- `archi remove-property <ref> <key>` verwijdert een property; een ontbrekende
  key is een fout.
- `archi move <ref> --subfolder "<map>"` en `--subfolder` bij `add-element` en
  `add-relation` plaatsen elementen, relaties en views in een submap van hun
  laag. Een ontbrekende of dubbelzinnige map is een fout; `--create-subfolder`
  maakt hem bewust aan.
- Doorklikken tussen views via een links-bestand (`[tool.archi] links`):
  elementen in de webpagina's en slides worden klikbaar naar een andere view of
  een ander bestand (ADR 0010).
- `archi validate` vindt view-onderdelen die los in een map staan en views
  waarvan de naam dezelfde bestandsnaam oplevert.

### Gewijzigd

- Tooltips en slide-intro's lezen eerst het documentatieveld van Archi, met de
  property `Omschrijving` als terugval. Heeft een element beide, dan wint nu de
  documentatie.
- `Omschrijving` en `Toelichting` zijn geen ingebouwde property-keys meer;
  modellen zonder eigen conventielijst die ze gebruiken, krijgen waarschuwingen
  (ADR 0009).

### Opgelost

- Views waarvan de naam dezelfde slug oplevert, schreven naar hetzelfde bestand.
  Ze krijgen nu elk een eigen bestand, en alle links naar views volgen dat.

### Beveiliging

- Modelbestanden worden geparseerd zonder DTD's, entities of netwerktoegang, en
  de minimale versie is `lxml>=6.1.3`. Een gemanipuleerd `.archimate`-bestand
  kon eerder een lokaal bestand in het model laden.

### Bekend probleem

- `archi setup` en het automatisch ophalen in `normalize` geven een 404 op een
  machine zonder lokale Archi. Opgelost in 0.2.1.

## [0.1.1] - 2026-07-04

### Gewijzigd

- De tool staat los van het model waarvoor hij ontstond: de ingebouwde
  property-keys zijn generiek, en een project levert zijn eigen keys via een
  conventielijst (ADR 0008).

### Toegevoegd

- De repository is een Claude Code plugin (`archi-tools`) en marketplace
  (`archi-marketplace`) voor de skills (ADR 0007).

## [0.1.0] - 2026-07-04

Eerste release op PyPI.

### Toegevoegd

- Inspecteren: `stats`, `list`, `show` en `tree`.
- Muteren met validatie: `add-element`, `add-relation`, `set-property`,
  `set-documentation`, `rename`, `remove` (met `--cascade`) en `set-model-name`.
  Bij een validatiefout wordt niet opgeslagen.
- `archi validate` met integriteitschecks en een conventiecheck op
  property-keys.
- `archi normalize` via de headless Archi-engine, die de tool zelf ophaalt
  (`archi setup`, ADR 0005).
- `archi add-view` met grid- en clusterlayout.
- `archi render`: views naar Mermaid en naar HTML met het NLDD Design System,
  inclusief ArchiMate-notatie, en een indexpagina.
- `archi slides`: decks in TOML naar zelfstandige HTML-presentaties.
- Het model vinden via `--model`, een `archi.toml` of het enige
  `.archimate`-bestand in de map (ADR 0004).

[Unreleased]: https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/releases/tag/v0.1.1
[0.1.0]: https://pypi.org/project/archi-cli/0.1.0/
