import imaplib
import email
import os
import uuid
import time
import threading
from email.header import decode_header
from datetime import datetime

from app.database import SessionLocal
from app.models.user import User
from app.models.invoice import Invoice


UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def decode_str(value: str) -> str:
    """Decode encoded email headers like =?utf-8?b?...?="""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            result.append(str(part))
    return " ".join(result)


def extract_attachments(msg) -> list[dict]:
    """
    Walks through a MIME email and pulls out all valid attachments.
    Returns list of {"filename": str, "data": bytes}
    """
    attachments = []

    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition", ""))

        # Only process attachments, skip inline content
        if "attachment" not in content_disposition:
            continue

        filename = part.get_filename()
        if not filename:
            continue

        filename = decode_str(filename)
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            print(f"📎 Skipping {filename} — unsupported type")
            continue

        data = part.get_payload(decode=True)
        if not data:
            continue

        attachments.append({"filename": filename, "data": data})

    return attachments


def save_attachment(data: bytes, filename: str, user_id: str) -> tuple[str, str]:
    """Save attachment bytes to disk. Returns (file_url, saved_filename)."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{user_id}_{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(save_path, "wb") as f:
        f.write(data)

    return f"/uploads/{unique_name}", filename


def find_user_by_alias(alias_email: str, db) -> User | None:
    """
    The TO address of the email should match a user's unique_email_alias.
    e.g. raj-a3f9@mailtomint.io → find the user with that alias.
    """
    alias_local = alias_email.split("@")[0].lower()

    users = db.query(User).filter(User.is_active == True).all()
    for user in users:
        if user.unique_email_alias:
            user_local = user.unique_email_alias.split("@")[0].lower()
            if user_local == alias_local:
                return user

    return None


def process_email_message(msg, db) -> int:
    """
    Processes a single email message.
    Returns the number of invoices created.
    """
    from app.services.processing_pipeline import process_invoice

    # Extract TO addresses to identify the target user
    to_header = decode_str(msg.get("To", ""))
    from_header = decode_str(msg.get("From", ""))
    subject = decode_str(msg.get("Subject", "(no subject)"))

    print(f"📧 Processing email from {from_header}: '{subject}'")

    # Parse all TO addresses
    to_addresses = [addr.strip().lower() for addr in to_header.split(",")]

    target_user = None
    for addr in to_addresses:
        # Strip display name if present: "Raj <raj@x.com>" → "raj@x.com"
        if "<" in addr:
            addr = addr.split("<")[1].rstrip(">")
        user = find_user_by_alias(addr, db)
        if user:
            target_user = user
            break

    if not target_user:
        print(f"⚠️  No user found for addresses: {to_addresses}")
        return 0

    print(f"✅ Matched email to user: {target_user.email}")

    attachments = extract_attachments(msg)
    if not attachments:
        print(f"📭 No valid attachments in email from {from_header}")
        return 0

    created = 0
    for attachment in attachments:
        try:
            file_url, file_name = save_attachment(
                attachment["data"],
                attachment["filename"],
                str(target_user.id),
            )

            # Create invoice record
            invoice = Invoice(
                user_id=target_user.id,
                file_url=file_url,
                file_name=file_name,
                source="email",
                status="pending",
            )
            db.add(invoice)
            db.commit()
            db.refresh(invoice)

            print(f"📄 Created invoice for {file_name} — running pipeline...")

            # Run OCR + AI + Fraud
            disk_path = os.path.join(UPLOAD_DIR, os.path.basename(file_url))
            process_invoice(str(invoice.id), disk_path, db)

            created += 1

        except Exception as e:
            print(f"❌ Failed to process attachment {attachment['filename']}: {e}")
            db.rollback()

    return created


def poll_inbox_once(settings) -> int:
    """
    Connects to IMAP, checks for unread emails, processes them.
    Returns total invoices created in this poll cycle.
    """
    if not settings.imap_email or not settings.imap_password:
        print("⚠️  IMAP credentials not configured — skipping email poll")
        return 0

    total_created = 0

    try:
        print(f"📬 Polling inbox: {settings.imap_email}...")

        # Connect over SSL
        mail = imaplib.IMAP4_SSL(settings.imap_server, settings.imap_port)
        mail.login(settings.imap_email, settings.imap_password)
        mail.select("INBOX")

        # Search for UNSEEN (unread) emails only
        status, message_ids = mail.search(None, "UNSEEN")
        if status != "OK" or not message_ids[0]:
            print("📭 No new emails")
            mail.logout()
            return 0

        ids = message_ids[0].split()
        print(f"📬 Found {len(ids)} new email(s)")

        db = SessionLocal()
        try:
            for email_id in ids:
                try:
                    # Fetch the full email
                    status, data = mail.fetch(email_id, "(RFC822)")
                    if status != "OK":
                        continue

                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    created = process_email_message(msg, db)
                    total_created += created

                    # Mark as read so we don't process again
                    mail.store(email_id, "+FLAGS", "\\Seen")

                except Exception as e:
                    print(f"❌ Error processing email {email_id}: {e}")
                    # Mark as read anyway to avoid infinite retry loop
                    mail.store(email_id, "+FLAGS", "\\Seen")
        finally:
            db.close()

        mail.logout()
        print(f"✅ Poll complete — {total_created} invoice(s) created")

    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP connection error: {e}")
    except Exception as e:
        print(f"❌ Email worker error: {e}")

    return total_created


def start_email_worker():
    """
    Starts the email polling loop in a background thread.
    Runs forever, polling every EMAIL_POLL_INTERVAL seconds.
    Called once at app startup.
    """
    from app.config import get_settings
    settings = get_settings()

    if not settings.imap_email:
        print("⚠️  IMAP not configured — email worker disabled")
        return

    def worker_loop():
        print(f"📮 Email worker started — polling every {settings.email_poll_interval}s")
        while True:
            try:
                poll_inbox_once(settings)
            except Exception as e:
                print(f"❌ Worker loop error: {e}")
            time.sleep(settings.email_poll_interval)

    # daemon=True means the thread dies when the main process exits
    thread = threading.Thread(target=worker_loop, daemon=True)
    thread.start()
    print("📮 Email worker thread running")