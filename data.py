import os
import re
import sqlite3

import pandas as pd


DEFAULT_DATASET_PATH = "/Users/BEAST/Downloads/Amazon Sale Report.csv"

SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "latin1", "cp1252", "iso-8859-1"]

COLUMN_ALIASES = {
    "sales": "amount",
    "revenue": "amount",
    "total_amount": "amount",
    "order_amount": "amount",
    "order_date": "date",
    "order_status": "status",
    "delivery_status": "status",
    "state": "ship_state",
    "city": "ship_city",
    "postal_code": "ship_postal_code",
    "zip_code": "ship_postal_code",
    "quantity": "qty",
    "product_category": "category",
    "item_category": "category",
}


def get_dataset_path():
    return os.getenv("AMAZON_SALES_CSV", DEFAULT_DATASET_PATH)


def normalize_column_name(column_name):
    normalized = str(column_name).strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if normalized and normalized[0].isdigit():
        normalized = f"col_{normalized}"
    return normalized or "unnamed_column"


def load_dataset(csv_path=None, csv_source=None, *args, **kwargs):
    source = csv_path if csv_path is not None else csv_source
    if source is None and args:
        source = args[0]
    if source is None:
        source = (
            kwargs.get("source")
            or kwargs.get("file")
            or kwargs.get("buffer")
            or kwargs.get("file_path")
        )
    if source is None:
        source = get_dataset_path()

    # Determine display / reference name
    if hasattr(source, "name") and source.name:
        dataset_name = source.name
    elif isinstance(source, (str, os.PathLike)):
        dataset_name = str(source)
    else:
        dataset_name = "uploaded_dataset.csv"

    # Validation: local path existence & empty file check
    if isinstance(source, (str, os.PathLike)):
        if not os.path.exists(source):
            raise FileNotFoundError(
                f"Dataset file not found at: '{source}'. Please verify the path or upload a CSV file."
            )
        if os.path.getsize(source) == 0:
            raise ValueError(
                f"The file '{dataset_name}' is empty (0 bytes). Please provide a CSV file containing data."
            )
    elif hasattr(source, "size") and source.size == 0:
        raise ValueError(
            f"The uploaded file '{dataset_name}' is empty (0 bytes). Please upload a valid CSV file with data."
        )

    # Read CSV with pandas, attempting multiple encodings gracefully
    df = None
    last_exc = None

    for enc in SUPPORTED_ENCODINGS:
        try:
            if hasattr(source, "seek"):
                source.seek(0)
            df = pd.read_csv(source, encoding=enc, low_memory=False)
            break
        except UnicodeDecodeError as exc:
            last_exc = exc
            continue
        except pd.errors.EmptyDataError:
            raise ValueError(
                f"The CSV file '{dataset_name}' contains no readable columns or data."
            )
        except pd.errors.ParserError as exc:
            raise ValueError(
                f"Could not parse '{dataset_name}' as a valid CSV: {exc}"
            )
        except Exception as exc:
            last_exc = exc
            break

    if df is None:
        if isinstance(last_exc, UnicodeDecodeError):
            raise ValueError(
                f"Encoding error: Unable to decode '{dataset_name}' using UTF-8, Latin-1, or CP1252. "
                "Please ensure the file is saved with standard UTF-8 encoding."
            )
        raise ValueError(f"Could not read CSV file '{dataset_name}': {last_exc}")

    # Validation: empty dataframe or no columns
    if df.empty or len(df) == 0:
        raise ValueError(
            f"The CSV file '{dataset_name}' contains no data rows. Please upload a dataset with records."
        )

    if len(df.columns) == 0:
        raise ValueError(
            f"The CSV file '{dataset_name}' has no columns."
        )

    # Normalize column names
    renamed_columns = {
        original: normalize_column_name(original)
        for original in df.columns
    }
    df = df.rename(columns=renamed_columns)

    # Map common aliases if the standard column is missing
    for alias, standard in COLUMN_ALIASES.items():
        if standard not in df.columns and alias in df.columns:
            df[standard] = df[alias]

    # Required column validation
    if "amount" not in df.columns:
        available = ", ".join(list(df.columns)[:8])
        raise ValueError(
            f"Missing required sales column 'amount' (or 'sales'/'revenue') in '{dataset_name}'. "
            f"Detected columns: {available}."
        )

    # Graceful handling and type casting of standard columns
    if "date" in df.columns:
        parsed_date = pd.to_datetime(df["date"], format="%m-%d-%y", errors="coerce")
        if parsed_date.notna().sum() == 0 and df["date"].notna().sum() > 0:
            parsed_date = pd.to_datetime(df["date"], errors="coerce")
        df["date"] = parsed_date
    else:
        df["date"] = pd.NaT

    if "amount" in df.columns:
        if df["amount"].dtype == object:
            df["amount"] = (
                df["amount"]
                .astype(str)
                .str.replace(r"[^\d.-]", "", regex=True)
            )
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    if "qty" in df.columns:
        df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0).astype(int)
    else:
        df["qty"] = 1

    if "status" not in df.columns:
        df["status"] = "Completed"
    else:
        df["status"] = df["status"].fillna("Unknown").astype(str)

    if "category" not in df.columns:
        df["category"] = "General"
    else:
        df["category"] = df["category"].fillna("General").astype(str)

    if "ship_state" not in df.columns:
        df["ship_state"] = "Unknown"
    else:
        df["ship_state"] = df["ship_state"].fillna("Unknown").astype(str)

    if "ship_city" not in df.columns:
        df["ship_city"] = "Unknown"
    else:
        df["ship_city"] = df["ship_city"].fillna("Unknown").astype(str)

    if "order_id" not in df.columns:
        df["order_id"] = [f"ORD_{i+1:05d}" for i in range(len(df))]

    if "ship_postal_code" in df.columns:
        try:
            df["ship_postal_code"] = (
                pd.to_numeric(df["ship_postal_code"], errors="coerce")
                .round()
                .astype("Int64")
            )
        except Exception:
            df["ship_postal_code"] = df["ship_postal_code"].astype(str)
    else:
        df["ship_postal_code"] = pd.Series([pd.NA] * len(df), dtype="Int64")

    if "b2b" in df.columns:
        df["b2b"] = df["b2b"].astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        df["b2b"] = False

    if "fulfilment" not in df.columns:
        df["fulfilment"] = "Standard"

    return df, dataset_name, renamed_columns


def build_in_memory_db(df):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    sqlite_df = df.copy()
    if "date" in sqlite_df.columns and pd.api.types.is_datetime64_any_dtype(sqlite_df["date"]):
        sqlite_df["date"] = sqlite_df["date"].dt.strftime("%Y-%m-%d")

    sqlite_df.to_sql("amazon_sales", conn, if_exists="replace", index=False, chunksize=10000)
    return conn


def get_schema_text(df):
    lines = [
        f"- {column}: {dtype}"
        for column, dtype in df.dtypes.items()
    ]
    return "\n".join(lines)
