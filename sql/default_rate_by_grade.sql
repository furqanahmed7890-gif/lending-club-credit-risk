-- Default rate, pricing, principal loss, and realized return by Lending Club grade (judged loans only).
-- Return is lifetime (not annualized): everything collected net of collection fees vs. the amount funded.
SELECT
    grade,
    COUNT(*) AS loans,
    ROUND(AVG(bad) * 100, 1) AS default_rate_pct,
    ROUND(AVG(int_rate)::numeric, 1) AS avg_int_rate_pct,
    ROUND((SUM(CASE WHEN bad = 1 THEN funded_amnt - total_rec_prncp - (recoveries - collection_recovery_fee) ELSE 0 END)
           / SUM(funded_amnt) * 100)::numeric, 1) AS loss_rate_pct,
    ROUND(((SUM(total_pymnt - collection_recovery_fee) / SUM(funded_amnt) - 1) * 100)::numeric, 1) AS net_return_pct
FROM loans
WHERE bad IS NOT NULL
GROUP BY grade
ORDER BY grade;
