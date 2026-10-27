import streamlit as st

from db import run_query

GRADES = list("ABCDEFG")

st.title("Loan Portfolio Overview")
st.write(
    "2.26 million Lending Club loans issued 2007-2018, as of the March 2019 snapshot. "
    "Every number on this page is a live SQL query against PostgreSQL."
)

with st.sidebar:
    st.header("Filters")
    years = st.slider("Year issued", 2007, 2018, (2007, 2018))
    terms = st.multiselect("Term (months)", [36, 60], default=[36, 60])
    grades = st.multiselect("Grade", GRADES, default=GRADES)

if not terms or not grades:
    st.warning("Pick at least one term and one grade.")
    st.stop()

params = {"start": years[0], "end": years[1], "terms": terms, "grades": grades}
FILTER = "WHERE issue_year BETWEEN :start AND :end AND term = ANY(:terms) AND grade = ANY(:grades)"


def show_data(data, sql):
    with st.expander("See the data and SQL"):
        st.dataframe(data, hide_index=True)
        st.code(sql.strip(), language="sql")


kpi_sql = f"""
SELECT
    SUM(loans) AS loans,
    SUM(funded) / 1e9 AS funded_billions,
    SUM(defaults)::numeric / NULLIF(SUM(judged_loans), 0) * 100 AS default_rate_pct,
    SUM(principal_loss) / NULLIF(SUM(judged_funded), 0) * 100 AS loss_rate_pct,
    SUM(outstanding) / 1e9 AS outstanding_billions
FROM loan_cube
{FILTER}
"""
kpis = run_query(kpi_sql, params).iloc[0]


def pct(value):
    return "n/a" if value is None or value != value else f"{float(value):.1f}%"


col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Loans", f"{int(kpis['loans'] or 0) / 1e6:.2f}M")
col2.metric("Funded", f"${float(kpis['funded_billions'] or 0):.1f}B")
col3.metric("Default rate", pct(kpis["default_rate_pct"]), help="Matured loans only")
col4.metric("Loss rate", pct(kpis["loss_rate_pct"]), help="Share of the amount funded that was lost, matured loans only")
col5.metric("Outstanding", f"${float(kpis['outstanding_billions'] or 0):.2f}B", help="Principal still owed at the March 2019 snapshot")

left, right = st.columns(2)

with left:
    st.subheader("Risk by grade")
    grade_sql = f"""
SELECT
    grade,
    SUM(judged_loans) AS matured_loans,
    ROUND(SUM(defaults)::numeric / NULLIF(SUM(judged_loans), 0) * 100, 1) AS default_rate_pct,
    ROUND((SUM(principal_loss) / NULLIF(SUM(judged_funded), 0) * 100)::numeric, 1) AS loss_rate_pct,
    ROUND((SUM(rate_x_funded) / SUM(funded))::numeric, 1) AS avg_int_rate_pct
FROM loan_cube
{FILTER}
GROUP BY grade
ORDER BY grade
"""
    by_grade = run_query(grade_sql, params)
    chart = by_grade.rename(columns={
        "default_rate_pct": "Default rate", "loss_rate_pct": "Loss rate", "avg_int_rate_pct": "Interest rate",
    })
    st.bar_chart(chart, x="grade", y=["Default rate", "Loss rate", "Interest rate"], stack=False,
                 x_label="Grade", y_label="%")
    st.write("Grades rank risk cleanly, and interest rates rise with them. The extra interest on lower grades "
             "has historically more than covered their extra losses.")
    show_data(by_grade, grade_sql)

with right:
    st.subheader("Default rate by vintage")
    vintage_sql = f"""
SELECT
    issue_year,
    term,
    SUM(judged_loans) AS matured_loans,
    ROUND(SUM(defaults)::numeric / NULLIF(SUM(judged_loans), 0) * 100, 1) AS default_rate_pct
FROM loan_cube
{FILTER}
GROUP BY issue_year, term
HAVING SUM(judged_loans) >= 1000
ORDER BY issue_year, term
"""
    vintages = run_query(vintage_sql, params)
    if vintages.empty:
        st.info("No matured loans for this selection yet.")
    else:
        chart = vintages.pivot(index="issue_year", columns="term", values="default_rate_pct")
        chart.columns = [f"{term}-month" for term in chart.columns]
        chart.index = chart.index.astype(str)
        st.line_chart(chart, x_label="Year issued", y_label="Default rate (%)")
    st.write("60-month loans default about twice as often as 36-month loans. Defaults bottomed out for "
             "2010-2011 loans and rose again as Lending Club grew.")
    show_data(vintages, vintage_sql)

left, right = st.columns(2)

with left:
    st.subheader("Projected vs. realized lifetime loss")
    loss_sql = """
SELECT
    issue_year,
    term,
    projected_loss_rate_pct,
    realized_loss_rate_pct
FROM vintage_loss
WHERE issue_year BETWEEN :start AND :end AND term = ANY(:terms) AND loans >= 1000
ORDER BY issue_year, term
"""
    losses = run_query(loss_sql, params)
    chart = losses.pivot(index="issue_year", columns="term", values=["projected_loss_rate_pct", "realized_loss_rate_pct"])
    chart.columns = [f"{term}-month {'projected' if kind.startswith('projected') else 'realized'}" for kind, term in chart.columns]
    chart.index = chart.index.astype(str)
    st.line_chart(chart, x_label="Year issued", y_label="Principal lost (% of funded)")
    st.write("Projected = the model's expected loss at origination. Realized = what was actually lost, shown "
             "once a vintage has (almost) fully matured. Grade filters do not apply to this chart.")
    show_data(losses, loss_sql)

with right:
    st.subheader("Volume by year")
    volume_sql = f"""
SELECT
    issue_year,
    ROUND((SUM(funded) / 1e9)::numeric, 2) AS funded_billions,
    SUM(loans) AS loans
FROM loan_cube
{FILTER}
GROUP BY issue_year
ORDER BY issue_year
"""
    volume = run_query(volume_sql, params)
    st.bar_chart(volume.astype({"issue_year": str}), x="issue_year", y="funded_billions", x_label="Year issued",
                 y_label="Funded ($ billions)")
    st.write("Most of the book was issued from 2015 onward, which is why so much of it was still running "
             "at the snapshot.")
    show_data(volume, volume_sql)

st.subheader("Default rate by loan purpose")
purpose_sql = f"""
SELECT
    purpose,
    SUM(judged_loans) AS matured_loans,
    ROUND(SUM(defaults)::numeric / NULLIF(SUM(judged_loans), 0) * 100, 1) AS default_rate_pct,
    ROUND((SUM(rate_x_funded) / SUM(funded))::numeric, 1) AS avg_int_rate_pct
FROM loan_cube
{FILTER}
GROUP BY purpose
HAVING SUM(judged_loans) >= 500
ORDER BY default_rate_pct DESC
"""
purposes = run_query(purpose_sql, params)
st.bar_chart(purposes, x="purpose", y="default_rate_pct", horizontal=True, x_label="", y_label="Default rate (%)",
             sort="-default_rate_pct")
show_data(purposes, purpose_sql)
