"""
What-If scenario simulator (deterministic backend logic).

All arithmetic for scenarios lives here. The LLM's only job (see
ai/scenario_parser.py) is to turn a natural-language sentence into the
structured parameters this module accepts — it never sees or produces a
result number.

Every scenario compares against the same baseline: the AVERAGE monthly
income / expenses / savings over the last 3 months of data. An average
is used instead of the latest month because one unusual month (e.g. the
food-spending spike in our dataset) would make the "before" picture
misleading.

Results are always labelled is_scenario=True — hypothetical, not actual
and not a forecast.
"""
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from backend.services import analytics_service, subscription_service, savings_service

BASELINE_MONTHS = 3
SCENARIO_TYPES = ("reduce_category", "increase_savings", "cancel_subscriptions")


class ScenarioError(ValueError):
    """Bad or unsupported scenario input — message is safe to show the user."""


def get_baseline(db: Session) -> dict:
    trend = analytics_service.get_monthly_trend(db, BASELINE_MONTHS)
    if not trend:
        raise ScenarioError("There is no transaction data yet, so there is nothing to simulate against.")

    n = len(trend)
    income = sum(t["income"] for t in trend) / n
    expenses = sum(t["expenses"] for t in trend) / n

    category_totals: dict[str, float] = defaultdict(float)
    for t in trend:
        for row in analytics_service.get_spending_by_category(db, t["year"], t["month"]):
            category_totals[row["category"]] += row["amount"]
    category_avg = {c: total / n for c, total in category_totals.items()}

    savings = income - expenses
    return {
        "months_used": n,
        "avg_monthly_income": round(income, 2),
        "avg_monthly_expenses": round(expenses, 2),
        "avg_monthly_savings": round(savings, 2),
        "savings_rate_percent": round(savings / income * 100, 2) if income > 0 else 0.0,
        "category_avg": category_avg,
    }


def _rate(savings: float, income: float) -> float:
    return round(savings / income * 100, 2) if income > 0 else 0.0


def _match_category(name: str, known: list[str]) -> Optional[str]:
    lowered = name.strip().lower()
    for c in known:
        if c.lower() == lowered:
            return c
    return None


def _result(kind: str, title: str, baseline: dict, monthly_saved: float, assumptions: list[str], details: dict) -> dict:
    """Shared output shape so the UI can render every scenario the same way."""
    new_expenses = baseline["avg_monthly_expenses"] - monthly_saved
    new_savings = baseline["avg_monthly_savings"] + monthly_saved
    return {
        "is_scenario": True,
        "scenario_type": kind,
        "title": title,
        "baseline": {
            "months_used": baseline["months_used"],
            "avg_monthly_income": baseline["avg_monthly_income"],
            "avg_monthly_expenses": baseline["avg_monthly_expenses"],
            "avg_monthly_savings": baseline["avg_monthly_savings"],
            "savings_rate_percent": baseline["savings_rate_percent"],
        },
        "scenario": {
            "avg_monthly_expenses": round(new_expenses, 2),
            "avg_monthly_savings": round(new_savings, 2),
            "savings_rate_percent": _rate(new_savings, baseline["avg_monthly_income"]),
        },
        "monthly_difference": round(monthly_saved, 2),
        "annual_difference": round(monthly_saved * 12, 2),
        "assumptions": assumptions,
        "details": details,
    }


def _goal_impact(db: Session, baseline: dict, extra_monthly: float) -> list[dict]:
    """Months-to-goal at the baseline savings pace vs. with the extra amount."""
    impacts = []
    base = baseline["avg_monthly_savings"]
    for g in savings_service.list_goals_with_progress(db):
        remaining = g["remaining"]
        if remaining <= 0:
            continue
        before = round(remaining / base, 1) if base > 0 else None
        after = round(remaining / (base + extra_monthly), 1) if (base + extra_monthly) > 0 else None
        impacts.append({"goal": g["name"], "remaining": remaining, "months_before": before, "months_after": after})
    return impacts


def simulate_scenario(
    db: Session,
    scenario_type: str,
    category: Optional[str] = None,
    percent: Optional[float] = None,
    amount: Optional[float] = None,
    merchants: Optional[list[str]] = None,
) -> dict:
    if scenario_type not in SCENARIO_TYPES:
        raise ScenarioError(f"Unsupported scenario type. Supported: {', '.join(SCENARIO_TYPES)}.")

    baseline = get_baseline(db)

    if scenario_type == "reduce_category":
        if not category:
            raise ScenarioError("Which spending category should be reduced?")
        if percent is None or not (0 < percent <= 100):
            raise ScenarioError("The reduction must be a percentage between 0 and 100.")
        known = sorted(baseline["category_avg"].keys())
        matched = _match_category(category, known)
        if not matched:
            raise ScenarioError(f"I couldn't find a '{category}' category. Your categories are: {', '.join(known)}.")

        current = baseline["category_avg"][matched]
        saved = current * percent / 100
        return _result(
            scenario_type,
            f"Reduce {matched} spending by {percent:g}%",
            baseline,
            saved,
            [
                f"Baseline is your average monthly spend over the last {baseline['months_used']} months.",
                "All other income and spending stay exactly the same.",
            ],
            {
                "category": matched,
                "percent_reduction": percent,
                "current_monthly_spend": round(current, 2),
                "new_monthly_spend": round(current - saved, 2),
            },
        )

    if scenario_type == "increase_savings":
        if amount is None or amount <= 0:
            raise ScenarioError("Please give a positive monthly amount to save.")
        return _result(
            scenario_type,
            f"Save ₹{amount:,.0f} more per month",
            baseline,
            amount,
            [
                f"Baseline is your average monthly savings over the last {baseline['months_used']} months.",
                "The extra amount is assumed to come from spending, not from new income.",
            ],
            {"extra_monthly_savings": round(amount, 2), "goal_impact": _goal_impact(db, baseline, amount)},
        )

    # cancel_subscriptions
    if not merchants:
        raise ScenarioError("Which subscriptions should be cancelled?")
    recurring = {r["merchant"].lower(): r for r in subscription_service.detect_recurring_payments(db)}
    cancelled, not_found = [], []
    for name in merchants:
        key = name.strip().lower()
        hit = recurring.get(key) or next((r for k, r in recurring.items() if key in k or k in key), None)
        if hit and hit not in cancelled:
            cancelled.append(hit)
        elif not hit:
            not_found.append(name)
    if not cancelled:
        raise ScenarioError(
            f"I couldn't match those to your recurring payments. Yours are: "
            f"{', '.join(r['merchant'] for r in recurring.values())}."
        )

    saved = sum(r["latest_amount"] for r in cancelled)
    return _result(
        scenario_type,
        "Cancel " + ", ".join(r["merchant"].title() for r in cancelled),
        baseline,
        saved,
        [
            "Savings use each subscription's most recent charge amount.",
            "Assumes the subscription is cancelled with no fees and nothing replaces it.",
        ],
        {
            "cancelled": [{"merchant": r["merchant"], "monthly_amount": r["latest_amount"]} for r in cancelled],
            "not_found": not_found,
        },
    )
