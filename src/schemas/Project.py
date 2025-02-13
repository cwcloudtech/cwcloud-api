from typing import Optional, Literal
from pydantic import BaseModel, Field

class ProjectBaseSchema(BaseModel):
    name: str
    type: Optional[Literal['vm', 'k8s']] = Field('vm', description="Type of project (vm or k8s)")
    host: Optional[str] = None
    token: Optional[str] = None
    git_username: Optional[str] = None
    git_useremail: Optional[str] = None
    namespace: Optional[str] = None

class ProjectSchema(ProjectBaseSchema):
    pass

class ProjectAdminSchema(ProjectBaseSchema):
    email: str

class ProjectTransferSchema(BaseModel):
    email: str