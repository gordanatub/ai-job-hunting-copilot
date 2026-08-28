/*Duplikati >0 */
SELECT
    source,
    job_id,
    COUNT(*) AS cnt
FROM job_postings
GROUP BY source, job_id
HAVING COUNT(*) > 1;
/*Oglasi bez naslova >0 */
SELECT COUNT(*)
FROM job_postings
WHERE title IS NULL OR trim(title) = '';
/*Oglasi bez opisa >0 */
SELECT COUNT(*)
FROM job_postings
WHERE description IS NULL OR trim(description) = '';
/*Neispravne plate >0 */
SELECT COUNT(*)
FROM job_postings
WHERE salary_min IS NOT NULL
  AND salary_max IS NOT NULL
  AND salary_min > salary_max;
/*Neispravan id > 0*/
SELECT COUNT(*)
FROM job_postings
WHERE job_id IS NULL OR trim(job_id) = '';