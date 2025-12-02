from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid
import requests

from database import get_db
from models import Client, User, ClientEmail, ClientPhoneNumber, ClientAddress
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
    
    # Check for at least one client-provided email (status = "Client Provided")
    client_provided_email = db.query(ClientEmail).filter(
        ClientEmail.client_id == client_id,
        ClientEmail.status == "Client Provided"
    ).first()
    
    # Check for at least one client-provided phone number (client_provided = "Yes")
    client_provided_phone = db.query(ClientPhoneNumber).filter(
        ClientPhoneNumber.client_id == client_id,
        ClientPhoneNumber.client_provided == "Yes"
    ).first()
    
    # Check for at least one client-provided address (client_provided = "Yes")
    client_provided_address = db.query(ClientAddress).filter(
        ClientAddress.client_id == client_id,
        ClientAddress.client_provided == "Yes"
    ).first()
    
    # Debug logging
    print(f"Client {client_id} validation:")
    print(f"- Client provided email: {bool(client_provided_email)}")
    print(f"- Client provided phone: {bool(client_provided_phone)}")
    print(f"- Client provided address: {bool(client_provided_address)}")
    
    # Validate that ALL three client-provided data types exist
    missing_data = []
    if not client_provided_email:
        missing_data.append("client-provided email")
    if not client_provided_phone:
        missing_data.append("client-provided phone number")
    if not client_provided_address:
        missing_data.append("client-provided address")
    
    if missing_data:
        missing_items = ", ".join(missing_data)
        raise HTTPException(
            status_code=400, 
            detail=f"Please add the following required client-provided data: {missing_items}"
        )

    webhook_url = "https://obscureiq.app.n8n.cloud/webhook/c6cd3dab-bf74-4e93-98b3-6a1da378b730"
    
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
