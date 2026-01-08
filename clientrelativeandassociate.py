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
    
    # Normalize and check duplicate name (case-insensitive)
    normalized_name = relative_data.name.strip()
    existing = db.query(ClientRelativeAssociate).filter(
        ClientRelativeAssociate.client_id == client_id
    ).all()
    
    for record in existing:
        if record.name.strip().lower() == normalized_name.lower():
            raise HTTPException(status_code=400, detail="This relative/associate name already exists for this client")
    
    # Create new relative/associate
    new_relative = ClientRelativeAssociate(
        client_id=client_id,
        name=normalized_name,
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
    
    # Check duplicate if name is being changed (case-insensitive)
    if relative_data.name:
        normalized_name = relative_data.name.strip()
        
        if normalized_name.lower() != relative_record.name.strip().lower():
            existing = db.query(ClientRelativeAssociate).filter(
                ClientRelativeAssociate.client_id == client_id,
                ClientRelativeAssociate.id != relative_id
            ).all()
            
            for record in existing:
                if record.name.strip().lower() == normalized_name.lower():
                    raise HTTPException(status_code=400, detail="This relative/associate name already exists for this client")
        
        relative_record.name = normalized_name
    
    # Update relationship_type if provided
    if relative_data.relationship_type is not None:
        relative_record.relationship_type = relative_data.relationship_type
    
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
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    relationship_type = bulk_data.relationship_type or "Associate"
    if relationship_type not in ["Relative", "Associate"]:
        raise HTTPException(
            status_code=400,
            detail="relationship_type must be 'Relative' or 'Associate'"
        )

    webhook_url = "https://obscureiq.app.n8n.cloud/webhook/a68f0e08-aa20-470d-b0e5-fbda8968d7e2"

    payload = {
        "relative_name": bulk_data.relatives_text,
        "relationship_type": relationship_type,
        "client_id": str(client_id)
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=60)

        try:
            n8n_result = response.json()
        except ValueError:
            raise HTTPException(
                status_code=500,
                detail="Webhook did not return valid JSON"
            )

        # 🔁 FALLBACK: webhook inactive
        if "detail" in n8n_result and "not registered" in str(n8n_result.get("detail", "")):
            names = [
                n.strip()
                for n in bulk_data.relatives_text.split("\n")
                if n.strip()
            ]

            existing_records = db.query(ClientRelativeAssociate).filter(
                ClientRelativeAssociate.client_id == client_id
            ).all()

            existing_names = {
                r.name.strip().lower() for r in existing_records
            }

            added_any = False

            for name in names:
                if name.lower() in existing_names:
                    continue

                db.add(ClientRelativeAssociate(
                    client_id=client_id,
                    name=name,
                    relationship_type=relationship_type
                ))
                added_any = True

            db.commit()

            if not added_any:
                return {
                    "success": False,
                    "message": "Relatives already exist"
                }

            return {
                "success": True,
                "message": "Relatives added successfully"
            }

        # ✅ NORMAL n8n RESPONSE
        success = n8n_result.get("success")

        if success is True:
            return {
                "success": True,
                "message": n8n_result.get("message", "Relatives added successfully")
            }

        if success is False:
            return {
                "success": False,
                "message": n8n_result.get("message", "Relatives already exist")
            }

        raise HTTPException(
            status_code=500,
            detail="Unexpected webhook response"
        )

    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Webhook connection error: {str(e)}"
        )
