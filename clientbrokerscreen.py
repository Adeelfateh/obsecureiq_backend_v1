from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from pathlib import Path
import uuid
import shutil
import os

from database import get_db
from models import Client, ClientBrokerScreenRecord, User
from schemas import BrokerScreenRecordResponse, BrokerScreenRecordUpdate
from users import get_current_user

router = APIRouter()
BASE_URL = "https://obsecureiqbackendv1-production.up.railway.app"

# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/clients/{client_id}/broker-screen-records", response_model=List[BrokerScreenRecordResponse], tags=["Broker Screen Records"])
def get_broker_screen_records(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all broker screen records for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(ClientBrokerScreenRecord).filter(
        ClientBrokerScreenRecord.client_id == client_id
    ).order_by(ClientBrokerScreenRecord.created_at.desc()).all()

@router.post("/clients/{client_id}/broker-screen-records", tags=["Broker Screen Records"])
def create_broker_screen_records(
    client_id: uuid.UUID,
    broker_name: str = Form(...),
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create broker screen records with images"""
    if not broker_name.strip():
        raise HTTPException(status_code=400, detail="Broker name is required")

    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    uploaded = []

    for image in images:
        ext = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        path = UPLOAD_DIR / filename

        with path.open("wb") as f:
            shutil.copyfileobj(image.file, f)

        # Create complete image URL for database
        url = f"{BASE_URL}/uploads/client_images/{filename}"

        record = ClientBrokerScreenRecord(
            client_id=client_id,
            broker_name=broker_name.strip(),
            image_url=url
        )

        db.add(record)
        db.flush()
        uploaded.append({
            "id": str(record.id),
            "broker_name": record.broker_name,
            "image_url": url,
            "created_at": record.created_at.isoformat()
        })

    db.commit()

    return {"message": f"{len(uploaded)} image(s) uploaded", "records": uploaded}

@router.put("/clients/{client_id}/broker-screen-records/{record_id}", response_model=BrokerScreenRecordResponse, tags=["Broker Screen Records"])
def update_broker_screen_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    broker_data: BrokerScreenRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit a broker screen record"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    record = db.query(ClientBrokerScreenRecord).filter(
        ClientBrokerScreenRecord.id == record_id,
        ClientBrokerScreenRecord.client_id == client_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Broker screen record not found")
    
    update_data = broker_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'broker_name' and (not value or not value.strip()):
            raise HTTPException(status_code=400, detail="Broker name cannot be empty")
        setattr(record, field, value.strip() if isinstance(value, str) else value)
    
    record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(record)
    
    return record

@router.delete("/clients/{client_id}/broker-screen-records/{record_id}", tags=["Broker Screen Records"])
def delete_broker_screen_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a broker screen record"""
    record = db.query(ClientBrokerScreenRecord).filter(
        ClientBrokerScreenRecord.id == record_id,
        ClientBrokerScreenRecord.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if current_user.role == "Analyst" and record.client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        old_path = UPLOAD_DIR / Path(record.image_url).name
        if old_path.exists():
            old_path.unlink()
    except Exception as e:
        print(f"Warning: Could not delete image: {str(e)}")

    db.delete(record)
    db.commit()

    return {"message": "Record deleted successfully"}
