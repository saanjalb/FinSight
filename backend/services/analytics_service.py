"""
Analytics service.

Pure deterministic calculation — no LLM involved anywhere in this file,
per the project's architectural principle. This is the layer that both
the dashboard API and (later) the Finance Agent's tools will call for
any question that boils down to "add up / group / compare some numbers."
"""
from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.transaction import Transaction


def latest_data_month(db: Session) -> tuple[int, int]:
    """
    The (year, month) of the most recent transaction, falling back to the
    real current month when there is no data yet.

    This is the app-wide meaning of "this month". Using the calendar
    month instead would make every screen empty whenever the data ends
    before today (e.g. presenting in October with data through September).
    """
    from sqlalchemy import func

    latest = db.query(func.max(Transaction.date)).scalar()
    if latest is None:
        latest = date.today()
    return latest.year, latest.month


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def get_overview(db: Session, year: int, month: int) -> dict:
    """Income, expenses, balance, and savings rate for one calendar month."""
    start, end = _month_bounds(year, month)
    txns = db.query(Transaction).filter(Transaction.date >= start, Transaction.date < end).all()

    income = sum(t.amount for t in txns if t.transaction_type == "income")
    expenses = sum(t.amount for t in txns if t.transaction_type == "expense")
    savings = income - expenses
    savings_rate = (savings / income * 100) if income > 0 else 0.0

    return {
        "year": year,
        "month": month,
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "savings": round(savings, 2),
        "savings_rate_percent": round(savings_rate, 2),
        "transaction_count": len(txns),
    }


def get_spending_by_category(db: Session, year: int, month: int) -> list[dict]:
    """Expense total per category for one month, sorted descending."""
    start, end = _month_bounds(year, month)
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.transaction_type == "expense",
        )
        .all()
    )

    totals: dict[str, float] = defaultdict(float)
    for t in txns:
        totals[t.category or "Uncategorized"] += t.amount

    result = [{"category": cat, "amount": round(amt, 2)} for cat, amt in totals.items()]
    return sorted(result, key=lambda r: r["amount"], reverse=True)


def get_monthly_trend(db: Session, num_months: int = 6) -> list[dict]:
    """
    Income vs expense totals for each of the last N months that have
    data, oldest first — the shape a line/bar chart needs directly.
    """
    all_txns = db.query(Transaction).all()
    if not all_txns:
        return []

    by_month: dict[tuple[int, int], dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
    for t in all_txns:
        key = (t.date.year, t.date.month)
        if t.transaction_type == "income":
            by_month[key]["income"] += t.amount
        else:
            by_month[key]["expenses"] += t.amount

    sorted_months = sorted(by_month.keys())[-num_months:]
    return [
        {
            "year": y,
            "month": m,
            "income": round(by_month[(y, m)]["income"], 2),
            "expenses": round(by_month[(y, m)]["expenses"], 2),
        }
        for (y, m) in sorted_months
    ]


def get_top_merchants(db: Session, year: int, month: int, limit: int = 5) -> list[dict]:
    """Highest-total merchants (by expense amount) for one month."""
    start, end = _month_bounds(year, month)
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.transaction_type == "expense",
        )
        .all()
    )

    totals: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    for t in txns:
        totals[t.merchant]["total"] += t.amount
        totals[t.merchant]["count"] += 1

    result = [
        {"merchant": m, "total": round(v["total"], 2), "transaction_count": v["count"]}
        for m, v in totals.items()
    ]
    return sorted(result, key=lambda r: r["total"], reverse=True)[:limit]


def compare_periods(db: Session, year1: int, month1: int, year2: int, month2: int) -> dict:
    """
    Category-by-category comparison between two months. This is the
    calculation behind "why did my spending increase this month?" —
    the Finance Agent (Phase 8) will call this directly as a tool.
    """
    cats1 = {c["category"]: c["amount"] for c in get_spending_by_category(db, year1, month1)}
    cats2 = {c["category"]: c["amount"] for c in get_spending_by_category(db, year2, month2)}

    all_categories = set(cats1) | set(cats2)
    changes = []
    for cat in all_categories:
        prev = cats1.get(cat, 0.0)
        curr = cats2.get(cat, 0.0)
        change_pct = ((curr - prev) / prev * 100) if prev > 0 else (100.0 if curr > 0 else 0.0)
        changes.append({
            "category": cat,
            "previous_amount": round(prev, 2),
            "current_amount": round(curr, 2),
            "change_amount": round(curr - prev, 2),
            "change_percent": round(change_pct, 2),
        })

    changes.sort(key=lambda c: abs(c["change_amount"]), reverse=True)

    return {
        "period_1": {"year": year1, "month": month1},
        "period_2": {"year": year2, "month": month2},
        "overview_1": get_overview(db, year1, month1),
        "overview_2": get_overview(db, year2, month2),
        "category_changes": changes,
    }
