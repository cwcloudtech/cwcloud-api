from pydantic import BaseModel
from typing import List, Optional
from schemas.UserAuthentication import UserAuthentication

from schemas.faas.InvocationArg import InvocationArgument

class InvocationContent(BaseModel):
    function_id: str
    args: List[InvocationArgument]
    state: Optional[str] = None
    result: Optional[str] = None
    user_id: Optional[str] = None
    user_auth: Optional[UserAuthentication] = None
