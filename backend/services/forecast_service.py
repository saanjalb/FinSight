"""
Forecast service.

Combines two things that are each already correct on their own:
  1. The ML trend forecast (ml/forecasting.py) for expected totals.
  2. The recurring-payment detector from Phase 5 (subscription_service)
     for the concrete list of "upcoming expenses" — reused as-is rather
     than re-derived, since it's the same underlying question ("what
     recurring charges are coming up") asked over a longer window.

This is a good architecture talking point for the presentation: the
forecast isn't one monolithic black box, it's a composition of a
statistical model (for aggregate numbers) and existing deterministic
logic (for the concrete near-term expense list) — using the right tool
for each sub-question.
"""
from sqlalchemy.orm import Session

from backend.ml import forecasting
from backend.services import subscription_service

# A month is ~30 days — use that as the window for "expenses expected
# before the forecasted month is over."
FORECAST_WINDOW_DAYS = 30


def get_full_forecast(db: Session) -> dict:
    monthly_forecast = forecasting.forecast_next_month(db)

    if not monthly_forecast["available"]:
        return monthly_forecast

    upcoming = subscription_service.get_upcoming_payments(db, within_days=FORECAST_WINDOW_DAYS)
    upcoming_expenses = [
        {
            "merchant": u["merchant"],
            "category": u["category"],
            "expected_amount": u["latest_amount"],
            "expected_date": u["next_expected"],
        }
        for u in upcoming
    ]

    monthly_forecast["upcoming_expenses"] = upcoming_expenses
    monthly_forecast["upcoming_expenses_total"] = round(
        sum(u["expected_amount"] for u in upcoming_expenses), 2
    )
    return monthly_forecast
