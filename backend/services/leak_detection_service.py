"""
Spending-leak detection.

Three independent detectors, each pure calculation (no LLM):
  1. Category increase — this month vs last month, reusing the same
     compare_periods logic the Finance Agent will later call directly.
  2. Frequent small purchases — many sub-threshold transactions in one
     category that add up, even though no single one looks alarming.
  3. Unusual category spending — this month vs this category's own
     trailing 3-month average, catching drift that a single
     month-over-month comparison might miss (e.g. a slow creep).

Each detector returns structured facts plus a plain-English sentence
built from a template. The template wording is a placeholder — Phase
10 will swap it for real LLM-generated explanations without changing
anything here, since the structured fields stay identical.
"""
from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.transaction import Transaction
from backend.services import analytics_service

# A category increase must clear both bars to be worth flagging —
# otherwise noise from small categories (e.g. Healthcare going from
# ₹100 to ₹250) would swamp genuinely meaningful increases.
CATEGORY_INCREASE_PCT_THRESHOLD = 20.0
CATEGORY_INCREASE_MIN_AMOUNT = 500.0

# "Small purchase" ceiling and how many of them in a month counts as
# a pattern worth flagging.
SMALL_PURCHASE_CEILING = 500.0
SMALL_PURCHASE_COUNT_THRESHOLD = 15

# This month's category spend must exceed its own trailing average by
# this fraction to count as "unusual."
UNUSUAL_SPENDING_THRESHOLD_PCT = 30.0


# "Uncategorized" is a catch-all bucket, not a spending habit — a jump in it
# usually just means a new merchant hasn't been categorized yet. Those rows
# are visible (and editable) in the Transactions tab, so alerting on them
# would only produce scary but meaningless warnings.
IGNORED_CATEGORIES = {"Uncategorized"}


def _current_and_previous_month(latest_date: date) -> tuple[tuple[int, int], tuple[int, int]]:
    y, m = latest_date.year, latest_date.month
    if m == 1:
        return (y, m), (y - 1, 12)
    return (y, m), (y, m - 1)


def detect_category_increases(db: Session) -> list[dict]:
    latest = db.query(Transaction).order_by(Transaction.date.desc()).first()
    if not latest:
        return []
    (cy, cm), (py, pm) = _current_and_previous_month(latest.date)

    comparison = analytics_service.compare_periods(db, py, pm, cy, cm)
    leaks = []
    for change in comparison["category_changes"]:
        if change["category"] in IGNORED_CATEGORIES:
            continue
        if (
            change["change_percent"] >= CATEGORY_INCREASE_PCT_THRESHOLD
            and change["change_amount"] >= CATEGORY_INCREASE_MIN_AMOUNT
        ):
            leaks.append({
                "type": "category_increase",
                "category": change["category"],
                "previous_amount": change["previous_amount"],
                "current_amount": change["current_amount"],
                "change_amount": change["change_amount"],
                "change_percent": change["change_percent"],
                "severity": "high" if change["change_percent"] >= 50 else "medium",
                "explanation": (
                    f"{change['category']} spending increased {change['change_percent']:.1f}% "
                    f"(₹{change['previous_amount']:,.0f} → ₹{change['current_amount']:,.0f})."
                ),
            })
    return sorted(leaks, key=lambda l: l["change_amount"], reverse=True)


def detect_frequent_small_purchases(db: Session) -> list[dict]:
    latest = db.query(Transaction).order_by(Transaction.date.desc()).first()
    if not latest:
        return []
    y, m = latest.date.year, latest.date.month
    start = date(y, m, 1)
    end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)

    small_txns = (
        db.query(Transaction)
        .filter(
            Transaction.transaction_type == "expense",
            Transaction.amount < SMALL_PURCHASE_CEILING,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .all()
    )

    by_category: dict[str, list[Transaction]] = defaultdict(list)
    for t in small_txns:
        by_category[t.category or "Uncategorized"].append(t)

    results = []
    for category, txns in by_category.items():
        if category in IGNORED_CATEGORIES:
            continue
        if len(txns) >= SMALL_PURCHASE_COUNT_THRESHOLD:
            total = sum(t.amount for t in txns)
            avg = total / len(txns)
            results.append({
                "type": "frequent_small_purchases",
                "category": category,
                "transaction_count": len(txns),
                "total_amount": round(total, 2),
                "average_amount": round(avg, 2),
                "severity": "medium",
                "explanation": (
                    f"{len(txns)} {category} transactions this month, averaging "
                    f"₹{avg:,.0f} each — ₹{total:,.0f} total."
                ),
            })
    return sorted(results, key=lambda r: r["total_amount"], reverse=True)


def detect_unusual_category_spending(db: Session, trailing_months: int = 3) -> list[dict]:
    latest = db.query(Transaction).order_by(Transaction.date.desc()).first()
    if not latest:
        return []
    current_year, current_month = latest.date.year, latest.date.month

    current_spend = {
        c["category"]: c["amount"]
        for c in analytics_service.get_spending_by_category(db, current_year, current_month)
    }

    # Walk backward through the trailing months, collecting per-category totals.
    trailing_totals: dict[str, list[float]] = defaultdict(list)
    y, m = current_year, current_month
    for _ in range(trailing_months):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        month_spend = {
            c["category"]: c["amount"]
            for c in analytics_service.get_spending_by_category(db, y, m)
        }
        for category, amount in month_spend.items():
            trailing_totals[category].append(amount)

    results = []
    for category, current_amount in current_spend.items():
        if category in IGNORED_CATEGORIES:
            continue
        history = trailing_totals.get(category, [])
        if not history:
            continue
        trailing_avg = sum(history) / len(history)
        if trailing_avg <= 0:
            continue
        pct_above = (current_amount - trailing_avg) / trailing_avg * 100
        if pct_above >= UNUSUAL_SPENDING_THRESHOLD_PCT:
            results.append({
                "type": "unusual_category_spending",
                "category": category,
                "current_amount": round(current_amount, 2),
                "trailing_average": round(trailing_avg, 2),
                "percent_above_average": round(pct_above, 2),
                "severity": "high" if pct_above >= 60 else "medium",
                "explanation": (
                    f"{category} is {pct_above:.0f}% higher than your "
                    f"{trailing_months}-month average (₹{current_amount:,.0f} vs ₹{trailing_avg:,.0f})."
                ),
            })
    return sorted(results, key=lambda r: r["percent_above_average"], reverse=True)


def get_all_spending_leaks(db: Session) -> dict:
    return {
        "category_increases": detect_category_increases(db),
        "frequent_small_purchases": detect_frequent_small_purchases(db),
        "unusual_category_spending": detect_unusual_category_spending(db),
    }
