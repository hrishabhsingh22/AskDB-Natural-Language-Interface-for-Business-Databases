import os
import re

from dotenv import load_dotenv
from groq import Groq

from data import get_schema_text, load_dataset

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
TABLE_NAME = "amazon_sales"
MONTH_MAP = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


def clean_sql(sql):
    sql = sql.replace("```sql", "").replace("```", "").strip()
    sql = sql.split(";")[0]
    return sql.strip()


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_intent(question):
    q = normalize(question)

    if any(phrase in q for phrase in ["total sales", "total revenue", "sum of amount", "overall sales"]):
        return "TOTAL_SALES"

    if "status" in q and any(word in q for word in ["count", "summary", "breakdown", "distribution"]):
        return "STATUS_BREAKDOWN"

    if any(phrase in q for phrase in ["sales by state", "revenue by state", "state wise sales"]):
        return "SALES_BY_STATE"

    if any(phrase in q for phrase in ["sales by city", "revenue by city", "city wise sales"]):
        return "SALES_BY_CITY"

    if any(phrase in q for phrase in ["sales by category", "revenue by category", "category wise sales", "top categories"]):
        return "SALES_BY_CATEGORY"

    if any(phrase in q for phrase in ["sales by month", "monthly sales", "month wise sales"]):
        return "SALES_BY_MONTH"

    if any(phrase in q for phrase in ["top states", "best states"]):
        return "TOP_STATES"

    if any(phrase in q for phrase in ["top cities", "best cities"]):
        return "TOP_CITIES"

    if any(phrase in q for phrase in ["b2b sales", "b2b orders", "b2b summary"]):
        return "B2B_SUMMARY"

    if any(phrase in q for phrase in ["fulfilment summary", "fulfillment summary", "sales by fulfilment", "sales by fulfillment"]):
        return "FULFILMENT_SUMMARY"

    if "show" in q and any(word in q for word in ["orders", "rows", "records"]):
        return "SHOW_ORDERS"

    return "UNKNOWN"


def rule_sql(intent):
    if intent == "TOTAL_SALES":
        return f"SELECT ROUND(SUM(amount), 2) AS total_sales FROM {TABLE_NAME}"

    if intent == "STATUS_BREAKDOWN":
        return f"""
SELECT status, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
GROUP BY status
ORDER BY order_count DESC
LIMIT 20
""".strip()

    if intent == "SALES_BY_STATE":
        return f"""
SELECT ship_state, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
WHERE ship_state IS NOT NULL AND TRIM(ship_state) != ''
GROUP BY ship_state
ORDER BY total_sales DESC
LIMIT 15
""".strip()

    if intent == "SALES_BY_CITY":
        return f"""
SELECT ship_city, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
WHERE ship_city IS NOT NULL AND TRIM(ship_city) != ''
GROUP BY ship_city
ORDER BY total_sales DESC
LIMIT 15
""".strip()

    if intent == "SALES_BY_CATEGORY":
        return f"""
SELECT category, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
WHERE category IS NOT NULL AND TRIM(category) != ''
GROUP BY category
ORDER BY total_sales DESC
LIMIT 15
""".strip()

    if intent == "SALES_BY_MONTH":
        return f"""
SELECT strftime('%Y-%m', date) AS month, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
WHERE date IS NOT NULL
GROUP BY month
ORDER BY month
""".strip()

    if intent == "TOP_STATES":
        return f"""
SELECT ship_state, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
WHERE ship_state IS NOT NULL AND TRIM(ship_state) != ''
GROUP BY ship_state
ORDER BY total_sales DESC
LIMIT 10
""".strip()

    if intent == "TOP_CITIES":
        return f"""
SELECT ship_city, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
WHERE ship_city IS NOT NULL AND TRIM(ship_city) != ''
GROUP BY ship_city
ORDER BY total_sales DESC
LIMIT 10
""".strip()

    if intent == "B2B_SUMMARY":
        return f"""
SELECT b2b, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
GROUP BY b2b
ORDER BY total_sales DESC
""".strip()

    if intent == "FULFILMENT_SUMMARY":
        return f"""
SELECT fulfilment, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
WHERE fulfilment IS NOT NULL AND TRIM(fulfilment) != ''
GROUP BY fulfilment
ORDER BY total_sales DESC
""".strip()

    if intent == "SHOW_ORDERS":
        return f"""
SELECT order_id, date, status, category, ship_city, ship_state, qty, amount
FROM {TABLE_NAME}
LIMIT 100
""".strip()

    return None


def is_safe_sql(sql):
    sql = sql.strip().lower()
    if not (sql.startswith("select") or sql.startswith("with")):
        return False

    blocked = ["insert", "update", "delete", "drop", "alter", "attach", "pragma"]
    return not any(word in sql for word in blocked)


def sql_quote(value):
    return "'" + value.replace("'", "''") + "'"


def extract_top_limit(question):
    match = re.search(r"\btop\s+(\d+)\b", question.lower())
    if match:
        return int(match.group(1))
    return 10


def extract_month_filter(question):
    q = question.lower()
    for month_name, month_number in MONTH_MAP.items():
        if month_name in q:
            return f"strftime('%m', date) = '{month_number}'"
    return None


def extract_location(question):
    lower_q = question.lower()
    location_match = re.search(r"\b(?:in|from)\s+([a-z\s]+)", lower_q)
    if not location_match:
        return None

    location = location_match.group(1).strip()
    location = re.sub(
        r"\b(?:with|where|for|show|top|sales|orders|order|category|categories|status|month|revenue)\b.*$",
        "",
        location,
    ).strip()
    if location in MONTH_MAP:
        return None
    if not location:
        return None

    location = location.upper()
    return (
        f"(UPPER(ship_city) = {sql_quote(location)} "
        f"OR UPPER(ship_state) = {sql_quote(location)})"
    )


def extract_status_filter(question):
    lower_q = question.lower()
    if "cancelled" in lower_q or "canceled" in lower_q:
        return "LOWER(status) LIKE '%cancelled%'"
    if "delivered" in lower_q:
        return "LOWER(status) LIKE '%delivered%'"
    if "returned" in lower_q:
        return "LOWER(status) LIKE '%returned%'"
    if "shipped" in lower_q:
        return "LOWER(status) LIKE '%shipped%'"
    if "pending" in lower_q:
        return "LOWER(status) LIKE '%pending%'"
    return None


def build_heuristic_sql(question):
    lower_q = question.lower().strip()
    where_clauses = []

    month_filter = extract_month_filter(question)
    if month_filter:
        where_clauses.append(month_filter)

    status_filter = extract_status_filter(question)
    if status_filter:
        where_clauses.append(status_filter)

    location_filter = extract_location(question)
    if location_filter:
        where_clauses.append(location_filter)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    if "forecast" in lower_q and "month" in lower_q:
        return None

    if "top" in lower_q and "categor" in lower_q:
        limit = extract_top_limit(question)
        return f"""
SELECT category, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
{where_sql}
GROUP BY category
ORDER BY total_sales DESC
LIMIT {limit}
""".strip()

    if "sales" in lower_q and "category" in lower_q:
        return f"""
SELECT category, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
{where_sql}
GROUP BY category
ORDER BY total_sales DESC
LIMIT 15
""".strip()

    if ("orders" in lower_q or "order" in lower_q or "show" in lower_q) and where_sql:
        return f"""
SELECT order_id, date, status, category, ship_city, ship_state, qty, amount
FROM {TABLE_NAME}
{where_sql}
ORDER BY date DESC
LIMIT 100
""".strip()

    if "sales" in lower_q or "revenue" in lower_q:
        if "state" in lower_q:
            return f"""
SELECT ship_state, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
{where_sql}
GROUP BY ship_state
ORDER BY total_sales DESC
LIMIT 15
""".strip()
        if "city" in lower_q:
            return f"""
SELECT ship_city, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_sales
FROM {TABLE_NAME}
{where_sql}
GROUP BY ship_city
ORDER BY total_sales DESC
LIMIT 15
""".strip()
        if where_sql:
            return f"""
SELECT ROUND(SUM(amount), 2) AS total_sales, COUNT(*) AS order_count
FROM {TABLE_NAME}
{where_sql}
""".strip()

    if where_sql:
        return f"""
SELECT order_id, date, status, category, ship_city, ship_state, qty, amount
FROM {TABLE_NAME}
{where_sql}
ORDER BY date DESC
LIMIT 100
""".strip()

    return None


def llm_sql(question, csv_path=None, df=None):
    if client is None:
        return None

    if df is None:
        df, _, _ = load_dataset(csv_path)
    schema_text = get_schema_text(df)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate SQLite SQL only. "
                    f"The dataset is in a single table called {TABLE_NAME}. "
                    "Return only a SELECT query with no markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Table schema:\n{schema_text}\n\n"
                    f"Question: {question}\n\n"
                    "Useful notes:\n"
                    "- Use date for time analysis.\n"
                    "- Use amount for sales/revenue.\n"
                    "- Use ship_city and ship_state for geography.\n"
                    "- Use status, category, fulfilment, b2b, qty for analysis."
                ),
            },
        ],
    )
    return clean_sql(response.choices[0].message.content)


def generate_sql(question, csv_path=None, df=None):
    intent = detect_intent(question)
    if intent != "UNKNOWN":
        return rule_sql(intent)

    heuristic_sql = build_heuristic_sql(question)
    if heuristic_sql and is_safe_sql(heuristic_sql):
        return heuristic_sql

    try:
        sql = llm_sql(question, csv_path=csv_path, df=df)
    except Exception:
        sql = None

    if sql and is_safe_sql(sql):
        return sql

    return (
        f"SELECT order_id, date, status, category, ship_city, ship_state, qty, amount "
        f"FROM {TABLE_NAME} LIMIT 25"
    )


def explain_result(question, sql, result):
    if not result:
        return "No rows matched that question in the Amazon sales dataset."

    if len(result) == 1 and len(result[0]) == 1:
        key, value = next(iter(result[0].items()))
        return f"For '{question}', the query returned {key} = {value}."

    preview = result[:3]
    columns = ", ".join(preview[0].keys())
    return (
        f"The query answered '{question}' using {TABLE_NAME}. "
        f"It returned {len(result)} row(s) with columns: {columns}. "
        f"The first few rows are: {preview}"
    )
