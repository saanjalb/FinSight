"""
Transaction API routes.

Kept intentionally thin: every route delegates to transaction_service.py.
No business logic here — just request parsing and response shaping.
"""
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from backend.services import transaction_service, categorization_service

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/", response_model=List[TransactionResponse])
def list_transactions(
    category: Optional[str] = None,
    merchant: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    List transactions with optional filters, all combinable — e.g.
    /api/transactions/?category=Food & Dining&date_from=2026-08-01
    """
    return transaction_service.list_transactions(
        db,
        category=category,
        merchant=merchant,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
    )


@router.post("/", response_model=TransactionResponse)
def create_transaction(txn: TransactionCreate, db: Session = Depends(get_db)):
    return transaction_service.create_transaction(db, txn)


@router.get("/{txn_id}", response_model=TransactionResponse)
def get_transaction(txn_id: int, db: Session = Depends(get_db)):
    txn = transaction_service.get_transaction(db, txn_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.patch("/{txn_id}", response_model=TransactionResponse)
def update_transaction(txn_id: int, updates: TransactionUpdate, db: Session = Depends(get_db)):
    txn = transaction_service.update_transaction(db, txn_id, updates)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.delete("/{txn_id}")
def delete_transaction(txn_id: int, db: Session = Depends(get_db)):
    deleted = transaction_service.delete_transaction(db, txn_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"deleted": True}


@router.post("/import")
async def import_transactions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Bulk import transactions from a CSV file.
    Expected columns: date, merchant, amount, transaction_type[, category, description]
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")
    content = await file.read()
    result = transaction_service.import_transactions_from_csv(db, content)

    # Auto-categorize whatever arrived without a category: rules first, then
    # the ML model. The model is (re)trained first on the rows that DO have
    # labels, so it learns this user's own merchants. Anything neither stage
    # is confident about stays uncategorized (the future LLM-fallback slot).
    if result["imported"] > 0:
        categorization_service.train_model(db)
        result["categorization"] = categorization_service.categorize_uncategorized(db)
    return result
