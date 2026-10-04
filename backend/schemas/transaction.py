"""
Pydantic schemas for the Transaction API.

Kept separate from the SQLAlchemy model (models/transaction.py) on purpose:
the DB model is the storage shape, this is the wire shape. They often
overlap now but will diverge later (e.g. we may not want to expose
internal fields, or may want to add computed fields to responses).
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class TransactionBase(BaseModel):
    date: date
    merchant: str
    amount: float
    transaction_type: str  # "income" or "expense"
    category: Optional[str] = None
    description: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Shape expected when creating a transaction."""
    pass


class TransactionUpdate(BaseModel):
    """
    Shape for partial updates (e.g. user corrects a category).
    All fields optional — only fields actually sent get changed,
    via exclude_unset in the service layer.
    """
    date: Optional[date] = None
    merchant: Optional[str] = None
    amount: Optional[float] = None
    transaction_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None


class TransactionResponse(TransactionBase):
    """Shape returned to the frontend."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # allows creating this from an ORM object directly
