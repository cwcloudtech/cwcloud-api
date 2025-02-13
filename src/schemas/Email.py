from typing import Optional
from pydantic import BaseModel, Field, EmailStr

class AttachmentSchema(BaseModel):
    mime_type: str
    file_name: str
    b64: str

class EmailSchema(BaseModel):
    from_: Optional[EmailStr] = Field(None, alias="from")
    from_name: Optional[str] = None
    to: EmailStr
    cc: Optional[EmailStr] = None
    bcc: Optional[EmailStr] = None
    replyto: Optional[EmailStr] = None
    subject: str
    content: Optional[str] = None
    attachment: Optional[AttachmentSchema] = None

class EmailAdminSchema(BaseModel):
    from_: EmailStr = Field(..., alias = "from")
    from_name: Optional[str] = None
    to: EmailStr
    cc: Optional[EmailStr] = None
    bcc: Optional[EmailStr] = None
    replyto: Optional[EmailStr] = None
    subject: str
    content: Optional[str] = None
    attachment: Optional[AttachmentSchema] = None
    templated: Optional[bool] = False
