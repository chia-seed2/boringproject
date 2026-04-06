from pydantic import BaseModel

class StoreCreate(BaseModel):
    name: str
    platform: str
    domain: str
