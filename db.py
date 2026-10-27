import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.pool import StaticPool

load_dotenv(Path(__file__).parent / ".env")

SNAPSHOT = Path(__file__).parent / "app_data"


def get_database_url():
    url = os.getenv("DATABASE_URL")
    if url is None:
        try:
            url = st.secrets.get("DATABASE_URL")
        except FileNotFoundError:
            url = None
    return url


def data_source():
    return "PostgreSQL" if get_database_url() else "a SQLite snapshot of the PostgreSQL summary tables"


def snapshot_engine():
    """In-memory SQLite copy of app_data/, used when no database is configured (e.g. the public demo)."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    for csv in SNAPSHOT.glob("*.csv"):
        pd.read_csv(csv).to_sql(csv.stem, engine, index=False)
    return engine


@st.cache_resource
def get_engine():
    url = get_database_url()
    if url is None:
        return snapshot_engine()
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=600)
def run_query(sql, params=None):
    statement = text(sql)
    lists = [name for name, value in (params or {}).items() if isinstance(value, (list, tuple))]
    if lists:
        statement = statement.bindparams(*[bindparam(name, expanding=True) for name in lists])
    return pd.read_sql(statement, get_engine(), params=params)
