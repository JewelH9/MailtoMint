from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
import shutil

from app.database import get_db
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.invoice import InvoiceResponse, InvoiceUpdate
from app.core.auth import get_current_user

from app.services.processing_pipeline import process_invoice
from app.database import SessionLocal

from app.core.file_validator import validate_file_content, sanitize_filename

def process_invoice_background(invoice_id: str, file_path: str):
    from app.database import SessionLocal
    from app.services.processing_pipeline import process_invoice
    db = SessionLocal()
    try:
        print(f"🔧 Background task started for {invoice_id}")
        process_invoice(invoice_id, file_path, db)
    except Exception as e:
        print(f"❌ Background task crashed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

router = APIRouter()

UPLOAD_DIR = "uploads"
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/jpg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def save_file_locally(file: UploadFile, user_id: str) -> tuple[str, str]:
    """
    Saves uploaded file to disk, returns (file_url, file_name).
    In production this would upload to Cloudinary instead.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{user_id}_{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return f"/uploads/{unique_name}", file.filename


@router.post("/upload", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def upload_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Sanitize filename first
    safe_filename = sanitize_filename(file.filename or "upload")

    # Check declared content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPG, and PNG files are allowed",
        )

    # Check file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB",
        )

    # Save file to disk
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_url, _ = save_file_locally(file, str(current_user.id))

    # Validate actual file content (not just the declared type)
    disk_path = os.path.join(UPLOAD_DIR, os.path.basename(file_url))
    is_valid, error = validate_file_content(disk_path)
    if not is_valid:
        # File already deleted inside validate_file_content if invalid
        raise HTTPException(status_code=400, detail=error)

    # Create invoice record
    invoice = Invoice(
        user_id=current_user.id,
        file_url=file_url,
        file_name=safe_filename,
        source="upload",
        status="pending",
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    background_tasks.add_task(
        process_invoice_background,
        str(invoice.id),
        disk_path,
    )

    return InvoiceResponse(
        id=invoice.id,
        vendor_name=invoice.vendor_name,
        invoice_number=invoice.invoice_number,
        total_amount=invoice.total_amount,
        tax_amount=invoice.tax_amount,
        currency=invoice.currency,
        invoice_date=invoice.invoice_date,
        category=invoice.category,
        source=invoice.source,
        status=invoice.status,
        fraud_score=invoice.fraud_score,
        is_duplicate=invoice.is_duplicate,
        is_flagged=invoice.is_flagged,
        file_url=invoice.file_url,
        file_name=invoice.file_name,
        ai_notes=invoice.ai_notes,
        created_at=invoice.created_at,
    )


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Invoice).filter(Invoice.user_id == current_user.id)

    if status:
        query = query.filter(Invoice.status == status)
    if category:
        query = query.filter(Invoice.category == category)

    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()

    return [
        InvoiceResponse(
            id=inv.id,
            vendor_name=inv.vendor_name,
            invoice_number=inv.invoice_number,
            total_amount=inv.total_amount,
            tax_amount=inv.tax_amount,
            currency=inv.currency,
            invoice_date=inv.invoice_date,
            category=inv.category,
            source=inv.source,
            status=inv.status,
            fraud_score=inv.fraud_score,
            is_duplicate=inv.is_duplicate,
            is_flagged=inv.is_flagged,
            file_url=inv.file_url,
            file_name=inv.file_name,
            ai_notes=inv.ai_notes,
            created_at=inv.created_at,
        )
        for inv in invoices
    ]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == uuid.UUID(invoice_id),
        Invoice.user_id == current_user.id,
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return InvoiceResponse(
        id=invoice.id,
        vendor_name=invoice.vendor_name,
        invoice_number=invoice.invoice_number,
        total_amount=invoice.total_amount,
        tax_amount=invoice.tax_amount,
        currency=invoice.currency,
        invoice_date=invoice.invoice_date,
        category=invoice.category,
        source=invoice.source,
        status=invoice.status,
        fraud_score=invoice.fraud_score,
        is_duplicate=invoice.is_duplicate,
        is_flagged=invoice.is_flagged,
        file_url=invoice.file_url,
        file_name=invoice.file_name,
        ai_notes=invoice.ai_notes,
        created_at=invoice.created_at,
    )


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == uuid.UUID(invoice_id),
        Invoice.user_id == current_user.id,
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Only update fields that were actually sent
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)

    db.commit()
    db.refresh(invoice)

    return InvoiceResponse(
        id=invoice.id,
        vendor_name=invoice.vendor_name,
        invoice_number=invoice.invoice_number,
        total_amount=invoice.total_amount,
        tax_amount=invoice.tax_amount,
        currency=invoice.currency,
        invoice_date=invoice.invoice_date,
        category=invoice.category,
        source=invoice.source,
        status=invoice.status,
        fraud_score=invoice.fraud_score,
        is_duplicate=invoice.is_duplicate,
        is_flagged=invoice.is_flagged,
        file_url=invoice.file_url,
        file_name=invoice.file_name,
        ai_notes=invoice.ai_notes,
        created_at=invoice.created_at,
    )


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == uuid.UUID(invoice_id),
        Invoice.user_id == current_user.id,
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Delete file from disk too
    if invoice.file_url:
        disk_path = invoice.file_url.lstrip("/")
        if os.path.exists(disk_path):
            os.remove(disk_path)

    db.delete(invoice)
    db.commit()