import os
import re
import sqlite3

import pandas as pd


DEFAULT_DATASET_PATH = "/Users/BEAST/Downloads/Amazon Sale Report.csv"


def get_dataset_path():
    return os.getenv("AMAZON_SALES_CSV", DEFAULT_DATASET_PATH)


def normalize_column_name(column_name):
    normalized = column_name.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if normalized and normalized[0].isdigit():
        normalized = f"col_{normalized}"
    return normalized or "unnamed_column"


def load_dataset(csv_path=None):
    dataset_path = csv_path or get_dataset_path()
    df = pd.read_csv(dataset_path, low_memory=False)

    renamed_columns = {
        original: normalize_column_name(original)
        for original in df.columns
    }
    df = df.rename(columns=renamed_columns)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], format="%m-%d-%y", errors="coerce")

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    if "qty" in df.columns:
        df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0).astype(int)

    if "ship_postal_code" in df.columns:
        df["ship_postal_code"] = (
            pd.to_numeric(df["ship_postal_code"], errors="coerce")
            .astype("Int64")
        )

    if "b2b" in df.columns:
        df["b2b"] = df["b2b"].astype(str).str.lower().isin(["true", "1", "yes"])

    return df, dataset_path, renamed_columns


def build_in_memory_db(df):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    sqlite_df = df.copy()
    if "date" in sqlite_df.columns:
        sqlite_df["date"] = sqlite_df["date"].dt.strftime("%Y-%m-%d")

    sqlite_df.to_sql("amazon_sales", conn, if_exists="replace", index=False)
    return conn


def get_schema_text(df):
    lines = [
        f"- {column}: {dtype}"
        for column, dtype in df.dtypes.items()
    ]
    return "\n".join(lines)
