from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
import uuid
import shutil
import os
import json

from database import get_db
from models import Client, ClientSocialAccount, User
from schemas import SocialAccountCreate, SocialAccountUpdate, SocialAccountResponse
from users import get_current_user

router = APIRouter()

# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://obsecureiqbackendv1-production-e750.up.railway.app"

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
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new social media account with multiple images"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Parse JSON data
    record_data = json.loads(data)
    
    # Validate required fields
    if not record_data.get('platform') or not record_data.get('platform').strip():
        raise HTTPException(status_code=400, detail="Platform is required")
    
    if not record_data.get('profile_url') or not record_data.get('profile_url').strip():
        raise HTTPException(status_code=400, detail="Profile URL is required")
    
    # Check for duplicate URL
    existing = db.query(ClientSocialAccount).filter(
        ClientSocialAccount.client_id == client_id,
        ClientSocialAccount.profile_url == record_data.get('profile_url')
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="This profile URL already exists for this client"
        )
    
    # Handle multiple image uploads
    image_urls = []
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOAD_DIR / filename
            
            with filepath.open("wb") as f:
                shutil.copyfileobj(image.file, f)

            image_url = f"{BASE_URL}/uploads/client_images/{filename}"
            image_urls.append(image_url)
    
    # Parse what_is_exposed if provided
    exposed_list = []
    if record_data.get('what_is_exposed'):
        exposed_list = [item.strip() for item in record_data.get('what_is_exposed').split(',') if item.strip()]
    
    # Create new social account
    new_social_account = ClientSocialAccount(
        client_id=client_id,
        platform=record_data.get('platform').strip(),
        profile_url=record_data.get('profile_url').strip(),
        what_is_exposed=exposed_list,
        engagement_level=record_data.get('engagement_level'),
        confidence_level=record_data.get('confidence_level'),
        images=image_urls  # Store multiple images
    )
    
    db.add(new_social_account)
    db.commit()
    db.refresh(new_social_account)
    
    return new_social_account

@router.put("/clients/{client_id}/social-accounts/{social_account_id}", response_model=SocialAccountResponse, tags=["Client Social Media"])
def edit_client_social_account(
    client_id: uuid.UUID,
    social_account_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit a social media account with multiple images"""
    
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
    
    update_data = json.loads(data)
    
    # Check if this is an inline update (single field) or modal update (multiple fields + images)
    is_inline_update = len(update_data) == 1 and 'remaining_images' not in update_data and not images
    
    if is_inline_update:
        # Handle inline update - just update the single field
        for field, value in update_data.items():
            if field == 'platform':
                social_record.platform = value.strip() if value else None
            elif field == 'profile_url':
                # Check duplicate URL if being changed
                if value and value != social_record.profile_url:
                    existing = db.query(ClientSocialAccount).filter(
                        ClientSocialAccount.client_id == client_id,
                        ClientSocialAccount.profile_url == value,
                        ClientSocialAccount.id != social_account_id
                    ).first()
                    
                    if existing:
                        raise HTTPException(
                            status_code=400, 
                            detail="This profile URL already exists"
                        )
                social_record.profile_url = value.strip() if value else None
            elif field == 'what_is_exposed':
                social_record.what_is_exposed = [item.strip() for item in value.split(',') if item.strip()] if value else []
            elif field == 'engagement_level':
                social_record.engagement_level = value
            elif field == 'confidence_level':
                social_record.confidence_level = value
        
        social_record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(social_record)
        return social_record
    
    # Handle modal update with images
    # Store original images in memory
    original_images = social_record.images or []
    
    # Get remaining images from frontend (after user removed some)
    remaining_images = update_data.get('remaining_images', original_images)
    
    # Find images that user removed (to delete from storage)
    removed_images = [img for img in original_images if img not in remaining_images]
    
    # Delete removed images from storage
    for removed_url in removed_images:
        try:
            filename = Path(removed_url).name
            file_path = UPLOAD_DIR / filename
            if file_path.exists():
                file_path.unlink()
                print(f"Deleted image: {filename}")
        except Exception as e:
            print(f"Warning: Could not delete file {filename}: {str(e)}")
    
    # Upload new images
    new_image_urls = []
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOAD_DIR / filename
            
            with filepath.open("wb") as f:
                shutil.copyfileobj(image.file, f)
            
            
            image_url = f"{BASE_URL}/uploads/client_images/{filename}"
            new_image_urls.append(image_url)
    
    # Update record with combined images (remaining + new)
    social_record.images = remaining_images + new_image_urls
    
    # Update other fields
    if 'platform' in update_data:
        social_record.platform = update_data['platform'].strip() if update_data['platform'] else None
    if 'profile_url' in update_data:
        # Check duplicate URL if being changed
        if update_data['profile_url'] and update_data['profile_url'] != social_record.profile_url:
            existing = db.query(ClientSocialAccount).filter(
                ClientSocialAccount.client_id == client_id,
                ClientSocialAccount.profile_url == update_data['profile_url'],
                ClientSocialAccount.id != social_account_id
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail="This profile URL already exists"
                )
        social_record.profile_url = update_data['profile_url'].strip() if update_data['profile_url'] else None
    if 'what_is_exposed' in update_data:
        social_record.what_is_exposed = [item.strip() for item in update_data['what_is_exposed'].split(',') if item.strip()] if update_data['what_is_exposed'] else []
    if 'engagement_level' in update_data:
        social_record.engagement_level = update_data['engagement_level']
    if 'confidence_level' in update_data:
        social_record.confidence_level = update_data['confidence_level']
    
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
    
    # Delete associated images if exist
    if social_record.images:
        for image_url in social_record.images:
            try:
                old_path = UPLOAD_DIR / Path(image_url).name
                if old_path.exists():
                    old_path.unlink()
            except Exception as e:
                print(f"Warning: Could not delete image: {str(e)}")
    
    db.delete(social_record)
    db.commit()
    
    return {"message": "Social media account deleted successfully"}
