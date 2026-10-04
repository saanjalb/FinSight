"""
Budget service.

Budget status (spent vs. limit) is calculated live from the transactions
table on every request rather than stored — this guarantees it can never
drift out of sync with actual spending, at the cost of a bit more
computation per request, which is a fine trade-off at this data scale.
"""
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.budget import Budget
from backend.models.transaction import Transaction
from backend.schemas.budget import BudgetCreate, BudgetUpdate


def create_budget(db: Session, data: BudgetCreate) -> Budget:
    budget = Budget(**data.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def list_budgets(db: Session) -> list[Budget]:
    return db.query(Budget).order_by(Budget.category).all()


def get_budget(db: Session, budget_id: int) -> Optional[Budget]:
    return db.query(Budget).filter(Budget.id == budget_id).first()


def update_budget(db: Session, budget_id: int, updates: BudgetUpdate) -> Optional[Budget]:
    budget = get_budget(db, budget_id)
    if not budget:
        return None
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, budget_id: int) -> bool:
    budget = get_budget(db, budget_id)
    if not budget:
        return False
    db.delete(budget)
    db.commit()
    return True


def _spent_this_month(db: Session, category: str, year: int, month: int) -> float:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.category == category,
            Transaction.transaction_type == "expense",
            Transaction.date >= start,
            Transaction.date < end,
        )
        .all()
    )
    return sum(t.amount for t in txns)


def get_budget_status(db: Session, year: int, month: int) -> list[dict]:
    """Every budget joined with this month's actual spend and utilization."""
    budgets = list_budgets(db)
    result = []
    for b in budgets:
        spent = _spent_this_month(db, b.category, year, month)
        utilization = (spent / b.monthly_limit * 100) if b.monthly_limit > 0 else 0.0
        result.append({
            "id": b.id,
            "category": b.category,
            "monthly_limit": b.monthly_limit,
            "spent": round(spent, 2),
            "utilization_percent": round(utilization, 2),
            "remaining": round(b.monthly_limit - spent, 2),
            "over_budget": spent > b.monthly_limit,
        })
    return result
