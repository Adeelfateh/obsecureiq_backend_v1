from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from pathlib import Path
import uuid
import shutil
import json

# Hardcoded BASE_URL
BASE_URL = "https://obsecureiqbackendv1-production.up.railway.app"

from database import get_db
from models import (
    Client, ClientFrontHouseRecord, ClientBackHouseRecord, 
    ClientInsideHouseRecord, ClientGoogleStreetViewRecord, User
)
from schemas import (
    FrontHouseRecordCreate, FrontHouseRecordUpdate, FrontHouseRecordResponse,
    BackHouseRecordCreate, BackHouseRecordUpdate, BackHouseRecordResponse,
    InsideHouseRecordCreate, InsideHouseRecordUpdate, InsideHouseRecordResponse,
    GoogleStreetViewRecordCreate, GoogleStreetViewRecordUpdate, GoogleStreetViewRecordResponse
)
from users import get_current_user

router = APIRouter()

# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ==================== FRONT OF HOUSE APIS ====================

@router.get("/clients/{client_id}/front-house-records", response_model=List[FrontHouseRecordResponse], tags=["Digital Recognition - Front House"])
def get_front_house_records(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all front house records for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.query(ClientFrontHouseRecord).filter(
        ClientFrontHouseRecord.client_id == client_id
    ).order_by(ClientFrontHouseRecord.created_at.desc()).all()

@router.post("/clients/{client_id}/front-house-records", response_model=FrontHouseRecordResponse, tags=["Digital Recognition - Front House"])
def create_front_house_record(
    client_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new front house record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Parse JSON data
    record_data = json.loads(data)
    
    # Handle image uploads
    image_urls = []
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOAD_DIR / filename
            
            with filepath.open("wb") as f:
                shutil.copyfileobj(image.file, f)
            
            # Create complete image URL for database
            image_url = f"{BASE_URL}/uploads/client_images/{filename}"
            image_urls.append(image_url)
    
    record = ClientFrontHouseRecord(
        client_id=client_id,
        home_visible_from_street=record_data.get('home_visible_from_street', 'No'),
        exterior_lighting=record_data.get('exterior_lighting', 'No'),
        surveillance_cameras=record_data.get('surveillance_cameras', 'No'),
        motion_sensors_alarms=record_data.get('motion_sensors_alarms', 'No'),
        ground_floor_windows_accessible=record_data.get('ground_floor_windows_accessible', 'No'),
        bars_locks_reinforced_glass=record_data.get('bars_locks_reinforced_glass', 'No'),
        gate_fence=record_data.get('gate_fence', 'No'),
        obstruction_of_view=record_data.get('obstruction_of_view'),
        security_signage=record_data.get('security_signage', 'No'),
        images=image_urls
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.post("/clients/{client_id}/front-house-records/{record_id}/images", tags=["Digital Recognition - Front House"])
def upload_front_house_images(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload additional images to front house record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    record = db.query(ClientFrontHouseRecord).filter(
        ClientFrontHouseRecord.id == record_id,
        ClientFrontHouseRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")
    
    uploaded_urls = []
    for image in images:
        ext = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        filepath = UPLOAD_DIR / filename
        
        with filepath.open("wb") as f:
            shutil.copyfileobj(image.file, f)
        
        # Create complete image URL for database
        image_url = f"{BASE_URL}/uploads/client_images/{filename}"
        uploaded_urls.append(image_url)
    
    # Update record with new image URLs
    current_images = record.images or []
    record.images = current_images + uploaded_urls
    record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(record)
    
    return {
        "success": True,
        "message": f"Uploaded {len(uploaded_urls)} image(s)",
        "image_urls": uploaded_urls,
        "record": record
    }

@router.put("/clients/{client_id}/front-house-records/{record_id}", response_model=FrontHouseRecordResponse, tags=["Digital Recognition - Front House"])
def update_front_house_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a front house record"""
    record = db.query(ClientFrontHouseRecord).filter(
        ClientFrontHouseRecord.id == record_id,
        ClientFrontHouseRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.role == "Analyst" and record.client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = json.loads(data)
    
    # Check if this is an inline update (single field) or modal update (multiple fields + images)
    is_inline_update = len(update_data) == 1 and 'remaining_images' not in update_data and not images
    
    if is_inline_update:
        # Handle inline update - just update the single field
        allowed_fields = {
            'home_visible_from_street', 'exterior_lighting', 'surveillance_cameras',
            'motion_sensors_alarms', 'ground_floor_windows_accessible', 
            'bars_locks_reinforced_glass', 'gate_fence', 'obstruction_of_view', 'security_signage'
        }
        
        for field, value in update_data.items():
            if field in allowed_fields:
                setattr(record, field, value)
        
        record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(record)
        return record
    
    # Handle modal update with images
    # Store original images in memory
    original_images = record.images or []
    
    # Get remaining images from frontend (after user removed some)
    remaining_images = update_data.get('remaining_images', original_images)
    
    # Find images that user removed (to delete from storage)
    removed_images = [img for img in original_images if img not in remaining_images]
    
    # Delete removed images from storage
    for removed_url in removed_images:
        try:
            filename = Path(removed_url).name
            file_path = UPLOAD_DIR / filename
            if file_path.exists():
                file_path.unlink()
                print(f"Deleted image: {filename}")
        except Exception as e:
            print(f"Warning: Could not delete file {filename}: {str(e)}")
    
    # Upload new images
    new_image_urls = []
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOAD_DIR / filename
            
            with filepath.open("wb") as f:
                shutil.copyfileobj(image.file, f)
            
            image_url =  f"{BASE_URL}/uploads/client_images/{filename}"
            new_image_urls.append(image_url)
            print(f"Uploaded new image: {filename}")
    
    # Update form fields
    allowed_fields = {
        'home_visible_from_street', 'exterior_lighting', 'surveillance_cameras',
        'motion_sensors_alarms', 'ground_floor_windows_accessible', 
        'bars_locks_reinforced_glass', 'gate_fence', 'obstruction_of_view', 'security_signage'
    }
    
    for field, value in update_data.items():
        if field in allowed_fields:
            setattr(record, field, value)
    
    # Final images = remaining existing images + newly uploaded images
    record.images = remaining_images + new_image_urls
    record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(record)
    
    print(f"Updated record {record_id}: {len(remaining_images)} remaining + {len(new_image_urls)} new = {len(record.images)} total images")
    return record

@router.delete("/clients/{client_id}/front-house-records/{record_id}", tags=["Digital Recognition - Front House"])
def delete_front_house_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a front house record"""
    record = db.query(ClientFrontHouseRecord).filter(
        ClientFrontHouseRecord.id == record_id,
        ClientFrontHouseRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.role == "Analyst" and record.client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete associated image files
    if record.images:
        for image_url in record.images:
            try:
                filename = Path(image_url).name
                file_path = UPLOAD_DIR / filename
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                print(f"Warning: Could not delete file: {str(e)}")
    
    db.delete(record)
    db.commit()
    return {"message": "Record deleted successfully"}

# ==================== BACK OF HOUSE APIS ====================

@router.get("/clients/{client_id}/back-house-records", response_model=List[BackHouseRecordResponse], tags=["Digital Recognition - Back House"])
def get_back_house_records(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all back house records for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.query(ClientBackHouseRecord).filter(
        ClientBackHouseRecord.client_id == client_id
    ).order_by(ClientBackHouseRecord.created_at.desc()).all()

@router.post("/clients/{client_id}/back-house-records", response_model=BackHouseRecordResponse, tags=["Digital Recognition - Back House"])
def create_back_house_record(
    client_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new back house record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Parse JSON data
    record_data = json.loads(data)
    
    # Handle image uploads
    image_urls = []
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOAD_DIR / filename
            
            with filepath.open("wb") as f:
                shutil.copyfileobj(image.file, f)
            
            image_url =  f"{BASE_URL}/uploads/client_images/{filename}"
            image_urls.append(image_url)
    
    record = ClientBackHouseRecord(
        client_id=client_id,
        rear_entry_door=record_data.get('rear_entry_door', 'No'),
        ground_floor_windows_accessible=record_data.get('ground_floor_windows_accessible', 'No'),
        rear_exterior_lighting=record_data.get('rear_exterior_lighting', 'No'),
        bars_locks_reinforced_glass=record_data.get('bars_locks_reinforced_glass', 'No'),
        gate_fence=record_data.get('gate_fence', 'No'),
        obstruction_of_view=record_data.get('obstruction_of_view'),
        surveillance_cameras=record_data.get('surveillance_cameras', 'No'),
        landscaping_concealment=record_data.get('landscaping_concealment', 'None'),
        outbuildings_visible=record_data.get('outbuildings_visible', 'No'),
        pet_door_present=record_data.get('pet_door_present', 'No'),
        images=image_urls
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.post("/clients/{client_id}/back-house-records/{record_id}/images", tags=["Digital Recognition - Back House"])
def upload_back_house_images(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload additional images to back house record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    record = db.query(ClientBackHouseRecord).filter(
        ClientBackHouseRecord.id == record_id,
        ClientBackHouseRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")
    
    uploaded_urls = []
    for image in images:
        ext = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        filepath = UPLOAD_DIR / filename
        
        with filepath.open("wb") as f:
            shutil.copyfileobj(image.file, f)
        
        image_url =  f"{BASE_URL}/uploads/client_images/{filename}"
        uploaded_urls.append(image_url)
    
    # Update record with new image URLs
    current_images = record.images or []
    record.images = current_images + uploaded_urls
    record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(record)
    
    return {
        "success": True,
        "message": f"Uploaded {len(uploaded_urls)} image(s)",
        "image_urls": uploaded_urls,
        "record": record
    }

@router.put("/clients/{client_id}/back-house-records/{record_id}", response_model=BackHouseRecordResponse, tags=["Digital Recognition - Back House"])
def update_back_house_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a back house record"""
    record = db.query(ClientBackHouseRecord).filter(
        ClientBackHouseRecord.id == record_id,
        ClientBackHouseRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.role == "Analyst" and record.client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = json.loads(data)
    
    # Check if this is an inline update (single field) or modal update (multiple fields + images)
    is_inline_update = len(update_data) == 1 and 'remaining_images' not in update_data and not images
    
    if is_inline_update:
        # Handle inline update - just update the single field
        allowed_fields = {
            'rear_entry_door', 'ground_floor_windows_accessible', 'rear_exterior_lighting',
            'bars_locks_reinforced_glass', 'gate_fence', 'obstruction_of_view',
            'surveillance_cameras', 'landscaping_concealment', 'outbuildings_visible', 'pet_door_present'
        }
        
        for field, value in update_data.items():
            if field in allowed_fields:
                setattr(record, field, value)
        
        record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(record)
        return record
    
    # Handle modal update with images
    # Store original images in memory
    original_images = record.images or []
    
    # Get remaining images from frontend (after user removed some)
    remaining_images = update_data.get('remaining_images', original_images)
    
    # Find images that user removed (to delete from storage)
    removed_images = [img for img in original_images if img not in remaining_images]
    
    # Delete removed images from storage
    for removed_url in removed_images:
        try:
            filename = Path(removed_url).name
            file_path = UPLOAD_DIR / filename
            if file_path.exists():
                file_path.unlink()
                print(f"Deleted image: {filename}")
        except Exception as e:
            print(f"Warning: Could not delete file {filename}: {str(e)}")
    
    # Upload new images
    new_image_urls = []
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOAD_DIR / filename
            
            with filepath.open("wb") as f:
                shutil.copyfileobj(image.file, f)
            
            image_url =  f"{BASE_URL}/uploads/client_images/{filename}"
            new_image_urls.append(image_url)
            print(f"Uploaded new image: {filename}")
    
    # Update form fields
    allowed_fields = {
        'rear_entry_door', 'ground_floor_windows_accessible', 'rear_exterior_lighting',
        'bars_locks_reinforced_glass', 'gate_fence', 'obstruction_of_view',
        'surveillance_cameras', 'landscaping_concealment', 'outbuildings_visible', 'pet_door_present'
    }
    
    for field, value in update_data.items():
        if field in allowed_fields:
            setattr(record, field, value)
    
    # Final images = remaining existing images + newly uploaded images
    record.images = remaining_images + new_image_urls
    record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(record)
    
    print(f"Updated back house record {record_id}: {len(remaining_images)} remaining + {len(new_image_urls)} new = {len(record.images)} total images")
    return record

@router.delete("/clients/{client_id}/back-house-records/{record_id}", tags=["Digital Recognition - Back House"])
def delete_back_house_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a back house record"""
    record = db.query(ClientBackHouseRecord).filter(
        ClientBackHouseRecord.id == record_id,
        ClientBackHouseRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.role == "Analyst" and record.client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete(record)
    db.commit()
    return {"message": "Record deleted successfully"}

# ==================== INSIDE HOUSE APIS ====================

@router.get("/clients/{client_id}/inside-house-records", response_model=List[InsideHouseRecordResponse], tags=["Digital Recognition - Inside House"])
def get_inside_house_records(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all inside house records for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.query(ClientInsideHouseRecord).filter(
        ClientInsideHouseRecord.client_id == client_id
    ).order_by(ClientInsideHouseRecord.created_at.desc()).all()

@router.post("/clients/{client_id}/inside-house-records", response_model=InsideHouseRecordResponse, tags=["Digital Recognition - Inside House"])
def create_inside_house_record(
    client_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new inside house record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Parse JSON data
    record_data = json.loads(data)
    
    # Handle image uploads
    image_urls = []
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOAD_DIR / filename
            
            with filepath.open("wb") as f:
                shutil.copyfileobj(image.file, f)
            
            image_url = f"{BASE_URL}/uploads/client_images/{filename}"
            image_urls.append(image_url)
    
    record = ClientInsideHouseRecord(
        client_id=client_id,
        layout_exposure=record_data.get('layout_exposure'),
        images=image_urls
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.post("/clients/{client_id}/inside-house-records/{record_id}/images", tags=["Digital Recognition - Inside House"])
def upload_inside_house_images(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload additional images to inside house record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    record = db.query(ClientInsideHouseRecord).filter(
        ClientInsideHouseRecord.id == record_id,
        ClientInsideHouseRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")
    
    uploaded_urls = []
    for image in images:
        ext = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        filepath = UPLOAD_DIR / filename
        
        with filepath.open("wb") as f:
            shutil.copyfileobj(image.file, f)
        
        image_url =  f"{BASE_URL}/uploads/client_images/{filename}"
        uploaded_urls.append(image_url)
    
    # Update record with new image URLs
    current_images = record.images or []
    record.images = current_images + uploaded_urls
    record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(record)
    
    return {
        "success": True,
        "message": f"Uploaded {len(uploaded_urls)} image(s)",
        "image_urls": uploaded_urls,
        "record": record
    }

@router.put("/clients/{client_id}/inside-house-records/{record_id}", response_model=InsideHouseRecordResponse, tags=["Digital Recognition - Inside House"])
def update_inside_house_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an inside house record"""
    record = db.query(ClientInsideHouseRecord).filter(
        ClientInsideHouseRecord.id == record_id,
        ClientInsideHouseRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.role == "Analyst" and record.client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = json.loads(data)
    
    # Check if this is an inline update (single field) or modal update (multiple fields + images)
    is_inline_update = len(update_data) == 1 and 'remaining_images' not in update_data and not images
    
    if is_inline_update:
        # Handle inline update - just update the single field
        allowed_fields = {'layout_exposure'}
        
        for field, value in update_data.items():
            if field in allowed_fields:
                setattr(record, field, value)
        
        record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(record)
        return record
    
    # Handle modal update with images
    original_images = record.images or []
    remaining_images = update_data.get('remaining_images', original_images)
    removed_images = [img for img in original_images if img not in remaining_images]
    
    # Delete removed images from storage
    for removed_url in removed_images:
        try:
            filename = Path(removed_url).name
            file_path = UPLOAD_DIR / filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Warning: Could not delete file {filename}: {str(e)}")
    
    # Upload new images
    new_image_urls = []
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOAD_DIR / filename
            
            with filepath.open("wb") as f:
                shutil.copyfileobj(image.file, f)
            
            image_url =  f"{BASE_URL}/uploads/client_images/{filename}"
            new_image_urls.append(image_url)
    
    # Update fields
    allowed_fields = {'layout_exposure'}
    for field, value in update_data.items():
        if field in allowed_fields:
            setattr(record, field, value)
    
    # Final images = remaining + new
    record.images = remaining_images + new_image_urls
    record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(record)
    return record

@router.delete("/clients/{client_id}/inside-house-records/{record_id}", tags=["Digital Recognition - Inside House"])
def delete_inside_house_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an inside house record"""
    record = db.query(ClientInsideHouseRecord).filter(
        ClientInsideHouseRecord.id == record_id,
        ClientInsideHouseRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.role == "Analyst" and record.client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete(record)
    db.commit()
    return {"message": "Record deleted successfully"}

# ==================== GOOGLE STREET VIEW APIS ====================

@router.get("/clients/{client_id}/google-street-view-records", response_model=List[GoogleStreetViewRecordResponse], tags=["Digital Recognition - Google Street View"])
def get_google_street_view_records(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all Google Street View records for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.query(ClientGoogleStreetViewRecord).filter(
        ClientGoogleStreetViewRecord.client_id == client_id
    ).order_by(ClientGoogleStreetViewRecord.created_at.desc()).all()

@router.post("/clients/{client_id}/google-street-view-records", response_model=GoogleStreetViewRecordResponse, tags=["Digital Recognition - Google Street View"])
def create_google_street_view_record(
    client_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new Google Street View record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Parse JSON data
    record_data = json.loads(data)
    
    # Handle image uploads
    image_urls = []
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOAD_DIR / filename
            
            with filepath.open("wb") as f:
                shutil.copyfileobj(image.file, f)
            
            image_url =  f"{BASE_URL}/uploads/client_images/{filename}"
            image_urls.append(image_url)
    
    record = ClientGoogleStreetViewRecord(
        client_id=client_id,
        home_visible_from_street=record_data.get('home_visible_from_street'),
        exterior_lighting=record_data.get('exterior_lighting'),
        surveillance_cameras=record_data.get('surveillance_cameras'),
        motion_sensors_alarms=record_data.get('motion_sensors_alarms'),
        ground_floor_windows_accessible=record_data.get('ground_floor_windows_accessible'),
        bars_locks_reinforced_glass=record_data.get('bars_locks_reinforced_glass'),
        gate_fence=record_data.get('gate_fence'),
        obstruction_of_view=record_data.get('obstruction_of_view'),
        security_signage=record_data.get('security_signage'),
        images=image_urls
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.post("/clients/{client_id}/google-street-view-records/{record_id}/images", tags=["Digital Recognition - Google Street View"])
def upload_google_street_view_images(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload additional images to Google Street View record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    record = db.query(ClientGoogleStreetViewRecord).filter(
        ClientGoogleStreetViewRecord.id == record_id,
        ClientGoogleStreetViewRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")
    
    uploaded_urls = []
    for image in images:
        ext = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        filepath = UPLOAD_DIR / filename
        
        with filepath.open("wb") as f:
            shutil.copyfileobj(image.file, f)
        
        image_url =  f"{BASE_URL}/uploads/client_images/{filename}"
        uploaded_urls.append(image_url)
    
    # Update record with new image URLs
    current_images = record.images or []
    record.images = current_images + uploaded_urls
    record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(record)
    
    return {
        "success": True,
        "message": f"Uploaded {len(uploaded_urls)} image(s)",
        "image_urls": uploaded_urls,
        "record": record
    }

@router.put("/clients/{client_id}/google-street-view-records/{record_id}", response_model=GoogleStreetViewRecordResponse, tags=["Digital Recognition - Google Street View"])
def update_google_street_view_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    data: str = Form(...),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a Google Street View record"""
    record = db.query(ClientGoogleStreetViewRecord).filter(
        ClientGoogleStreetViewRecord.id == record_id,
        ClientGoogleStreetViewRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.role == "Analyst" and record.client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = json.loads(data)
    
    # Check if this is an inline update (single field) or modal update (multiple fields + images)
    is_inline_update = len(update_data) == 1 and 'remaining_images' not in update_data and not images
    
    if is_inline_update:
        # Handle inline update - just update the single field
        allowed_fields = {
            'home_visible_from_street', 'exterior_lighting', 'surveillance_cameras',
            'motion_sensors_alarms', 'ground_floor_windows_accessible', 
            'bars_locks_reinforced_glass', 'gate_fence', 'obstruction_of_view', 'security_signage'
        }
        
        for field, value in update_data.items():
            if field in allowed_fields:
                setattr(record, field, value)
        
        record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(record)
        return record
    
    # Handle modal update with images
    original_images = record.images or []
    remaining_images = update_data.get('remaining_images', original_images)
    removed_images = [img for img in original_images if img not in remaining_images]
    
    # Delete removed images from storage
    for removed_url in removed_images:
        try:
            filename = Path(removed_url).name
            file_path = UPLOAD_DIR / filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Warning: Could not delete file {filename}: {str(e)}")
    
    # Upload new images
    new_image_urls = []
    if images:
        for image in images:
            ext = Path(image.filename).suffix or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOAD_DIR / filename
            
            with filepath.open("wb") as f:
                shutil.copyfileobj(image.file, f)
            
            image_url =  f"{BASE_URL}/uploads/client_images/{filename}"
            new_image_urls.append(image_url)
    
    # Update fields
    allowed_fields = {
        'home_visible_from_street', 'exterior_lighting', 'surveillance_cameras',
        'motion_sensors_alarms', 'ground_floor_windows_accessible', 
        'bars_locks_reinforced_glass', 'gate_fence', 'obstruction_of_view', 'security_signage'
    }
    for field, value in update_data.items():
        if field in allowed_fields:
            setattr(record, field, value)
    
    # Final images = remaining + new
    record.images = remaining_images + new_image_urls
    record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(record)
    return record

@router.delete("/clients/{client_id}/google-street-view-records/{record_id}", tags=["Digital Recognition - Google Street View"])
def delete_google_street_view_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a Google Street View record"""
    record = db.query(ClientGoogleStreetViewRecord).filter(
        ClientGoogleStreetViewRecord.id == record_id,
        ClientGoogleStreetViewRecord.client_id == client_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.role == "Analyst" and record.client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete(record)
    db.commit()
    return {"message": "Record deleted successfully"}
