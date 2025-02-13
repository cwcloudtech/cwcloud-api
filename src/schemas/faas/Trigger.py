from pydantic import BaseModel
from typing import Optional

from schemas.faas.TriggerContent import TriggerContent

class Trigger(BaseModel):
    kind: str
    owner_id: Optional[int] = None
    content: TriggerContent

class CompletedTrigger(Trigger):
    id: Optional[str] = None
    owner_username: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
