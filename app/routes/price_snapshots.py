from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.variant import Variant
from app.models.price_snapshot import PriceSnapshot
from app.schemas.price_snapshot import PriceSnapshotCreate

router = APIRouter()

@router.post("/price-snapshots")
def create_price_snapshot(payload: PriceSnapshotCreate, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == payload.variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found.")

    snapshot = PriceSnapshot(
        variant_id=payload.variant_id,
        price=payload.price,
        compare_at_price=payload.compare_at_price,
        currency=payload.currency
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot

@router.get("/price-snapshots")
def list_price_snapshots(db: Session = Depends(get_db)):
    return db.query(PriceSnapshot).all()
