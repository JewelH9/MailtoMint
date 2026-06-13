from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional
import re

from app.database import get_db
from app.models.user import User
from app.models.invoice import Invoice
from app.core.auth import get_current_user
from app.core.security import verify_password, hash_password

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    full_name: str

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Must contain an uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Must contain a number")
        return v


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice_count = db.query(Invoice).filter(
        Invoice.user_id == current_user.id
    ).count()

    processed_count = db.query(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
    ).count()

    total_spend = db.query(Invoice).filter(
        Invoice.user_id == current_user.id,
    ).all()
    spend = sum(inv.total_amount or 0 for inv in total_spend)

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "unique_email_alias": current_user.unique_email_alias,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "stats": {
            "total_invoices": invoice_count,
            "processed_invoices": processed_count,
            "total_spend": round(spend, 2),
        }
    }


@router.patch("/profile")
def update_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.full_name = payload.full_name
    db.commit()
    db.refresh(current_user)

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "unique_email_alias": current_user.unique_email_alias,
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current password before allowing change
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/check-email")
def trigger_email_check(
    current_user: User = Depends(get_current_user),
):
    """
    Manually triggers an inbox poll.
    Useful for testing without waiting 5 minutes.
    """
    from app.services.email_worker import poll_inbox_once
    from app.config import get_settings

    settings = get_settings()
    created = poll_inbox_once(settings)

    return {
        "message": f"Inbox checked — {created} new invoice(s) created",
        "invoices_created": created,
    }


@router.delete("/account")
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Delete all invoices first (cascade should handle this
    # but we do it explicitly for safety)
    db.query(Invoice).filter(Invoice.user_id == current_user.id).delete()
    db.delete(current_user)
    db.commit()

    return {"message": "Account deleted"}
