from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone, date
from pathlib import Path
import uuid
import shutil
import os

from database import get_db
from models import (
    Client, ClientDonorRecord, ClientVoterRecord, ClientDVMRecord, 
    ClientGovRecord, User
)
from schemas import (
    DonorRecordCreate, DonorRecordUpdate, DonorRecordResponse,
    VoterRecordCreate, VoterRecordUpdate, VoterRecordResponse,
    DVMRecordCreate, DVMRecordUpdate, DVMRecordResponse,
    GovRecordCreate, GovRecordUpdate, GovRecordResponse
)
from users import get_current_user

router = APIRouter()

# Upload directory setup
UPLOAD_DIR = Path("uploads/client_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ==================== DONOR RECORD APIS ====================

@router.get("/clients/{client_id}/donor-records", response_model=List[DonorRecordResponse], tags=["Government Records - Donor"])
def get_client_donor_records(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all donor records for a client"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    donor_records = db.query(ClientDonorRecord).filter(
        ClientDonorRecord.client_id == client_id
    ).order_by(ClientDonorRecord.created_at.desc()).all()
    
    return donor_records

@router.post("/clients/{client_id}/donor-records", response_model=DonorRecordResponse, tags=["Government Records - Donor"])
def add_client_donor_record(
    client_id: uuid.UUID,
    donor_data: DonorRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a single donor record manually (no CSV file)"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate required fields
    if not donor_data.contributor_name or not donor_data.contributor_name.strip():
        raise HTTPException(status_code=400, detail="Contributor name is required")
    
    if not donor_data.recipient or not donor_data.recipient.strip():
        raise HTTPException(status_code=400, detail="Recipient is required")
    
    # Create new donor record (csv_file will be NULL)
    new_donor_record = ClientDonorRecord(
        client_id=client_id,
        contributor_name=donor_data.contributor_name,
        recipient=donor_data.recipient,
        recipient_date=donor_data.recipient_date,
        contribution_amount=donor_data.contribution_amount,
        csv_file=None
    )
    
    db.add(new_donor_record)
    db.commit()
    db.refresh(new_donor_record)
    
    return new_donor_record

@router.post("/clients/{client_id}/donor-records/csv-upload", tags=["Government Records - Donor"])
def upload_donor_csv(
    client_id: uuid.UUID,
    csv_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload CSV file - creates a record with CSV file path only"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not csv_file:
        raise HTTPException(status_code=400, detail="CSV file is required")
    
    # Save CSV file to disk
    file_extension = Path(csv_file.filename).suffix.lower() if csv_file.filename else ".csv"
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    csv_file_path = UPLOAD_DIR / unique_filename
    
    try:
        with csv_file_path.open("wb") as buffer:
            shutil.copyfileobj(csv_file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save CSV file: {str(e)}"
        )
    
    # Create complete CSV file URL
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    csv_file_url = f"{base_url}/uploads/client_images/{unique_filename}"
    
    # Create a record with just the CSV file
    new_record = ClientDonorRecord(
        client_id=client_id,
        contributor_name=None,
        recipient=None,
        recipient_date=None,
        contribution_amount=None,
        csv_file=csv_file_url
    )
    
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    return {
        "success": True,
        "message": "CSV file uploaded successfully",
        "record": {
            "id": str(new_record.id),
            "client_id": str(new_record.client_id),
            "contributor_name": new_record.contributor_name,
            "recipient": new_record.recipient,
            "recipient_date": new_record.recipient_date,
            "contribution_amount": new_record.contribution_amount,
            "csv_file": new_record.csv_file,
            "created_at": new_record.created_at.isoformat(),
            "updated_at": new_record.updated_at.isoformat()
        }
    }

@router.put("/clients/{client_id}/donor-records/{donor_id}", tags=["Government Records - Donor"])
def update_client_donor_record(
    client_id: uuid.UUID,
    donor_id: uuid.UUID,
    donor_data: DonorRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a donor record - works for both manual and CSV records"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    donor_record = db.query(ClientDonorRecord).filter(
        ClientDonorRecord.id == donor_id,
        ClientDonorRecord.client_id == client_id
    ).first()
    
    if not donor_record:
        raise HTTPException(status_code=404, detail="Donor record not found")
    
    # Update only the fields that are provided
    update_data = donor_data.model_dump(exclude_unset=True)
    updated = False
    
    for field, value in update_data.items():
        setattr(donor_record, field, value)
        updated = True
    
    if not updated:
        raise HTTPException(
            status_code=400,
            detail="No updates provided"
        )
    
    donor_record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(donor_record)
    
    return donor_record

@router.delete("/clients/{client_id}/donor-records/{donor_id}", tags=["Government Records - Donor"])
def delete_client_donor_record(
    client_id: uuid.UUID,
    donor_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a donor record and associated CSV file if exists"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    donor_record = db.query(ClientDonorRecord).filter(
        ClientDonorRecord.id == donor_id,
        ClientDonorRecord.client_id == client_id
    ).first()
    
    if not donor_record:
        raise HTTPException(status_code=404, detail="Donor record not found")
    
    # Delete CSV file if exists
    if donor_record.csv_file:
        try:
            filename = Path(donor_record.csv_file).name
            file_path = UPLOAD_DIR / filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Warning: Could not delete CSV file: {str(e)}")
    
    db.delete(donor_record)
    db.commit()
    
    return {"message": "Donor record deleted successfully"}

# ==================== VOTER RECORD APIS ====================

@router.get("/clients/{client_id}/voter-records", response_model=List[VoterRecordResponse], tags=["Government Records - Voter"])
def get_client_voter_records(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all voter records for a client"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    voter_records = db.query(ClientVoterRecord).filter(
        ClientVoterRecord.client_id == client_id
    ).order_by(ClientVoterRecord.created_at.desc()).all()
    
    return voter_records

@router.post("/clients/{client_id}/voter-records", response_model=VoterRecordResponse, tags=["Government Records - Voter"])
def add_client_voter_record(
    client_id: uuid.UUID,
    voter_data: VoterRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new voter record"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate required field
    if not voter_data.voter_record or not voter_data.voter_record.strip():
        raise HTTPException(status_code=400, detail="Voter record is required")
    
    # Create new voter record
    new_voter_record = ClientVoterRecord(
        client_id=client_id,
        voter_record=voter_data.voter_record
    )
    
    db.add(new_voter_record)
    db.commit()
    db.refresh(new_voter_record)
    
    return new_voter_record

@router.put("/clients/{client_id}/voter-records/{voter_id}", response_model=VoterRecordResponse, tags=["Government Records - Voter"])
def update_client_voter_record(
    client_id: uuid.UUID,
    voter_id: uuid.UUID,
    voter_data: VoterRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a voter record"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    voter_record = db.query(ClientVoterRecord).filter(
        ClientVoterRecord.id == voter_id,
        ClientVoterRecord.client_id == client_id
    ).first()
    
    if not voter_record:
        raise HTTPException(status_code=404, detail="Voter record not found")
    
    # Validate and update
    if not voter_data.voter_record or not voter_data.voter_record.strip():
        raise HTTPException(status_code=400, detail="Voter record cannot be empty")
    
    voter_record.voter_record = voter_data.voter_record
    voter_record.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(voter_record)
    
    return voter_record

@router.delete("/clients/{client_id}/voter-records/{voter_id}", tags=["Government Records - Voter"])
def delete_client_voter_record(
    client_id: uuid.UUID,
    voter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a voter record"""
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    voter_record = db.query(ClientVoterRecord).filter(
        ClientVoterRecord.id == voter_id,
        ClientVoterRecord.client_id == client_id
    ).first()
    
    if not voter_record:
        raise HTTPException(status_code=404, detail="Voter record not found")
    
    db.delete(voter_record)
    db.commit()
    
    return {"message": "Voter record deleted successfully"}

# ==================== DVM RECORD APIS ====================

@router.get("/clients/{client_id}/dvm-records", response_model=List[DVMRecordResponse], tags=["Government Records - DVM"])
def get_client_dvm_records(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all DVM records for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    dvm_records = db.query(ClientDVMRecord).filter(
        ClientDVMRecord.client_id == client_id
    ).order_by(ClientDVMRecord.created_at.desc()).all()

    return dvm_records

@router.post("/clients/{client_id}/dvm-records", response_model=DVMRecordResponse, tags=["Government Records - DVM"])
def add_client_dvm_record(
    client_id: uuid.UUID,
    dvm_data: DVMRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new DVM record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not dvm_data.dvm_record.strip():
        raise HTTPException(status_code=400, detail="DVM record is required")

    new_dvm_record = ClientDVMRecord(
        client_id=client_id,
        dvm_record=dvm_data.dvm_record
    )

    db.add(new_dvm_record)
    db.commit()
    db.refresh(new_dvm_record)

    return new_dvm_record

@router.put("/clients/{client_id}/dvm-records/{dvm_id}", response_model=DVMRecordResponse, tags=["Government Records - DVM"])
def update_client_dvm_record(
    client_id: uuid.UUID,
    dvm_id: uuid.UUID,
    dvm_data: DVMRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a DVM record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    dvm_record = db.query(ClientDVMRecord).filter(
        ClientDVMRecord.id == dvm_id,
        ClientDVMRecord.client_id == client_id
    ).first()

    if not dvm_record:
        raise HTTPException(status_code=404, detail="DVM record not found")

    if dvm_data.dvm_record and dvm_data.dvm_record.strip():
        dvm_record.dvm_record = dvm_data.dvm_record
        dvm_record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(dvm_record)
    else:
        raise HTTPException(status_code=400, detail="DVM record cannot be empty")

    return dvm_record

@router.delete("/clients/{client_id}/dvm-records/{dvm_id}", tags=["Government Records - DVM"])
def delete_client_dvm_record(
    client_id: uuid.UUID,
    dvm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a DVM record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    dvm_record = db.query(ClientDVMRecord).filter(
        ClientDVMRecord.id == dvm_id,
        ClientDVMRecord.client_id == client_id
    ).first()

    if not dvm_record:
        raise HTTPException(status_code=404, detail="DVM record not found")

    db.delete(dvm_record)
    db.commit()

    return {"message": "DVM record deleted successfully"}

# ==================== GOVERNMENT RECORD APIS ====================

@router.get("/clients/{client_id}/gov-records", response_model=List[GovRecordResponse], tags=["Government Records - General"])
def get_gov_records(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all government records for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    records = db.query(ClientGovRecord).filter(
        ClientGovRecord.client_id == client_id
    ).order_by(ClientGovRecord.created_at.desc()).all()

    return records

@router.post("/clients/{client_id}/gov-records", response_model=GovRecordResponse, tags=["Government Records - General"])
def add_gov_record(
    client_id: uuid.UUID,
    data: GovRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new government record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not data.record_type.strip() or not data.record.strip():
        raise HTTPException(status_code=400, detail="Both record_type and record are required")

    new_record = ClientGovRecord(
        client_id=client_id,
        record_type=data.record_type.strip(),
        record=data.record.strip()
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return new_record

@router.put("/clients/{client_id}/gov-records/{record_id}", response_model=GovRecordResponse, tags=["Government Records - General"])
def update_gov_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    data: GovRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a government record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(ClientGovRecord).filter(
        ClientGovRecord.id == record_id,
        ClientGovRecord.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Government record not found")

    update_fields = data.model_dump(exclude_unset=True)

    if not update_fields:
        raise HTTPException(status_code=400, detail="No updates provided")

    if "record_type" in update_fields and not update_fields["record_type"].strip():
        raise HTTPException(status_code=400, detail="record_type cannot be empty")

    if "record" in update_fields and not update_fields["record"].strip():
        raise HTTPException(status_code=400, detail="record cannot be empty")

    for field, value in update_fields.items():
        setattr(record, field, value)

    record.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(record)

    return record

@router.delete("/clients/{client_id}/gov-records/{record_id}", tags=["Government Records - General"])
def delete_gov_record(
    client_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a government record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(ClientGovRecord).filter(
        ClientGovRecord.id == record_id,
        ClientGovRecord.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Government record not found")

    db.delete(record)
    db.commit()

    return {"message": "Government record deleted successfully"}