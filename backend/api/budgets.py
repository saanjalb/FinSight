from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from backend.services import budget_service, analytics_service

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("/", response_model=list[BudgetResponse])
def list_budgets(db: Session = Depends(get_db)):
    return budget_service.list_budgets(db)


@router.post("/", response_model=BudgetResponse)
def create_budget(data: BudgetCreate, db: Session = Depends(get_db)):
    return budget_service.create_budget(db, data)


@router.patch("/{budget_id}", response_model=BudgetResponse)
def update_budget(budget_id: int, updates: BudgetUpdate, db: Session = Depends(get_db)):
    budget = budget_service.update_budget(db, budget_id, updates)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.delete("/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    if not budget_service.delete_budget(db, budget_id):
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"deleted": True}


@router.get("/status")
def budget_status(year: int | None = None, month: int | None = None, db: Session = Depends(get_db)):
    y, m = (year, month) if year and month else analytics_service.latest_data_month(db)
    return budget_service.get_budget_status(db, y, m)
