# Bokhylla

En lokal digital tvilling av en personlig boksamling. Lydbøker, e-bøker og papirbøker samles i ett register med lesestatus og fremdrift, og vises som bokrygger i et mørkt bibliotekrom.

Dette repoet er kode og design. Selve biblioteket, lesehistorikken, omslagene og bokfilene ligger bare lokalt og er holdt utenfor med `.gitignore`. En fersk klone starter derfor med en tom hylle.

## Tre rom

- **Bokhylla** viser hele samlingen samtidig, fordelt over tolv hyllefag. Bokbreddene skaleres innenfor hvert fag.
- **Leser nå** legger de aktive bøkene med omslaget opp på et opplyst nattbord.
- **Leseåret** sprer årets fullførte bøker utover et salongbord.

Søk, formatfilter og sortering gjelder i alle tre, og bøkene flytter seg animert når rommet skifter. Rombildene i `static/room/` er genererte bakgrunner. Bøkene er vanlige HTML-elementer oppå, så hover, tastatur og skjermleser virker på dem.

## Hva den gjør

- Bokkort med status, år, fremdrift i sider eller prosent, format, kilde, språk, serie, sjanger og notater. Usikre år holdes utenfor årstellingen.
- Seks organiseringer av veggen: tittel, forfatter, serie, sjanger, omslagsfarge og egne hyller. Egne hyller sorteres med dra og slipp eller med knapper fra tastaturet.
- Bokryggfargene hentes fra omslaget. Bredden og høyden varieres for utseendets skyld.
- Flervalg med samlet statusendring. Alt lagres med endringshistorikk.
- Import fra Calibre (skrivebeskyttet), M4B-filer fra Libation og CSV fra Audible med forhåndsvisning. Importerte bøker får uavklart lesestatus.
- Egne bokfiler kan lastes opp, lydfiler i MP3/M4A/M4B/AAC spilles av i nettleseren, og hele registeret kan eksporteres til JSON og CSV.

## Kjøre den

```bash
python3 launch.py
```

Appen åpner http://127.0.0.1:8767/. Den bruker standardbiblioteket i Python 3.9 eller nyere, pluss Pillow til omslagsfargene.

Calibre og Libation leses fra `~/Calibre Library` og `~/Music/Libation/Books`. Andre plasseringer settes med `BOKHYLLA_CALIBRE` og `BOKHYLLA_LIBATION`, og datamappen med `BOKHYLLA_DATA`. Finnes ikke Calibre-mappen, hoppes importen over.

## Hvor dataene lagres

| sti | innhold |
|---|---|
| `data/library.sqlite3` | hovedregisteret med endringshistorikk |
| `data/library.json` | lesbar kopi, skrives ved hver lagring |
| `data/backups/` | en databasekopi per dag før første endring |
| `data/files/` | bokfiler lastet opp i appen |
| `static/covers/` | omslag kopiert fra Calibre og Libation |
| `imports/audible/` | uendret Amazon-dataeksport |

Ingen av disse er med i repoet.

## Sikkerhet

Serveren lytter bare på 127.0.0.1, og alle endringer krever en tilfeldig nøkkel som lages når serveren starter. Appen har ingen sporing, skylagring eller konto. Det eneste skriptet som går ut på nettet er `fetch_physical_covers.py`, som slår opp titler og forfattere i Google Books og bare kjøres når det startes for hånd.

## Teknologi

Python, SQLite, HTML, CSS og JavaScript uten rammeverk.
