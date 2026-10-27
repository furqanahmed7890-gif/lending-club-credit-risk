-- Headline numbers for the whole book. Default rate uses judged (matured) loans only.
SELECT
    COUNT(*) AS loans,
    ROUND((SUM(funded_amnt) / 1e9)::numeric, 2) AS funded_billions,
    COUNT(bad) AS judged_loans,
    ROUND(AVG(bad) * 100, 2) AS default_rate_pct,
    ROUND(AVG(int_rate)::numeric, 2) AS avg_int_rate_pct,
    MIN(issue_d)::date AS first_issued,
    MAX(issue_d)::date AS last_issued
FROM loans;
