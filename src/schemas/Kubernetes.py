from typing import Any, Dict, Optional
from pydantic import BaseModel

class ObjectAddSchema(BaseModel):
    cluster_id: str
    kind: str

class ObjectSchema(BaseModel):
    kind: str
    cluster_id: str
    name: str
    namespace: str

class ExternalChart(BaseModel):
    name: str
    version: str
    repository: str

class DeploymentSchema(BaseModel):
    name: str
    description: str
    env_id: int
    cluster_id: int
    project_id: int
    args: Optional[Dict[str, Any]] = None