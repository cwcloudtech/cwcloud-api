from pydantic import BaseModel
from typing import Optional

class UserAuthentication(BaseModel):
    is_authenticated: bool
    header_key: Optional[str] = None
    header_value: Optional[str] = None
