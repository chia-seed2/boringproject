from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.product import Product
from app.models.variant import Variant
from app.models.store import Store
from app.schemas.product import ProductCreate, VariantCreate

router = APIRouter()

@router.post("/products")
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == payload.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")

    product = Product(
        store_id=payload.store_id,
        external_id=payload.external_id,
        title=payload.title,
        handle=payload.handle,
        url=payload.url,
        active=payload.active
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@router.post("/variants")
def create_variant(payload: VariantCreate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    variant = Variant(
        product_id=payload.product_id,
        external_id=payload.external_id,
        sku=payload.sku,
        title=payload.title
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant

@router.get("/variants")
def list_variants(db: Session = Depends(get_db)):
    return db.query(Variant).all()
