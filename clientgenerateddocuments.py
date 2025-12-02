from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from models import Client, ClientGeneratedDocument, User
from users import get_current_user

router = APIRouter()

def _validate_client_access(client_id: uuid.UUID, current_user: User, db: Session) -> Client:
    """Validate client exists and user has access"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return client

@router.get("/clients/{client_id}/documents", tags=["Generated Documents"])
def get_client_generated_documents(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all generated documents for a specific client (Analyst view)"""
    client = _validate_client_access(client_id, current_user, db)
    
    documents = db.query(ClientGeneratedDocument).filter(
        ClientGeneratedDocument.client_id == client_id
    ).order_by(ClientGeneratedDocument.created_at.desc()).all()
    
    return {
        "client": {
            "id": str(client.id),
            "full_name": client.full_name,
            "email": client.email
        },
        "documents": [
            {
                "id": str(doc.id),
                "client_name": doc.client_name,
                "file_name": doc.file_name,
                "view_url": doc.view_url,
                "download_url": doc.download_url,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat()
            }
            for doc in documents
        ]
    }

@router.get("/admin/all-documents", tags=["Generated Documents"])
def get_all_generated_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all generated documents across all clients (Admin view)"""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    documents = db.query(ClientGeneratedDocument).join(Client).order_by(
        ClientGeneratedDocument.created_at.desc()
    ).all()
    
    return {
        "documents": [
            {
                "id": str(doc.id),
                "client_name": doc.client_name,
                "file_name": doc.file_name,
                "view_url": doc.view_url,
                "download_url": doc.download_url,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
                "client": {
                    "id": str(doc.client.id),
                    "full_name": doc.client.full_name,
                    "email": doc.client.email,
                    "analyst_id": doc.client.analyst_id
                }
            }
            for doc in documents
        ]
    }