# MailToMint

**AI-powered invoice and expense intelligence platform for modern businesses.**

MailToMint automates the most painful part of business finance — managing invoices. Upload a PDF or image, and within seconds the platform extracts vendor name, amount, date, GST, and category using OCR and AI. Duplicate invoices are flagged automatically. Spending patterns are visualized in real time. Everything is exportable in one click.

**Live demo:** https://mailto-mint.vercel.app

---

## The problem it solves

Small businesses and finance teams waste hours every week manually entering invoice data into spreadsheets, checking for duplicates, and building expense reports. MailToMint eliminates all of that:

- A Swiggy invoice forwarded to your unique inbox gets processed automatically — no manual entry
- A duplicate bill submitted twice gets flagged before it's paid
- Month-end expense reports that used to take hours are exported in seconds
- Unusual spending spikes are detected and surfaced before they become problems

---

## Features

### Smart invoice upload

Drag and drop PDFs, JPGs, or PNGs. The platform validates the real file content (not just the extension), saves it securely, and immediately begins processing in the background so the UI stays responsive.

### OCR + AI extraction

Text is extracted from digital PDFs using `pypdf` and from scanned documents using PaddleOCR. The raw text is then sent to Google Gemini 2.0 Flash which returns structured JSON — vendor name, invoice number, total amount, tax, date, currency, and expense category. A regex fallback parser handles cases where the AI quota is exceeded, ensuring the system never fails silently.

### Email invoice automation

Every user gets a unique inbox address (e.g. `raj-a3f9@mailtomint.io`). Forwarding any invoice email to that address triggers automatic extraction — no upload needed. Built with IMAP polling and designed to migrate to Cloudflare Email Routing webhooks for production scale.

### AI fraud detection

A rule-based scoring engine runs on every invoice and produces a fraud score from 0.0 to 1.0. Five checks are applied: exact duplicate detection, fuzzy duplicate matching using Levenshtein distance, amount spike detection (3x vendor average), suspiciously round amounts with no tax breakdown, and rapid resubmission within 24 hours. Flagged invoices appear in a dedicated fraud dashboard with risk labels and score bars.

### Analytics dashboard

Real-time charts built with Recharts show monthly spending trends, category breakdowns, and top vendors by spend. Summary cards display total invoices, total spend, this month's spend, and flagged count. An AI insights panel calls Gemini to generate natural language observations like "Food spending increased 38% this month."

### Natural language search

Search invoices the way you'd speak: "Amazon bills from March", "Travel expenses above 5000", "Flagged invoices". A custom query parser extracts structured filters (vendor, month, amount range, category, status) from plain English and translates them into efficient database queries with 400ms debouncing.

### Export engine

One-click export to CSV (works in any spreadsheet app), Excel (formatted `.xlsx` with green headers, alternating row shading, and a summary row), or PDF (branded report with summary stats table). All formats support date range and category filters.

### Security hardening

Rate limiting on auth endpoints (5/min signup, 10/min login), magic bytes file validation, filename sanitization to prevent path traversal, input sanitization against XSS, security headers on every response (X-Frame-Options, X-Content-Type-Options, CSP), request size limits, and a global error handler that never leaks stack traces to clients.

---

## Tech stack

| Layer      | Technology                                               |
| ---------- | -------------------------------------------------------- |
| Frontend   | React 18, Vite, Tailwind CSS v3, Recharts, Zustand       |
| Backend    | Python, FastAPI, SQLAlchemy ORM                          |
| Database   | SQLite (development), Supabase PostgreSQL (production)   |
| AI / OCR   | Google Gemini 2.0 Flash, pypdf, PaddleOCR                |
| Auth       | JWT (python-jose), bcrypt password hashing               |
| Export     | openpyxl (Excel), reportlab (PDF)                        |
| Security   | slowapi (rate limiting), magic bytes validation          |
| Storage    | Local (development), Cloudinary (production)             |
| Deployment | Vercel (frontend), Render (backend), Supabase (database) |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                     │
│          Vercel · mailto-mint.vercel.app             │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS + JWT
┌──────────────────────▼──────────────────────────────┐
│                  FastAPI Backend                     │
│            Render · mailtomint-api.onrender.com      │
│                                                      │
│  /auth      /invoices    /analytics    /fraud        │
│  /search    /export      /settings     /email        │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │           Processing Pipeline               │    │
│  │  Upload → OCR → Gemini AI → Fraud Check    │    │
│  │  (runs in background, non-blocking)         │    │
│  └─────────────────────────────────────────────┘    │
└──────┬─────────────────────┬────────────────────────┘
       │                     │
┌──────▼──────┐    ┌─────────▼──────────┐
│  Supabase   │    │     Cloudinary     │
│ PostgreSQL  │    │   File Storage     │
└─────────────┘    └────────────────────┘
```

---

## Local development

**Prerequisites:** Python 3.11+, Node 18+

```bash
# Clone
git clone https://github.com/JewelH9/MailtoMint.git
cd MailtoMint

# Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt

# Create .env
cp .env.example .env
# Fill in your GEMINI_API_KEY

uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

---

## Environment variables

**Backend `.env`:**

```env
DATABASE_URL=sqlite:///./mailtomint.db
SECRET_KEY=your-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
APP_ENV=development
ALLOWED_ORIGINS=http://localhost:5173
GEMINI_API_KEY=your-gemini-api-key
```

Production additionally requires:

```env
APP_ENV=production
DATABASE_URL=postgresql://...supabase...
ALLOWED_ORIGINS=https://your-frontend.vercel.app
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

---

## API reference

```
POST   /auth/signup              Create account
POST   /auth/login               Login, returns JWT
GET    /auth/me                  Get current user

GET    /invoices                 List invoices (filterable)
POST   /invoices/upload          Upload invoice file
GET    /invoices/{id}            Get single invoice
PATCH  /invoices/{id}            Update invoice fields
DELETE /invoices/{id}            Delete invoice

GET    /analytics/summary        Stats overview
GET    /analytics/monthly        Monthly trend data
GET    /analytics/categories     Category breakdown
GET    /analytics/vendors        Top vendors by spend
GET    /analytics/insights       AI-generated insights

GET    /fraud/flags              All flagged invoices
GET    /fraud/summary            Fraud statistics
POST   /fraud/recheck/{id}       Re-run fraud check

GET    /search?q=                Natural language search

GET    /export/csv               Download CSV
GET    /export/excel             Download Excel
GET    /export/pdf               Download PDF report

GET    /settings/profile         User profile + stats
PATCH  /settings/profile         Update display name
POST   /settings/change-password Change password
DELETE /settings/account         Delete account
```

---

## Project structure

```
MailtoMint/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middleware, routers
│   │   ├── config.py            # Pydantic settings, env vars
│   │   ├── database.py          # SQLAlchemy engine and session
│   │   ├── models/              # ORM models (User, Invoice)
│   │   ├── schemas/             # Pydantic request/response shapes
│   │   ├── routers/             # Route handlers per feature
│   │   ├── services/            # Business logic
│   │   │   ├── ocr_service.py           # PDF/image text extraction
│   │   │   ├── ai_service.py            # Gemini + regex fallback
│   │   │   ├── fraud_service.py         # Fraud scoring engine
│   │   │   ├── processing_pipeline.py   # OCR → AI → Fraud orchestration
│   │   │   ├── export_service.py        # CSV, Excel, PDF generation
│   │   │   ├── email_worker.py          # IMAP polling worker
│   │   │   └── storage_service.py       # Cloudinary file storage
│   │   └── core/
│   │       ├── auth.py          # JWT dependency injection
│   │       ├── security.py      # Password hashing, token creation
│   │       ├── limiter.py       # Rate limiter setup
│   │       ├── middleware.py    # Security headers, request size
│   │       ├── file_validator.py # Magic bytes validation
│   │       └── sanitizer.py    # Input sanitization
│   ├── requirements.txt
│   └── runtime.txt
│
└── frontend/
    └── src/
        ├── api/client.js        # Axios with JWT interceptors
        ├── store/authStore.js   # Zustand global auth state
        ├── components/          # Navbar, Layout, UploadZone, ProtectedRoute
        └── pages/               # Dashboard, Invoices, Analytics,
                                 # Fraud, Search, Export, Settings
```

---

## What makes this different from typical student projects

Most invoice projects stop at "upload a file and show it in a table." MailToMint goes further in several ways:

**Background processing pipeline** — uploads return instantly while OCR and AI run asynchronously in a background thread. Users never wait for AI to finish.

**Graceful degradation** — when Gemini quota is exceeded, a regex fallback parser takes over automatically. The system never fails silently or shows empty results.

**Real fraud detection** — five independent scoring checks with weighted confidence scores, fuzzy string matching for near-duplicate detection, and a visual risk dashboard. Not just a boolean "duplicate" flag.

**Email automation** — each user gets a unique inbox address. Forwarding an invoice email is enough to trigger the full processing pipeline with no manual upload. This is the pattern used by real expense management tools like Expensify and Dext.

**Production security** — magic bytes file validation (catches renamed malware), rate limiting on auth routes, security headers, input sanitization, and a global error handler that never exposes internals to clients.

---

## Deployment

| Service     | Purpose             | Plan |
| ----------- | ------------------- | ---- |
| Vercel      | Frontend hosting    | Free |
| Render      | Backend API         | Free |
| Supabase    | PostgreSQL database | Free |
| Cloudinary  | File storage        | Free |
| UptimeRobot | Uptime monitoring   | Free |

Total infrastructure cost: **$0/month**

---

## Roadmap

- [ ] Cloudflare Email Routing webhooks (replace IMAP polling)
- [ ] Recurring expense detection
- [ ] Vendor trust scoring
- [ ] AI spending predictions
- [ ] Voice-based invoice querying
- [ ] Multi-user organization support
- [ ] Mobile app (React Native)

---

## Author

Built by **Jewel Hossain** — MSIT student, full-stack developer.

GitHub: [@JewelH9](https://github.com/JewelH9)
