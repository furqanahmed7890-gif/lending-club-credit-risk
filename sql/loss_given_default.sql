-- How much is lost when a loan defaults, by term.
--   exposure at default (EAD) = principal still owed when the loan defaulted
--   loss given default (LGD)  = share of that exposure never recovered, net of collection fees
WITH defaults AS (
    SELECT
        term,
        funded_amnt,
        funded_amnt - total_rec_prncp AS ead,
        recoveries - collection_recovery_fee AS net_recovery
    FROM loans
    WHERE bad = 1
)
SELECT
    term,
    COUNT(*) AS defaults,
    ROUND((SUM(ead) / SUM(funded_amnt) * 100)::numeric, 1) AS ead_pct_of_funded,
    ROUND(((1 - SUM(net_recovery) / SUM(ead)) * 100)::numeric, 1) AS lgd_pct,
    ROUND((SUM(ead - net_recovery) / SUM(funded_amnt) * 100)::numeric, 1) AS loss_pct_of_funded
FROM defaults
GROUP BY term
ORDER BY term;
