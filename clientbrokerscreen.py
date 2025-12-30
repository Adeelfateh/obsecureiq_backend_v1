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
def create_broker_screen_record(
    client_id: uuid.UUID,
    broker_name: str = Form(...),
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a broker screen record with multiple images"""
    if not broker_name.strip():
        raise HTTPException(status_code=400, detail="Broker name is required")

    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    image_urls = []

    for image in images:
        ext = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        path = UPLOAD_DIR / filename

        with path.open("wb") as f:
            shutil.copyfileobj(image.file, f)

        # Create complete image URL for database
        url = f"{BASE_URL}/uploads/client_images/{filename}"
        image_urls.append(url)

    # Create a single record with multiple images
    record = ClientBrokerScreenRecord(
        client_id=client_id,
        broker_name=broker_name.strip(),
        images=image_urls
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": f"Broker record created with {len(image_urls)} image(s)",
        "record": {
            "id": str(record.id),
            "broker_name": record.broker_name,
            "images": record.images,
            "created_at": record.created_at.isoformat()
        }
    }

@router.put("/clients/{client_id}/broker-screen-records/{record_id}", response_model=BrokerScreenRecordResponse, tags=["Broker Screen Records"])
def update_broker_screen_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a broker screen record"""
    
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
    
    try:
        import json
        record_data = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    
    # Update broker name
    broker_name = record_data.get('broker_name')
    if not broker_name or not broker_name.strip():
        raise HTTPException(status_code=400, detail="Broker name cannot be empty")
    record.broker_name = broker_name.strip()
    
    # Handle images
    remaining_images = record_data.get('remaining_images', [])
    
    # Delete removed images from filesystem
    if record.images:
        for old_image_url in record.images:
            if old_image_url not in remaining_images:
                try:
                    old_path = UPLOAD_DIR / Path(old_image_url).name
                    if old_path.exists():
                        old_path.unlink()
                except Exception as e:
                    print(f"Warning: Could not delete old image: {str(e)}")
    
    # Start with remaining images
    final_images = remaining_images.copy()
    
    # Add new uploaded images
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            path = UPLOAD_DIR / filename

            with path.open("wb") as f:
                shutil.copyfileobj(image.file, f)

            url = f"{BASE_URL}/uploads/client_images/{filename}"
            final_images.append(url)
    
    record.images = final_images
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

    # Delete all images from filesystem
    if record.images:
        for image_url in record.images:
            try:
                old_path = UPLOAD_DIR / Path(image_url).name
                if old_path.exists():
                    old_path.unlink()
            except Exception as e:
                print(f"Warning: Could not delete image: {str(e)}")

    db.delete(record)
    db.commit()

    return {"message": "Record deleted successfully"}
