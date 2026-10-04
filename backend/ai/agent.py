"""
Finance Agent.

This is the GenAI orchestration layer: it hands Gemini a natural-
language question plus the tool functions from tools.py, and lets the
model's automatic function calling decide which tools to call (and in
what order/combination) to answer it. We never parse the question
ourselves or guess which tool applies — that decision-making is
exactly what "agentic" means here, per the project's Section 10.

Uses Gemini because it has a genuinely free API tier (no expiring
trial credit), which matters for a project meant to be run and
re-run without worrying about billing. See ai/tools.py for what the
model can actually call, and note that every one of those tools is
deterministic application logic underneath — the LLM only orchestrates
and explains, it never computes a financial number itself.
"""
import os
from sqlalchemy.orm import Session

from backend.ai.tools import build_tools
from backend.services import analytics_service

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION = """You are FinSight's Finance Analyst assistant, built into a personal finance app.

Rules you must follow:
- Never guess or estimate a financial number yourself. Always call a tool to get exact figures — every number in your answer must come from a tool result.
- If a question requires combining multiple pieces of information (e.g. "why did my spending increase"), call every tool you need before answering — don't answer after only a partial picture.
- Clearly say when something is a forecast/projection rather than actual historical data (the forecast tool result includes an explicit flag for this).
- Be concise and conversational, like a knowledgeable friend, not a financial disclaimer generator. A few sentences is usually enough.
- Use ₹ (Indian Rupees) when stating amounts, since that's the currency this data is in.
- If a tool returns empty results (e.g. no transactions matched), say so plainly rather than inventing an answer.
- You are not a licensed financial advisor — for questions asking for investment advice or recommendations beyond this app's own data, say that's outside what you can help with here.
"""


MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]


def _date_context(db: Session) -> str:
    """
    The model has no idea what 'today' is, so 'last month' would be a
    guess (possibly a year from its training data). We anchor it to the
    latest month that actually has data, computed fresh from the DB.
    """
    y, m = analytics_service.latest_data_month(db)
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
    return (
        f"\nDate context: the most recent month with data is {MONTH_NAMES[m]} {y}. "
        f"Treat 'this month' as {MONTH_NAMES[m]} {y} (year={y}, month={m}) and "
        f"'last month' / 'previous month' as {MONTH_NAMES[pm]} {py} (year={py}, month={pm}). "
        f"Always pass explicit year and month numbers to tools when the user names or implies a month."
    )


def _tools_used(response) -> list[str]:
    """Names of the tools Gemini actually called, in order. Shown in the UI
    so it's visible that answers come from tool results, not from guessing."""
    used = []
    for content in (response.automatic_function_calling_history or []):
        for part in (content.parts or []):
            if part.function_call:
                used.append(part.function_call.name)
    return used


def ask_finance_agent(db: Session, question: str) -> dict:
    """
    Sends the user's question to Gemini with the finance tools attached.
    Returns {"answer": str, "tools_used": [str]} on success, or
    {"error": str} if the key is missing or the call fails. Callers show
    the error instead of crashing, since this feature depends on config
    the user sets up themselves (see .env.example).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "error": "GEMINI_API_KEY is not set. Add it to your .env file to enable the Finance Agent (see .env.example)."
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=question,
            config=types.GenerateContentConfig(
                tools=build_tools(db),
                system_instruction=SYSTEM_INSTRUCTION + _date_context(db),
            ),
        )
        return {"answer": response.text or "I couldn't produce an answer for that.", "tools_used": _tools_used(response)}

    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            return {"error": "Gemini free-tier rate limit reached. Wait a minute and try again."}
        if "API key" in msg or "401" in msg or "403" in msg:
            return {"error": "Gemini rejected the API key. Check GEMINI_API_KEY in your .env file."}
        return {"error": f"Finance Agent request failed: {msg[:200]}"}
