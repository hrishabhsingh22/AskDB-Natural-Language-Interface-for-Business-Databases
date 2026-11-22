# AskDB Sales Analytics

AI-powered natural language analytics dashboard for Amazon sales data with SQL generation, interactive Streamlit visualizations, and next-month sales forecasting.

## Features

- Ask business questions in natural language
- Generate safe SQL automatically
- Use a dropdown for common customer queries
- View query results and charts
- Explore sales dashboard metrics
- Predict next-month sales from historical monthly trends

## Tech Stack

- Python
- Streamlit
- Pandas
- SQLite
- Groq API

## Project Files

- `streamlit_app.py` - main Streamlit UI
- `agent.py` - query understanding and SQL generation
- `db.py` - query execution on the Amazon sales table
- `data.py` - dataset loading and column normalization
- `forecast.py` - next-month sales prediction
- `app.py` - CLI version

## Dataset

This project is configured to work with `Amazon Sale Report.csv`.

By default, it loads:

```bash
/Users/aryantripathi/Downloads/Amazon Sale Report.csv
```

You can change the dataset path from the Streamlit sidebar.

## Setup

Activate the virtual environment:

```bash
source /Users/aryantripathi/Documents/DTI_project/venv/bin/activate
```

Install dependencies if needed:

```bash
pip install streamlit pandas python-dotenv groq
```

Create a `.env` file with your Groq API key:

```bash
GROQ_API_KEY=your_api_key_here
```

## Run the App

```bash
streamlit run /Users/aryantripathi/Documents/DTI_project/streamlit_app.py
```

Open the local URL shown in the terminal, usually:

```bash
http://localhost:8501
```

## Example Questions

- total sales
- sales by state
- sales by city
- status breakdown
- monthly sales
- forecast next month sales
- top 5 categories in April
- cancelled orders in Karnataka
- orders from Mumbai

## Notes

- `.env`, `venv/`, and `__pycache__/` are ignored by Git.
- The forecast is a simple linear trend estimate, suitable for demo/analysis but not production-grade demand forecasting.
