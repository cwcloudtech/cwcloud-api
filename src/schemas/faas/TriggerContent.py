from pydantic import BaseModel
from typing import List, Optional

from schemas.faas.InvocationArg import InvocationArgument

class TriggerContent(BaseModel):
    function_id: str
    name: str
    args: List[InvocationArgument]
    cron_expr: Optional[str] = None
    execution_time: Optional[str] = None
