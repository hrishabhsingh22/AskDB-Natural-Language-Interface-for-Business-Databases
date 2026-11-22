import numpy as np
import pandas as pd


def monthly_sales_series(df):
    monthly_sales = (
        df.dropna(subset=["date"])
        .assign(month=df["date"].dt.to_period("M"))
        .groupby("month", as_index=False)["amount"]
        .sum()
        .sort_values("month")
    )
    monthly_sales["month"] = monthly_sales["month"].astype(str)
    return monthly_sales


def forecast_next_month_sales(df):
    monthly_sales = monthly_sales_series(df)

    if monthly_sales.empty:
        return {
            "forecast_month": None,
            "predicted_sales": None,
            "history": monthly_sales,
        }

    month_periods = pd.PeriodIndex(monthly_sales["month"], freq="M")
    next_month = (month_periods[-1] + 1).strftime("%Y-%m")

    if len(monthly_sales) == 1:
        predicted_sales = float(monthly_sales["amount"].iloc[0])
    else:
        x = np.arange(len(monthly_sales), dtype=float)
        y = monthly_sales["amount"].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        predicted_sales = max(0.0, float(intercept + slope * len(monthly_sales)))

    forecast_row = pd.DataFrame(
        [{"month": next_month, "amount": round(predicted_sales, 2)}]
    )
    chart_data = pd.concat([monthly_sales, forecast_row], ignore_index=True)
    chart_data["series"] = ["historical"] * len(monthly_sales) + ["forecast"]

    return {
        "forecast_month": next_month,
        "predicted_sales": round(predicted_sales, 2),
        "history": monthly_sales,
        "chart_data": chart_data,
    }
