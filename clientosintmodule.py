from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from models import Client, ClientOsintModuleResult, User
from schemas import OsintModuleResultResponse
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/osint-module-results", response_model=List[OsintModuleResultResponse], tags=["OSINT Module Results"])
def get_osint_module_results(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get OSINT module results for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(ClientOsintModuleResult).filter(
        ClientOsintModuleResult.client_id == client_id
    ).order_by(ClientOsintModuleResult.created_at.desc()).all()

@router.delete("/clients/{client_id}/osint-module-results/{result_id}", tags=["OSINT Module Results"])
def delete_osint_module_result(
    client_id: uuid.UUID,
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete OSINT module result"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(ClientOsintModuleResult).filter(
        ClientOsintModuleResult.id == result_id,
        ClientOsintModuleResult.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="OSINT module result not found")

    db.delete(record)
    db.commit()

    return {"message": "OSINT module result deleted successfully"}