from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid
import requests

from database import get_db
from models import Client, User
from users import get_current_user

router = APIRouter()

@router.post("/clients/{client_id}/generate-document", tags=["Document Generation"])
def generate_document(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate document by sending client ID to webhook"""
    
    # Check client exists and user has access
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    webhook_url = "https://obscureiq.app.n8n.cloud/webhook-test/c6cd3dab-bf74-4e93-98b3-6a1da378b730"
    
    payload = {
        "client_id": str(client_id)
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            return {
                "message": "Document generation initiated successfully",
                "status": "success",
                "client_id": str(client_id)
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Webhook failed with status {response.status_code}"
            )
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=500, detail="Webhook request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send to webhook: {str(e)}")