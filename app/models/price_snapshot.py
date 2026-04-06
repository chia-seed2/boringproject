import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from app.db import Base

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    variant_id = Column(String, ForeignKey("product_variants.id"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    compare_at_price = Column(Numeric(10, 2), nullable=True)
    currency = Column(String, nullable=False, default="EUR")
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
