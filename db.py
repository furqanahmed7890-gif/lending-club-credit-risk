import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).parent / ".env")


def get_database_url():
    url = os.getenv("DATABASE_URL")
    if url is None:
        url = st.secrets["DATABASE_URL"]
    return url


@st.cache_resource
def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)


@st.cache_data(ttl=600)
def run_query(sql, params=None):
    return pd.read_sql(text(sql), get_engine(), params=params)
