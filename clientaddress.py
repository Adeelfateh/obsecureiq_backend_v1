from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import uuid
import requests

from database import get_db
from models import Client, ClientAddress, User
from schemas import AddressCreate, AddressUpdate, AddressResponse, BulkAddressUpload
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/addresses", response_model=List[AddressResponse], tags=["Client Addresses"])
def get_client_addresses(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all addresses for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    addresses = db.query(ClientAddress).filter(
        ClientAddress.client_id == client_id
    ).order_by(ClientAddress.created_at.desc()).all()
    
    return addresses

@router.post("/clients/{client_id}/addresses", tags=["Client Addresses"])
def add_client_address(
    client_id: uuid.UUID,
    address_data: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new address"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if address_data.client_provided and address_data.client_provided not in ["Yes", "No"]:
        raise HTTPException(status_code=400, detail="client_provided must be 'Yes' or 'No'")
    
    existing = db.query(ClientAddress).filter(
        ClientAddress.client_id == client_id,
        ClientAddress.address == address_data.address
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="This address already exists for this client")
    
    webhook_url = "https://obscureiq.app.n8n.cloud/webhook/45a0f761-1c53-4017-9248-f523c7aa702e"
    payload = {
        "address": address_data.address,
        "client_provided": address_data.client_provided,
        "client_id": str(client_id)
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=60)
        n8n_result = response.json()

        if n8n_result.get("status") == "Success" or n8n_result.get("success") is True:
            return {
                "status": "success",
                "message": n8n_result.get("message", "Address added successfully")
            }

        raise HTTPException(
            status_code=400,
            detail=n8n_result.get("message", "Failed to insert address")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/clients/{client_id}/addresses/{address_id}", response_model=AddressResponse, tags=["Client Addresses"])
def edit_client_address(
    client_id: uuid.UUID,
    address_id: uuid.UUID,
    address_data: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit an address"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    address_record = db.query(ClientAddress).filter(
        ClientAddress.id == address_id,
        ClientAddress.client_id == client_id
    ).first()
    
    if not address_record:
        raise HTTPException(status_code=404, detail="Address not found")
    
    if address_data.client_provided and address_data.client_provided not in ["Yes", "No"]:
        raise HTTPException(status_code=400, detail="client_provided must be 'Yes' or 'No'")
    
    update_data = address_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(address_record, field, value)
    
    address_record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(address_record)
    
    return address_record

@router.delete("/clients/{client_id}/addresses/{address_id}", tags=["Client Addresses"])
def delete_client_address(
    client_id: uuid.UUID,
    address_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an address"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    address_record = db.query(ClientAddress).filter(
        ClientAddress.id == address_id,
        ClientAddress.client_id == client_id
    ).first()
    
    if not address_record:
        raise HTTPException(status_code=404, detail="Address not found")
    
    db.delete(address_record)
    db.commit()
    
    return {"message": "Address deleted successfully"}

@router.post("/clients/{client_id}/addresses/bulk-upload", tags=["Client Addresses"])
def bulk_upload_addresses(
    client_id: uuid.UUID,
    bulk_data: BulkAddressUpload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send raw addresses directly to n8n webhook and return actual result"""
    
    # Check client access
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # n8n Webhook URL
    webhook_url = "https://obscureiq.app.n8n.cloud/webhook/2e898a83-9646-491d-a0b9-6d85c2b8c437"
    
    payload = {
        "addresses": bulk_data.addresses_text,
        "client_id": str(client_id)
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=60)

        # n8n returns JSON because of responseMode="responseNode"
        n8n_result = response.json()

        # SUCCESS CASE
        if n8n_result.get("status") == "Success" or n8n_result.get("success") is True:
            return {
                "status": "success",
                "message": n8n_result.get("message", "Addresses added successfully")
            }

        # ERROR CASE
        raise HTTPException(
            status_code=400,
            detail=n8n_result.get("message", "Failed to insert addresses")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))