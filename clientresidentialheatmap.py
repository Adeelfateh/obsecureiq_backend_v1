from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from pathlib import Path
import uuid
import shutil
import os

from database import get_db
from models import Client, ClientResidentialHeatmapImage, User
from schemas import ResidentialHeatmapImageResponse
from users import get_current_user

router = APIRouter()

# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/clients/{client_id}/residential-heatmap-images", response_model=List[ResidentialHeatmapImageResponse], tags=["Client Residential & Heatmap"])
def get_client_residential_heatmap_images(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all residential and heatmap images for a client"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    images = db.query(ClientResidentialHeatmapImage).filter(
        ClientResidentialHeatmapImage.client_id == client_id
    ).order_by(ClientResidentialHeatmapImage.created_at.desc()).all()
    
    return images

@router.post("/clients/{client_id}/residential-heatmap-images", tags=["Client Residential & Heatmap"])
def upload_client_residential_heatmap_images(
    client_id: uuid.UUID,
    image_type: str = Form(...),  # Required - from dropdown
    images: List[UploadFile] = File(...),  # Multiple image files
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload multiple residential/heatmap images for a client"""
    
    # Check if client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check access rights
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate image_type
    if not image_type or not image_type.strip():
        raise HTTPException(status_code=400, detail="Image type is required")
    
    # Validate that at least one image is uploaded
    if not images or len(images) == 0:
        raise HTTPException(status_code=400, detail="At least one image is required")
    
    uploaded_images = []
    
    for image in images:
        # Get file extension (keep original extension)
        file_extension = Path(image.filename).suffix.lower() if image.filename else ".jpg"
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save file to disk
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save image {image.filename}: {str(e)}"
            )
        
        # Create complete image URL for database
        base_url = os.getenv("BASE_URL")
        image_url = f"{base_url}/uploads/client_images/{unique_filename}"
        
        # Create database record for each image
        new_image = ClientResidentialHeatmapImage(
            client_id=client_id,
            image_type=image_type,
            image_url=image_url
        )
        
        db.add(new_image)
        db.flush()  # Get the ID without committing yet
        
        uploaded_images.append({
            "id": str(new_image.id),
            "client_id": str(client_id),
            "image_type": image_type,
            "image_url": image_url,
            "original_filename": image.filename,
            "created_at": new_image.created_at.isoformat()
        })
    
    # Commit all records at once
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully uploaded {len(uploaded_images)} image(s)",
        "images": uploaded_images
    }

@router.put("/clients/{client_id}/residential-heatmap-images/{image_id}", tags=["Client Residential & Heatmap"])
def update_client_residential_heatmap_image(
    client_id: uuid.UUID,
    image_id: uuid.UUID,
    image_type: str = Form(None),  # Optional - update image type
    image: UploadFile = File(None),  # Optional - replace image file
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update image type or replace image file"""
    
    # Check if client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check access rights
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get existing image record
    image_record = db.query(ClientResidentialHeatmapImage).filter(
        ClientResidentialHeatmapImage.id == image_id,
        ClientResidentialHeatmapImage.client_id == client_id
    ).first()
    
    if not image_record:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Track if anything was updated
    updated = False
    old_image_url = image_record.image_url
    
    # Update image_type if provided
    if image_type is not None and image_type.strip():
        image_record.image_type = image_type
        updated = True
    
    # Replace image file if provided
    if image is not None:
        # Get file extension (keep original extension)
        file_extension = Path(image.filename).suffix.lower() if image.filename else ".jpg"
        
        # Generate new unique filename
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        new_file_path = UPLOAD_DIR / unique_filename
        
        # Save new file to disk
        try:
            with new_file_path.open("wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save new image: {str(e)}"
            )
        
        # Update image URL in database with complete URL
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        new_image_url = f"{base_url}/uploads/client_images/{unique_filename}"
        image_record.image_url = new_image_url
        updated = True
        
        # Delete old physical file (after new file is saved successfully)
        try:
            old_filename = Path(old_image_url).name
            old_file_path = UPLOAD_DIR / old_filename
            if old_file_path.exists():
                old_file_path.unlink()
        except Exception as e:
            print(f"Warning: Could not delete old file: {str(e)}")
    
    # Check if anything was actually updated
    if not updated:
        raise HTTPException(
            status_code=400,
            detail="No updates provided. Please provide image_type or image file to update."
        )
    
    # Update timestamp
    image_record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(image_record)
    
    return {
        "success": True,
        "message": "Image updated successfully",
        "image": {
            "id": str(image_record.id),
            "client_id": str(image_record.client_id),
            "image_type": image_record.image_type,
            "image_url": image_record.image_url,
            "created_at": image_record.created_at.isoformat(),
            "updated_at": image_record.updated_at.isoformat()
        }
    }

@router.delete("/clients/{client_id}/residential-heatmap-images/{image_id}", tags=["Client Residential & Heatmap"])
def delete_client_residential_heatmap_image(
    client_id: uuid.UUID,
    image_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a residential/heatmap image"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    image_record = db.query(ClientResidentialHeatmapImage).filter(
        ClientResidentialHeatmapImage.id == image_id,
        ClientResidentialHeatmapImage.client_id == client_id
    ).first()
    
    if not image_record:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete physical file from disk
    try:
        filename = Path(image_record.image_url).name
        file_path = UPLOAD_DIR / filename
        
        if file_path.exists():
            file_path.unlink()  # Delete the file
    except Exception as e:
        print(f"Warning: Could not delete physical file: {str(e)}")
        # Continue anyway - delete from database even if file deletion fails
    
    # Delete from database
    db.delete(image_record)
    db.commit()
    
    return {"message": "Image deleted successfully"}