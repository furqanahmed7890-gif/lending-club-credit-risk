-- Default rate by the year the loan was issued (its vintage) and its term.
-- Vintages that have not fully matured by the March 2019 snapshot have no judged loans yet.
SELECT
    issue_year,
    term,
    COUNT(*) AS loans,
    COUNT(bad) AS judged_loans,
    ROUND(AVG(bad) * 100, 1) AS default_rate_pct
FROM loans
GROUP BY issue_year, term
ORDER BY issue_year, term;
