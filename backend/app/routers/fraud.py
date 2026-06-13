from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.invoice import Invoice
from app.models.user import User
from app.core.auth import get_current_user
from app.services.fraud_service import run_fraud_check, score_invoice

router = APIRouter()


@router.get("/flags")
def get_flagged_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    flagged = db.query(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.is_flagged == True,
    ).order_by(Invoice.fraud_score.desc()).all()

    return [
        {
            "id": str(inv.id),
            "vendor_name": inv.vendor_name,
            "invoice_number": inv.invoice_number,
            "total_amount": inv.total_amount,
            "fraud_score": inv.fraud_score,
            "is_duplicate": inv.is_duplicate,
            "file_name": inv.file_name,
            "created_at": inv.created_at.isoformat(),
        }
        for inv in flagged
    ]


@router.get("/summary")
def get_fraud_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    all_invoices = db.query(Invoice).filter(
        Invoice.user_id == current_user.id
    ).all()

    total = len(all_invoices)
    flagged = sum(1 for inv in all_invoices if inv.is_flagged)
    duplicates = sum(1 for inv in all_invoices if inv.is_duplicate)
    high_risk = sum(1 for inv in all_invoices if inv.fraud_score >= 0.7)
    avg_score = (
        sum(inv.fraud_score for inv in all_invoices) / total
        if total > 0 else 0.0
    )

    return {
        "total_invoices": total,
        "flagged_count": flagged,
        "duplicate_count": duplicates,
        "high_risk_count": high_risk,
        "average_fraud_score": round(avg_score, 3),
        "flag_rate_pct": round((flagged / total * 100) if total > 0 else 0, 1),
    }


@router.post("/recheck/{invoice_id}")
def recheck_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger fraud re-check on a specific invoice."""
    result = run_fraud_check(invoice_id, db)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Invoice not found")
    return result