"""
Chat API — the Natural Language Finance Analyst interface (Section 9).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.ai.agent import ask_finance_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("/")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    result = ask_finance_agent(db, request.message)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result
