from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"

class MonitorType(str, Enum):
    HTTP = "http"
    TCP = "tcp"

class Header(BaseModel):
    name: str
    value: str
    
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

class BaseMonitorSchema(BaseModel):
    type: MonitorType = Field(..., description="Type of monitor (http or tcp)")
    name: str
    family: Optional[str] = None
    url: str = Field(..., description="URL to monitor")
    method: Optional[HttpMethod] = Field(default=HttpMethod.GET, description="HTTP method")
    expected_http_code: Optional[str] = Field(default='20*')
    body: Optional[str] = Field(None, description="Request body for POST/PUT requests")
    expected_contain: Optional[str] = Field(None, description="Expected content in the HTTP response body")
    timeout: int = Field(default=30, gt=0, le=300)
    username: Optional[str] = None
    password: Optional[str] = None
    headers: List[Header] = Field(default_factory=list, description="Optional headers for the HTTP request")
    callbacks: Optional[List[CallbackContent]] = Field(None, description="List of callbacks to be triggered on monitor failure")
    check_tls: Optional[bool] = Field(default=True, description="Check TLS certificate")
    level: Optional[str] = Field(default="DEBUG", description="Log Level (INFO or DEBUG)")

class MonitorSchema(BaseMonitorSchema):
    pass

class AdminMonitorSchema(BaseMonitorSchema):
    user_id: int
