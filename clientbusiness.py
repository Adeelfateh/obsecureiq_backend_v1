from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import uuid

from database import get_db
from models import Client, ClientBusinessInfo, User
from schemas import BusinessInfoCreate, BusinessInfoUpdate, BusinessInfoResponse
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/business-info", response_model=List[BusinessInfoResponse], tags=["Client Business Information"])
def get_business_info(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all business information for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(ClientBusinessInfo).filter(
        ClientBusinessInfo.client_id == client_id
    ).order_by(ClientBusinessInfo.created_at.desc()).all()

@router.post("/clients/{client_id}/business-info", response_model=BusinessInfoResponse, tags=["Client Business Information"])
def create_business_info(
    client_id: uuid.UUID,
    data: BusinessInfoCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new business information"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not data.business_name.strip() or not data.business_information.strip():
        raise HTTPException(status_code=400, detail="Both fields are required")

    new_record = ClientBusinessInfo(
        client_id=client_id,
        business_name=data.business_name.strip(),
        business_information=data.business_information.strip()
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return new_record

@router.put("/clients/{client_id}/business-info/{info_id}", response_model=BusinessInfoResponse, tags=["Client Business Information"])
def update_business_info(
    client_id: uuid.UUID,
    info_id: uuid.UUID,
    data: BusinessInfoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update business information"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(ClientBusinessInfo).filter(
        ClientBusinessInfo.id == info_id,
        ClientBusinessInfo.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Business info not found")

    updates = data.model_dump(exclude_unset=True)

    if "business_name" in updates and not updates["business_name"].strip():
        raise HTTPException(status_code=400, detail="business_name cannot be empty")
    if "business_information" in updates and not updates["business_information"].strip():
        raise HTTPException(status_code=400, detail="business_information cannot be empty")

    for field, value in updates.items():
        setattr(record, field, value)

    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)

    return record

@router.delete("/clients/{client_id}/business-info/{info_id}", tags=["Client Business Information"])
def delete_business_info(
    client_id: uuid.UUID,
    info_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete business information"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(ClientBusinessInfo).filter(
        ClientBusinessInfo.id == info_id,
        ClientBusinessInfo.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Business info not found")

    db.delete(record)
    db.commit()

    return {"message": "Business information deleted successfully"}