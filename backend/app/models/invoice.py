import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Boolean,
    DateTime, Date, Text, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Extracted invoice data
    vendor_name = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True)
    total_amount = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    currency = Column(String, default="INR")
    invoice_date = Column(Date, nullable=True)
    
    # Classification
    category = Column(String, nullable=True)   # travel, food, office, etc.
    
    # File info
    file_url = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    source = Column(String, default="upload")  # upload | email | api
    
    # AI outputs
    ocr_raw_text = Column(Text, nullable=True)
    fraud_score = Column(Float, default=0.0)   # 0.0 = clean, 1.0 = very suspicious
    ai_notes = Column(Text, nullable=True)     # AI-generated accounting notes
    
    # Flags
    is_duplicate = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    status = Column(String, default="pending")  # pending | processed | flagged
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="invoices")

    def __repr__(self):
        return f"<Invoice {self.invoice_number} from {self.vendor_name}>"