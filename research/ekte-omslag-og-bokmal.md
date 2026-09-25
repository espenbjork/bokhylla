# Ekte omslag og bokmål

Undersøkt 24. september 2026. Dette er kildekartlegging; ingen bokkort eller mål er endret.

## Funn

- Bokbasen Søk viser forside, bokrygg og bakside for noen utgaver. Bakside forutsetter innbundet/heftet bok, mottatt omslagstrykkunderlag og registrert høyde/bredde. https://www.bokbasen.no/nyheter/nyheter-i-bokbasen-sok
- Bokbasen mottar komplette omslagsfiler med forside, bakside, rygg og eventuelle innbretter. Det betyr ikke at trykkfilene er offentlig tilgjengelige. https://support.bokbasen.no/hc/no/articles/12895866711580-Hva-er-trykkunderlag
- Metadata-API krever avtale. Offentlig Objects-dokumentasjon beskriver omslagsbilder, men bekrefter ikke egen tilgang til rygg/bakside eller full trykkfil. Dekning, pris og rett til lokal lagring må avklares før integrasjon. Ingen henvendelse eller avtale er gjort. https://www.bokbasen.no/hjelp/fa-tilgang-til-metadata og https://bokbasen.jira.com/wiki/spaces/api/pages/67993638/Objects
- Open Library tilbyr ISBN-basert oppslag av omslagsbilder, men dokumentasjonen gir ingen garanti for rygg/bakside. Ikke en bekreftet kilde til komplette omslag. https://openlibrary.org/dev/docs/api/covers

## Konkrete kandidater

Hva jeg snakker om når jeg snakker om løping, norsk pocket 2021, ISBN 9788253042756: ARK oppgir høyde 202 mm, bredde 128 mm og lengde 17 mm (sistnevnte tolkes som tykkelse). Ikke bekreftet som Espens utgave.
https://www.ark.no/produkt/boker/dokumentar-og-faktaboker/hva-jeg-snakker-om-nar-jeg-snakker-om-loping-9788253042756

Arcanum Unbounded, Gollancz pocket 2017, ISBN 9781473218055: ARK oppgir høyde 129 mm, bredde 197 mm og lengde 39 mm. Høyde/bredde ser ombyttet ut og må kontrolleres mot en annen kilde før bruk. Ikke bekreftet som Espens utgave.
https://www.ark.no/produkt/arcanum-unbounded-9781473218055

Lokal Calibre-database inneholder 53 ISBN-identifikatorer. De må klassifiseres som trykt/digital utgave før mål kobles på. Audible-ASIN identifiserer lydutgaven, ikke en fysisk bok.

## Anbefalt implementering

1. Behold verk, lyd-/e-bokfiler og lesehistorikk. Legg til en separat valgt fysisk visningsutgave med ISBN, språk og innbinding. For bøker kun eid digitalt er dette en visningsutgave, ikke dokumentasjon av fysisk eierskap.
2. Lagre høyde, bredde og tykkelse i millimeter med kilde, hentet dato og bekreftelsesstatus. Gjengi alle bøker i samme relative skala; fysisk millimeter på skjerm krever kalibrering.
3. Lagre forside, rygg og bakside separat, eventuelt et komplett omslag med beskjæringsfelt. Alle må tilhøre samme utgave. Manglende sider må merkes som illustrerte; ikke presenteres som ekte.
4. Hent metadata automatisk der kilde og tilgang er avklart. Start med et lite utvalg og vis foreslåtte utgaver før kobling.
5. Tilby manuell opplasting av fotografier/skanning og egne mål for fysiske bøker når nettet mangler materiale. Ett rett bilde per side er enklere enn å rette ut et perspektivfoto av hele boka.

Faktiske mål kan ikke utledes sikkert fra sidetall alene; papir og innbinding påvirker tykkelsen. https://www.ingramspark.com/master-your-book-cover-design

Ingen universell, fritt tilgjengelig kilde til komplette omslag for hele biblioteket er bekreftet i denne undersøkelsen.
