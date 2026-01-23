from typing import Optional
from pydantic import BaseModel

class ContactFormSchema(BaseModel):
    name: str
    mail_from: str
    mail_to: str
    copyright_name: Optional[str]
    logo_url: Optional[str]

class AdminContactFormSchema(ContactFormSchema):
    user_id: str

class ContactFormRequestSchema(BaseModel):
    id: str
    email: str
    subject: str
    message: str
    firstname: Optional[str] = ""
    name: Optional[str] = ""
    phone: Optional[str] = ""
