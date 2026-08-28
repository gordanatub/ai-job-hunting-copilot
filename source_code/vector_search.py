from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import EndpointType, VectorIndexType, PipelineType, DeltaSyncVectorIndexSpecRequest, EmbeddingSourceColumn

# ---------------------------------------------------------
# 1. Vector Search client
# ---------------------------------------------------------

wsc = WorkspaceClient()

ENDPOINT_NAME = "job-copilot-endpoint"
INDEX_NAME = "job_copilot.vector.job_postings_index"
SOURCE_TABLE = "job_copilot.vector.job_postings_src"


# ---------------------------------------------------------
# 2. Provjeri da li endpoint postoji
# ---------------------------------------------------------

try:
    endpoint = wsc.vector_search_endpoints.get_endpoint(endpoint_name=ENDPOINT_NAME)
    print(f"Endpoint '{ENDPOINT_NAME}' već postoji.")

except Exception:
    print(f"Endpoint '{ENDPOINT_NAME}' ne postoji.")
    print("Kreiram endpoint...")

    wsc.vector_search_endpoints.create_endpoint(
        name=ENDPOINT_NAME,
        endpoint_type=EndpointType.STANDARD
    )

    endpoint = wsc.vector_search_endpoints.get_endpoint(endpoint_name=ENDPOINT_NAME)

print(endpoint)


# ---------------------------------------------------------
# 3. Prikaži postojeće indekse
# ---------------------------------------------------------

print("\nPostojeći indeksi:")

indexes = list(wsc.vector_search_indexes.list_indexes(endpoint_name=ENDPOINT_NAME))

print(indexes)


# ---------------------------------------------------------
# 4. Kreiraj index ako ne postoji
# ---------------------------------------------------------

try:
    index = wsc.vector_search_indexes.get_index(
        index_name=INDEX_NAME
    )

    print(f"\nIndex '{INDEX_NAME}' već postoji.")

except Exception:
    print(f"\nIndex '{INDEX_NAME}' ne postoji.")
    print("Kreiram index...")

    index = wsc.vector_search_indexes.create_index(
        name=INDEX_NAME,
        endpoint_name=ENDPOINT_NAME,
        primary_key="job_id",
        index_type=VectorIndexType.DELTA_SYNC,
        delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
            source_table=SOURCE_TABLE,
            pipeline_type=PipelineType.TRIGGERED,
            embedding_source_columns=[
                EmbeddingSourceColumn(
                    name="combined_text",
                    embedding_model_endpoint_name="databricks-bge-large-en"
                )
            ]
        )
    )

    print("Index je kreiran.")


# ---------------------------------------------------------
# 5. Provjera statusa indexa
# ---------------------------------------------------------

status = index.as_dict()["status"]

print("\nIndex status:")
print("State:", status.get("detailed_state"))
print("Ready:", status.get("ready"))
print("Message:", status.get("message"))


# ---------------------------------------------------------
# 6. Ako je index spreman - test semantic search
# ---------------------------------------------------------

if status.get("ready"):

    results = wsc.vector_search_indexes.query_index(
        index_name=INDEX_NAME,
        query_text="remote backend uloga bez zahteva 5+ godina Kubernetes iskustva",
        columns=[
            "job_id",
            "title",
            "company",
            "description"
        ],
        num_results=10
    )

    print("\nRezultati pretrage:")

    for row in results.as_dict()["result"]["data_array"]:
        print(row)

else:

    print("\nIndex još nije spreman.")
    print("Sačekaj da Vector Search završi indeksiranje.")


