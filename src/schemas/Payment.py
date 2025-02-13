from typing import Optional
from pydantic import BaseModel

class PaymentSchema(BaseModel):
    invoice_id: str
    voucher_id: Optional[str] = None

class PaymentRelaunchSchema(BaseModel):
    invoice_id: str
