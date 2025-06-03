from pydantic import BaseModel
from typing import Optional

from schemas.faas.FunctionContent import FunctionContent

class BaseFunction(BaseModel):
    is_public: Optional[bool] = None
    is_protected: bool = False
    owner_id: Optional[int] = None
    content: FunctionContent

class Function(BaseFunction):
    id: Optional[str] = None
    owner_username: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
