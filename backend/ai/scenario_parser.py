"""
Scenario parser (GenAI, structured output).

The LLM's ONLY job: turn a sentence like "what if I cut food by 20%?"
into a ScenarioParams object. It never computes or sees a result.

Three safeguards, all discussed in the presentation:
  1. Structured output — Gemini must return JSON matching ScenarioParams
     (response_schema), so we never parse free-form text.
  2. Grounding — the prompt lists the user's REAL category and
     subscription names, so "food" maps to "Food & Dining" instead of
     an invented category.
  3. Validation — the parsed object is re-validated by pydantic here and
     again by scenario_service before any calculation runs.
"""
import json
import os
from typing import Literal, Optional

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from backend.services import scenario_service, subscription_service

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class ScenarioParams(BaseModel):
    scenario_type: Literal["reduce_category", "increase_savings", "cancel_subscriptions", "unsupported"]
    category: Optional[str] = None      # for reduce_category, must be one of the user's categories
    percent: Optional[float] = None     # for reduce_category, 0-100
    amount: Optional[float] = None      # for increase_savings, rupees per month
    merchants: Optional[list[str]] = None  # for cancel_subscriptions, names of recurring payments


def _build_prompt(question: str, categories: list[str], subscriptions: list[str]) -> str:
    return f"""Convert the user's what-if question into scenario parameters. Do NOT answer the question or calculate anything.

Scenario types:
- reduce_category: user wants to spend X% less in a category. Set category and percent.
- increase_savings: user wants to save a fixed extra rupee amount per month. Set amount.
- cancel_subscriptions: user wants to cancel recurring payments. Set merchants.
- unsupported: anything else (investing, income changes, unrelated questions).

The user's real spending categories: {', '.join(categories)}
The user's real recurring payments: {', '.join(subscriptions)}

Rules:
- category must be copied exactly from the category list above (e.g. "food" -> "Food & Dining").
- merchants must be copied exactly from the recurring payments list above.
- Leave fields that don't apply as null.

User question: {question}"""


def parse_scenario(db: Session, question: str) -> dict:
    """Returns {"params": ScenarioParams-dict} or {"error": str}."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY is not set. Add it to your .env file (see .env.example)."}

    try:
        baseline = scenario_service.get_baseline(db)
    except scenario_service.ScenarioError as e:
        return {"error": str(e)}

    categories = sorted(baseline["category_avg"].keys())
    subscriptions = [r["merchant"] for r in subscription_service.detect_recurring_payments(db)]

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=_build_prompt(question, categories, subscriptions),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ScenarioParams,
                temperature=0,
            ),
        )
        params = ScenarioParams.model_validate(json.loads(response.text))
        return {"params": params.model_dump()}

    except (ValidationError, json.JSONDecodeError):
        return {"error": "I couldn't understand that as a what-if scenario. Try rephrasing."}
    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            return {"error": "Gemini free-tier rate limit reached. Wait a minute and try again."}
        if "API key" in msg or "401" in msg or "403" in msg:
            return {"error": "Gemini rejected the API key. Check GEMINI_API_KEY in your .env file."}
        return {"error": f"Scenario parsing failed: {msg[:200]}"}
