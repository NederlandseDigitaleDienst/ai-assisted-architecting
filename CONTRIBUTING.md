# Bijdragen

Fijn dat je wilt bijdragen aan `archi-cli`. Deze repository bevat de tool zelf
(Python, in `tools/archi_tool/`) en de skills voor AI-assistenten (in
`skills/`). Een foutmelding, een idee of een verbetering in de
documentatie is net zo welkom als code.

Iedereen die meedoet, houdt zich aan de [gedragscode](CODE_OF_CONDUCT.md). Een
beveiligingsprobleem meld je volgens [SECURITY.md](SECURITY.md), niet in een
openbaar issue.

## Een issue openen

Zoek eerst of je probleem of idee al bestaat. Gebruik daarna een van de
sjablonen: bij een fout helpen de uitvoer van `archi --version`, het commando en
de volledige foutmelding het meest. Kun je het laten zien op het voorbeeld in
`examples/vergunningverlening/`, dan hoef je geen eigen model te delen. Deel
nooit een model met vertrouwelijke inhoud.

## Opzetten

Je hebt [uv](https://docs.astral.sh/uv/) en [just](https://just.systems/) nodig;
uv regelt Python zelf.

```bash
git clone https://github.com/NederlandseDigitaleDienst/ai-assisted-architecting.git
cd ai-assisted-architecting
just setup     # venv, dependencies en de pre-commit hooks
just test      # de testsuite
just lint      # alle hooks op alle bestanden, zoals CI
```

De tests draaien op een klein fixture-model in `tests/fixtures/`. Je hebt geen
eigen `.archimate`-bestand nodig om aan de tool te werken.

## Een wijziging voorstellen

1. Maak een branch vanaf een verse `main` en houd de wijziging klein en
   samenhangend. Eén onderwerp per pull request reviewt het snelst.
2. Schrijf of pas tests aan. Een nieuwe check in `validate.py` krijgt een test
   die het fixture-model gericht beschadigt en de foutmelding controleert. Geen
   test raakt het netwerk.
3. Werk `CHANGELOG.md` bij onder **Unreleased** als een gebruiker de wijziging
   merkt. Verandert een CLI-optie, werk dan ook de README, de skills en
   `AGENTS.md` bij.
4. Leg een structurele beslissing vast in een ADR in `adr/`.
5. Open een pull request en vul het sjabloon in. CI draait de hooks, de tests op
   Ubuntu (Python 3.12 en 3.14) en Windows, en een testbuild van het pakket.

## Conventies

- **Taal.** Code en comments in het Engels; documentatie, meldingen voor
  gebruikers, commit-berichten en PR-beschrijvingen in het Nederlands. Een
  Nederlandse domeinterm zonder goede Engelse tegenhanger mag blijven staan.
- **Commit-berichten.** Een titel in de gebiedende wijs ("Voeg ... toe",
  "Herstel ..."), en in de body waarom de wijziging nodig is.
- **Opmaak.** ruff format en ruff lint; de pre-commit hooks controleren het, dus
  `just lint` vóór je commit voorkomt verrassingen in CI.
- **Determinisme.** Gegenereerde uitvoer bevat geen tijdstempels, absolute paden
  of willekeurige volgordes.
- **Modelbestanden.** Bewerk nooit met de hand de XML van een model, ook niet
  van het fixture of het voorbeeld; gebruik de `archi`-CLI.

Meer over de opbouw van de code, de bestandsindeling en de werkwijze staat in
[AGENTS.md](AGENTS.md). Dat bestand is geschreven voor AI-codeassistenten, maar
is net zo bruikbaar voor mensen.

## De skills

De skills in `skills/` beschrijven hoe een AI-assistent via de tool aan
een model werkt. Houd ze generiek: gebruik placeholders in plaats van namen uit
een specifiek model, en laat ze dezelfde commando's en opties noemen als de
tool echt heeft.

## Versies en releases

De versies volgen [Semantic Versioning](https://semver.org/lang/nl/): een
patch voor een oplossing, een minor voor nieuwe functies. Zolang de versie onder
1.0 ligt, kan een minor gedrag veranderen; dat staat dan in de changelog onder
**Gewijzigd**, met wat een gebruiker moet aanpassen.

Een release maken is aan de maintainers. De stappen staan in
[AGENTS.md](AGENTS.md#releasen); de release-workflow controleert de versie en de
changelog, draait de tests en publiceert via PyPI Trusted Publishing.

## Licentie

Door bij te dragen ga je ermee akkoord dat je bijdrage onder de
[EUPL-1.2](LICENSE) valt, net als de rest van deze repository.
