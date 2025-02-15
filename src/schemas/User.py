from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class UserSchema(BaseModel):
    email: str
    registration_number: str
    address: str
    company_name: str
    contact_info: str
    password: str
    is_admin: bool
    confirmed: Optional[bool] = False
    created_at: Optional[str] = datetime.now().isoformat()

    class config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class ListUserResponse(BaseModel):
    status: str
    results: int
    users: List[UserSchema]

class UserRegisterSchema(BaseModel):
    email: str
    password: str
    registration_number: Optional[str]
    address: Optional[str]
    company_name: Optional[str]
    contact_info: Optional[str]

class UserUpdatePasswordSchema(BaseModel):
    old_password: str
    new_password: str

class UserLoginSchema(BaseModel):
    email: str
    password: str

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class UserResponse(BaseModel):
    status: str
    user: UserSchema

class UserAdminUpdateRoleSchema(BaseModel):
    is_admin: bool = False

class EnabledFeatures(BaseModel):
    billable: Optional[bool] = True
    without_vat: Optional[bool] = False
    auto_pay: Optional[bool] = False
    daasapi: Optional[bool] = False
    emailapi: Optional[bool] = False
    cwaiapi: Optional[bool] = False
    faasapi: Optional[bool] = False
    disable_emails: Optional[bool] = False
    k8sapi: Optional[bool] = False
    iotapi: Optional[bool] = False
    monitorapi: Optional[bool] = False

class UserEmailUpdateSchema(BaseModel):
    email: str

class UserAdminUpdateSchema(BaseModel):
    email: str
    is_admin: Optional[bool] = False
    registration_number: Optional[str] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    contact_info: Optional[str] = None
    confirmed: Optional[bool] = True
    enabled_features: Optional[EnabledFeatures] = None

class UserAdminAddSchema(BaseModel):
    email: str
    password: str
    is_admin: bool = False
    registration_number: Optional[str] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    contact_info: Optional[str] = None
    st_customer_id: Optional[str] = None
    enabled_features: Optional[EnabledFeatures] = None
