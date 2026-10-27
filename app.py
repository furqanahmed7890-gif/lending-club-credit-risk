import streamlit as st

st.set_page_config(page_title="Loan Portfolio Credit Risk", page_icon="💳", layout="wide")

page = st.navigation([
    st.Page("portfolio.py", title="Portfolio", icon="📊"),
    st.Page("score.py", title="Score a Loan", icon="🧮"),
    st.Page("strategy.py", title="Strategy & Stress Test", icon="🎯"),
    st.Page("about.py", title="About", icon="ℹ️"),
])

page.run()
