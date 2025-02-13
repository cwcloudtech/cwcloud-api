from typing import Optional
from pydantic import BaseModel

class SupportTicketSchema(BaseModel):
    product: str
    severity: str
    subject: str
    message: str
    
class AdminSupportTicketSchema(BaseModel):
    email: str
    product: str
    severity: str
    subject: str
    message: str

class SupportTicketReplySchema(BaseModel):
    status: Optional[str] = None
    message: str
