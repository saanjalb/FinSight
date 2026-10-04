from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.services import subscription_service, leak_detection_service

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/subscriptions")
def subscriptions(db: Session = Depends(get_db)):
    """All detected recurring payments/subscriptions."""
    return subscription_service.detect_recurring_payments(db)


@router.get("/upcoming-payments")
def upcoming_payments(within_days: int = 10, db: Session = Depends(get_db)):
    return subscription_service.get_upcoming_payments(db, within_days)


@router.get("/duplicate-subscriptions")
def duplicate_subscriptions(db: Session = Depends(get_db)):
    """Categories with more than one recurring charge — potential overlap."""
    return subscription_service.detect_potential_duplicates(db)


@router.get("/spending-leaks")
def spending_leaks(db: Session = Depends(get_db)):
    """All three leak-detection categories combined."""
    return leak_detection_service.get_all_spending_leaks(db)
