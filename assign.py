from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Annotated, Optional
from datetime import datetime
from pathlib import Path
import uuid
import shutil
import requests
import os

from database import get_db
from models import Client, User, ClientEmail, ClientPhoneNumber
from schemas import ClientResponse, AssignClientRequest, ClientCreate
from users import get_admin_user, get_analyst_user, get_current_user

router = APIRouter()

# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BASE_URL = "https://obsecureiqbackendv1-production-e750.up.railway.app"

def clean_phone_number(phone: str) -> str:
    """Clean and normalize phone number by removing formatting characters"""
    import re
    # Remove all characters except digits and +
    cleaned = re.sub(r'[^0-9+]', '', phone.strip())
    
    # Add +1 if doesn't start with +
    if not cleaned.startswith('+'):
        cleaned = '+1' + cleaned
    
    return cleaned

def update_image_url(client):
    """Update client profile photo URL with current BASE_URL"""
    if client.profile_photo_url:
        # Extract just the filename from the stored URL
        filename = client.profile_photo_url.split('/')[-1]
        # Reconstruct URL with current BASE_URL
        client.profile_photo_url = f"{BASE_URL}/uploads/client_images/{filename}"
    return client

@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    full_name: str = Form(...),
    other_names: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    sex: Optional[str] = Form(None),
    organization: Optional[str] = Form(None),
    emails: Optional[str] = Form(None),
    phone_numbers: Optional[str] = Form(None),
    employer: Optional[str] = Form(None),
    darkside_module: bool = Form(False),
    snubase_module: bool = Form(False),
    profile_photo: Optional[UploadFile] = File(None),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create new client (Admin only)"""
    profile_photo_url = None
    
    # Handle profile photo upload
    if profile_photo:
        ext = Path(profile_photo.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        path = UPLOAD_DIR / filename
        
        with path.open("wb") as f:
            shutil.copyfileobj(profile_photo.file, f)
        
        # Create complete image URL
        profile_photo_url = f"{BASE_URL}/uploads/client_images/{filename}"
    
    # Parse date_of_birth if provided
    parsed_date = None
    if date_of_birth and date_of_birth.strip():  # Only process if not empty
        try:
            parsed_date = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Process phone numbers and store in client table
    phone_for_client = None
    if phone_numbers and phone_numbers.strip():
        phone_lines = [line.strip() for line in phone_numbers.strip().split('\n') if line.strip()]
        unique_phones = list(set(phone_lines))  # Remove duplicates
        # Clean and normalize phone numbers
        cleaned_phones = [clean_phone_number(phone) for phone in unique_phones]
        # Store all phone numbers as newline-separated string in client table
        phone_for_client = '\n'.join(cleaned_phones)
    
    # Process emails and store in client table
    email_for_client = None
    if emails and emails.strip():
        email_lines = [line.strip() for line in emails.strip().split('\n') if line.strip()]
        unique_emails = list(set(email_lines))  # Remove duplicates
        # Store all emails as newline-separated string in client table
        email_for_client = '\n'.join(unique_emails)
    
    # Create new client with provided data
    new_client = Client(
        full_name=full_name,
        other_names=other_names,
        date_of_birth=parsed_date,
        sex=sex,
        organization=organization,
        email=email_for_client,
        phone_number=phone_for_client,
        employer=employer,
        darkside_module=darkside_module,
        snubase_module=snubase_module,
        profile_photo_url=profile_photo_url,
        status="pending"
    )
    
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    # Create individual email records
    if emails and emails.strip():
        email_lines = [line.strip() for line in emails.strip().split('\n') if line.strip()]
        unique_emails = list(set(email_lines))  # Remove duplicates
        for email_addr in unique_emails:
            client_email = ClientEmail(
                client_id=new_client.id,
                email=email_addr,
                status="Client Provided",
                validation_sources=[],
                email_tag=False
            )
            db.add(client_email)
        db.commit()
    
    # Send phone numbers to webhook
    if phone_numbers and phone_numbers.strip():
        webhook_url = "https://obscureiq.app.n8n.cloud/webhook/92457ed2-aad5-4981-b88c-cd65f11b3a8b"
        payload = {
            "phone_number": phone_for_client,
            "client_id": str(new_client.id),
            "client_provided": "Yes"
        }
        try:
            requests.post(webhook_url, json=payload, timeout=60)
        except Exception as e:
            print(f"Warning: Failed to send phone numbers to webhook: {str(e)}")
    
    return new_client

@router.get("/clients", response_model=Annotated[List[ClientResponse], None])
def get_all_clients(db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    """Get all clients (Admin only)"""
    clients = db.query(Client).order_by(Client.created_at.desc()).all()
    # Update image URLs with current BASE_URL
    for client in clients:
        update_image_url(client)
    return clients

@router.put("/clients/{client_id}/assign", status_code=status.HTTP_200_OK)
def assign_client_to_analyst(
    client_id: uuid.UUID, 
    req: AssignClientRequest, 
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Assign client to analyst (Admin only)"""
    # Check if client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check if analyst exists and is a valid user
    analyst = db.query(User).filter(
        User.email == req.analyst_email,
        User.role == "Analyst"
    ).first()
    if not analyst:
        raise HTTPException(status_code=404, detail="No analyst found with that email")

    # Assign analyst to client
    client.analyst_id = analyst.id
    client.assigned_at = datetime.utcnow()
    db.commit()

    return {"message": f"Client assigned to analyst {analyst.full_name}"}

@router.put("/clients/{client_id}/unassign", status_code=status.HTTP_200_OK)
def unassign_client(
    client_id: uuid.UUID, 
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Unassign client from analyst (Admin only)"""
    # Check if client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if not client.analyst_id:
        raise HTTPException(status_code=400, detail="Client is not assigned to any analyst")

    # Unassign client
    client.analyst_id = None
    client.assigned_at = None
    db.commit()

    return {"message": "Client unassigned successfully"}

@router.put("/clients/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: uuid.UUID,
    full_name: Optional[str] = Form(None),
    other_names: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    sex: Optional[str] = Form(None),
    organization: Optional[str] = Form(None),
    emails: Optional[str] = Form(None),
    phone_numbers: Optional[str] = Form(None),
    employer: Optional[str] = Form(None),
    darkside_module: Optional[bool] = Form(None),
    snubase_module: Optional[bool] = Form(None),
    profile_photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update client (Admin or assigned Analyst)"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check permissions: Admin can edit any client, Analyst can only edit assigned clients
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied. You can only edit clients assigned to you.")
    
    # Handle profile photo upload
    if profile_photo:
        # Delete old photo if exists
        if client.profile_photo_url:
            try:
                # Extract filename from URL
                old_filename = client.profile_photo_url.split('/')[-1]
                old_file_path = UPLOAD_DIR / old_filename
                if old_file_path.exists():
                    old_file_path.unlink()
                    print(f"Deleted old profile photo: {old_filename}")
            except Exception as e:
                print(f"Warning: Could not delete old profile photo: {str(e)}")
        
        # Save new photo
        ext = Path(profile_photo.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        path = UPLOAD_DIR / filename
        
        with path.open("wb") as f:
            shutil.copyfileobj(profile_photo.file, f)
        
        # Create complete image URL
        client.profile_photo_url = f"{BASE_URL}/uploads/client_images/{filename}"
    
    # Update only provided fields
    if full_name is not None:
        client.full_name = full_name
    if other_names is not None:
        client.other_names = other_names
    if date_of_birth is not None:
        if date_of_birth.strip():  # Only process if not empty
            try:
                client.date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            client.date_of_birth = None
    if sex is not None:
        client.sex = sex
    if organization is not None:
        client.organization = organization
    if emails is not None:
        # Update client email field and individual email records
        if emails.strip():
            email_lines = [line.strip() for line in emails.strip().split('\n') if line.strip()]
            unique_emails = list(set(email_lines))
            client.email = '\n'.join(unique_emails)
            
            # Get existing emails for this client
            existing_emails = {email.email for email in db.query(ClientEmail).filter(ClientEmail.client_id == client_id).all()}
            
            # Only add new emails that don't already exist
            for email_addr in unique_emails:
                if email_addr not in existing_emails:
                    client_email = ClientEmail(
                        client_id=client_id,
                        email=email_addr,
                        status="Client Provided",
                        validation_sources=[],
                        email_tag=False
                    )
                    db.add(client_email)
        else:
            client.email = None
            db.query(ClientEmail).filter(ClientEmail.client_id == client_id).delete()
    if phone_numbers is not None:
        # Update client phone field and send to webhook
        if phone_numbers.strip():
            phone_lines = [line.strip() for line in phone_numbers.strip().split('\n') if line.strip()]
            unique_phones = list(set(phone_lines))
            cleaned_phones = [clean_phone_number(phone) for phone in unique_phones]
            phone_for_client = '\n'.join(cleaned_phones)
            client.phone_number = phone_for_client
            
            # Send to webhook
            webhook_url = "https://obscureiq.app.n8n.cloud/webhook/92457ed2-aad5-4981-b88c-cd65f11b3a8b"
            payload = {
                "phone_number": phone_for_client,
                "client_id": str(client_id),
                "client_provided": "Yes"
            }
            try:
                requests.post(webhook_url, json=payload, timeout=60)
            except Exception as e:
                print(f"Warning: Failed to send phone numbers to webhook: {str(e)}")
        else:
            client.phone_number = None
    if employer is not None:
        client.employer = employer
    if darkside_module is not None:
        client.darkside_module = darkside_module
    if snubase_module is not None:
        client.snubase_module = snubase_module
    
    db.commit()
    db.refresh(client)
    
    # Update image URL with current BASE_URL before returning
    update_image_url(client)
    
    return client

@router.delete("/clients/{client_id}", status_code=status.HTTP_200_OK)
def delete_client(
    client_id: uuid.UUID, 
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete client completely (Admin only)"""
    # Check if client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Delete the client
    db.delete(client)
    db.commit()

    return {"message": "Client deleted successfully"}

@router.get("/analyst/clients", response_model=Annotated[List[ClientResponse], None])
def get_clients_for_analyst(
    analyst_user: User = Depends(get_analyst_user), 
    db: Session = Depends(get_db)
):
    """Get clients assigned to current analyst"""
    clients = db.query(Client).filter(
        Client.analyst_id == analyst_user.id
    ).order_by(Client.created_at.desc()).all()
    # Update image URLs with current BASE_URL
    for client in clients:
        update_image_url(client)
    return clients
