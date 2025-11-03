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

class PodLogsSchema(BaseModel):
    cluster_id: int
    pod_name: str
    namespace: str
    container_name: Optional[str] = None
    tail_lines: Optional[int] = 100
    follow: Optional[bool] = False

class PodTerminalSchema(BaseModel):
    cluster_id: int
    pod_name: str
    namespace: str
    container_name: Optional[str] = None

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