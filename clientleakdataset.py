from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from models import Client, ClientLeakedDataset, User
from schemas import LeakedDatasetResponse
from users import get_current_user

router = APIRouter()

@router.get("/clients/{client_id}/leaked-datasets", response_model=List[LeakedDatasetResponse], tags=["Leaked Datasets"])
def get_leaked_datasets(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get leaked datasets for a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(ClientLeakedDataset).filter(
        ClientLeakedDataset.client_id == client_id
    ).order_by(ClientLeakedDataset.created_at.desc()).all()

@router.delete("/clients/{client_id}/leaked-datasets/{dataset_id}", tags=["Leaked Datasets"])
def delete_leaked_dataset(
    client_id: uuid.UUID,
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete leaked dataset record"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(ClientLeakedDataset).filter(
        ClientLeakedDataset.id == dataset_id,
        ClientLeakedDataset.client_id == client_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Leaked dataset not found")

    db.delete(record)
    db.commit()

    return {"message": "Leaked dataset deleted successfully"}