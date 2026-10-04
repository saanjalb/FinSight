from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SavingsGoalCreate(BaseModel):
    name: str
    target_amount: float
    saved_amount: float = 0.0
    monthly_contribution: Optional[float] = None


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    saved_amount: Optional[float] = None
    monthly_contribution: Optional[float] = None


class SavingsGoalResponse(BaseModel):
    id: int
    name: str
    target_amount: float
    saved_amount: float
    monthly_contribution: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SavingsGoalProgress(BaseModel):
    """Goal joined with computed progress — never LLM-generated, per spec."""
    id: int
    name: str
    target_amount: float
    saved_amount: float
    remaining: float
    progress_percent: float
    monthly_contribution: Optional[float]
    estimated_months_to_complete: Optional[float]  # None if it can't be estimated yet
    estimation_note: str  # explains what the estimate is based on, or why there isn't one
