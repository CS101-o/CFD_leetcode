from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
from app.services.airfoil_agent_free import FreeAirfoilAgent

router = APIRouter()
sessions: Dict[str, FreeAirfoilAgent] = {}

class CommandRequest(BaseModel):
    command: str
    session_id: str = "default"

def get_agent(session_id: str) -> FreeAirfoilAgent:
    if session_id not in sessions:
        sessions[session_id] = FreeAirfoilAgent()
    return sessions[session_id]

@router.post("/command")
async def process_command(request: CommandRequest):
    agent = get_agent(request.session_id)
    result = agent.process_command(request.command)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/current")
async def get_current_airfoil(session_id: str = "default"):
    agent = get_agent(session_id)
    if agent.current_airfoil is None:
        raise HTTPException(status_code=404, detail="No airfoil generated")
    return {"coordinates": agent.current_airfoil.tolist()}

@router.get("/health")
async def health_check():
    return {"status": "healthy", "sessions": len(sessions)}
