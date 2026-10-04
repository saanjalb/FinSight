from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.schemas.savings_goal import SavingsGoalCreate, SavingsGoalUpdate, SavingsGoalResponse, SavingsGoalProgress
from backend.services import savings_service

router = APIRouter(prefix="/api/savings-goals", tags=["savings-goals"])


@router.get("/", response_model=list[SavingsGoalProgress])
def list_goals(db: Session = Depends(get_db)):
    return savings_service.list_goals_with_progress(db)


@router.post("/", response_model=SavingsGoalResponse)
def create_goal(data: SavingsGoalCreate, db: Session = Depends(get_db)):
    return savings_service.create_goal(db, data)


@router.patch("/{goal_id}", response_model=SavingsGoalResponse)
def update_goal(goal_id: int, updates: SavingsGoalUpdate, db: Session = Depends(get_db)):
    goal = savings_service.update_goal(db, goal_id, updates)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    return goal


@router.delete("/{goal_id}")
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    if not savings_service.delete_goal(db, goal_id):
        raise HTTPException(status_code=404, detail="Savings goal not found")
    return {"deleted": True}
