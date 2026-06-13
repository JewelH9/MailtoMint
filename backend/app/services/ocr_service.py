import os


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from digital PDFs — no OCR needed for clean PDFs."""
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(text)
        result = "\n\n".join(pages_text)
        print(f"📄 Extracted {len(result)} characters from PDF")
        return result
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""


def extract_text_from_image(file_path: str) -> str:
    """
    For now returns empty — PaddleOCR has Windows compatibility issues.
    Images will be processed once we switch to Gemini Vision in a later phase.
    """
    print(f"⚠️  Image OCR skipped for now — upload PDFs for best results")
    return ""


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in {".jpg", ".jpeg", ".png"}:
        return extract_text_from_image(file_path)
    return ""