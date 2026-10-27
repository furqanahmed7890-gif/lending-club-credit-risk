-- A small summary table (a few thousand rows) the app queries instead of the 2.26M-row loans table.
-- Every sum is additive, so any filter or grouping in the app gives exact rates.
DROP TABLE IF EXISTS loan_cube;

CREATE TABLE loan_cube AS
SELECT
    issue_year,
    term,
    grade,
    purpose,
    COUNT(*) AS loans,
    SUM(funded_amnt) AS funded,
    SUM(int_rate * funded_amnt) AS rate_x_funded,
    COUNT(bad) AS judged_loans,
    COALESCE(SUM(bad), 0) AS defaults,
    SUM(CASE WHEN bad IS NOT NULL THEN funded_amnt ELSE 0 END) AS judged_funded,
    SUM(CASE WHEN bad IS NOT NULL THEN total_pymnt - collection_recovery_fee ELSE 0 END) AS judged_collected,
    SUM(CASE WHEN bad = 1 THEN funded_amnt - total_rec_prncp - (recoveries - collection_recovery_fee) ELSE 0 END) AS principal_loss,
    SUM(CASE WHEN loan_status IN ('Current', 'In Grace Period', 'Late (16-30 days)', 'Late (31-120 days)', 'Default')
             THEN funded_amnt - total_rec_prncp ELSE 0 END) AS outstanding
FROM loans
GROUP BY issue_year, term, grade, purpose;
