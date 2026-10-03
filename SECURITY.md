# Beveiliging

Ontdek je een kwetsbaarheid in `archi-cli`, meld hem dan vertrouwelijk via GitHub:

**https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting/security/advisories/new**

Je melding is dan alleen zichtbaar voor jou en de beheerders van deze
repository. Meld een kwetsbaarheid niet in een openbaar issue.

Heb je geen GitHub-account, of meld je liever niet via GitHub, dan kan het ook
via het Nationaal Cyber Security Centrum:

**https://www.ncsc.nl/contact/kwetsbaarheid-melden**

Vermeld daarbij dat het gaat om `archi-cli` van de Nederlandse Digitale Dienst
(https://github.com/BureauArchitectuurDigitaleOverheid/ai-assisted-architecting). Het NCSC brengt je melding dan bij ons onder de aandacht.

## Wat er onder valt

`archi-cli` is een command line tool die lokaal draait op modelbestanden. Een
melding gaat over het gepubliceerde pakket op PyPI of de broncode in deze
repository. Voorbeelden van wat we graag horen:

- een modelbestand of deckbestand dat bij het inlezen bestanden of netwerk
  bereikt die het niet zou mogen bereiken;
- gegenereerde HTML die door de inhoud van een model scripts uitvoert;
- een manier om een andere Archi-engine te laten downloaden of uitvoeren dan de
  geverifieerde.

Kwetsbaarheden in Archi zelf meld je bij het
[Archi-project](https://github.com/archimatetool/archi).

## Wat we van je vragen

- **De versie** van `archi-cli` (`archi --version`) waarin je het zag.
- **Hoe je het reproduceert**, met een zo klein mogelijk modelbestand of
  commando.
- **Wat er misgaat**, en waar mogelijk wat een aanvaller ermee zou kunnen.

Deel de kwetsbaarheid niet met anderen voordat hij is opgelost, en ga niet
verder dan nodig is om het bestaan aan te tonen.

## Wat je van ons mag verwachten

Meld je via het NCSC, dan volgt de afhandeling het beleid op
https://www.ncsc.nl/contact/kwetsbaarheid-melden. Meld je via GitHub:

- Je krijgt een reactie op je melding met een inschatting.
- Je hoort hoe het staat met de oplossing. Dat gesprek loopt in de melding zelf,
  en daar kun je ook meewerken aan de fix.
- Is de kwetsbaarheid opgelost, dan publiceren we een nieuwe versie en een
  security advisory, en noemen we je als ontdekker, tenzij je dat liever niet
  hebt.

## Ondersteunde versies

Alleen de nieuwste versie op PyPI krijgt beveiligingsupdates. Zolang de tool
onder versie 1.0 ligt, verschijnt een oplossing altijd als nieuwe versie, niet
als patch op een oudere reeks.
