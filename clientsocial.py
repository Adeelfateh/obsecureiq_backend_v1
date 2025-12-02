from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import uuid

from database import get_db
from models import Client, ClientSocialAccount, User
from schemas import SocialAccountCreate, SocialAccountUpdate, SocialAccountResponse
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/social-accounts", response_model=List[SocialAccountResponse], tags=["Client Social Media"])
def get_client_social_accounts(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all social media accounts for a client"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    social_accounts = db.query(ClientSocialAccount).filter(
        ClientSocialAccount.client_id == client_id
    ).order_by(ClientSocialAccount.created_at.desc()).all()
    
    return social_accounts

@router.post("/clients/{client_id}/social-accounts", response_model=SocialAccountResponse, tags=["Client Social Media"])
def add_client_social_account(
    client_id: uuid.UUID,
    social_data: SocialAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new social media account"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Only validate required fields
    if not social_data.platform or not social_data.platform.strip():
        raise HTTPException(status_code=400, detail="Platform is required")
    
    if not social_data.profile_url or not social_data.profile_url.strip():
        raise HTTPException(status_code=400, detail="Profile URL is required")
    
    # Check for duplicate - ONLY if exact same URL exists (regardless of platform)
    # This allows multiple LinkedIn/Instagram accounts with different URLs
    existing = db.query(ClientSocialAccount).filter(
        ClientSocialAccount.client_id == client_id,
        ClientSocialAccount.profile_url == social_data.profile_url
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="This profile URL already exists for this client"
        )
    
    # Create new social account - allows multiple accounts per platform
    new_social_account = ClientSocialAccount(
        client_id=client_id,
        platform=social_data.platform,
        profile_url=social_data.profile_url,
        what_is_exposed=social_data.what_is_exposed or [],
        engagement_level=social_data.engagement_level,
        confidence_level=social_data.confidence_level
    )
    
    db.add(new_social_account)
    db.commit()
    db.refresh(new_social_account)
    
    return new_social_account

@router.put("/clients/{client_id}/social-accounts/{social_account_id}", response_model=SocialAccountResponse, tags=["Client Social Media"])
def edit_client_social_account(
    client_id: uuid.UUID,
    social_account_id: uuid.UUID,
    social_data: SocialAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit a social media account - works for both modal and inline editing"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    social_record = db.query(ClientSocialAccount).filter(
        ClientSocialAccount.id == social_account_id,
        ClientSocialAccount.client_id == client_id
    ).first()
    
    if not social_record:
        raise HTTPException(status_code=404, detail="Social media account not found")
    
    # Check duplicate only if profile_url is being changed
    # Only prevent same URL, allow multiple accounts per platform
    if social_data.profile_url and social_data.profile_url != social_record.profile_url:
        existing = db.query(ClientSocialAccount).filter(
            ClientSocialAccount.client_id == client_id,
            ClientSocialAccount.profile_url == social_data.profile_url,
            ClientSocialAccount.id != social_account_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="This profile URL already exists"
            )
    
    # Update only the fields that are provided
    update_data = social_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(social_record, field, value)
    
    social_record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(social_record)
    
    return social_record

@router.delete("/clients/{client_id}/social-accounts/{social_account_id}", tags=["Client Social Media"])
def delete_client_social_account(
    client_id: uuid.UUID,
    social_account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a social media account"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    social_record = db.query(ClientSocialAccount).filter(
        ClientSocialAccount.id == social_account_id,
        ClientSocialAccount.client_id == client_id
    ).first()
    
    if not social_record:
        raise HTTPException(status_code=404, detail="Social media account not found")
    
    db.delete(social_record)
    db.commit()
    
    return {"message": "Social media account deleted successfully"}