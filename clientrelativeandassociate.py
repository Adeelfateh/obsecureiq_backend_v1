from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import uuid
import requests

from database import get_db
from models import Client, ClientRelativeAssociate, User
from schemas import RelativeAssociateCreate, RelativeAssociateUpdate, RelativeAssociateResponse, BulkRelativeUpload
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/relatives", response_model=List[RelativeAssociateResponse], tags=["Client Relatives & Associates"])
def get_client_relatives(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all relatives and associates for a client"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    relatives = db.query(ClientRelativeAssociate).filter(
        ClientRelativeAssociate.client_id == client_id
    ).order_by(ClientRelativeAssociate.created_at.desc()).all()
    
    return relatives

@router.post("/clients/{client_id}/relatives", response_model=RelativeAssociateResponse, tags=["Client Relatives & Associates"])
def add_client_relative(
    client_id: uuid.UUID,
    relative_data: RelativeAssociateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new relative or associate"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate relationship_type (only if provided)
    if relative_data.relationship_type and relative_data.relationship_type not in ["Relative", "Associate"]:
        raise HTTPException(
            status_code=400, 
            detail="relationship_type must be 'Relative' or 'Associate'"
        )
    
    # Check duplicate name
    existing = db.query(ClientRelativeAssociate).filter(
        ClientRelativeAssociate.client_id == client_id,
        ClientRelativeAssociate.name == relative_data.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Name already exists")
    
    # Create new relative/associate
    new_relative = ClientRelativeAssociate(
        client_id=client_id,
        name=relative_data.name,
        relationship_type=relative_data.relationship_type
    )
    
    db.add(new_relative)
    db.commit()
    db.refresh(new_relative)
    
    return new_relative

@router.put("/clients/{client_id}/relatives/{relative_id}", response_model=RelativeAssociateResponse, tags=["Client Relatives & Associates"])
def edit_client_relative(
    client_id: uuid.UUID,
    relative_id: uuid.UUID,
    relative_data: RelativeAssociateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit a relative or associate - works for both modal and inline editing"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    relative_record = db.query(ClientRelativeAssociate).filter(
        ClientRelativeAssociate.id == relative_id,
        ClientRelativeAssociate.client_id == client_id
    ).first()
    
    if not relative_record:
        raise HTTPException(status_code=404, detail="Relative/Associate not found")
    
    # Validate relationship_type if being updated
    if relative_data.relationship_type and relative_data.relationship_type not in ["Relative", "Associate"]:
        raise HTTPException(
            status_code=400, 
            detail="relationship_type must be 'Relative' or 'Associate'"
        )
    
    # Check duplicate if name is being changed
    if relative_data.name and relative_data.name != relative_record.name:
        existing = db.query(ClientRelativeAssociate).filter(
            ClientRelativeAssociate.client_id == client_id,
            ClientRelativeAssociate.name == relative_data.name,
            ClientRelativeAssociate.id != relative_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Name already exists")
    
    # Update only the fields that are provided
    update_data = relative_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(relative_record, field, value)
    
    relative_record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(relative_record)
    
    return relative_record

@router.delete("/clients/{client_id}/relatives/{relative_id}", tags=["Client Relatives & Associates"])
def delete_client_relative(
    client_id: uuid.UUID,
    relative_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a relative or associate"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    relative_record = db.query(ClientRelativeAssociate).filter(
        ClientRelativeAssociate.id == relative_id,
        ClientRelativeAssociate.client_id == client_id
    ).first()
    
    if not relative_record:
        raise HTTPException(status_code=404, detail="Relative/Associate not found")
    
    db.delete(relative_record)
    db.commit()
    
    return {"message": "Relative/Associate deleted successfully"}

@router.post("/clients/{client_id}/relatives/bulk-upload", tags=["Client Relatives & Associates"])
def bulk_upload_relatives(
    client_id: uuid.UUID,
    bulk_data: BulkRelativeUpload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send raw relatives/associates text directly to n8n webhook and return actual result"""
    
    # Validate client
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # n8n Webhook URL
    webhook_url = "https://obscureiq.app.n8n.cloud/webhook/a68f0e08-aa20-470d-b0e5-fbda8968d7e2"
    
    payload = {
        "relative_name": bulk_data.relatives_text,  # Raw uploaded block
        "client_id": str(client_id)
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=60)

        # n8n always returns JSON because of responseMode="responseNode"
        n8n_result = response.json()

        # n8n SUCCESS
        if n8n_result.get("status") == "Success" or n8n_result.get("success") is True:
            return {
                "status": "success",
                "message": n8n_result.get("message", "Relative added successfully")
            }

        # n8n ERROR
        raise HTTPException(
            status_code=400,
            detail=n8n_result.get("message", "Failed to insert relatives")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))