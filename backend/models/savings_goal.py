"""
SavingsGoal model. `saved_amount` is a running total the user updates
directly (e.g. "add ₹5,000 to this goal") — it does not automatically
pull from transaction data, since a savings goal often represents money
set aside outside day-to-day spending (a separate account, an FD, etc.)
rather than something derivable from the transaction feed.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from backend.db.database import Base


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    saved_amount = Column(Float, nullable=False, default=0.0)
    monthly_contribution = Column(Float, nullable=True)  # optional user-declared rate
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
