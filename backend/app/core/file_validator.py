import os
import re

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/jpg"}

# Real file signatures (magic bytes) — first bytes of the file
# This detects the actual file type regardless of extension
MAGIC_BYTES = {
    b"%PDF":          "application/pdf",
    b"\xff\xd8\xff":  "image/jpeg",
    b"\x89PNG":       "image/png",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def detect_mime_from_bytes(file_path: str) -> str:
    """Read first 8 bytes and match against known signatures."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
        for signature, mime in MAGIC_BYTES.items():
            if header.startswith(signature):
                return mime
        return "unknown"
    except Exception:
        return "unknown"


def validate_file_content(file_path: str) -> tuple[bool, str]:
    if not os.path.exists(file_path):
        return False, "File not found"

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return False, "File is empty"

    if file_size > MAX_FILE_SIZE:
        return False, f"File exceeds 10MB limit ({file_size / 1024 / 1024:.1f}MB)"

    mime = detect_mime_from_bytes(file_path)
    if mime not in MAGIC_BYTES.values():
        os.remove(file_path)
        return False, f"Invalid file type. Only PDF, JPG, PNG allowed."

    return True, ""


def sanitize_filename(filename: str) -> str:
    filename = os.path.basename(filename)
    filename = re.sub(r"[^\w\s\-.]", "", filename)
    filename = re.sub(r"\.{2,}", ".", filename)
    filename = filename.strip()
    return filename or "unnamed_file"