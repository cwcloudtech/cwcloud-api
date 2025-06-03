from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel, validator

class StorageKVBaseRequest(BaseModel):
    ttl: Optional[int] = None
    payload: Union[Dict[str, Any], List[Any], Any]
    
    @validator('ttl')
    def validate_ttl(cls, v):
        if v is not None and v <= 0:
            raise ValueError('TTL must be a positive number of hours')
        return v

class StorageKVCreateRequest(StorageKVBaseRequest):
    key: str

class StorageKVUpdateRequest(StorageKVBaseRequest):
    pass
