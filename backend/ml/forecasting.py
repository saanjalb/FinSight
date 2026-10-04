"""
Cash-flow forecasting.

Uses linear regression (scikit-learn) on the monthly income/expense
trend to project next month's numbers — a genuine statistical model,
appropriately simple for the data volume a personal-finance app
actually has (a handful of months, not years of daily data that would
justify something heavier like ARIMA or a neural forecaster).

Per the project's reliability requirements (Section 22): every forecast
is clearly labeled as a projection, never presented as an actual value,
and includes the basis it was computed from so the user can judge how
much to trust it.
"""
from typing import Optional

import numpy as np
from sklearn.linear_model import LinearRegression

from sqlalchemy.orm import Session

from backend.services import analytics_service

MIN_MONTHS_FOR_REGRESSION = 3  # fewer than this and a trend line is mostly noise


def _fit_and_predict(values: list[float]) -> tuple[float, float]:
    """
    Fits a line through (month_index, value) and predicts the next index.
    Returns (prediction, r_squared) — r_squared indicates how much of the
    month-to-month variation the trend line actually explains; low values
    mean the prediction should be trusted less.
    """
    X = np.arange(len(values)).reshape(-1, 1)
    y = np.array(values)

    model = LinearRegression()
    model.fit(X, y)

    next_index = np.array([[len(values)]])
    prediction = float(model.predict(next_index)[0])

    r_squared = model.score(X, y) if len(values) > 2 else 0.0

    return max(prediction, 0.0), r_squared  # a forecast can't be meaningfully negative here


def forecast_next_month(db: Session, history_months: int = 6) -> dict:
    """
    Projects next month's income, expenses, and savings from the
    trailing `history_months` of actual data.
    """
    trend = analytics_service.get_monthly_trend(db, num_months=history_months)

    if len(trend) < 2:
        return {
            "available": False,
            "reason": "Not enough transaction history to forecast yet — need at least 2 months of data.",
        }

    incomes = [t["income"] for t in trend]
    expenses = [t["expenses"] for t in trend]

    if len(trend) < MIN_MONTHS_FOR_REGRESSION:
        # Too little history for a trend line to mean anything — fall back
        # to "next month looks like the average of what we've seen," and
        # say so plainly rather than dressing up a guess as a regression.
        predicted_income = sum(incomes) / len(incomes)
        predicted_expenses = sum(expenses) / len(expenses)
        method = f"Average of the last {len(trend)} month(s) — too little history yet for a trend line."
        income_confidence = expense_confidence = None
    else:
        predicted_income, income_r2 = _fit_and_predict(incomes)
        predicted_expenses, expense_r2 = _fit_and_predict(expenses)
        method = f"Linear regression trend over the last {len(trend)} months."
        income_confidence = round(income_r2, 2)
        expense_confidence = round(expense_r2, 2)

    # Next month/year label, derived from the last month in the trend.
    last_year, last_month = trend[-1]["year"], trend[-1]["month"]
    forecast_month = last_month + 1
    forecast_year = last_year
    if forecast_month > 12:
        forecast_month = 1
        forecast_year += 1

    predicted_savings = predicted_income - predicted_expenses

    return {
        "available": True,
        "is_forecast": True,  # explicit flag — never to be confused with actuals by any consumer
        "forecast_year": forecast_year,
        "forecast_month": forecast_month,
        "expected_income": round(predicted_income, 2),
        "expected_expenses": round(predicted_expenses, 2),
        "expected_savings": round(predicted_savings, 2),
        "method": method,
        "income_trend_confidence": income_confidence,
        "expense_trend_confidence": expense_confidence,
        "based_on_months": len(trend),
    }
