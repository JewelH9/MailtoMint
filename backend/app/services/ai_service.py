import json
import re
import google.generativeai as genai
from app.config import get_settings

settings = get_settings()

genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-2.0-flash")


def parse_with_regex_fallback(raw_text: str) -> dict:
    result = {}
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    # --- Amount: look for explicit total patterns first ---
    # Order matters — most specific first
    total_patterns = [
        r"invoice\s*total[\s:₹Rs\.]*([0-9,]+\.?[0-9]*)",
        r"grand\s*total[\s:₹Rs\.]*([0-9,]+\.?[0-9]*)",
        r"total\s*amount[\s:₹Rs\.]*([0-9,]+\.?[0-9]*)",
        r"net\s*payable[\s:₹Rs\.]*([0-9,]+\.?[0-9]*)",
        r"amount\s*payable[\s:₹Rs\.]*([0-9,]+\.?[0-9]*)",
        # "Rs. 5000.00 / FIVE THOUSAND" pattern (Titan style)
        r"Rs\.?\s*([0-9,]+\.?[0-9]*)\s*/\s*[A-Z]+\s+THOUSAND",
        r"Rs\.?\s*([0-9,]+\.?[0-9]*)\s*/\s*[A-Z]+\s+HUNDRED",
        r"Rs\.?\s*([0-9,]+\.?[0-9]*)\s*/\s*[A-Z]+\s+LAKH",
        # "in words" pattern — amount before "only"
        r"([0-9,]+\.?[0-9]*)\s*(?:rupees\s*only|only)",
    ]
    for pattern in total_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1).replace(",", ""))
                if val >= 10:
                    result["total_amount"] = val
                    result["currency"] = "INR"
                    break
            except ValueError:
                pass

    # If no explicit total found, take largest number >= 100
    if not result.get("total_amount"):
        all_amounts = re.findall(r"([0-9,]+\.[0-9]{2})", raw_text)
        candidates = []
        for a in all_amounts:
            try:
                val = float(a.replace(",", ""))
                if val >= 100:
                    candidates.append(val)
            except ValueError:
                pass
        if candidates:
            result["total_amount"] = max(candidates)
            result["currency"] = "INR"

    # --- Invoice number ---
    inv_match = re.search(
        r"(?:invoice\s*(?:no|number|#)|bill\s*no|receipt\s*no|order\s*id)[\s:]*([A-Z0-9\-/]+)",
        raw_text, re.IGNORECASE
    )
    if inv_match:
        val = inv_match.group(1).strip()
        if len(val) > 2:
            result["invoice_number"] = val

    # --- Date ---
    date_patterns = [
        r"(?:date of invoice|invoice date|date)[\s:]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})",
        r"(\d{2}/\d{2}/\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{2}-\d{2}-\d{4})",
        r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %B %Y", "%d %b %Y", "%m/%d/%Y"):
                try:
                    from datetime import datetime as dt
                    parsed_date = dt.strptime(date_str.strip(), fmt)
                    result["invoice_date"] = parsed_date.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
            if result.get("invoice_date"):
                break

    # --- Vendor name ---
    # Strategy: look for known vendor signals first
    vendor_signals = [
        # "issued by X" or "invoice by X"
        r"(?:issued by|invoice by|billed by|sold by|from)\s*[:\-]?\s*([A-Z][A-Za-z\s&\.,]+(?:Ltd|Limited|Pvt|Inc|LLP|LLC|Private)?\.?)",
        # Company name before "Tax Invoice"
        r"^([A-Z][A-Z\s&\.,]+(?:LIMITED|LTD|PVT|PRIVATE|INC)\.?)",
        # Restaurant name pattern (Swiggy style)
        r"restaurant\s*name[\s:]*([A-Za-z\s&]+)",
    ]
    for pattern in vendor_signals:
        match = re.search(pattern, raw_text, re.IGNORECASE | re.MULTILINE)
        if match:
            vendor = match.group(1).strip()
            # Clean up — remove trailing punctuation and extra spaces
            vendor = re.sub(r"[,\.\s]+$", "", vendor).strip()
            if len(vendor) > 3:
                result["vendor_name"] = vendor[:80]
                break

    # Fallback: find first clean capitalized line
    if not result.get("vendor_name"):
        skip_patterns = re.compile(
            r"^(terms|conditions|page|date|invoice|bill|receipt|tax|gst|total|"
            r"amount|payment|original|customer|address|phone|email|dear|to|from|"
            r"igst|cgst|sgst|hsn|qty|description|sr|s\.no|item|thank|regards|"
            r"note|subject|ref|www\.|http|flat|plot|floor|road|nagar|lane|"
            r"known|formerly|technologies|bundl|\d)",
            re.IGNORECASE
        )
        for line in lines[:25]:
            if (len(line) > 5
                    and not skip_patterns.match(line)
                    and not re.match(r"^[\d\s₹Rs\.,:\-/\(\)]+$", line)
                    and sum(c.isalpha() for c in line) > 4
                    and not line.startswith("+")):
                result["vendor_name"] = line[:80]
                break

    # --- Tax amount ---
    tax_match = re.search(
        r"total\s*(?:tax(?:es)?|gst)[\s:₹Rs\.]*([0-9,]+\.?[0-9]*)",
        raw_text, re.IGNORECASE
    )
    if tax_match:
        try:
            result["tax_amount"] = float(tax_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # --- Category ---
    text_lower = raw_text.lower()
    category_keywords = {
        "food": [
            # Food delivery platforms
            "swiggy", "zomato", "dunzo", "blinkit", "bigbasket",
            # Restaurant keywords
            "restaurant", "cafe", "dhaba", "eatery", "kitchen", "bistro",
            "canteen", "food court", "bakery", "confectionery",
            # Food items
            "biryani", "pizza", "burger", "sandwich", "noodles", "pasta",
            "chicken", "mutton", "paneer", "dosa", "idli", "paratha",
            "thali", "meal", "snack", "dessert", "beverage",
            # Food invoice signals
            "fssai", "packing charges", "delivery charges", "order id",
            "restaurant service", "food service", "hsn 996331",
        ],
        "healthcare": [
            # Medical facilities
            "hospital", "clinic", "nursing home", "diagnostic", "pathology",
            "laboratory", "health centre", "medical centre",
            # Professionals
            "doctor", "physician", "dentist", "surgeon", "consultant",
            # Pharmacy
            "pharmacy", "medical store", "chemist", "medicine", "tablet",
            "capsule", "syrup", "prescription", "drug store", "medicos",
            # Optical (any brand)
            "optical", "optician", "eyewear", "spectacle", "sunglass",
            "contact lens", "eye care", "vision care", "lens", "frames",
            "fitting charges", "uv protection", "anti glare",
            # Health services
            "health", "wellness", "physiotherapy", "rehabilitation",
            "vaccination", "blood test", "x-ray", "scan", "mri", "ecg",
            "ultrasound", "consultation fee",
        ],
        "travel": [
            # Airlines and booking
            "flight", "airline", "airfare", "boarding pass", "airport",
            "makemytrip", "goibibo", "cleartrip", "yatra", "ixigo",
            "indigo", "air india", "spicejet", "vistara",
            # Ground transport
            "taxi", "cab", "auto", "uber", "ola", "rapido",
            "bus", "volvo", "shuttle",
            # Rail
            "railway", "train", "irctc", "platform ticket",
            # Accommodation
            "hotel", "resort", "inn", "lodge", "hostel", "oyo",
            "airbnb", "room rent", "accommodation",
            # Travel signals
            "booking", "reservation", "check in", "check out",
            "passenger", "journey", "trip", "tour",
        ],
        "office": [
            # Supplies
            "stationery", "pen", "pencil", "notebook", "paper", "file",
            "folder", "envelope", "stamp", "cartridge", "toner",
            # Equipment
            "printer", "scanner", "laptop", "desktop", "monitor",
            "keyboard", "mouse", "webcam", "headset", "projector",
            "hard disk", "usb", "cable",
            # Furniture
            "office furniture", "chair", "desk", "table", "cabinet",
            "whiteboard",
            # Services
            "office supplies", "office rent", "coworking", "workspace",
        ],
        "utilities": [
            # Bills
            "electricity", "electric bill", "power bill", "wbsedcl",
            "bescom", "tata power", "adani electricity",
            "water bill", "water supply",
            "gas bill", "piped gas", "indane", "hp gas", "bharat gas",
            # Telecom
            "internet", "broadband", "wifi", "jio", "airtel", "bsnl",
            "vodafone", "vi ", "recharge", "mobile bill", "postpaid",
            # Education (fees)
            "tuition", "fees", "school fees", "college fees", "admission",
            "examination fee", "university", "institute",
        ],
        "marketing": [
            "advertising", "advertisement", "google ads", "meta ads",
            "facebook ads", "instagram ads", "youtube ads",
            "marketing", "campaign", "promotion", "branding",
            "banner", "poster", "flyer", "pamphlet", "hoarding",
            "seo", "digital marketing", "social media",
            "pr agency", "public relations",
        ],
        "subscription": [
            # Entertainment
            "netflix", "amazon prime", "hotstar", "disney", "zee5",
            "spotify", "apple music", "youtube premium",
            # Software/SaaS
            "subscription", "saas", "software license", "annual plan",
            "monthly plan", "renewal", "membership",
            "adobe", "microsoft 365", "google workspace", "slack",
            "zoom", "dropbox", "github",
            # Other memberships
            "gym membership", "club membership",
        ],
    }
    # Check food FIRST — prevent Swiggy being tagged as travel
    for category in ["food", "healthcare", "travel", "office", "utilities", "marketing", "subscription"]:
        keywords = category_keywords[category]
        if any(kw in text_lower for kw in keywords):
            result["category"] = category
            break

    if not result.get("category"):
        result["category"] = "other"

    result["ai_notes"] = "Extracted using local parser"
    return result


def parse_invoice_with_ai(raw_text: str) -> dict:
    if not raw_text or len(raw_text.strip()) < 10:
        return {}

    # Try Gemini first
    if settings.gemini_api_key:
        prompt = f"""
You are an expert invoice parser. Extract structured data from this OCR text.

OCR TEXT:
{raw_text[:3000]}

Return ONLY a valid JSON object with these exact keys (use null for missing fields):
{{
  "vendor_name": "company name",
  "invoice_number": "invoice number",
  "total_amount": 1234.56,
  "tax_amount": 123.45,
  "currency": "INR",
  "invoice_date": "YYYY-MM-DD or null",
  "category": "one of: travel, food, office, utilities, marketing, healthcare, subscription, other",
  "ai_notes": "one sentence accounting note"
}}

Rules:
- total_amount must be a number
- Return ONLY the JSON, no explanation, no markdown
"""
        try:
            import time
            response = model.generate_content(prompt)
            raw_response = response.text.strip()
            raw_response = re.sub(r"```json\s*", "", raw_response)
            raw_response = re.sub(r"```\s*", "", raw_response)
            parsed = json.loads(raw_response)
            print("✅ Gemini parsed successfully")
            return parsed

        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                print("⚠️  Gemini quota exceeded — using local parser")
            elif "404" in error_str:
                print("⚠️  Gemini model not found — using local parser")
            else:
                print(f"⚠️  Gemini error ({e}) — using local parser")

    # Fallback to regex parser
    print("🔧 Running local regex parser...")
    result = parse_with_regex_fallback(raw_text)
    print(f"🔧 Local parser extracted: {result}")
    return result


def generate_insights(invoices_summary: str) -> str:
    if not settings.gemini_api_key:
        return ""
    prompt = f"""
You are a financial analyst. Analyze this invoice data and give 3 specific insights.

DATA:
{invoices_summary}

Format each as one sentence starting with an emoji.
Return only 3 insights, one per line.
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return ""