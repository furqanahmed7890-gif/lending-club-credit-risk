# Loan Portfolio Credit Risk

**Live demo: [loan-portfolio-credit-risk-fa.streamlit.app](https://loan-portfolio-credit-risk-fa.streamlit.app/)**

An end-to-end credit risk project on 2.26 million Lending Club loans (\$34 billion, 2007-2018). It predicts
each loan's probability of default (PD), turns PD into an expected dollar loss, backtests the estimate
against what actually happened, stress-tests the loans still running, and compares approval strategies.
The analysis runs on PostgreSQL, and a Streamlit app presents the results.

![Default rate and interest rate by grade](images/default_rate_by_grade.png)

## Highlights
- **Data engineering:** 393 MB raw file audited column by column (151 → 37 columns), cleaned to Parquet,
  and bulk-loaded into PostgreSQL with `COPY` (2.26M rows in about 2 minutes).
- **Outcome definition without look-ahead:** only loans past their full term are judged, so recent loans
  can't pass as good just because they haven't defaulted yet.
- **SQL portfolio analysis:** default and loss rates by grade, vintage, term, and purpose; loss given
  default; live-book exposure and delinquency. All queries live in [`sql/`](sql/).
- **PD model tested out of time:** trained on 2007-2014 loans, tested on 372,811 loans from 2015-2016.
  XGBoost beats Lending Club's own sub-grade and logistic regression, and SHAP explains every prediction.
- **Expected loss, backtest, and recalibration:** EL = PD × exposure at default × loss given default ×
  amount funded. The backtest caught real drift, and the model is recalibrated the way a lender would.
- **Stress test and approval strategy:** recession scenarios on the \$23.6B still running, and
  model-based vs. grade-based approval at every approval rate.
- **App:** four Streamlit pages (Portfolio, Score a Loan, Strategy & Stress Test, About), backed by live SQL.

## Results

**PD model, out-of-time test (372,811 loans issued 2015-2016)**

| Model | AUC | Gini | KS |
|---|---|---|---|
| Lending Club sub-grade (baseline) | 0.682 | 0.364 | 0.266 |
| Logistic regression | 0.687 | 0.374 | 0.272 |
| XGBoost without Lending Club's grade or rate | 0.687 | 0.375 | 0.270 |
| **XGBoost** | **0.700** | **0.400** | **0.291** |

**Expected loss and portfolio**

| Measure | Result |
|---|---|
| Backtest, 2015-2016 loans (original model) | expected 6.44% lost, actual 7.90% |
| After recalibration | expected 7.67%, actual 7.90% (within 3%) |
| Loans still running at the snapshot | 1.47M loans, \$23.6B funded |
| Lifetime expected loss: baseline / mild / severe recession | \$2.94B / \$4.66B / \$6.52B |
| Approve 80%: model vs. sub-grade ranking | default rate 11.60% vs. 12.02%, +\$12.4M profit |

## Key findings
- **Grade ranks risk cleanly:** default rates climb from 5.5% (A) to 38.9% (G), and interest rates
  rise with them (7.1% to 24.8%).
- **Term matters as much as grade:** 60-month loans default about twice as often as 36-month loans
  issued the same year.
- **Vintages:** defaults bottomed out for 2010-2011 loans and rose again through 2016 as Lending Club grew.
- **Loss given default is about 89%** of the balance still owed, or 52-62% of the original amount.
- **Live book:** \$9.51B outstanding at the March 2019 snapshot, with early delinquency rising from 1.2%
  (grade A) to 13.3% (grade G).
- **Drift:** 2015-2016 loans defaulted more than older loans with the same profile, and riskier grades
  drifted the most. The backtest caught it, and recalibration fixed the portfolio-level estimate.
- **The riskiest 2015-2016 borrowers were underpriced:** declining the riskiest 5% by model PD earns more
  than approving everyone.

| | |
|---|---|
| ![Default rate by vintage](images/default_rate_by_vintage.png) | ![Calibration](images/calibration.png) |
| ![Projected vs. realized loss](images/vintage_loss.png) | ![Approval strategy](images/approval_strategy.png) |

## Project structure

```
01_explore_raw.ipynb        Raw data peek, column audit (feature / reporting / drop), Parquet export
02_define_outcome.ipynb     Maturity filter and default definition
03_load_postgres.ipynb      Bulk load into PostgreSQL with COPY, indexes, row-count checks
04_portfolio_sql.ipynb      SQL portfolio analysis and the loan_cube summary table
05_pd_model.ipynb           Out-of-time split, baseline vs. logistic regression vs. XGBoost, SHAP, loss severity
06_expected_loss.ipynb      Expected loss, backtest, recalibration, vintages, stress test, approval strategy
sql/                        Every portfolio query as a .sql file
features.py                 Feature engineering shared by the notebooks and the app
app.py                      Streamlit entry point (navigation)
portfolio.py                Portfolio page: filters, KPIs, live SQL charts
score.py                    Score a Loan page: PD, expected loss, SHAP waterfall
strategy.py                 Strategy & Stress Test page
about.py                    About page: methods, results, limitations
db.py                       Database connection: PostgreSQL if configured, else the bundled snapshot
load_to_cloud.py            Copies the app's summary tables to a cloud database
export_snapshot.py          Exports the app's summary tables to app_data/ for the public demo
app_data/                   Snapshot of the four summary tables the app reads
models/pd_model.joblib      XGBoost pipeline, loss severity, recalibration
docs/column_audit.csv       Every raw column with its type, missing %, example, and role
```

## Run it locally

1. Download `accepted_2007_to_2018Q4.csv.gz` from the
   [Lending Club dataset on Kaggle](https://www.kaggle.com/datasets/wordsforthewise/lending-club) into
   `data/raw/`.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt pyarrow ipykernel
   ```
3. Create a PostgreSQL database and a `.env` file:
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/lending_db
   ```
4. Run the notebooks in order (01 → 06).
5. Start the app:
   ```bash
   streamlit run app.py
   ```

## Deploy (Streamlit Community Cloud)

The app only reads four small summary tables (a few thousand rows). On
[share.streamlit.io](https://share.streamlit.io), create an app from this repo with `app.py` as the main
file and Python 3.13. That's all the public demo needs: with no database configured, the app loads
`app_data/` into an in-memory SQLite database and runs the same SQL queries.

To query PostgreSQL in the cloud instead:
1. Add `CLOUD_DATABASE_URL=postgresql+psycopg2://...neon.tech/...?sslmode=require` to `.env`, then run
   `python load_to_cloud.py`.
2. Under the app's **Settings → Secrets**, add:
   ```toml
   DATABASE_URL = "postgresql+psycopg2://...neon.tech/...?sslmode=require"
   ```

## Limitations
- **Only approved loans.** There are no rejected applications, so the model has never seen the riskiest
  applicants (no reject inference).
- **Drift.** Credit quality changed over time; 60-month loans from 2015 on have no outcomes yet to check.
- **Lifetime PD, not timing.** The model says whether a loan defaults over its life, not when.
- **Stress multipliers are assumptions** anchored to Lending Club's 2007-2008 experience, not a macro model.
- **Returns are lifetime totals**, not annualized, and ignore servicing fees and the cost of funds.

## Tech stack
Python, pandas, PostgreSQL, SQL, SQLAlchemy, scikit-learn, XGBoost, SHAP, Streamlit
