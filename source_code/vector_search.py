from databricks.vector_search.client import VectorSearchClient

# Ako fali databricks-vectorsearch, instaliraj ga
# %pip install databricks-vectorsearch
from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()
vsc.create_endpoint(name="job-copilot-endpoint", endpoint_type="STANDARD")

vsc = VectorSearchClient()
endpoint = vsc.get_endpoint("job-copilot-endpoint")
print(endpoint)
vsc.list_indexes("job-copilot-endpoint")

index = vsc.create_delta_sync_index(
endpoint_name="job-copilot-endpoint",
source_table_name="job_copilot.vector.job_postings_src",
index_name="job_copilot.vector.job_postings_index",
pipeline_type="TRIGGERED",
primary_key="job_id",
embedding_source_column="combined_text",
embedding_model_endpoint_name="databricks-bge-large-en"  # ugrađeni Databricks FM endpoint
)
## Nakon kreiranja index nije odmah SPREMAN za koristenje. Moze se provjeriti status
        #status = index.describe()["status"]
        #print("State:", status["detailed_state"])
        #print("Ready:", status["ready"])
        #print("Message:", status["message"])


##!!!! TODO !!!!!! Isto uradi i za profil korisnika (resume/skills) — opciono ali preporučeno
## Ako želiš da agent poredi profil korisnika sa oglasima semantički (a ne samo SQL filterima), napravi i tabelu job_copilot.vector.user_profiles_src sa kolonom profile_text (spojen resume + skills), pa isti postupak — poseban indeks ili isti endpoint.

vsc = VectorSearchClient()
endpoint = vsc.get_endpoint("job-copilot-endpoint")
print(endpoint)

vsc.list_indexes("job-copilot-endpoint")

index = vsc.get_index(
    endpoint_name="job-copilot-endpoint",
    index_name="job_copilot.vector.job_postings_index"
)
# Pretraga iz koda -> potrebno koristiti agente kasnije
results = index.similarity_search(
    query_text="remote backend uloga bez zahteva 5+ godina Kubernetes iskustva",
    columns=["job_id", "title", "company", "description"],
    num_results=10
)


