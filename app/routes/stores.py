from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import distinct, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.price_snapshot import PriceSnapshot
from app.models.product import Product
from app.models.store import Store
from app.models.variant import Variant
from app.schemas.store import StoreCreate

router = APIRouter()


def start_of_today() -> datetime:
    return datetime.combine(datetime.utcnow().date(), time.min)


def serialize_store_with_info(db: Session, store: Store) -> dict:
    today_start = start_of_today()

    total_products = (
        db.query(func.count(Product.id))
        .filter(Product.store_id == store.id)
        .scalar()
        or 0
    )

    total_variants = (
        db.query(func.count(Variant.id))
        .join(Product, Variant.product_id == Product.id)
        .filter(Product.store_id == store.id)
        .scalar()
        or 0
    )

    total_snapshots = (
        db.query(func.count(PriceSnapshot.id))
        .join(Variant, PriceSnapshot.variant_id == Variant.id)
        .join(Product, Variant.product_id == Product.id)
        .filter(Product.store_id == store.id)
        .scalar()
        or 0
    )

    products_scanned_today = (
        db.query(func.count(distinct(Product.id)))
        .join(Variant, Variant.product_id == Product.id)
        .join(PriceSnapshot, PriceSnapshot.variant_id == Variant.id)
        .filter(
            Product.store_id == store.id,
            PriceSnapshot.captured_at >= today_start,
        )
        .scalar()
        or 0
    )

    snapshots_created_today = (
        db.query(func.count(PriceSnapshot.id))
        .join(Variant, PriceSnapshot.variant_id == Variant.id)
        .join(Product, Variant.product_id == Product.id)
        .filter(
            Product.store_id == store.id,
            PriceSnapshot.captured_at >= today_start,
        )
        .scalar()
        or 0
    )

    latest_scan_time = (
        db.query(func.max(PriceSnapshot.captured_at))
        .join(Variant, PriceSnapshot.variant_id == Variant.id)
        .join(Product, Variant.product_id == Product.id)
        .filter(Product.store_id == store.id)
        .scalar()
    )

    return {
        "id": store.id,
        "name": store.name,
        "platform": store.platform,
        "domain": store.domain,
        "created_at": store.created_at,
        "store_info": {
            "total_products": total_products,
            "total_variants": total_variants,
            "total_snapshots": total_snapshots,
            "products_scanned_today": products_scanned_today,
            "snapshots_created_today": snapshots_created_today,
            "latest_scan_time": latest_scan_time.isoformat() if latest_scan_time else None,
        },
    }


@router.post("/stores")
def create_store(payload: StoreCreate, db: Session = Depends(get_db)):
    store = Store(
        name=payload.name,
        platform=payload.platform,
        domain=payload.domain,
    )
    db.add(store)

    try:
        db.commit()
        db.refresh(store)
        return serialize_store_with_info(db, store)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="A store with that domain already exists.")


@router.get("/stores")
def list_stores(db: Session = Depends(get_db)):
    stores = db.query(Store).all()
    return [serialize_store_with_info(db, store) for store in stores]


@router.get("/stores/{store_id}")
def get_store(store_id: str, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")

    return serialize_store_with_info(db, store)


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
