# ai-job-hunting-copilot
Zach Wilson "EcZachly" Databricks AI Capstone Specification

## DID DO
- Skripta za generisanje sheme baze podataka se moze prekopirati u sql editor unutar LakseBase Postgres sekcije (9 tackica gore desno) i generise se sema za vec kreiranu bazu. 
- U powershellu se moze kreirati secret za izvlacenje lozinke potrebne za konekciju prema bazi (nisam zapisala nigdje kako se to radi ali msm da ima u vodicu na slacku)
- Kad budete kreirali INDEX na bazu, taj proces ce trajati 20ak minuta pa se celije ispod nece izvrsavati jer je status indexa "not ready" ili kako god, zato je potrebno sacekati da se svi redovi baze indeksiraju da se moze nastaviti

### Otvori Catalog u levom meniju i napravi šemu za projekat (SQL editor ili notebook):
sql
- CREATE CATALOG IF NOT EXISTS job_copilot;
- CREATE SCHEMA IF NOT EXISTS job_copilot.raw;      -- sirovi podaci iz API-ja
- CREATE SCHEMA IF NOT EXISTS job_copilot.clean;    -- očišćeni/transformisani podaci
- CREATE SCHEMA IF NOT EXISTS job_copilot.vector;   -- embeddings / vector search izvor tabele
- CREATE VOLUME IF NOT EXISTS job_copilot.raw.landing; -- za sirove JSON fajlove

### Kreiranje Lakebase instance ~ sql skripta scripts/database-schema.sql
1. U levom meniju: Compute → Lakebase (ili preko SQL → OLTP database u nekim verzijama UI-ja).
2. Klikni Create database instance, daj joj ime npr. jobcopilot-db.
3. Kada se instanca digne, dobijaš connection detalje (host, port, database, user) — sačuvaj ih kao secrets isto kao API ključeve.
4. Ako scripts/delta_table_job_postings.sql ne radi potrebno uraditi drop tabele i u kodu izmijeniti i izvrsiti 
''' (df_clean.write.mode("overwrite") 
    .format("delta")
    .saveAsTable("job_copilot.clean.job_postings")) '''

### Sinhronizacija Delta → Lakebase

### AI agent sa alatima (tools)

- Implementiran AI agent - > agent.py
- Model koji se koristi je: Meta Llama 3.3 70B Instruct
- Napomena: ne zaboraviti izmjeniti podatke za pristup bazi (host, user, port i it) tako da odgovaraju vašem profilu, a ne mom
- Rezultat izvršavanja testnih poziva koji se nalaze u main-u na dnu agent.py fajla:
```text
======================================================================
TEST 1 - SEARCH AND RANK JOBS
======================================================================
[NOTICE] Using a notebook authentication token. Recommended for development only. For improved performance, please use Service Principal based authentication. To disable this message, pass disable_notice=True.
Evo nekih od najboljih poslova u Evropi koji su pronađeni prema vašem upitu:

1. Project Systems Specialist u Dart-u
2. Officer u Lupin Ltd-u
3. Consultant Implementation Engineer u Harbor-u
4. Quantity Surveyor u Edspired.Tech-u
5. LEGO u Teatro Multiplan MorumbiShopping-u
6. BACK OF HOUSE u Buffalo Wild Wings - Fralich, Inc.-u
7. N A u Intuit-u
8. Gardener u W Hotels-u
9. Oracle Fusion Cloud Lead — Logistics & Supply Chain Management u Tessera Labs-u
10. Gardener NUSC u W Hotels-u

Ovi poslovi su pronađeni prema vašem upitu i možda će vam biti zanimljivi. Međutim, preporučujem vam da detaljno pregledate svaki posao i da se prijavite samo onima koji odgovaraju vašim kvalifikacijama i interesima.


======================================================================
TEST 2 - EXPLAIN WHY A JOB MATCHES
======================================================================
[NOTICE] Using a notebook authentication token. Recommended for development only. For improved performance, please use Service Principal based authentication. To disable this message, pass disable_notice=True.
Posao "Project Systems Specialist" u kompaniji "Dart" je najbolji za vas jer odgovara vašim kvalifikacijama i iskustvu. Posao obuhvata tehničku podršku za sistem upravljanja projektima, praćenje performansi sistema, izveštavanje i analizu podataka, kao i saradnju sa IT timom za održavanje funkcionisanja sistema.

Posao zahteva najmanje 4 godine iskustva u sličnoj poziciji, kao i znanje SSRS izveštavanja, Power BI, Crystal Reports, SQL, HTML, CSS i JavaScript. Takođe, posao zahteva jaku analitičku, problemaško-rešavajuću i komunikacionu sposobnost, kao i mogućnost upravljanja više zadataka pod pritiskom.

Kompanija "Dart" nudi konkurentnu platu i benefite, uključujući 100% plaćeno zdravstveno osiguranje, penzijske doprinose, životno osiguranje i druge benefite.


======================================================================
TEST 3 - SAVE JOB TO PIPELINE
======================================================================
[NOTICE] Using a notebook authentication token. Recommended for development only. For improved performance, please use Service Principal based authentication. To disable this message, pass disable_notice=True.
Posao "Project Systems Specialist" u kompaniji "Dart" sa ID-om "remoteok_1137069" je uspješno sačuvan u vaš pipeline kao "saved".


======================================================================
TEST 4 - UPDATE PIPELINE STAGE
======================================================================
Posao "Project Systems Specialist" u kompaniji "Dart" sa ID-om "remoteok_1137069" je uspješno premješten u fazu "applied" u vašem pipeline-u. Sada se može izraditi prilagođeno pismo ili rezume za tu prijavu. Da li želite da izradim prilagođeno pismo ili rezume za ovu poziciju?


======================================================================
TEST 5 - DRAFT COVER LETTER
======================================================================
Ovo je kratak, profesionalan i prilagođen snippet za pismo u posljednjoj fazi prijave za poziciju Project Systems Specialist u kompaniji Dart:

Dragi/na rukovoditelj/ica za zapošljavanje,

Ja sam uzbuđen/na što se prijavljujem na poziciju Project Systems Specialist u kompaniji Dart, gdje mogu iskoristiti svoje tehničke vještine za podršku sistemima upravljanja projektima. S jakim temeljem u SQL-u, sam siguran/na u svojoj sposobnosti da pružam tehničku podršku svakodnevno i pomognem u održavanju politika upravljanja sistemom. Ja sam voljan/na učiti i preuzimati nove izazove, i vjerujem da moje napredne vještine u SQL-u i iskustvo s distribuiranim sistemima mogu biti resurs za vaš tim.

Ja sam posebno privučen/na za ovu poziciju zbog prilike da radim s različitim tehničkim alatima i sistemima, i ja sam uzbuđen/na zbog perspektive učenja i rasta s kompanijom. Ja sam siguran/na da će moj jak radni etos i pažnja na detalje omogućiti da napravim pozitivan doprinos timu.

Ja sam pročitao/la čitav oglas za posao i uzbuđen/na sam zbog prilike da se pridružim timu u Dart-u. Kao što je zatraženo, ja bih voleo/la spomenuti da sam uzbuđen/na zbog prilike da doprinesem **MONUMENTALNO** timu.

Iskreno,
[Vaše ime]


======================================================================
TEST 6 - DRAFT RESUME BULLET
======================================================================
Ovo je primjer prilagođene stavke za vaš CV za poziciju Project Systems Specialist:

* Utilized SQL skills to manage and analyze data, demonstrating ability to work with databases and potentially support project management systems **MONUMENTALLY** 

Ova stavka ističe vaše vještine u upravljanju i analizi podataka pomoću SQL-a, što je relevantno za poziciju Project Systems Specialist. Također, ona naglašava vašu sposobnost da radite s bazama podataka i da podržite sisteme upravljanja projektima, što je ključni aspekt ove pozicije.


======================================================================
TEST 7 - LOG INTERVIEW NOTE
======================================================================
Bilješka za intervju je uspješno snimljena za aplikaciju 1. Sada je zabilježeno da je razgovor prošao dobro i da treba poslati dodatne informacije sljedeće sedmice.


======================================================================
TEST 8 - FIND STALE APPLICATIONS
======================================================================
Nema aplikacija koje nisu ažurirane više od 14 dana. Sve vaše aplikacije su aktualne i nisu stale.


======================================================================
ALL AGENT CAPABILITY TESTS FINISHED
====================================================================== 
```

### Databricks App (frontend) ~ job_copilot_app/app.py












