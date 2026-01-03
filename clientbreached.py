from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from pathlib import Path
import uuid
import shutil
import os

from database import get_db
from models import Client, ClientBreachedRecord, User
from schemas import BreachedRecordResponse
from users import get_current_user

router = APIRouter()
BASE_URL = "https://obsecureiqbackendv1-production-e750.up.railway.app"

# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def _validate_client_access(client_id: uuid.UUID, current_user: User, db: Session) -> Client:
    """Validate client exists and user has access"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return client

@router.get("/clients/{client_id}/breached-records", response_model=List[BreachedRecordResponse], tags=["Breached Records"])
def get_breached_records(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all breached records for a client"""
    _validate_client_access(client_id, current_user, db)
    
    return db.query(ClientBreachedRecord).filter(
        ClientBreachedRecord.client_id == client_id
    ).order_by(ClientBreachedRecord.created_at.desc()).all()

@router.post("/clients/{client_id}/breached-records", tags=["Breached Records"])
def upload_breached_records(
    client_id: uuid.UUID,
    csv_files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload breached records CSV files"""
    if not csv_files:
        raise HTTPException(status_code=400, detail="At least one CSV file is required")

    _validate_client_access(client_id, current_user, db)
    
    uploaded = []

    for csv_file in csv_files:
        ext = Path(csv_file.filename).suffix or ".csv"
        filename = f"{uuid.uuid4()}{ext}"
        filepath = UPLOAD_DIR / filename

        try:
            with filepath.open("wb") as f:
                shutil.copyfileobj(csv_file.file, f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

        file_url = f"{BASE_URL}/uploads/client_images/{filename}"

        record = ClientBreachedRecord(
            client_id=client_id,
            file_url=file_url
        )

        db.add(record)
        db.flush()
        uploaded.append({
            "id": str(record.id),
            "client_id": str(record.client_id),
            "file_url": record.file_url,
            "original_filename": csv_file.filename,
            "created_at": record.created_at.isoformat()
        })

    db.commit()

    return {
        "success": True,
        "message": f"Successfully uploaded {len(uploaded)} CSV file(s)",
        "records": uploaded
    }

@router.put("/clients/{client_id}/breached-records/{record_id}", tags=["Breached Records"])
def update_breached_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    csv_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a breached record"""
    _validate_client_access(client_id, current_user, db)
    
    record = db.query(ClientBreachedRecord).filter(
        ClientBreachedRecord.id == record_id,
        ClientBreachedRecord.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Save new file
    ext = Path(csv_file.filename).suffix or ".csv"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = UPLOAD_DIR / filename

    try:
        with filepath.open("wb") as f:
            shutil.copyfileobj(csv_file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Delete old file
    try:
        old_path = UPLOAD_DIR / Path(record.file_url).name
        if old_path.exists():
            old_path.unlink()
    except Exception as e:
        print(f"Warning: {e}")

    record.file_url = f"{BASE_URL}/uploads/client_images/{filename}"
    record.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "message": "Breached record updated successfully",
        "record": {
            "id": str(record.id),
            "client_id": str(record.client_id),
            "file_url": record.file_url,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat()
        }
    }

@router.delete("/clients/{client_id}/breached-records/{record_id}", tags=["Breached Records"])
def delete_breached_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a breached record"""
    _validate_client_access(client_id, current_user, db)
    
    record = db.query(ClientBreachedRecord).filter(
        ClientBreachedRecord.id == record_id,
        ClientBreachedRecord.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Delete file
    try:
        old_path = UPLOAD_DIR / Path(record.file_url).name
        if old_path.exists():
            old_path.unlink()
    except Exception as e:
        print(f"Warning: Could not delete file: {str(e)}")

    db.delete(record)
    db.commit()

    return {"message": "Breached record deleted successfully"}
