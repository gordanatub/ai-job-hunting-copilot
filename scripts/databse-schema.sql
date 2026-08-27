/*
In Lakebase, databases are stored on branches. By default, a project has one branch and one database.
You can select the branch and database to use from the drop-down menus above.

Try generating sample data and querying it by running the example statements below, or clear
the editor to skip this guide.
*/

CREATE TABLE IF NOT EXISTS playing_with_lakebase(id SERIAL PRIMARY KEY, name TEXT NOT NULL, value REAL);
INSERT INTO playing_with_lakebase(name, value)
  SELECT LEFT(md5(i::TEXT), 10), random() FROM generate_series(1, 10) s(i);
SELECT * FROM playing_with_lakebase;

CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    full_name     TEXT,
    created_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE profiles (
    profile_id    SERIAL PRIMARY KEY,
    user_id       INTEGER REFERENCES users(user_id),
    target_roles  TEXT[],           -- npr. {'Data Engineer','Backend Developer'}
    min_salary    NUMERIC,
    remote_only   BOOLEAN DEFAULT false,
    preferred_locations TEXT[],
    resume_text   TEXT,
    updated_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE skills (
    skill_id      SERIAL PRIMARY KEY,
    user_id       INTEGER REFERENCES users(user_id),
    skill_name    TEXT NOT NULL,
    proficiency   TEXT CHECK (proficiency IN ('beginner','intermediate','advanced','expert')),
    years_exp     NUMERIC
);

CREATE TABLE job_postings (
    job_id        TEXT PRIMARY KEY,      -- source + external_id iz Delta tabele
    source        TEXT,
    title         TEXT,
    company       TEXT,
    location      TEXT,
    description   TEXT,
    url           TEXT,
    salary_min    NUMERIC,
    salary_max    NUMERIC,
    remote        BOOLEAN,
    posted_at     TIMESTAMP,
    synced_at     TIMESTAMP DEFAULT now()
);

CREATE TABLE applications (
    application_id SERIAL PRIMARY KEY,
    user_id        INTEGER REFERENCES users(user_id),
    job_id         TEXT REFERENCES job_postings(job_id),
    stage          TEXT CHECK (stage IN ('saved','applied','interviewing','rejected','offer')) DEFAULT 'saved',
    cover_letter_snippet TEXT,
    applied_at     TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT now()
);

CREATE TABLE saved_jobs (
    saved_id     SERIAL PRIMARY KEY,
    user_id      INTEGER REFERENCES users(user_id),
    job_id       TEXT REFERENCES job_postings(job_id),
    saved_at     TIMESTAMP DEFAULT now(),
    notes        TEXT
);

CREATE TABLE interview_notes (
    note_id       SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES applications(application_id),
    note          TEXT,
    follow_up_date DATE,
    created_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE contacts (
    contact_id    SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES applications(application_id),
    name          TEXT,
    role          TEXT,
    email         TEXT,
    linkedin_url  TEXT
);