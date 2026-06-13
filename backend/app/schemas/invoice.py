from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime
import uuid


class InvoiceResponse(BaseModel):
    id: str
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    currency: str = "INR"
    invoice_date: Optional[date] = None
    category: Optional[str] = None
    source: str
    status: str
    fraud_score: float = 0.0
    is_duplicate: bool = False
    is_flagged: bool = False
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    ai_notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v):
        return str(v)


class InvoiceUpdate(BaseModel):
    vendor_name: Optional[str] = None
    category: Optional[str] = None
    total_amount: Optional[float] = None
    invoice_date: Optional[date] = None
    currency: Optional[str] = None
    status: Optional[str] = None