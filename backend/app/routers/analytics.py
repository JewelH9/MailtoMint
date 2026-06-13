from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, date
from collections import defaultdict

from app.database import get_db
from app.models.invoice import Invoice
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter()


@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoices = db.query(Invoice).filter(Invoice.user_id == current_user.id).all()

    total_invoices = len(invoices)
    total_spend = sum(inv.total_amount or 0 for inv in invoices)
    flagged_count = sum(1 for inv in invoices if inv.is_flagged)
    processed_count = sum(1 for inv in invoices if inv.status == "processed")

    # This month's spend
    now = datetime.utcnow()
    this_month_spend = sum(
        inv.total_amount or 0
        for inv in invoices
        if inv.created_at.month == now.month and inv.created_at.year == now.year
    )

    # Top vendor by total spend
    vendor_spend = defaultdict(float)
    for inv in invoices:
        if inv.vendor_name and inv.total_amount:
            vendor_spend[inv.vendor_name] += inv.total_amount
    top_vendor = max(vendor_spend, key=vendor_spend.get) if vendor_spend else None

    return {
        "total_invoices": total_invoices,
        "total_spend": round(total_spend, 2),
        "flagged_count": flagged_count,
        "processed_count": processed_count,
        "this_month_spend": round(this_month_spend, 2),
        "top_vendor": top_vendor,
    }


@router.get("/monthly")
def get_monthly_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoices = db.query(Invoice).filter(Invoice.user_id == current_user.id).all()

    monthly = defaultdict(float)
    for inv in invoices:
        if inv.total_amount:
            key = inv.created_at.strftime("%b %Y")
            monthly[key] += inv.total_amount

    # Sort by date
    sorted_months = sorted(monthly.keys(), key=lambda x: datetime.strptime(x, "%b %Y"))

    return [
        {"month": month, "amount": round(monthly[month], 2)}
        for month in sorted_months
    ]


@router.get("/categories")
def get_category_breakdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoices = db.query(Invoice).filter(Invoice.user_id == current_user.id).all()

    category_data = defaultdict(float)
    for inv in invoices:
        cat = inv.category or "uncategorized"
        category_data[cat] += inv.total_amount or 0

    return [
        {"category": cat, "amount": round(amount, 2)}
        for cat, amount in sorted(category_data.items(), key=lambda x: x[1], reverse=True)
    ]


@router.get("/vendors")
def get_top_vendors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoices = db.query(Invoice).filter(Invoice.user_id == current_user.id).all()

    vendor_data = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for inv in invoices:
        if inv.vendor_name:
            vendor_data[inv.vendor_name]["amount"] += inv.total_amount or 0
            vendor_data[inv.vendor_name]["count"] += 1

    sorted_vendors = sorted(
        vendor_data.items(), key=lambda x: x[1]["amount"], reverse=True
    )[:10]

    return [
        {
            "vendor": name,
            "amount": round(data["amount"], 2),
            "count": data["count"],
        }
        for name, data in sorted_vendors
    ]


@router.get("/insights")
def get_ai_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoices = db.query(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
    ).all()

    if not invoices:
        return {"insights": "Upload and process some invoices to get AI insights."}

    # Build a summary to send to Gemini
    summary_lines = []
    for inv in invoices[:20]:  # limit to last 20 to stay within token limits
        summary_lines.append(
            f"- {inv.vendor_name or 'Unknown'}: ₹{inv.total_amount or 0} "
            f"({inv.category or 'uncategorized'}) on {inv.created_at.strftime('%d %b %Y')}"
        )

    summary = "\n".join(summary_lines)

    try:
        from app.services.ai_service import generate_insights
        insights = generate_insights(summary)
        return {"insights": insights}
    except Exception:
        return {"insights": "Insights unavailable right now."}