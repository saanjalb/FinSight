"""
Categorization service — thin orchestration layer between the API and
the ml/categorization.py engine. Keeps DB queries here, keeps the ML
module free of any database/ORM knowledge (so it stays testable and
reusable independent of how transactions are stored).
"""
from sqlalchemy.orm import Session

from backend.models.transaction import Transaction
from backend.ml import categorization


def categorize_uncategorized(db: Session) -> dict:
    """
    Find every transaction with no category and run the pipeline on it.
    Returns a summary of how many were resolved by rules vs ML vs left
    uncategorized (candidates for LLM fallback once that's wired).
    """
    uncategorized = db.query(Transaction).filter(Transaction.category.is_(None)).all()

    resolved_by_rule = 0
    resolved_by_ml = 0
    still_uncategorized = 0

    for txn in uncategorized:
        result = categorization.categorize_transaction(txn.merchant)
        if result["category"]:
            txn.category = result["category"]
            if result["source"] == "rule":
                resolved_by_rule += 1
            elif result["source"] == "ml":
                resolved_by_ml += 1
        else:
            still_uncategorized += 1

    db.commit()

    return {
        "total_processed": len(uncategorized),
        "resolved_by_rule": resolved_by_rule,
        "resolved_by_ml": resolved_by_ml,
        "still_uncategorized": still_uncategorized,
    }


def train_model(db: Session) -> dict:
    """Train (or retrain) the ML categorizer on current labeled data."""
    return categorization.train_ml_categorizer(db)
