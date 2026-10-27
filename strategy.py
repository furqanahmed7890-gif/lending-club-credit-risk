import streamlit as st

from db import run_query

st.title("Approval Strategy & Stress Test")

st.header("Which loans should a lender approve?")
st.write(
    "Suppose a lender could fund only part of the 2015-2016 applications. It can rank them by Lending Club's "
    "sub-grade, or by the model's predicted PD, and approve from the top. These are the real outcomes of "
    "372,811 loans the model never saw during training."
)

curve_sql = """
SELECT policy, approval_rate_pct, approved_loans, max_pd_pct, default_rate_pct, loss_rate_pct, net_return_pct
FROM strategy_curve
ORDER BY policy, approval_rate_pct
"""
curve = run_query(curve_sql)

rate = st.select_slider("Share of applications approved (%)", options=list(range(50, 101, 5)), value=80)
model_row = curve[(curve["policy"] == "Model") & (curve["approval_rate_pct"] == rate)].iloc[0]
grade_row = curve[(curve["policy"] == "Sub-grade") & (curve["approval_rate_pct"] == rate)].iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("Default rate, model", f"{model_row['default_rate_pct']:.2f}%",
            delta=f"{model_row['default_rate_pct'] - grade_row['default_rate_pct']:+.2f} pts vs. sub-grade",
            delta_color="inverse")
col2.metric("Principal lost, model", f"{model_row['loss_rate_pct']:.2f}%",
            delta=f"{model_row['loss_rate_pct'] - grade_row['loss_rate_pct']:+.2f} pts vs. sub-grade",
            delta_color="inverse")
col3.metric("Net return, model", f"{model_row['net_return_pct']:.2f}%",
            delta=f"{model_row['net_return_pct'] - grade_row['net_return_pct']:+.2f} pts vs. sub-grade")
if rate < 100:
    st.caption(f"At {rate}% approval the model declines every application with a predicted PD above "
               f"{model_row['max_pd_pct']:.1f}%.")

left, right = st.columns(2)
default_chart = curve.pivot(index="approval_rate_pct", columns="policy", values="default_rate_pct")
left.markdown("**Default rate of approved loans (%)**")
left.line_chart(default_chart, x_label="Share approved (%)")
return_chart = curve.pivot(index="approval_rate_pct", columns="policy", values="net_return_pct")
right.markdown("**Lifetime net return of approved loans (%)**")
right.line_chart(return_chart, x_label="Share approved (%)")

st.write(
    "Ranking by the model beats ranking by sub-grade at every approval rate: fewer defaults and a higher "
    "return. At 80% approval it earns $12.4 million more. Declining just the riskiest 5% by predicted PD would "
    "have earned more in total than approving everyone, because Lending Club underpriced its riskiest "
    "2015-2016 borrowers."
)
with st.expander("See the data and SQL"):
    st.dataframe(curve, hide_index=True)
    st.code(curve_sql.strip(), language="sql")

st.header("Stress test: loans still running")
st.write(
    "Loans that had not reached full term by March 2019 are the part of the book whose losses are still "
    "uncertain. Each scenario scales the model's PD and adds to loss given default, because recoveries "
    "usually fall in a downturn. The severe case doubles PD, roughly the gap between loans issued in "
    "2007-2008 and those issued in 2010-2011."
)

stress_sql = """
SELECT
    scenario,
    ROUND((SUM(funded) / 1e9)::numeric, 2) AS funded_billions,
    ROUND((SUM(expected_loss) / 1e9)::numeric, 2) AS expected_loss_billions,
    ROUND((SUM(expected_loss) / SUM(funded) * 100)::numeric, 2) AS loss_rate_pct
FROM stress_test
GROUP BY scenario
ORDER BY expected_loss_billions
"""
stress = run_query(stress_sql)

cols = st.columns(len(stress))
baseline = float(stress["expected_loss_billions"].iloc[0])
for col, (_, row) in zip(cols, stress.iterrows()):
    loss = float(row["expected_loss_billions"])
    delta = None if loss == baseline else f"+${loss - baseline:.2f}B vs. baseline"
    col.metric(row["scenario"], f"${loss:.2f}B", delta=delta, delta_color="inverse")
    col.caption(f"{float(row['loss_rate_pct']):.1f}% of ${float(row['funded_billions']):.1f}B funded")

grade_sql = """
SELECT
    grade,
    scenario,
    ROUND((expected_loss / funded * 100)::numeric, 2) AS loss_rate_pct
FROM stress_test
ORDER BY grade
"""
by_grade = run_query(grade_sql)
chart = by_grade.pivot(index="grade", columns="scenario", values="loss_rate_pct")[stress["scenario"].tolist()]
st.markdown("**Expected lifetime loss by grade (% of amount funded)**")
st.bar_chart(chart, stack=False, x_label="Grade", y_label="% of funded")
with st.expander("See the data and SQL"):
    st.dataframe(stress, hide_index=True)
    st.code(stress_sql.strip(), language="sql")
    st.dataframe(by_grade, hide_index=True)
    st.code(grade_sql.strip(), language="sql")
