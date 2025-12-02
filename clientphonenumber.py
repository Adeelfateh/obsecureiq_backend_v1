from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import uuid
import requests

from database import get_db
from models import Client, ClientPhoneNumber, User
from schemas import PhoneNumberCreate, PhoneNumberUpdate, PhoneNumberResponse, BulkPhoneUpload
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/phone-numbers", response_model=List[PhoneNumberResponse], tags=["Client Phone Numbers"])
def get_client_phone_numbers(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all phone numbers for a client"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    phone_numbers = db.query(ClientPhoneNumber).filter(
        ClientPhoneNumber.client_id == client_id
    ).order_by(ClientPhoneNumber.created_at.desc()).all()
    
    return phone_numbers

@router.post("/clients/{client_id}/phone-numbers", response_model=PhoneNumberResponse, tags=["Client Phone Numbers"])
def add_client_phone_number(
    client_id: uuid.UUID,
    phone_data: PhoneNumberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new phone number"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate client_provided value (only if provided and not empty)
    if phone_data.client_provided is not None and phone_data.client_provided.strip() and phone_data.client_provided not in ["Yes", "No"]:
        raise HTTPException(
            status_code=400, 
            detail="client_provided must be 'Yes' or 'No'"
        )
    
    # Check duplicate
    existing = db.query(ClientPhoneNumber).filter(
        ClientPhoneNumber.client_id == client_id,
        ClientPhoneNumber.phone_number == phone_data.phone_number
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already exists")
    
    # Create new phone number
    new_phone = ClientPhoneNumber(
        client_id=client_id,
        phone_number=phone_data.phone_number,
        client_provided=phone_data.client_provided
    )
    
    db.add(new_phone)
    db.commit()
    db.refresh(new_phone)
    
    return new_phone

@router.put("/clients/{client_id}/phone-numbers/{phone_id}", response_model=PhoneNumberResponse, tags=["Client Phone Numbers"])
def edit_client_phone_number(
    client_id: uuid.UUID,
    phone_id: uuid.UUID,
    phone_data: PhoneNumberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit a phone number - works for both modal and inline editing"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    phone_record = db.query(ClientPhoneNumber).filter(
        ClientPhoneNumber.id == phone_id,
        ClientPhoneNumber.client_id == client_id
    ).first()
    
    if not phone_record:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    # Validate client_provided if being updated
    if phone_data.client_provided is not None and phone_data.client_provided.strip() and phone_data.client_provided not in ["Yes", "No"]:
        raise HTTPException(
            status_code=400, 
            detail="client_provided must be 'Yes' or 'No'"
        )
    
    # Check duplicate if phone number is being changed
    if phone_data.phone_number and phone_data.phone_number != phone_record.phone_number:
        existing = db.query(ClientPhoneNumber).filter(
            ClientPhoneNumber.client_id == client_id,
            ClientPhoneNumber.phone_number == phone_data.phone_number,
            ClientPhoneNumber.id != phone_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Phone number already exists")
    
    # Update only the fields that are provided
    update_data = phone_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(phone_record, field, value)
    
    phone_record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(phone_record)
    
    return phone_record

@router.delete("/clients/{client_id}/phone-numbers/{phone_id}", tags=["Client Phone Numbers"])
def delete_client_phone_number(
    client_id: uuid.UUID,
    phone_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a phone number"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    phone_record = db.query(ClientPhoneNumber).filter(
        ClientPhoneNumber.id == phone_id,
        ClientPhoneNumber.client_id == client_id
    ).first()
    
    if not phone_record:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    db.delete(phone_record)
    db.commit()
    
    return {"message": "Phone number deleted successfully"}

@router.post("/clients/{client_id}/phone-numbers/bulk-upload", tags=["Client Phone Numbers"])
def bulk_upload_phone_numbers(
    client_id: uuid.UUID,
    bulk_data: BulkPhoneUpload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send raw phone numbers directly to webhook and return real n8n result"""
    
    # Check client access
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    webhook_url = "https://obscureiq.app.n8n.cloud/webhook/92457ed2-aad5-4981-b88c-cd65f11b3a8b"
    
    payload = {
        "phone_number": bulk_data.phone_numbers_text,
        "client_id": str(client_id)
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=60)

        # response from n8n (JSON only because responseMode="responseNode")
        n8n_result = response.json()

        if n8n_result.get("success") is True:
            return {
                "status": "success",
                "message": n8n_result.get("message", "Phone numbers added successfully")
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=n8n_result.get("message", "Failed to insert phone numbers")
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))