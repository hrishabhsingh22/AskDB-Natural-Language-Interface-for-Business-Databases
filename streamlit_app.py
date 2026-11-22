import os

import pandas as pd
import streamlit as st

from agent import explain_result, generate_sql
from data import DEFAULT_DATASET_PATH, get_dataset_path, load_dataset
from db import run_query
from forecast import forecast_next_month_sales


st.set_page_config(page_title="AskDB", layout="wide")

SUGGESTED_QUERIES = [
    "total sales",
    "sales by state",
    "sales by city",
    "status breakdown",
    "monthly sales",
    "forecast next month sales",
    "top categories",
    "b2b summary",
    "fulfilment summary",
    "show orders",
]


def inject_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

        :root {
            --bg: #060a10;
            --panel: rgba(14, 18, 28, 0.94);
            --panel-soft: rgba(19, 24, 36, 0.88);
            --border: rgba(53, 68, 91, 0.46);
            --accent: #17d4c2;
            --accent-soft: rgba(23, 212, 194, 0.14);
            --text: #ecf3fb;
            --muted: #8d98ab;
            --danger: #ff786b;
            --shadow: 0 30px 60px rgba(0, 0, 0, 0.45);
        }

        html, body, [class*="css"] {
            font-family: "Manrope", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top, rgba(23, 212, 194, 0.18), transparent 28%),
                radial-gradient(circle at 85% 20%, rgba(16, 92, 154, 0.18), transparent 24%),
                linear-gradient(180deg, #03060b 0%, #060a10 100%);
            color: var(--text);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stSidebar"] {
            background: rgba(6, 10, 16, 0.95);
            border-right: 1px solid rgba(53, 68, 91, 0.35);
        }

        [data-testid="stSidebar"] * {
            color: var(--text);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }

        div[data-baseweb="select"] > div,
        div[data-baseweb="base-input"] > div,
        .stTextInput input,
        .stTextArea textarea {
            background: rgba(11, 15, 23, 0.95) !important;
            border: 1px solid rgba(53, 68, 91, 0.45) !important;
            color: var(--text) !important;
            border-radius: 12px !important;
        }

        .stButton button,
        .stDownloadButton button {
            background: linear-gradient(90deg, #12d8c4 0%, #0eb6a6 100%);
            color: #041116;
            border: none;
            border-radius: 999px;
            font-weight: 800;
            padding: 0.7rem 1.2rem;
            box-shadow: 0 10px 24px rgba(18, 216, 196, 0.25);
        }

        .stRadio > div {
            gap: 0.75rem;
        }

        .stDataFrame, [data-testid="stMetric"] {
            background: transparent;
        }

        .hero-wrap {
            padding: 0.5rem 0 1rem 0;
        }

        .brand-chip {
            width: fit-content;
            margin: 0 auto 1rem auto;
            display: flex;
            align-items: center;
            gap: 0.55rem;
            color: var(--text);
            font-weight: 800;
            letter-spacing: 0.01em;
        }

        .brand-dot {
            width: 1.35rem;
            height: 1.35rem;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(180deg, #19ddcb 0%, #0ca99a 100%);
            color: #03222b;
            font-size: 0.8rem;
            box-shadow: 0 0 24px rgba(23, 212, 194, 0.35);
        }

        .hero-grid {
            display: grid;
            grid-template-columns: 1.15fr 0.85fr;
            gap: 1.25rem;
            align-items: stretch;
        }

        .glass-panel {
            background: linear-gradient(180deg, rgba(13, 18, 28, 0.95), rgba(9, 13, 20, 0.92));
            border: 1px solid var(--border);
            border-radius: 28px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }

        .hero-copy {
            padding: 2rem;
            min-height: 470px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .eyebrow {
            color: var(--accent);
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }

        .hero-copy h1 {
            font-size: 3.2rem;
            line-height: 1.02;
            margin: 0.65rem 0 0.9rem 0;
            letter-spacing: -0.04em;
        }

        .hero-copy p {
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.7;
            max-width: 42rem;
        }

        .feature-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.9rem;
            margin-top: 1.6rem;
        }

        .feature-card,
        .metric-card,
        .section-card {
            background: var(--panel-soft);
            border: 1px solid var(--border);
            border-radius: 20px;
        }

        .feature-card {
            padding: 1rem;
        }

        .feature-card strong {
            display: block;
            margin-bottom: 0.35rem;
            font-size: 0.95rem;
        }

        .feature-card span {
            color: var(--muted);
            font-size: 0.88rem;
            line-height: 1.55;
        }

        .auth-shell {
            padding: 1.3rem;
            background:
                radial-gradient(circle at top, rgba(23, 212, 194, 0.14), transparent 32%),
                linear-gradient(180deg, rgba(6, 10, 16, 0.88), rgba(7, 11, 18, 0.96));
            min-height: 470px;
        }

        .auth-card {
            width: min(360px, 100%);
            background: rgba(14, 18, 28, 0.96);
            border: 1px solid rgba(53, 68, 91, 0.44);
            border-radius: 20px;
            padding: 1.35rem;
            box-shadow: 0 22px 48px rgba(0, 0, 0, 0.42);
            margin: 2.2rem auto;
        }

        .auth-card h3 {
            margin: 0;
            text-align: center;
            font-size: 1.35rem;
        }

        .auth-card p {
            margin: 0.35rem 0 1rem 0;
            text-align: center;
            color: var(--muted);
            font-size: 0.9rem;
        }

        .tiny-note {
            color: var(--muted);
            font-size: 0.8rem;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin: 1rem 0 1.2rem 0;
        }

        .metric-card {
            padding: 1rem 1.1rem;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.84rem;
            margin-bottom: 0.5rem;
        }

        .metric-value {
            font-size: 1.35rem;
            font-weight: 800;
            letter-spacing: -0.03em;
        }

        .metric-foot {
            margin-top: 0.45rem;
            color: var(--accent);
            font-size: 0.8rem;
            font-weight: 700;
        }

        .section-card {
            padding: 1.2rem;
            margin-top: 1rem;
        }

        .section-title {
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 0.3rem;
        }

        .section-subtitle {
            color: var(--muted);
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }

        .query-strip {
            display: flex;
            gap: 0.65rem;
            flex-wrap: wrap;
            margin-top: 0.7rem;
        }

        .query-pill {
            background: rgba(23, 212, 194, 0.08);
            border: 1px solid rgba(23, 212, 194, 0.18);
            color: #bff7f1;
            padding: 0.5rem 0.8rem;
            border-radius: 999px;
            font-size: 0.82rem;
        }

        .auth-divider {
            text-align: center;
            color: var(--muted);
            font-size: 0.78rem;
            margin: 0.85rem 0;
        }

        .oauth-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.7rem;
            margin-top: 0.5rem;
        }

        .oauth-chip {
            text-align: center;
            background: rgba(22, 27, 39, 0.96);
            border: 1px solid rgba(53, 68, 91, 0.44);
            color: var(--text);
            border-radius: 12px;
            padding: 0.7rem 0.9rem;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .mock-tabs {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.6rem;
            margin-bottom: 1rem;
            background: rgba(10, 14, 22, 0.95);
            border: 1px solid rgba(53, 68, 91, 0.35);
            border-radius: 999px;
            padding: 0.3rem;
        }

        .mock-tab {
            text-align: center;
            padding: 0.55rem 0.7rem;
            border-radius: 999px;
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 700;
        }

        .mock-tab.active {
            background: linear-gradient(90deg, #12d8c4 0%, #0eb6a6 100%);
            color: #041116;
        }

        .mock-field-label {
            color: #b5c1d4;
            font-size: 0.76rem;
            margin: 0.65rem 0 0.35rem 0;
        }

        .mock-input {
            background: rgba(11, 15, 23, 0.95);
            border: 1px solid rgba(53, 68, 91, 0.45);
            color: #6f7f94;
            border-radius: 12px;
            padding: 0.8rem 0.9rem;
            font-size: 0.86rem;
        }

        .mock-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--muted);
            font-size: 0.78rem;
            margin-top: 0.8rem;
        }

        .mock-link {
            color: var(--accent);
            font-weight: 700;
        }

        .mock-button {
            margin-top: 1rem;
            text-align: center;
            background: linear-gradient(90deg, #12d8c4 0%, #0eb6a6 100%);
            color: #041116;
            border-radius: 999px;
            padding: 0.78rem 1rem;
            font-weight: 800;
            box-shadow: 0 10px 24px rgba(18, 216, 196, 0.25);
        }

        @media (max-width: 980px) {
            .hero-grid,
            .metric-grid,
            .feature-row {
                grid-template-columns: 1fr;
            }

            .hero-copy {
                min-height: auto;
            }

            .auth-shell {
                min-height: auto;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def get_dataset(csv_path):
    return load_dataset(csv_path)


def render_brand():
    st.markdown(
        """
        <div class="brand-chip">
            <span class="brand-dot">●</span>
            <span>AskDB</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(dataset_df, forecast, dataset_name=None):
    total_sales = float(dataset_df["amount"].sum()) if "amount" in dataset_df.columns else 0.0
    total_orders = int(len(dataset_df))
    unique_states = int(dataset_df["ship_state"].dropna().nunique()) if "ship_state" in dataset_df.columns else 0
    delivered_orders = int(
        dataset_df["status"].fillna("").str.contains("Delivered", case=False).sum()
    ) if "status" in dataset_df.columns else 0
    forecast_text = (
        "N/A"
        if forecast.get("predicted_sales") is None
        else f"INR {forecast['predicted_sales']:,.0f}"
    )

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Sales</div>
                <div class="metric-value">INR {total_sales:,.0f}</div>
                <div class="metric-foot">Live from CSV</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Orders Processed</div>
                <div class="metric-value">{total_orders:,}</div>
                <div class="metric-foot">Across all statuses</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Delivered Orders</div>
                <div class="metric-value">{delivered_orders:,}</div>
                <div class="metric-foot">Shipment success view</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Next Month Forecast</div>
                <div class="metric-value">{forecast_text}</div>
                <div class="metric-foot">Trend-based estimate</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    caption_name = dataset_name or get_dataset_path()
    st.caption(f"Dataset loaded from `{caption_name}`")


def render_home(dataset_df, dataset_name=None):
    forecast = forecast_next_month_sales(dataset_df)
    st.markdown('<div class="hero-wrap">', unsafe_allow_html=True)
    render_brand()
    left_col, right_col = st.columns([1.15, 0.85], gap="large")

    with left_col:
        st.markdown(
            """
            <div class="glass-panel hero-copy">
                <div>
                    <div class="eyebrow">Amazon Sales Intelligence</div>
                    <h1>Ask your data in a UI styled like a premium product.</h1>
                    <p>
                        The interface now follows the dark centered card style from your reference PDF,
                        while keeping the live dataset tools underneath it. Customers can explore sales,
                        run guided queries, and check the next-month forecast from one place.
                    </p>
                    <div class="feature-row">
                        <div class="feature-card">
                            <strong>Prompt to Insight</strong>
                            <span>Choose ready-made queries or type your own business question.</span>
                        </div>
                        <div class="feature-card">
                            <strong>Forecast Ready</strong>
                            <span>Estimate the next month of sales directly from historical trend data.</span>
                        </div>
                        <div class="feature-card">
                            <strong>Exec Dashboard</strong>
                            <span>See revenue, status mix, geography, and growth in one surface.</span>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown(
            """
            <div class="glass-panel auth-shell">
                <div class="auth-card">
                    <div class="mock-tabs">
                        <div class="mock-tab active">Sign In</div>
                        <div class="mock-tab">Create Account</div>
                    </div>
                    <h3>Welcome back</h3>
                    <p>Sign in to your account to continue</p>
                    <div class="mock-field-label">Email address</div>
                    <div class="mock-input">name@example.com</div>
                    <div class="mock-field-label">Password</div>
                    <div class="mock-input">Enter your password</div>
                    <div class="mock-row">
                        <span>Remember me for 30 days</span>
                        <span class="mock-link">Forgot password?</span>
                    </div>
                    <div class="mock-button">Sign In</div>
                    <div class="auth-divider">or continue with</div>
                    <div class="oauth-row">
                        <div class="oauth-chip">Google</div>
                        <div class="oauth-chip">GitHub</div>
                    </div>
                    <p class="tiny-note" style="text-align:center; margin-top:0.9rem;">
                        Extra features: smart query dropdown, live KPI cards, monthly forecast, and dataset preview.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        cta1, cta2 = st.columns(2)
        with cta1:
            if st.button("Open Query Console", use_container_width=True):
                st.info("Use the sidebar and open `Ask Dataset` to run customer queries.")
        with cta2:
            if st.button("Open Dashboard", use_container_width=True):
                st.info("Use the sidebar and open `Dashboard` to view charts and forecast.")

    render_metric_cards(dataset_df, forecast, dataset_name=dataset_name)

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Suggested customer queries</div>
            <div class="section-subtitle">These are wired into the app and available from the query dropdown.</div>
            <div class="query-strip">
                <span class="query-pill">total sales</span>
                <span class="query-pill">sales by state</span>
                <span class="query-pill">sales by city</span>
                <span class="query-pill">status breakdown</span>
                <span class="query-pill">monthly sales</span>
                <span class="query-pill">forecast next month sales</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Dataset preview</div>
            <div class="section-subtitle">A quick look at the live rows that power the analytics screens.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(dataset_df.head(12), use_container_width=True)


def render_ask_dataset(dataset_df, csv_path):
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Customer Query Console</div>
            <div class="section-subtitle">Pick a guided query or ask your own question in natural language.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1.3])
    with col1:
        selected_query = st.selectbox(
            "Choose a query",
            ["Custom question"] + SUGGESTED_QUERIES,
        )
    with col2:
        typed_question = st.text_input("Custom question", placeholder="Example: cancelled orders in Karnataka")

    question = typed_question.strip() or (
        selected_query if selected_query != "Custom question" else ""
    )

    if question:
        normalized_question = question.lower()
        if "forecast" in normalized_question and "month" in normalized_question:
            forecast = forecast_next_month_sales(dataset_df)
            st.markdown(
                """
                <div class="section-card">
                    <div class="section-title">Next Month Sales Prediction</div>
                    <div class="section-subtitle">A simple forecast based on monthly sales trend.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if forecast["predicted_sales"] is None:
                st.warning("Not enough date data is available to build a forecast.")
            else:
                st.metric(
                    f"Predicted Sales for {forecast['forecast_month']}",
                    f"INR {forecast['predicted_sales']:,.2f}",
                )
                chart_df = forecast["chart_data"].pivot_table(
                    index="month",
                    columns="series",
                    values="amount",
                    aggfunc="first",
                )
                st.line_chart(chart_df)
            return

        sql = generate_sql(question, df=dataset_df, csv_path=csv_path)
        result = run_query(sql, df=dataset_df, csv_path=csv_path)

        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Generated SQL</div>
                <div class="section-subtitle">The app translates your question into a safe read-only query.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code(sql, language="sql")

        if result is None:
            st.error("Query failed.")
            return
        if len(result) == 0:
            st.warning("The query ran successfully but returned no rows.")
            return

        result_df = pd.DataFrame(result)
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Result</div>
                <div class="section-subtitle">Live output from your Amazon sales dataset.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(result_df, use_container_width=True)

        numeric_columns = result_df.select_dtypes(include="number").columns.tolist()
        dimension_columns = [col for col in result_df.columns if col not in numeric_columns]
        if dimension_columns and numeric_columns:
            chart_df = result_df[[dimension_columns[0], numeric_columns[-1]]].copy()
            chart_df = chart_df.set_index(dimension_columns[0])
            st.markdown(
                """
                <div class="section-card">
                    <div class="section-title">Visual Summary</div>
                    <div class="section-subtitle">Quick chart for faster scanning.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.bar_chart(chart_df)

        if "total_sales" in result_df.columns and len(result_df) == 1:
            st.metric("Total Sales", f"INR {result_df.iloc[0]['total_sales']:,.2f}")

        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Explanation</div>
                <div class="section-subtitle">Business-friendly summary of the result.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write(explain_result(question, sql, result))


def render_dashboard(dataset_df, dataset_name=None):
    forecast = forecast_next_month_sales(dataset_df)
    render_metric_cards(dataset_df, forecast, dataset_name=dataset_name)

    monthly_sales = forecast["history"]
    state_sales = (
        dataset_df.dropna(subset=["ship_state"])
        .groupby("ship_state", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .head(10)
    ) if "ship_state" in dataset_df.columns and "amount" in dataset_df.columns else pd.DataFrame(columns=["ship_state", "amount"])

    status_counts = (
        dataset_df.groupby("status", as_index=False)
        .size()
        .rename(columns={"size": "order_count"})
        .sort_values("order_count", ascending=False)
        .head(10)
    ) if "status" in dataset_df.columns else pd.DataFrame(columns=["status", "order_count"])

    category_sales = (
        dataset_df.dropna(subset=["category"])
        .groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .head(8)
    ) if "category" in dataset_df.columns and "amount" in dataset_df.columns else pd.DataFrame(columns=["category", "amount"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Monthly Sales</div>
                <div class="section-subtitle">Historical month-over-month performance.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.line_chart(monthly_sales.set_index("month"))
    with col2:
        st.markdown(
            f"""
            <div class="section-card">
                <div class="section-title">Forecast for {forecast['forecast_month'] or 'next month'}</div>
                <div class="section-subtitle">Historical sales plus predicted next-month value.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if forecast["predicted_sales"] is not None:
            forecast_chart = forecast["chart_data"].pivot_table(
                index="month",
                columns="series",
                values="amount",
                aggfunc="first",
            )
            st.line_chart(forecast_chart)
        else:
            st.info("Forecast unavailable.")

    col3, col4 = st.columns(2)
    with col3:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Top States by Sales</div>
                <div class="section-subtitle">Geographic revenue concentration.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.bar_chart(state_sales.set_index("ship_state"))
    with col4:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Top Categories</div>
                <div class="section-subtitle">Best-performing product groups.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.bar_chart(category_sales.set_index("category"))

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Order Status Breakdown</div>
            <div class="section-subtitle">Operational status distribution across the dataset.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(status_counts, use_container_width=True)


inject_styles()

st.sidebar.title("AskDB")
page = st.sidebar.radio("Navigation", ["Home", "Ask Dataset", "Dashboard"])

st.sidebar.markdown("---")
st.sidebar.subheader("Dataset")

# Streamlit file uploader accepting CSV files
uploaded_file = st.sidebar.file_uploader(
    "Upload CSV dataset",
    type=["csv"],
    help="Upload your sales CSV dataset directly without specifying an absolute local path.",
)

# Preserve existing dataset path functionality for local development
default_path = get_dataset_path()
local_path_exists = bool(default_path and os.path.exists(default_path))

with st.sidebar.expander("Local CSV Path (Optional)", expanded=(uploaded_file is None and local_path_exists)):
    csv_path_input = st.text_input(
        "Local file path",
        value=default_path if local_path_exists else "",
        placeholder=f"e.g. {DEFAULT_DATASET_PATH}",
        help="Optional local path used if no file is uploaded.",
    )

# Determine the dataset source
dataset_source = None
if uploaded_file is not None:
    dataset_source = uploaded_file
elif csv_path_input and csv_path_input.strip():
    dataset_source = csv_path_input.strip()

# If no source is provided at all
if dataset_source is None:
    st.sidebar.info("Upload a CSV file or enter a local CSV path to get started.")
    st.markdown('<div class="hero-wrap">', unsafe_allow_html=True)
    render_brand()
    st.info(
        "👋 **Welcome to AskDB Sales Analytics!**\n\n"
        "To get started, please **upload a CSV dataset** using the uploader in the sidebar "
        "or provide a local file path under **Local CSV Path**."
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

try:
    dataset_df, resolved_path, _ = get_dataset(dataset_source)
    st.sidebar.success(f"Loaded {len(dataset_df):,} rows")
    st.sidebar.caption(f"📁 {resolved_path}")
except Exception as exc:
    st.sidebar.error(f"Could not load dataset: {exc}")
    st.markdown('<div class="hero-wrap">', unsafe_allow_html=True)
    render_brand()
    st.error(
        f"⚠️ **Could not load dataset**: {exc}\n\n"
        "Please verify that your CSV file is properly formatted, not empty, and contains sales data."
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if page == "Home":
    render_home(dataset_df, dataset_name=resolved_path)
elif page == "Ask Dataset":
    render_ask_dataset(dataset_df, csv_path=resolved_path)
else:
    render_dashboard(dataset_df, dataset_name=resolved_path)
