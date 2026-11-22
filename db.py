from data import build_in_memory_db, load_dataset


def run_query(sql, csv_path=None, df=None):
    try:
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
