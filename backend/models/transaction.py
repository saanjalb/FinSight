"""
Transaction database model.

This is the central table FinSight is built around — every analytics,
ML, and AI feature downstream reads from this table.
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from sqlalchemy.sql import func
from backend.db.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    merchant = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)  # "income" or "expense"
    category = Column(String, nullable=True, index=True)  # filled by categorization later
    description = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
