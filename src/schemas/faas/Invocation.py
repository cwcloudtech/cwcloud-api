from pydantic import BaseModel
from typing import Optional

from schemas.faas.InvocationContent import InvocationContent

class Invocation(BaseModel):
    invoker_id: Optional[int] = None
    content: InvocationContent

class CompletedInvocation(Invocation):
    id: Optional[str] = None
    invoker_username: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
