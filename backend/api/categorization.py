"""
Categorization API routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.services import categorization_service

router = APIRouter(prefix="/api/categorization", tags=["categorization"])


@router.post("/train")
def train(db: Session = Depends(get_db)):
    """Train the ML categorizer on currently labeled transactions."""
    return categorization_service.train_model(db)


@router.post("/run")
def run_categorization(db: Session = Depends(get_db)):
    """Categorize every transaction currently missing a category."""
    return categorization_service.categorize_uncategorized(db)
