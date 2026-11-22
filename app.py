from agent import explain_result, generate_sql
from db import run_query


# ---------------------------
# STRONG SAFE CHECK
# ---------------------------
def is_safe_query(sql):
    if not sql:
        return False

    sql_clean = sql.strip().lower()

    # allow SELECT and WITH queries
    if not (sql_clean.startswith("select") or sql_clean.startswith("with")):
        return False

    # block dangerous keywords
    blocked = ["insert", "update", "delete", "drop", "alter"]

    return not any(word in sql_clean for word in blocked)


# ---------------------------
# MAIN APP
# ---------------------------
def main():
    print("🤖 AI Data Analyst Ready!")
    print("📁 Using Amazon sales CSV data")

    while True:
        question = input("\nAsk a question: ")

        if question.lower() in ["exit", "quit"]:
            print("👋 Exiting...")
            break

        # Generate SQL
        sql = generate_sql(question)
        print("\n🧾 Generated SQL:\n", sql)

        # Safety check
        if not is_safe_query(sql):
            print("❌ Unsafe query blocked")
            continue

        # Run query
        result = run_query(sql)

        if result is None:
            print("❌ Query failed")
            continue

        print("\n📊 Result:\n", result)

        # Explanation
        explanation = explain_result(question, sql, result)
        print("\n🧠 Explanation:\n", explanation)


if __name__ == "__main__":
    main()
