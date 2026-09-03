# /// script
# [tool.databricks.environment]
# dependencies = [
#   "databricks-vectorsearch",
#   "psycopg2-binary"
# ]
# ///

import json
import psycopg2

from databricks.sdk import WorkspaceClient
from databricks.vector_search.client import VectorSearchClient


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

ENDPOINT_NAME = "job-copilot-endpoint"
INDEX_NAME = "job_copilot.vector.job_postings_index"

LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"

MAX_TOOL_ROUNDS = 5


# ---------------------------------------------------------
# LAKEBASE CONNECTION
# Uses Apps + Lakebase integration pattern with env vars
# ---------------------------------------------------------

import os


# ---------------------------------------------------------
# DATABRICKS CLIENTS
# ---------------------------------------------------------

workspace = WorkspaceClient()

# Lazy initialization for vector search (to avoid auth errors at import time)
_vector_client = None
_index = None

def get_vector_index():
    """Get the vector search index, initializing on first use."""
    global _vector_client, _index
    if _index is None:
        if "DATABRICKS_CLIENT_SECRET" in os.environ:
            # Databricks App environment — authenticate as the app's service principal
            _vector_client = VectorSearchClient(
                workspace_url=f"https://{os.environ['DATABRICKS_HOST']}",
                service_principal_client_id=os.environ["DATABRICKS_CLIENT_ID"],
                service_principal_client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
                disable_notice=True
            )
        else:
            # Notebook environment — auto-detect credentials
            _vector_client = VectorSearchClient(disable_notice=True)
        _index = _vector_client.get_index(
            endpoint_name=ENDPOINT_NAME,
            index_name=INDEX_NAME
        )
    return _index


# ---------------------------------------------------------
# LAKEBASE CONNECTION
# ---------------------------------------------------------

def get_conn():
    """
    Create a connection to Lakebase PostgreSQL.

    Uses the Apps + Lakebase integration pattern:
    - Connection params from environment variables (PGHOST, PGDATABASE, PGUSER, PGPORT, PGSSLMODE)
    - Password from Lakebase credential generation API (workspace.postgres.generate_database_credential)
    - Endpoint path from LAKEBASE_ENDPOINT env var (set via valueFrom in app.yaml)
    """
    credential = workspace.postgres.generate_database_credential(
        endpoint=os.environ["LAKEBASE_ENDPOINT"]
    )

    return psycopg2.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ.get("PGPORT", 5432)),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=credential.token,
        sslmode=os.environ.get("PGSSLMODE", "require")
    )


# ---------------------------------------------------------
# 1. GET USER PROFILE
# ---------------------------------------------------------

def get_user_profile(user_id: int) -> dict:
    """
    Retrieve the complete profile and skills of one user.

    This function is always called with the current user_id
    supplied by the application.
    """

    conn = get_conn()

    try:
        with conn.cursor() as cur:

            # ------------------------------------------------
            # USER PROFILE
            # ------------------------------------------------

            cur.execute(
                """
                SELECT
                    user_id,
                    target_roles,
                    min_salary,
                    remote_only,
                    preferred_locations,
                    resume_text
                FROM profiles
                WHERE user_id = %s
                """,
                (user_id,)
            )

            profile = cur.fetchone()

            if profile is None:
                return {
                    "error": f"Profile for user {user_id} was not found."
                }

            # ------------------------------------------------
            # USER SKILLS
            # ------------------------------------------------

            cur.execute(
                """
                SELECT
                    skill_name,
                    proficiency,
                    years_exp
                FROM skills
                WHERE user_id = %s
                ORDER BY skill_name
                """,
                (user_id,)
            )

            skills = cur.fetchall()

            return {
                "user_id": profile[0],
                "target_roles": profile[1],
                "min_salary": (
                    float(profile[2])
                    if profile[2] is not None
                    else None
                ),
                "remote_only": profile[3],
                "preferred_locations": profile[4],
                "resume_text": profile[5],
                "skills": [
                    {
                        "skill_name": skill[0],
                        "proficiency": skill[1],
                        "years_exp": (
                            float(skill[2])
                            if skill[2] is not None
                            else None
                        )
                    }
                    for skill in skills
                ]
            }

    finally:
        conn.close()


# ---------------------------------------------------------
# 2. SEARCH JOBS
# ---------------------------------------------------------

def search_jobs(
    query: str,
    user_id: int,
    top_k: int = 10
) -> list[dict]:
    """
    Semantically search job postings while taking the
    current user's profile into account.

    The user profile is incorporated into the semantic query
    so that search results are personalized.
    """

    profile = get_user_profile(user_id)

    if "error" in profile:
        return profile

    # --------------------------------------------------------
    # BUILD USER-SPECIFIC SEARCH CONTEXT
    # --------------------------------------------------------

    skill_names = [
        skill["skill_name"]
        for skill in profile["skills"]
    ]

    user_context = f"""
Current user's job preferences:

Target roles:
{profile["target_roles"]}

Skills:
{", ".join(skill_names)}

Preferred locations:
{profile["preferred_locations"]}

Remote only:
{profile["remote_only"]}

Minimum salary:
{profile["min_salary"]}

Resume:
{profile["resume_text"]}
"""

    personalized_query = f"""
User's request:
{query}

{user_context}

Find job postings that are semantically relevant to the
user's request and compatible with the user's profile.

Prioritize:
- target roles
- user's technical skills
- preferred locations
- remote preference
- relevant experience

Do not invent requirements or user qualifications.
"""

    # --------------------------------------------------------
    # VECTOR SEARCH
    # --------------------------------------------------------

    results = get_vector_index().similarity_search(
        query_text=personalized_query,
        columns=[
            "job_id",
            "title",
            "company",
            "description"
        ],
        num_results=top_k
    )

    rows = results["result"]["data_array"]

    jobs = []

    for row in rows:

        jobs.append({
            "job_id": row[0],
            "title": row[1],
            "company": row[2],
            "description": row[3]
        })

    return jobs


# ---------------------------------------------------------
# 3. GET JOB
# ---------------------------------------------------------

def get_job(job_id: str):

    conn = get_conn()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    job_id,
                    title,
                    company,
                    description
                FROM job_postings
                WHERE job_id = %s
                """,
                (job_id,)
            )

            return cur.fetchone()

    finally:
        conn.close()


# ---------------------------------------------------------
# 4. CHECK USER
# ---------------------------------------------------------

def user_exists(user_id: int) -> bool:
    """
    Verify that the requested user exists in the profile table.
    """

    conn = get_conn()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT 1
                FROM profiles
                WHERE user_id = %s
                LIMIT 1
                """,
                (user_id,)
            )

            return cur.fetchone() is not None

    finally:
        conn.close()


# ---------------------------------------------------------
# 5. LLM CALL
# ---------------------------------------------------------

def call_llm(messages, tools=None):
    """
    Call Databricks Model Serving.

    Authentication is handled by WorkspaceClient.

    Function calling is passed through the REST request
    using the OpenAI-compatible tools format.
    """

    request = {
        "messages": messages
    }

    if tools is not None:
        request["tools"] = tools
        request["tool_choice"] = "auto"

    response = workspace.api_client.do(
        "POST",
        f"/serving-endpoints/{LLM_ENDPOINT}/invocations",
        body=request
    )

    return response


# ---------------------------------------------------------
# 6. EXPLAIN MATCH
# ---------------------------------------------------------

def explain_match(
    job_id: str,
    user_id: int
) -> str:
    """
    Explain why a specific job matches the current user's
    profile.
    """

    job = get_job(job_id)

    if job is None:
        return f"Job '{job_id}' was not found."

    profile = get_user_profile(user_id)

    if "error" in profile:
        return profile["error"]

    prompt = f"""
You are a job-matching assistant.

Compare this job posting with the CURRENT USER'S profile.

JOB:
Title: {job[1]}
Company: {job[2]}

Description:
{job[3]}


CURRENT USER PROFILE:

Target roles:
{profile["target_roles"]}

Minimum salary:
{profile["min_salary"]}

Remote only:
{profile["remote_only"]}

Preferred locations:
{profile["preferred_locations"]}

Resume:
{profile["resume_text"]}

Skills:
{profile["skills"]}


Explain:

1. Why the job matches this user.
2. Which user skills are relevant.
3. Which requirements are missing or unclear.
4. Whether the job fits the user's stated preferences.
5. Give an overall assessment.

Do not invent information that is not present
in the job or user profile.
"""

    response = call_llm([
        {
            "role": "user",
            "content": prompt
        }
    ])

    return response["choices"][0]["message"]["content"]


# ---------------------------------------------------------
# 7. SAVE JOB
# ---------------------------------------------------------

def save_job(
    user_id: int,
    job_id: str,
    stage: str = "saved"
) -> str:
    """
    Save a job to the CURRENT USER'S application pipeline.
    """

    allowed_stages = {
        "saved",
        "applied",
        "interviewing",
        "rejected",
        "offer"
    }

    if stage not in allowed_stages:
        return (
            f"Invalid stage '{stage}'. "
            f"Allowed stages: "
            f"{', '.join(sorted(allowed_stages))}"
        )

    if not user_exists(user_id):
        return f"User {user_id} was not found."

    if get_job(job_id) is None:
        return f"Job '{job_id}' was not found."

    conn = get_conn()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO applications
                    (user_id, job_id, stage)
                VALUES
                    (%s, %s, %s)
                ON CONFLICT (user_id, job_id)
                DO UPDATE SET
                    stage = EXCLUDED.stage,
                    updated_at = now()
                """,
                (user_id, job_id, stage)
            )

        conn.commit()

    finally:
        conn.close()

    return (
        f"Job {job_id} saved for user {user_id} "
        f"with stage '{stage}'."
    )


# ---------------------------------------------------------
# 8. UPDATE PIPELINE
# ---------------------------------------------------------

def update_pipeline_stage(
    user_id: int,
    job_id: str,
    new_stage: str
) -> str:
    """
    Update the application stage only for the CURRENT USER.
    """

    allowed_stages = {
        "saved",
        "applied",
        "interviewing",
        "rejected",
        "offer"
    }

    if new_stage not in allowed_stages:
        return (
            f"Invalid stage '{new_stage}'. "
            f"Allowed stages: "
            f"{', '.join(sorted(allowed_stages))}"
        )

    conn = get_conn()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE applications
                SET
                    stage = %s,
                    updated_at = now()
                WHERE
                    user_id = %s
                    AND job_id = %s
                """,
                (
                    new_stage,
                    user_id,
                    job_id
                )
            )

            updated = cur.rowcount

        conn.commit()

    finally:
        conn.close()

    if updated == 0:
        return (
            f"No application found for user {user_id} "
            f"and job {job_id}."
        )

    return (
        f"Job {job_id} for user {user_id} "
        f"moved to stage '{new_stage}'."
    )


# ---------------------------------------------------------
# 9. DRAFT COVER LETTER
# ---------------------------------------------------------

def draft_cover_letter(
    user_id: int,
    job_id: str
) -> str:
    """
    Generate a tailored cover-letter snippet based only
    on the CURRENT USER'S profile.
    """

    job = get_job(job_id)

    if job is None:
        return f"Job '{job_id}' was not found."

    profile = get_user_profile(user_id)

    if "error" in profile:
        return profile["error"]

    prompt = f"""
Write a concise, professional cover-letter snippet
tailored to this job and CURRENT USER.

JOB:

Title:
{job[1]}

Company:
{job[2]}

Description:
{job[3]}


CURRENT USER:

Resume:
{profile["resume_text"]}

Skills:
{profile["skills"]}

Target roles:
{profile["target_roles"]}


Only use information present in the user's profile.

Do not invent:
- experience
- employers
- degrees
- achievements
- certifications
- skills
"""

    response = call_llm([
        {
            "role": "user",
            "content": prompt
        }
    ])

    return response["choices"][0]["message"]["content"]


# ---------------------------------------------------------
# 10. DRAFT RESUME BULLET
# ---------------------------------------------------------

def draft_resume_bullet(
    user_id: int,
    job_id: str
) -> str:
    """
    Generate one tailored resume bullet for the CURRENT USER
    based on a specific job.

    Only information actually present in the user's resume
    and skills may be used.
    """

    job = get_job(job_id)

    if job is None:
        return f"Job '{job_id}' was not found."

    profile = get_user_profile(user_id)

    if "error" in profile:
        return profile["error"]

    prompt = f"""
Create one concise resume bullet tailored to this job.

JOB:

Title:
{job[1]}

Company:
{job[2]}

Description:
{job[3]}


CURRENT USER:

Resume:
{profile["resume_text"]}

Skills:
{profile["skills"]}


Rules:

- Use ONLY information present in the user's profile.
- Do not invent work experience.
- Do not invent projects.
- Do not invent achievements.
- Do not invent technologies.
- Do not invent numbers or metrics.
- Do not claim that the user performed something
  if it is not supported by the profile.

Return only the final resume bullet.
"""

    response = call_llm([
        {
            "role": "user",
            "content": prompt
        }
    ])

    return response["choices"][0]["message"]["content"]


# ---------------------------------------------------------
# 11. LOG INTERVIEW NOTE
# ---------------------------------------------------------

def log_interview_note(
    user_id: int,
    application_id: int,
    note: str,
    follow_up_date: str | None = None
) -> str:
    """
    Save an interview note only if the application belongs
    to the CURRENT USER.
    """

    conn = get_conn()

    try:
        with conn.cursor() as cur:

            # ------------------------------------------------
            # VERIFY APPLICATION OWNERSHIP
            # ------------------------------------------------

            cur.execute(
                """
                SELECT application_id
                FROM applications
                WHERE
                    application_id = %s
                    AND user_id = %s
                """,
                (
                    application_id,
                    user_id
                )
            )

            application = cur.fetchone()

            if application is None:
                return (
                    f"Application {application_id} does not "
                    f"belong to user {user_id}."
                )

            # ------------------------------------------------
            # INSERT NOTE
            # ------------------------------------------------

            cur.execute(
                """
                INSERT INTO interview_notes
                    (application_id, note, follow_up_date)
                VALUES
                    (%s, %s, %s)
                """,
                (
                    application_id,
                    note,
                    follow_up_date
                )
            )

        conn.commit()

    finally:
        conn.close()

    return (
        f"Interview note saved for application "
        f"{application_id}."
    )


# ---------------------------------------------------------
# 12. FIND STALE APPLICATIONS
# ---------------------------------------------------------

def find_stale_applications(
    user_id: int,
    days: int = 14
) -> list[dict]:
    """
    Find stale applications belonging ONLY to the
    CURRENT USER.
    """

    conn = get_conn()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    application_id,
                    job_id,
                    stage,
                    updated_at
                FROM applications
                WHERE
                    user_id = %s
                    AND updated_at < now() -
                        (%s * interval '1 day')
                    AND stage NOT IN ('rejected', 'offer')
                ORDER BY updated_at
                """,
                (
                    user_id,
                    days
                )
            )

            rows = cur.fetchall()

            return [
                {
                    "application_id": row[0],
                    "job_id": row[1],
                    "stage": row[2],
                    "updated_at": str(row[3])
                }
                for row in rows
            ]

    finally:
        conn.close()


# ---------------------------------------------------------
# 13. TOOLS SCHEMA
# ---------------------------------------------------------

tools_schema = [

    # --------------------------------------------------------
    # SEARCH JOBS
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description":
                "Search job postings semantically and "
                "personalize the search using the current "
                "user's profile, skills and preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description":
                            "Natural language description "
                            "of what the user is looking for."
                    },
                    "user_id": {
                        "type": "integer",
                        "description":
                            "The current user's ID."
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 10,
                        "description":
                            "Maximum number of jobs to return."
                    }
                },
                "required": [
                    "query",
                    "user_id"
                ]
            }
        }
    },

    # --------------------------------------------------------
    # GET USER PROFILE
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description":
                "Retrieve the current user's resume, target "
                "roles, preferences and skills.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description":
                            "The current user's ID."
                    }
                },
                "required": [
                    "user_id"
                ]
            }
        }
    },

    # --------------------------------------------------------
    # EXPLAIN MATCH
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "explain_match",
            "description":
                "Explain why a particular job matches the "
                "current user's profile.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string"
                    },
                    "user_id": {
                        "type": "integer",
                        "description":
                            "The current user's ID."
                    }
                },
                "required": [
                    "job_id",
                    "user_id"
                ]
            }
        }
    },

    # --------------------------------------------------------
    # SAVE JOB
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "save_job",
            "description":
                "Save a job into the current user's "
                "application pipeline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description":
                            "The current user's ID."
                    },
                    "job_id": {
                        "type": "string"
                    },
                    "stage": {
                        "type": "string",
                        "enum": [
                            "saved",
                            "applied",
                            "interviewing",
                            "rejected",
                            "offer"
                        ]
                    }
                },
                "required": [
                    "user_id",
                    "job_id"
                ]
            }
        }
    },

    # --------------------------------------------------------
    # UPDATE PIPELINE
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "update_pipeline_stage",
            "description":
                "Change the stage of a job application "
                "belonging to the current user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description":
                            "The current user's ID."
                    },
                    "job_id": {
                        "type": "string"
                    },
                    "new_stage": {
                        "type": "string",
                        "enum": [
                            "saved",
                            "applied",
                            "interviewing",
                            "rejected",
                            "offer"
                        ]
                    }
                },
                "required": [
                    "user_id",
                    "job_id",
                    "new_stage"
                ]
            }
        }
    },

    # --------------------------------------------------------
    # COVER LETTER
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "draft_cover_letter",
            "description":
                "Create a tailored cover-letter snippet "
                "for a specific job using only the current "
                "user's profile.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description":
                            "The current user's ID."
                    },
                    "job_id": {
                        "type": "string"
                    }
                },
                "required": [
                    "user_id",
                    "job_id"
                ]
            }
        }
    },

    # --------------------------------------------------------
    # RESUME BULLET
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "draft_resume_bullet",
            "description":
                "Create one tailored resume bullet for a "
                "specific job using only information from "
                "the current user's profile.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description":
                            "The current user's ID."
                    },
                    "job_id": {
                        "type": "string"
                    }
                },
                "required": [
                    "user_id",
                    "job_id"
                ]
            }
        }
    },

    # --------------------------------------------------------
    # INTERVIEW NOTE
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "log_interview_note",
            "description":
                "Save an interview note for an application "
                "belonging to the current user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description":
                            "The current user's ID."
                    },
                    "application_id": {
                        "type": "integer"
                    },
                    "note": {
                        "type": "string"
                    },
                    "follow_up_date": {
                        "type": "string"
                    }
                },
                "required": [
                    "user_id",
                    "application_id",
                    "note"
                ]
            }
        }
    },

    # --------------------------------------------------------
    # STALE APPLICATIONS
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "find_stale_applications",
            "description":
                "Find applications belonging to the current "
                "user that have not been updated recently.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description":
                            "The current user's ID."
                    },
                    "days": {
                        "type": "integer",
                        "default": 14
                    }
                },
                "required": [
                    "user_id"
                ]
            }
        }
    }
]


# ---------------------------------------------------------
# 14. TOOL DISPATCHER
# ---------------------------------------------------------

TOOL_FUNCTIONS = {
    "search_jobs": search_jobs,
    "get_user_profile": get_user_profile,
    "explain_match": explain_match,
    "save_job": save_job,
    "update_pipeline_stage": update_pipeline_stage,
    "draft_cover_letter": draft_cover_letter,
    "draft_resume_bullet": draft_resume_bullet,
    "log_interview_note": log_interview_note,
    "find_stale_applications": find_stale_applications
}


def execute_tool(
    tool_name: str,
    arguments: dict,
    current_user_id: int
):
    """
    Execute an agent tool.

    The current_user_id comes from the application and is
    therefore authoritative.

    If the LLM attempts to use another user_id, the tool
    execution is rejected.
    """

    if tool_name not in TOOL_FUNCTIONS:
        return {
            "error": f"Unknown tool: {tool_name}"
        }

    # --------------------------------------------------------
    # ENFORCE CURRENT USER
    # --------------------------------------------------------

    if "user_id" in arguments:

        requested_user_id = arguments["user_id"]

        if requested_user_id != current_user_id:

            return {
                "error":
                    "The requested user_id does not match "
                    "the current application user."
            }

    # --------------------------------------------------------
    # FORCE CURRENT USER ID
    # --------------------------------------------------------

    arguments["user_id"] = current_user_id

    try:

        return TOOL_FUNCTIONS[tool_name](**arguments)

    except Exception as e:

        return {
            "error": str(e)
        }


# ---------------------------------------------------------
# 15. AGENT
# ---------------------------------------------------------

def call_agent(
    user_message: str,
    user_id: int,
    history: list
):
    """
    Main AI Job Hunting Copilot agent.

    user_id is supplied by the Streamlit application and
    represents the CURRENT USER.

    The agent is not allowed to operate on another user's
    profile or applications.
    """

    # --------------------------------------------------------
    # VERIFY USER
    # --------------------------------------------------------

    if not user_exists(user_id):

        return (
            f"User {user_id} was not found. "
            f"Please select a valid user."
        )

    # --------------------------------------------------------
    # SYSTEM PROMPT
    # --------------------------------------------------------

    system_message = {
        "role": "system",
        "content": f"""
            You are AI Job Hunting Copilot.

            You are currently assisting USER ID {user_id}.

            IMPORTANT USER RULE:

            You MUST operate only on the current user with ID {user_id}.

            Never:
            - use another user's profile,
            - search another user's applications,
            - save a job for another user,
            - update another user's application,
            - access another user's interview notes.

            The application provides the authoritative user ID.

            Your capabilities are:

            1. Find suitable job openings.
            2. Use semantic job search.
            3. Personalize job search using the user's profile,
            skills and preferences.
            4. Compare jobs against the user's profile.
            5. Explain why a job is or is not a good match.
            6. Save jobs into the user's application pipeline.
            7. Update application stages.
            8. Draft tailored cover-letter snippets.
            9. Draft tailored resume bullets.
            10. Record interview notes and follow-up dates.
            11. Find stale applications.

            USER ID:
            {user_id}

            When the user asks for jobs:

            - Always use the search_jobs tool.
            - Do not invent job postings.
            - Consider the user's skills and preferences.
            - After receiving search results, rank or explain them
            according to the user's request.
            - If the user asks for the "best" jobs, consider relevance
            to the user's profile rather than simply returning the
            first results.

            When the user asks why a job matches:

            - Use explain_match.

            When the user asks to save a job:

            - Use save_job.

            When the user asks to move an application:

            - Use update_pipeline_stage.

            When the user asks for a cover letter:

            - Use draft_cover_letter.

            When the user asks for a resume bullet:

            - Use draft_resume_bullet.

            When the user provides an interview note:

            - Use log_interview_note.

            When the user asks about old or inactive applications:

            - Use find_stale_applications.

            Never invent:
            - user experience,
            - skills,
            - employers,
            - education,
            - achievements,
            - job requirements,
            - salary,
            - location,
            - application status.

            Be concise, useful and personalized to the current user.
            """
    }

    # --------------------------------------------------------
    # BUILD MESSAGE HISTORY
    # --------------------------------------------------------

    messages = [
        system_message
    ]

    if history:
        messages.extend(history)

    messages.append({
        "role": "user",
        "content": user_message
    })

    # --------------------------------------------------------
    # FIRST LLM CALL
    # --------------------------------------------------------

    response = call_llm(
        messages=messages,
        tools=tools_schema
    )

    message = response["choices"][0]["message"]

    # --------------------------------------------------------
    # TOOL-CALLING LOOP
    # --------------------------------------------------------

    tool_round = 0

    while message.get("tool_calls"):

        tool_round += 1

        if tool_round > MAX_TOOL_ROUNDS:

            return (
                "The agent reached the maximum number of "
                "tool calls for this request."
            )

        messages.append(message)

        for tool_call in message["tool_calls"]:

            tool_name = tool_call["function"]["name"]

            # ------------------------------------------------
            # PARSE TOOL ARGUMENTS
            # ------------------------------------------------

            try:

                arguments = json.loads(
                    tool_call["function"]["arguments"]
                )

            except json.JSONDecodeError as e:

                result = {
                    "error":
                        f"Invalid JSON tool arguments: {str(e)}"
                }

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(
                        result,
                        ensure_ascii=False
                    )
                })

                continue

            # ------------------------------------------------
            # EXECUTE TOOL
            # ------------------------------------------------

            result = execute_tool(
                tool_name,
                arguments,
                current_user_id=user_id
            )

            # ------------------------------------------------
            # SEND TOOL RESULT TO MODEL
            # ------------------------------------------------

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(
                    result,
                    ensure_ascii=False,
                    default=str
                )
            })

        # ----------------------------------------------------
        # SECOND / NEXT LLM CALL
        # ----------------------------------------------------

        response = call_llm(
            messages=messages,
            tools=tools_schema
        )

        message = response["choices"][0]["message"]

    # --------------------------------------------------------
    # FINAL RESPONSE
    # --------------------------------------------------------

    return message.get(
        "content",
        "I could not generate a response."
    )

# --------------------------------------------------------
# 16. TEST ALL AGENT CAPABILITIES
# --------------------------------------------------------

if __name__ == "__main__":

    TEST_USER_ID = 1
    history = []

    print("\n")
    print("=" * 70)
    print("TEST 1 - SEARCH AND RANK JOBS")
    print("=" * 70)

    response1 = call_agent(
        "Pronađi mi najbolje poslove za mene u Evropi.",
        TEST_USER_ID,
        history
    )

    print(response1)

    history.append({
        "role": "user",
        "content": "Pronađi mi najbolje poslove za mene u Evropi."
    })

    history.append({
        "role": "assistant",
        "content": response1
    })


    print("\n")
    print("=" * 70)
    print("TEST 2 - EXPLAIN WHY A JOB MATCHES")
    print("=" * 70)

    response2 = call_agent(
        "Koji od pronađenih poslova je najbolji za mene i zašto?",
        TEST_USER_ID,
        history
    )

    print(response2)

    history.append({
        "role": "user",
        "content": "Koji od pronađenih poslova je najbolji za mene i zašto?"
    })

    history.append({
        "role": "assistant",
        "content": response2
    })


    print("\n")
    print("=" * 70)
    print("TEST 3 - SAVE JOB TO PIPELINE")
    print("=" * 70)

    response3 = call_agent(
        "Sačuvaj prvi posao iz rezultata u moj pipeline kao saved.",
        TEST_USER_ID,
        history
    )

    print(response3)

    history.append({
        "role": "user",
        "content": "Sačuvaj prvi posao iz rezultata u moj pipeline kao saved."
    })

    history.append({
        "role": "assistant",
        "content": response3
    })


    print("\n")
    print("=" * 70)
    print("TEST 4 - UPDATE PIPELINE STAGE")
    print("=" * 70)

    response4 = call_agent(
        "Promijeni taj posao iz saved u applied.",
        TEST_USER_ID,
        history
    )

    print(response4)

    history.append({
        "role": "user",
        "content": "Promijeni taj posao iz saved u applied."
    })

    history.append({
        "role": "assistant",
        "content": response4
    })


    print("\n")
    print("=" * 70)
    print("TEST 5 - DRAFT COVER LETTER")
    print("=" * 70)

    response5 = call_agent(
        "Napiši mi kratak prilagođeni cover-letter snippet za taj posao.",
        TEST_USER_ID,
        history
    )

    print(response5)

    history.append({
        "role": "user",
        "content": "Napiši mi kratak prilagođeni cover-letter snippet za taj posao."
    })

    history.append({
        "role": "assistant",
        "content": response5
    })


    print("\n")
    print("=" * 70)
    print("TEST 6 - DRAFT RESUME BULLET")
    print("=" * 70)

    response6 = call_agent(
        "Napiši jednu prilagođenu stavku za moj CV za taj posao.",
        TEST_USER_ID,
        history
    )

    print(response6)

    history.append({
        "role": "user",
        "content": "Napiši jednu prilagođenu stavku za moj CV za taj posao."
    })

    history.append({
        "role": "assistant",
        "content": response6
    })


    print("\n")
    print("=" * 70)
    print("TEST 7 - LOG INTERVIEW NOTE")
    print("=" * 70)

    response7 = call_agent(
        "Zapiši bilješku za moj intervju: Razgovor je prošao dobro. "
        "Treba da pošaljem dodatne informacije sljedeće sedmice.",
        TEST_USER_ID,
        history
    )

    print(response7)

    history.append({
        "role": "user",
        "content":
            "Zapiši bilješku za moj intervju: Razgovor je prošao dobro. "
            "Treba da pošaljem dodatne informacije sljedeće sedmice."
    })

    history.append({
        "role": "assistant",
        "content": response7
    })


    print("\n")
    print("=" * 70)
    print("TEST 8 - FIND STALE APPLICATIONS")
    print("=" * 70)

    response8 = call_agent(
        "Pronađi moje aplikacije koje nisu ažurirane više od 14 dana.",
        TEST_USER_ID,
        history
    )

    print(response8)

    print("\n")
    print("=" * 70)
    print("ALL AGENT CAPABILITY TESTS FINISHED")
    print("=" * 70)




