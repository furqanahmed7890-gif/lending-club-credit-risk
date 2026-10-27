"""Copies the small tables the app needs from local PostgreSQL to a cloud database (e.g. Neon).

The full loans table (2.26M rows) stays local; the app only reads these summary tables.
Set CLOUD_DATABASE_URL in .env first.
"""
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

APP_TABLES = ["loan_cube", "vintage_loss", "stress_test", "strategy_curve"]

load_dotenv(".env", override=True)

local_engine = create_engine(os.environ["DATABASE_URL"])
cloud_engine = create_engine(os.environ["CLOUD_DATABASE_URL"])

for table in APP_TABLES:
    df = pd.read_sql(f"SELECT * FROM {table}", local_engine)
    df.to_sql(table, cloud_engine, if_exists="replace", index=False)
    check = pd.read_sql(f"SELECT COUNT(*) AS n FROM {table}", cloud_engine)
    print(f"{table}: {int(check['n'].iloc[0])} rows in the cloud")
