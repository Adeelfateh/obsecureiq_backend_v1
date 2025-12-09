from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import uuid

from database import get_db
from models import Client, ClientUsername, User
from schemas import UsernameCreate, UsernameUpdate, UsernameResponse, BulkUsernameUpload
from users import get_current_user
import requests

router = APIRouter()

@router.get("/clients/{client_id}/usernames", response_model=List[UsernameResponse], tags=["Client Usernames"])
def get_client_usernames(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all usernames for a client"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    usernames = db.query(ClientUsername).filter(
        ClientUsername.client_id == client_id
    ).order_by(ClientUsername.created_at.desc()).all()
    
    return usernames

@router.post("/clients/{client_id}/usernames", response_model=UsernameResponse, tags=["Client Usernames"])
def add_client_username(
    client_id: uuid.UUID,
    username_data: UsernameCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new username"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check duplicate
    existing = db.query(ClientUsername).filter(
        ClientUsername.client_id == client_id,
        ClientUsername.username == username_data.username
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists for this client")
    
    # Create new username
    new_username = ClientUsername(
        client_id=client_id,
        username=username_data.username
    )
    
    db.add(new_username)
    db.commit()
    db.refresh(new_username)
    
    return new_username

@router.put("/clients/{client_id}/usernames/{username_id}", response_model=UsernameResponse, tags=["Client Usernames"])
def edit_client_username(
    client_id: uuid.UUID,
    username_id: uuid.UUID,
    username_data: UsernameUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit a username - works for both modal and inline editing"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    username_record = db.query(ClientUsername).filter(
        ClientUsername.id == username_id,
        ClientUsername.client_id == client_id
    ).first()
    
    if not username_record:
        raise HTTPException(status_code=404, detail="Username not found")
    
    # Check duplicate if username is being changed
    if username_data.username and username_data.username != username_record.username:
        existing = db.query(ClientUsername).filter(
            ClientUsername.client_id == client_id,
            ClientUsername.username == username_data.username,
            ClientUsername.id != username_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists for this client")
    
    # Update only the fields that are provided
    update_data = username_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(username_record, field, value)
    
    username_record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(username_record)
    
    return username_record

@router.delete("/clients/{client_id}/usernames/{username_id}", tags=["Client Usernames"])
def delete_client_username(
    client_id: uuid.UUID,
    username_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a username"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    username_record = db.query(ClientUsername).filter(
        ClientUsername.id == username_id,
        ClientUsername.client_id == client_id
    ).first()
    
    if not username_record:
        raise HTTPException(status_code=404, detail="Username not found")
    
    db.delete(username_record)
    db.commit()
    
    return {"message": "Username deleted successfully"}

@router.post("/clients/{client_id}/usernames/bulk-upload", tags=["Client Usernames"])
def bulk_upload_usernames(
    client_id: uuid.UUID,
    bulk_data: BulkUsernameUpload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send raw usernames directly to n8n webhook and return result"""
    
    # Check client access
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # NOTE: If webhook is not active, will fallback to direct database insert
    webhook_url = "https://obscureiq.app.n8n.cloud/webhook/aa83c014-36f6-4206-acb2-10507cbe5eb0"
    
    payload = {
        "usernames": bulk_data.usernames_text,
        "client_id": str(client_id)
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=60)
        
        # Check if response is JSON
        try:
            n8n_result = response.json()
        except:
            raise HTTPException(
                status_code=500,
                detail=f"Webhook returned non-JSON response: {response.text[:200]}"
            )
        
        # Check for n8n webhook registration error - if webhook not active, insert directly
        if "detail" in n8n_result and "not registered" in str(n8n_result.get("detail", "")):
            # Fallback: Insert directly without webhook
            usernames_list = bulk_data.usernames_text.strip().split('\n')
            added_count = 0
            
            for username_line in usernames_list:
                username = username_line.strip()
                if username:
                    # Check duplicate
                    existing = db.query(ClientUsername).filter(
                        ClientUsername.client_id == client_id,
                        ClientUsername.username == username
                    ).first()
                    
                    if not existing:
                        new_username = ClientUsername(
                            client_id=client_id,
                            username=username
                        )
                        db.add(new_username)
                        added_count += 1
            
            db.commit()
            return {
                "status": "success",
                "message": f"{added_count} username(s) added successfully (webhook inactive, used direct insert)"
            }
        
        if n8n_result.get("success") is True or n8n_result.get("status") == "Success":
            return {
                "status": "success",
                "message": n8n_result.get("message", "Usernames added successfully")
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=n8n_result.get("message") or n8n_result.get("detail") or "Failed to insert usernames"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook error: {str(e)}")
