from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.services import forecast_service

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("/next-month")
def next_month_forecast(db: Session = Depends(get_db)):
    """
    Projected income/expenses/savings for next month, plus concrete
    recurring expenses expected in that window. Always a projection —
    see the `is_forecast` flag and `method` field in the response.
    """
    return forecast_service.get_full_forecast(db)
