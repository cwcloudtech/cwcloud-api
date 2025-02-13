from typing import Optional
from pydantic import BaseModel

class RegistrySchema(BaseModel):
    name: str
    email: str
    type: str


class RegistryUpdateSchema(BaseModel):
    email: Optional[str] = None
    update_creds: Optional[bool] = False
