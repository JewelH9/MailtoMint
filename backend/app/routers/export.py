from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.invoice import Invoice
from app.models.user import User
from app.core.auth import get_current_user
from app.services.export_service import export_csv, export_excel, export_pdf

router = APIRouter()


def get_filtered_invoices(
    db: Session,
    user_id,
    category: Optional[str],
    status: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
):
    """Shared filter logic used by all three export formats."""
    query = db.query(Invoice).filter(Invoice.user_id == user_id)

    if category:
        query = query.filter(Invoice.category == category)
    if status:
        query = query.filter(Invoice.status == status)
    if date_from:
        try:
            query = query.filter(
                Invoice.created_at >= datetime.strptime(date_from, "%Y-%m-%d")
            )
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(
                Invoice.created_at <= datetime.strptime(date_to, "%Y-%m-%d")
            )
        except ValueError:
            pass

    return query.order_by(Invoice.created_at.desc()).all()


@router.get("/csv")
def download_csv(
    category: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoices = get_filtered_invoices(db, current_user.id, category, status, date_from, date_to)
    content = export_csv(invoices)

    filename = f"mailtomint_export_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/excel")
def download_excel(
    category: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoices = get_filtered_invoices(db, current_user.id, category, status, date_from, date_to)
    content = export_excel(invoices)

    filename = f"mailtomint_export_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/pdf")
def download_pdf(
    category: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoices = get_filtered_invoices(db, current_user.id, category, status, date_from, date_to)
    content = export_pdf(invoices, user_name=current_user.full_name)

    filename = f"mailtomint_report_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )