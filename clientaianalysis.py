from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from models import Client, ClientAIAnalysis, User
from schemas import AIAnalysisResponse
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/ai-analysis", response_model=List[AIAnalysisResponse], tags=["AI Analysis"])
def get_ai_analysis(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI analysis for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(ClientAIAnalysis).filter(
        ClientAIAnalysis.client_id == client_id
    ).order_by(ClientAIAnalysis.created_at.desc()).all()

@router.delete("/clients/{client_id}/ai-analysis/{analysis_id}", tags=["AI Analysis"])
def delete_ai_analysis(
    client_id: uuid.UUID,
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete AI analysis record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(ClientAIAnalysis).filter(
        ClientAIAnalysis.id == analysis_id,
        ClientAIAnalysis.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="AI analysis record not found")

    db.delete(record)
    db.commit()

    return {"message": "AI analysis record deleted successfully"}