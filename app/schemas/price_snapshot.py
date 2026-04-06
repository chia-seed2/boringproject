from pydantic import BaseModel
from decimal import Decimal

class PriceSnapshotCreate(BaseModel):
    variant_id: str
    price: Decimal
    compare_at_price: Decimal | None = None
    currency: str = "EUR"
