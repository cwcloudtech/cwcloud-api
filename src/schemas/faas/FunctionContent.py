from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class MQTTCertificates(BaseModel):
    iot_hub_certificate: Optional[str] = None
    device_certificate: Optional[str] = None
    device_key_certificate: Optional[str] = None

class CallbackContent(BaseModel):
    type: str = Field(examples=["http", "websocket", "mqtt"])
    endpoint: str
    token: Optional[str] = None
    client_id: Optional[str] = None
    user_data: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    port: Optional[str] = None
    subscription: Optional[str] = None
    qos: Optional[str] = None
    topic: Optional[str] = None
    certificates_are_required: bool = Field(default=False)
    certificates: Optional[MQTTCertificates] = None

class FunctionContent(BaseModel):
    code: str = Field(examples=['function foo(arg): {return "bar " + arg;}'])
    blockly: Optional[str] = None
    language: str = Field(examples=["javascript", "python", "go", "bash"])
    name: str
    args: List[str]
    callbacks: Optional[List[CallbackContent]] = None
    regexp: Optional[str] = None
    env: Optional[Dict[str, str]] = None
