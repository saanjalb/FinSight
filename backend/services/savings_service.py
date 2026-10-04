"""
Savings goal service.

The time-to-completion estimate follows a strict priority order and is
always a plain arithmetic calculation — never an LLM guess, per the
project's Section 14 requirement:

  1. If the user declared a monthly_contribution on the goal, use it directly.
  2. Otherwise, derive a rate from the average of the last 3 months' actual
     savings (income - expenses) from the transaction data.
  3. If neither is available/positive, return no estimate rather than a
     misleading number — and say why in estimation_note.
"""
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.savings_goal import SavingsGoal
from backend.schemas.savings_goal import SavingsGoalCreate, SavingsGoalUpdate
from backend.services import analytics_service


def create_goal(db: Session, data: SavingsGoalCreate) -> SavingsGoal:
    goal = SavingsGoal(**data.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def list_goals(db: Session) -> list[SavingsGoal]:
    return db.query(SavingsGoal).order_by(SavingsGoal.created_at.desc()).all()


def get_goal(db: Session, goal_id: int) -> Optional[SavingsGoal]:
    return db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()


def update_goal(db: Session, goal_id: int, updates: SavingsGoalUpdate) -> Optional[SavingsGoal]:
    goal = get_goal(db, goal_id)
    if not goal:
        return None
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal_id: int) -> bool:
    goal = get_goal(db, goal_id)
    if not goal:
        return False
    db.delete(goal)
    db.commit()
    return True


def _historical_avg_monthly_savings(db: Session, num_months: int = 3) -> Optional[float]:
    """Average of (income - expenses) over the last N months with data."""
    trend = analytics_service.get_monthly_trend(db, num_months=num_months)
    if not trend:
        return None
    savings_values = [t["income"] - t["expenses"] for t in trend]
    return sum(savings_values) / len(savings_values)


def get_goal_progress(db: Session, goal: SavingsGoal) -> dict:
    remaining = goal.target_amount - goal.saved_amount
    progress_percent = (goal.saved_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0.0

    monthly_rate: Optional[float] = None
    note_source = ""

    if goal.monthly_contribution and goal.monthly_contribution > 0:
        monthly_rate = goal.monthly_contribution
        note_source = "your declared monthly contribution"
    else:
        avg = _historical_avg_monthly_savings(db)
        if avg and avg > 0:
            monthly_rate = avg
            note_source = "your average monthly savings over the last 3 months"

    if remaining <= 0:
        estimated_months = 0.0
        note = "Goal already reached."
    elif monthly_rate:
        estimated_months = round(remaining / monthly_rate, 1)
        note = f"Estimated using {note_source} (₹{monthly_rate:,.0f}/month)."
    else:
        estimated_months = None
        note = "Not enough data to estimate — set a monthly contribution or build up a few months of transaction history."

    return {
        "id": goal.id,
        "name": goal.name,
        "target_amount": goal.target_amount,
        "saved_amount": goal.saved_amount,
        "remaining": round(remaining, 2),
        "progress_percent": round(progress_percent, 2),
        "monthly_contribution": goal.monthly_contribution,
        "estimated_months_to_complete": estimated_months,
        "estimation_note": note,
    }


def list_goals_with_progress(db: Session) -> list[dict]:
    return [get_goal_progress(db, g) for g in list_goals(db)]
