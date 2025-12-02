from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from pathlib import Path
import uuid
import shutil
import requests

# Hardcoded BASE_URL
BASE_URL = "https://obsecureiq-frontend-v1.vercel.app"

from database import get_db
from models import Client, ClientFacialRecognitionURL, ClientFacialRecognitionSite, User
from schemas import (
    FacialRecognitionCreate, FacialRecognitionUpdate, FacialRecognitionResponse,
    FacialRecognitionBulkUpload, FacialRecognitionSiteResponse
)
from users import get_current_user

router = APIRouter()

# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ==================== FACIAL RECOGNITION URL APIS ====================

@router.get("/clients/{client_id}/facial-recognition-urls", response_model=List[FacialRecognitionResponse], tags=["Facial Recognition - URLs"])
def get_facial_recognition_urls(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all facial recognition URLs for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(ClientFacialRecognitionURL).filter(
        ClientFacialRecognitionURL.client_id == client_id
    ).order_by(ClientFacialRecognitionURL.created_at.desc()).all()

@router.post("/clients/{client_id}/facial-recognition-urls", response_model=FacialRecognitionResponse, tags=["Facial Recognition - URLs"])
def add_facial_recognition_url(
    client_id: uuid.UUID,
    data: FacialRecognitionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new facial recognition URL"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not data.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    new_url = ClientFacialRecognitionURL(
        client_id=client_id,
        url=data.url.strip()
    )

    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    return new_url

@router.put("/clients/{client_id}/facial-recognition-urls/{url_id}", response_model=FacialRecognitionResponse, tags=["Facial Recognition - URLs"])
def update_facial_recognition_url(
    client_id: uuid.UUID,
    url_id: uuid.UUID,
    data: FacialRecognitionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a facial recognition URL"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(ClientFacialRecognitionURL).filter(
        ClientFacialRecognitionURL.id == url_id,
        ClientFacialRecognitionURL.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Facial recognition URL not found")

    if not data.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    record.url = data.url.strip()
    record.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(record)

    return record

@router.delete("/clients/{client_id}/facial-recognition-urls/{url_id}", tags=["Facial Recognition - URLs"])
def delete_facial_recognition_url(
    client_id: uuid.UUID,
    url_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a facial recognition URL"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(ClientFacialRecognitionURL).filter(
        ClientFacialRecognitionURL.id == url_id,
        ClientFacialRecognitionURL.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Facial recognition URL not found")

    db.delete(record)
    db.commit()

    return {"message": "Facial recognition URL deleted successfully"}

@router.post("/clients/{client_id}/facial-recognition-urls/bulk-upload", tags=["Facial Recognition - URLs"])
def bulk_upload_facial_urls(
    client_id: uuid.UUID,
    data: FacialRecognitionBulkUpload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send raw facial recognition URLs to n8n and return actual result"""
    
    # Check client
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    webhook_url = "https://obscureiq.app.n8n.cloud/webhook/25c6e6ed-d58b-4e0b-a7cf-0347b14e2771"
    
    payload = {
        "urls": data.urls_text,
        "client_id": str(client_id)
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=60)

        # n8n ALWAYS returns JSON because responseMode = "responseNode"
        n8n_result = response.json()

        # SUCCESS CASE from n8n
        if (
            n8n_result.get("status") == "Success"
            or n8n_result.get("success") is True
        ):
            return {
                "status": "success",
                "message": n8n_result.get("message", "Facial URLs added successfully")
            }

        # ERROR CASE (n8n returned failure)
        raise HTTPException(
            status_code=400,
            detail=n8n_result.get("message", "Failed to insert facial recognition URLs")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== FACIAL RECOGNITION SITES APIS ====================

@router.get("/clients/{client_id}/facial-recognition-sites", response_model=List[FacialRecognitionSiteResponse], tags=["Facial Recognition - Sites"])
def get_facial_recognition_sites(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all facial recognition sites for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(ClientFacialRecognitionSite).filter(
        ClientFacialRecognitionSite.client_id == client_id
    ).order_by(ClientFacialRecognitionSite.created_at.desc()).all()

@router.post("/clients/{client_id}/facial-recognition-sites", tags=["Facial Recognition - Sites"])
def create_facial_recognition_sites(
    client_id: uuid.UUID,
    site_name: str = Form(...),
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create facial recognition sites with images"""
    if not site_name.strip():
        raise HTTPException(status_code=400, detail="Site name is required")

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

        url = f"{BASE_URL}/uploads/client_images/{filename}"

        record = ClientFacialRecognitionSite(
            client_id=client_id,
            site_name=site_name.strip(),
            image_url=url
        )

        db.add(record)
        db.flush()
        uploaded.append({
            "id": str(record.id),
            "site_name": record.site_name,
            "image_url": url,
            "created_at": record.created_at.isoformat()
        })

    db.commit()

    return {"message": f"{len(uploaded)} image(s) uploaded", "records": uploaded}

@router.put("/clients/{client_id}/facial-recognition-sites/{record_id}", tags=["Facial Recognition - Sites"])
def update_facial_recognition_site(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    site_name: str = Form(...),
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a facial recognition site"""
    record = db.query(ClientFacialRecognitionSite).filter(
        ClientFacialRecognitionSite.id == record_id,
        ClientFacialRecognitionSite.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if current_user.role == "Analyst" and record.client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate input
    if not site_name.strip():
        raise HTTPException(status_code=400, detail="Site name is required")

    ext = Path(image.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = UPLOAD_DIR / filename

    with filepath.open("wb") as f:
        shutil.copyfileobj(image.file, f)

    # Delete old file
    try:
        old_path = UPLOAD_DIR / Path(record.image_url).name
        if old_path.exists():
            old_path.unlink()
    except Exception as e:
        print(f"Warning: {e}")

    record.site_name = site_name.strip()
    record.image_url = f"{BASE_URL}/uploads/client_images/{filename}"
    record.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(record)

    return {"message": "Record updated", "record": {
        "id": str(record.id),
        "site_name": record.site_name,
        "image_url": record.image_url,
        "updated_at": record.updated_at.isoformat()
    }}

@router.delete("/clients/{client_id}/facial-recognition-sites/{record_id}", tags=["Facial Recognition - Sites"])
def delete_facial_recognition_site(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a facial recognition site"""
    record = db.query(ClientFacialRecognitionSite).filter(
        ClientFacialRecognitionSite.id == record_id,
        ClientFacialRecognitionSite.client_id == client_id
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
