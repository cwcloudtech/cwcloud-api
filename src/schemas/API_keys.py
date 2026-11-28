from pydantic import BaseModel

class ApiKeysSchema(BaseModel):
    name: str

class ApiKeysAdminSchema(ApiKeysSchema):
    #? the user the key is created for
    email: str

class ApiKeysVerificationSchema(BaseModel):
    access_key: str
    secret_key: str
