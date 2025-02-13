from pydantic import BaseModel

class DataSchema(BaseModel):
    device_id: str
    content: str
