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

### Sinhronizacija Delta → Lakebase

### AI agent sa alatima (tools)

Agent mora da čita (pretražuje/rangira) i piše (menja stanje u Lakebase-u). Najlakši put u Databricks-u je Mosaic AI Agent Framework (koristi LangChain/LangGraph stil, može i čist Python + databricks-sdk + OpenAI-compatible poziv modelu preko Model Serving-a).

Alternativa: ako želiš gotov framework, koristi LangGraph (pip install langgraph langchain-databricks) — mnogo je manje "ručnog" koda za tool-calling petlju, i lakše se testira. Loop je isti: model → tool_call → izvršiš Python funkciju → rezultat nazad modelu → finalni odgovor.


### Databricks App (frontend) ~ job_copilot_app/app.py












