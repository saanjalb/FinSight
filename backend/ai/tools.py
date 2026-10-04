"""
Finance Agent tools.

Per the project's architecture (Section 10), the agent doesn't do any
math itself — it decides WHICH of these tools answer a question, and
every tool here just calls into the deterministic services we already
built (analytics_service, subscription_service, budget_service,
savings_service, forecast_service, transaction_service). No new
calculation logic lives in this file; it's purely an adapter layer.

Why closures: Gemini's automatic function calling (google-genai SDK)
inspects a plain Python function's signature and docstring to build
its tool schema, then calls it directly with the arguments it decides
on. Our services all take a `db: Session` as their first argument,
but the LLM should never see or supply that — it's not something a
natural-language question would ever specify. So `build_tools(db)` is
a factory: each inner function closes over one specific `db` session
(the one for the current request) and exposes only the parameters
that are actually the model's to decide.

Important, verified-by-testing detail: this SDK version only sends the
function-level docstring summary to Gemini — NOT the per-argument
"Args:" descriptions (confirmed by inspecting the generated schema
directly, offline, with no API key needed). So every piece of guidance
that matters — what an optional argument defaults to, what units a
number is in — is folded into the main description sentence instead of
an Args section, and every optional parameter uses `Optional[X] = None`
(never a magic sentinel like -1 or "") since `None` produces a clean
`nullable: true` in the schema that the model can reason about without
needing to learn an undocumented convention.
"""
from typing import Optional
from datetime import date as date_cls

from sqlalchemy.orm import Session

from backend.services import (
    analytics_service,
    subscription_service,
    budget_service,
    savings_service,
    forecast_service,
    transaction_service,
)


def _txn_to_dict(t) -> dict:
    return {
        "id": t.id,
        "date": t.date.isoformat(),
        "merchant": t.merchant,
        "amount": t.amount,
        "transaction_type": t.transaction_type,
        "category": t.category,
        "description": t.description,
    }


def build_tools(db: Session) -> list:
    """Returns the list of tool functions bound to this request's DB session."""

    def get_transactions(
        category: Optional[str] = None,
        merchant: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None,
    ) -> list:
        """Look up individual transactions matching filters (all filters are
        optional and combine together; omit any filter you don't need).
        date_from/date_to must be YYYY-MM-DD strings if given. Use this for
        questions about specific transactions or merchants, not for totals
        or summaries — use get_monthly_summary or get_spending_by_category
        for those instead, since they compute totals directly rather than
        requiring you to sum a transaction list yourself.
        """
        results = transaction_service.list_transactions(
            db,
            category=category,
            merchant=merchant,
            date_from=date_cls.fromisoformat(date_from) if date_from else None,
            date_to=date_cls.fromisoformat(date_to) if date_to else None,
            min_amount=min_amount,
            max_amount=max_amount,
            search=search,
        )
        # Cap at 50 so a broad query doesn't flood the model's context.
        return [_txn_to_dict(t) for t in results[:50]]

    def get_monthly_summary(year: Optional[int] = None, month: Optional[int] = None) -> dict:
        """Get total income, total expenses, savings, and savings rate for
        one calendar month (year as four digits, month as 1-12). Omit both
        to default to the current month. Use this for "how much did I
        spend/save this month" style questions.
        """
        if year is None or month is None:
            year, month = analytics_service.latest_data_month(db)
        return analytics_service.get_overview(db, year, month)

    def get_spending_by_category(year: Optional[int] = None, month: Optional[int] = None) -> list:
        """Get total expense amount per category for one calendar month,
        sorted highest first (year as four digits, month as 1-12). Omit
        both to default to the current month. Use this for "where did my
        money go" or "what did I spend on X" style questions.
        """
        if year is None or month is None:
            year, month = analytics_service.latest_data_month(db)
        return analytics_service.get_spending_by_category(db, year, month)

    def compare_periods(year1: int, month1: int, year2: int, month2: int) -> dict:
        """Compare spending between two specific calendar months (each year
        as four digits, each month as 1-12), broken down by category, with
        percentage changes already computed. Use this for "why did my
        spending increase" or "compare X to Y" style questions — always
        call this rather than calling get_spending_by_category twice and
        comparing the numbers yourself.
        """
        return analytics_service.compare_periods(db, year1, month1, year2, month2)

    def get_recurring_payments() -> list:
        """Get all detected recurring/subscription payments (Netflix, rent,
        gym, etc.), including their typical amount, billing cycle in days,
        and whether the amount recently changed. Use this for questions
        about subscriptions or recurring bills.
        """
        return subscription_service.detect_recurring_payments(db)

    def get_budget_status(year: Optional[int] = None, month: Optional[int] = None) -> list:
        """Get every category budget along with how much has actually been
        spent, utilization percentage, and whether it's been exceeded, for
        one calendar month (year as four digits, month as 1-12). Omit both
        to default to the current month. Use this for "am I over budget"
        style questions.
        """
        if year is None or month is None:
            year, month = analytics_service.latest_data_month(db)
        return budget_service.get_budget_status(db, year, month)

    def get_savings_goals() -> list:
        """Get every savings goal with current progress, remaining amount,
        and an estimated number of months left to reach it. Use this for
        questions about savings goals or "how long until I can afford X."
        """
        return savings_service.list_goals_with_progress(db)

    def get_cashflow_forecast() -> dict:
        """Get a statistical forecast of next month's expected income,
        expenses, and savings based on historical trend, plus a concrete
        list of recurring expenses expected in that window. Use this for
        "what will next month look like" style questions. The result is
        always a projection, never actual data — say so explicitly when
        answering with it.
        """
        return forecast_service.get_full_forecast(db)

    return [
        get_transactions,
        get_monthly_summary,
        get_spending_by_category,
        compare_periods,
        get_recurring_payments,
        get_budget_status,
        get_savings_goals,
        get_cashflow_forecast,
    ]
