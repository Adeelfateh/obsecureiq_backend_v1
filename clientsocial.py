from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
import uuid
import shutil
import os

from database import get_db
from models import Client, ClientSocialAccount, User
from schemas import SocialAccountCreate, SocialAccountUpdate, SocialAccountResponse
from users import get_current_user

router = APIRouter()
BASE_URL = "https://obsecureiqbackendv1-production.up.railway.app"
# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
    platform: str = Form(...),
    profile_url: str = Form(...),
    what_is_exposed: Optional[str] = Form(None),
    engagement_level: Optional[str] = Form(None),
    confidence_level: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new social media account with optional image"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate required fields
    if not platform or not platform.strip():
        raise HTTPException(status_code=400, detail="Platform is required")
    
    if not profile_url or not profile_url.strip():
        raise HTTPException(status_code=400, detail="Profile URL is required")
    
    # Check for duplicate URL
    existing = db.query(ClientSocialAccount).filter(
        ClientSocialAccount.client_id == client_id,
        ClientSocialAccount.profile_url == profile_url
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="This profile URL already exists for this client"
        )
    
    # Handle image upload
    image_url = None
    if image:
        ext = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        filepath = UPLOAD_DIR / filename
        
        with filepath.open("wb") as f:
            shutil.copyfileobj(image.file, f)
        
        image_url = f"{BASE_URL}/uploads/client_images/{filename}"
    
    # Parse what_is_exposed if provided
    exposed_list = []
    if what_is_exposed:
        exposed_list = [item.strip() for item in what_is_exposed.split(',') if item.strip()]
    
    # Create new social account
    new_social_account = ClientSocialAccount(
        client_id=client_id,
        platform=platform.strip(),
        profile_url=profile_url.strip(),
        what_is_exposed=exposed_list,
        engagement_level=engagement_level,
        confidence_level=confidence_level,
        image_url=image_url
    )
    
    db.add(new_social_account)
    db.commit()
    db.refresh(new_social_account)
    
    return new_social_account

@router.put("/clients/{client_id}/social-accounts/{social_account_id}", response_model=SocialAccountResponse, tags=["Client Social Media"])
def edit_client_social_account(
    client_id: uuid.UUID,
    social_account_id: uuid.UUID,
    platform: Optional[str] = Form(None),
    profile_url: Optional[str] = Form(None),
    what_is_exposed: Optional[str] = Form(None),
    engagement_level: Optional[str] = Form(None),
    confidence_level: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit a social media account with optional image update"""
    
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
    
    # Check duplicate URL if being changed
    if profile_url and profile_url != social_record.profile_url:
        existing = db.query(ClientSocialAccount).filter(
            ClientSocialAccount.client_id == client_id,
            ClientSocialAccount.profile_url == profile_url,
            ClientSocialAccount.id != social_account_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="This profile URL already exists"
            )
    
    # Handle image upload
    if image:
        # Delete old image if exists
        if social_record.image_url:
            try:
                old_path = UPLOAD_DIR / Path(social_record.image_url).name
                if old_path.exists():
                    old_path.unlink()
            except Exception as e:
                print(f"Warning: Could not delete old image: {str(e)}")
        
        # Save new image
        ext = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        filepath = UPLOAD_DIR / filename
        
        with filepath.open("wb") as f:
            shutil.copyfileobj(image.file, f)
        
        social_record.image_url = f"{BASE_URL}/uploads/client_images/{filename}"
    
    # Update other fields if provided
    if platform is not None:
        social_record.platform = platform.strip()
    if profile_url is not None:
        social_record.profile_url = profile_url.strip()
    if what_is_exposed is not None:
        social_record.what_is_exposed = [item.strip() for item in what_is_exposed.split(',') if item.strip()] if what_is_exposed else []
    if engagement_level is not None:
        social_record.engagement_level = engagement_level
    if confidence_level is not None:
        social_record.confidence_level = confidence_level
    
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
    
    # Delete associated image if exists
    if social_record.image_url:
        try:
            old_path = UPLOAD_DIR / Path(social_record.image_url).name
            if old_path.exists():
                old_path.unlink()
        except Exception as e:
            print(f"Warning: Could not delete image: {str(e)}")
    
    db.delete(social_record)
    db.commit()
    
    return {"message": "Social media account deleted successfully"}
