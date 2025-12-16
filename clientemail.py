from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import uuid
import requests

from database import get_db
from models import Client, ClientEmail, User
from schemas import EmailCreate, EmailUpdate, EmailResponse, BulkEmailUpload
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/emails", response_model=List[EmailResponse], tags=["Client Emails"])
def get_client_emails(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all emails for a client"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    emails = db.query(ClientEmail).filter(
        ClientEmail.client_id == client_id
    ).order_by(ClientEmail.created_at.desc()).all()
    
    return emails

@router.post("/clients/{client_id}/emails", response_model=EmailResponse, tags=["Client Emails"])
def add_client_email(
    client_id: uuid.UUID,
    email_data: EmailCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new email"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check duplicate
    existing = db.query(ClientEmail).filter(
        ClientEmail.client_id == client_id,
        ClientEmail.email == email_data.email
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Create new email
    new_email = ClientEmail(
        client_id=client_id,
        email=email_data.email,
        status=email_data.status,
        validation_sources=email_data.validation_sources or [],
        email_tag=email_data.email_tag
    )
    
    db.add(new_email)
    db.commit()
    db.refresh(new_email)
    
    # Send data to webhook after successful insertion
    try:
        webhook_url = "https://obscureiq.app.n8n.cloud/webhook/dd57b579-6035-461b-8eb1-b59123f72546"
        payload = {
            "id": str(new_email.id),
            "client_id": str(new_email.client_id),
            "email": new_email.email,
            "status": new_email.status,
            "validation_sources": new_email.validation_sources,
            "email_tag": new_email.email_tag,
            "created_at": new_email.created_at.isoformat(),
            "updated_at": new_email.updated_at.isoformat()
        }
        requests.post(webhook_url, json=payload, timeout=5)
    except:
        pass  # Ignore webhook errors, don't affect main functionality
    
    return new_email

@router.put("/clients/{client_id}/emails/{email_id}", response_model=EmailResponse, tags=["Client Emails"])
def edit_client_email(
    client_id: uuid.UUID,
    email_id: uuid.UUID,
    email_data: EmailUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit an email - works for both modal and inline editing"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    email_record = db.query(ClientEmail).filter(
        ClientEmail.id == email_id,
        ClientEmail.client_id == client_id
    ).first()
    
    if not email_record:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Check duplicate if email is being changed
    if email_data.email and email_data.email != email_record.email:
        existing = db.query(ClientEmail).filter(
            ClientEmail.client_id == client_id,
            ClientEmail.email == email_data.email,
            ClientEmail.id != email_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    # Update only the fields that are provided
    update_data = email_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(email_record, field, value)
    
    email_record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(email_record)
    
    # Send data to webhook after successful update
    try:
        webhook_url = "https://obscureiq.app.n8n.cloud/webhook/dd57b579-6035-461b-8eb1-b59123f72546"
        payload = {
            "id": str(email_record.id),
            "client_id": str(email_record.client_id),
            "email": email_record.email,
            "status": email_record.status,
            "validation_sources": email_record.validation_sources,
            "email_tag": email_record.email_tag,
            "created_at": email_record.created_at.isoformat(),
            "updated_at": email_record.updated_at.isoformat()
        }
        requests.post(webhook_url, json=payload, timeout=5)
    except:
        pass  # Ignore webhook errors, don't affect main functionality
    
    return email_record

@router.delete("/clients/{client_id}/emails/{email_id}", tags=["Client Emails"])
def delete_client_email(
    client_id: uuid.UUID,
    email_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an email"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    email_record = db.query(ClientEmail).filter(
        ClientEmail.id == email_id,
        ClientEmail.client_id == client_id
    ).first()
    
    if not email_record:
        raise HTTPException(status_code=404, detail="Email not found")
    
    db.delete(email_record)
    db.commit()
    
    return {"message": "Email deleted successfully"}

@router.post("/clients/{client_id}/emails/bulk-upload", tags=["Client Emails"])
def bulk_upload_emails(
    client_id: uuid.UUID,
    bulk_data: BulkEmailUpload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    webhook_url = "https://obscureiq.app.n8n.cloud/webhook/54db872b-e2e7-4b81-9d94-01ca7e62428c"

    payload = {
        "emails": bulk_data.emails_text,
        "client_id": str(client_id),
        "status": bulk_data.status
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=30)

        try:
            n8n_result = response.json()
        except ValueError:
            raise HTTPException(
                status_code=500,
                detail="Webhook did not return valid JSON"
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=n8n_result.get("message", "Webhook failed")
            )

        success = n8n_result.get("success")
        print(success)

        if success is True:
            return {
                "status": "success",
                "message": n8n_result.get(
                    "message",
                    "Emails inserted successfully"
                ),
                "count": n8n_result.get("count", 0)
            }

        if success is False:
            return {
                "status": "info",
                "message": n8n_result.get(
                    "message",
                    "Email already exists"
                ),
                "count": 0
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
