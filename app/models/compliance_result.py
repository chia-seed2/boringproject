import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from app.db import Base


class ComplianceResult(Base):
    __tablename__ = "compliance_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    variant_id = Column(String, ForeignKey("product_variants.id"), nullable=False)
    lowest_30_day_price = Column(Numeric(10, 2), nullable=True)
    current_price = Column(Numeric(10, 2), nullable=True)
    compare_at_price = Column(Numeric(10, 2), nullable=True)
    status = Column(String, nullable=False)  # no_discount, compliant, violation, insufficient_data
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)