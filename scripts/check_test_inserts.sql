/*
Izvrsava se u Lakebase Postgres sql editoru
*/

SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
UNION ALL
SELECT 'profiles', COUNT(*) FROM profiles
UNION ALL
SELECT 'skills', COUNT(*) FROM skills
UNION ALL
SELECT 'job_postings', COUNT(*) FROM job_postings
UNION ALL
SELECT 'applications', COUNT(*) FROM applications
UNION ALL
SELECT 'saved_jobs', COUNT(*) FROM saved_jobs
UNION ALL
SELECT 'interview_notes', COUNT(*) FROM interview_notes
UNION ALL
SELECT 'contacts', COUNT(*) FROM contacts;