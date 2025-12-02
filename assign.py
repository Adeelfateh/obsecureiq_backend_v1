from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Annotated
from datetime import datetime
import uuid

from database import get_db
from models import Client, User
from schemas import ClientResponse, AssignClientRequest
from users import get_admin_user, get_analyst_user, get_current_user

router = APIRouter()

@router.get("/clients", response_model=Annotated[List[ClientResponse], None])
def get_all_clients(db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    """Get all clients (Admin only)"""
    clients = db.query(Client).order_by(Client.created_at.desc()).all()
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