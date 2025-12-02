from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from models import Client, ClientSerpAnalysis, User
from schemas import SerpAnalysisResponse
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/serp-analysis", response_model=List[SerpAnalysisResponse], tags=["SERP Analysis"])
def get_serp_analysis(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get SERP analysis for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(ClientSerpAnalysis).filter(
        ClientSerpAnalysis.client_id == client_id
    ).order_by(ClientSerpAnalysis.created_at.desc()).all()

@router.delete("/clients/{client_id}/serp-analysis/{analysis_id}", tags=["SERP Analysis"])
def delete_serp_analysis(
    client_id: uuid.UUID,
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete SERP analysis record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(ClientSerpAnalysis).filter(
        ClientSerpAnalysis.id == analysis_id,
        ClientSerpAnalysis.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="SERP analysis record not found")

    db.delete(record)
    db.commit()

    return {"message": "SERP analysis record deleted successfully"}