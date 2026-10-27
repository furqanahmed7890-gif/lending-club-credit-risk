from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import streamlit as st
from scipy.special import expit, logit

from features import SUB_GRADES, add_features, monthly_installment

MODEL_PATH = Path(__file__).parent / "models" / "pd_model.joblib"


@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


saved = load_model()
model = saved["model"]
calibration = saved["calibration"]
severity = saved["severity_recalibrated"]
grade_rates = saved["grade_default_rates"]


@st.cache_resource
def load_explainer():
    return shap.TreeExplainer(model.named_steps["model"])


explainer = load_explainer()

PURPOSES = {
    "Debt consolidation": "debt_consolidation", "Credit card": "credit_card", "Home improvement": "home_improvement",
    "Major purchase": "major_purchase", "Small business": "small_business", "Car": "car", "Medical": "medical",
    "Moving": "moving", "Vacation": "vacation", "House": "house", "Wedding": "wedding", "Other": "other",
}
HOME = {"Rent": "RENT", "Mortgage": "MORTGAGE", "Own": "OWN"}
VERIFICATION = {"Not verified": "Not Verified", "Source verified": "Source Verified", "Verified": "Verified"}
EMPLOYMENT = ["< 1 year", "1 year"] + [f"{n} years" for n in range(2, 10)] + ["10+ years", "Not provided"]

FRIENDLY_NAMES = {
    "sub_grade_num": "Sub-grade", "int_rate": "Interest rate", "installment": "Monthly payment",
    "loan_amnt": "Loan amount", "term": "Term", "emp_years": "Years employed", "log_annual_inc": "Annual income",
    "dti": "Debt-to-income", "fico": "FICO score", "credit_history_years": "Credit history (years)",
    "delinq_2yrs": "Delinquencies (2 yrs)", "inq_last_6mths": "Credit inquiries (6 mo)", "open_acc": "Open accounts",
    "total_acc": "Total accounts", "pub_rec": "Public records", "pub_rec_bankruptcies": "Bankruptcies",
    "log_revol_bal": "Revolving balance", "revol_util": "Revolving utilization", "mort_acc": "Mortgage accounts",
    "loan_to_income": "Loan / income", "payment_to_income": "Payments / income",
}

st.title("Score a Loan")
st.write("Enter a loan application to estimate its probability of default (PD) and expected dollar loss.")

with st.form("loan_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Loan**")
        amount = st.number_input("Loan amount ($)", min_value=1000, max_value=40000, value=15000, step=500)
        term = st.selectbox("Term", [36, 60], format_func=lambda t: f"{t} months")
        sub_grade = st.selectbox("Lending Club sub-grade", SUB_GRADES, index=SUB_GRADES.index("B4"))
        int_rate = st.number_input(
            "Interest rate (%)", min_value=5.0, max_value=31.0, value=11.5, step=0.1,
            help="Typical rates: A about 7%, B 11%, C 14%, D 17%, E 20%, F 23%, G 25%.",
        )
        purpose = st.selectbox("Purpose", list(PURPOSES.keys()))
        joint = st.selectbox("Application type", ["Individual", "Joint"])

    with col2:
        st.markdown("**Borrower**")
        income = st.number_input("Annual income ($)", min_value=5000, max_value=1000000, value=70000, step=1000)
        employment = st.selectbox("Employment length", EMPLOYMENT, index=EMPLOYMENT.index("10+ years"))
        home = st.selectbox("Home ownership", list(HOME.keys()))
        verification = st.selectbox("Income verification", list(VERIFICATION.keys()))
        dti = st.number_input("Debt-to-income ratio (%)", min_value=0.0, max_value=60.0, value=18.0, step=0.5,
                              help="Monthly debt payments, excluding mortgage and this loan, as a % of monthly income.")
        mort_acc = st.number_input("Mortgage accounts", min_value=0, max_value=20, value=1)

    with col3:
        st.markdown("**Credit report**")
        fico = st.slider("FICO score", 660, 850, 700, step=5)
        history = st.number_input("Credit history (years)", min_value=1, max_value=60, value=15)
        open_acc = st.number_input("Open credit lines", min_value=0, max_value=60, value=11)
        total_acc = st.number_input("Total credit lines", min_value=1, max_value=120, value=24)
        revol_bal = st.number_input("Revolving balance ($)", min_value=0, max_value=500000, value=15000, step=500)
        revol_util = st.slider("Revolving utilization (%)", 0, 120, 50)
        inquiries = st.number_input("Credit inquiries, last 6 months", min_value=0, max_value=10, value=0)
        delinquencies = st.number_input("Delinquencies, last 2 years", min_value=0, max_value=20, value=0)
        public_records = st.number_input("Public records", min_value=0, max_value=10, value=0)
        bankruptcies = st.number_input("Bankruptcies", min_value=0, max_value=10, value=0)

    submitted = st.form_submit_button("Score this loan")

if submitted:
    today = pd.Timestamp.today().normalize()
    application = pd.DataFrame([{
        "sub_grade": sub_grade,
        "int_rate": int_rate,
        "installment": monthly_installment(amount, int_rate, term),
        "loan_amnt": amount,
        "term": term,
        "emp_length": None if employment == "Not provided" else employment,
        "annual_inc": income,
        "dti": dti,
        "fico_range_low": fico,
        "fico_range_high": fico + 4,
        "issue_d": today,
        "earliest_cr_line": today - pd.DateOffset(years=history),
        "delinq_2yrs": delinquencies,
        "inq_last_6mths": inquiries,
        "open_acc": open_acc,
        "total_acc": max(total_acc, open_acc),
        "pub_rec": public_records,
        "pub_rec_bankruptcies": bankruptcies,
        "revol_bal": revol_bal,
        "revol_util": revol_util,
        "mort_acc": mort_acc,
        "purpose": PURPOSES[purpose],
        "home_ownership": HOME[home],
        "verification_status": VERIFICATION[verification],
        "application_type": "Joint App" if joint == "Joint" else "Individual",
    }])
    X = add_features(application)

    raw_pd = model.predict_proba(X)[:, 1][0]
    pd_hat = float(expit(calibration["intercept"] + calibration["slope"] * logit(raw_pd)))
    loss_rate = severity[term]["ead_factor"] * severity[term]["lgd"]
    expected_loss = pd_hat * loss_rate * amount
    similar_grade = min(grade_rates, key=lambda g: abs(grade_rates[g] - raw_pd))

    st.subheader("Result")
    col1, col2, col3 = st.columns(3)
    col1.metric("Probability of default", f"{pd_hat:.1%}", help="Chance the loan is charged off over its life")
    col2.metric("Expected loss", f"${expected_loss:,.0f}", help="PD x share still owed at default x loss given default x amount")
    col3.metric("Risk similar to", f"Grade {similar_grade}", help="The Lending Club grade with the closest historical default rate")

    st.write(
        f"If this loan defaults, about {severity[term]['ead_factor']:.0%} of the amount would still be owed and "
        f"about {severity[term]['lgd']:.0%} of that would never be recovered, so a default costs about "
        f"**${loss_rate * amount:,.0f}**. Weighted by the {pd_hat:.1%} chance of default, the expected loss is "
        f"**{expected_loss / amount:.1%}** of the loan."
    )
    if similar_grade != sub_grade[0]:
        direction = "riskier" if similar_grade > sub_grade[0] else "safer"
        st.info(f"The model rates this borrower **{direction}** than Lending Club's grade {sub_grade[0]}.")

    preprocess = model.named_steps["preprocess"]
    feature_names = [name.split("__")[1] for name in preprocess.get_feature_names_out()]
    transformed = pd.DataFrame(preprocess.transform(X), columns=feature_names)
    explanation = explainer(transformed)[0]

    input_display = {
        "sub_grade_num": sub_grade, "int_rate": f"{int_rate:.1f}%", "installment": f"${X['installment'].iloc[0]:,.0f}",
        "loan_amnt": f"${amount:,}", "term": f"{term} mo", "emp_years": employment, "log_annual_inc": f"${income:,}",
        "dti": f"{dti:.1f}", "fico": str(fico), "credit_history_years": str(history), "delinq_2yrs": str(delinquencies),
        "inq_last_6mths": str(inquiries), "open_acc": str(open_acc), "total_acc": str(total_acc),
        "pub_rec": str(public_records), "pub_rec_bankruptcies": str(bankruptcies), "log_revol_bal": f"${revol_bal:,}",
        "revol_util": f"{revol_util}%", "mort_acc": str(mort_acc),
        "loan_to_income": f"{X['loan_to_income'].iloc[0]:.2f}", "payment_to_income": f"{X['payment_to_income'].iloc[0]:.2f}",
    }
    labels = []
    for name, value in zip(feature_names, transformed.iloc[0]):
        labels.append(input_display.get(name, "Yes" if value == 1 else "No"))

    explanation.data = np.array(labels, dtype=object)
    explanation.feature_names = [
        FRIENDLY_NAMES.get(name, name.replace("_", " ").capitalize()) for name in feature_names
    ]

    st.subheader("Why this result?")
    st.write("Red bars pushed the risk **up**, blue bars pushed it **down**. Values are on the model's "
             "log-odds scale, before recalibration.")
    shap.plots.waterfall(explanation, max_display=12, show=False)
    fig = plt.gcf()
    st.pyplot(fig)
    plt.close(fig)

    st.caption("Educational project built on historical Lending Club data. Not a lending decision tool.")
