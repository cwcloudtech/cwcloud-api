from typing import Optional
from pydantic import BaseModel

class BucketSchema(BaseModel):
    name: str
    email: str
    type: str

class BucketUpdateSchema(BaseModel):
    email: Optional[str] = None
    update_creds: Optional[bool] = None
