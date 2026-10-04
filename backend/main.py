"""
FinSight backend entrypoint.

Run with:  uvicorn backend.main:app --reload
Docs at:   http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()  # reads .env into os.environ — must happen before any module reads GEMINI_API_KEY

from backend.db.database import Base, engine
from backend.models import transaction, budget, savings_goal  # noqa: F401 (imports register models with Base)
from backend.api import transactions, categorization, analytics, budgets, savings_goals, insights, forecast, chat, scenarios, knowledge

# Creates tables if they don't already exist. Fine for SQLite/dev;
# a real production app would use Alembic migrations instead.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FinSight API", version="0.1.0")

# Allow the Vite dev server (default port 5173) to call this API.
app.add_middleware(
    CORSMiddleware,
    # Any local dev port: Vite silently moves to 5174, 5175... if 5173 is busy.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router)
app.include_router(categorization.router)
app.include_router(analytics.router)
app.include_router(budgets.router)
app.include_router(savings_goals.router)
app.include_router(insights.router)
app.include_router(forecast.router)
app.include_router(chat.router)
app.include_router(scenarios.router)
app.include_router(knowledge.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "FinSight API"}
