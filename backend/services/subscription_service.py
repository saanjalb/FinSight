"""
Subscription / recurring-payment detection.

Pure statistics — no LLM. A merchant is treated as "recurring" if it
charges the user repeatedly across multiple distinct months at a
roughly consistent amount. This catches real subscriptions (Netflix,
gym) as well as recurring bills (rent, internet) — anything that
repeats predictably, which is the behavior users actually care about
regardless of whether it's technically a "subscription."
"""
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.transaction import Transaction

# A merchant needs to appear in at least this many distinct months to
# be considered recurring — one-off purchases from the same store
# (e.g. two unrelated Amazon orders) shouldn't count.
MIN_DISTINCT_MONTHS = 2

# Amounts across occurrences must be within this fraction of their mean
# to count as "the same charge" — allows for small variation (taxes,
# minor plan changes) without treating genuinely different purchases
# as one recurring series.
AMOUNT_CONSISTENCY_THRESHOLD = 0.20

# A charge in the last N days from "today" (the most recent transaction
# date in the dataset) is flagged as "upcoming" for the next cycle.
UPCOMING_WINDOW_DAYS = 10

# A change between the two most recent occurrences bigger than this
# fraction is flagged as "amount changed."
AMOUNT_CHANGE_THRESHOLD = 0.05


def detect_recurring_payments(db: Session) -> list[dict]:
    txns = (
        db.query(Transaction)
        .filter(Transaction.transaction_type == "expense")
        .order_by(Transaction.date)
        .all()
    )
    if not txns:
        return []

    # "Today" is anchored to the most recent transaction in the data,
    # not the real calendar date — makes "upcoming" detection meaningful
    # for a synthetic/demo dataset that may not extend to today.
    latest_date = max(t.date for t in txns)

    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for t in txns:
        by_merchant[t.merchant].append(t)

    results = []
    for merchant, group in by_merchant.items():
        distinct_months = {(t.date.year, t.date.month) for t in group}
        if len(distinct_months) < MIN_DISTINCT_MONTHS:
            continue

        amounts = [t.amount for t in group]
        avg_amount = mean(amounts)
        # Coefficient of variation — stdev relative to the mean, so it
        # works regardless of the absolute amount size.
        variation = (pstdev(amounts) / avg_amount) if avg_amount > 0 else 0
        if variation > AMOUNT_CONSISTENCY_THRESHOLD:
            continue  # too inconsistent to call this a recurring charge

        group_sorted = sorted(group, key=lambda t: t.date)
        last_txn = group_sorted[-1]

        # Scan every consecutive pair in the history for a change, not just
        # the most recent step — a price increase can "settle" for a couple
        # of cycles before we look, and only comparing the last two would
        # miss it entirely once it's no longer the very latest transition.
        amount_changed = False
        change_percent = 0.0
        change_detected_at: Optional[str] = None
        for i in range(1, len(group_sorted)):
            prev_amt = group_sorted[i - 1].amount
            curr_amt = group_sorted[i].amount
            if prev_amt <= 0:
                continue
            pct = (curr_amt - prev_amt) / prev_amt * 100
            if abs(pct) > AMOUNT_CHANGE_THRESHOLD * 100:
                amount_changed = True
                change_percent = pct  # keep the most recent qualifying change
                change_detected_at = group_sorted[i].date.isoformat()

        # Estimate cycle length from average gap between consecutive charges.
        gaps = [
            (group_sorted[i].date - group_sorted[i - 1].date).days
            for i in range(1, len(group_sorted))
        ]
        avg_cycle_days = round(mean(gaps)) if gaps else 30

        next_expected = last_txn.date + timedelta(days=avg_cycle_days)
        days_until_next = (next_expected - latest_date).days
        is_upcoming = 0 <= days_until_next <= UPCOMING_WINDOW_DAYS

        results.append({
            "merchant": merchant,
            "category": last_txn.category,
            "average_amount": round(avg_amount, 2),
            "latest_amount": round(last_txn.amount, 2),
            "occurrences": len(group),
            "distinct_months": len(distinct_months),
            "estimated_cycle_days": avg_cycle_days,
            "last_charged": last_txn.date.isoformat(),
            "next_expected": next_expected.isoformat(),
            "days_until_next": days_until_next,
            "is_upcoming": is_upcoming,
            "amount_changed": amount_changed,
            "amount_change_percent": round(change_percent, 2),
        })

    # Upcoming and changed ones are the most actionable — surface first.
    results.sort(key=lambda r: (not r["is_upcoming"], not r["amount_changed"], -r["average_amount"]))
    return results


def get_upcoming_payments(db: Session, within_days: int = 10) -> list[dict]:
    """Subset of recurring payments expected within the given window."""
    all_recurring = detect_recurring_payments(db)
    return [r for r in all_recurring if 0 <= r["days_until_next"] <= within_days]


def detect_potential_duplicates(db: Session) -> list[dict]:
    """
    Flag categories where more than one recurring merchant is charging
    the user — e.g. two cloud storage services, or an unused gym
    membership sitting alongside a newer one. This is a category-level
    heuristic, not a merchant-name-similarity one: it surfaces genuine
    overlap (multiple streaming services) without trying to guess
    whether "CLOUD STORAGE" and "CLOUD STORAGE PRO" are the same thing.
    """
    recurring = detect_recurring_payments(db)

    by_category: dict[str, list[dict]] = defaultdict(list)
    for r in recurring:
        by_category[r["category"] or "Uncategorized"].append(r)

    results = []
    for category, merchants in by_category.items():
        if len(merchants) < 2:
            continue
        total_monthly_cost = sum(m["average_amount"] for m in merchants)
        results.append({
            "category": category,
            "merchant_count": len(merchants),
            "merchants": [
                {"merchant": m["merchant"], "average_amount": m["average_amount"]}
                for m in merchants
            ],
            "total_monthly_cost": round(total_monthly_cost, 2),
            "explanation": (
                f"You have {len(merchants)} recurring charges in {category}: "
                + ", ".join(m["merchant"] for m in merchants)
                + f" — ₹{total_monthly_cost:,.0f}/month combined."
            ),
        })

    return sorted(results, key=lambda r: r["total_monthly_cost"], reverse=True)
