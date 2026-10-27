-- Loans still on the books at the March 2019 snapshot: outstanding principal and early delinquency by grade.
SELECT
    grade,
    COUNT(*) AS active_loans,
    ROUND((SUM(funded_amnt - total_rec_prncp) / 1e6)::numeric, 1) AS outstanding_millions,
    ROUND(AVG(CASE WHEN loan_status = 'Current' THEN 0 ELSE 1 END) * 100, 2) AS delinquent_pct
FROM loans
WHERE loan_status IN ('Current', 'In Grace Period', 'Late (16-30 days)', 'Late (31-120 days)', 'Default')
GROUP BY grade
ORDER BY grade;
