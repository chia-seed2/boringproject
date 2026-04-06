from pydantic import BaseModel

class ProductCreate(BaseModel):
    store_id: str
    external_id: str
    title: str
    handle: str | None = None
    url: str | None = None
    active: bool = True

class VariantCreate(BaseModel):
    product_id: str
    external_id: str
    sku: str | None = None
    title: str | None = None
