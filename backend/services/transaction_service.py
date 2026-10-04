"""
Transaction service layer.

This is where deterministic business logic lives — CRUD operations,
CSV parsing/validation, and filtering. Per the project's architectural
principle, this layer never calls an LLM; it's pure application logic
that the API layer (thin) and, later, the AI agent's tools (Phase 8)
will both call into — one source of truth for "how do I fetch/filter
transactions" whether the caller is a REST client or an LLM tool call.
"""
import csv
import io
from collections import Counter
from datetime import date as date_type
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.models.transaction import Transaction
from backend.schemas.transaction import TransactionCreate, TransactionUpdate


def create_transaction(db: Session, txn: TransactionCreate) -> Transaction:
    db_txn = Transaction(**txn.model_dump())
    db.add(db_txn)
    db.commit()
    db.refresh(db_txn)
    return db_txn


def get_transaction(db: Session, txn_id: int) -> Optional[Transaction]:
    return db.query(Transaction).filter(Transaction.id == txn_id).first()


def update_transaction(db: Session, txn_id: int, updates: TransactionUpdate) -> Optional[Transaction]:
    db_txn = get_transaction(db, txn_id)
    if not db_txn:
        return None
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_txn, field, value)
    db.commit()
    db.refresh(db_txn)
    return db_txn


def delete_transaction(db: Session, txn_id: int) -> bool:
    db_txn = get_transaction(db, txn_id)
    if not db_txn:
        return False
    db.delete(db_txn)
    db.commit()
    return True


def list_transactions(
    db: Session,
    category: Optional[str] = None,
    merchant: Optional[str] = None,
    date_from: Optional[date_type] = None,
    date_to: Optional[date_type] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
) -> list[Transaction]:
    """
    Query transactions with optional filters, combined with AND —
    e.g. category="Food & Dining" AND date_from=... narrows to that
    category within that date range.
    """
    query = db.query(Transaction)
    conditions = []

    if category:
        conditions.append(Transaction.category == category)
    if merchant:
        conditions.append(Transaction.merchant.ilike(f"%{merchant}%"))
    if date_from:
        conditions.append(Transaction.date >= date_from)
    if date_to:
        conditions.append(Transaction.date <= date_to)
    if min_amount is not None:
        conditions.append(Transaction.amount >= min_amount)
    if max_amount is not None:
        conditions.append(Transaction.amount <= max_amount)
    if search:
        like = f"%{search}%"
        conditions.append(
            (Transaction.merchant.ilike(like)) | (Transaction.description.ilike(like))
        )

    if conditions:
        query = query.filter(and_(*conditions))

    return query.order_by(Transaction.date.desc()).all()


def import_transactions_from_csv(db: Session, file_bytes: bytes) -> dict:
    """
    Parse a CSV file and bulk-insert transactions.

    Expected columns: date, merchant, amount, transaction_type, category,
    description (category/description optional — category gets filled by
    the categorization step in Phase 3 if left blank).

    Returns a summary dict rather than raising on row-level issues, so a
    partially-malformed file still imports the valid rows and reports
    which ones failed.
    """
    text = file_bytes.decode("utf-8-sig")  # handles BOM some banks/Excel add
    reader = csv.DictReader(io.StringIO(text))

    required_columns = {"date", "merchant", "amount", "transaction_type"}
    if not required_columns.issubset(set(reader.fieldnames or [])):
        missing = required_columns - set(reader.fieldnames or [])
        return {
            "imported": 0,
            "skipped_duplicates": 0,
            "failed": 0,
            "errors": [f"Missing required column(s): {', '.join(missing)}"],
        }

    imported = 0
    skipped = 0
    failed = 0
    errors = []

    # Make re-importing the same file harmless. Each row is matched against
    # rows already in the database by (date, merchant, amount, type). It is
    # a COUNT, not a set: if the file has two identical purchases and the DB
    # already has one, exactly one new row is added. So genuine repeat
    # purchases are kept, but importing the same file twice adds nothing.
    existing = Counter(
        (t.date.isoformat(), t.merchant.strip().upper(), round(t.amount, 2), t.transaction_type)
        for t in db.query(Transaction).all()
    )

    for i, row in enumerate(reader, start=2):  # start=2 accounts for header line
        try:
            txn = TransactionCreate(
                date=row["date"].strip(),
                merchant=row["merchant"].strip(),
                amount=float(row["amount"]),
                transaction_type=row["transaction_type"].strip().lower(),
                category=(row.get("category") or "").strip() or None,
                description=(row.get("description") or "").strip() or None,
            )
            key = (txn.date.isoformat(), txn.merchant.upper(), round(txn.amount, 2), txn.transaction_type)
            if existing[key] > 0:
                existing[key] -= 1
                skipped += 1
                continue
            create_transaction(db, txn)
            imported += 1
        except Exception as e:
            failed += 1
            errors.append(f"Row {i}: {e}")

    return {"imported": imported, "skipped_duplicates": skipped, "failed": failed, "errors": errors[:10]}
