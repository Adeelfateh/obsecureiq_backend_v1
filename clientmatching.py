from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from models import Client, ClientMatchingResult, User
from schemas import ClientMatchingResultResponse
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/matching-results", response_model=List[ClientMatchingResultResponse], tags=["Client Matching Results"])
def get_client_matching_results(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all matching results for a client"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    matching_results = db.query(ClientMatchingResult).filter(
        ClientMatchingResult.client_id == client_id
    ).order_by(ClientMatchingResult.created_at.desc()).all()
    
    return matching_results


@router.delete("/clients/{client_id}/matching-results/{result_id}", tags=["Client Matching Results"])
def delete_client_matching_result(
    client_id: uuid.UUID,
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a matching result"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    matching_result = db.query(ClientMatchingResult).filter(
        ClientMatchingResult.id == result_id,
        ClientMatchingResult.client_id == client_id
    ).first()
    
    if not matching_result:
        raise HTTPException(status_code=404, detail="Matching result not found")
    
    db.delete(matching_result)
    db.commit()
    
    return {"message": "Matching result deleted successfully"}
