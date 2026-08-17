from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import AskRequest, AskResponse
from app.agent import run_agent_loop

router = APIRouter(prefix="/api", tags=["Chat & Agent"])

@router.post("/ask", response_model=AskResponse)
def ask_agent(req: AskRequest, db: Session = Depends(get_db)):
    """
    Main conversational agent endpoint. Receives user questions, executes tool calling against MySQL, 
    and returns answer with full execution traces.
    """
    response = run_agent_loop(
        question=req.question, 
        db=db, 
        session_id=req.session_id
    )
    return response