"""Knowledge assistant API — RAG over finance-education notes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.ai.rag import answer_question

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class AskRequest(BaseModel):
    question: str


@router.post("/ask")
def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Please enter a question.")
    result = answer_question(req.question.strip())
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result
