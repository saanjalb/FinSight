"""
FinSight pre-presentation check.   Run from the finsight/ folder:

    python demo_check.py            # all checks (AI checks run if GEMINI_API_KEY is set)
    python demo_check.py --no-ai    # backend-only, no Gemini calls

Runs every demo flow against a THROWAWAY database (your real data and
trained model are never touched) and prints PASS / FAIL / WARN.
  FAIL = something is broken.  WARN = LLM-dependent or environment issue
  (e.g. free-tier rate limit) - worth re-running, not necessarily a bug.
Exit code is non-zero if anything FAILED.
"""
import os
import re
import sys
import tempfile
from collections import defaultdict

TMP = tempfile.mkdtemp(prefix="finsight_check_")
os.environ["DATABASE_URL"] = f"sqlite:///{TMP}/check.db"   # must be set before importing the app

from fastapi.testclient import TestClient  # noqa: E402

import backend.ml.categorization as categorization  # noqa: E402
categorization.MODEL_PATH = os.path.join(TMP, "model.joblib")  # keep the real trained model untouched

from backend.main import app  # noqa: E402  (also loads .env)

RUN_AI = "--no-ai" not in sys.argv and bool(os.getenv("GEMINI_API_KEY"))
results = {"PASS": 0, "FAIL": 0, "WARN": 0}


def check(name: str, ok: bool, detail: str = "", soft: bool = False):
    status = "PASS" if ok else ("WARN" if soft else "FAIL")
    results[status] += 1
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail and not ok else ""))


def section(title: str):
    print(f"\n{title}")


c = TestClient(app)
DATA = os.path.join(os.path.dirname(__file__), "backend", "data")

# ------------------------------------------------------------------ Demo 1 + 3
section("Demo 1 & 3 — Import + automatic categorization")
r = c.post("/api/transactions/import", files={"file": ("s.csv", open(f"{DATA}/sample_uncategorized.csv", "rb"))}).json()
check("CSV imports all rows", r.get("imported") == 305 and r.get("failed") == 0, str(r))
cat = r.get("categorization", {})
check("Rules categorize most blank rows", cat.get("resolved_by_rule", 0) > 100, str(cat))
tx = c.get("/api/transactions/").json()
by_merchant = {t["merchant"]: t["category"] for t in tx}
check("ML stage categorizes an unseen merchant (ZEPTO -> Food & Dining)", by_merchant.get("ZEPTO") == "Food & Dining", str(by_merchant.get("ZEPTO")))
check("Unknown merchant is left uncategorized, not guessed", by_merchant.get("MYSTERY MERCHANT CO") is None)
r2 = c.post("/api/transactions/import", files={"file": ("s.csv", open(f"{DATA}/sample_uncategorized.csv", "rb"))}).json()
check("Re-importing the same file adds nothing", r2.get("imported") == 0 and r2.get("skipped_duplicates") == 305, str(r2))

# ------------------------------------------------------------------ Demo 2
section("Demo 2 — Analytics")
latest = max(t["date"] for t in tx)
ly, lm = int(latest[:4]), int(latest[5:7])
ov = c.get("/api/analytics/overview").json()
check('"This month" defaults to the latest month with data', (ov["year"], ov["month"]) == (ly, lm), str(ov))
check("Overview income/expenses are consistent", abs(ov["savings"] - (ov["income"] - ov["expenses"])) < 0.01)
check("Category breakdown returns data", len(c.get("/api/analytics/by-category").json()) >= 5)
check("Monthly trend has 6 months", len(c.get("/api/analytics/monthly-trend").json()) == 6)

# ------------------------------------------------------------------ Demo 4
section("Demo 4 — Subscriptions and spending leaks")
subs = {s["merchant"]: s for s in c.get("/api/insights/subscriptions").json()}
check("Recurring payments detected (Netflix, Spotify, Rent)", {"NETFLIX", "SPOTIFY", "RENT PAYMENT"} <= set(subs), str(list(subs)))
check("Rent increase flagged as an amount change", subs.get("RENT PAYMENT", {}).get("amount_changed") is True)
leaks = c.get("/api/insights/spending-leaks").json()
check("Food & Dining spike detected", any(l["category"] == "Food & Dining" for l in leaks["category_increases"]), str(leaks["category_increases"])[:100])

# ------------------------------------------------------------------ Forecast / budgets / goals
section("Forecast, budgets, goals")
fc = c.get("/api/forecast/next-month").json()
nxt = (ly, lm + 1) if lm < 12 else (ly + 1, 1)
check("Forecast is flagged as a forecast for the month after the data", fc.get("is_forecast") is True and (fc["forecast_year"], fc["forecast_month"]) == nxt, str(fc)[:120])
c.post("/api/budgets/", json={"category": "Food & Dining", "monthly_limit": 8000})
bs = c.get("/api/budgets/status").json()
check("Food budget shows as exceeded in the spike month", bs and bs[0]["over_budget"] is True, str(bs))
c.post("/api/savings-goals/", json={"name": "Laptop", "target_amount": 80000, "saved_amount": 35000, "monthly_contribution": 5000})
g = c.get("/api/savings-goals/").json()
check("Savings goal progress is 43.75%", g and g[0]["progress_percent"] == 43.75, str(g))

# ------------------------------------------------------------------ Demo 6
section("Demo 6 — What-if simulator (backend math, independent cross-check)")
months = sorted({t["date"][:7] for t in tx})[-3:]


def avg_month(pred):
    return sum(t["amount"] for t in tx if t["date"][:7] in months and pred(t)) / 3


food_avg = avg_month(lambda t: t["transaction_type"] == "expense" and t["category"] == "Food & Dining")
expected_saving = round(food_avg * 0.20, 2)
sim = c.post("/api/scenarios/simulate", json={"scenario_type": "reduce_category", "category": "Food & Dining", "percent": 20}).json()
check("Reduce food 20%: matches independent calculation", abs(sim["monthly_difference"] - expected_saving) < 0.02, f"{sim['monthly_difference']} vs {expected_saving}")
check("Scenario is labelled as a scenario", sim.get("is_scenario") is True)
sub = c.post("/api/scenarios/simulate", json={"scenario_type": "cancel_subscriptions", "merchants": ["Netflix", "Spotify"]}).json()
check("Cancel Netflix + Spotify = ₹768/month", sub["monthly_difference"] == 768.0, str(sub["monthly_difference"]))
sv = c.post("/api/scenarios/simulate", json={"scenario_type": "increase_savings", "amount": 5000}).json()
check("Save ₹5,000 more: savings rise by exactly 5,000", abs(sv["scenario"]["avg_monthly_savings"] - sv["baseline"]["avg_monthly_savings"] - 5000) < 0.02)
bad = c.post("/api/scenarios/simulate", json={"scenario_type": "reduce_category", "category": "Pets", "percent": 20})
check("Unknown category is rejected with a clear message", bad.status_code == 400 and "Pets" in bad.json()["detail"])

# ------------------------------------------------------------------ AI
section("Demos 5, 6 & 7 — AI features (Gemini)")
if not RUN_AI:
    print("  [SKIP] GEMINI_API_KEY not set (or --no-ai). Set it in .env to run the AI checks.")
else:
    def call(path, body):
        r = c.post(path, json=body)
        if r.status_code == 502 and "rate limit" in r.text.lower():
            check(f"{path} (Gemini free-tier rate limit hit - wait a minute and re-run)", False, soft=True)
            return None
        return r

    prev_y, prev_m = (ly, lm - 1) if lm > 1 else (ly - 1, 12)
    prev_key = f"{prev_y}-{prev_m:02d}"
    prev_food = sum(t["amount"] for t in tx if t["date"][:7] == prev_key and t["transaction_type"] == "expense" and t["category"] == "Food & Dining")

    r = call("/api/chat/", {"message": "How much did I spend on food last month?"})
    if r is not None:
        check("Agent responds", r.status_code == 200, r.text[:150])
        if r.status_code == 200:
            j = r.json()
            check("Agent used data tools (not guessing)", len(j["tools_used"]) > 0, str(j))
            variants = {f"{int(prev_food):,}", str(int(prev_food)), f"{round(prev_food):,}", str(round(prev_food))}
            check(f"Answer contains the real figure (~₹{prev_food:,.0f})", any(v in j["answer"] for v in variants), j["answer"][:160], soft=True)

    r = call("/api/scenarios/ask", {"message": "What if I reduce food spending by 20%?"})
    if r is not None:
        check("Scenario question is understood", r.status_code == 200, r.text[:150])
        if r.status_code == 200:
            j = r.json()
            check("AI-parsed scenario gives the same number as the direct calculation", abs(j["monthly_difference"] - expected_saving) < 0.02, f"{j['monthly_difference']} vs {expected_saving}")

    r = call("/api/knowledge/ask", {"question": "What is compound interest?"})
    if r is not None:
        check("Knowledge question answered", r.status_code == 200, r.text[:150])
        if r.status_code == 200:
            j = r.json()
            check("Answer is grounded and shows sources", j["grounded"] and len(j["sources"]) >= 1, str(j)[:150])
            check("Top source is the Compound Interest note", any(s["title"] == "Compound Interest" for s in j["sources"]), str(j["sources"])[:150], soft=True)

    r = call("/api/knowledge/ask", {"question": "Who won the cricket world cup?"})
    if r is not None and r.status_code == 200:
        check("Off-topic question is declined instead of answered", r.json()["grounded"] is False, r.text[:150], soft=True)

# ------------------------------------------------------------------ summary
print(f"\nResult: {results['PASS']} passed, {results['FAIL']} failed, {results['WARN']} warnings")
sys.exit(1 if results["FAIL"] else 0)
