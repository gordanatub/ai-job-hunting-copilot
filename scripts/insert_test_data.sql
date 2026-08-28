/*
Skripta se izvrsava unutar Lakebase Postgres sql editora

*/
INSERT INTO users (email, full_name)
VALUES
    ('test.user1@example.com', 'Marko Test'),
    ('test.user2@example.com', 'Ana Test') ON CONFLICT (email) DO NOTHING;

INSERT INTO profiles (
    user_id,
    target_roles,
    min_salary,
    remote_only,
    preferred_locations,
    resume_text
)
SELECT
    user_id,
    ARRAY['Backend Developer', 'Java Developer'],
    2500,
    true,
    ARRAY['Remote', 'Banja Luka', 'Beograd'],
    'Software Engineering student with experience in Java, Spring Boot, SQL, REST APIs and distributed systems.'
FROM users
WHERE email = 'test.user1@example.com'
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO profiles (
    user_id,
    target_roles,
    min_salary,
    remote_only,
    preferred_locations,
    resume_text
)
SELECT
    user_id,
    ARRAY['Data Engineer', 'Python Developer'],
    2500,
    true,
    ARRAY['Remote', 'Banja Luka'],
    'Software engineering student with experience in Python, PySpark, Databricks, SQL and machine learning.'
FROM users
WHERE email = 'test.user2@example.com'
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO skills (user_id, skill_name, proficiency, years_exp)
SELECT user_id, 'Java', 'advanced', 3
FROM users
WHERE email = 'test.user1@example.com';

INSERT INTO skills (user_id, skill_name, proficiency, years_exp)
SELECT user_id, 'Spring Boot', 'intermediate', 2
FROM users
WHERE email = 'test.user1@example.com';

INSERT INTO skills (user_id, skill_name, proficiency, years_exp)
SELECT user_id, 'SQL', 'advanced', 3
FROM users
WHERE email = 'test.user1@example.com';

INSERT INTO skills (user_id, skill_name, proficiency, years_exp)
SELECT user_id, 'Python', 'advanced', 3
FROM users
WHERE email = 'test.user2@example.com';

INSERT INTO skills (user_id, skill_name, proficiency, years_exp)
SELECT user_id, 'PySpark', 'intermediate', 2
FROM users
WHERE email = 'test.user2@example.com';

INSERT INTO skills (user_id, skill_name, proficiency, years_exp)
SELECT user_id, 'Databricks', 'intermediate', 1
FROM users
WHERE email = 'test.user2@example.com';

INSERT INTO skills (user_id, skill_name, proficiency, years_exp)
SELECT user_id, 'SQL', 'advanced', 3
FROM users
WHERE email = 'test.user2@example.com';
