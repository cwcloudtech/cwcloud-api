from typing import Literal, Optional

from pydantic import BaseModel, NonNegativeInt


class DnsRecordSchema(BaseModel):
    record_name: str
    dns_zone: str
    type: Literal["A", "AAAA", "NS", "CNAME", "DNAME", "TXT"]
    ttl: NonNegativeInt
    data: Optional[str] = ""
 
class DnsDeleteSchema(BaseModel):
    id: str
    record_name: str
    dns_zone: str
