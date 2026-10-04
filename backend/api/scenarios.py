"""
Scenario API.

  POST /api/scenarios/simulate  structured params -> result. No LLM.
  POST /api/scenarios/ask       sentence -> (LLM parses) -> (backend calculates).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.services import scenario_service
from backend.ai.scenario_parser import parse_scenario

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


class SimulateRequest(BaseModel):
    scenario_type: str
    category: Optional[str] = None
    percent: Optional[float] = None
    amount: Optional[float] = None
    merchants: Optional[list[str]] = None


class AskRequest(BaseModel):
    message: str


@router.post("/simulate")
def simulate(req: SimulateRequest, db: Session = Depends(get_db)):
    try:
        return scenario_service.simulate_scenario(db, **req.model_dump())
    except scenario_service.ScenarioError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ask")
def ask(req: AskRequest, db: Session = Depends(get_db)):
    parsed = parse_scenario(db, req.message)
    if "error" in parsed:
        raise HTTPException(status_code=502, detail=parsed["error"])

    params = parsed["params"]
    if params["scenario_type"] == "unsupported":
        raise HTTPException(
            status_code=400,
            detail="I can simulate: cutting a spending category by a %, saving a fixed extra amount per month, or cancelling subscriptions.",
        )
    try:
        result = scenario_service.simulate_scenario(db, **params)
    except scenario_service.ScenarioError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Echo what the LLM understood so the UI can show it transparently.
    result["understood_as"] = params
    return result
