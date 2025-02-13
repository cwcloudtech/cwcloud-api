import os

from typing import Any, Dict, Optional
from pydantic import BaseModel

from utils.dns_zones import get_first_dns_zone_doc
from utils.provider import get_provider_infos

DEFAULT_PROVIDER = os.getenv('DEFAULT_PROVIDER', 'scaleway')

class InstanceUpdateSchema(BaseModel):
    status: Optional[str] = None
    is_protected: Optional[bool] = False

class InstanceAttachSchema(BaseModel):
    name: str = "Instance Name"
    type: str = get_provider_infos(DEFAULT_PROVIDER, 'instance_types')[0]
    debug: Optional[bool] = True

class InstanceProvisionSchema(BaseModel):
    name: str = "Instance Name"
    email: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    project_url: Optional[str] = None
    debug: Optional[str] = None
    type: str = get_provider_infos(DEFAULT_PROVIDER, 'instance_types')[0]
    root_dns_zone: str = get_first_dns_zone_doc()
    args: Optional[Dict[str, Any]] = None
