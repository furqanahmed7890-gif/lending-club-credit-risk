"""Turns raw Lending Club columns into model inputs.

Shared by the modeling notebooks and the app so both build features the same way.
Only uses information known on the day the loan is issued.
"""
import numpy as np
import pandas as pd

SUB_GRADES = [f"{grade}{n}" for grade in "ABCDEFG" for n in range(1, 6)]

EMP_YEARS = {"< 1 year": 0, "1 year": 1, "10+ years": 10}
EMP_YEARS.update({f"{n} years": n for n in range(2, 10)})

# Lending Club's own risk assessment and pricing
LC_PRICING = ["sub_grade_num", "int_rate", "installment"]

NUMERIC = LC_PRICING + [
    "loan_amnt", "term", "emp_years", "log_annual_inc", "dti", "fico", "credit_history_years",
    "delinq_2yrs", "inq_last_6mths", "open_acc", "total_acc", "pub_rec", "pub_rec_bankruptcies",
    "log_revol_bal", "revol_util", "mort_acc", "loan_to_income", "payment_to_income",
]
CATEGORICAL = ["purpose", "home_ownership", "verification_status", "application_type"]
FEATURES = NUMERIC + CATEGORICAL


def add_features(loans):
    income = loans["annual_inc"].where(loans["annual_inc"] > 0)
    X = pd.DataFrame({
        "sub_grade_num": loans["sub_grade"].map({s: i for i, s in enumerate(SUB_GRADES, start=1)}),
        "int_rate": loans["int_rate"],
        "installment": loans["installment"],
        "loan_amnt": loans["loan_amnt"],
        "term": loans["term"],
        "emp_years": loans["emp_length"].map(EMP_YEARS),
        "log_annual_inc": np.log1p(income),
        "dti": loans["dti"].clip(0, 100),
        "fico": (loans["fico_range_low"] + loans["fico_range_high"]) / 2,
        "credit_history_years": (loans["issue_d"] - loans["earliest_cr_line"]).dt.days / 365.25,
        "delinq_2yrs": loans["delinq_2yrs"],
        "inq_last_6mths": loans["inq_last_6mths"],
        "open_acc": loans["open_acc"],
        "total_acc": loans["total_acc"],
        "pub_rec": loans["pub_rec"],
        "pub_rec_bankruptcies": loans["pub_rec_bankruptcies"],
        "log_revol_bal": np.log1p(loans["revol_bal"]),
        "revol_util": loans["revol_util"].clip(0, 150),
        "mort_acc": loans["mort_acc"],
        "loan_to_income": (loans["loan_amnt"] / income).clip(upper=5),
        "payment_to_income": (loans["installment"] * 12 / income).clip(upper=2),
    }, index=loans.index)
    for col in CATEGORICAL:
        X[col] = loans[col].fillna("missing").astype(str)
    return X[FEATURES]


def monthly_installment(amount, annual_rate_pct, term_months):
    """Standard amortizing loan payment."""
    r = annual_rate_pct / 100 / 12
    return amount * r / (1 - (1 + r) ** -term_months)
