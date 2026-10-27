from pathlib import Path

import streamlit as st

IMAGES = Path(__file__).parent / "images"

st.title("About This Project")

st.markdown(r"""
This app measures the credit risk of a \$34 billion consumer loan portfolio. It predicts each loan's
probability of default, turns that into an expected dollar loss, backtests the estimate against what
really happened, stress-tests the loans still running, and shows how a lender could use the model to
decide which applications to approve. It was built as an end-to-end portfolio project covering data
engineering, SQL, machine learning, and deployment.

### The data
[Lending Club](https://www.kaggle.com/datasets/wordsforthewise/lending-club) accepted loans,
2007-2018: 2.26 million loans and 151 columns, with a snapshot date of March 2019. A loan only gets an
outcome once it has reached full term, so 779,026 loans are **judged**: fully paid (good) or charged
off/defaulted (bad). Their default rate is 15.19%. Loans that were still running are excluded from
training and scored as the live book instead.

### How it was built
1. **Column audit.** 25 columns known at application kept as features and 114 dropped. 12 columns
   recorded after the loan was issued (status, payments, recoveries) are kept for reporting only and
   never fed to the model, because they would leak the outcome.
2. **Outcome definition.** Only loans past their full term are judged, so slow-defaulting recent loans
   can't pass as good.
3. **PostgreSQL.** All 2.26M rows bulk-loaded with `COPY`. The portfolio analysis is plain SQL
   (in the `sql/` folder), and the app reads small summary tables built from it.
4. **Out-of-time test.** Models train on loans issued 2007-2014 and are tested on 2015-2016 loans they
   never saw, the way a lender actually uses a model.
5. **Models.** Lending Club's own sub-grade as the baseline, then logistic regression and XGBoost.
   XGBoost is explained with SHAP.
6. **Expected loss** = PD x exposure at default x loss given default x amount funded.
7. **Monitoring.** The backtest showed newer loans defaulted more than the model expected, so it was
   recalibrated on the 2015-2016 outcomes before scoring the loans still running.
""")

st.markdown("### Results on 372,811 out-of-time test loans (issued 2015-2016)")
st.markdown(r"""
| Model | AUC | Gini | KS |
|---|---|---|---|
| Lending Club sub-grade (baseline) | 0.682 | 0.364 | 0.266 |
| Logistic regression | 0.687 | 0.374 | 0.272 |
| XGBoost without Lending Club's grade or rate | 0.687 | 0.375 | 0.270 |
| **XGBoost** | **0.700** | **0.400** | **0.291** |

**Expected loss backtest.** On 2015-2016 loans the original model expected 6.4% of the amount funded
to be lost, and 7.9% was. Newer loans defaulted more than older loans with the same profile, and the
riskier grades drifted the most. After recalibrating on those outcomes the total is within 3%, though
losses for grades D-G are still understated.

**Stress test.** The \$23.6 billion of loans still running at the snapshot are expected to lose
\$2.94 billion over their lives, rising to \$4.66 billion in a mild recession and \$6.52 billion in a
severe one.

**Approval strategy.** At 80% approval, ranking by the model instead of sub-grade cuts the default rate
from 12.0% to 11.6% and earns \$12.4 million more. Declining just the riskiest 5% by the model beats
approving everyone.
""")

if (IMAGES / "shap_summary.png").exists():
    st.markdown("### What drives the model's predictions")
    st.image(str(IMAGES / "shap_summary.png"))
    st.markdown("""
Lending Club's sub-grade is the strongest signal, followed by income, loan size relative to income,
FICO score, and debt-to-income. Renters, borrowers with many recent credit inquiries, and borrowers who
left employment length blank are riskier. These match standard credit risk factors.
""")

st.markdown("""
### Limitations
- **Only approved loans.** The data has no rejected applications, so the model has never seen the
  riskiest applicants. Any lender using it would need to correct for that (reject inference).
- **Drift.** Credit quality changed over time. The model needed recalibration for 2015-2016 loans, and
  60-month loans from 2015 on have no outcomes yet to check against.
- **Lifetime, not timing.** PD is the chance of default over the loan's life. The model does not say
  when a default happens, so it is not a full CECL/IFRS 9 lifetime loss engine.
- **Stress scenarios are assumptions.** The multipliers are anchored to Lending Club's own 2007-2008
  experience, not to a macroeconomic model.
- **Returns are lifetime totals**, not annualized, and ignore servicing fees and the cost of funds.
- **Educational project.** Not a lending decision tool.

### Tech stack
Python, pandas, PostgreSQL, SQL, SQLAlchemy, scikit-learn, XGBoost, SHAP, Streamlit

### Source code
[github.com/furqanahmed7890-gif/lending-club-credit-risk](https://github.com/furqanahmed7890-gif/lending-club-credit-risk)
""")
