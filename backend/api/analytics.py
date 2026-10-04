"""
Analytics API routes. Thin — all calculation lives in analytics_service.py.

year/month default to the current month if not supplied, since that's
the overwhelmingly common case for a dashboard.
"""
from datetime import date as date_type
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.services import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _default_year_month(db: Session):
    return analytics_service.latest_data_month(db)


@router.get("/overview")
def overview(year: int | None = None, month: int | None = None, db: Session = Depends(get_db)):
    y, m = (year, month) if year and month else _default_year_month(db)
    return analytics_service.get_overview(db, y, m)


@router.get("/by-category")
def by_category(year: int | None = None, month: int | None = None, db: Session = Depends(get_db)):
    y, m = (year, month) if year and month else _default_year_month(db)
    return analytics_service.get_spending_by_category(db, y, m)


@router.get("/monthly-trend")
def monthly_trend(num_months: int = 6, db: Session = Depends(get_db)):
    return analytics_service.get_monthly_trend(db, num_months)


@router.get("/top-merchants")
def top_merchants(
    year: int | None = None,
    month: int | None = None,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    y, m = (year, month) if year and month else _default_year_month(db)
    return analytics_service.get_top_merchants(db, y, m, limit)


@router.get("/compare")
def compare(
    year1: int = Query(...), month1: int = Query(...),
    year2: int = Query(...), month2: int = Query(...),
    db: Session = Depends(get_db),
):
    return analytics_service.compare_periods(db, year1, month1, year2, month2)
