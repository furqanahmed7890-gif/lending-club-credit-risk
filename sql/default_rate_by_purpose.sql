-- Default rate by the borrower's stated loan purpose (judged loans, purposes with 1,000+ loans).
SELECT
    purpose,
    COUNT(*) AS loans,
    ROUND(AVG(bad) * 100, 1) AS default_rate_pct,
    ROUND(AVG(int_rate)::numeric, 1) AS avg_int_rate_pct
FROM loans
WHERE bad IS NOT NULL
GROUP BY purpose
HAVING COUNT(*) >= 1000
ORDER BY default_rate_pct DESC;
