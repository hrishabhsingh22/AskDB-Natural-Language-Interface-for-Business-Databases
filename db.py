import os

from data import build_in_memory_db, load_dataset


def run_query(sql, df=None, csv_path=None, *args, **kwargs):
    try:
        if df is None and args:
            first_arg = args[0]
            if isinstance(first_arg, (str, os.PathLike)):
                csv_path = first_arg
            else:
                df = first_arg
        elif isinstance(df, (str, os.PathLike)):
            csv_path = df
            df = None

        if df is None and "dataset_df" in kwargs:
            df = kwargs["dataset_df"]

        if csv_path is None:
            if "csv_path" in kwargs:
                csv_path = kwargs["csv_path"]
            elif "csv_source" in kwargs and isinstance(kwargs["csv_source"], (str, os.PathLike)):
                csv_path = kwargs["csv_source"]

        if df is None:
            df, _, _ = load_dataset(csv_path)

        conn = build_in_memory_db(df)
        cursor = conn.cursor()
        cursor.execute(sql)

        rows = [dict(row) for row in cursor.fetchall()]

        cursor.close()
        conn.close()
        return rows
    except Exception as exc:
        print("Database Error:", exc)
        return None
