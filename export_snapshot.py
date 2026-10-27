"""Exports the small tables the app reads to app_data/ as CSV.

The app uses these when no database is configured (for example the public demo), running the same SQL
against an in-memory SQLite copy. Rerun after notebooks 04 and 06 change the tables.
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

APP_TABLES = ["loan_cube", "vintage_loss", "stress_test", "strategy_curve"]
SNAPSHOT = Path(__file__).parent / "app_data"

load_dotenv(Path(__file__).parent / ".env")
engine = create_engine(os.environ["DATABASE_URL"])

SNAPSHOT.mkdir(exist_ok=True)
for table in APP_TABLES:
    df = pd.read_sql(f"SELECT * FROM {table}", engine)
    df.to_csv(SNAPSHOT / f"{table}.csv", index=False)
    print(f"{table}: {len(df)} rows")
