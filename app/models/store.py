import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db import Base

class Store(Base):
    __tablename__ = "stores"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    domain = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
