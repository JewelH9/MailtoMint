from sqlalchemy.orm import Session
from app.models.invoice import Invoice
from thefuzz import fuzz
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID


# --- Scoring weights ---
# Each check contributes a portion to the final fraud score (0.0 - 1.0)
WEIGHTS = {
    "exact_duplicate":    0.95,  # same invoice number + same vendor = almost certainly fraud
    "fuzzy_duplicate":    0.70,  # very similar invoice = suspicious
    "amount_spike":       0.50,  # amount 3x higher than vendor average = suspicious
    "round_amount":       0.20,  # suspiciously round numbers (5000, 10000) = mild flag
    "rapid_resubmission": 0.60,  # same vendor, same amount within 24hrs = suspicious
}


def score_invoice(invoice: Invoice, all_invoices: list[Invoice]) -> dict:
    """
    Runs all fraud checks on a single invoice against the user's invoice history.
    Returns a score (0.0-1.0) and a list of triggered flags.
    """
    flags = []
    score = 0.0

    other_invoices = [inv for inv in all_invoices if str(inv.id) != str(invoice.id)]

    # --- Check 1: Exact duplicate ---
    # Same invoice number AND same vendor = definite duplicate
    if invoice.invoice_number and invoice.vendor_name:
        for other in other_invoices:
            if (
                other.invoice_number == invoice.invoice_number
                and other.vendor_name == invoice.vendor_name
            ):
                score = max(score, WEIGHTS["exact_duplicate"])
                flags.append({
                    "flag_type": "exact_duplicate",
                    "reason": f"Duplicate of invoice {other.invoice_number} from {other.vendor_name}",
                    "confidence": WEIGHTS["exact_duplicate"],
                })
                break

    # --- Check 2: Fuzzy duplicate ---
    # Very similar vendor name + very similar amount = likely duplicate
    if invoice.vendor_name and invoice.total_amount:
        for other in other_invoices:
            if not other.vendor_name or not other.total_amount:
                continue

            name_similarity = fuzz.ratio(
                invoice.vendor_name.lower(),
                other.vendor_name.lower()
            )
            amount_diff_pct = abs(invoice.total_amount - other.total_amount) / max(other.total_amount, 1)

            # 85%+ name match AND within 5% amount = fuzzy duplicate
            if name_similarity >= 85 and amount_diff_pct <= 0.05:
                score = max(score, WEIGHTS["fuzzy_duplicate"])
                flags.append({
                    "flag_type": "fuzzy_duplicate",
                    "reason": f"Very similar to invoice from {other.vendor_name} (₹{other.total_amount})",
                    "confidence": round(name_similarity / 100, 2),
                })
                break

    # --- Check 3: Amount spike ---
    # Invoice amount is 3x the average for this vendor = unusual
    if invoice.vendor_name and invoice.total_amount:
        vendor_invoices = [
            inv for inv in other_invoices
            if inv.vendor_name == invoice.vendor_name and inv.total_amount
        ]
        if len(vendor_invoices) >= 2:
            avg_amount = sum(inv.total_amount for inv in vendor_invoices) / len(vendor_invoices)
            if invoice.total_amount > avg_amount * 3:
                score = max(score, WEIGHTS["amount_spike"])
                flags.append({
                    "flag_type": "amount_spike",
                    "reason": f"Amount ₹{invoice.total_amount} is {invoice.total_amount/avg_amount:.1f}x the vendor average (₹{avg_amount:.0f})",
                    "confidence": WEIGHTS["amount_spike"],
                })

    # --- Check 4: Suspiciously round amount ---
    # Fraudulent invoices often use perfectly round numbers
    if invoice.total_amount and invoice.total_amount > 0:
        amount = invoice.total_amount
        if (
            amount >= 1000
            and amount % 1000 == 0
            and invoice.tax_amount in (None, 0)
        ):
            score = max(score, WEIGHTS["round_amount"])
            flags.append({
                "flag_type": "round_amount",
                "reason": f"Suspiciously round amount ₹{amount:.0f} with no tax breakdown",
                "confidence": WEIGHTS["round_amount"],
            })

    # --- Check 5: Rapid resubmission ---
    # Same vendor + same amount submitted within 24 hours
    if invoice.vendor_name and invoice.total_amount:
        cutoff = invoice.created_at - timedelta(hours=24)
        recent_similar = [
            inv for inv in other_invoices
            if (
                inv.vendor_name == invoice.vendor_name
                and inv.total_amount == invoice.total_amount
                and inv.created_at >= cutoff
            )
        ]
        if recent_similar:
            score = max(score, WEIGHTS["rapid_resubmission"])
            flags.append({
                "flag_type": "rapid_resubmission",
                "reason": f"Same amount from {invoice.vendor_name} submitted within 24 hours",
                "confidence": WEIGHTS["rapid_resubmission"],
            })

    return {
        "score": round(min(score, 1.0), 2),
        "flags": flags,
        "is_flagged": score >= 0.5,
    }


def run_fraud_check(invoice_id: str, db: Session):
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        return

    invoice = db.query(Invoice).filter(Invoice.id == invoice_uuid).first()
    if not invoice:
        return

    all_invoices = db.query(Invoice).filter(
        Invoice.user_id == invoice.user_id
    ).all()

    result = score_invoice(invoice, all_invoices)

    invoice.fraud_score = result["score"]
    invoice.is_flagged = result["is_flagged"]
    invoice.is_duplicate = any(
        f["flag_type"] in ("exact_duplicate", "fuzzy_duplicate")
        for f in result["flags"]
    )
    db.commit()

    if result["is_flagged"]:
        print(f"🚨 Invoice {invoice_id} flagged — score: {result['score']}")
        for flag in result["flags"]:
            print(f"   → {flag['flag_type']}: {flag['reason']}")
    else:
        print(f"✅ Fraud check clean — score: {result['score']}")

    return result