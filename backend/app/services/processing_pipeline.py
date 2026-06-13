from sqlalchemy.orm import Session
from app.models.invoice import Invoice
from app.services.ocr_service import extract_text
from app.services.ai_service import parse_invoice_with_ai
from app.services.fraud_service import run_fraud_check
from datetime import datetime
from uuid import UUID


def process_invoice(invoice_id: str, file_path: str, db: Session):
    # SQLite stores UUIDs as strings — must convert before querying
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        print(f"❌ Invalid invoice ID: {invoice_id}")
        return

    invoice = db.query(Invoice).filter(Invoice.id == invoice_uuid).first()
    if not invoice:
        print(f"❌ Invoice {invoice_id} not found in DB")
        return

    try:
        # Step 1: OCR
        print(f"🔍 Running OCR on {file_path}...")
        raw_text = extract_text(file_path)
        invoice.ocr_raw_text = raw_text
        db.commit()

        if not raw_text.strip():
            print(f"⚠️  No text extracted from {file_path}")
            invoice.status = "processed"
            db.commit()
            run_fraud_check(invoice_id, db)
            return

        print(f"📄 Extracted {len(raw_text)} characters")

        # Step 2: AI parsing
        print(f"🤖 Parsing invoice with AI...")
        parsed = parse_invoice_with_ai(raw_text)
        print(f"📊 Parsed result: {parsed}")

        if parsed:
            if parsed.get("vendor_name"):
                invoice.vendor_name = str(parsed["vendor_name"])[:200]
            if parsed.get("invoice_number"):
                invoice.invoice_number = str(parsed["invoice_number"])[:100]
            if parsed.get("total_amount") is not None:
                try:
                    invoice.total_amount = float(parsed["total_amount"])
                except (ValueError, TypeError):
                    pass
            if parsed.get("tax_amount") is not None:
                try:
                    invoice.tax_amount = float(parsed["tax_amount"])
                except (ValueError, TypeError):
                    pass
            if parsed.get("currency"):
                invoice.currency = str(parsed["currency"])[:10]
            if parsed.get("invoice_date"):
                try:
                    invoice.invoice_date = datetime.strptime(
                        str(parsed["invoice_date"]), "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass
            if parsed.get("category"):
                invoice.category = str(parsed["category"])[:50]
            if parsed.get("ai_notes"):
                invoice.ai_notes = str(parsed["ai_notes"])[:500]

        invoice.status = "processed"
        db.commit()

        # Step 3: Fraud check
        print(f"🛡️  Running fraud check...")
        run_fraud_check(invoice_id, db)

        print(f"✅ Invoice {invoice_id} fully processed")

    except Exception as e:
        print(f"❌ Processing failed for {invoice_id}: {e}")
        import traceback
        traceback.print_exc()
        try:
            invoice.status = "processed"
            db.commit()
        except Exception:
            pass