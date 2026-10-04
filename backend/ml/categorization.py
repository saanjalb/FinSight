"""
Transaction categorization engine.

Hybrid pipeline, in order:
  1. Rule-based keyword matching — fast, free, deterministic. Covers
     the overwhelming majority of real transactions since most people's
     merchants repeat (same Netflix, same landlord, same grocery store).
  2. ML classifier (TF-IDF + Logistic Regression) — trained on this
     user's own already-categorized transactions. Catches merchant name
     variants the rules don't know about (e.g. "UBER EATS" when only
     "UBER" is a known rule), by matching on text similarity rather
     than exact keywords.
  3. LLM fallback — NOT wired yet. This is the deliberate plug-in point
     for genuinely ambiguous merchants where neither rules nor the ML
     model are confident. It's built once we set up the GenAI client in
     a later phase — see ai/categorization_llm.py (not yet created).

Why this order matters for the presentation: it demonstrates knowing
when NOT to reach for the most powerful (and most expensive/slowest)
tool. An LLM call for "NETFLIX" would be wasteful; it's reserved for
the cases that actually need judgment.
"""
import os
import re
from typing import Optional
import joblib
from sqlalchemy.orm import Session

from backend.models.transaction import Transaction

# Resolved relative to this file, not the process's working directory —
# so it works whether the app is launched from the project root or
# from inside backend/, and so tests importing this module directly
# don't silently fail to find the model.
MODEL_PATH = os.path.join(os.path.dirname(__file__), "category_model.joblib")

# Keyword -> category. Matched case-insensitively as a substring against
# the merchant name. Order doesn't matter; first match wins.
RULE_MAP = {
    "SALARY": "Income",
    "RENT": "Housing",
    "ELECTRICITY": "Utilities",
    "INTERNET": "Utilities",
    "NETFLIX": "Subscriptions",
    "SPOTIFY": "Subscriptions",
    "CLOUD STORAGE": "Subscriptions",
    "GYM": "Subscriptions",
    "SWIGGY": "Food & Dining",
    "ZOMATO": "Food & Dining",
    "DOMINOS": "Food & Dining",
    "CAFE": "Food & Dining",
    "UBER": "Transport",
    "OLA": "Transport",
    "METRO": "Transport",
    "AMAZON": "Shopping",
    "MYNTRA": "Shopping",
    "FLIPKART": "Shopping",
    "BOOKMYSHOW": "Entertainment",
    "PVR": "Entertainment",
    "PHARMACY": "Healthcare",
    "APOLLO": "Healthcare",
}

# ML confidence below this is treated as "not confident enough" —
# falls through to the LLM fallback stage instead of guessing.
ML_CONFIDENCE_THRESHOLD = 0.55


def rule_based_categorize(merchant: str) -> Optional[str]:
    """Exact keyword substring match. Returns None if nothing matches."""
    merchant_upper = merchant.upper()
    for keyword, category in RULE_MAP.items():
        if keyword in merchant_upper:
            return category
    return None


def train_ml_categorizer(db: Session) -> dict:
    """
    Train a TF-IDF + Logistic Regression classifier on this user's
    already-categorized transactions (merchant name -> category).

    Uses character n-grams rather than word tokens, since merchant names
    are short and often not real words ("SWIGGY", "ZOMATO") — character
    n-grams let the model generalize to variants like "SWIGGY INSTAMART"
    even though it never saw that exact string during training.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    labeled = (
        db.query(Transaction)
        .filter(Transaction.category.isnot(None))
        .all()
    )
    if len(labeled) < 10:
        return {"trained": False, "reason": "Not enough labeled transactions (need at least 10)"}

    merchants = [t.merchant for t in labeled]
    categories = [t.category for t in labeled]

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    pipeline.fit(merchants, categories)
    joblib.dump(pipeline, MODEL_PATH)

    return {"trained": True, "training_examples": len(labeled), "categories": sorted(set(categories))}


def ml_categorize(merchant: str) -> Optional[tuple[str, float]]:
    """Returns (category, confidence) if the model is confident enough, else None."""
    try:
        pipeline = joblib.load(MODEL_PATH)
    except FileNotFoundError:
        return None

    probs = pipeline.predict_proba([merchant])[0]
    best_idx = probs.argmax()
    confidence = probs[best_idx]
    category = pipeline.classes_[best_idx]

    if confidence >= ML_CONFIDENCE_THRESHOLD:
        return str(category), float(confidence)
    return None


def categorize_transaction(merchant: str) -> dict:
    """
    Run the full pipeline for one merchant name. Returns which stage
    produced the answer — useful for the presentation demo and for
    debugging why something got categorized the way it did.
    """
    rule_result = rule_based_categorize(merchant)
    if rule_result:
        return {"category": rule_result, "source": "rule", "confidence": 1.0}

    ml_result = ml_categorize(merchant)
    if ml_result:
        category, confidence = ml_result
        return {"category": category, "source": "ml", "confidence": confidence}

    # LLM fallback goes here once wired (later phase) — for now, uncategorized.
    return {"category": None, "source": "none", "confidence": 0.0}
