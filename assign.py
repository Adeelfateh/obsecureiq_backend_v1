from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Annotated, Optional
from datetime import datetime
from pathlib import Path
import uuid
import shutil
import os

from database import get_db
from models import Client, User
from schemas import ClientResponse, AssignClientRequest, ClientCreate
from users import get_admin_user, get_analyst_user, get_current_user

router = APIRouter()
BASE_URL = "https://obsecureiqbackendv1-production.up.railway.app"

# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    full_name: str = Form(...),
    other_names: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    sex: Optional[str] = Form(None),
    organization: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    employer: Optional[str] = Form(None),
    status: Optional[str] = Form("pending"),
    risk_score: Optional[str] = Form(None),
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
    if date_of_birth:
        try:
            from datetime import datetime
            parsed_date = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Create new client with provided data
    new_client = Client(
        full_name=full_name,
        other_names=other_names,
        date_of_birth=parsed_date,
        sex=sex,
        organization=organization,
        email=email,
        phone_number=phone_number,
        employer=employer,
        profile_photo_url=profile_photo_url,
        status=status or "pending",
        risk_score=risk_score
    )
    
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    return new_client

@router.get("/clients", response_model=Annotated[List[ClientResponse], None])
def get_all_clients(db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    """Get all clients (Admin only)"""
    clients = db.query(Client).order_by(Client.created_at.desc()).all()
    
    # Add analyst information to each client
    for client in clients:
        if client.analyst_id:
            analyst = db.query(User).filter(User.id == client.analyst_id).first()
            if analyst:
                client.analyst_name = analyst.full_name
                client.analyst_email = analyst.email
    
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
    return clients
