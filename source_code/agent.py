from databricks.sdk import WorkspaceClient
import psycopg2

def get_conn():
    return psycopg2.connect(host=lb_host, port=lb_port, dbname=lb_db,
                             user=lb_user, password=lb_password, sslmode="require")

def search_jobs(query: str, user_id: int, top_k: int = 10) -> list[dict]:
    """Semantička pretraga oglasa + osnovno filtriranje po profilu korisnika."""
    hits = index.similarity_search(query_text=query,
                                    columns=["job_id","title","company","description"],
                                    num_results=top_k)
    return hits["result"]["data_array"]

def explain_match(job_id: str, user_id: int) -> str:
    """Vrati objašnjenje zašto oglas odgovara/ne odgovara profilu (LLM poziv nad description + skills)."""
    # povuci opis oglasa i skills korisnika iz Lakebase, prosledi LLM-u da generiše objašnjenje
    ...

def save_job(user_id: int, job_id: str, stage: str = "saved") -> str:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO applications (user_id, job_id, stage)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING""", (user_id, job_id, stage))
    conn.commit()
    return f"Oglas {job_id} sačuvan u fazi '{stage}'."

def update_pipeline_stage(user_id: int, job_id: str, new_stage: str) -> str:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""UPDATE applications SET stage=%s, updated_at=now()
                        WHERE user_id=%s AND job_id=%s""", (new_stage, user_id, job_id))
    conn.commit()
    return f"Status ažuriran na '{new_stage}'."

def draft_cover_letter(user_id: int, job_id: str) -> str:
    """Povuci resume + opis posla, pošalji LLM-u da napiše pasus za propratno pismo."""
    ...

def log_interview_note(application_id: int, note: str, follow_up_date: str | None) -> str:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO interview_notes (application_id, note, follow_up_date)
                        VALUES (%s, %s, %s)""", (application_id, note, follow_up_date))
    conn.commit()
    return "Beleška sačuvana."

def find_stale_applications(user_id: int, days: int = 14) -> list[dict]:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""SELECT application_id, job_id, stage, updated_at FROM applications
                        WHERE user_id=%s AND updated_at < now() - interval '%s days'
                        AND stage NOT IN ('rejected','offer')""", (user_id, days))
        return cur.fetchall()

#########################################################################
# 7.2 Registracija alata kod modela (tool calling)
##########################################################################

w = WorkspaceClient()

tools_schema = [
    {"type": "function", "function": {
        "name": "search_jobs",
        "description": "Pretraži oglase semantički na osnovu opisa željene uloge.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}, "user_id": {"type": "integer"}}}}},
    {"type": "function", "function": {
        "name": "save_job",
        "description": "Sačuvaj oglas u pipeline korisnika sa datim statusom.",
        "parameters": {"type": "object", "properties": {
            "user_id": {"type": "integer"}, "job_id": {"type": "string"},
            "stage": {"type": "string"}}}}},
    # ... ostali alati na isti način
]

def call_agent(user_message: str, user_id: int, history: list):
    response = w.serving_endpoints.query(
        name="databricks-meta-llama-3-3-70b-instruct",  # ili drugi dostupan chat model
        messages=history + [{"role": "user", "content": user_message}]
        #tools=tools_schema,
    )
    # ako model vrati tool_call -> pozovi odgovarajuću Python funkciju, vrati rezultat modelu,
    # pa nastavi razgovor (standardni tool-calling loop)
    ...