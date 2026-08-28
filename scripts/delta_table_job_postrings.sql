
/*Nisam sig da je ovo dobra shema*/
CREATE SCHEMA IF NOT EXISTS job_copilot.vector;
CREATE TABLE job_copilot.vector.job_postings_src (
    job_id STRING,
    title STRING,
    company STRING,
    description STRING,
    combined_text STRING   -- title + qualifications + description spojeno, za embedding
) TBLPROPERTIES (delta.enableChangeDataFeed = true);

ALTER TABLE job_copilot.vector.job_postings_src
SET TBLPROPERTIES (
    delta.enableChangeDataFeed = true
);