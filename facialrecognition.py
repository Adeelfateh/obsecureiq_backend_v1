from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from pathlib import Path
import uuid
import shutil
import requests
import os

from database import get_db
from models import Client, ClientFacialRecognitionURL, ClientFacialRecognitionSite, User
from schemas import (
    FacialRecognitionCreate, FacialRecognitionUpdate, FacialRecognitionResponse,
    FacialRecognitionBulkUpload, FacialRecognitionSiteResponse
)
from users import get_current_user

router = APIRouter()
BASE_URL = "https://obsecureiqbackendv1-production-e750.up.railway.app"


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
    """Create facial recognition sites with multiple images in one record"""
    if not site_name.strip():
        raise HTTPException(status_code=400, detail="Site name is required")

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

        url = f"{BASE_URL}/uploads/client_images/{filename}"
        image_urls.append(url)

    # Create a single record with multiple images
    record = ClientFacialRecognitionSite(
        client_id=client_id,
        site_name=site_name.strip(),
        images=image_urls  # Store array of images
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": f"Facial recognition site created with {len(image_urls)} image(s)",
        "record": {
            "id": str(record.id),
            "site_name": record.site_name,
            "images": record.images,
            "created_at": record.created_at.isoformat()
        }
    }

@router.put("/clients/{client_id}/facial-recognition-sites/{record_id}", tags=["Facial Recognition - Sites"])
def update_facial_recognition_site(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a facial recognition site with multiple images"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    record = db.query(ClientFacialRecognitionSite).filter(
        ClientFacialRecognitionSite.id == record_id,
        ClientFacialRecognitionSite.client_id == client_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Facial recognition site not found")
    
    try:
        import json
        record_data = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    
    # Update site name
    site_name = record_data.get('site_name')
    if not site_name or not site_name.strip():
        raise HTTPException(status_code=400, detail="Site name cannot be empty")
    record.site_name = site_name.strip()
    
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
