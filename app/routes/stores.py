from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.models.store import Store
from app.models.product import Product
from app.models.variant import Variant
from app.models.price_snapshot import PriceSnapshot
from app.schemas.store import StoreCreate

router = APIRouter()


@router.post("/stores")
def create_store(payload: StoreCreate, db: Session = Depends(get_db)):
    store = Store(
        name=payload.name,
        platform=payload.platform,
        domain=payload.domain
    )
    db.add(store)

    try:
        db.commit()
        db.refresh(store)
        return store
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="A store with that domain already exists.")


@router.get("/stores")
def list_stores(db: Session = Depends(get_db)):
    return db.query(Store).all()


@router.delete("/stores/{store_id}")
def delete_store(store_id: str, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")

    products = db.query(Product).filter(Product.store_id == store_id).all()

    for product in products:
        variants = db.query(Variant).filter(Variant.product_id == product.id).all()

        for variant in variants:
            db.query(PriceSnapshot).filter(PriceSnapshot.variant_id == variant.id).delete()
            db.delete(variant)

        db.delete(product)

    db.delete(store)
    db.commit()

    return {"status": "deleted", "store_id": store_id}