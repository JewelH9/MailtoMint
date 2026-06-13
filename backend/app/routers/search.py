from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional
from datetime import datetime
import re

from app.database import get_db
from app.models.invoice import Invoice
from app.models.user import User
from app.core.auth import get_current_user

from app.core.sanitizer import sanitize_search_query

router = APIRouter()


def parse_natural_query(query: str) -> dict:
    """
    Parses a natural language query into structured filters.
    Examples:
      "Amazon bills from March"     → vendor=Amazon, month=3
      "Travel expenses above 5000"  → category=travel, min_amount=5000
      "GST invoices from Flipkart"  → vendor=Flipkart
      "food bills last month"       → category=food, relative=last_month
    """
    filters = {}
    q = query.lower().strip()

    # --- Amount filters ---
    # "above 5000", "over 5000", "more than 5000"
    above_match = re.search(r"(?:above|over|more than|greater than)\s*₹?\s*(\d+)", q)
    if above_match:
        filters["min_amount"] = float(above_match.group(1))

    # "below 1000", "under 1000", "less than 1000"
    below_match = re.search(r"(?:below|under|less than)\s*₹?\s*(\d+)", q)
    if below_match:
        filters["max_amount"] = float(below_match.group(1))

    # --- Month filters ---
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    for month_name, month_num in months.items():
        if month_name in q:
            filters["month"] = month_num
            break

    # "this month", "last month"
    if "this month" in q:
        filters["month"] = datetime.utcnow().month
        filters["year"] = datetime.utcnow().year
    elif "last month" in q:
        now = datetime.utcnow()
        if now.month == 1:
            filters["month"] = 12
            filters["year"] = now.year - 1
        else:
            filters["month"] = now.month - 1
            filters["year"] = now.year

    # --- Category filters ---
    categories = ["travel", "food", "office", "utilities", "marketing", "healthcare", "subscription"]
    for cat in categories:
        if cat in q:
            filters["category"] = cat
            break

    # --- Status filters ---
    if "flagged" in q or "suspicious" in q or "fraud" in q:
        filters["is_flagged"] = True
    if "duplicate" in q:
        filters["is_duplicate"] = True
    if "pending" in q:
        filters["status"] = "pending"
    if "processed" in q:
        filters["status"] = "processed"

    # --- Vendor extraction ---
    # Remove known keywords to extract vendor name
    stop_words = {
        "bills", "invoices", "invoice", "from", "above", "below", "over",
        "under", "more", "than", "less", "this", "last", "month", "year",
        "expenses", "expense", "flagged", "duplicate", "pending", "processed",
        "gst", "tax", "all", "show", "me", "find", "get", "the", "and",
        *categories,
        *months.keys(),
    }
    # Also remove amount patterns
    cleaned = re.sub(r"(?:above|over|more than|below|under|less than)\s*₹?\s*\d+", "", q)
    words = [w.strip(".,") for w in cleaned.split() if w.strip(".,") not in stop_words and len(w) > 2]

    if words:
        # Remaining words are likely vendor name fragments
        filters["vendor_hint"] = " ".join(words)

    return filters


@router.get("")
def search_invoices(
    q: str = Query(default="", description="Natural language search query"),
    vendor: Optional[str] = None,
    category: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    status: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_query = db.query(Invoice).filter(Invoice.user_id == current_user.id)
    q = sanitize_search_query(q)

    # Parse natural language if provided
    if q:
        parsed = parse_natural_query(q)
        # Explicit params override parsed ones
        if not min_amount and "min_amount" in parsed:
            min_amount = parsed["min_amount"]
        if not max_amount and "max_amount" in parsed:
            max_amount = parsed["max_amount"]
        if not category and "category" in parsed:
            category = parsed["category"]
        if not month and "month" in parsed:
            month = parsed["month"]
        if not year and "year" in parsed:
            year = parsed["year"]
        if not status and "status" in parsed:
            status = parsed["status"]
        if "is_flagged" in parsed:
            base_query = base_query.filter(Invoice.is_flagged == True)
        if "is_duplicate" in parsed:
            base_query = base_query.filter(Invoice.is_duplicate == True)

        # Vendor hint — search vendor name and file name
        vendor_hint = parsed.get("vendor_hint") or (vendor if vendor else None)
        if vendor_hint:
            base_query = base_query.filter(
                or_(
                    Invoice.vendor_name.ilike(f"%{vendor_hint}%"),
                    Invoice.file_name.ilike(f"%{vendor_hint}%"),
                    Invoice.invoice_number.ilike(f"%{vendor_hint}%"),
                    Invoice.category.ilike(f"%{vendor_hint}%"),
                )
            )
    elif vendor:
        base_query = base_query.filter(Invoice.vendor_name.ilike(f"%{vendor}%"))

    # Apply remaining filters
    if category:
        base_query = base_query.filter(Invoice.category == category)
    if min_amount is not None:
        base_query = base_query.filter(Invoice.total_amount >= min_amount)
    if max_amount is not None:
        base_query = base_query.filter(Invoice.total_amount <= max_amount)
    if status:
        base_query = base_query.filter(Invoice.status == status)
    if month:
        # SQLite uses strftime, PostgreSQL uses extract — handle both
        from sqlalchemy import func
        base_query = base_query.filter(
            func.strftime("%m", Invoice.created_at) == f"{month:02d}"
        )
    if year:
        from sqlalchemy import func
        base_query = base_query.filter(
            func.strftime("%Y", Invoice.created_at) == str(year)
        )

    results = base_query.order_by(Invoice.created_at.desc()).limit(50).all()

    return [
        {
            "id": str(inv.id),
            "vendor_name": inv.vendor_name,
            "invoice_number": inv.invoice_number,
            "total_amount": inv.total_amount,
            "currency": inv.currency,
            "category": inv.category,
            "status": inv.status,
            "fraud_score": inv.fraud_score,
            "is_flagged": inv.is_flagged,
            "is_duplicate": inv.is_duplicate,
            "file_name": inv.file_name,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "created_at": inv.created_at.isoformat(),
        }
        for inv in results
    ]