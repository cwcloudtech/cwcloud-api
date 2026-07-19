import re

from typing import List, Optional
from typing_extensions import Annotated
from pydantic import BaseModel, Field, EmailStr, BeforeValidator

def _split_emails(value):
    if value is None or isinstance(value, list):
        return value
    return [part.strip() for part in re.split(r"[;,]", str(value)) if part.strip()]

# Accepts a single email or a `,`/`;` separated list of emails (each trimmed) instead of a single EmailStr
EmailListStr = Annotated[List[EmailStr], BeforeValidator(_split_emails)]

class AttachmentSchema(BaseModel):
    mime_type: str
    file_name: str
    b64: str

class EmailSchema(BaseModel):
    from_: Optional[EmailStr] = Field(None, alias="from")
    from_name: Optional[str] = None
    to: EmailListStr
    cc: Optional[EmailListStr] = None
    bcc: Optional[EmailListStr] = None
    replyto: Optional[EmailStr] = None
    subject: str
    content: Optional[str] = None
    attachment: Optional[AttachmentSchema] = None
    attachments: Optional[List[AttachmentSchema]] = None

class EmailAdminSchema(BaseModel):
    from_: EmailStr = Field(..., alias = "from")
    from_name: Optional[str] = None
    to: EmailListStr
    cc: Optional[EmailListStr] = None
    bcc: Optional[EmailListStr] = None
    replyto: Optional[EmailStr] = None
    subject: str
    content: Optional[str] = None
    attachment: Optional[AttachmentSchema] = None
    attachments: Optional[List[AttachmentSchema]] = None
    templated: Optional[bool] = False
