from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float


class BudgetUpdate(BaseModel):
    monthly_limit: Optional[float] = None


class BudgetResponse(BaseModel):
    id: int
    category: str
    monthly_limit: float
    created_at: datetime

    class Config:
        from_attributes = True


class BudgetStatus(BaseModel):
    """Budget joined with this month's actual spending — computed, not stored."""
    id: int
    category: str
    monthly_limit: float
    spent: float
    utilization_percent: float
    remaining: float
    over_budget: bool
